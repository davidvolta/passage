"""
words.py — Cluster passage embeddings and extract representative words per cluster.
Writes results to words.json for the home screen animation.

Usage:
    python words.py [--clusters 40] [--count 50] [--collection passages|notion_words]
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
    # Generic words that don't make interesting particles
    'based', 'right', 'method', 'approach', 'process', 'result', 'results',
    'value', 'values', 'aspect', 'system', 'level', 'using', 'used', 'also',
    'within', 'without', 'through', 'often', 'every', 'other', 'would',
    'could', 'should', 'might', 'still', 'even', 'first', 'after', 'before',
    'always', 'never', 'again', 'though', 'while', 'where', 'which', 'much',
    'many', 'more', 'most', 'good', 'great', 'large', 'small', 'number',
    'state', 'states', 'sense', 'seems', 'seem', 'start', 'starts', 'started',
    'certain', 'allows', 'allow', 'create', 'creates', 'created', 'order',
    'helps', 'help', 'helps', 'each', 'both', 'between', 'among',
    'doesn', 'points', 'isn', 'wasn', 'didn', 'aren', 'couldn', 'hasn',
}


def fetch_all_points(client: QdrantClient, collection_name: str):
    texts, vectors = [], []
    offset = None
    while True:
        result = client.scroll(
            collection_name=collection_name,
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


def top_words_for_cluster(cluster_texts: list[str], n: int = 5) -> list[str]:
    if not cluster_texts:
        return []
    min_df = 1 if len(cluster_texts) < 5 else 2
    vec = TfidfVectorizer(
        stop_words='english',
        min_df=min_df,
        max_df=0.85,
        token_pattern=r'\b[a-z]{5,}\b',
    )
    try:
        tfidf = vec.fit_transform(cluster_texts)
    except ValueError:
        return []
    scores = tfidf.sum(axis=0).A1
    vocab = vec.get_feature_names_out()
    results = []
    for word, _ in sorted(zip(vocab, scores), key=lambda x: -x[1]):
        if word not in EXTRA_STOPWORDS:
            results.append(word)
            if len(results) >= n:
                break
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--clusters', type=int, default=40)
    parser.add_argument('--count', type=int, default=50, help='Target number of output words')
    parser.add_argument('--collection', type=str, default='passages',
                       help='Qdrant collection to use (passages or notion_words)')
    args = parser.parse_args()

    collection_name = args.collection
    if collection_name == config.NOTION_COLLECTION:
        out_filename = 'words_notion.json'
    else:
        out_filename = 'words.json'

    print(f"Connecting to Qdrant...")
    print(f"Using collection: {collection_name}")
    client = QdrantClient(url=config.QDRANT_URL)

    print("Fetching passages...")
    texts, vectors = fetch_all_points(client, collection_name)
    client.close()
    print(f"  {len(texts)} passages")

    n_clusters = min(args.clusters, len(texts) // 2)
    if n_clusters < 2:
        print(f"Too few passages ({len(texts)}) to cluster", file=sys.stderr)
        sys.exit(1)

    print(f"Clustering into {n_clusters} groups...")
    km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10, max_iter=300)
    labels = km.fit_predict(vectors)
    sizes = Counter(labels)
    print(f"  Cluster sizes — min: {min(sizes.values())}, max: {max(sizes.values())}, mean: {np.mean(list(sizes.values())):.0f}")

    print("Extracting representative words...")
    seen = set()
    words = []
    for cluster_id in range(n_clusters):
        cluster_texts = [texts[i] for i, l in enumerate(labels) if l == cluster_id]
        for word in top_words_for_cluster(cluster_texts, n=5):
            if word not in seen:
                seen.add(word)
                words.append(word)

    words = sorted(words[:args.count])
    print(f"\n  {len(words)} words found:")
    print(' ', ', '.join(words))

    out = config.ROOT / out_filename
    out.write_text(json.dumps(words, indent=2))
    print(f"\nWritten to {out}")


if __name__ == '__main__':
    main()
