#!/usr/bin/env python3
"""
find_dupes.py — Detect duplicate/fragment markdown files via content sampling.

Method: shingle fingerprinting.
- Extract overlapping 12-word shingles sampled every ~20 words from each file's body.
- Build an inverted index: shingle_hash -> list of files containing it.
- For each file pair sharing shingles, compute:
    overlap_ratio = shared_shingles / shingles_in_smaller_file
- If overlap_ratio > threshold, flag as duplicate or fragment.
"""

import hashlib
import re
import sys
from collections import defaultdict
from pathlib import Path

import yaml

MARKDOWN_DIR = Path("processed/markdown")
SHINGLE_SIZE = 12       # words per shingle
SAMPLE_STEP = 15        # take one shingle every N words (overlapping coverage)
DUPE_THRESHOLD = 0.80   # fraction of smaller file's shingles found in larger → duplicate
FRAGMENT_THRESHOLD = 0.55  # lower bar: smaller file is a fragment of larger


def parse_body(md_path: Path) -> tuple[dict, str]:
    text = md_path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    try:
        meta = yaml.safe_load(parts[1]) or {}
    except Exception:
        meta = {}
    return meta, parts[2].strip()


def normalize(text: str) -> list[str]:
    """Lowercase, strip punctuation, split into word tokens."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return text.split()


def shingle_hashes(words: list[str]) -> set[str]:
    hashes = set()
    # Dense shingles: step through the word list
    for i in range(0, max(1, len(words) - SHINGLE_SIZE + 1), SAMPLE_STEP):
        shingle = " ".join(words[i:i + SHINGLE_SIZE])
        if len(shingle.strip()) > 10:  # skip degenerate shingles
            hashes.add(hashlib.md5(shingle.encode()).hexdigest())
    return hashes


def main():
    files = sorted(MARKDOWN_DIR.glob("*.md"))
    print(f"Scanning {len(files)} files...\n", flush=True)

    records = []
    for f in files:
        meta, body = parse_body(f)
        words = normalize(body)
        shingles = shingle_hashes(words)
        records.append({
            "path": f,
            "name": f.name,
            "title": meta.get("title", f.stem),
            "source": meta.get("source_file", ""),
            "word_count": len(words),
            "shingles": shingles,
            "n_shingles": len(shingles),
        })

    # Build inverted index: shingle_hash -> list of record indices
    print("Building shingle index...", flush=True)
    inverted: dict[str, list[int]] = defaultdict(list)
    for idx, rec in enumerate(records):
        for h in rec["shingles"]:
            inverted[h].append(idx)

    # Count shared shingles for each pair
    print("Computing pairwise overlaps...", flush=True)
    pair_shared: dict[tuple[int,int], int] = defaultdict(int)
    for h, idxs in inverted.items():
        if len(idxs) < 2:
            continue
        for i in range(len(idxs)):
            for j in range(i + 1, len(idxs)):
                pair_shared[(idxs[i], idxs[j])] += 1

    # Evaluate pairs
    duplicates = []    # (smaller_idx, larger_idx, ratio, label)
    fragments = []

    for (i, j), shared in pair_shared.items():
        ri, rj = records[i], records[j]
        smaller, larger = (ri, rj) if ri["n_shingles"] <= rj["n_shingles"] else (rj, ri)

        if smaller["n_shingles"] == 0:
            continue

        ratio = shared / smaller["n_shingles"]

        if ratio >= DUPE_THRESHOLD:
            duplicates.append((smaller, larger, ratio))
        elif ratio >= FRAGMENT_THRESHOLD:
            fragments.append((smaller, larger, ratio))

    # Sort by ratio desc
    duplicates.sort(key=lambda x: -x[2])
    fragments.sort(key=lambda x: -x[2])

    print("\n" + "=" * 72)
    print("NEAR-EXACT DUPLICATES  (≥80% shingle overlap)")
    print("=" * 72)
    if duplicates:
        for small, large, ratio in duplicates:
            print(f"\n  KEEP   {large['name']}")
            print(f"         {large['word_count']:6d} words | title: {large['title'][:55]}")
            print(f"  REMOVE {small['name']}")
            print(f"         {small['word_count']:6d} words | title: {small['title'][:55]}")
            print(f"  Shingle overlap: {ratio:.1%}")
    else:
        print("  None found.")

    print("\n" + "=" * 72)
    print("LIKELY FRAGMENTS  (55–79% shingle overlap in smaller file)")
    print("=" * 72)
    if fragments:
        for small, large, ratio in fragments:
            print(f"\n  LARGE  {large['name']}")
            print(f"         {large['word_count']:6d} words | title: {large['title'][:55]}")
            print(f"  SMALL  {small['name']}")
            print(f"         {small['word_count']:6d} words | title: {small['title'][:55]}")
            print(f"  Shingle overlap: {ratio:.1%}")
    else:
        print("  None found.")

    # Deletion candidates = clear dupes + high-confidence fragments
    print("\n" + "=" * 72)
    print("DELETION CANDIDATES")
    print("=" * 72)

    candidates = []
    seen_small = set()

    for small, large, ratio in duplicates:
        if small["name"] not in seen_small:
            candidates.append((small, large, ratio, "near-exact duplicate"))
            seen_small.add(small["name"])

    for small, large, ratio in fragments:
        if small["name"] not in seen_small and ratio >= 0.65:
            candidates.append((small, large, ratio, "fragment"))
            seen_small.add(small["name"])

    if candidates:
        for small, large, ratio, label in sorted(candidates, key=lambda x: x["name"] if isinstance(x[0], str) else x[0]["name"]):
            print(f"\n  FILE:   {small['name']}")
            print(f"  REASON: {label} ({ratio:.1%} overlap) — content covered by {large['name']}")
    else:
        print("  No high-confidence candidates found.")

    return candidates


if __name__ == "__main__":
    main()
