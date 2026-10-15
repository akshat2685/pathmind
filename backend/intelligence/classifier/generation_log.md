# Generation log — readiness classifier synthetic data (v1)

Generated: 2026-10-15 (seed=42, deterministic). Script: `generate_data.py`.

## Totals
- Total examples: 3661 (train=2908, test=753)
- Per-class counts (total):
  - precontemplation: 728
  - contemplation: 737
  - preparation: 732
  - action: 731
  - maintenance: 733
- Train per-class: {'precontemplation': 569, 'contemplation': 571, 'preparation': 588, 'action': 588, 'maintenance': 592}
- Test per-class: {'precontemplation': 159, 'contemplation': 166, 'preparation': 144, 'action': 143, 'maintenance': 141}

## Split methodology (template-level holdout)
- A random 80/20 row split would leak: the SAME template skeleton appears in
  both train and test with only slot words swapped, so 100% test accuracy would
  measure template memorization, not understanding (this was observed: 1.0000
  accuracy on a row-level split).
- Instead, templates are held out at the TEMPLATE level: for each class, template
  indices with `idx % 5 == 0` (5 of 24, ~21%) generate ONLY test examples; the
  remaining 19 generate ONLY train examples. Same rule for the 25 BORDERLINE
  templates (5 held out). Each noisy short answer is assigned wholly to train or
  test by coin flip (3:1) so identical surface strings never appear in both.
- The test set therefore contains phrasing patterns the model has never seen —
  a much more honest estimate of generalization within the synthetic
  distribution. `train.py` fits on `data_train.jsonl` only; `evaluate.py` scores
  on `data_test.jsonl` only. `data.jsonl` is the union (kept for reference).

## Templates
- 24 templates per class x 5 classes = 120 main templates (see `generate_data.py`,
  lists PRE_T / CON_T / PRP_T / ACT_T / MNT_T).
- Each template has slots: `{f}` (10 filler openers), `{who}`/`{goal}`
  (38 personas across 4 categories), `{h}` (7 hedges), `{e}` (6 enders).
- Personas: school (10, classes 6-12 + boards/JEE/NEET), college (10, B.Tech/BCA/B.Sc/MCA,
  CGPA/backlogs/placements/DSA), career switchers (8), small-business aspirants (8).
- ~700 examples per class drawn from templates; exact-duplicate (label+text) pairs
  rejected.

## How ambiguity was introduced
1. **25 hand-written borderline templates** (`BORDERLINE`), each generated 6x with
   fresh persona draws (~150 examples). Each carries a "why" note: negated
   preparation cues (bought books, never opened), ambivalence with action cues
   (signed up for workshop but hopes it is cancelled), short/garbled answers,
   awareness-without-intent (precontemplation, not contemplation), relapse
   survived by systems (maintenance), time boundaries (4 months: action vs
   maintenance — labeled by vigilance-about-relapse).
2. **25 noisy one-to-three-word answers** (`NOISY`: "idk maybe", "starting soon",
   "day 5", "habit now", ...) each repeated 8x (~200 examples) — mimics terse
   onboarding replies.
3. **Anti-cue templates inside classes**: e.g. precontemplation examples that use
   the words "plan"/"goal" while rejecting change ("i have no plan and i dont
   want one"), and contemplation examples containing "started"/"change" in
   tentative or negated frames ("nothing has changed yet, but..."). This is meant
   to stop the model from keying on single cue words — though on purely synthetic
   data the model can still memorize template skeletons (see eval_report.md).

## Known limitations of this data
- All examples are synthetic: vocabulary, grammar patterns and class boundaries
  come from the template author's head, not from real learners.
- Real onboarding text will have typos, Hinglish/code-mixing, and messier
  reasoning than this data — expect a real-world accuracy drop.
- Borderline labels reflect the author's judgment of TTM stage boundaries;
  a human rater study was not done.
