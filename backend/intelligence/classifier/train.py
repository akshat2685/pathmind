"""
Train the two baseline models for the PathMind readiness classifier (v1).

- Template-level train/test split: `data_train.jsonl` / `data_test.jsonl`
  (templates held out at the template level — see generation_log.md; the test
  set contains phrasing patterns never seen in training).
- TF-IDF (word unigrams+bigrams) + LogisticRegression.
- TF-IDF (same vectorizer) + LinearSVC.
- No hyperparameter tuning (per the honesty rules in the classifier spec).
- Saves: vectorizer.joblib, model_logreg.joblib, model_svc.joblib.

> This classifier is a SCREENING HEURISTIC, not a psychological diagnosis.
> It must not be used to label a person's mental state or make clinical claims.
"""
import json
import os

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC

HERE = os.path.dirname(os.path.abspath(__file__))
SEED = 42
LABELS = ["precontemplation", "contemplation", "preparation", "action", "maintenance"]


def load(path):
    texts, labels = [], []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            ex = json.loads(line)
            texts.append(ex["text"])
            labels.append(ex["label"])
    return texts, labels


def main():
    X_train, y_train = load(os.path.join(HERE, "data_train.jsonl"))
    X_test, y_test = load(os.path.join(HERE, "data_test.jsonl"))
    print(f"train={len(X_train)} test={len(X_test)}")

    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)
    Xtr = vectorizer.fit_transform(X_train)

    logreg = LogisticRegression(max_iter=1000, random_state=SEED)  # defaults, untuned
    logreg.fit(Xtr, y_train)

    svc = LinearSVC(random_state=SEED)  # defaults, untuned
    svc.fit(Xtr, y_train)

    joblib.dump(vectorizer, os.path.join(HERE, "vectorizer.joblib"))
    joblib.dump(logreg, os.path.join(HERE, "model_logreg.joblib"))
    joblib.dump(svc, os.path.join(HERE, "model_svc.joblib"))
    print("train acc logreg:", logreg.score(Xtr, y_train))
    print("train acc svc:  ", svc.score(Xtr, y_train))
    print("saved models + vectorizer (test set untouched)")


if __name__ == "__main__":
    main()
