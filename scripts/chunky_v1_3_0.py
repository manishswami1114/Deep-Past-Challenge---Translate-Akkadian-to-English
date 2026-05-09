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
Chunky v1.3.0 — S2: Exact competitor clone with length_penalty=1.5

Exact duplicate of serariagomes/akkadian-english-byt5-optimized-again
with only length_penalty changed from 1.09 to 1.5.
"""

import os

os.environ["OMP_NUM_THREADS"] = "4"
os.environ["MKL_NUM_THREADS"] = "4"
os.environ["CUDA_LAUNCH_BLOCKING"] = "0"
os.environ["TORCH_CUDNN_V8_API_ENABLED"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "true"

import re
import logging
import warnings
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import pandas as pd
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader, Sampler
from torch.cuda.amp import autocast
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from tqdm.auto import tqdm
import json
import random

warnings.filterwarnings("ignore")

print(f"PyTorch version: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(
        f"GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB"
    )


# %%
@dataclass
class UltraConfig:
    test_data_path: str = (
        "/kaggle/input/deep-past-initiative-machine-translation/test.csv"
    )
    model_path: str = "/kaggle/input/final-byt5/byt5-akkadian-optimized-34x"
    output_dir: str = "/kaggle/working/"

    max_length: int = 512
    batch_size: int = 8
    num_workers: int = 4

    num_beams: int = 8
    max_new_tokens: int = 512
    length_penalty: float = 1.5  # <-- CHANGED from 1.09
    early_stopping: bool = True
    no_repeat_ngram_size: int = 0

    use_mixed_precision: bool = True
    use_better_transformer: bool = True
    use_bucket_batching: bool = True
    use_vectorized_postproc: bool = True
    use_adaptive_beams: bool = True
    use_auto_batch_size: bool = False

    aggressive_postprocessing: bool = True
    checkpoint_freq: int = 100
    num_buckets: int = 4

    def __post_init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        Path(self.output_dir).mkdir(exist_ok=True, parents=True)
        if not torch.cuda.is_available():
            self.use_mixed_precision = False
            self.use_better_transformer = False


config = UltraConfig()
print(f"\nConfig: beams={config.num_beams}, length_penalty={config.length_penalty}")


# %%
def setup_logging(output_dir: str = "./outputs"):
    Path(output_dir).mkdir(exist_ok=True, parents=True)
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )
    return logging.getLogger(__name__)


logger = setup_logging(config.output_dir)


# %%
class OptimizedPreprocessor:
    def __init__(self):
        self.patterns = {
            "big_gap": re.compile(r"(\.{3,}|…+|……)"),
            "small_gap": re.compile(r"(xx+|\s+x\s+)"),
        }

    def preprocess_input_text(self, text: str) -> str:
        if pd.isna(text):
            return ""
        text = str(text)
        text = self.patterns["big_gap"].sub("<big_gap>", text)
        text = self.patterns["small_gap"].sub("<gap>", text)
        return text

    def preprocess_batch(self, texts: List[str]) -> List[str]:
        s = pd.Series(texts).fillna("")
        s = s.astype(str)
        s = s.str.replace(self.patterns["big_gap"], "<big_gap>", regex=True)
        s = s.str.replace(self.patterns["small_gap"], "<gap>", regex=True)
        return s.tolist()


preprocessor = OptimizedPreprocessor()


# %%
class VectorizedPostprocessor:
    def __init__(self, aggressive: bool = True):
        self.aggressive = aggressive
        self.patterns = {
            "gap": re.compile(r"(\[x\]|\(x\)|\bx\b)", re.I),
            "big_gap": re.compile(r"(\.{3,}|…|\[\.+\])"),
            "annotations": re.compile(
                r"\((fem|plur|pl|sing|singular|plural|\?|!)\..\s*\w*\)", re.I
            ),
            "repeated_words": re.compile(r"\b(\w+)(?:\s+\1\b)+"),
            "whitespace": re.compile(r"\s+"),
            "punct_space": re.compile(r"\s+([.,:])"),
            "repeated_punct": re.compile(r"([.,])\1+"),
        }
        self.subscript_trans = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")
        self.special_chars_trans = str.maketrans("ḫḪ", "hH")
        self.forbidden_chars = '!?()"——<>⌈⌋⌊[]+ʾ/;'
        self.forbidden_trans = str.maketrans("", "", self.forbidden_chars)

    def postprocess_batch(self, translations: List[str]) -> List[str]:
        s = pd.Series(translations)
        valid_mask = s.apply(lambda x: isinstance(x, str) and x.strip())
        if not valid_mask.all():
            s[~valid_mask] = ""

        s = s.str.translate(self.special_chars_trans)
        s = s.str.translate(self.subscript_trans)
        s = s.str.replace(self.patterns["whitespace"], " ", regex=True)
        s = s.str.strip()

        if self.aggressive:
            s = s.str.replace(self.patterns["gap"], "<gap>", regex=True)
            s = s.str.replace(self.patterns["big_gap"], "<big_gap>", regex=True)
            s = s.str.replace("<gap> <gap>", "<big_gap>", regex=False)
            s = s.str.replace("<big_gap> <big_gap>", "<big_gap>", regex=False)
            s = s.str.replace(self.patterns["annotations"], "", regex=True)

            s = s.str.replace("<gap>", "\x00GAP\x00", regex=False)
            s = s.str.replace("<big_gap>", "\x00BIG\x00", regex=False)
            s = s.str.translate(self.forbidden_trans)
            s = s.str.replace("\x00GAP\x00", " <gap> ", regex=False)
            s = s.str.replace("\x00BIG\x00", " <big_gap> ", regex=False)

            s = s.str.replace(r"(\d+)\.5\b", r"\1½", regex=True)
            s = s.str.replace(r"\b0\.5\b", "½", regex=True)
            s = s.str.replace(r"(\d+)\.25\b", r"\1¼", regex=True)
            s = s.str.replace(r"\b0\.25\b", "¼", regex=True)
            s = s.str.replace(r"(\d+)\.75\b", r"\1¾", regex=True)
            s = s.str.replace(r"\b0\.75\b", "¾", regex=True)

            s = s.str.replace(self.patterns["repeated_words"], r"\1", regex=True)
            for n in range(4, 1, -1):
                pattern = r"\b((?:\w+\s+){" + str(n - 1) + r"}\w+)(?:\s+\1\b)+"
                s = s.str.replace(pattern, r"\1", regex=True)

            s = s.str.replace(self.patterns["punct_space"], r"\1", regex=True)
            s = s.str.replace(self.patterns["repeated_punct"], r"\1", regex=True)
            s = s.str.replace(self.patterns["whitespace"], " ", regex=True)
            s = s.str.strip().str.strip("-").str.strip()

        return s.tolist()


postprocessor = VectorizedPostprocessor(aggressive=config.aggressive_postprocessing)


# %%
class BucketBatchSampler(Sampler):
    def __init__(
        self, dataset, batch_size: int, num_buckets: int = 4, shuffle: bool = False
    ):
        self.dataset = dataset
        self.batch_size = batch_size
        self.shuffle = shuffle

        lengths = [len(text.split()) for _, text in dataset]
        sorted_indices = sorted(range(len(lengths)), key=lambda i: lengths[i])

        bucket_size = len(sorted_indices) // num_buckets
        self.buckets = []
        for i in range(num_buckets):
            start = i * bucket_size
            end = None if i == num_buckets - 1 else (i + 1) * bucket_size
            self.buckets.append(sorted_indices[start:end])

        logger.info(f"Created {num_buckets} buckets:")
        for i, bucket in enumerate(self.buckets):
            bucket_lengths = [lengths[idx] for idx in bucket]
            logger.info(
                f"  Bucket {i}: {len(bucket)} samples, "
                f"length range [{min(bucket_lengths)}, {max(bucket_lengths)}]"
            )

    def __iter__(self):
        for bucket in self.buckets:
            if self.shuffle:
                random.shuffle(bucket)
            for i in range(0, len(bucket), self.batch_size):
                yield bucket[i : i + self.batch_size]

    def __len__(self):
        return sum(
            (len(b) + self.batch_size - 1) // self.batch_size for b in self.buckets
        )


# %%
class AkkadianDataset(Dataset):
    def __init__(self, dataframe: pd.DataFrame, preprocessor: OptimizedPreprocessor):
        self.sample_ids = dataframe["id"].tolist()
        raw_texts = dataframe["transliteration"].tolist()
        preprocessed = preprocessor.preprocess_batch(raw_texts)
        self.input_texts = [
            "translate Akkadian to English: " + text for text in preprocessed
        ]
        logger.info(f"Dataset created with {len(self.sample_ids)} samples")

    def __len__(self):
        return len(self.sample_ids)

    def __getitem__(self, index: int):
        return self.sample_ids[index], self.input_texts[index]


# %%
class UltraInferenceEngine:
    def __init__(self, config: UltraConfig):
        self.config = config
        self.preprocessor = OptimizedPreprocessor()
        self.postprocessor = VectorizedPostprocessor(
            aggressive=config.aggressive_postprocessing
        )
        self.results = []
        self._load_model()

    def _load_model(self):
        logger.info(f"Loading model from {self.config.model_path}")
        self.model = (
            AutoModelForSeq2SeqLM.from_pretrained(self.config.model_path)
            .to(self.config.device)
            .eval()
        )
        self.tokenizer = AutoTokenizer.from_pretrained(self.config.model_path)

        num_params = sum(p.numel() for p in self.model.parameters())
        logger.info(f"Model loaded: {num_params:,} parameters")

        if self.config.use_better_transformer and torch.cuda.is_available():
            try:
                from optimum.bettertransformer import BetterTransformer

                logger.info("Applying BetterTransformer...")
                self.model = BetterTransformer.transform(self.model)
                logger.info("BetterTransformer applied")
            except ImportError:
                logger.warning("optimum not installed, skipping BetterTransformer")
            except Exception as e:
                logger.warning(f"BetterTransformer failed: {e}")

    def _collate_fn(self, batch_samples):
        batch_ids = [s[0] for s in batch_samples]
        batch_texts = [s[1] for s in batch_samples]
        tokenized = self.tokenizer(
            batch_texts,
            max_length=self.config.max_length,
            padding=True,
            truncation=True,
            return_tensors="pt",
        )
        return batch_ids, tokenized

    def _get_adaptive_beam_size(self, input_ids, attention_mask):
        if not self.config.use_adaptive_beams:
            return self.config.num_beams
        lengths = attention_mask.sum(dim=1)
        beam_sizes = torch.where(
            lengths < 100,
            torch.tensor(max(4, self.config.num_beams // 2)),
            torch.tensor(self.config.num_beams),
        )
        return beam_sizes[0].item()

    def run_inference(self, test_df: pd.DataFrame) -> pd.DataFrame:
        logger.info("Starting inference")
        dataset = AkkadianDataset(test_df, self.preprocessor)

        if self.config.use_bucket_batching:
            batch_sampler = BucketBatchSampler(
                dataset, self.config.batch_size, num_buckets=self.config.num_buckets
            )
            dataloader = DataLoader(
                dataset,
                batch_sampler=batch_sampler,
                num_workers=self.config.num_workers,
                collate_fn=self._collate_fn,
                pin_memory=True,
                prefetch_factor=2,
                persistent_workers=True if self.config.num_workers > 0 else False,
            )
        else:
            dataloader = DataLoader(
                dataset,
                batch_size=self.config.batch_size,
                shuffle=False,
                num_workers=self.config.num_workers,
                collate_fn=self._collate_fn,
                pin_memory=True,
                prefetch_factor=2,
                persistent_workers=True if self.config.num_workers > 0 else False,
            )

        base_gen_config = {
            "max_new_tokens": self.config.max_new_tokens,
            "length_penalty": self.config.length_penalty,
            "early_stopping": self.config.early_stopping,
            "use_cache": True,
        }
        if self.config.no_repeat_ngram_size > 0:
            base_gen_config["no_repeat_ngram_size"] = self.config.no_repeat_ngram_size

        self.results = []

        with torch.inference_mode():
            for batch_idx, (batch_ids, tokenized) in enumerate(
                tqdm(dataloader, desc="Translating")
            ):
                try:
                    input_ids = tokenized.input_ids.to(self.config.device)
                    attention_mask = tokenized.attention_mask.to(self.config.device)

                    beam_size = self._get_adaptive_beam_size(input_ids, attention_mask)
                    gen_config = {**base_gen_config, "num_beams": beam_size}

                    if self.config.use_mixed_precision:
                        with autocast():
                            outputs = self.model.generate(
                                input_ids=input_ids,
                                attention_mask=attention_mask,
                                **gen_config,
                            )
                    else:
                        outputs = self.model.generate(
                            input_ids=input_ids,
                            attention_mask=attention_mask,
                            **gen_config,
                        )

                    translations = self.tokenizer.batch_decode(
                        outputs, skip_special_tokens=True
                    )

                    if self.config.use_vectorized_postproc:
                        cleaned = self.postprocessor.postprocess_batch(translations)
                    else:
                        cleaned = [
                            self.postprocessor.postprocess_batch([t])[0]
                            for t in translations
                        ]

                    self.results.extend(zip(batch_ids, cleaned))

                    if torch.cuda.is_available() and batch_idx % 10 == 0:
                        torch.cuda.empty_cache()

                except Exception as e:
                    logger.error(f"Batch {batch_idx} error: {e}")
                    self.results.extend([(bid, "") for bid in batch_ids])
                    continue

        logger.info("Inference completed")
        results_df = pd.DataFrame(self.results, columns=["id", "translation"])
        return results_df


# %%
logger.info(f"Loading test data from {config.test_data_path}")
test_df = pd.read_csv(config.test_data_path, encoding="utf-8")
logger.info(f"Loaded {len(test_df)} test samples")
print(f"\nTest samples: {len(test_df)}")
print(test_df.head())

# %%
engine = UltraInferenceEngine(config)
results_df = engine.run_inference(test_df)

# %%
output_path = Path(config.output_dir) / "submission.csv"
results_df.to_csv(output_path, index=False)
print(f"\nSubmission shape: {results_df.shape}")
print(results_df)
print(f"\nSaved submission.csv ({os.path.getsize(output_path):,} bytes)")
