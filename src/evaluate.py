"""
Evaluation pipeline for Deep Past Challenge.

Competition metric: Geometric mean of BLEU and chrF++ scores,
with each score's sufficient statistics aggregated across the entire corpus
(micro-averaged). Uses SacreBLEU library.
"""

import math
import json
import pandas as pd
import sacrebleu
from pathlib import Path
from typing import Optional


def compute_bleu(predictions: list[str], references: list[str]) -> float:
    """Compute corpus-level BLEU score using SacreBLEU."""
    bleu = sacrebleu.corpus_bleu(predictions, [references])
    return bleu.score


def compute_chrf(predictions: list[str], references: list[str]) -> float:
    """Compute corpus-level chrF++ score using SacreBLEU (word_order=2)."""
    chrf = sacrebleu.corpus_chrf(predictions, [references], word_order=2)
    return chrf.score


def compute_competition_metric(predictions: list[str], references: list[str]) -> dict:
    """
    Compute the competition metric: geometric mean of BLEU and chrF++.

    Returns a dict with individual scores and the final metric.
    """
    bleu_score = compute_bleu(predictions, references)
    chrf_score = compute_chrf(predictions, references)

    # Geometric mean
    if bleu_score <= 0 or chrf_score <= 0:
        geo_mean = 0.0
    else:
        geo_mean = math.sqrt(bleu_score * chrf_score)

    return {
        'bleu': bleu_score,
        'chrf_pp': chrf_score,
        'geo_mean': geo_mean,
    }


def evaluate_predictions(
    predictions_file: str,
    references_file: str,
    output_file: Optional[str] = None
) -> dict:
    """
    Evaluate a predictions file against references.

    Args:
        predictions_file: CSV with columns 'id', 'translation'
        references_file: CSV with columns 'id', 'translation'
        output_file: Optional path to save evaluation results as JSON
    """
    pred_df = pd.read_csv(predictions_file)
    ref_df = pd.read_csv(references_file)

    # Ensure alignment by id
    merged = ref_df.merge(pred_df, on='id', suffixes=('_ref', '_pred'))

    predictions = merged['translation_pred'].fillna('').tolist()
    references = merged['translation_ref'].fillna('').tolist()

    results = compute_competition_metric(predictions, references)

    print(f"Evaluation Results:")
    print(f"  BLEU:    {results['bleu']:.2f}")
    print(f"  chrF++:  {results['chrf_pp']:.2f}")
    print(f"  GeoMean: {results['geo_mean']:.2f}")

    if output_file:
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)

    return results


def evaluate_lists(predictions: list[str], references: list[str]) -> dict:
    """Quick evaluation from lists of strings."""
    results = compute_competition_metric(predictions, references)
    print(f"BLEU: {results['bleu']:.2f} | chrF++: {results['chrf_pp']:.2f} | GeoMean: {results['geo_mean']:.2f}")
    return results


def detailed_evaluation(
    predictions: list[str],
    references: list[str],
    source_texts: Optional[list[str]] = None,
    metadata: Optional[pd.DataFrame] = None,
) -> dict:
    """
    Detailed evaluation with per-length-bucket and per-source analysis.
    """
    overall = compute_competition_metric(predictions, references)
    results = {'overall': overall}

    if source_texts:
        # Per-length-bucket analysis
        lengths = [len(s) for s in source_texts]
        buckets = [
            ('short', 0, 100),
            ('medium', 100, 300),
            ('long', 300, 600),
            ('very_long', 600, float('inf')),
        ]

        results['by_length'] = {}
        for name, lo, hi in buckets:
            indices = [i for i, l in enumerate(lengths) if lo <= l < hi]
            if indices:
                bucket_preds = [predictions[i] for i in indices]
                bucket_refs = [references[i] for i in indices]
                bucket_results = compute_competition_metric(bucket_preds, bucket_refs)
                bucket_results['count'] = len(indices)
                results['by_length'][name] = bucket_results

    if metadata is not None and 'source' in metadata.columns:
        # Per-source analysis
        results['by_source'] = {}
        for source in metadata['source'].unique():
            indices = metadata[metadata['source'] == source].index.tolist()
            if indices:
                src_preds = [predictions[i] for i in indices if i < len(predictions)]
                src_refs = [references[i] for i in indices if i < len(references)]
                if src_preds and src_refs:
                    src_results = compute_competition_metric(src_preds, src_refs)
                    src_results['count'] = len(src_preds)
                    results['by_source'][source] = src_results

    return results


if __name__ == '__main__':
    import sys

    if len(sys.argv) >= 3:
        evaluate_predictions(sys.argv[1], sys.argv[2],
                           sys.argv[3] if len(sys.argv) > 3 else None)
    else:
        # Quick test with sample data
        preds = [
            "Seal of Mannum-balum-Aššur son of Ṣilli-Adad.",
            "He has received one textile of ordinary quality.",
        ]
        refs = [
            "Seal of Mannum-balum-Aššur son of Ṣilli-Adad, seal of Šu-Illil.",
            "Itūr-ilī has received one textile of ordinary quality.",
        ]
        results = evaluate_lists(preds, refs)
        print(f"\nDetailed: {json.dumps(results, indent=2)}")
