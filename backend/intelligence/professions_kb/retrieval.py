"""Retrieval over the professions encyclopedia KB (professions.json).

Curated, verified, ML-indexed knowledge — NOT a trained model.
Index: TF-IDF + cosine over name/category/description/entry_paths/pros/cons/
demand_outlook/fit_notes. See ../retrieval_core.py for why TF-IDF.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from retrieval_core import KBIndex

_HERE = os.path.dirname(os.path.abspath(__file__))
_INDEX_PATH = os.path.join(_HERE, "index.joblib")


def entry_text(e):
    parts = [
        e.get("name", ""),
        e.get("category", ""),
        e.get("description", ""),
        " ".join(e.get("entry_paths", [])),
        " ".join(e.get("pros", [])),
        " ".join(e.get("cons", [])),
        e.get("demand_outlook", ""),
        e.get("fit_notes", ""),
    ]
    return " ".join(parts)


def load_entries():
    with open(os.path.join(_HERE, "professions.json"), encoding="utf-8") as f:
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
    for q in sys.argv[1:] or ["pros and cons of becoming a CA vs lawyer"]:
        print("\nQ:", q)
        for r in retrieve(q, k=3):
            print(f"  {r['score']:.3f} {r['entry']['id']} | {r['entry']['name']}")
