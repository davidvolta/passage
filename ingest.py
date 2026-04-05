#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ingest.py — Convert books to searchable passages.

One script that does it all:
  1. Convert PDF/EPUB → Markdown (with YAML frontmatter)
  2. Chunk Markdown → ~200 word passages
  3. Embed passages → OpenAI vectors
  4. Store in Qdrant (local)

Idempotent: safe to re-run, only processes new books.
Parallel: processes multiple books concurrently.

Usage:
    python ingest.py
"""

import logging
import os
import re
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional

import yaml
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

import config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Initialize clients (module level for reuse)
openai_client: Optional[OpenAI] = None
qdrant_client: Optional[QdrantClient] = None


def get_openai_client() -> OpenAI:
    """Get or create OpenAI client."""
    global openai_client
    if openai_client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY not set. Get a key from https://platform.openai.com/api-keys"
            )
        openai_client = OpenAI(api_key=api_key)
    return openai_client


def get_qdrant_client() -> QdrantClient:
    """Get or create Qdrant client."""
    global qdrant_client
    if qdrant_client is None:
        qdrant_client = QdrantClient(path=str(config.DB_DIR))
    return qdrant_client


def ensure_collection() -> None:
    """Ensure Qdrant collection exists with correct schema."""
    client = get_qdrant_client()
    try:
        client.get_collection(config.QDRANT_COLLECTION)
    except Exception:
        client.create_collection(
            collection_name=config.QDRANT_COLLECTION,
            vectors_config=VectorParams(
                size=config.EMBED_DIMENSIONS,
                distance=Distance.COSINE,
            ),
        )
        logger.info(f"Created Qdrant collection: {config.QDRANT_COLLECTION}")


def slugify(text: str) -> str:
    """Convert text to URL-safe slug."""
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text)
    return text.strip("-")


def filename_to_title(stem: str) -> str:
    """Convert filename stem to human-readable title."""
    title = stem.replace("_", " ").replace("-", " ")
    return title.title()


def extract_pdf_title(pdf_path: Path) -> str:
    """Extract title from PDF metadata, fallback to filename."""
    try:
        import fitz  # pymupdf

        doc = fitz.open(str(pdf_path))
        metadata = doc.metadata
        doc.close()

        title = metadata.get("title", "").strip()
        if title and title.lower() not in ("untitled", "", "unknown"):
            return title
    except Exception as e:
        logger.debug(f"Could not extract PDF title from {pdf_path}: {e}")

    return filename_to_title(pdf_path.stem)


def extract_epub_title(epub_path: Path) -> str:
    """Extract title from EPUB metadata, fallback to filename."""
    try:
        import ebooklib
        from ebooklib import epub

        book = epub.read_epub(str(epub_path))
        titles = book.get_metadata("DC", "title")
        if titles:
            return titles[0][0]
    except Exception as e:
        logger.debug(f"Could not extract EPUB title from {epub_path}: {e}")

    return filename_to_title(epub_path.stem)


def convert_pdf_to_markdown(pdf_path: Path) -> tuple[str, str]:
    """
    Convert PDF to markdown text.
    Returns (title, markdown_body).
    """
    import pymupdf4llm

    title = extract_pdf_title(pdf_path)
    logger.debug(f"Converting PDF: {pdf_path.name} (title: {title})")

    # Extract markdown text
    md_text = pymupdf4llm.to_markdown(str(pdf_path))

    return title, md_text


def convert_epub_to_markdown(epub_path: Path) -> tuple[str, str]:
    """
    Convert EPUB to markdown text.
    Returns (title, markdown_body).
    """
    import ebooklib
    from ebooklib import epub
    import html2text

    title = extract_epub_title(epub_path)
    logger.debug(f"Converting EPUB: {epub_path.name} (title: {title})")

    book = epub.read_epub(str(epub_path))

    # Setup html2text
    h = html2text.HTML2Text()
    h.ignore_links = True
    h.ignore_images = True
    h.body_width = 0  # No line wrapping
    h.ignore_emphasis = False

    # Process spine items in order
    chapters = []
    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            try:
                html_content = item.get_content().decode("utf-8", errors="ignore")
                md_content = h.handle(html_content)
                chapters.append(md_content)
            except Exception as e:
                logger.debug(f"Could not process chapter in {epub_path}: {e}")

    md_text = "\n\n".join(chapters)
    return title, md_text


def write_markdown(
    output_path: Path, title: str, source_file: str, fmt: str, body: str
) -> None:
    """Write markdown with YAML frontmatter."""
    slug = slugify(title)

    frontmatter = {
        "title": title,
        "source_file": source_file,
        "format": fmt,
        "slug": slug,
    }

    content = f"---\n{yaml.dump(frontmatter, default_flow_style=False)}---\n\n{body}"
    output_path.write_text(content, encoding="utf-8")


def parse_frontmatter(md_content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter and return (metadata, body)."""
    if not md_content.startswith("---"):
        raise ValueError("No frontmatter found")

    parts = md_content.split("---", 2)
    if len(parts) < 3:
        raise ValueError("Invalid frontmatter format")

    metadata = yaml.safe_load(parts[1])
    body = parts[2].strip()
    return metadata, body


