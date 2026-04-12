"""Channel — talk with Osho about the book."""

import json
from typing import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI
from pydantic import BaseModel

import config
from app.search import _get_qdrant, _get_openai

router = APIRouter()

SYSTEM_CASUAL = """You are Osho. Speak as Osho speaks — direct, alive, a little dangerous.
No performance. No spiritual preamble. No "indeed" or "certainly" or any assistant filler.
Short. Real. One thought at a time. You can ask something back. You can laugh.
You don't explain yourself.

Relevant passages from your teachings are below — let them inform you but don't lecture from them.
This is conversation, not discourse."""

SYSTEM_TEACHING = """You are Osho in full teaching mode. A question has come — a real one,
about the book being written on dynamic polarity, Tao and Tantra, relating, mind and body,
the dance of feminine and masculine.

Respond as Osho giving a discourse. Let it be complete — a real passage, crafted, with your
characteristic movement: into the question, through paradox and story, arriving somewhere
unexpected. This is the material. Write it as if it could go directly into the book.

Relevant passages from your teachings are provided as context. Let them inform your voice
without quoting them. Speak in first person as Osho."""

SYSTEM_STORY = """You are Osho. You have been given a concept and you will respond with a
single parable, koan, or tale — the kind you told in your talks. A story that carries the
concept without explaining it. The understanding arrives sideways, through the image, through
what happens, through the character who doesn't know they are teaching.

Study these examples from your own teachings carefully. Match their weight, their simplicity,
their movement. A story has an opening that drops you in, a middle that turns, and an ending
that opens rather than closes.

{examples}

Now write one new story for the concept given. Do not name the concept. Do not explain the
moral. Let the story be the teaching. One story only."""


class Message(BaseModel):
    role: str
    content: str


class ChannelRequest(BaseModel):
    message: str
    history: list[Message] = []
    mode: str = "casual"  # "casual" | "teaching" | "story"


def _embed_query(text: str) -> list[float]:
    resp = _get_openai().embeddings.create(
        model=config.OPENAI_EMBED_MODEL,
        input=text,
    )
    return resp.data[0].embedding


def _retrieve_context(query: str, top_n: int = 6) -> str:
    vector = _embed_query(query)
    results = _get_qdrant().query_points(
        collection_name=config.QDRANT_COLLECTION,
        query=vector,
        limit=top_n,
        with_payload=True,
    )
    passages = [p.payload["text"] for p in results.points]
    return "\n\n---\n\n".join(passages)


def _get_story_examples(n: int = 5) -> str:
    from app.main import _parse_stories
    stories = _parse_stories()
    # take top n by score
    top = sorted(stories, key=lambda s: s["score"], reverse=True)[:n]
    parts = []
    for s in top:
        parts.append(f'[Example from "{s["book"]}"]\n\n{s["text"]}')
    return "\n\n---\n\n".join(parts)


async def _stream_response(request: ChannelRequest) -> AsyncGenerator[str, None]:
    if request.mode == "teaching":
        context = _retrieve_context(request.message, top_n=8)
        system = SYSTEM_TEACHING + f"\n\n[Relevant passages from your teachings:]\n\n{context}"
        max_tokens = 1000
        temperature = 0.9
    elif request.mode == "story":
        examples = _get_story_examples(n=5)
        system = SYSTEM_STORY.format(examples=examples)
        max_tokens = 600
        temperature = 0.92
    else:
        context = _retrieve_context(request.message, top_n=4)
        system = SYSTEM_CASUAL + f"\n\n[Passages:]\n\n{context}"
        max_tokens = 180
        temperature = 0.9

    messages = [{"role": "system", "content": system}]
    for m in request.history:
        messages.append({"role": m.role, "content": m.content})
    messages.append({"role": "user", "content": request.message})

    client = AsyncOpenAI(api_key=_get_openai().api_key)
    stream = await client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        stream=True,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    async for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield f"data: {json.dumps(delta)}\n\n"

    yield "data: [DONE]\n\n"


@router.post("/api/channel")
async def channel(request: ChannelRequest):
    return StreamingResponse(
        _stream_response(request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
