"""
Evaluate both baselines on the template-held-out test set (`data_test.jsonl`),
whose phrasing patterns were never seen in training. Prints metrics and saves
raw results for eval_report.md.

> This classifier is a SCREENING HEURISTIC, not a psychological diagnosis.
> It must not be used to label a person's mental state or make clinical claims.
"""
import json
import os

import joblib
from sklearn.metrics import (accuracy_score, classification_report,
                             confusion_matrix)

HERE = os.path.dirname(os.path.abspath(__file__))
LABELS = ["precontemplation", "contemplation", "preparation", "action", "maintenance"]


def load_test():
    texts, labels = [], []
    with open(os.path.join(HERE, "data_test.jsonl"), encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            ex = json.loads(line)
            texts.append(ex["text"])
            labels.append(ex["label"])
    return texts, labels


def main():
    vec = joblib.load(os.path.join(HERE, "vectorizer.joblib"))
    models = {
        "logreg": joblib.load(os.path.join(HERE, "model_logreg.joblib")),
        "svc": joblib.load(os.path.join(HERE, "model_svc.joblib")),
    }
    test_texts, y_test = load_test()
    X_test = vec.transform(test_texts)

    results = {}
    for name, model in models.items():
        pred = model.predict(X_test)
        acc = accuracy_score(y_test, pred)
        rep = classification_report(y_test, pred, labels=LABELS, digits=4,
                                    output_dict=True, zero_division=0)
        cm = confusion_matrix(y_test, pred, labels=LABELS)
        results[name] = {"acc": acc, "report": rep, "cm": cm.tolist(), "pred": pred}
        print(f"== {name}: accuracy={acc:.4f}")
        print(classification_report(y_test, pred, labels=LABELS, digits=4,
                                    zero_division=0))
        print("confusion matrix (rows=true, cols=pred):")
        print(cm)

    joblib.dump(results, os.path.join(HERE, "eval_results.joblib"))
    return results


if __name__ == "__main__":
    main()
