"""Fine-tunes DeBERTa-v3 (small and base) for injection detection and
pushes both to a private Hugging Face Hub repo (build order step 5).

Runs on Kaggle's free GPU — see defense_layer/train/README.md for the
push/run workflow. NOT executed locally: this repo's Intel Mac dev
laptop can't install torch (see the `ml` extra note in pyproject.toml),
so this script has been written carefully against standard HF
Transformers patterns but not run-tested. Treat the first real Kaggle
run as the actual verification, and watch its logs closely.

Reads train.csv/val.csv/held_out.csv straight from this repo's GitHub
raw URLs (kernel-metadata.json enables internet access) rather than
requiring a separate Kaggle Dataset upload — one less moving part to
keep in sync.
"""

from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd
from datasets import Dataset
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    Trainer,
    TrainingArguments,
)

GITHUB_RAW_BASE = (
    "https://raw.githubusercontent.com/AakashGiri12/CANARY/main/"
    "datasets/injection_classifier"
)
MODEL_NAMES = ["microsoft/deberta-v3-small", "microsoft/deberta-v3-base"]
HF_REPO_PREFIX = "canary-deberta"
OUTPUT_DIR = "/kaggle/working"


HF_TOKEN_DATASET_PATH = "/kaggle/input/canary-hf-token/hf_token.txt"


def get_hf_token() -> str:
    """Three ways to supply the HF token, tried in order:

    1. A private Kaggle Dataset mounted at HF_TOKEN_DATASET_PATH. This is
       the primary path: UserSecretsClient().get_secret() is documented
       to fail with HTTP 400 on kernels triggered via `kaggle kernels
       push` (the API), even when the secret is correctly attached in
       the UI - it's only reliable for interactive browser-triggered
       runs. See https://www.kaggle.com/product-feedback/467871
    2. Kaggle Secrets (kept for interactive/manual runs, where it does
       work).
    3. An HF_TOKEN env var (local debugging, Colab, etc).
    """
    if os.path.exists(HF_TOKEN_DATASET_PATH):
        with open(HF_TOKEN_DATASET_PATH) as f:
            return f.read().strip()

    try:
        from kaggle_secrets import UserSecretsClient

        token = UserSecretsClient().get_secret("HF_TOKEN")
        if token:
            return token
    except Exception:
        pass

    token = os.environ.get("HF_TOKEN")
    if not token:
        raise RuntimeError(
            "No HF token found. Expected one of: a private Kaggle Dataset "
            f"mounted at {HF_TOKEN_DATASET_PATH}, a Kaggle Secret named "
            "HF_TOKEN (interactive runs only), or an HF_TOKEN env var."
        )
    return token


def load_splits() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    train = pd.read_csv(f"{GITHUB_RAW_BASE}/train.csv")
    val = pd.read_csv(f"{GITHUB_RAW_BASE}/val.csv")
    held_out = pd.read_csv(f"{GITHUB_RAW_BASE}/held_out.csv")
    return train, val, held_out


def to_hf_dataset(df: pd.DataFrame, tokenizer, max_length: int = 256) -> Dataset:
    ds = Dataset.from_pandas(df[["text", "label"]].reset_index(drop=True))
    # Trainer/model.forward() expect the label column named "labels"
    # (plural) - the CSV column is "label" (singular).
    ds = ds.rename_column("label", "labels")

    def _tokenize(batch):
        return tokenizer(batch["text"], truncation=True, max_length=max_length)

    return ds.map(_tokenize, batched=True)


def compute_metrics(eval_pred) -> dict:
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)
    precision, recall, f1, _ = precision_recall_fscore_support(
        labels, preds, average="binary", zero_division=0
    )
    return {
        "accuracy": accuracy_score(labels, preds),
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def evaluate_on(trainer: Trainer, df: pd.DataFrame, tokenizer) -> dict:
    ds = to_hf_dataset(df, tokenizer)
    metrics = trainer.evaluate(eval_dataset=ds)
    return {k.replace("eval_", ""): v for k, v in metrics.items()}


def train_one_model(
    model_name: str,
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    held_out_df: pd.DataFrame,
    hf_token: str,
    hf_username: str,
) -> dict:
    print(f"\n=== training {model_name} ===")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(model_name, num_labels=2)

    train_ds = to_hf_dataset(train_df, tokenizer)
    val_ds = to_hf_dataset(val_df, tokenizer)

    short_name = model_name.split("/")[-1]

    # NOTE: `eval_strategy` is the current (transformers>=4.4x) param
    # name; older versions used `evaluation_strategy`. If this errors on
    # Kaggle's image, that's the first thing to check.
    args = TrainingArguments(
        output_dir=f"{OUTPUT_DIR}/{short_name}",
        num_train_epochs=3,
        per_device_train_batch_size=16,
        per_device_eval_batch_size=32,
        learning_rate=2e-5,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        logging_steps=10,
        report_to=[],
    )

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        compute_metrics=compute_metrics,
    )

    trainer.train()
    val_metrics = evaluate_on(trainer, val_df, tokenizer)
    held_out_metrics = evaluate_on(trainer, held_out_df, tokenizer)

    hub_repo_id = f"{hf_username}/{HF_REPO_PREFIX}-{short_name}"
    model.push_to_hub(hub_repo_id, token=hf_token, private=True)
    tokenizer.push_to_hub(hub_repo_id, token=hf_token, private=True)

    return {
        "model_name": model_name,
        "hub_repo_id": hub_repo_id,
        "val_metrics": val_metrics,
        "held_out_metrics": held_out_metrics,
    }


def main() -> None:
    hf_token = get_hf_token()

    from huggingface_hub import HfApi

    hf_username = HfApi().whoami(token=hf_token)["name"]

    train_df, val_df, held_out_df = load_splits()
    print(f"train={len(train_df)} val={len(val_df)} held_out={len(held_out_df)}")

    results = []
    for model_name in MODEL_NAMES:
        try:
            result = train_one_model(
                model_name, train_df, val_df, held_out_df, hf_token, hf_username
            )
        except Exception as exc:  # keep going even if one model fails
            print(f"!!! {model_name} failed: {exc}")
            result = {"model_name": model_name, "error": str(exc)}
        results.append(result)
        print(json.dumps(result, indent=2, default=str))

    summary_path = f"{OUTPUT_DIR}/training_results.json"
    with open(summary_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nwrote summary to {summary_path}")


if __name__ == "__main__":
    main()
