# PathMind Intelligence Pack v1

**What this is:** three intelligence components for PathMind's counselor —
**one trained ML classifier + two curated knowledge bases with an ML retrieval
layer.** That phrasing is deliberate and non-negotiable:

> The KBs are **curated, verified, ML-indexed knowledge — NOT "trained models"**.
> Training a generative model on scraped web text would produce hallucinations
> (invented channel names, prices, salaries). Curation + verification + retrieval
> is the honest architecture for factual knowledge.

## Components

### 1. Readiness-to-change classifier (`classifier/`) — the actual ML model
- **Task:** classify a learner's onboarding text into a Transtheoretical Model stage:
  `precontemplation | contemplation | preparation | action | maintenance`.
- **Training:** synthetic labeled dataset (~3-5k examples, Indian student/switcher/
  business personas) → TF-IDF + LogReg/SVM baselines (+ DistilBERT only if
  CPU-feasible). Evaluated on a stratified held-out split: accuracy, per-class
  precision/recall/F1, confusion matrix — real numbers, no target-chasing.
- **Output contract:** `predict(text) -> {"stage", "confidence", "note"}`.
- ⚠️ **The output is a SCREENING HEURISTIC, not a psychological diagnosis.**
  Labeled as such in code, docs, and every output.
- **Honest results (template-held-out test, n=753, untuned):** LinearSVC
  accuracy **0.4927** / macro F1 0.4986 (shipped); LogReg 0.4343. A naive
  row-level split scored 1.0000 — pure template memorization, reported in
  `eval_report.md` only as a warning. Contemplation is the hardest stage
  (F1 0.22); errors are adjacent-stage confusions. DistilBERT skipped after
  genuine attempts (proxy/ABI pain on this VM; synthetic data is the real
  bottleneck, not capacity). Full detail: `classifier/eval_report.md`.

### 2. Indian learning-resources KB (`resources_kb/`)
- **309 verified entries** (304 fetch-verified via HTTP 200 + relevance check;
  5 search-confirmed-only — Codeforces, Microsoft Learn, Stack Overflow,
  r/learnprogramming, Khan Academy site — bot-blocked for text fetch, flagged
  `url_verified: false`).
- Fields: id, subject, level (class_6_8 / class_9_10 / class_11_12 / UG / PG / skill),
  stream, type (youtube_channel / free_course / paid_course / book / community),
  name, url, url_verified, language (English/Hindi/Hinglish/other), cost_inr, notes.
- Coverage: school 6-12 (CBSE-oriented, 87) · college incl. deep B.Tech CSE (146) ·
  exam prep JEE/NEET/UPSC/GATE + upskilling (76).
- `landscape_notes.md`: general knowledge on what Indian students use now
  (YouTube-first, NPTEL/SWAYAM under-discovered, etc.) — orientation, not statistics.
- **Prices** were live on 2026-10-15 and will drift — re-check at recommendation time.

### 3. Professions encyclopedia KB (`professions_kb/`)
- **171 entries** covering what Indian students actually choose between: tech (60),
  institutional — healthcare/law/finance/govt/education (56), trades/small
  business/creative/services/defence (55). Yes, tea shop owner is in there.
- Fields: id, name, category, description, entry_paths, pros[], cons[],
  salary_inr {entry, experienced, note: "estimate", confidence: researched|inferred},
  demand_outlook, fit_notes, typical_timeline, sources[].
- **Salaries are ranges marked "estimate", never precise facts.** 10 tech entries
  have `confidence: "inferred"` (grounded in adjacent roles, labeled in sources).
  Every entry has real, balanced cons — saturation, grind, pay ceilings included.

### Retrieval layer (both KBs)
- `resources_kb/retrieval.py` / `professions_kb/retrieval.py`:
  `retrieve(query, k=5) -> [{"entry", "score"}]`.
- Index: **TF-IDF + cosine** (sklearn). Dense embeddings were evaluated and
  deliberately not used: externally-managed Python (PEP 668), no GPU, and
  TF-IDF is deterministic, dependency-free, and strong on keyword-rich queries
  against curated metadata. Known weakness: paraphrased/Hinglish-mixed queries.
- Prebuilt indexes: `resources_kb/index.joblib`, `professions_kb/index.joblib`.
- Evaluation: ~50 realistic test queries per KB with builder-written relevance
  judgments → precision@k / recall@k. Honest numbers in `retrieval_eval.md`.

## How PathMind's counselor consumes this

1. **Onboarding:** run `classifier/inference.py::predict()` on the learner's
   free-text answers → readiness stage steers the conversation
   (precontemplation → motivational, not a roadmap dump; preparation/action →
   concrete planning).
2. **Recommendations:** call `retrieve(query, k)` on the relevant KB and cite
   returned entries as evidence — names, URLs, costs, salaries come from the
   entry, never from the LLM's memory.
3. **Career discussions:** professions KB entries supply balanced pros/cons and
   India-grounded entry paths; salary figures are always presented as estimates.

## File map
```
intelligence/
├── README.md                  ← this file
├── retrieval_core.py          ← shared TF-IDF index (why-TF-IDF documented here)
├── retrieval_eval.md          ← retrieval metrics + failure modes
├── schemas/                   ← resources_schema.md, professions_schema.md,
│                                 classifier_spec.md, retrieval_spec.md
├── classifier/                ← data.jsonl, generation_log.md, model files,
│                                 eval_report.md, inference.py
├── resources_kb/
│   ├── resources.json         ← 309 merged entries
│   ├── retrieval.py           ← retrieve(query, k)
│   ├── index.joblib           ← prebuilt TF-IDF index
│   ├── test_queries.jsonl     ← 52 eval queries + relevance judgments
│   ├── landscape_notes.md
│   └── parts/                 ← per-slice source files
└── professions_kb/
    ├── professions.json       ← 171 merged entries
    ├── retrieval.py           ← retrieve(query, k)
    ├── index.joblib           ← prebuilt TF-IDF index
    ├── test_queries.jsonl     ← 53 eval queries + relevance judgments
    └── parts/                 ← per-slice source files
```

## Verification checklist (maintainer)
- [x] All JSON parses; ids unique within and across parts
- [x] Professions: no empty pros/cons; all salaries note="estimate"
- [x] Resources: 304/309 fetch-verified; 5 flagged search-confirmed-only
- [x] `retrieve()` smoke-tested on both KBs
- [x] Retrieval P@k/R@k evaluated and reviewed in `retrieval_eval.md`
  (resources P@1 0.558 / R@5 0.716; professions P@1 0.755 / R@5 0.843 —
  honest lower-bound numbers, see the report for interpretation)
- [x] Classifier: model loads, predicts (5/5 on fresh texts, disclaimer in every
  response), eval report reviewed — honest 0.49 accuracy, memorization trap
  caught and documented
