"""
Inference entry point for the PathMind readiness-to-change classifier (v1).

Exposes:
    predict(text) -> {"stage": ..., "confidence": ..., "note": ...}

Uses the TF-IDF + LinearSVC baseline (`model_svc.joblib`), the stronger of the
two baselines on the template-held-out test set. Confidence is the softmax of
the LinearSVC decision function (a rough calibration, not a true probability).

> DISCLAIMER: This classifier is a SCREENING HEURISTIC, not a psychological
> diagnosis. It must not be used to label a person's mental state or make
> clinical claims.

Stage labels (Transtheoretical Model, fixed strings):
  precontemplation, contemplation, preparation, action, maintenance
"""
import os

import joblib
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))

DISCLAIMER = (
    "Screening heuristic only — not a psychological diagnosis. "
    "Do not use this output to label a person's mental state or make clinical claims."
)

LABELS = ["precontemplation", "contemplation", "preparation", "action", "maintenance"]

_vectorizer = None
_model = None


def _load():
    global _vectorizer, _model
    if _vectorizer is None:
        _vectorizer = joblib.load(os.path.join(HERE, "vectorizer.joblib"))
        _model = joblib.load(os.path.join(HERE, "model_svc.joblib"))
    return _vectorizer, _model


def _softmax(x):
    x = np.asarray(x, dtype=float)
    e = np.exp(x - x.max())
    return e / e.sum()


def predict(text):
    """Classify onboarding text into a readiness stage.

    Returns {"stage": <label>, "confidence": <0..1 float>, "note": <disclaimer>}.
    """
    vec, model = _load()
    text = (text or "").strip()
    if not text:
        return {"stage": "contemplation", "confidence": 0.0, "note": DISCLAIMER}
    X = vec.transform([text])
    scores = model.decision_function(X)[0]
    probs = _softmax(scores)
    best = int(np.argmax(probs))
    return {
        "stage": model.classes_[best],
        "confidence": round(float(probs[best]), 4),
        "note": DISCLAIMER,
    }


if __name__ == "__main__":
    samples = [
        ("I don't see any problem with my maths marks, everyone should stop bothering me.",
         "precontemplation"),
        ("I've been wondering lately if I should do something about my coding practice, but I'm not sure where to begin.",
         "contemplation"),
        ("I've decided to work on my placement preparation starting next month and bought the books already.",
         "preparation"),
        ("I've been working on my DSA practice every day for the past two weeks and I'm sticking to it.",
         "action"),
        ("I've kept up my study routine for over six months now; it's just part of who I am.",
         "maintenance"),
    ]
    for text, expected in samples:
        out = predict(text)
        print(f"expected={expected:17s} predicted={out['stage']:17s} "
              f"conf={out['confidence']:.3f}")
        print(f"   note: {out['note']}")