def split_paragraphs(body: str) -> list[str]:
    """Split body into clean paragraphs, filtering noise."""
    # Split on blank lines
    raw_paragraphs = re.split(r"\n\n+", body)

    paragraphs = []
    for p in raw_paragraphs:
        p = p.strip()
        if not p:
            continue
        # Skip very short paragraphs (likely headers/artifacts)
        word_count = len(p.split())
        if word_count < 5:
            continue
        # Skip ALL CAPS lines (running headers)
        if p.isupper():
            continue
        paragraphs.append(p)

    return paragraphs


def count_words(text: str) -> int:
    """Count words in text."""
    return len(text.split())


def build_chunks(
    paragraphs: list[str], book_slug: str, metadata: dict
) -> list[dict]:
    """
    Build chunks using greedy accumulator.
    Target: ~200 words, max: 300 words.
    """
    chunks = []
    current_paragraphs = []
    current_word_count = 0
    chunk_index = 0

    for paragraph in paragraphs:
        para_word_count = count_words(paragraph)

        # If adding this paragraph exceeds max, flush current chunk
        if current_word_count + para_word_count > config.MAX_CHUNK_WORDS:
            if current_paragraphs:
                chunk_text = "\n\n".join(current_paragraphs)
                chunks.append(
                    {
                        "chunk_id": f"{book_slug}_{chunk_index:04d}",
                        "book_title": metadata["title"],
                        "source_file": metadata["source_file"],
                        "source_type": "book",
                        "chapter": "",  # Reserved for future use
                        "text": chunk_text,
                        "word_count": current_word_count,
                    }
                )
                chunk_index += 1
                current_paragraphs = []
                current_word_count = 0

        # Add paragraph to current chunk
        current_paragraphs.append(paragraph)
        current_word_count += para_word_count

        # If we've hit target, flush
        if current_word_count >= config.TARGET_CHUNK_WORDS:
            chunk_text = "\n\n".join(current_paragraphs)
            chunks.append(
                {
                    "chunk_id": f"{book_slug}_{chunk_index:04d}",
                    "book_title": metadata["title"],
                    "source_file": metadata["source_file"],
                    "source_type": "book",
                    "chapter": "",
                    "text": chunk_text,
                    "word_count": current_word_count,
                }
            )
            chunk_index += 1
            current_paragraphs = []
            current_word_count = 0

    # Flush remaining paragraphs
    if current_paragraphs:
        chunk_text = "\n\n".join(current_paragraphs)
        chunks.append(
            {
                "chunk_id": f"{book_slug}_{chunk_index:04d}",
                "book_title": metadata["title"],
                "source_file": metadata["source_file"],
                "source_type": "book",
                "chapter": "",
                "text": chunk_text,
                "word_count": current_word_count,
            }
        )

    return chunks



