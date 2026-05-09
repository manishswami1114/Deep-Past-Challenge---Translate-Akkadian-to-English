"""
Training script for ByT5 model on Akkadian-to-English translation.

Supports 3-phase curriculum training:
  Phase 1: Pre-fine-tune on all data (including ORACC, lower quality)
  Phase 2: Fine-tune on OA-only high-quality data
  Phase 3: Fine-tune on sentence-level only (match test distribution)

Designed to run on Kaggle with H100 GPU or locally.
"""

import os
import json
import math
import torch
import pandas as pd
import numpy as np
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

from torch.utils.data import Dataset, DataLoader, WeightedRandomSampler
from transformers import (
    AutoTokenizer,
    AutoModelForSeq2SeqLM,
    Seq2SeqTrainer,
    Seq2SeqTrainingArguments,
    DataCollatorForSeq2Seq,
    EarlyStoppingCallback,
)
import sacrebleu


# --- Configuration ---

@dataclass
class TrainingConfig:
    """Training configuration."""
    # Model
    model_name: str = "google/byt5-large"
    max_source_length: int = 1024
    max_target_length: int = 1280

    # Data paths (Kaggle or local)
    train_file: str = ""
    val_file: str = ""
    output_dir: str = "models/byt5-akkadian"

    # Phase 1: All data
    phase1_epochs: int = 5
    phase1_lr: float = 3e-4
    phase1_warmup_steps: int = 500

    # Phase 2: OA-only
    phase2_epochs: int = 15
    phase2_lr: float = 5e-5
    phase2_warmup_steps: int = 200

    # Phase 3: Sentence-level only
    phase3_epochs: int = 5
    phase3_lr: float = 1e-5
    phase3_warmup_steps: int = 100

    # Common
    batch_size: int = 4
    gradient_accumulation_steps: int = 8
    weight_decay: float = 0.01
    label_smoothing: float = 0.1
    fp16: bool = True
    seed: int = 42

    # Generation
    num_beams: int = 5
    length_penalty: float = 1.0
    no_repeat_ngram_size: int = 3

    # Input prefix
    source_prefix: str = "translate Akkadian to English: "

    @classmethod
    def from_yaml(cls, path: str):
        import yaml
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(**data)


# --- Dataset ---

class AkkadianDataset(Dataset):
    """Dataset for Akkadian-to-English translation with ByT5."""

    def __init__(
        self,
        data: pd.DataFrame,
        tokenizer,
        max_source_length: int = 1024,
        max_target_length: int = 1280,
        source_prefix: str = "translate Akkadian to English: ",
    ):
        self.data = data.reset_index(drop=True)
        self.tokenizer = tokenizer
        self.max_source_length = max_source_length
        self.max_target_length = max_target_length
        self.source_prefix = source_prefix

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        row = self.data.iloc[idx]
        source = self.source_prefix + str(row['transliteration'])
        target = str(row['translation'])

        # Tokenize source
        source_encoding = self.tokenizer(
            source,
            max_length=self.max_source_length,
            padding='max_length',
            truncation=True,
            return_tensors='pt',
        )

        # Tokenize target
        target_encoding = self.tokenizer(
            text_target=target,
            max_length=self.max_target_length,
            padding='max_length',
            truncation=True,
            return_tensors='pt',
        )

        labels = target_encoding['input_ids'].squeeze()
        # Replace padding token ids with -100 so they're ignored in loss
        labels[labels == self.tokenizer.pad_token_id] = -100

        return {
            'input_ids': source_encoding['input_ids'].squeeze(),
            'attention_mask': source_encoding['attention_mask'].squeeze(),
            'labels': labels,
        }


# --- Metrics ---

