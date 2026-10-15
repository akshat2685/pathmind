"""DistilBERT feasibility time trial: 1 epoch on a 300-example subset, CPU only.
Extrapolates to a full fine-tune (2,908 train examples x 3 epochs)."""
import json
import os
import time

import torch

torch.set_num_threads(2)
HERE = os.path.dirname(os.path.abspath(__file__))
LABELS = ["precontemplation", "contemplation", "preparation", "action", "maintenance"]
lab2id = {l: i for i, l in enumerate(LABELS)}

print("loading tokenizer/model (downloads weights on first run)...", flush=True)
t0 = time.time()
from transformers import (AutoModelForSequenceClassification, AutoTokenizer)

tok = AutoTokenizer.from_pretrained("distilbert-base-uncased")
model = AutoModelForSequenceClassification.from_pretrained(
    "distilbert-base-uncased", num_labels=5)
print(f"model load: {time.time()-t0:.1f}s", flush=True)

texts, labels = [], []
with open(os.path.join(HERE, "data_train.jsonl"), encoding="utf-8") as f:
    for line in f:
        ex = json.loads(line)
        texts.append(ex["text"])
        labels.append(lab2id[ex["label"]])
texts, labels = texts[:300], labels[:300]

enc = tok(texts, truncation=True, padding=True, max_length=64, return_tensors="pt")
input_ids, attn = enc["input_ids"], enc["attention_mask"]
print("subset:", input_ids.shape, flush=True)

opt = torch.optim.AdamW(model.parameters(), lr=5e-5)
model.train()
bs = 8
t0 = time.time()
for i in range(0, len(texts), bs):
    opt.zero_grad()
    out = model(input_ids=input_ids[i:i+bs], attention_mask=attn[i:i+bs],
                labels=torch.tensor(labels[i:i+bs]))
    out.loss.backward()
    opt.step()
dt = time.time() - t0
per_epoch_full = dt / 300 * 2908
print(f"1 epoch on 300 examples: {dt:.1f}s "
      f"-> extrapolated 1 epoch on 2908: {per_epoch_full/60:.1f} min "
      f"-> 3 epochs: {per_epoch_full*3/60:.1f} min "
      f"-> 5 epochs: {per_epoch_full*5/60:.1f} min", flush=True)
