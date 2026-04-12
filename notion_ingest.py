# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
notion_ingest.py — Fetch Notion page, chunk, embed into Qdrant.

Usage:
    export NOTION_TOKEN=ntn_...
    export NOTION_PAGE_ID=xxx
    python notion_ingest.py
"""

import logging
import os
import re
import uuid
from pathlib import Path
from typing import List, Dict

import httpx
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def fetch_notion_blocks(page_id: str, token: str) -> list:
    """Recursively fetch all blocks from a Notion page."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
    }

    blocks = []
    url = f"https://api.notion.com/v1/blocks/{page_id}/children"

    while url:
        resp = httpx.get(url, headers=headers)
        resp.raise_for_status()
        data = resp.json()

        for block in data.get("results", []):
            blocks.append(block)
            # Recursively fetch children for blocks that have them
            if block.get("has_children"):
                child_url = f"https://api.notion.com/v1/blocks/{block['id']}/children"
                child_resp = httpx.get(child_url, headers=headers)
                if child_resp.status_code == 200:
                    blocks.extend(child_resp.json().get("results", []))

        url = data.get("next_cursor")
        if url:
            url = f"https://api.notion.com/v1/blocks/{page_id}/children?start_cursor={url}"

    return blocks


def blocks_to_text(blocks: list) -> str:
    """Convert Notion blocks to plain text."""
    texts = []

    for block in blocks:
        block_type = block.get("type", "")

        if block_type in ["paragraph", "heading_1", "heading_2", "heading_3",
                         "bulleted_list_item", "numbered_list_item", "quote"]:
            rich_text = block.get(block_type, {}).get("rich_text", [])
            text = "".join(rt.get("plain_text", "") for rt in rich_text)
            if text.strip():
                texts.append(text)

        elif block_type == "to_do":
            rich_text = block.get("to_do", {}).get("rich_text", [])
            text = "".join(rt.get("plain_text", "") for rt in rich_text)
            if text.strip():
                texts.append(text)

    return "\n\n".join(texts)


def chunk_text(text: str, target_words: int = 200, max_words: int = 300) -> List[dict]:
    """Split text into chunks."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    chunks = []
    current_paras = []
    current_word_count = 0
    chunk_idx = 0

    def flush():
        nonlocal chunk_idx, current_paras, current_word_count
        if not current_paras:
            return
        chunk_text = "\n\n".join(current_paras)
        chunks.append({
            "chunk_id": f"notion_{chunk_idx:04d}",
            "book_title": "Notion Document",
            "source_file": "notion",
            "source_type": "notion",
            "chapter": "",
            "text": chunk_text,
            "word_count": len(chunk_text.split()),
        })
        chunk_idx += 1
        current_paras = []
        current_word_count = 0

    for para in paragraphs:
        para_word_count = len(para.split())

        if current_word_count + para_word_count > max_words:
            flush()

        if para_word_count > max_words:
            # Split long paragraph
            words = para.split()
            for i in range(0, len(words), target_words):
                chunk_words = words[i:i + max_words]
                chunks.append({
                    "chunk_id": f"notion_{chunk_idx:04d}",
                    "book_title": "Notion Document",
                    "source_file": "notion",
                    "source_type": "notion",
                    "chapter": "",
                    "text": " ".join(chunk_words),
                    "word_count": len(chunk_words),
                })
                chunk_idx += 1
        else:
            current_paras.append(para)
            current_word_count += para_word_count

            if current_word_count >= target_words:
                flush()

    flush()
    return chunks


def embed_and_upsert(chunks: List[dict], collection_name: str) -> None:
    """Embed chunks and upsert to Qdrant."""
    client = QdrantClient(url=config.QDRANT_URL)

    # Ensure collection exists
    try:
        client.get_collection(collection_name)
    except Exception:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=config.EMBED_DIMENSIONS, distance=Distance.COSINE),
        )
        logger.info(f"Created collection: {collection_name}")

    # Clear existing data
    client.delete(collection_name=collection_name, points_selector={"must": []})
    logger.info(f"Cleared collection: {collection_name}")

    if not chunks:
        logger.warning("No chunks to embed")
        return

    # Embed
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    batch_size = 32
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        resp = openai_client.embeddings.create(
            model=config.OPENAI_EMBED_MODEL,
            input=[c["text"] for c in batch],
        )
        embeddings = [item.embedding for item in resp.data]

        points = []
        for chunk, embedding in zip(batch, embeddings):
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk["chunk_id"]))
            points.append(PointStruct(
                id=point_id,
                vector=embedding,
                payload=chunk,
            ))

        client.upsert(collection_name=collection_name, points=points)
        logger.info(f"Upserted {len(points)} chunks")

    client.close()
    logger.info(f"Total chunks: {len(chunks)}")


def main():
    token = config.NOTION_TOKEN
    page_id = config.NOTION_PAGE_ID

    if not token:
        logger.error("NOTION_TOKEN not set")
        return
    if not page_id:
        logger.error("NOTION_PAGE_ID not set")
        return

    logger.info(f"Fetching Notion page: {page_id}")
    blocks = fetch_notion_blocks(page_id, token)
    logger.info(f"Fetched {len(blocks)} blocks")

    text = blocks_to_text(blocks)
    logger.info(f"Extracted {len(text)} characters")

    chunks = chunk_text(text, config.TARGET_CHUNK_WORDS, config.MAX_CHUNK_WORDS)
    logger.info(f"Created {len(chunks)} chunks")

    embed_and_upsert(chunks, config.NOTION_COLLECTION)
    logger.info("Done!")


if __name__ == "__main__":
    main()
