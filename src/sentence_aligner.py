"""
Sentence-level alignment for Deep Past Challenge.

Converts document-level training data into sentence-level pairs that match
the test data format. Implements three strategies:

Strategy A: Direct alignment using Sentences_Oare_FirstWord_LinNum.csv
Strategy B: Heuristic document splitting for non-overlapping documents
Strategy C: Sentences file + published_texts.csv for additional pairs
"""

import re
import json
import pandas as pd
import numpy as np
from pathlib import Path
from difflib import SequenceMatcher
from src.preprocessing import (
    normalize_transliteration,
    normalize_translation,
    DATA_DIR,
    OUTPUT_DIR,
)


def fuzzy_find_word(text: str, word: str, start_pos: int = 0) -> int:
    """
    Find the position of a word in text, allowing for fuzzy matching.
    Returns the start index or -1 if not found.
    """
    # Exact match first
    idx = text.find(word, start_pos)
    if idx >= 0:
        return idx

    # Try without subscripts (₁₂₃₄₅₆₇₈₉ -> plain)
    word_plain = re.sub(r'[₁₂₃₄₅₆₇₈₉₀]', '', word)
    text_plain = re.sub(r'[₁₂₃₄₅₆₇₈₉₀]', '', text)
    idx = text_plain.find(word_plain, start_pos)
    if idx >= 0:
        return idx

    # Try case-insensitive
    idx_lower = text.lower().find(word.lower(), start_pos)
    if idx_lower >= 0:
        return idx_lower

    # Try matching just the first few syllables
    syllables = word.split('-')
    if len(syllables) >= 2:
        prefix = '-'.join(syllables[:2])
        idx = text.find(prefix, start_pos)
        if idx >= 0:
            return idx

    return -1


def split_document_by_sentences(
    transliteration: str,
    sentences_info: list[dict],
) -> list[dict]:
    """
    Split a document transliteration into sentence-level segments
    using first_word_spelling and line_number from the Sentences file.

    Args:
        transliteration: Full document transliteration
        sentences_info: List of dicts with keys:
            - first_word_spelling: first word of the sentence
            - translation: English translation
            - sentence_obj_in_text: position ordering
            - line_number: line number in document

    Returns:
        List of dicts with 'transliteration' and 'translation' keys
    """
    if not sentences_info or not transliteration:
        return []

    # Sort sentences by their position in the document
    sentences_info = sorted(sentences_info, key=lambda x: int(x.get('sentence_obj_in_text', 0)))

    # Find sentence boundaries in the transliteration
    boundaries = []
    search_start = 0

    for sent in sentences_info:
        first_word = sent.get('first_word_spelling', '')
        if not first_word:
            # Try using first_word_transcription as fallback
            first_word = sent.get('first_word_transcription', '')

        if not first_word:
            boundaries.append(-1)
            continue

        # Normalize the first word the same way we normalize transliterations
        first_word_norm = normalize_transliteration(first_word)

        pos = fuzzy_find_word(transliteration, first_word_norm, search_start)
        if pos >= 0:
            boundaries.append(pos)
            search_start = pos + 1
        else:
            # Try from the beginning (in case sentences are out of order)
            pos = fuzzy_find_word(transliteration, first_word_norm, 0)
            if pos >= 0:
                boundaries.append(pos)
            else:
                boundaries.append(-1)

    # Extract sentence-level transliterations
    result = []
    for i, sent in enumerate(sentences_info):
        translation = sent.get('translation', '')
        if not translation or not isinstance(translation, str):
            continue

        start = boundaries[i]
        if start < 0:
            continue

        # End is the start of the next sentence, or end of document
        end = len(transliteration)
        for j in range(i + 1, len(boundaries)):
            if boundaries[j] >= 0:
                end = boundaries[j]
                break

        segment = transliteration[start:end].strip()
        if segment:
            result.append({
                'transliteration': segment,
                'translation': translation.strip(),
                'source': 'strategy_a',
            })

    return result


