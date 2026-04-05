"""Unit tests for ingest.py"""

import uuid
from unittest.mock import MagicMock, patch

import pytest

import config
from ingest import (
    build_chunks,
    chunk_to_point,
    count_words,
    filename_to_title,
    parse_frontmatter,
    slugify,
    split_paragraphs,
    write_markdown,
)


# ── slugify ───────────────────────────────────────────────────────────────────

def test_slugify_basic():
    assert slugify("Hello World") == "hello-world"

def test_slugify_punctuation():
    assert slugify("It's a Test!") == "its-a-test"

def test_slugify_multiple_spaces():
    assert slugify("too  many   spaces") == "too-many-spaces"

def test_slugify_leading_trailing_hyphens():
    assert slugify("  --hello--  ") == "hello"


# ── filename_to_title ─────────────────────────────────────────────────────────

def test_filename_to_title_underscores():
    assert filename_to_title("the_great_gatsby") == "The Great Gatsby"

def test_filename_to_title_hyphens():
    assert filename_to_title("moby-dick") == "Moby Dick"


# ── count_words ───────────────────────────────────────────────────────────────

def test_count_words():
    assert count_words("one two three") == 3

def test_count_words_empty():
    assert count_words("") == 0


# ── split_paragraphs ──────────────────────────────────────────────────────────

def test_split_paragraphs_filters_short():
    body = "Hi.\n\nThis is a real paragraph with enough words to pass the filter."
    result = split_paragraphs(body)
    assert len(result) == 1
    assert "real paragraph" in result[0]

def test_split_paragraphs_filters_all_caps():
    body = "RUNNING HEADER\n\nThis is a real paragraph with enough words in it."
    result = split_paragraphs(body)
    assert len(result) == 1
    assert "real paragraph" in result[0]

def test_split_paragraphs_empty_body():
    assert split_paragraphs("") == []


# ── parse_frontmatter ─────────────────────────────────────────────────────────

def test_parse_frontmatter_valid():
    content = "---\ntitle: Test Book\nslug: test-book\n---\n\nBody text here."
    metadata, body = parse_frontmatter(content)
    assert metadata["title"] == "Test Book"
    assert body == "Body text here."

def test_parse_frontmatter_no_frontmatter():
    with pytest.raises(ValueError, match="No frontmatter"):
        parse_frontmatter("Just plain text.")

def test_parse_frontmatter_malformed():
    with pytest.raises(ValueError, match="Invalid frontmatter"):
        parse_frontmatter("---\nonly one separator")


# ── build_chunks ──────────────────────────────────────────────────────────────

def _make_paragraph(word_count: int) -> str:
    return " ".join(["word"] * word_count)

def test_build_chunks_single_chunk():
    paragraphs = [_make_paragraph(50), _make_paragraph(50)]
    metadata = {"title": "Test", "source_file": "test.pdf"}
    chunks = build_chunks(paragraphs, "test", metadata)
    assert len(chunks) == 1
    assert chunks[0]["chunk_id"] == "test_0000"
    assert chunks[0]["word_count"] == 100

def test_build_chunks_splits_at_target():
    # Greedy accumulator: flushes AFTER adding a paragraph that hits target.
    # [150] → below target, [150+100=250] → hits target (>=200), flush as one chunk.
    paragraphs = [_make_paragraph(150), _make_paragraph(100)]
    metadata = {"title": "Test", "source_file": "test.pdf"}
    chunks = build_chunks(paragraphs, "test", metadata)
    assert len(chunks) == 1
    assert chunks[0]["word_count"] == 250

def test_build_chunks_flushes_at_max():
    # Single oversized paragraph forces flush of current before adding
    paragraphs = [_make_paragraph(100), _make_paragraph(250)]
    metadata = {"title": "Test", "source_file": "test.pdf"}
    chunks = build_chunks(paragraphs, "test", metadata)
    # First para (100 words) gets flushed when second para would exceed MAX (300)
    assert len(chunks) == 2

def test_build_chunks_empty():
    assert build_chunks([], "test", {"title": "T", "source_file": "t.pdf"}) == []

def test_build_chunks_metadata_fields():
    paragraphs = [_make_paragraph(50)]
    metadata = {"title": "My Book", "source_file": "my_book.epub"}
    chunks = build_chunks(paragraphs, "my-book", metadata)
    assert chunks[0]["book_title"] == "My Book"
    assert chunks[0]["source_file"] == "my_book.epub"
    assert chunks[0]["source_type"] == "book"


# ── chunk_to_point ────────────────────────────────────────────────────────────

def test_chunk_to_point_deterministic_id():
    chunk = {
        "chunk_id": "test_0000",
        "book_title": "Test",
        "source_file": "test.pdf",
        "source_type": "book",
        "chapter": "",
        "text": "Some text.",
        "word_count": 2,
    }
    embedding = [0.1] * config.EMBED_DIMENSIONS
    point1 = chunk_to_point(chunk, embedding)
    point2 = chunk_to_point(chunk, embedding)
    assert point1.id == point2.id

def test_chunk_to_point_payload():
    chunk = {
        "chunk_id": "test_0001",
        "book_title": "Test Book",
        "source_file": "test.pdf",
        "source_type": "book",
        "chapter": "",
        "text": "Hello world.",
        "word_count": 2,
    }
    embedding = [0.0] * config.EMBED_DIMENSIONS
    point = chunk_to_point(chunk, embedding)
    assert point.payload["book_title"] == "Test Book"
    assert point.payload["chunk_id"] == "test_0001"
    assert point.vector == embedding


# ── write_markdown ────────────────────────────────────────────────────────────

def test_write_markdown_roundtrip(tmp_path):
    out = tmp_path / "test.md"
    write_markdown(out, "My Title", "my_title.pdf", "pdf", "Body content here.")
    content = out.read_text()
    metadata, body = parse_frontmatter(content)
    assert metadata["title"] == "My Title"
    assert metadata["format"] == "pdf"
    assert body == "Body content here."
