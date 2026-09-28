# defense_layer/train

Classifier training (build order step 5): fine-tune `deberta-v3-small`
and `deberta-v3-base` for injection detection on Kaggle's free GPU, push
both to a private Hugging Face Hub repo. See "Classifier training
workflow" in the root CLAUDE.md for the full rationale.

Not run locally — this repo's Intel Mac dev laptop can't install torch
(no wheels; see the `ml` extra note in `pyproject.toml`), so training
happens entirely on Kaggle.

## Contents

- `train_classifier.py` — the training script itself. Loads
  `datasets/injection_classifier/{train,val,held_out}.csv` straight from
  this repo's GitHub raw URLs, fine-tunes both model sizes, evaluates
  accuracy/precision/recall/F1 on val and held_out, pushes each to
  `<hf-username>/canary-deberta-<size>` (private), writes a
  `training_results.json` summary.
- `kernel-metadata.json` — Kaggle kernel config (`enable_gpu`,
  `enable_internet`). Replace `<KAGGLE_USERNAME>` with your actual
  Kaggle username before pushing.

## One-time setup: HF token as a Kaggle Secret

Kaggle Secrets can only be attached through the Kaggle web UI — there's
no API/CLI way to inject them into a kernel push (that would defeat the
point of a secret). So:

1. Get a **write**-scoped token at `huggingface.co/settings/tokens` (the
   script needs write access to push trained weights).
2. Push this kernel at least once (see below) so it exists on Kaggle.
3. Open it at `kaggle.com/code/<username>/canary-classifier-training`.
4. Top menu → **Add-ons** → **Secrets** → **Add a new secret**:
   - Label: `HF_TOKEN` (exact — the script reads it by this name)
   - Value: your HF token
5. Save, then make sure the toggle next to `HF_TOKEN` is **on** for this
   notebook specifically (Kaggle requires attaching a secret per-kernel
   even though it's stored once on your account).

## Running it

```bash
pip install kaggle   # once
# ~/.kaggle/kaggle.json must exist (Kaggle -> Settings -> API -> Create New Token)

cd defense_layer/train
kaggle kernels push          # uploads + triggers a run
kaggle kernels status <KAGGLE_USERNAME>/canary-classifier-training
kaggle kernels output <KAGGLE_USERNAME>/canary-classifier-training -p ./output
```

The dataset CSVs are fetched from `main` on GitHub at kernel runtime, so
push any dataset changes to GitHub first — the kernel won't see local,
unpushed changes.

## Known risk, unverified

`eval_strategy` (the `TrainingArguments` param controlling when
evaluation runs) is the current name as of `transformers>=4.4x`; older
versions use `evaluation_strategy`. If the first real run errors on
`TrainingArguments(...)`, that's the first thing to check against
whatever `transformers` version Kaggle's default GPU image ships.

## Verify this step is done

- [ ] Both classifier sizes trained, weights pushed to the Hub, metrics
      (val + held_out) recorded in `training_results.json`
- [ ] Off-the-shelf baseline (e.g. ProtectAI's deberta-v3-base
      prompt-injection model — verify current name/license) run on the
      same `held_out.csv` — not yet built, follow-up to this step
- [ ] At least one trained classifier deployed and reachable from the
      Oracle VM — depends on that VM being provisioned (build order
      step 6 territory)
