"""
Post-processing pipeline for ByT5 translation outputs.

Handles proper noun normalization, formula consistency,
fragment markers, and generation artifact removal.
"""

import re
import pandas as pd
from pathlib import Path
from src.preprocessing import DATA_DIR


class PostProcessor:
    """Post-process ByT5 translation outputs."""

    def __init__(self, lexicon_path=None):
        self.proper_noun_map = {}
        self.logogram_map = {
            'KÙ.BABBAR': 'silver',
            'KÙ.GI': 'gold',
            'KÙ.AN': 'meteoric iron',
            'DUMU': 'son of',
            'DUMU.MUNUS': 'daughter of',
            'IGI': 'before',
            'KIŠIB': 'seal of',
            'ITU.KAM': 'month',
            'GÍN': 'shekel',
            'TÚG': 'textile',
        }

        if lexicon_path:
            self._load_lexicon(lexicon_path)
        else:
            default_path = DATA_DIR / 'OA_Lexicon_eBL.csv'
            if default_path.exists():
                self._load_lexicon(default_path)

    def _load_lexicon(self, path):
        """Load proper noun mappings from lexicon."""
        try:
            df = pd.read_csv(path)
            # Build proper noun map from PN (person name) and GN (geographic name) entries
            for _, row in df.iterrows():
                word_type = str(row.get('type', ''))
                form = str(row.get('form', ''))
                norm = str(row.get('norm', ''))
                lexeme = str(row.get('lexeme', ''))

                if word_type in ('PN', 'GN', 'DN', 'RN') and form and norm:
                    # Map transliteration form to normalized name
                    self.proper_noun_map[form.lower()] = norm
        except Exception as e:
            print(f"Warning: Could not load lexicon: {e}")

    def remove_repeated_phrases(self, text: str) -> str:
        """Remove immediately repeated phrases (common ByT5 artifact)."""
        # Remove exact duplicate consecutive sentences
        sentences = text.split('. ')
        deduped = []
        for s in sentences:
            if not deduped or s.strip() != deduped[-1].strip():
                deduped.append(s)
        text = '. '.join(deduped)

        # Remove repeated consecutive words (3+ word phrases)
        text = re.sub(r'(\b\w+(?:\s+\w+){2,})\s+\1\b', r'\1', text)

        return text

    def fix_punctuation(self, text: str) -> str:
        """Fix common punctuation issues in generated text."""
        # Fix unclosed quotation marks
        quote_count = text.count('"')
        if quote_count % 2 != 0:
            # Add closing quote at end if needed
            if text.count('"') > 0:
                last_quote = text.rfind('"')
                # Check if last quote is likely an opening quote
                if last_quote > 0 and text[last_quote - 1] in ' (':
                    text += '"'

        # Ensure sentence ends with punctuation
        text = text.strip()
        if text and text[-1] not in '.!?:;':
            text += '.'

        # Fix double periods
        text = text.replace('..', '.')
        # But preserve ellipsis
        text = re.sub(r'\.{4,}', '...', text)

        # Fix space before punctuation
        text = re.sub(r'\s+([.,;:!?])', r'\1', text)

        # Fix missing space after punctuation
        text = re.sub(r'([.,;:!?])([A-Z])', r'\1 \2', text)

        return text

    def handle_fragments(self, source: str, translation: str) -> str:
        """Ensure fragment markers in source are reflected in translation."""
        has_leading_gap = source.strip().startswith(('<gap>', '<big_gap>', '…'))
        has_trailing_gap = source.strip().endswith(('<gap>', '<big_gap>', '…'))

        if has_leading_gap and not translation.startswith('...'):
            translation = '... ' + translation

        if has_trailing_gap and not translation.endswith('...'):
            if translation.endswith('.'):
                translation = translation[:-1] + ' ...'
            else:
                translation += ' ...'

        return translation

    def normalize_numbers(self, text: str) -> str:
        """Ensure consistent number/measurement rendering."""
        # Common measurement terms
        text = re.sub(r'(?i)\bshekels?\b', 'shekels', text)
        text = re.sub(r'(?i)\bminas?\b', 'minas', text)
        text = re.sub(r'(?i)\btalents?\b', 'talents', text)

        # Fix "1/3 of a mina" variations
        text = re.sub(r'1/3\s+(?:of\s+(?:a\s+)?)?mina', '1/3 mina', text)
        text = re.sub(r'2/3\s+(?:of\s+(?:a\s+)?)?mina', '2/3 mina', text)

        return text

    def postprocess(self, translation: str, source: str = '') -> str:
        """Full post-processing pipeline."""
        if not isinstance(translation, str) or not translation.strip():
            return translation

        translation = self.remove_repeated_phrases(translation)
        translation = self.fix_punctuation(translation)
        translation = self.normalize_numbers(translation)

        if source:
            translation = self.handle_fragments(source, translation)

        # Final cleanup
        translation = re.sub(r'\s+', ' ', translation).strip()

        return translation


def postprocess_submission(
    submission_path: str,
    test_path: str,
    output_path: str,
    lexicon_path: str = None,
):
    """Post-process a submission file."""
    processor = PostProcessor(lexicon_path)

    submission_df = pd.read_csv(submission_path)
    test_df = pd.read_csv(test_path)

    # Merge to get source transliterations
    merged = submission_df.merge(test_df[['id', 'transliteration']], on='id', how='left')

    merged['translation'] = merged.apply(
        lambda row: processor.postprocess(
            row['translation'],
            row.get('transliteration', '')
        ),
        axis=1,
    )

    # Save
    merged[['id', 'translation']].to_csv(output_path, index=False)
    print(f"Post-processed submission saved to: {output_path}")


if __name__ == '__main__':
    import sys
    if len(sys.argv) >= 4:
        postprocess_submission(sys.argv[1], sys.argv[2], sys.argv[3])
    else:
        # Test with sample data
        processor = PostProcessor()
        samples = [
            ("Seal of Mannum-balum-Aššur son of Ṣilli-Adad Seal of Mannum-balum-Aššur son of Ṣilli-Adad",
             "KIŠIB ma-nu-ba-lúm-a-šur"),
            ("He has received one textile of ordinary quality",
             "1 TÚG ša qá-tim"),
            ("he did not give you a textile He returned and 9 shekels of Silver",
             "TÚG u-la i-dí-na-ku-um …"),
        ]
        for translation, source in samples:
            result = processor.postprocess(translation, source)
            print(f"  IN:  {translation}")
            print(f"  OUT: {result}")
            print()
