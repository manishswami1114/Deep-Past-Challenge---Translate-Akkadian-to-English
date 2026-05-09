"""
Preprocessing pipeline for Deep Past Challenge - Akkadian to English Translation.

Normalizes transliterations and translations following competition formatting
suggestions and ensuring consistency across train, test, published_texts, and
external data sources.
"""

import re
import unicodedata
import pandas as pd
from pathlib import Path


# --- Transliteration Normalization ---

def normalize_h_characters(text: str) -> str:
    """Normalize Ḫ/ḫ to H/h (test data uses H/h only)."""
    text = text.replace('Ḫ', 'H').replace('ḫ', 'h')
    return text


def normalize_determinatives(text: str) -> str:
    """Unify determinative notation to curly bracket form {x}."""
    # Handle superscript determinatives written as (d), (ki), (m), (mi), etc.
    # Pattern: word immediately preceded/followed by (determinative)
    # Common determinatives from competition docs
    determinatives = [
        'd', 'ki', 'lu₂', 'e₂', 'uru', 'kur', 'mi', 'm',
        'geš', 'ĝeš', 'tug₂', 'dub', 'id₂', 'mušen',
        'na₄', 'kuš', 'u₂', 'mul', 'f',
        # uppercase variants
        'D', 'KI', 'LÚ', 'É', 'URU', 'KUR', 'MI', 'M',
        'GEŠ', 'ĜEŠ', 'TÚG', 'DUB', 'ÍD', 'MUŠEN',
        'NA₄', 'KUŠ', 'Ú', 'MUL', 'F',
    ]

    # Convert parenthesized determinatives to curly brackets
    # e.g., (d)UTU -> {d}UTU, a-lim(ki) -> a-lim{ki}
    for det in determinatives:
        # Before a word: (d)word -> {d}word
        text = text.replace(f'({det})', f'{{{det}}}')

    return text


def normalize_gap_markers(text: str) -> str:
    """Standardize break/gap markers — v3: unified to <gap> only."""
    # All gap types → <gap> (v3 test data uses <gap> only, no <big_gap>)
    text = text.replace('{large break}', '<gap>')
    text = re.sub(r'\[…\s*…\]', '<gap>', text)
    text = re.sub(r'\[\.\.\.\s*\.\.\.\]', '<gap>', text)
    text = re.sub(r'\[…\]', '<gap>', text)
    text = re.sub(r'\[\.\.\.\]', '<gap>', text)
    text = text.replace('<big_gap>', '<gap>')

    # Single sign breaks
    text = re.sub(r'\[x\]', '<gap>', text)

    # Standalone ellipsis → <gap>
    text = re.sub(r'\.{3,}|…+', '<gap>', text)

    # Deduplicate sequential gaps: <gap> <gap> → <gap>
    text = re.sub(r'(<gap>[\s\-]*){2,}', '<gap> ', text)

    return text


def remove_scribal_notations(text: str) -> str:
    """Remove modern scribal notations that don't affect meaning."""
    # Remove certain reading marker (!)
    text = re.sub(r'!(?=[^=]|$)', '', text)

    # Remove uncertain reading marker (?) - but not in other contexts
    # Only remove ? that's attached to a word (not standalone question marks)
    text = re.sub(r'(?<=\w)\?', '', text)

    # Remove line divider (/)
    # Be careful: forward slash between words is a line divider
    # but // might be something else
    text = re.sub(r'(?<!\/)\/(?!\/)', ' ', text)

    # Remove word divider (: or . when used as divider, not decimal)
    # The colon as word divider is context-specific
    # For now, only remove standalone colons between words
    text = re.sub(r'\s:\s', ' ', text)

    # Remove half brackets ˹ ˺ (partially broken signs)
    text = text.replace('˹', '').replace('˺', '')

    # Remove square brackets but keep content: [WORD] -> WORD
    # But preserve <gap> and <big_gap> markers
    text = re.sub(r'\[([^\]]*?)\]', lambda m: m.group(1) if m.group(1) not in ['x'] else '<gap>', text)

    # Handle scribal insertions: <text> -> text (keep the text, remove brackets)
    # But preserve <gap> and <big_gap>
    text = re.sub(r'<(?!gap|big_gap)([^>]+)>', r'\1', text)

    # Remove double angle brackets (erroneous signs): <<text>> -> remove
    text = re.sub(r'<<[^>]*>>', '', text)

    return text