def compute_metrics(eval_preds, tokenizer):
    """Compute BLEU, chrF++, and geometric mean."""
    preds, labels = eval_preds

    # Decode predictions
    if isinstance(preds, tuple):
        preds = preds[0]

    # Replace -100 with pad token id
    labels = np.where(labels != -100, labels, tokenizer.pad_token_id)

    decoded_preds = tokenizer.batch_decode(preds, skip_special_tokens=True)
    decoded_labels = tokenizer.batch_decode(labels, skip_special_tokens=True)

    # Strip whitespace
    decoded_preds = [p.strip() for p in decoded_preds]
    decoded_labels = [l.strip() for l in decoded_labels]

    # Compute metrics
    bleu = sacrebleu.corpus_bleu(decoded_preds, [decoded_labels]).score
    chrf = sacrebleu.corpus_chrf(decoded_preds, [decoded_labels], word_order=2).score

    geo_mean = math.sqrt(bleu * chrf) if bleu > 0 and chrf > 0 else 0.0

    return {
        'bleu': bleu,
        'chrf_pp': chrf,
        'geo_mean': geo_mean,
    }


# --- Training ---

def create_weighted_sampler(data: pd.DataFrame) -> WeightedRandomSampler:
    """Create a weighted sampler based on source quality."""
    weights = data['weight'].values if 'weight' in data.columns else np.ones(len(data))
    sampler = WeightedRandomSampler(
        weights=weights,
        num_samples=len(data),
        replacement=True,
    )
    return sampler


def filter_data_for_phase(data: pd.DataFrame, phase: int) -> pd.DataFrame:
    """Filter data based on training phase."""
    if phase == 1:
        # All data
        return data

    elif phase == 2:
        # OA-only (exclude ORACC and publications, keep lexicon with low weight)
        oa_sources = ['strategy_a', 'strategy_b_short', 'strategy_b_aligned',
                      'strategy_b_doc', 'strategy_c', 'lexicon']
        return data[data['source'].isin(oa_sources)]

    elif phase == 3:
        # Sentence-level only (match test distribution)
        sentence_sources = ['strategy_a', 'strategy_b_aligned', 'strategy_c']
        return data[data['source'].isin(sentence_sources)]

    return data


def train_phase(
    model,
    tokenizer,
    train_data: pd.DataFrame,
    val_data: pd.DataFrame,
    config: TrainingConfig,
    phase: int,
    output_dir: str,
):
    """Run a single training phase."""
    phase_config = {
        1: (config.phase1_epochs, config.phase1_lr, config.phase1_warmup_steps),
        2: (config.phase2_epochs, config.phase2_lr, config.phase2_warmup_steps),
        3: (config.phase3_epochs, config.phase3_lr, config.phase3_warmup_steps),
    }

    epochs, lr, warmup = phase_config[phase]

    # Filter data for this phase
    phase_data = filter_data_for_phase(train_data, phase)
    print(f"\nPhase {phase}: {len(phase_data)} training examples, {epochs} epochs, lr={lr}")

    # Create datasets
    train_dataset = AkkadianDataset(
        phase_data, tokenizer,
        config.max_source_length, config.max_target_length,
        config.source_prefix,
    )

    val_dataset = AkkadianDataset(
        val_data, tokenizer,
        config.max_source_length, config.max_target_length,
        config.source_prefix,
    )

    # Training arguments
    training_args = Seq2SeqTrainingArguments(
        output_dir=output_dir,
        num_train_epochs=epochs,
        learning_rate=lr,
        per_device_train_batch_size=config.batch_size,
        per_device_eval_batch_size=config.batch_size,
        gradient_accumulation_steps=config.gradient_accumulation_steps,
        warmup_steps=warmup,
        weight_decay=config.weight_decay,
        label_smoothing_factor=config.label_smoothing,
        fp16=config.fp16,
        predict_with_generate=True,
        generation_max_length=config.max_target_length,
        generation_num_beams=config.num_beams,
        eval_strategy="epoch",
        save_strategy="epoch",
        logging_steps=50,
        save_total_limit=3,
        load_best_model_at_end=True,
        metric_for_best_model="geo_mean",
        greater_is_better=True,
        seed=config.seed,
        report_to="none",
        dataloader_num_workers=2,
    )

    # Data collator
    data_collator = DataCollatorForSeq2Seq(
        tokenizer=tokenizer,
        model=model,
        padding=True,
    )

    # Trainer
    trainer = Seq2SeqTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        tokenizer=tokenizer,
        data_collator=data_collator,
        compute_metrics=lambda p: compute_metrics(p, tokenizer),
        callbacks=[EarlyStoppingCallback(early_stopping_patience=3)],
    )

    # Train
    trainer.train()

    # Save best model
    best_dir = f"{output_dir}/best"
    trainer.save_model(best_dir)
    tokenizer.save_pretrained(best_dir)

    # Evaluate
    eval_results = trainer.evaluate()
    print(f"Phase {phase} results: {eval_results}")

    return model, eval_results


