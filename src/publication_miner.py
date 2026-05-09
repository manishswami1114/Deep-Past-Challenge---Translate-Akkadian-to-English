"""
Mine translations from publications.csv OCR data.

Extracts Akkadian transliteration + English translation pairs
from the OCR output of 880+ academic publications.
"""

import re
import pandas as pd
from pathlib import Path
from src.preprocessing import (
    normalize_transliteration,
    normalize_translation,
    DATA_DIR,
    OUTPUT_DIR,
)


def detect_language(text: str) -> str:
    """Simple language detection based on common words."""
    text_lower = text.lower()

    # English indicators
    en_words = ['the', 'and', 'of', 'to', 'in', 'that', 'is', 'was', 'for', 'he', 'she',
                'has', 'have', 'with', 'his', 'her', 'they', 'which', 'from', 'this',
                'silver', 'seal', 'son', 'tablet', 'merchant', 'textile']

    # German indicators
    de_words = ['der', 'die', 'das', 'und', 'von', 'den', 'des', 'ist', 'ein', 'eine',
                'mit', 'auf', 'für', 'nicht', 'sich', 'auch', 'werden', 'kann']

    # French indicators
    fr_words = ['les', 'des', 'une', 'est', 'dans', 'pour', 'que', 'pas', 'sur',
                'avec', 'cette', 'sont', 'mais', 'aussi']

    # Turkish indicators
    tr_words = ['bir', 'olan', 'için', 'ile', 'olan', 'ise', 'daha', 'sonra']

    en_count = sum(1 for w in en_words if f' {w} ' in f' {text_lower} ')
    de_count = sum(1 for w in de_words if f' {w} ' in f' {text_lower} ')
    fr_count = sum(1 for w in fr_words if f' {w} ' in f' {text_lower} ')
    tr_count = sum(1 for w in tr_words if f' {w} ' in f' {text_lower} ')

    scores = {'en': en_count, 'de': de_count, 'fr': fr_count, 'tr': tr_count}
    best = max(scores, key=scores.get)
    return best if scores[best] >= 2 else 'unknown'


def is_akkadian_transliteration(text: str) -> bool:
    """Check if text looks like Akkadian transliteration."""
    # Must have hyphenated syllables
    if not re.search(r'\b\w+-\w+\b', text):
        return False

    # Must have some diacritical characters or Sumerograms
    has_diacritics = bool(re.search(r'[šṣṭḫáàéèíìúùŠṢṬḪ]', text))
    has_sumerograms = bool(re.search(r'\b[A-Z]{2,}\b', text))

    return has_diacritics or has_sumerograms


def extract_interlinear_pairs(text: str) -> list[dict]:
    """
    Extract transliteration-translation pairs from interlinear format.
    In academic publications, transliterations and translations often appear
    as alternating blocks.
    """
    pairs = []

    # Pattern: numbered lines followed by transliteration then translation
    # e.g., "1 a-na X qí-bi-ma\n  To X, say:\n2 um-ma Y-ma\n  Thus says Y:"
    lines = text.split('\n')

    current_translit = []
    current_translation = []
    in_translit = False

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Line starting with number followed by transliteration
        if re.match(r'^\d+[\'\"]?\s', line):
            content = re.sub(r'^\d+[\'\"]?\s+', '', line)
            if is_akkadian_transliteration(content):
                # Save previous pair if exists
                if current_translit and current_translation:
                    pairs.append({
                        'transliteration': ' '.join(current_translit),
                        'translation': ' '.join(current_translation),
                    })
                    current_translit = []
                    current_translation = []
                current_translit.append(content)
                in_translit = True
            else:
                # This might be a translation line
                if in_translit and current_translit:
                    current_translation.append(content)
                    in_translit = False
        elif in_translit and is_akkadian_transliteration(line):
            current_translit.append(line)
        elif not in_translit and current_translit:
            current_translation.append(line)

    # Save last pair
    if current_translit and current_translation:
        pairs.append({
            'transliteration': ' '.join(current_translit),
            'translation': ' '.join(current_translation),
        })

    return pairs