def normalize_fractions(text: str) -> str:
    """Normalize fractions to Unicode chars (v3 test uses Unicode only)."""
    # Decimal → Unicode fractions
    text = re.sub(r'0\.3333\d*', '⅓', text)
    text = re.sub(r'0\.6666\d*', '⅔', text)
    text = re.sub(r'0\.1666\d*', '⅙', text)
    text = re.sub(r'0\.8333\d*', '⅚', text)
    # Slash fractions → Unicode
    FRAC_MAP = {'1/3': '⅓', '2/3': '⅔', '1/6': '⅙', '5/6': '⅚',
                '1/2': '½', '1/4': '¼', '3/4': '¾'}
    for frac, uni in FRAC_MAP.items():
        text = text.replace(frac, uni)
    # Decimal halves
    text = re.sub(r'(?<!\d)0\.5(?!\d)', '½', text)
    text = re.sub(r'(\d+)\.5\b', lambda m: f"{m.group(1)}½", text)
    text = re.sub(r'(?<!\d)0\.25(?!\d)', '¼', text)
    text = re.sub(r'(?<!\d)0\.75(?!\d)', '¾', text)
    return text


def normalize_whitespace(text: str) -> str:
    """Clean up whitespace."""
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def normalize_transliteration(text: str) -> str:
    """
    Full normalization pipeline for Akkadian transliterations.
    Applied to train, test, published_texts, and external data.
    """
    if not isinstance(text, str) or not text.strip():
        return text

    # Unicode NFC normalization first
    text = unicodedata.normalize('NFC', text)

    # Apply normalization steps in order
    text = normalize_h_characters(text)
    text = normalize_determinatives(text)
    text = normalize_gap_markers(text)
    text = remove_scribal_notations(text)
    text = normalize_fractions(text)
    text = normalize_whitespace(text)

    return text


# --- Translation Normalization ---

def normalize_quotation_marks(text: str) -> str:
    """Standardize quotation marks in English translations."""
    # German-style quotes
    text = text.replace('„', '"').replace('"', '"').replace('"', '"')
    # Single curly quotes
    text = text.replace('\u2018', "'").replace('\u2019', "'")
    # Double curly quotes
    text = text.replace('\u201C', '"').replace('\u201D', '"')
    return text


def normalize_translation(text: str) -> str:
    """
    Normalize English translations — v3 comprehensive rules.
    """
    if not isinstance(text, str) or not text.strip():
        return text

    # Unicode NFC normalization
    text = unicodedata.normalize('NFC', text)

    # PN → <gap> (Veenhof AKT 8 convention)
    text = re.sub(r'\bPN\b', '<gap>', text)

    # ḫ/Ḫ → h/H in translations too
    text = text.replace('ḫ', 'h').replace('Ḫ', 'H')

    # Gap unification: <big_gap> → <gap>
    text = text.replace('<big_gap>', '<gap>')
    text = re.sub(r'\.{3,}|…+', '<gap>', text)
    text = re.sub(r'(<gap>[\s\-]*){2,}', '<gap> ', text)

    # Remove annotations: (fem), (plur), (sing), (plural), (?), (!)
    text = re.sub(r'\s*\((fem|plur|pl|sing|singular|plural)\.?\s*\w*\)', '', text, flags=re.I)
    text = re.sub(r'\s*\([?!]\)', '', text)

    # Fractions → Unicode (BEFORE any char removal!)
    text = normalize_fractions(text)

    # Remove orphan brackets (protect gaps first)
    text = text.replace('<gap>', '\x00GAP\x00')
    text = re.sub(r'\[([^\]]*)\]', r'\1', text)
    text = re.sub(r'<<[^>]*>>', '', text)
    text = text.replace('\x00GAP\x00', '<gap>')

    # Normalize quotes
    text = normalize_quotation_marks(text)

    # Gap spacing
    text = re.sub(r'(?<![- ])<gap>(?![- ])', ' <gap> ', text)

    # Clean whitespace
    text = normalize_whitespace(text)

    return text


