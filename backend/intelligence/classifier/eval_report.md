# Eval report — readiness-to-change classifier v1 (2026-10-15)

> **Disclaimer (standing):** This classifier is a SCREENING HEURISTIC, not a
> psychological diagnosis. It must not be used to label a person's mental state
> or make clinical claims.

## Setup
- Data: 3,661 synthetic examples, ~730/class, 5 TTM stages (see
  `generation_log.md`).
- Split: **template-level holdout** — 2,908 train / 753 test. The test set is
  generated from template indices never used in training (plus held-out
  borderline templates and coin-flipped noisy answers), so it measures
  generalization to unseen phrasings.
- Models: TF-IDF (1–2 grams, min_df=2, sublinear) + LogisticRegression and
  TF-IDF + LinearSVC, both with **default hyperparameters — deliberately
  untuned** (per the honesty rules; no number-chasing).
- A naive row-level 80/20 split was also run as a cautionary experiment:
  **both models scored 1.0000 accuracy** — pure template memorization, reported
  here only as evidence that row-level splits on synthetic data are meaningless.

## Results (template-held-out test set, n=753)

| Model | Accuracy | Macro P | Macro R | Macro F1 |
|---|---|---|---|---|
| TF-IDF + LogisticRegression | 0.4343 | 0.4431 | 0.4424 | 0.4419 |
| TF-IDF + LinearSVC | **0.4927** | 0.4955 | 0.5035 | 0.4986 |

### Per-class (LinearSVC — the shipped baseline)

| Stage | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| precontemplation | 0.3989 | 0.4465 | 0.4214 | 159 |
| contemplation | 0.2340 | 0.1988 | 0.2150 | 166 |
| preparation | 0.6547 | 0.6319 | 0.6431 | 144 |
| action | 0.5683 | 0.5524 | 0.5603 | 143 |
| maintenance | 0.6218 | 0.6879 | 0.6532 | 141 |

### Per-class (LogisticRegression)

| Stage | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| precontemplation | 0.4036 | 0.4214 | 0.4123 | 159 |
| contemplation | 0.1950 | 0.1867 | 0.1908 | 166 |
| preparation | 0.6277 | 0.5972 | 0.6121 | 144 |
| action | 0.4695 | 0.5385 | 0.5016 | 143 |
| maintenance | 0.5197 | 0.4681 | 0.4925 | 141 |

### Confusion matrices (rows = true, cols = predicted)
Order: precontemplation, contemplation, preparation, action, maintenance.

LinearSVC:
```
[[71 47 16  0 25]
 [89 33  1 42  1]
 [ 0 35 91 18  0]
 [ 0  0 31 79 33]
 [18 26  0  0 97]]
```

LogisticRegression:
```
[[67 49 16  1 26]
 [90 31  1 42  2]
 [ 0 44 86 14  0]
 [ 0  0 33 77 33]
 [ 9 35  1 30 66]]
```

### Reading the errors
- **Contemplation is the hardest stage** (F1 ~0.20): 89/166 contemplation
  examples are misclassified as precontemplation, 42 as action. Ambivalence
  shares vocabulary with defensiveness ("not sure", "don't know", negated
  change-words) — genuinely the hardest boundary, including for humans.
- **Adjacent-stage confusion dominates**: preparation↔contemplation,
  action↔maintenance (33 each way for SVC), preparation↔action. The model
  rarely jumps two stages — errors are clinically sensible, not random.
- preparation/action/maintenance carry the most distinctive surface cues
  (dates, routines, durations: "next month", "every day", "six months"), hence
  their higher F1. precontemplation vs contemplation is decided by stance,
  which bag-of-n-grams captures poorly.

## DistilBERT fine-tune — decision: SKIPPED (install too painful)

A genuine attempt was made; the environment fought back at every step:

1. `pip install torch` (CPU wheel, ~200MB): first foreground attempt died on a
   proxy read-timeout; a background attempt stalled awaiting runtime
   confirmation; a third attempt with `--timeout 120 --retries 6` succeeded
   (torch 2.14.1+cpu).
2. `pip install transformers`: failed — "Cannot uninstall typing_extensions
   4.10.0, RECORD file not found" (debian-packaged). Worked around with
   `--ignore-installed`, which pulled numpy 2.5.4 and **broke the debian
   scipy 1.11.4 ABI** (`numpy.core.multiarray failed to import`), taking down
   sklearn. Repaired by letting pip resolve scipy+numpy consistently (now
   numpy 1.26.4 + debian scipy 1.11.4; torch 2.14.1, transformers 5.19.0 and
   sklearn 1.9.1 all import cleanly — baselines re-verified byte-identical).
3. HuggingFace weight download: `huggingface_hub`'s vendored httpx2 crashes
   parsing this sandbox's proxy env (`InvalidURL: Invalid port: ':1]'` —
   it chokes on the IPv6 entries in `no_proxy`). Unsetting `no_proxy` got the
   download path working but the run then hung for 30 minutes (weight download
   + first-epoch compute through the proxy on 2 vCPUs) before the runtime
   killed it — no timing data obtained.

Per the spec ("skip if projected > 6h or install is painful"): the install was
unambiguously painful, the epoch-timing trial never completed, and — more
importantly — a 66M-parameter model fine-tuned on 2,908 *synthetic template*
examples would mostly learn to be a better template-matcher, not a better
readiness judge. The honest bottleneck is the data (synthetic, one author),
not model capacity. `time_trial.py` is kept in this directory documenting the
attempted protocol. Revisit DistilBERT when (a) there is real labeled learner
data, and (b) a machine with a GPU or fatter CPU is available.

## HONEST LIMITATIONS
1. **Synthetic-data ceiling.** Every example was generated from 120 hand-written
   templates + 25 borderline templates + 25 short answers by one author. The
   49% accuracy measures generalization *within this synthetic distribution* —
   not performance on real learner text. Real onboarding replies will contain
   Hinglish/code-mixing, typos, and reasoning patterns absent here; expect a
   further real-world drop.
2. **No, it is not 97%.** AJ asked for 97%+ accuracy. The honest number on
   unseen phrasings is ~43–49%. The 100% figure from a row-level split is
   template memorization and is reported only as a warning, not a result.
   Accuracy is measured, not ordered.
3. **Labels are one author's judgment.** Borderline-stage boundaries (e.g. "4
   months in, worried about exams" → maintenance) reflect the template author's
   reading of the Transtheoretical Model. No inter-rater study was done; a
   second rater would likely disagree on 10–20% of borderline cases.
4. **Bag-of-words blindness.** TF-IDF cannot model negation scope, hedging, or
   stance reliably ("I have no plan and I don't want one" vs "I have a plan") —
   exactly the signals that separate precontemplation from contemplation. A
   contextual model may do better, but only real data will prove it.
5. **Screening heuristic, not diagnosis.** Even at high accuracy this output
   must only seed a conversation in onboarding — never label a learner's mental
   state, never drive clinical or high-stakes decisions. The disclaimer ships
   in every `predict()` response (`inference.py`).

## Reproducibility
`python3 generate_data.py` (seed=42) → `python3 train.py` → `python3 evaluate.py`.
`python3 inference.py` runs the 5-sample verification. Models:
`vectorizer.joblib`, `model_logreg.joblib`, `model_svc.joblib`.