def get_existing_chunk_ids_from_payload() -> set[str]:
    """Get chunk_ids from Qdrant payload (more reliable)."""
    client = get_qdrant_client()
    existing_ids = set()

    try:
        offset = None
        while True:
            result = client.scroll(
                collection_name=config.QDRANT_COLLECTION,
                offset=offset,
                limit=1000,
                with_payload=["chunk_id"],
                with_vectors=False,
            )

            for point in result[0]:
                if point.payload and "chunk_id" in point.payload:
                    existing_ids.add(point.payload["chunk_id"])

            offset = result[1]
            if offset is None:
                break

    except Exception as e:
        logger.debug(f"Could not get existing chunk IDs: {e}")

    return existing_ids


def embed_chunks_batch(chunks: list[dict]) -> list[list[float]]:
    """Embed a batch of chunks using OpenAI."""
    client = get_openai_client()

    texts = [chunk["text"] for chunk in chunks]

    response = client.embeddings.create(
        model=config.OPENAI_EMBED_MODEL,
        input=texts,
    )

    embeddings = [item.embedding for item in response.data]
    return embeddings


def chunk_to_point(chunk: dict, embedding: list[float]) -> PointStruct:
    """Convert chunk dict to Qdrant PointStruct."""
    # Generate deterministic UUID from chunk_id
    chunk_id = chunk["chunk_id"]
    point_id = uuid.uuid5(uuid.NAMESPACE_DNS, chunk_id)

    return PointStruct(
        id=str(point_id),
        vector=embedding,
        payload={
            "chunk_id": chunk["chunk_id"],
            "book_title": chunk["book_title"],
            "source_file": chunk["source_file"],
            "source_type": chunk["source_type"],
            "chapter": chunk["chapter"],
            "text": chunk["text"],
            "word_count": chunk["word_count"],
        },
    )


def process_book(source_path: Path, existing_chunk_ids: set[str]) -> dict:
    """
    Full pipeline for one book: convert → chunk → embed → store.
    Returns summary dict.
    """
    result = {
        "source": source_path.name,
        "converted": False,
        "chunks_created": 0,
        "chunks_embedded": 0,
        "chunks_skipped": 0,
        "error": None,
    }

    try:
        # Determine format and convert
        fmt = source_path.suffix.lower()[1:]  # 'pdf' or 'epub'
        md_path = config.MARKDOWN_DIR / f"{slugify(source_path.stem)}.md"

        # Check if already converted
        if md_path.exists():
            logger.debug(f"Skipping conversion for {source_path.name} (already exists)")
            md_content = md_path.read_text(encoding="utf-8")
            metadata, body = parse_frontmatter(md_content)
            title = metadata["title"]
            result["converted"] = True  # Already done
        else:
            logger.info(f"Converting: {source_path.name}")
            if fmt == "pdf":
                title, body = convert_pdf_to_markdown(source_path)
            elif fmt == "epub":
                title, body = convert_epub_to_markdown(source_path)
            else:
                raise ValueError(f"Unknown format: {fmt}")

            # Write markdown
            config.MARKDOWN_DIR.mkdir(parents=True, exist_ok=True)
            write_markdown(md_path, title, source_path.name, fmt, body)
            result["converted"] = True

            # Parse frontmatter for chunking
            md_content = md_path.read_text(encoding="utf-8")
            metadata, body = parse_frontmatter(md_content)

        # Chunk
        paragraphs = split_paragraphs(body)
        if not paragraphs:
            logger.warning(f"No paragraphs found in {source_path.name}")
            return result

        book_slug = metadata.get("slug", slugify(metadata["title"]))
        chunks = build_chunks(paragraphs, book_slug, metadata)
        result["chunks_created"] = len(chunks)

        if not chunks:
            logger.warning(f"No chunks created for {source_path.name}")
            return result

        # Filter out already-embedded chunks
        new_chunks = [
            c for c in chunks if c["chunk_id"] not in existing_chunk_ids
        ]
        result["chunks_skipped"] = len(chunks) - len(new_chunks)

        if not new_chunks:
            logger.info(
                f"Skipping embedding for {source_path.name} (all {len(chunks)} chunks already embedded)"
            )
            return result

        logger.info(
            f"Embedding {len(new_chunks)} chunks for {source_path.name} (skipped {result['chunks_skipped']})"
        )

        # Embed in batches
        batch_size = 32
        all_points = []

        for i in range(0, len(new_chunks), batch_size):
            batch = new_chunks[i : i + batch_size]
            embeddings = embed_chunks_batch(batch)

            for chunk, embedding in zip(batch, embeddings):
                point = chunk_to_point(chunk, embedding)
                all_points.append(point)

        # Upload to Qdrant
        client = get_qdrant_client()
        client.upsert(
            collection_name=config.QDRANT_COLLECTION,
            points=all_points,
        )

        result["chunks_embedded"] = len(new_chunks)

    except Exception as e:
        logger.error(f"Error processing {source_path.name}: {e}")
        result["error"] = str(e)

    return result


