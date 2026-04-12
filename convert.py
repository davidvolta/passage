#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
convert.py — Convert PDF/EPUB books to cleaned Markdown files.

Outputs one .md file per book to processed/, with YAML frontmatter.
Edit the markdown files before running ingest.py.

Usage:
    python convert.py              # convert all books
    python convert.py --force      # re-convert even if .md already exists
"""

import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import yaml

import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text)
    return text.strip("-")


def filename_to_title(stem: str) -> str:
    return stem.replace("_", " ").replace("-", " ").title()


def extract_pdf_title(pdf_path: Path) -> str:
    try:
        import fitz
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
    try:
        from ebooklib import epub
        book = epub.read_epub(str(epub_path))
        titles = book.get_metadata("DC", "title")
        if titles:
            return titles[0][0]
    except Exception as e:
        logger.debug(f"Could not extract EPUB title from {epub_path}: {e}")
    return filename_to_title(epub_path.stem)


def _strip_md_formatting(line: str) -> str:
    """Strip markdown formatting for comparison purposes."""
    line = re.sub(r"\*{1,2}(.+?)\*{1,2}", r"\1", line)  # bold/italic
    line = re.sub(r"_{1,2}(.+?)_{1,2}", r"\1", line)      # underscore italic/bold
    line = re.sub(r"^#{1,6}\s*", "", line)                 # headers
    return line.strip()


def detect_running_lines(pages: list[str], check_lines: int = 3, threshold: float = 0.15) -> set[str]:
    """
    Find lines that repeat across many pages — these are running headers/footers.
    Only looks at the top and bottom N lines of each page, since that's where
    headers/footers live. Compares normalized (markdown-stripped) versions so
    that **CHAPTER 1.** and CHAPTER 1. are treated as the same line.
    """
    from collections import Counter

    n_pages = len(pages)
    if n_pages == 0:
        return set()

    min_occurrences = max(3, int(n_pages * threshold))

    # Map normalized form -> set of raw forms seen
    normalized_counts: Counter = Counter()
    normalized_to_raw: dict[str, set[str]] = {}

    for page_text in pages:
        lines = [l.strip() for l in page_text.split("\n") if l.strip()]
        if not lines:
            continue
        candidates = set(lines[:check_lines] + lines[-check_lines:])
        for line in candidates:
            norm = _strip_md_formatting(line)
            if norm:
                normalized_counts[norm] += 1
                normalized_to_raw.setdefault(norm, set()).add(line)

    # Collect all raw variants of frequently-appearing lines
    running_lines = set()
    for norm, count in normalized_counts.items():
        if count >= min_occurrences:
            running_lines.update(normalized_to_raw[norm])

    return running_lines


def _is_page_number(line: str) -> bool:
    """Return True if line is just a page number (digits only, optionally with dashes)."""
    return bool(re.match(r"^\s*-?\s*\d+\s*-?\s*$", line.strip()))


def _is_chapter_header(line: str) -> bool:
    """Return True if line is a chapter/section heading artifact."""
    normalized = _strip_md_formatting(line).strip()
    # Match "CHAPTER 1", "CHAPTER 1.", "CHAPTER 1. THE FULL TITLE", etc.
    return bool(re.match(
        r"^(chapter|section|part|appendix|prologue|epilogue|introduction|preface)\s+[\d\w]+",
        normalized,
        re.IGNORECASE,
    ))


def strip_running_lines(page_text: str, running_lines: set[str]) -> str:
    """Remove detected header/footer lines, page numbers, and chapter headers from a page."""
    lines = page_text.split("\n")
    cleaned = []
    for l in lines:
        if l.strip() in running_lines:
            continue
        if _is_page_number(l):
            continue
        if _is_chapter_header(l):
            continue
        cleaned.append(l)
    # Collapse runs of blank lines left behind by removed headers
    text = "\n".join(cleaned)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# Sentence-ending punctuation — if a page ends with one of these, it's a real
# paragraph boundary. If not, the sentence continues on the next page.
_TERMINAL = re.compile(r'[.?!:)\]"\'»–—]\s*$')


def join_pages(pages: list[str]) -> str:
    """
    Join cleaned PDF pages into a single text, repairing mid-sentence page breaks.
    If a page ends without terminal punctuation the next page is appended with
    a space (not a blank line) so the sentence stays intact.
    """
    result = ""
    for page in pages:
        page = page.strip()
        if not page:
            continue
        if not result:
            result = page
            continue

        # Last non-empty line of accumulated text
        last_line = next((l.strip() for l in reversed(result.split("\n")) if l.strip()), "")

        if last_line and not _TERMINAL.search(last_line):
            # Mid-sentence — join with a space, no paragraph break
            result = result.rstrip() + " " + page.lstrip()
        else:
            result = result.rstrip() + "\n\n" + page.lstrip()

    return re.sub(r"\n{3,}", "\n\n", result)


def convert_pdf_to_markdown(pdf_path: Path) -> tuple[str, str]:
    import pymupdf4llm
    title = extract_pdf_title(pdf_path)
    logger.debug(f"Converting PDF: {pdf_path.name} (title: {title})")

    page_chunks = pymupdf4llm.to_markdown(str(pdf_path), page_chunks=True)
    page_texts = [p["text"] for p in page_chunks]

    running_lines = detect_running_lines(page_texts)
    if running_lines:
        logger.debug(f"Removing {len(running_lines)} running header/footer lines from {pdf_path.name}")

    cleaned_pages = [strip_running_lines(p, running_lines) for p in page_texts]
    md_text = join_pages(cleaned_pages)

    return title, md_text


def strip_markdown_formatting(body: str) -> str:
    """Strip all markdown formatting from body text, leaving plain paragraphs."""
    lines = body.split("\n")
    cleaned = []
    for line in lines:
        # Drop header lines entirely
        if re.match(r"^#{1,6}\s", line.strip()):
            continue
        # Drop horizontal rules
        if re.match(r"^[-*_]{3,}\s*$", line.strip()):
            continue
        # Drop blockquote markers
        line = re.sub(r"^>\s?", "", line)
        # Strip inline bold/italic: **text**, *text*, __text__, _text_
        line = re.sub(r"\*{1,2}(.+?)\*{1,2}", r"\1", line)
        line = re.sub(r"_{1,2}(.+?)_{1,2}", r"\1", line)
        # Strip backtick code spans
        line = re.sub(r"`(.+?)`", r"\1", line)
        cleaned.append(line)
    return "\n".join(cleaned)


_EPUB_METADATA_LINES = re.compile(
    r"^(archive|code|short\s*title|audio|video|length|mins|chapter\s*#|chapter\s*title"
    r"|english\s*discourse|year\s*published|talks\s*given|darshan\s*diary"
    r"|discourse\s*series|\d+\s+chapters?)[\s:]*.*$",
    re.IGNORECASE,
)


def strip_epub_metadata(text: str) -> str:
    """Remove Osho EPUB chapter metadata fields that duplicate the YAML frontmatter."""
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        stripped = line.strip()
        if _EPUB_METADATA_LINES.match(stripped):
            continue
        if re.match(r"^[A-Z0-9]{4,12}$", stripped):
            continue
        if re.match(r"^(yes|no|\d+)$", stripped, re.IGNORECASE):
            continue
        if _is_chapter_header(stripped):
            continue
        cleaned.append(line)
    return "\n".join(cleaned)


def convert_epub_to_markdown(epub_path: Path) -> tuple[str, str]:
    import ebooklib
    from ebooklib import epub
    import html2text

    title = extract_epub_title(epub_path)
    logger.debug(f"Converting EPUB: {epub_path.name} (title: {title})")

    book = epub.read_epub(str(epub_path))

    h = html2text.HTML2Text()
    h.ignore_links = True
    h.ignore_images = True
    h.body_width = 0
    h.ignore_emphasis = False

    chapters = []
    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            try:
                html_content = item.get_content().decode("utf-8", errors="ignore")
                md_content = h.handle(html_content)
                chapters.append(md_content)
            except Exception as e:
                logger.debug(f"Could not process chapter in {epub_path}: {e}")

    return title, strip_epub_metadata("\n\n".join(chapters))


def write_markdown(output_path: Path, title: str, source_file: str, fmt: str, body: str) -> None:
    slug = slugify(title)
    frontmatter = {
        "title": title,
        "source_file": source_file,
        "format": fmt,
        "slug": slug,
    }
    body = strip_markdown_formatting(body)
    content = f"---\n{yaml.dump(frontmatter, default_flow_style=False)}---\n\n{body}"
    output_path.write_text(content, encoding="utf-8")


def collect_source_files() -> list[Path]:
    files = []
    if config.BOOKS_PDF_DIR.exists():
        files.extend(config.BOOKS_PDF_DIR.glob("*.pdf"))
    if config.BOOKS_EPUB_DIR.exists():
        files.extend(config.BOOKS_EPUB_DIR.glob("*.epub"))
    return sorted(files)


def convert_book(source_path: Path, force: bool = False) -> dict:
    result = {"source": source_path.name, "skipped": False, "error": None}
    fmt = source_path.suffix.lower()[1:]
    md_path = config.MARKDOWN_DIR / f"{slugify(source_path.stem)}.md"

    if md_path.exists() and not force:
        logger.info(f"Skipping (already converted): {source_path.name}")
        result["skipped"] = True
        return result

    try:
        logger.info(f"Converting: {source_path.name}")
        if fmt == "pdf":
            title, body = convert_pdf_to_markdown(source_path)
        elif fmt == "epub":
            title, body = convert_epub_to_markdown(source_path)
        else:
            raise ValueError(f"Unsupported format: {fmt}")

        config.MARKDOWN_DIR.mkdir(parents=True, exist_ok=True)
        write_markdown(md_path, title, source_path.name, fmt, body)
        logger.info(f"Written: {md_path.name}")

    except Exception as e:
        logger.error(f"Error converting {source_path.name}: {e}")
        result["error"] = str(e)

    return result


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Convert books to Markdown")
    parser.add_argument("--file", type=Path, help="Convert a single file instead of all books")
    parser.add_argument("--force", action="store_true", help="Re-convert even if .md already exists")
    parser.add_argument("--pdf-only", action="store_true", help="Convert PDFs only")
    parser.add_argument("--epub-only", action="store_true", help="Convert EPUBs only")
    args = parser.parse_args()

    if args.file:
        if not args.file.exists():
            logger.error(f"File not found: {args.file}")
            return
        source_files = [args.file]
    else:
        all_files = collect_source_files()
        if args.pdf_only:
            source_files = [f for f in all_files if f.suffix.lower() == ".pdf"]
        elif args.epub_only:
            source_files = [f for f in all_files if f.suffix.lower() == ".epub"]
        else:
            source_files = all_files

    if not source_files:
        logger.warning("No source files found in books/pdf/ or books/epub/")
        return

    logger.info(f"Found {len(source_files)} source files")

    converted = skipped = errors = 0

    with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
        future_to_file = {
            executor.submit(convert_book, f, args.force): f
            for f in source_files
        }
        for i, future in enumerate(as_completed(future_to_file), 1):
            file_path = future_to_file[future]
            try:
                result = future.result()
                if result["skipped"]:
                    skipped += 1
                elif result["error"]:
                    errors += 1
                else:
                    converted += 1
            except Exception as e:
                logger.error(f"Unhandled error for {file_path.name}: {e}")
                errors += 1

    logger.info("=" * 60)
    logger.info(f"Converted: {converted}  Skipped: {skipped}  Errors: {errors}")


if __name__ == "__main__":
    main()
