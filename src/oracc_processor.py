"""
ORACC (Open Richly Annotated Cuneiform Corpus) data processor.

Downloads and processes the ORACC Akkadian-English parallel corpus
for use as supplementary training data.
"""

import os
import re
import json
import subprocess
import pandas as pd
from pathlib import Path
from src.preprocessing import normalize_transliteration, normalize_translation, OUTPUT_DIR


ORACC_DIR = OUTPUT_DIR / 'oracc'


def normalize_oracc_transliteration(text: str) -> str:
    """
    Additional normalization specific to ORACC format before standard normalization.
    ORACC uses 'a - mat' style (space-hyphen-space) instead of 'a-mat'.
    """
    if not isinstance(text, str):
        return ''

    # Remove half brackets ⸢ ⸣ (ORACC uses these for partially broken signs)
    text = text.replace('⸢', '').replace('⸣', '')

    # Remove asterisks used for uncertain readings in ORACC
    text = text.replace(' * ', ' ').replace('*', '')

    # ORACC: collapse 'a - mat' (space-hyphen-space) → 'a-mat'
    text = re.sub(r'(\S)\s+-\s+(\S)', r'\1-\2', text)

    # ORACC: 'm ' before names → '{m}'  (masculine determinative)
    text = re.sub(r'\bm\s+(?=[A-Z])', '{m}', text)
    text = re.sub(r'\bm\s+(?=d\s)', '{m}', text)

    # ORACC: 'f ' before names → '{mi}'  (feminine determinative)
    text = re.sub(r'\bf\s+(?=[A-Z])', '{mi}', text)

    # ORACC: 'd + ' or 'd ' before divine names → '{d}'
    text = re.sub(r'\bd\s*\+\s*', '{d}', text)
    text = re.sub(r'\bd\s+(?=[A-Z])', '{d}', text)

    # Clean up multiple spaces
    text = re.sub(r'\s+', ' ', text).strip()

    # Now apply standard normalization
    text = normalize_transliteration(text)

    return text


def download_oracc_from_kaggle():
    """
    Download ORACC dataset from Kaggle.
    Requires kaggle CLI configured with API credentials.
    """
    ORACC_DIR.mkdir(parents=True, exist_ok=True)

    print("Downloading ORACC dataset from Kaggle...")
    try:
        subprocess.run(
            ['kaggle', 'datasets', 'download',
             'manwithacat/oracc-akkadian-english-parallel-corpus',
             '-p', str(ORACC_DIR), '--unzip'],
            check=True,
            capture_output=True,
            text=True,
        )
        print("Download complete!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Kaggle download failed: {e.stderr}")
        return False
    except FileNotFoundError:
        print("Kaggle CLI not found. Install with: pip install kaggle")
        return False


def download_oracc_from_github():
    """
    Download ORACC data from GitHub as fallback.
    """
    ORACC_DIR.mkdir(parents=True, exist_ok=True)

    print("Downloading ORACC dataset from GitHub...")
    try:
        subprocess.run(
            ['git', 'clone', '--depth', '1',
             'https://github.com/veezbo/akkadian_english_corpus.git',
             str(ORACC_DIR / 'github_corpus')],
            check=True,
            capture_output=True,
            text=True,
        )
        print("Download complete!")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"GitHub download failed: {e}")
        return False