# --- File Processing ---

DATA_DIR = Path(__file__).parent.parent / 'data' / 'deep-past-initiative-machine-translation'
OUTPUT_DIR = Path(__file__).parent.parent / 'data_processed'


def process_train_csv() -> pd.DataFrame:
    """Load and normalize train.csv."""
    df = pd.read_csv(DATA_DIR / 'train.csv')
    df['transliteration_orig'] = df['transliteration']
    df['translation_orig'] = df['translation']
    df['transliteration'] = df['transliteration'].apply(normalize_transliteration)
    df['translation'] = df['translation'].apply(normalize_translation)
    return df


def process_test_csv() -> pd.DataFrame:
    """Load and normalize test.csv."""
    df = pd.read_csv(DATA_DIR / 'test.csv')
    df['transliteration_orig'] = df['transliteration']
    df['transliteration'] = df['transliteration'].apply(normalize_transliteration)
    return df


def process_published_texts() -> pd.DataFrame:
    """Load and normalize published_texts.csv."""
    df = pd.read_csv(DATA_DIR / 'published_texts.csv')
    # Use the cleaned transliteration column
    df['transliteration_normalized'] = df['transliteration'].apply(
        lambda x: normalize_transliteration(x) if isinstance(x, str) else x
    )
    return df


def process_sentences_file() -> pd.DataFrame:
    """Load and normalize Sentences_Oare_FirstWord_LinNum.csv."""
    df = pd.read_csv(DATA_DIR / 'Sentences_Oare_FirstWord_LinNum.csv')
    # Normalize translations
    df['translation'] = df['translation'].apply(
        lambda x: normalize_translation(x) if isinstance(x, str) else x
    )
    return df


def load_lexicon() -> pd.DataFrame:
    """Load the OA Lexicon."""
    return pd.read_csv(DATA_DIR / 'OA_Lexicon_eBL.csv')


def load_dictionary() -> pd.DataFrame:
    """Load the eBL Dictionary."""
    return pd.read_csv(DATA_DIR / 'eBL_Dictionary.csv')


def run_preprocessing():
    """Run the full preprocessing pipeline and save results."""
    print("Processing train.csv...")
    train_df = process_train_csv()

    print("Processing test.csv...")
    test_df = process_test_csv()

    print("Processing published_texts.csv...")
    pub_df = process_published_texts()

    print("Processing Sentences file...")
    sent_df = process_sentences_file()

    # Save processed files
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    train_df.to_csv(OUTPUT_DIR / 'train_processed.csv', index=False)
    test_df.to_csv(OUTPUT_DIR / 'test_processed.csv', index=False)
    pub_df.to_csv(OUTPUT_DIR / 'published_texts_processed.csv', index=False)
    sent_df.to_csv(OUTPUT_DIR / 'sentences_processed.csv', index=False)

    # Print stats
    print(f"\nPreprocessing complete:")
    print(f"  Train: {len(train_df)} documents")
    print(f"  Test: {len(test_df)} sentences")
    print(f"  Published texts: {len(pub_df)} documents")
    print(f"  Sentences: {len(sent_df)} sentences")

    # Show sample normalizations
    print(f"\nSample train transliteration normalization:")
    for i in range(min(3, len(train_df))):
        orig = train_df.iloc[i]['transliteration_orig']
        norm = train_df.iloc[i]['transliteration']
        if orig != norm:
            print(f"  ORIG: {orig[:100]}...")
            print(f"  NORM: {norm[:100]}...")
            print()

    return train_df, test_df, pub_df, sent_df


if __name__ == '__main__':
    run_preprocessing()
