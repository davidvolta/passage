# Passage — Claude Dev Guide

## What This Is

A FastAPI web app for searching a book library and having AI conversations grounded in that content. Four pages: Home (word animation), Passages (search), Channel (AI chat), Favorites (saved passages).

---

## Key Files

| File | Purpose |
|------|---------|
| `app/main.py` | All routes + saved passages API |
| `app/channel.py` | Streaming AI chat, 3 modes, system prompts |
| `app/search.py` | Query embedding + Qdrant search |
| `config.py` | Single source of truth for all paths and env vars |
| `scripts/notion_ingest.py` | Fetches Notion page recursively → chunks → Qdrant |
| `scripts/update_notion_words.py` | Orchestrates ingest + word generation (cron entry point) |
| `scripts/words.py` | Clusters Qdrant embeddings → word list for animation |
| `scripts/ingest.py` | Indexes books from `processed/markdown/` into Qdrant |
| `scripts/convert.py` | Converts PDFs/EPUBs to markdown |

---

## Running Locally

```bash
uvicorn app.main:app --reload
```

Requires `OPENAI_API_KEY` and `QDRANT_URL` in `.env`. Qdrant must be running and reachable.

---

## Running Tests

```bash
pytest tests/ -v
```

`conftest.py` at the project root adds the root to `sys.path` so tests can import `config` and `scripts.*`.

---

## Persistent Storage

Railway mounts a volume at `/data`. Two files live there in production:

- `saved_passages.json` — user's saved passages
- `words_notion.json` — word animation data from Notion sync

`config.py` auto-detects: uses `/data` if it exists, otherwise falls back to the project root. **Never hardcode these paths** — always use `config.SAVED_PASSAGES_FILE` and `config.WORDS_NOTION_FILE`.

---

## Deployment

Push to `master` → Railway auto-deploys. Daily cron at midnight UTC runs `python scripts/update_notion_words.py` — configured in `railway.toml`.

---

## Conventions

- All config (paths, env vars, model names) goes in `config.py` — nowhere else
- Qdrant collections: `passages` (books), `notion_words` (Notion)
- Any file that must survive redeploys goes on the `/data` volume via `SAVED_PASSAGES_DIR`
- Tests import scripts as `from scripts.ingest import ...` (scripts/ is a package)
