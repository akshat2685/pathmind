# Classifier spec — readiness-to-change (v1)

## Task
Classify a learner's onboarding text (free-text answers + questionnaire-style responses)
into a Transtheoretical Model readiness stage.

## Labels (fixed, use exactly these strings)
- `precontemplation` — not considering change; defensive or unaware
- `contemplation` — aware, ambivalent, thinking about it within ~6 months
- `preparation` — intends to act soon, taking small steps
- `action` — actively changing behavior now
- `maintenance` — sustaining change, working to prevent relapse

## ⚠️ Standing disclaimer (must appear in code docstrings, inference output, and eval report)
> This classifier is a SCREENING HEURISTIC, not a psychological diagnosis.
> It must not be used to label a person's mental state or make clinical claims.

## Dataset
- Synthetic, ~3,000-5,000 labeled examples.
- Personas: Indian school students (classes 6-12), college students, career switchers,
  small-business aspirants. Varied phrasing; include ambiguous / borderline cases.
- Keep a generation log: templates used, counts per class, how ambiguity was introduced.
- Format: JSONL `data.jsonl` with fields `{"text": ..., "label": ...}`.

## Models
1. TF-IDF + LogisticRegression (baseline)
2. TF-IDF + LinearSVC (baseline)
3. DistilBERT fine-tune — ONLY if it trains in hours on CPU (no GPU on this VM).
   Timebox it: time one epoch, extrapolate; skip if projected > 6h or install is painful.
   If skipped, document why.

## Evaluation (honesty rules)
- Stratified train/test split; test set NEVER seen in training.
- Report: accuracy, per-class precision/recall/F1, confusion matrix.
- Do NOT tune hyperparameters to hit a target number. AJ asked for 97%+ — we report
  what the data honestly gives. If synthetic-data scores look suspiciously high,
  say explicitly that this likely reflects template memorization, not understanding.

## Deliverables (in `classifier/`)
- `data.jsonl` + `generation_log.md`
- `model_logreg.joblib`, `vectorizer.joblib` (and SVM equivalents)
- `eval_report.md` (metrics + confusion matrix + honest limitations)
- `inference.py` exposing `predict(text) -> {"stage": ..., "confidence": ..., "note": ...}`
  where `note` carries the screening-heuristic disclaimer.
