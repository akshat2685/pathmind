"""Shared TF-IDF retrieval core for PathMind intelligence KBs.

HONESTY NOTE: these KBs are curated, verified, ML-indexed knowledge — NOT
"trained models". The only ML here is a TF-IDF retrieval index built over
human-verified entries.

Why TF-IDF and not dense embeddings: this VM's Python is externally managed
(PEP 668) with no sentence-transformers installed; torch 2.14+cpu IS present
but standing up a venv + embedding stack for ~480 short documents was judged
not worth it. TF-IDF + cosine is deterministic, dependency-free (sklearn),
fast, and strong on the keyword-rich queries this KB serves (course names,
exam names, subjects, professions).
Documented limitation: weaker than dense embeddings on paraphrased or
Hinglish-mixed queries. See retrieval_eval.md.
"""

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def _normalize(text: str) -> str:
    return text.lower().replace("_", " ")


class KBIndex:
    """TF-IDF cosine retrieval over a list of KB entry dicts."""

    def __init__(self, entries, text_fn):
        self.entries = entries
        self.ids = [e["id"] for e in entries]
        self.vectorizer = TfidfVectorizer(
            stop_words="english", ngram_range=(1, 2), sublinear_tf=True
        )
        self.matrix = self.vectorizer.fit_transform(
            [_normalize(text_fn(e)) for e in entries]
        )

    def retrieve(self, query, k=5):
        """retrieve(query, k=5) -> [{"entry": dict, "score": float}].

        Deterministic: same query + same index = same ranking.
        """
        q = self.vectorizer.transform([_normalize(query)])
        scores = cosine_similarity(q, self.matrix).flatten()
        top = scores.argsort()[::-1][:k]
        return [
            {"entry": self.entries[i], "score": float(scores[i])} for i in top
        ]

    def save(self, path):
        joblib.dump(
            {"ids": self.ids, "vectorizer": self.vectorizer, "matrix": self.matrix},
            path,
        )

    @classmethod
    def load(cls, path, entries, text_fn):
        idx = cls.__new__(cls)
        blob = joblib.load(path)
        idx.entries = entries
        idx.ids = blob["ids"]
        idx.vectorizer = blob["vectorizer"]
        idx.matrix = blob["matrix"]
        assert idx.ids == [e["id"] for e in entries], "index/entries mismatch"
        return idx
