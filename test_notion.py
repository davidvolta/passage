#!/usr/bin/env python3
"""Test fetching Notion page content."""
import httpx
import os

TOKEN = os.environ["NOTION_TOKEN"]
PAGE_ID = "3123e687-7214-805d-b552-eb1a5b61b55c"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Notion-Version": "2022-06-28",
}

# Fetch blocks
resp = httpx.get(f"https://api.notion.com/v1/blocks/{PAGE_ID}/children", headers=headers)
resp.raise_for_status()
data = resp.json()

print(f"Found {len(data['results'])} blocks\n")
print("First 5 blocks:")
for i, block in enumerate(data['results'][:5]):
    block_type = block.get('type', 'unknown')
    if block_type in ['paragraph', 'heading_1', 'heading_2', 'heading_3']:
        text = ''.join(rt.get('plain_text', '') for rt in block.get(block_type, {}).get('rich_text', []))
        print(f"  {i+1}. {block_type}: {text[:80]}...")
    else:
        print(f"  {i+1}. {block_type}")
