import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()  # Load OPENAI_API_KEY from .env file

# ── Project Root ─────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.resolve()

# ── Input ────────────────────────────────────────────────────────────────────
BOOKS_PDF_DIR = ROOT / "books" / "pdf"
BOOKS_EPUB_DIR = ROOT / "books" / "epub"

# ── Processed ────────────────────────────────────────────────────────────────
MARKDOWN_DIR = ROOT / "processed" / "markdown"

# ── Database ─────────────────────────────────────────────────────────────────
DB_DIR = ROOT / "db"  # legacy local path (used for migration)
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_COLLECTION = "passages"

# ── Embeddings ───────────────────────────────────────────────────────────────
OPENAI_EMBED_MODEL = "text-embedding-3-small"
EMBED_DIMENSIONS = 1536

# ── Chunking ─────────────────────────────────────────────────────────────────
TARGET_CHUNK_WORDS = 200
MAX_CHUNK_WORDS = 300

# ── Search ───────────────────────────────────────────────────────────────────
DEFAULT_TOP_N = 10
MAX_TOP_N = 50

# ── Parallelism ──────────────────────────────────────────────────────────────
MAX_WORKERS = 1

# ── Saved Passages ───────────────────────────────────────────────────────────
# Use Railway volume if available (persisted across deploys), else local file
SAVED_PASSAGES_DIR = Path("/data") if Path("/data").exists() else ROOT
SAVED_PASSAGES_FILE = SAVED_PASSAGES_DIR / "saved_passages.json"

# ── Notion ───────────────────────────────────────────────────────────────────
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_PAGE_ID = os.getenv("NOTION_PAGE_ID")
NOTION_COLLECTION = "notion_words"
