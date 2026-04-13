#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ingest.py — Chunk and embed cleaned Markdown files into Qdrant.

Reads from processed/*.md (output of convert.py).
Edit those markdown files first, then run this.

Idempotent: safe to re-run, skips already-embedded chunks.

Usage:
    python ingest.py
"""

import atexit
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

openai_client: Optional[OpenAI] = None
qdrant_client: Optional[QdrantClient] = None


def get_openai_client() -> OpenAI:
    global openai_client
    if openai_client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not set.")
        openai_client = OpenAI(api_key=api_key)
    return openai_client


def get_qdrant_client() -> QdrantClient:
    global qdrant_client
    if qdrant_client is None:
        qdrant_client = QdrantClient(url=config.QDRANT_URL)
    return qdrant_client


def close_qdrant_client() -> None:
    global qdrant_client
    if qdrant_client is not None:
        try:
            qdrant_client.close()
        except Exception:
            pass
        finally:
            qdrant_client = None


atexit.register(close_qdrant_client)


def ensure_collection() -> None:
    client = get_qdrant_client()
    try:
        client.get_collection(config.QDRANT_COLLECTION)
    except Exception:
        client.create_collection(
            collection_name=config.QDRANT_COLLECTION,
            vectors_config=VectorParams(size=config.EMBED_DIMENSIONS, distance=Distance.COSINE),
        )
        logger.info(f"Created Qdrant collection: {config.QDRANT_COLLECTION}")


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text)
    return text.strip("-")


def parse_frontmatter(md_content: str) -> tuple[dict, str]:
    if not md_content.startswith("---"):
        raise ValueError("No frontmatter found")
    parts = md_content.split("---", 2)
    if len(parts) < 3:
        raise ValueError("Invalid frontmatter format")
    metadata = yaml.safe_load(parts[1])
    body = parts[2].strip()
    return metadata, body


def count_words(text: str) -> int:
    return len(text.split())


def build_chunks(paragraphs: list[str], book_slug: str, metadata: dict) -> list[dict]:
    chunks = []
    current_paragraphs = []
    current_word_count = 0
    chunk_index = 0

    def flush(paras, word_count):
        if not paras:
            return
        nonlocal chunk_index
        chunks.append({
            "chunk_id": f"{book_slug}_{chunk_index:04d}",
            "book_title": metadata["title"],
            "source_file": metadata["source_file"],
            "source_type": "book",
            "chapter": "",
            "text": "\n\n".join(paras),
            "word_count": word_count,
        })
        chunk_index += 1

    for paragraph in paragraphs:
        para_word_count = count_words(paragraph)

        # Bracketed editorial lines are topic boundaries — skip and flush
        stripped = paragraph.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            flush(current_paragraphs, current_word_count)
            current_paragraphs = []
            current_word_count = 0
            continue

        if current_word_count + para_word_count > config.MAX_CHUNK_WORDS:
            flush(current_paragraphs, current_word_count)
            current_paragraphs = []
            current_word_count = 0

            if para_word_count > config.MAX_CHUNK_WORDS:
                flush([paragraph], para_word_count)
                continue

        current_paragraphs.append(paragraph)
        current_word_count += para_word_count

        if current_word_count >= config.TARGET_CHUNK_WORDS:
            flush(current_paragraphs, current_word_count)
            current_paragraphs = []
            current_word_count = 0

    flush(current_paragraphs, current_word_count)
    return chunks


def get_existing_chunk_ids() -> set[str]:
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
    client = get_openai_client()
    response = client.embeddings.create(
        model=config.OPENAI_EMBED_MODEL,
        input=[chunk["text"] for chunk in chunks],
    )
    return [item.embedding for item in response.data]


def chunk_to_point(chunk: dict, embedding: list[float]) -> PointStruct:
    point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk["chunk_id"]))
    return PointStruct(
        id=point_id,
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


def process_markdown(md_path: Path, existing_chunk_ids: set[str]) -> dict:
    result = {
        "source": md_path.name,
        "chunks_created": 0,
        "chunks_embedded": 0,
        "chunks_skipped": 0,
        "error": None,
    }

    try:
        md_content = md_path.read_text(encoding="utf-8")
        metadata, body = parse_frontmatter(md_content)

        paragraphs = [p.strip() for p in body.split("\n\n") if p.strip()]
        if not paragraphs:
            logger.warning(f"No paragraphs found in {md_path.name}")
            return result

        book_slug = metadata.get("slug", slugify(metadata["title"]))
        chunks = build_chunks(paragraphs, book_slug, metadata)
        result["chunks_created"] = len(chunks)

        new_chunks = [c for c in chunks if c["chunk_id"] not in existing_chunk_ids]
        result["chunks_skipped"] = len(chunks) - len(new_chunks)

        if not new_chunks:
            logger.info(f"Skipping {md_path.name} (all {len(chunks)} chunks already embedded)")
            return result

        logger.info(f"Embedding {len(new_chunks)} chunks for {md_path.name} (skipped {result['chunks_skipped']})")

        embed_batch_size = 32
        upsert_batch_size = 16
        all_points = []
        for i in range(0, len(new_chunks), embed_batch_size):
            batch = new_chunks[i:i + embed_batch_size]
            embeddings = embed_chunks_batch(batch)
            for chunk, embedding in zip(batch, embeddings):
                all_points.append(chunk_to_point(chunk, embedding))

        # Batch upserts to Qdrant to avoid payload size limits
        for i in range(0, len(all_points), upsert_batch_size):
            batch_points = all_points[i:i + upsert_batch_size]
            get_qdrant_client().upsert(
                collection_name=config.QDRANT_COLLECTION,
                points=batch_points,
            )
        result["chunks_embedded"] = len(new_chunks)

    except Exception as e:
        logger.error(f"Error processing {md_path.name}: {e}")
        result["error"] = str(e)

    return result


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--prefix", help="Only ingest files whose name starts with this prefix (e.g. 'a,b')")
    args = parser.parse_args()

    logger.info("Starting ingestion...")

    config.MARKDOWN_DIR.mkdir(parents=True, exist_ok=True)
    config.DB_DIR.mkdir(parents=True, exist_ok=True)

    md_files = sorted(config.MARKDOWN_DIR.glob("*.md"))
    if not md_files:
        logger.warning(f"No markdown files found in {config.MARKDOWN_DIR}. Run convert.py first.")
        return

    if args.prefix:
        prefixes = tuple(p.strip().lower() for p in args.prefix.split(","))
        md_files = [f for f in md_files if f.name.lower().startswith(prefixes)]
        logger.info(f"Filtered to {len(md_files)} files matching prefix(es): {prefixes}")
    else:
        logger.info(f"Found {len(md_files)} markdown files")

    ensure_collection()

    logger.info("Checking existing embeddings...")
    existing_chunk_ids = get_existing_chunk_ids()
    logger.info(f"Found {len(existing_chunk_ids)} existing chunks")

    total_created = total_embedded = total_skipped = 0
    errors = []

    with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
        future_to_file = {
            executor.submit(process_markdown, f, existing_chunk_ids): f
            for f in md_files
        }
        for i, future in enumerate(as_completed(future_to_file), 1):
            file_path = future_to_file[future]
            try:
                result = future.result()
                total_created += result["chunks_created"]
                total_embedded += result["chunks_embedded"]
                total_skipped += result["chunks_skipped"]
                if result["error"]:
                    errors.append((file_path.name, result["error"]))
                status = "✓" if not result["error"] else "✗"
                logger.info(
                    f"[{i:3d}/{len(md_files):3d}] {file_path.name:40s} "
                    f"chunks: {result['chunks_embedded']:3d} embedded, "
                    f"{result['chunks_skipped']:3d} skipped {status}"
                )
            except Exception as e:
                logger.error(f"Unhandled error for {file_path.name}: {e}")
                errors.append((file_path.name, str(e)))

    logger.info("=" * 60)
    logger.info("Ingestion complete!")
    logger.info(f"  Chunks created:  {total_created}")
    logger.info(f"  Chunks embedded: {total_embedded}")
    logger.info(f"  Chunks skipped:  {total_skipped}")
    if errors:
        logger.warning(f"  Errors: {len(errors)}")
        for name, err in errors[:5]:
            logger.warning(f"    - {name}: {err}")

    close_qdrant_client()


if __name__ == "__main__":
    main()
