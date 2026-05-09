"""
Create word-level translation pairs from the eBL Dictionary.
These provide basic vocabulary coverage for the model.
"""

import pandas as pd
from pathlib import Path
from src.preprocessing import normalize_transliteration, DATA_DIR, OUTPUT_DIR


def create_lexicon_pairs():
    """Create word-level translation pairs from dictionary."""
    print("Creating lexicon word-level pairs...")

    dict_path = DATA_DIR / 'eBL_Dictionary.csv'
    lex_path = DATA_DIR / 'OA_Lexicon_eBL.csv'

    pairs = []

    # From eBL Dictionary - word → definition pairs
    if dict_path.exists():
        dict_df = pd.read_csv(dict_path)
        print(f"Dictionary entries: {len(dict_df)}")

        for _, row in dict_df.iterrows():
            word = str(row.get('word', ''))
            definition = str(row.get('definition', ''))

            # Skip entries without useful info
            if not word or not definition or word.startswith('-'):
                continue
            if len(word) < 2 or len(definition) < 3:
                continue
            if definition in ('nan', ''):
                continue

            # Clean definition - take first meaning only
            definition = definition.split(';')[0].strip()
            definition = definition.split('(')[0].strip()

            if len(definition) >= 3:
                pairs.append({
                    'transliteration': normalize_transliteration(word),
                    'translation': definition,
                    'source': 'lexicon',
                })

    # From OA Lexicon - add common words with their lexeme meanings
    if lex_path.exists():
        lex_df = pd.read_csv(lex_path)
        print(f"Lexicon entries: {len(lex_df)}")

        # Only use word-type entries (not PN, GN, etc.)
        words = lex_df[lex_df['type'] == 'word']
        print(f"Word-type entries: {len(words)}")

        for _, row in words.iterrows():
            form = str(row.get('form', ''))
            lexeme = str(row.get('lexeme', ''))

            if not form or not lexeme or form == 'nan' or lexeme == 'nan':
                continue

            # Look up the lexeme in the dictionary
            # Just store the mapping for now
            form_normalized = normalize_transliteration(form)
            if len(form_normalized) >= 2 and len(lexeme) >= 2:
                pairs.append({
                    'transliteration': form_normalized,
                    'translation': lexeme,
                    'source': 'lexicon',
                })

    # Deduplicate
    result = pd.DataFrame(pairs)
    if len(result) > 0:
        result = result.drop_duplicates(subset=['transliteration'])

        # Limit to reasonable vocabulary (too many word pairs can bias the model)
        # Keep at most 3000 entries
        if len(result) > 3000:
            result = result.sample(n=3000, random_state=42)

        # Save
        output_path = OUTPUT_DIR / 'lexicon_pairs.csv'
        result.to_csv(output_path, index=False)
        print(f"\nLexicon pairs created: {len(result)}")
        print(f"Saved to: {output_path}")

        # Samples
        print("\nSamples:")
        for _, row in result.head(5).iterrows():
            print(f"  {row['transliteration']} → {row['translation']}")
    else:
        print("No lexicon pairs created.")

    return result


if __name__ == '__main__':
    create_lexicon_pairs()