def extract_block_pairs(text: str) -> list[dict]:
    """
    Extract pairs where transliteration and translation appear as separate blocks,
    often separated by keywords like "Translation:" or "Transliteration:".
    """
    pairs = []

    # Look for labeled blocks
    # Pattern: "Transliteration:" ... "Translation:" ...
    translit_pattern = r'(?:transliteration|text|original)[:.]?\s*\n(.*?)(?=\n\s*(?:translation|rendering|english)[:.]?\s*\n)'
    translation_pattern = r'(?:translation|rendering|english)[:.]?\s*\n(.*?)(?=\n\s*(?:transliteration|text|original|notes|commentary)[:.]?\s*\n|\Z)'

    translit_matches = re.finditer(translit_pattern, text, re.IGNORECASE | re.DOTALL)
    for match in translit_matches:
        translit_text = match.group(1).strip()
        # Find the translation that follows
        remaining = text[match.end():]
        trans_match = re.search(translation_pattern, remaining, re.IGNORECASE | re.DOTALL)
        if trans_match:
            trans_text = trans_match.group(1).strip()
            if is_akkadian_transliteration(translit_text) and len(trans_text) > 10:
                pairs.append({
                    'transliteration': translit_text,
                    'translation': trans_text,
                })

    return pairs


def mine_publications():
    """Main function to mine publications.csv for translation pairs."""
    print("Mining publications.csv for translation pairs...")

    pub_path = DATA_DIR / 'publications.csv'
    if not pub_path.exists():
        print(f"File not found: {pub_path}")
        return pd.DataFrame()

    # Load publications
    pub_df = pd.read_csv(pub_path)
    print(f"Total pages: {len(pub_df)}")

    # Filter to pages with Akkadian content
    if 'has_akkadian' in pub_df.columns:
        akk_pages = pub_df[pub_df['has_akkadian'] == True]
    else:
        akk_pages = pub_df
    print(f"Pages with Akkadian: {len(akk_pages)}")

    all_pairs = []
    pages_with_pairs = 0

    for _, row in akk_pages.iterrows():
        text = str(row.get('page_text', ''))
        if len(text) < 50:
            continue

        # Detect language
        lang = detect_language(text)
        if lang != 'en':
            continue

        # Try interlinear extraction
        interlinear = extract_interlinear_pairs(text)
        if interlinear:
            all_pairs.extend(interlinear)
            pages_with_pairs += 1
            continue

        # Try block extraction
        blocks = extract_block_pairs(text)
        if blocks:
            all_pairs.extend(blocks)
            pages_with_pairs += 1

    print(f"Pages yielding pairs: {pages_with_pairs}")
    print(f"Raw pairs extracted: {len(all_pairs)}")

    if not all_pairs:
        print("No pairs extracted from publications.")
        return pd.DataFrame()

    # Create DataFrame and normalize
    result = pd.DataFrame(all_pairs)
    result['transliteration'] = result['transliteration'].apply(normalize_transliteration)
    result['translation'] = result['translation'].apply(normalize_translation)
    result['source'] = 'publications'

    # Filter: require minimum lengths
    result = result[
        (result['transliteration'].str.len() >= 10) &
        (result['translation'].str.len() >= 10)
    ]

    # Remove duplicates
    result = result.drop_duplicates(subset=['transliteration'])

    print(f"Filtered pairs: {len(result)}")

    # Save
    out_dir = OUTPUT_DIR / 'publications_mined'
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / 'pub_pairs.csv'
    result.to_csv(output_path, index=False)
    print(f"Saved to: {output_path}")

    # Show samples
    if len(result) > 0:
        print("\nSample pairs:")
        for _, row in result.head(3).iterrows():
            print(f"  SRC: {row['transliteration'][:100]}")
            print(f"  TGT: {row['translation'][:100]}")
            print()

    return result


if __name__ == '__main__':
    mine_publications()