def train(config: TrainingConfig):
    """Run the full 3-phase curriculum training."""
    print(f"Loading model: {config.model_name}")
    tokenizer = AutoTokenizer.from_pretrained(config.model_name)
    model = AutoModelForSeq2SeqLM.from_pretrained(config.model_name)

    # Load data
    print(f"Loading training data from: {config.train_file}")
    train_data = pd.read_csv(config.train_file)
    val_data = pd.read_csv(config.val_file)

    print(f"Training data: {len(train_data)} examples")
    print(f"Validation data: {len(val_data)} examples")
    print(f"Sources: {train_data['source'].value_counts().to_dict()}")

    all_results = {}

    # Phase 1: All data
    print("\n" + "=" * 60)
    print("PHASE 1: Pre-fine-tune on all data")
    print("=" * 60)
    model, results = train_phase(
        model, tokenizer, train_data, val_data, config,
        phase=1, output_dir=f"{config.output_dir}/phase1"
    )
    all_results['phase1'] = results

    # Phase 2: OA-only
    print("\n" + "=" * 60)
    print("PHASE 2: Fine-tune on OA-only data")
    print("=" * 60)
    model, results = train_phase(
        model, tokenizer, train_data, val_data, config,
        phase=2, output_dir=f"{config.output_dir}/phase2"
    )
    all_results['phase2'] = results

    # Phase 3: Sentence-level only
    print("\n" + "=" * 60)
    print("PHASE 3: Fine-tune on sentence-level data")
    print("=" * 60)
    model, results = train_phase(
        model, tokenizer, train_data, val_data, config,
        phase=3, output_dir=f"{config.output_dir}/phase3"
    )
    all_results['phase3'] = results

    # Save final model
    final_dir = f"{config.output_dir}/final"
    model.save_pretrained(final_dir)
    tokenizer.save_pretrained(final_dir)
    print(f"\nFinal model saved to: {final_dir}")

    # Save training results
    with open(f"{config.output_dir}/training_results.json", 'w') as f:
        json.dump(all_results, f, indent=2, default=str)

    return model, tokenizer


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="Train ByT5 for Akkadian translation")
    parser.add_argument('--model', default='google/byt5-large', help='Model name or path')
    parser.add_argument('--train-file', required=True, help='Training data CSV')
    parser.add_argument('--val-file', required=True, help='Validation data CSV')
    parser.add_argument('--output-dir', default='models/byt5-akkadian', help='Output directory')
    parser.add_argument('--batch-size', type=int, default=4)
    parser.add_argument('--fp16', action='store_true', default=True)
    parser.add_argument('--config', default=None, help='YAML config file')

    args = parser.parse_args()

    if args.config:
        config = TrainingConfig.from_yaml(args.config)
    else:
        config = TrainingConfig(
            model_name=args.model,
            train_file=args.train_file,
            val_file=args.val_file,
            output_dir=args.output_dir,
            batch_size=args.batch_size,
            fp16=args.fp16,
        )

    train(config)
