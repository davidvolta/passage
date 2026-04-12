"""
words.py — Cluster passage embeddings and extract representative words per cluster.
Writes results to words.json for the home screen animation.

Usage:
    python words.py [--clusters 40]
"""

import argparse
import json
import sys
from collections import Counter

import numpy as np
from qdrant_client import QdrantClient
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer

import config

# Domain-specific words to suppress on top of sklearn's English stopwords
EXTRA_STOPWORDS = {
    'osho', 'said', 'says', 'just', 'know', 'think', 'yes', 'okay',
    'will', 'like', 'going', 'come', 'comes', 'came', 'gone', 'goes',
    'make', 'makes', 'made', 'want', 'wants', 'need', 'needs',
    'look', 'looks', 'looked', 'tell', 'told', 'says', 'feel', 'feels',
    'felt', 'give', 'given', 'take', 'taken', 'thing', 'things',
    'something', 'nothing', 'everything', 'anything', 'someone', 'anyone',
    'man', 'woman', 'people', 'person', 'human', 'world', 'life', 'time',
    'way', 'days', 'years', 'moment', 'place', 'point', 'part', 'side',
    'question', 'answer', 'word', 'words', 'mean', 'means', 'meaning',
    'understand', 'understanding', 'simply', 'really', 'actually',
    'example', 'different', 'trying', 'become', 'becomes', 'became',
}


def fetch_all_points(client: QdrantClient):
    texts, vectors = [], []
    offset = None
    while True:
        result = client.scroll(
            collection_name=config.QDRANT_COLLECTION,
            offset=offset,
            limit=500,
            with_payload=['text'],
            with_vectors=True,
        )
        for point in result[0]:
            texts.append(point.payload['text'])
            vectors.append(point.vector)
        offset = result[1]
        if offset is None:
            break
    return texts, np.array(vectors, dtype=np.float32)


def top_word_for_cluster(cluster_texts: list[str]) -> str | None:
    if len(cluster_texts) < 2:
        return None
    vec = TfidfVectorizer(
        stop_words='english',
        min_df=2,
        max_df=0.85,
        token_pattern=r'\b[a-z]{5,}\b',
    )
    try:
        tfidf = vec.fit_transform(cluster_texts)
    except ValueError:
        return None
    scores = tfidf.sum(axis=0).A1
    vocab = vec.get_feature_names_out()
    for word, _ in sorted(zip(vocab, scores), key=lambda x: -x[1]):
        if word not in EXTRA_STOPWORDS:
            return word
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--clusters', type=int, default=40)
    args = parser.parse_args()

    print("Connecting to Qdrant...")
    client = QdrantClient(path=str(config.DB_DIR))

    print("Fetching passages...")
    texts, vectors = fetch_all_points(client)
    client.close()
    print(f"  {len(texts)} passages")

    if len(texts) < args.clusters:
        print(f"Too few passages ({len(texts)}) for {args.clusters} clusters", file=sys.stderr)
        sys.exit(1)

    print(f"Clustering into {args.clusters} groups...")
    km = KMeans(n_clusters=args.clusters, random_state=42, n_init=10, max_iter=300)
    labels = km.fit_predict(vectors)
    sizes = Counter(labels)
    print(f"  Cluster sizes — min: {min(sizes.values())}, max: {max(sizes.values())}, mean: {np.mean(list(sizes.values())):.0f}")

    print("Extracting representative words...")
    words = []
    for cluster_id in range(args.clusters):
        cluster_texts = [texts[i] for i, l in enumerate(labels) if l == cluster_id]
        word = top_word_for_cluster(cluster_texts)
        if word:
            words.append(word)

    words = sorted(set(words))
    print(f"\n  {len(words)} words found:")
    print(' ', ', '.join(words))

    out = config.ROOT / 'words.json'
    out.write_text(json.dumps(words, indent=2))
    print(f"\nWritten to {out}")


if __name__ == '__main__':
    main()
