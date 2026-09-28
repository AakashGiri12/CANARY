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
- `kernel-metadata.json` — Kaggle kernel config: `enable_gpu`,
  `enable_internet`, and `dataset_sources` pointing at the private
  `canary-hf-token` dataset (see below).

## One-time setup: HF token

Two things get tried in this repo's history, only one of which actually
works for API-pushed kernels — worth knowing both:

- **Kaggle Secrets** (`kaggle_secrets.UserSecretsClient`) can only be
  attached through the Kaggle web UI (Add-ons → Secrets on the kernel
  editor page) — there's no API way to inject them on push. Worse: even
  when attached, `get_secret()` is documented to fail with HTTP 400 on
  kernels triggered via `kaggle kernels push` — it only reliably works
  for interactive, browser-triggered runs
  ([Kaggle product-feedback #467871](https://www.kaggle.com/product-feedback/467871)).
  `train_classifier.py` still tries this as a fallback (so it works if
  you ever run the notebook interactively), but don't rely on it for the
  CLI-driven workflow below.
- **A private Kaggle Dataset** containing just the token is what
  actually works for `kaggle kernels push` runs — the kernel reads it as
  a mounted file. This is the primary path `get_hf_token()` uses. Set it
  up once:

  ```bash
  mkdir -p /tmp/canary_hf_token_upload
  cat > /tmp/canary_hf_token_upload/dataset-metadata.json <<'JSON'
  {"title": "canary-hf-token", "id": "<username>/canary-hf-token", "licenses": [{"name": "CC0-1.0"}]}
  JSON
  printf '%s' '<your-hf-write-token>' > /tmp/canary_hf_token_upload/hf_token.txt
  chmod 600 /tmp/canary_hf_token_upload/hf_token.txt

  kaggle datasets create -p /tmp/canary_hf_token_upload   # private by default
  ```

  Note the filename is `dataset-metadata.json` (singular) — Kaggle's own
  `--help` text says `datasets-metadata.json` (plural), which is wrong
  and will fail with "Metadata file not found".

  Get the token itself at `huggingface.co/settings/tokens` with **Write**
  access (the script needs it to push trained weights).

## Running it

```bash
pip install kaggle   # once
# ~/.kaggle/access_token must exist (Kaggle -> Settings -> API -> Create New Token
# gives you a one-line command that writes this file directly)

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
