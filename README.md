# Passage
### Search and retrieve passages from a large book library

---

## What This Is

A web app for searching passages across hundreds of books.
Type a topic or question — get back real passages with the source book labeled.
Built for two people writing a book together.

---

## What It Does

- Ingests PDFs and EPUBs into a searchable vector database
- Returns semantically relevant passages (~200 words each) ranked by relevance
- Save passages to a personal list, accessible across sessions
- Runs locally, deployable to the web when you need shared access

---

## File Structure

```
passage/
├── books/
│   ├── pdf/                    # source PDFs (gitignored)
│   └── epub/                   # source EPUBs (gitignored)
├── processed/
│   └── markdown/               # converted .md files — auto-generated, inspectable
├── db/                         # Qdrant vector store (auto-generated)
├── app/
│   ├── main.py                 # FastAPI app
│   ├── search.py               # query logic
│   └── templates/
│       └── index.html          # UI
├── config.py
├── ingest.py                   # run this to index your books
├── requirements.txt
└── README.md
```

---

## Tech Stack

| Layer | Tool |
|---|---|
| PDF extraction | `pymupdf4llm` |
| EPUB extraction | `ebooklib` + `html2text` |
| Embeddings | OpenAI `text-embedding-3-small` |
| Vector store | Qdrant (local) |
| API | FastAPI |

**Requires:** Python 3.11+, an OpenAI API key

---

## Setup

```bash
pip install -r requirements.txt
export OPENAI_API_KEY=your_key_here
```

Add your books to `books/pdf/` and `books/epub/`.

---

## Indexing Your Books

```bash
python ingest.py
```

This converts every book to Markdown, chunks it into ~200-word passages, embeds each chunk with OpenAI, and stores the vectors in Qdrant. Idempotent — safe to re-run, only processes new files.

First run on a large library takes a while and costs roughly $1 in OpenAI API usage. After that, searches are free.

---

## Running the App

```bash
uvicorn app.main:app --reload
```

Open `http://localhost:8000`.

---

## Deploying (When You Need Shared Access)

```bash
railway up
```

Or push to Render, Fly.io — any Python host works. Free tier is sufficient.

---

## Key Design Decisions

**Why Markdown as intermediate format?**
Every book becomes a human-readable `.md` file before chunking. If a passage looks wrong in search results, you can open the file and see exactly what the converter produced.

**Why Qdrant?**
Local mode is just a folder — no server, no Docker. When you need to scale or share the DB across projects, Qdrant runs as a server with no schema changes required.

**Why OpenAI embeddings over a local model?**
One-time cost (~$1 for a large library), no local GPU or model management, and `text-embedding-3-small` is genuinely better for semantic retrieval than local alternatives at this scale.

**Why 200-word chunks?**
Smaller chunks produce more precise semantic matches. Results feel targeted rather than overwhelming. You read what's returned rather than skimming a wall of text.

**Why FastAPI over Streamlit?**
This tool is part of a larger system. The same FastAPI backend will feed a future chat interface (Channel) without rebuilding the stack. Deploying for two users is a `railway up` away.

---

*Last updated: April 2026*
