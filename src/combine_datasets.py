"""
Combine all data sources into a unified training dataset with quality-weighted splits.
"""

import json
import pandas as pd
import numpy as np
import sys
from pathlib import Path
from sklearn.model_selection import train_test_split

# Add the project root (parent directory of 'src') to sys.path to allow importing 'src'
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.preprocessing import OUTPUT_DIR


# Sampling weights by source quality
SOURCE_WEIGHTS = {
    'strategy_a': 1.0,        # High quality - direct sentence alignment
    'strategy_b_short': 0.8,  # High quality - short docs kept whole
    'strategy_b_aligned': 0.6, # Medium quality - heuristic alignment
    'strategy_b_doc': 0.5,    # Medium quality - document level
    'strategy_c': 0.7,        # Medium quality - published_texts alignment
    'oracc': 0.4,             # Medium quality - domain mismatch
    'publications': 0.3,      # Low-medium quality - OCR extracted
    'lexicon': 0.1,           # Low quality - word-level only
}


def load_all_sources() -> list[pd.DataFrame]:
    """Load all available data sources."""
    sources = []
    aligned_dir = OUTPUT_DIR / 'sentence_aligned'

    # Strategy A, B, C
    for strategy in ['strategy_a', 'strategy_b', 'strategy_c']:
        path = aligned_dir / f'{strategy}.csv'
        if path.exists():
            df = pd.read_csv(path)
            print(f"  Loaded {strategy}: {len(df)} pairs")
            sources.append(df)

    # ORACC external data
    oracc_path = OUTPUT_DIR / 'oracc' / 'oracc_parallel.csv'
    if oracc_path.exists():
        df = pd.read_csv(oracc_path)
        df['source'] = 'oracc'
        print(f"  Loaded ORACC: {len(df)} pairs")
        sources.append(df)

    # Publications mined data
    pub_path = OUTPUT_DIR / 'publications_mined' / 'pub_pairs.csv'
    if pub_path.exists():
        df = pd.read_csv(pub_path)
        df['source'] = 'publications'
        print(f"  Loaded publications: {len(df)} pairs")
        sources.append(df)

    # Lexicon word pairs
    lex_path = OUTPUT_DIR / 'lexicon_pairs.csv'
    if lex_path.exists():
        df = pd.read_csv(lex_path)
        df['source'] = 'lexicon'
        print(f"  Loaded lexicon: {len(df)} pairs")
        sources.append(df)

    return sources


def create_validation_set(
    strategy_a_df: pd.DataFrame,
    n_val_docs: int = 50,
) -> tuple[pd.DataFrame, set]:
    """
    Create a validation set from Strategy A data (sentence-level from train.csv).
    This mimics test conditions: sentence-level evaluation of known-quality pairs.

    Returns:
        (val_df, val_doc_ids) - validation dataframe and set of document IDs to exclude
    """
    if strategy_a_df is None or len(strategy_a_df) == 0:
        return pd.DataFrame(), set()

    # Get unique document IDs
    doc_ids = strategy_a_df['oare_id'].unique()

    if len(doc_ids) <= n_val_docs:
        # Not enough docs - use 20% of available
        n_val_docs = max(1, len(doc_ids) // 5)

    # Randomly select validation documents
    np.random.seed(42)
    val_doc_ids = set(np.random.choice(doc_ids, size=n_val_docs, replace=False))

    val_df = strategy_a_df[strategy_a_df['oare_id'].isin(val_doc_ids)].copy()
    val_df['source'] = 'validation'

    print(f"  Validation set: {len(val_df)} sentences from {n_val_docs} documents")
    return val_df, val_doc_ids


def combine_and_split():
    """Combine all sources and create train/val splits."""
    print("Combining all data sources...")
    sources = load_all_sources()

    if not sources:
        print("ERROR: No data sources found. Run preprocessing and alignment first.")
        return

    # Combine all sources
    combined = pd.concat(sources, ignore_index=True)

    # Ensure required columns exist
    required_cols = ['transliteration', 'translation', 'source']
    for col in required_cols:
        if col not in combined.columns:
            print(f"ERROR: Missing column '{col}' in combined data")
            return

    # Filter out empty/null entries
    combined = combined.dropna(subset=['transliteration', 'translation'])
    combined = combined[combined['transliteration'].str.strip().str.len() > 0]
    combined = combined[combined['translation'].str.strip().str.len() > 0]

    print(f"\nCombined dataset: {len(combined)} pairs")
    print(f"Source distribution:")
    for source, count in combined['source'].value_counts().items():
        weight = SOURCE_WEIGHTS.get(source, 0.5)
        print(f"  {source}: {count} pairs (weight: {weight})")

    # Create validation set from Strategy A
    strategy_a = combined[combined['source'] == 'strategy_a']
    val_df, val_doc_ids = create_validation_set(strategy_a)

    # Remove validation documents from training data (all strategies)
    if val_doc_ids:
        train_combined = combined[~combined.get('oare_id', pd.Series()).isin(val_doc_ids)]
    else:
        train_combined = combined

    # Add sampling weights
    train_combined = train_combined.copy()
    train_combined['weight'] = train_combined['source'].map(SOURCE_WEIGHTS).fillna(0.5)

    # Save outputs
    out_dir = OUTPUT_DIR / 'combined'
    out_dir.mkdir(parents=True, exist_ok=True)

    train_combined.to_csv(out_dir / 'train_split.csv', index=False)
    if len(val_df) > 0:
        val_df.to_csv(out_dir / 'val_split.csv', index=False)

    # Save all combined (for reference)
    combined.to_csv(out_dir / 'all_combined.csv', index=False)

    # Summary stats
    stats = {
        'total_combined': len(combined),
        'train_split': len(train_combined),
        'val_split': len(val_df),
        'sources': combined['source'].value_counts().to_dict(),
        'avg_transliteration_len': float(train_combined['transliteration'].str.len().mean()),
        'avg_translation_len': float(train_combined['translation'].str.len().mean()),
    }

    with open(out_dir / 'dataset_stats.json', 'w') as f:
        json.dump(stats, f, indent=2)

    print(f"\n=== Dataset Assembly Summary ===")
    print(f"  Training pairs: {len(train_combined)}")
    print(f"  Validation pairs: {len(val_df)}")
    print(f"  Avg transliteration length: {stats['avg_transliteration_len']:.0f} chars")
    print(f"  Avg translation length: {stats['avg_translation_len']:.0f} chars")
    print(f"  Saved to: {out_dir}")

    return train_combined, val_df


if __name__ == '__main__':
    combine_and_split()
