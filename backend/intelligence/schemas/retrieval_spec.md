# Retrieval layer spec (v1) — ML-indexed knowledge, NOT "trained models"

## Language honesty (non-negotiable)
The two KBs are **curated, verified, ML-indexed knowledge**. Never describe them as
"trained models" in docs, code, comments, or reports. The ML part is the retrieval
index over human-verified entries — quality over quantity; every URL fetched.

## Scope note
AJ asked for "every single data on the internet". That is NOT the target.
The target stays: comprehensive VERIFIED coverage (300-500 resources, 150-200
professions), every URL fetched, every salary an estimate, every entry honest.

## Layout
- `resources_kb/retrieval.py` — index + `retrieve(query, k)` over resources.json
- `professions_kb/retrieval.py` — index + `retrieve(query, k)` over professions.json
- `retrieval_eval.md` (at `intelligence/`) — method, test queries summary, honest metrics

## Index approach (decide at build time, document WHY in the eval report)
- Preferred: `sentence-transformers` `all-MiniLM-L6-v2` (~80MB; CPU-feasible —
  encodes a few hundred short docs in minutes, ms-level query encoding). Cosine similarity.
- Fallback: TF-IDF + cosine (sklearn) or BM25, if torch/sentence-transformers install
  is infeasible on this VM. Report which was used and why.
- Indexed text per entry:
  - resources: name + subject + level + stream + type + language + notes
  - professions: name + category + description + entry_paths + pros + cons + fit_notes
- Persist the index artifacts (embeddings .npy / vectorizer joblib) next to the code
  so the counselor can load without rebuilding.

## API
```python
retrieve(query: str, k: int = 5) -> list[{"entry": dict, "score": float}]
```
- `entry` is the full KB entry dict; `score` is cosine similarity (or TF-IDF cosine).
- Deterministic: same query + same index = same ranking.

## Evaluation
- `test_queries.jsonl` per KB: ~50 realistic queries, each
  `{"query": ..., "relevant_ids": [...]}` — e.g.
  - resources: "best free YouTube channel for class 12 physics in Hindi",
    "NPTEL course for data structures", "free spoken english course"
  - professions: "pros and cons of becoming a CA vs lawyer",
    "jobs with no degree that pay well", "is tea shop a good business"
- Relevance judgments written by the builder against the merged KB (ids known relevant).
- Metrics: precision@k and recall@k for k in {1, 3, 5}. Report honest numbers;
  note failure modes (e.g. Hinglish queries vs English-trained embeddings).