def process_kaggle_oracc(data_dir: Path = ORACC_DIR) -> pd.DataFrame:
    """Process ORACC data downloaded from Kaggle."""
    # Look for CSV files in the download directory
    csv_files = list(data_dir.glob('*.csv'))
    if not csv_files:
        csv_files = list(data_dir.glob('**/*.csv'))

    if not csv_files:
        print("No CSV files found in ORACC download directory")
        return pd.DataFrame()

    all_dfs = []
    for csv_file in csv_files:
        try:
            df = pd.read_csv(csv_file)
            print(f"  Loaded {csv_file.name}: {len(df)} rows, columns: {list(df.columns)}")
            all_dfs.append(df)
        except Exception as e:
            print(f"  Error loading {csv_file.name}: {e}")

    if not all_dfs:
        return pd.DataFrame()

    combined = pd.concat(all_dfs, ignore_index=True)

    # Try to find transliteration and translation columns
    # Common column names in ORACC datasets
    translit_cols = ['transliteration', 'akkadian', 'source', 'src', 'input']
    translation_cols = ['translation', 'english', 'target', 'tgt', 'output']

    translit_col = None
    for col in translit_cols:
        if col in combined.columns:
            translit_col = col
            break

    translation_col = None
    for col in translation_cols:
        if col in combined.columns:
            translation_col = col
            break

    if translit_col is None or translation_col is None:
        print(f"Could not identify columns. Available: {list(combined.columns)}")
        # Try first two non-id columns
        non_id_cols = [c for c in combined.columns if c.lower() not in ('id', 'index', 'unnamed: 0')]
        if len(non_id_cols) >= 2:
            translit_col, translation_col = non_id_cols[0], non_id_cols[1]
            print(f"  Using columns: {translit_col} (source), {translation_col} (target)")
        else:
            return pd.DataFrame()

    # Create standardized dataframe with ORACC-specific normalization
    result = pd.DataFrame({
        'transliteration': combined[translit_col].apply(
            lambda x: normalize_oracc_transliteration(str(x)) if pd.notna(x) else ''
        ),
        'translation': combined[translation_col].apply(
            lambda x: normalize_translation(str(x)) if pd.notna(x) else ''
        ),
        'source': 'oracc',
    })

    # Filter out empty pairs
    result = result[
        (result['transliteration'].str.strip().str.len() > 0) &
        (result['translation'].str.strip().str.len() > 0)
    ]

    return result


def process_github_oracc(data_dir: Path = ORACC_DIR / 'github_corpus') -> pd.DataFrame:
    """Process ORACC data from GitHub clone."""
    if not data_dir.exists():
        return pd.DataFrame()

    # Look for JSON or text files with parallel data
    json_files = list(data_dir.glob('**/*.json'))
    tsv_files = list(data_dir.glob('**/*.tsv'))
    txt_files = list(data_dir.glob('**/*.txt'))
    csv_files = list(data_dir.glob('**/*.csv'))

    all_pairs = []

    # Try JSON files
    for jf in json_files:
        try:
            with open(jf) as f:
                data = json.load(f)
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        translit = item.get('transliteration', item.get('source', ''))
                        translation = item.get('translation', item.get('target', ''))
                        if translit and translation:
                            all_pairs.append({
                                'transliteration': normalize_transliteration(str(translit)),
                                'translation': normalize_translation(str(translation)),
                                'source': 'oracc',
                            })
        except Exception:
            pass

    # Try TSV files
    for tf in tsv_files:
        try:
            df = pd.read_csv(tf, sep='\t')
            if len(df.columns) >= 2:
                for _, row in df.iterrows():
                    all_pairs.append({
                        'transliteration': normalize_transliteration(str(row.iloc[0])),
                        'translation': normalize_translation(str(row.iloc[1])),
                        'source': 'oracc',
                    })
        except Exception:
            pass

    # Try CSV files
    for cf in csv_files:
        try:
            df = pd.read_csv(cf)
            processed = process_kaggle_oracc(cf.parent)
            if len(processed) > 0:
                all_pairs.extend(processed.to_dict('records'))
        except Exception:
            pass

    if all_pairs:
        result = pd.DataFrame(all_pairs)
        result = result[
            (result['transliteration'].str.strip().str.len() > 0) &
            (result['translation'].str.strip().str.len() > 0)
        ]
        return result

    return pd.DataFrame()


def download_and_process_oracc() -> pd.DataFrame:
    """Download and process ORACC data from available sources."""
    ORACC_DIR.mkdir(parents=True, exist_ok=True)

    # Try Kaggle first
    result = pd.DataFrame()

    if download_oracc_from_kaggle():
        result = process_kaggle_oracc()

    if len(result) == 0:
        print("Trying GitHub source...")
        if download_oracc_from_github():
            result = process_github_oracc()

    if len(result) > 0:
        output_path = ORACC_DIR / 'oracc_parallel.csv'
        result.to_csv(output_path, index=False)
        print(f"\nORACC data processed: {len(result)} pairs")
        print(f"Saved to: {output_path}")

        # Show sample
        print("\nSample pairs:")
        for _, row in result.head(3).iterrows():
            print(f"  SRC: {row['transliteration'][:80]}...")
            print(f"  TGT: {row['translation'][:80]}...")
            print()
    else:
        print("WARNING: Could not download or process ORACC data.")
        print("You can manually download from:")
        print("  https://www.kaggle.com/datasets/manwithacat/oracc-akkadian-english-parallel-corpus")
        print(f"Place the CSV files in: {ORACC_DIR}")

    return result


if __name__ == '__main__':
    download_and_process_oracc()
