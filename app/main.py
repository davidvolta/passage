"""FastAPI app for searching and saving book passages."""

import json
from pathlib import Path

from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

import config
from app.search import search

app = FastAPI()
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
    config.SAVED_PASSAGES_FILE.write_text(json.dumps(saved, indent=2))


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html")


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
