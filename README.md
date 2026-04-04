# Four Polarities — Osho Knowledge Base
### Project Plan & Architecture

---

## What This Is

A local tool for searching and retrieving passages from 100+ Osho books.  
Built for two people writing a book. The tool ingests a large library, processes it into a searchable format, and surfaces relevant passages through a simple UI.

No cloud. No external services. Runs entirely on your Mac.

---

## The End State

A local web UI where you type a topic or question, and get back real passages from Osho's books — with the source book and chapter clearly labeled. You browse, read, and take what's useful for your writing.

---

## Project Structure

```
four_polarities/
│
├── books/                      # Raw source files (PDFs + EPUBs) — untouched
│
├── processed/
│   ├── markdown/               # One .md file per book after conversion
│   └── chunks/                 # Chunked JSON files ready for embedding
│
├── db/                         # ChromaDB vector store (auto-generated, don't edit)
│
├── pipeline/                   # All processing scripts
│   ├── convert.py              # PDF/EPUB → Markdown
│   ├── chunk.py                # Markdown → structured JSON chunks
│   ├── embed.py                # Chunks → ChromaDB vectors
│   └── run_all.py              # Coordinator: runs all three in parallel
│
├── app/                        # The UI
│   ├── main.py                 # Streamlit app entry point
│   └── search.py               # Query logic against ChromaDB
│
├── config.py                   # Paths, model names, chunk sizes — all config in one place
├── requirements.txt
└── README.md                   # This file
```

---

## Tech Stack

| Layer | Tool | Why |
|---|---|---|
| PDF conversion | `pymupdf4llm` | Best quality text extraction from PDFs, LLM-optimized output |
| EPUB conversion | `ebooklib` + `html2text` | Clean EPUB-to-text, handles Osho's talk format well |
| Intermediate format | Markdown (`.md`) | Human-readable, fast to process, easy to inspect and debug |
| Chunking | Custom Python | Paragraph-aware splitting — respects Osho's natural talk rhythm |
| Embeddings | `nomic-embed-text` via Ollama | Runs fully local, free, strong semantic quality |
| Vector store | `ChromaDB` | Local, no server needed, Python-native, persistent |
| UI | `Streamlit` | Simple, fast to build, runs in browser, no frontend code needed |
| Parallel processing | `concurrent.futures` | Built into Python, no heavy dependencies |
| Environment | Python 3.11+ | Standard |

**Everything runs locally. No API keys. No subscriptions. No data leaves your machine.**

---

## Phases

### Phase 0 — Setup
- Install dependencies: Python, Ollama, ChromaDB, Streamlit, pymupdf4llm, ebooklib
- Pull the `nomic-embed-text` model via Ollama
- Confirm folder structure exists
- Write `config.py` with all paths

### Phase 1 — Conversion (PDF + EPUB → Markdown)
- Script: `pipeline/convert.py`
- Reads every file in `books/`
- Detects format (PDF vs EPUB) and routes accordingly
- Outputs one clean `.md` file per book into `processed/markdown/`
- Adds YAML frontmatter: `title`, `source_file`, `format`
- Skips already-converted files (idempotent — safe to re-run)

### Phase 2 — Chunking (Markdown → JSON)
- Script: `pipeline/chunk.py`
- Reads each `.md` file
- Splits into paragraph-cluster chunks (~400 words each)
- Each chunk stored as JSON with: `chunk_id`, `book_title`, `text`, `word_count`
- Output goes to `processed/chunks/`

### Phase 3 — Embedding (JSON → ChromaDB)
- Script: `pipeline/embed.py`
- Reads all chunk JSON files
- Sends each chunk's text to `nomic-embed-text` via Ollama
- Stores vector + metadata in ChromaDB at `db/`
- Idempotent — checks if chunk already embedded before processing

### Phase 4 — Parallel Pipeline
- Script: `pipeline/run_all.py`
- Runs conversion, chunking, and embedding across all books in parallel
- Uses `concurrent.futures.ThreadPoolExecutor`
- Logs progress, errors, skipped files
- Estimated runtime: 1–3 hours for 100+ books (first run only)

### Phase 5 — UI
- Script: `app/main.py`
- Streamlit app
- Single search bar: type a topic, question, or phrase
- Returns top N passages, each showing: passage text + book title
- Adjustable result count
- Clean, readable layout — built for reading, not for showing off

---

## Key Design Decisions

**Why Markdown as intermediate format?**  
It's the most inspectable format at this scale. If something looks wrong in the search results, you can open the `.md` file and see exactly what the converter produced. Debugging 100 binary files is painful; debugging 100 text files is not.

**Why ChromaDB over alternatives?**  
Runs embedded in Python — no server process, no Docker, no setup. The database is just a folder. Works for personal scale (100+ books is well within its range). Can always migrate later.

**Why Ollama + nomic-embed-text over OpenAI embeddings?**  
This is personal research material. Keeping it fully local means no privacy concerns, no ongoing costs, and no dependency on external services. `nomic-embed-text` is competitive quality for this use case.

**Why Streamlit over a custom UI?**  
You're writing a book, not building a product. Streamlit gives you a working browser UI in ~50 lines of Python. The goal is the passages, not the interface.

---

## Open Decisions (Resolve When You Get There)

- [ ] **Chunk size**: 400 words is a starting point. May need tuning after seeing real results.
- [ ] **Result count**: How many passages per search? Start with 10, adjust.
- [ ] **Filtering**: Do you want to filter by book, or always search across all books?
- [ ] **Saving passages**: Do you want to mark/save passages inside the tool, or just read and copy manually?
- [ ] **UI design**: Functional first, then style if needed.

---

## How to Work on This in Claude Code

This project is designed to be built incrementally inside Claude Code. Suggested session pattern:

1. Start each session by referencing this README
2. Work one Phase at a time — don't move to the next until the current one produces clean output on a small sample (3–5 books)
3. Always test on a small batch before running the full parallel pipeline
4. Keep `config.py` as the single source of truth — never hardcode paths in scripts

---

## First Thing to Do

Open this project folder in Claude Code and say:  
**"Let's start Phase 0 — set up the environment and write config.py"**

---

*Last updated: April 2026*
