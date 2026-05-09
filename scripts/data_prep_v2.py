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
Deep Past Challenge - Data Prep v2

Goals:
1) Build higher-quality sentence pairs using first_word_number + first_word_spelling
2) Clean transliteration + translation with competition-specific rules
3) Filter to English translations (heuristic)
4) Create train/val splits for training a seq2seq model
"""

# %%
from __future__ import annotations

import re
import json
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

# %%
# Paths - auto-detect Kaggle vs local
if Path("/kaggle/input").exists():
    BASE_PATH = Path("/kaggle/input/deep-past-initiative-machine-translation")
    ADDITIONAL_PATH = Path(
        "/kaggle/input/old-assyrian-grammars-and-other-resources/archive"
    )
    OUTPUT_PATH = Path("/kaggle/working")
else:
    BASE_PATH = Path("data/deep-past-initiative-machine-translation")
    ADDITIONAL_PATH = Path("data/additional_data/archive")
    OUTPUT_PATH = Path(".")

OUTPUT_PATH.mkdir(parents=True, exist_ok=True)

print(f"BASE_PATH: {BASE_PATH}")
print(f"ADDITIONAL_PATH: {ADDITIONAL_PATH}")
print(f"OUTPUT_PATH: {OUTPUT_PATH}")

# %%
# Load core datasets
train_df = pd.read_csv(BASE_PATH / "train.csv")
sentences_df = pd.read_csv(BASE_PATH / "Sentences_Oare_FirstWord_LinNum.csv")
published_df = pd.read_csv(BASE_PATH / "published_texts.csv")
lexicon_df = pd.read_csv(BASE_PATH / "OA_Lexicon_eBL.csv")

print(f"train_df: {len(train_df):,}")
print(f"sentences_df: {len(sentences_df):,}")
print(f"published_df: {len(published_df):,}")
print(f"lexicon_df: {len(lexicon_df):,}")

# %%
# Optional onomasticon (may not exist in some environments)
onomasticon_path = ADDITIONAL_PATH / "onomasticon.csv"
if onomasticon_path.exists():
    onomasticon_df = pd.read_csv(onomasticon_path)
    print(f"onomasticon_df: {len(onomasticon_df):,}")
else:
    onomasticon_df = None
    print("onomasticon.csv not found; skipping proper noun dictionary.")

# %%
# Normalization helpers

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
    # normalize special characters
    t = t.translate(_h_map)
    t = t.translate(_subscript_map)

    # replace gaps
    t = _ellipses.sub(" <big_gap> ", t)
    t = _gap_x.sub(" <gap> ", t)

    # remove bracket markers but keep content
    t = _remove_double_angles.sub(" ", t)
    t = _remove_half_brackets.sub("", t)
    t = _remove_brackets.sub("", t)

    # remove scribal dividers that function as word separators
    t = _punct_to_space.sub(" ", t)

    # normalize whitespace
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


_token_cleanup = re.compile(r"[\\.,;:!\\?\\[\\](){}<>]")


def _norm_token(token: str) -> str:
    if not isinstance(token, str):
        return ""
    return _token_cleanup.sub("", token)


# %%
# Language filter (simple stopword scoring)
_stops: Dict[str, set] = {
    "en": set(
        "the of and to in a is that for with as on at from by this it be are "
        "will have has you your he she they we our not or if into per who whom "
        "which".split()
    ),
    "de": set(
        "der die das und zu in den von mit ist sind war waren des dem im auf "
        "ein eine nicht ich du er sie wir ihr es".split()
    ),
    "fr": set(
        "le la les et de des du en un une est sont a au aux dans pour pas je "
        "tu il elle nous vous ils elles".split()
    ),
    "it": set(
        "il lo la i gli le e di del dei delle un una nel nella per non io tu "
        "lui lei noi voi loro".split()
    ),
    "es": set(
        "el la los las y de del en un una es son para por no yo tu el ella "
        "nosotros vosotros ellos".split()
    ),
    "tr": set(
        "ve bir bu da de mi mu için ile olan olarak değil ben sen o biz siz "
        "onlar".split()
    ),
}


def detect_lang_simple(text: str) -> Tuple[str, float]:
    if not isinstance(text, str):
        return "unk", 0.0
    tokens = re.findall(r"[A-Za-z']+", text.lower())
    if not tokens:
        return "unk", 0.0
    counts = {lang: 0 for lang in _stops}
    for t in tokens:
        for lang, words in _stops.items():
            if t in words:
                counts[lang] += 1
    lang = max(counts, key=counts.get)
    score = counts[lang] / max(len(tokens), 1)
    return lang, score


def is_english(text: str, min_score: float = 0.08) -> bool:
    lang, score = detect_lang_simple(text)
    return lang == "en" and score >= min_score


# %%
# Proper noun dictionary (optional)
def build_proper_noun_dict(onomasticon_df, lexicon_df) -> Dict[str, str]:
    name_dict = {}

    if onomasticon_df is not None:
        for _, row in onomasticon_df.iterrows():
            canonical = row.get("Name")
            spellings = str(row.get("Spellings_semicolon_separated", ""))
            if pd.notna(spellings) and spellings.strip():
                variants = [v.strip() for v in spellings.split(";") if v.strip()]
                for variant in variants:
                    name_dict[variant.lower()] = str(canonical)
            if pd.notna(canonical):
                name_dict[str(canonical).lower()] = str(canonical)

    pn_entries = lexicon_df[lexicon_df["type"] == "PN"]
    for _, row in pn_entries.iterrows():
        form = str(row.get("form", ""))
        norm = str(row.get("norm", ""))
        if form and norm and form.lower() not in name_dict:
            name_dict[form.lower()] = norm

    gn_entries = lexicon_df[lexicon_df["type"] == "GN"]
    for _, row in gn_entries.iterrows():
        form = str(row.get("form", ""))
        norm = str(row.get("norm", ""))
        if form and norm and form.lower() not in name_dict:
            name_dict[form.lower()] = norm

    return name_dict


proper_noun_dict = build_proper_noun_dict(onomasticon_df, lexicon_df)
with open(OUTPUT_PATH / "proper_noun_dict.json", "w", encoding="utf-8") as f:
    json.dump(proper_noun_dict, f, ensure_ascii=False, indent=2)

print(f"proper_noun_dict: {len(proper_noun_dict):,}")

# %%
# Sentence extraction using first_word_number / first_word_spelling
def extract_sentence_pairs_word_index(
    sentences_df: pd.DataFrame, published_df: pd.DataFrame
) -> pd.DataFrame:
    merged = sentences_df.merge(
        published_df[["oare_id", "transliteration"]],
        left_on="text_uuid",
        right_on="oare_id",
        how="inner",
    )

    sentence_pairs: List[Dict[str, str]] = []

    for text_uuid, group in merged.groupby("text_uuid"):
        full_translit = str(group["transliteration"].iloc[0])
        words = full_translit.split()
        if not words:
            continue

        # sort by word index
        group = group.sort_values("first_word_number")

        valid = []
        for _, row in group.iterrows():
            idx = int(row["first_word_number"]) - 1
            if idx < 0 or idx >= len(words):
                continue
            if _norm_token(words[idx]).lower() == _norm_token(
                str(row.get("first_word_spelling", ""))
            ).lower():
                valid.append((idx, row))

        if not valid:
            continue

        for i, (start_idx, row) in enumerate(valid):
            end_idx = len(words)
            if i + 1 < len(valid):
                end_idx = valid[i + 1][0]
            if end_idx <= start_idx:
                continue
            sentence_translit = " ".join(words[start_idx:end_idx]).strip()
            sentence_trans = str(row.get("translation", "")).strip()
            if not sentence_translit or not sentence_trans:
                continue
            sentence_pairs.append(
                {
                    "text_uuid": text_uuid,
                    "sentence_uuid": row.get("sentence_uuid", ""),
                    "transliteration": sentence_translit,
                    "translation": sentence_trans,
                    "source": "sentence_word_index",
                }
            )

    return pd.DataFrame(sentence_pairs)


sentence_pairs_df = extract_sentence_pairs_word_index(sentences_df, published_df)
print(f"Extracted sentence pairs (word index): {len(sentence_pairs_df):,}")

# %%
# Document splitting (fallback heuristic)
def split_document_into_sentences(transliteration: str, translation: str) -> List[dict]:
    if pd.isna(transliteration) or pd.isna(translation):
        return []
    transliteration = str(transliteration).strip()
    translation = str(translation).strip()
    if not transliteration or not translation:
        return []

    # Split translation into sentences
    trans_sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", translation)
    trans_sentences = [s.strip() for s in trans_sentences if s.strip()]

    if len(trans_sentences) <= 1:
        return [{"transliteration": transliteration, "translation": translation}]

    translit_words = transliteration.split()
    total_trans_words = sum(len(s.split()) for s in trans_sentences)

    pairs = []
    translit_idx = 0
    for trans_sent in trans_sentences:
        trans_word_count = max(len(trans_sent.split()), 1)
        ratio = trans_word_count / max(total_trans_words, 1)
        translit_word_count = int(len(translit_words) * ratio)
        translit_word_count = max(1, translit_word_count)

        end_idx = min(translit_idx + translit_word_count, len(translit_words))
        translit_portion = " ".join(translit_words[translit_idx:end_idx])
        translit_idx = end_idx

        if translit_portion.strip() and trans_sent.strip():
            pairs.append(
                {"transliteration": translit_portion.strip(), "translation": trans_sent}
            )

    if translit_idx < len(translit_words) and pairs:
        remaining = " ".join(translit_words[translit_idx:])
        pairs[-1]["transliteration"] += " " + remaining

    return pairs


# %%
# Build training data
combined = []

# original document-level pairs
for _, row in train_df.iterrows():
    combined.append(
        {
            "transliteration": row["transliteration"],
            "translation": row["translation"],
            "source": "original_document",
        }
    )

# split document-level pairs
for _, row in train_df.iterrows():
    for pair in split_document_into_sentences(row["transliteration"], row["translation"]):
        pair["source"] = "train_split"
        combined.append(pair)

# extracted sentence pairs
if len(sentence_pairs_df) > 0:
    for _, row in sentence_pairs_df.iterrows():
        combined.append(
            {
                "transliteration": row["transliteration"],
                "translation": row["translation"],
                "source": row["source"],
            }
        )

combined_df = pd.DataFrame(combined)
print(f"Combined raw pairs: {len(combined_df):,}")
print(combined_df["source"].value_counts())

# %%
# Normalize + language filter
combined_df["transliteration"] = combined_df["transliteration"].map(
    normalize_transliteration
)
combined_df["translation"] = combined_df["translation"].map(normalize_translation)

combined_df = combined_df[
    (combined_df["transliteration"].str.len() >= 5)
    & (combined_df["translation"].str.len() >= 3)
]

# language filter
combined_df["is_english"] = combined_df["translation"].map(is_english)
english_df = combined_df[combined_df["is_english"]].copy()
english_df.drop(columns=["is_english"], inplace=True)

print(f"After English filter: {len(english_df):,}")

# %%
# Deduplicate + length filter
english_df = english_df.drop_duplicates(
    subset=["transliteration", "translation"], keep="first"
)

min_translit_len = 10
max_translit_len = 2000
min_trans_len = 5
max_trans_len = 5000

filtered_df = english_df[
    (english_df["transliteration"].str.len() >= min_translit_len)
    & (english_df["transliteration"].str.len() <= max_translit_len)
    & (english_df["translation"].str.len() >= min_trans_len)
    & (english_df["translation"].str.len() <= max_trans_len)
]

print(f"After dedup + length filter: {len(filtered_df):,}")

# %%
# Train/val split stratified by source
from sklearn.model_selection import train_test_split

train_data, val_data = train_test_split(
    filtered_df,
    test_size=0.1,
    random_state=42,
    stratify=filtered_df["source"],
)

print(f"Train: {len(train_data):,} | Val: {len(val_data):,}")

train_data.to_csv(OUTPUT_PATH / "train_final.csv", index=False)
val_data.to_csv(OUTPUT_PATH / "val_final.csv", index=False)
filtered_df.to_csv(OUTPUT_PATH / "train_augmented.csv", index=False)

print("Saved:")
print(f"  {OUTPUT_PATH / 'train_final.csv'}")
print(f"  {OUTPUT_PATH / 'val_final.csv'}")
print(f"  {OUTPUT_PATH / 'train_augmented.csv'}")
