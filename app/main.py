"""FastAPI app for searching and saving book passages."""

import json
import re
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

import config
from app.channel import router as channel_router
from app.search import _get_openai, _get_qdrant, search


@asynccontextmanager
async def lifespan(app: FastAPI):
    _get_openai()
    _get_qdrant()
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(channel_router)
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


class SavePassage(BaseModel):
    chunk_id: str
    book_title: str
    text: str


def _load_saved() -> list[dict]:
    if config.SAVED_PASSAGES_FILE.exists():
        return json.loads(config.SAVED_PASSAGES_FILE.read_text())
    return []


def _write_saved(saved: list[dict]) -> None:
    config.SAVED_PASSAGES_FILE.parent.mkdir(parents=True, exist_ok=True)
    config.SAVED_PASSAGES_FILE.write_text(json.dumps(saved, indent=2))


@app.get("/api/words")
async def api_words(source: str = Query(default="books", description="Word source: 'books' or 'notion'")):
    """Return words for the animation. source='books' or 'notion'."""
    if source == "notion":
        words_file = config.ROOT / "words_notion.json"
    else:
        words_file = config.ROOT / "words.json"

    if words_file.exists():
        return json.loads(words_file.read_text())
    return []


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html", {"active_tab": "home"})


@app.get("/channel", response_class=HTMLResponse)
async def channel_page(request: Request):
    return templates.TemplateResponse(request, "channel.html", {"active_tab": "channel"})


@app.get("/stories", response_class=HTMLResponse)
async def stories_page(request: Request):
    return templates.TemplateResponse(request, "stories.html", {"active_tab": "stories"})


@app.get("/favorites", response_class=HTMLResponse)
async def favorites_page(request: Request):
    return templates.TemplateResponse(request, "favorites.html", {"active_tab": "favorites"})


def _parse_stories() -> list[dict]:
    """Parse stories.md and return list of stories."""
    stories_file = config.ROOT / "stories.md"
    if not stories_file.exists():
        return []

    content = stories_file.read_text(encoding="utf-8")
    stories = []
    current_book = None

    # Split by headers
    lines = content.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]

        # Book header (## Book Title)
        if line.startswith("## "):
            current_book = line[3:].strip()
            i += 1
            continue

        # Story header (### N. (score: X.X))
        if line.startswith("### ") and "score:" in line:
            # Extract score
            score_match = re.search(r'score:\s*([\d.]+)', line)
            score = float(score_match.group(1)) if score_match else 0.0

            # Collect story text until next separator or header
            story_lines = []
            i += 1

            while i < len(lines):
                next_line = lines[i]

                # Stop at separator, next story, or indicators
                if next_line.startswith("---") or next_line.startswith("### ") or next_line.startswith("## "):
                    break
                if next_line.startswith("*Indicators:"):
                    i += 1
                    continue
                if next_line.strip() == "":
                    i += 1
                    continue

                story_lines.append(next_line)
                i += 1

            if story_lines and current_book:
                text = "\n".join(story_lines).strip()
                if len(text) > 50:
                    stories.append({
                        "book": current_book,
                        "text": text,
                        "score": score
                    })
            continue

        i += 1

    return stories


@app.get("/api/stories")
async def api_stories():
    return _parse_stories()


@app.get("/api/search")
async def api_search(q: str = Query(..., min_length=1), n: int = Query(default=10, ge=1, le=50)):
    return search(q, top_n=n)


@app.get("/api/saved")
async def api_saved():
    return _load_saved()


@app.post("/api/saved")
async def api_save(passage: SavePassage):
    saved = _load_saved()
    if any(s["chunk_id"] == passage.chunk_id for s in saved):
        return {"status": "already_saved"}
    saved.append(passage.model_dump())
    _write_saved(saved)
    return {"status": "saved"}


@app.delete("/api/saved/{chunk_id}")
async def api_unsave(chunk_id: str):
    saved = _load_saved()
    saved = [s for s in saved if s["chunk_id"] != chunk_id]
    _write_saved(saved)
    return {"status": "removed"}
