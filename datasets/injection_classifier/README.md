# datasets/injection_classifier

Labeled dataset for the Defense Layer's trained classifier (build order
step 5): `train.csv`, `val.csv`, `held_out.csv`, columns `text,label,category`
(`label` 1 = injection, 0 = clean).

## This is synthetic, not scraped

`build_dataset.py` generates every row from templates (7 injection
categories × 15 attacker goals, embedded in email/webpage/file-note
carriers alongside benign filler text) — it does **not** pull real
examples from AgentDojo, InjecAgent, or anywhere else. That was a
deliberate scope call: doing that properly needs actual network fetches
against those repos and a license check before reuse, which is follow-up
work, not something to fake by hardcoding a few of their example strings
in here.

What this buys us now: a real, reusable dataset-builder script and a
big-enough, balanced, leakage-free corpus to get the classifier training
pipeline (Kaggle → Hugging Face Hub → Oracle VM) working end to end. What
it doesn't buy: any claim that classifier accuracy on this data predicts
accuracy on real-world injection attempts, which will use phrasing this
generator never produces. Upgrading to real examples is the natural next
step once the pipeline itself is proven out.

## `held_out.csv` and judge validation

The 100 rows in `held_out.csv` are never trained on — they're reserved
for LLM judge validation (build order step 10). They're **programmatically
labeled, not hand-verified by a human**. Per the root CLAUDE.md, judge
validation requires a hand-labeled set; before treating this file as
ground truth for that step, a human should spot-check it (or replace it
with genuinely hand-labeled examples).

## Regenerating

```bash
python3 datasets/injection_classifier/build_dataset.py
```

Deterministic (fixed `SEED`) — reruns reproduce the same split. Prints a
class-balance summary for each file.