def strategy_a_alignment(
    train_df: pd.DataFrame,
    sentences_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Strategy A: Direct alignment using Sentences file.
    Match train.csv documents with Sentences file by text_uuid/oare_id.
    """
    print("Strategy A: Direct sentence alignment...")

    # Find overlapping documents
    train_ids = set(train_df['oare_id'].values)
    sent_uuids = set(sentences_df['text_uuid'].values)
    overlap = train_ids & sent_uuids

    print(f"  Train documents: {len(train_ids)}")
    print(f"  Sentences documents: {len(sent_uuids)}")
    print(f"  Overlap: {len(overlap)}")

    all_pairs = []
    success_count = 0

    for doc_id in overlap:
        # Get document transliteration from train.csv
        doc_row = train_df[train_df['oare_id'] == doc_id].iloc[0]
        transliteration = doc_row['transliteration']

        # Get sentences for this document
        doc_sentences = sentences_df[sentences_df['text_uuid'] == doc_id]
        sentences_info = doc_sentences.to_dict('records')

        # Split document into sentence-level pairs
        pairs = split_document_by_sentences(transliteration, sentences_info)

        if pairs:
            success_count += 1
            for pair in pairs:
                pair['oare_id'] = doc_id
            all_pairs.extend(pairs)

    result_df = pd.DataFrame(all_pairs)
    print(f"  Successfully split: {success_count}/{len(overlap)} documents")
    print(f"  Total sentence pairs: {len(result_df)}")
    return result_df


def heuristic_split_transliteration(text: str) -> list[str]:
    """
    Heuristically split a transliteration into sentence-like segments.
    Uses common Akkadian sentence boundary patterns.
    """
    if not text or len(text) < 20:
        return [text] if text else []

    # Common sentence-starting patterns in Old Assyrian
    # These typically start new clauses/sentences
    boundary_patterns = [
        r'\bum-ma\b',         # "Thus says..." (speech formula)
        r'\bKIŠIB\b',         # "Seal of..." (seal formula)
        r'\bIGI\b',           # "Before..." (witness formula)
        r'\bšu-ma\b',         # "If..." (conditional)
        r'\ba-na\b(?=\s+\d)', # "For/To..." followed by number (payment)
    ]

    # Find all potential boundaries
    splits = [0]
    for pattern in boundary_patterns:
        for m in re.finditer(pattern, text):
            pos = m.start()
            # Don't split at the very beginning
            if pos > 20 and pos not in splits:
                splits.append(pos)

    splits.sort()
    splits.append(len(text))

    # Extract segments
    segments = []
    for i in range(len(splits) - 1):
        segment = text[splits[i]:splits[i+1]].strip()
        if segment:
            segments.append(segment)

    # If no splits found, return the whole text as one segment
    if not segments:
        segments = [text]

    return segments


def heuristic_split_translation(text: str) -> list[str]:
    """Split English translation into sentences at period boundaries."""
    if not text:
        return []

    # Split at periods followed by space and capital letter
    # But not at abbreviations or numbers
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)

    # Filter out very short fragments
    sentences = [s.strip() for s in sentences if len(s.strip()) > 5]

    return sentences


def strategy_b_heuristic_split(
    train_df: pd.DataFrame,
    exclude_ids: set,
) -> pd.DataFrame:
    """
    Strategy B: Heuristic document splitting for documents NOT in Sentences file.
    """
    print("Strategy B: Heuristic sentence splitting...")

    # Get documents not in the Sentences file
    remaining_df = train_df[~train_df['oare_id'].isin(exclude_ids)]
    print(f"  Documents to split: {len(remaining_df)}")

    all_pairs = []

    for _, row in remaining_df.iterrows():
        translit = row['transliteration']
        translation = row['translation']

        # For short documents, keep as single pair
        if len(translit) < 150:
            all_pairs.append({
                'transliteration': translit,
                'translation': translation,
                'source': 'strategy_b_short',
                'oare_id': row['oare_id'],
            })
            continue

        # Split both sides
        translit_segments = heuristic_split_transliteration(translit)
        translation_sentences = heuristic_split_translation(translation)

        if len(translit_segments) == 1 or len(translation_sentences) == 1:
            # Can't align - keep as document-level pair
            all_pairs.append({
                'transliteration': translit,
                'translation': translation,
                'source': 'strategy_b_doc',
                'oare_id': row['oare_id'],
            })
            continue

        # Try to align segments by count
        if len(translit_segments) == len(translation_sentences):
            # Perfect alignment by count
            for t, e in zip(translit_segments, translation_sentences):
                all_pairs.append({
                    'transliteration': t,
                    'translation': e,
                    'source': 'strategy_b_aligned',
                    'oare_id': row['oare_id'],
                })
        else:
            # Can't align cleanly - keep as document-level
            all_pairs.append({
                'transliteration': translit,
                'translation': translation,
                'source': 'strategy_b_doc',
                'oare_id': row['oare_id'],
            })

    result_df = pd.DataFrame(all_pairs)
    source_counts = result_df['source'].value_counts()
    print(f"  Total pairs: {len(result_df)}")
    for src, count in source_counts.items():
        print(f"    {src}: {count}")
    return result_df


def strategy_c_published_texts(
    published_df: pd.DataFrame,
    sentences_df: pd.DataFrame,
    exclude_ids: set,
) -> pd.DataFrame:
    """
    Strategy C: Use Sentences file translations + published_texts.csv transliterations
    for documents that are in both but NOT in train.csv.
    """
    print("Strategy C: Sentences + published_texts alignment...")

    # Find published_texts that are in Sentences but not in train
    pub_ids = set(published_df['oare_id'].values)
    sent_uuids = set(sentences_df['text_uuid'].values)
    overlap = (pub_ids & sent_uuids) - exclude_ids

    print(f"  Published texts in Sentences (excl. train): {len(overlap)}")

    all_pairs = []
    success_count = 0

    for doc_id in overlap:
        # Get transliteration from published_texts
        pub_row = published_df[published_df['oare_id'] == doc_id]
        if pub_row.empty:
            continue
        pub_row = pub_row.iloc[0]

        # Use normalized transliteration
        transliteration = pub_row.get('transliteration_normalized',
                                       pub_row.get('transliteration', ''))
        if not isinstance(transliteration, str) or not transliteration.strip():
            continue

        # Normalize it
        transliteration = normalize_transliteration(transliteration)

        # Get sentences for this document
        doc_sentences = sentences_df[sentences_df['text_uuid'] == doc_id]
        sentences_info = doc_sentences.to_dict('records')

        # Split document into sentence-level pairs
        pairs = split_document_by_sentences(transliteration, sentences_info)

        if pairs:
            success_count += 1
            for pair in pairs:
                pair['oare_id'] = doc_id
                pair['source'] = 'strategy_c'
            all_pairs.extend(pairs)

    result_df = pd.DataFrame(all_pairs)
    print(f"  Successfully split: {success_count}/{len(overlap)} documents")
    print(f"  Total sentence pairs: {len(result_df)}")
    return result_df


def run_sentence_alignment():
    """Run all sentence alignment strategies and save results."""
    # Load processed data
    print("Loading data...")
    train_df = pd.read_csv(OUTPUT_DIR / 'train_processed.csv')
    sentences_df = pd.read_csv(OUTPUT_DIR / 'sentences_processed.csv')
    published_df = pd.read_csv(OUTPUT_DIR / 'published_texts_processed.csv')

    # Strategy A
    strategy_a_df = strategy_a_alignment(train_df, sentences_df)

    # IDs used in Strategy A
    a_ids = set(strategy_a_df['oare_id'].unique()) if len(strategy_a_df) > 0 else set()
    train_ids = set(train_df['oare_id'].values)

    # Strategy B
    strategy_b_df = strategy_b_heuristic_split(train_df, a_ids)

    # Strategy C
    strategy_c_df = strategy_c_published_texts(published_df, sentences_df, train_ids)

    # Save individual results
    out_dir = OUTPUT_DIR / 'sentence_aligned'
    out_dir.mkdir(parents=True, exist_ok=True)

    if len(strategy_a_df) > 0:
        strategy_a_df.to_csv(out_dir / 'strategy_a.csv', index=False)
    if len(strategy_b_df) > 0:
        strategy_b_df.to_csv(out_dir / 'strategy_b.csv', index=False)
    if len(strategy_c_df) > 0:
        strategy_c_df.to_csv(out_dir / 'strategy_c.csv', index=False)

    # Summary
    total = len(strategy_a_df) + len(strategy_b_df) + len(strategy_c_df)
    print(f"\n=== Sentence Alignment Summary ===")
    print(f"  Strategy A (direct): {len(strategy_a_df)} pairs")
    print(f"  Strategy B (heuristic): {len(strategy_b_df)} pairs")
    print(f"  Strategy C (pub_texts): {len(strategy_c_df)} pairs")
    print(f"  TOTAL: {total} pairs")

    # Save summary stats
    stats = {
        'strategy_a': len(strategy_a_df),
        'strategy_b': len(strategy_b_df),
        'strategy_c': len(strategy_c_df),
        'total': total,
    }
    with open(out_dir / 'alignment_report.json', 'w') as f:
        json.dump(stats, f, indent=2)

    return strategy_a_df, strategy_b_df, strategy_c_df


if __name__ == '__main__':
    run_sentence_alignment()
