# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %%
"""
Deep Past Challenge - ByT5 Training v2

This script assumes you have already generated:
  - train_final.csv
  - val_final.csv

It fine-tunes a ByT5 model for Akkadian -> English translation and
evaluates with BLEU + chrF++ geometric mean.
"""

# %%
import os
import gc
import re
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import pandas as pd
import torch

from datasets import Dataset
from transformers import (
    AutoTokenizer,
    AutoModelForSeq2SeqLM,
    DataCollatorForSeq2Seq,
    Seq2SeqTrainer,
    Seq2SeqTrainingArguments,
    EarlyStoppingCallback,
)
import evaluate

os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

print("CUDA available:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))

# %%
# Paths - auto-detect Kaggle vs local
if Path("/kaggle/input").exists():
    TRAIN_PATH = Path("/kaggle/working/train_final.csv")
    VAL_PATH = Path("/kaggle/working/val_final.csv")
else:
    TRAIN_PATH = Path("train_final.csv")
    VAL_PATH = Path("val_final.csv")

OUTPUT_DIR = Path("./byt5-dpc-v2")
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

# Model selection
MODEL_PATH = os.environ.get(
    "DPC_MODEL_PATH", "google/byt5-base"  # set to a Kaggle dataset path if desired
)

# Hyperparameters
MAX_SRC = int(os.environ.get("DPC_MAX_SRC", 512))
MAX_TGT = int(os.environ.get("DPC_MAX_TGT", 256))
BATCH = int(os.environ.get("DPC_BATCH", 2))
ACCUM = int(os.environ.get("DPC_ACCUM", 16))
EPOCHS = int(os.environ.get("DPC_EPOCHS", 3))
LR = float(os.environ.get("DPC_LR", 2e-5))

PREFIX = "translate Akkadian to English: "

print("TRAIN_PATH:", TRAIN_PATH)
print("VAL_PATH:", VAL_PATH)
print("MODEL_PATH:", MODEL_PATH)

# %%
# Normalization (must match data_prep_v2)
_punct_to_space = re.compile(r"[/:]")
_remove_brackets = re.compile(r"[\[\]\(\)<>«»‹›⟨⟩]")
_remove_half_brackets = re.compile(r"[˹˺]")
_remove_double_angles = re.compile(r"<<|>>")
_multi_space = re.compile(r"\s+")
_ellipses = re.compile(r"(\.{3,}|…+)")
_gap_x = re.compile(r"(\[x\]|\(x\)|\bx\b)", re.IGNORECASE)
_subscript_map = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")
_h_map = str.maketrans({"Ḫ": "H", "ḫ": "h"})


def normalize_transliteration(text: str) -> str:
    if pd.isna(text):
        return ""
    t = str(text)
    t = t.translate(_h_map)
    t = t.translate(_subscript_map)
    t = _ellipses.sub(" <big_gap> ", t)
    t = _gap_x.sub(" <gap> ", t)
    t = _remove_double_angles.sub(" ", t)
    t = _remove_half_brackets.sub("", t)
    t = _remove_brackets.sub("", t)
    t = _punct_to_space.sub(" ", t)
    t = _multi_space.sub(" ", t).strip()
    return t


def normalize_translation(text: str) -> str:
    if pd.isna(text):
        return ""
    t = str(text)
    t = t.translate(_subscript_map)
    t = _ellipses.sub(" <big_gap> ", t)
    t = _gap_x.sub(" <gap> ", t)
    t = _remove_double_angles.sub(" ", t)
    t = _remove_half_brackets.sub("", t)
    t = _remove_brackets.sub("", t)
    t = _multi_space.sub(" ", t).strip()
    return t


# %%
# Load data
train_df = pd.read_csv(TRAIN_PATH)
val_df = pd.read_csv(VAL_PATH)
print(f"Train rows: {len(train_df):,} | Val rows: {len(val_df):,}")

train_df["transliteration"] = train_df["transliteration"].map(normalize_transliteration)
train_df["translation"] = train_df["translation"].map(normalize_translation)
val_df["transliteration"] = val_df["transliteration"].map(normalize_transliteration)
val_df["translation"] = val_df["translation"].map(normalize_translation)

train_ds = Dataset.from_pandas(train_df[["transliteration", "translation"]])
val_ds = Dataset.from_pandas(val_df[["transliteration", "translation"]])

# %%
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_PATH)

if torch.cuda.is_available():
    model.gradient_checkpointing_enable()
    model.config.use_cache = False


def preprocess_function(batch):
    inputs = [PREFIX + t for t in batch["transliteration"]]
    model_inputs = tokenizer(
        inputs,
        max_length=MAX_SRC,
        truncation=True,
    )
    with tokenizer.as_target_tokenizer():
        labels = tokenizer(
            batch["translation"],
            max_length=MAX_TGT,
            truncation=True,
        )
    model_inputs["labels"] = labels["input_ids"]
    return model_inputs


tokenized_train = train_ds.map(preprocess_function, batched=True, remove_columns=train_ds.column_names)
tokenized_val = val_ds.map(preprocess_function, batched=True, remove_columns=val_ds.column_names)

data_collator = DataCollatorForSeq2Seq(tokenizer, model=model)

# %%
# Metrics: BLEU + chrF++ geometric mean
bleu_metric = evaluate.load("sacrebleu")
chrf_metric = evaluate.load("chrf")


def postprocess_text(preds, labels):
    preds = [p.strip() for p in preds]
    labels = [[l.strip()] for l in labels]
    return preds, labels


def compute_metrics(eval_preds):
    preds, labels = eval_preds
    preds = np.where(preds != -100, preds, tokenizer.pad_token_id)
    decoded_preds = tokenizer.batch_decode(preds, skip_special_tokens=True)

    labels = np.where(labels != -100, labels, tokenizer.pad_token_id)
    decoded_labels = tokenizer.batch_decode(labels, skip_special_tokens=True)

    decoded_preds, decoded_labels = postprocess_text(decoded_preds, decoded_labels)

    bleu = bleu_metric.compute(predictions=decoded_preds, references=decoded_labels)[
        "score"
    ]
    chrf = chrf_metric.compute(
        predictions=decoded_preds, references=decoded_labels, word_order=2
    )["score"]
    geom = np.sqrt(bleu * chrf) if bleu > 0 and chrf > 0 else 0.0
    return {"bleu": bleu, "chrf++": chrf, "geom_mean": geom}


# %%
training_args = Seq2SeqTrainingArguments(
    output_dir=str(OUTPUT_DIR),
    evaluation_strategy="epoch",
    save_strategy="epoch",
    learning_rate=LR,
    per_device_train_batch_size=BATCH,
    per_device_eval_batch_size=BATCH,
    gradient_accumulation_steps=ACCUM,
    num_train_epochs=EPOCHS,
    fp16=torch.cuda.is_available(),
    predict_with_generate=True,
    generation_max_length=MAX_TGT,
    generation_num_beams=4,
    logging_steps=50,
    save_total_limit=2,
    load_best_model_at_end=True,
    metric_for_best_model="geom_mean",
    greater_is_better=True,
    report_to="none",
)

trainer = Seq2SeqTrainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_train,
    eval_dataset=tokenized_val,
    data_collator=data_collator,
    tokenizer=tokenizer,
    compute_metrics=compute_metrics,
    callbacks=[EarlyStoppingCallback(early_stopping_patience=2)],
)

gc.collect()
if torch.cuda.is_available():
    torch.cuda.empty_cache()

trainer.train()

print("Training complete. Best model saved to:", OUTPUT_DIR)

