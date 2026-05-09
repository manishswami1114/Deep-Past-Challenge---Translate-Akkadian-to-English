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
Deep Past Challenge - ByT5 Inference v2

Supports single-model or multi-model ensemble (simple MBR if sacrebleu available).
Outputs submission.csv in the working directory.
"""

# %%
import os
import re
from pathlib import Path
from typing import List

import pandas as pd
import numpy as np
import torch
from torch.cuda.amp import autocast
from torch.utils.data import DataLoader, Dataset
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

os.environ["TOKENIZERS_PARALLELISM"] = "false"

# %%
# Paths - auto-detect Kaggle vs local
if Path("/kaggle/input").exists():
    TEST_PATH = Path("/kaggle/input/deep-past-initiative-machine-translation/test.csv")
    OUTPUT_DIR = Path("/kaggle/working")
else:
    TEST_PATH = Path("data/deep-past-initiative-machine-translation/test.csv")
    OUTPUT_DIR = Path(".")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Model paths (comma-separated)
MODEL_PATHS = os.environ.get("DPC_MODEL_PATHS", "google/byt5-base").split(",")
MODEL_PATHS = [m.strip() for m in MODEL_PATHS if m.strip()]

# Generation parameters
MAX_SRC = int(os.environ.get("DPC_MAX_SRC", 512))
MAX_NEW_TOKENS = int(os.environ.get("DPC_MAX_NEW_TOKENS", 256))
NUM_BEAMS = int(os.environ.get("DPC_NUM_BEAMS", 6))
LENGTH_PENALTY = float(os.environ.get("DPC_LENGTH_PENALTY", 1.2))
BATCH_SIZE = int(os.environ.get("DPC_BATCH", 8))

PREFIX = "translate Akkadian to English: "

print("TEST_PATH:", TEST_PATH)
print("MODEL_PATHS:", MODEL_PATHS)

# %%
# Normalization (must match training)
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
class AkkadianDataset(Dataset):
    def __init__(self, df: pd.DataFrame):
        self.ids = df["id"].tolist()
        self.texts = [
            PREFIX + normalize_transliteration(t) for t in df["transliteration"].tolist()
        ]

    def __len__(self):
        return len(self.ids)

    def __getitem__(self, idx):
        return self.ids[idx], self.texts[idx]


def load_models(paths: List[str]):
    models = []
    for p in paths:
        tokenizer = AutoTokenizer.from_pretrained(p)
        model = AutoModelForSeq2SeqLM.from_pretrained(p)
        if torch.cuda.is_available():
            model = model.cuda().eval()
        models.append((tokenizer, model))
    return models


def generate_batch(tokenizer, model, batch_texts):
    inputs = tokenizer(
        batch_texts,
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=MAX_SRC,
    )
    if torch.cuda.is_available():
        inputs = {k: v.cuda() for k, v in inputs.items()}
    with torch.inference_mode():
        if torch.cuda.is_available():
            with autocast():
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=MAX_NEW_TOKENS,
                    num_beams=NUM_BEAMS,
                    length_penalty=LENGTH_PENALTY,
                    early_stopping=True,
                )
        else:
            outputs = model.generate(
                **inputs,
                max_new_tokens=MAX_NEW_TOKENS,
                num_beams=NUM_BEAMS,
                length_penalty=LENGTH_PENALTY,
                early_stopping=True,
            )
    return tokenizer.batch_decode(outputs, skip_special_tokens=True)


def mbr_select(candidates: List[str]) -> str:
    # Minimum Bayes Risk using chrF (if available), else majority vote.
    try:
        import sacrebleu

        scores = []
        for i, cand in enumerate(candidates):
            others = [c for j, c in enumerate(candidates) if j != i]
            if not others:
                scores.append(0.0)
                continue
            # average chrF of cand vs others
            s = 0.0
            for ref in others:
                s += sacrebleu.sentence_chrf(cand, [ref]).score
            scores.append(s / len(others))
        return candidates[int(np.argmax(scores))]
    except Exception:
        # fallback: majority vote
        counts = {}
        for c in candidates:
            counts[c] = counts.get(c, 0) + 1
        return max(counts, key=counts.get)


# %%
test_df = pd.read_csv(TEST_PATH)
dataset = AkkadianDataset(test_df)
dataloader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=False)

models = load_models(MODEL_PATHS)

results = []
for batch_ids, batch_texts in dataloader:
    # generate from each model
    model_outputs = []
    for tokenizer, model in models:
        preds = generate_batch(tokenizer, model, list(batch_texts))
        preds = [normalize_translation(p) for p in preds]
        model_outputs.append(preds)

    # transpose: list of candidates per sample
    for i, sample_id in enumerate(batch_ids):
        if torch.is_tensor(sample_id):
            sample_id = int(sample_id.item())
        candidates = [outs[i] for outs in model_outputs]
        if len(candidates) == 1:
            final = candidates[0]
        else:
            final = mbr_select(candidates)
        results.append({"id": sample_id, "translation": final})

submission = pd.DataFrame(results)
output_path = OUTPUT_DIR / "submission.csv"
submission.to_csv(output_path, index=False)
print(f"Saved: {output_path} ({len(submission)} rows)")
