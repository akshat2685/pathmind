"""Retrieval over the Indian learning-resources KB (resources.json).

Curated, verified, ML-indexed knowledge — NOT a trained model.
Index: TF-IDF + cosine over name/subject/level/stream/type/language/notes.
See ../retrieval_core.py for why TF-IDF.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from retrieval_core import KBIndex

_HERE = os.path.dirname(os.path.abspath(__file__))
_INDEX_PATH = os.path.join(_HERE, "index.joblib")


def entry_text(e):
    return " ".join(
        [
            e.get("name", ""),
            e.get("subject", ""),
            e.get("level", ""),
            e.get("stream", ""),
            e.get("type", ""),
            e.get("language", ""),
            e.get("notes", ""),
        ]
    )


def load_entries():
    with open(os.path.join(_HERE, "resources.json"), encoding="utf-8") as f:
        return json.load(f)


def build_index():
    return KBIndex(load_entries(), entry_text)


def load_index():
    return KBIndex.load(_INDEX_PATH, load_entries(), entry_text)


def retrieve(query, k=5):
    """retrieve(query, k=5) -> [{"entry": dict, "score": float}]"""
    if not os.path.exists(_INDEX_PATH):
        build_index().save(_INDEX_PATH)
    return load_index().retrieve(query, k=k)


if __name__ == "__main__":
    build_index().save(_INDEX_PATH)
    print("index built:", _INDEX_PATH)
    for q in sys.argv[1:] or ["best free YouTube channel for class 12 physics in Hindi"]:
        print("\nQ:", q)
        for r in retrieve(q, k=3):
            print(f"  {r['score']:.3f} {r['entry']['id']} | {r['entry']['name']}")