def collect_source_files() -> list[Path]:
    """Collect all PDF and EPUB files from books directories."""
    files = []

    if config.BOOKS_PDF_DIR.exists():
        files.extend(config.BOOKS_PDF_DIR.glob("*.pdf"))

    if config.BOOKS_EPUB_DIR.exists():
        files.extend(config.BOOKS_EPUB_DIR.glob("*.epub"))

    return sorted(files)


def main():
    """Main entry point."""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", type=Path, help="Process a single file instead of all books")
    args = parser.parse_args()

    logger.info("Starting ingestion...")

    # Ensure directories exist
    config.MARKDOWN_DIR.mkdir(parents=True, exist_ok=True)
    config.DB_DIR.mkdir(parents=True, exist_ok=True)

    # Ensure Qdrant collection exists
    ensure_collection()

    # Collect source files
    if args.file:
        if not args.file.exists():
            logger.error(f"File not found: {args.file}")
            return
        source_files = [args.file]
    else:
        source_files = collect_source_files()

    if not source_files:
        logger.warning("No source files found in books/pdf/ or books/epub/")
        return

    logger.info(f"Found {len(source_files)} source files")

    # Get existing chunk IDs (for idempotency)
    logger.info("Checking existing embeddings...")
    existing_chunk_ids = get_existing_chunk_ids_from_payload()
    logger.info(f"Found {len(existing_chunk_ids)} existing chunks")

    # Process books in parallel
    total_converted = 0
    total_chunks_created = 0
    total_chunks_embedded = 0
    total_chunks_skipped = 0
    errors = []

    with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
        # Submit all tasks
        future_to_file = {
            executor.submit(process_book, f, existing_chunk_ids): f
            for f in source_files
        }

        # Process results as they complete
        for i, future in enumerate(as_completed(future_to_file), 1):
            file_path = future_to_file[future]
            try:
                result = future.result()

                if result["converted"]:
                    total_converted += 1
                total_chunks_created += result["chunks_created"]
                total_chunks_embedded += result["chunks_embedded"]
                total_chunks_skipped += result["chunks_skipped"]

                if result["error"]:
                    errors.append((file_path.name, result["error"]))

                status = "✓" if not result["error"] else "✗"
                logger.info(
                    f"[{i:3d}/{len(source_files):3d}] {file_path.name:40s} "
                    f"chunks: {result['chunks_embedded']:3d} embedded, "
                    f"{result['chunks_skipped']:3d} skipped {status}"
                )

            except Exception as e:
                logger.error(f"Unhandled error for {file_path.name}: {e}")
                errors.append((file_path.name, str(e)))

    # Summary
    logger.info("=" * 60)
    logger.info("Ingestion complete!")
    logger.info(f"  Books converted: {total_converted}")
    logger.info(f"  Chunks created:  {total_chunks_created}")
    logger.info(f"  Chunks embedded: {total_chunks_embedded}")
    logger.info(f"  Chunks skipped:  {total_chunks_skipped}")

    if errors:
        logger.warning(f"  Errors: {len(errors)}")
        for name, err in errors[:5]:
            logger.warning(f"    - {name}: {err}")


if __name__ == "__main__":
    main()
