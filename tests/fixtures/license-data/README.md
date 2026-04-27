# License Matching Test Dataset

This directory contains 200 JSON fixtures used to benchmark and evaluate the accuracy of the `licenseid` matcher.

## Dataset Composition
- **100 Popular Licenses**: Frequently used licenses (e.g., GPL variants, Apache, MIT, BSD, CC).
- **50 Confusing Licenses**: Licenses chosen because they share common stems/prefixes with popular licenses, making them difficult to distinguish without precision ranking.
- **50 Rare Licenses**: A random selection from the broader SPDX list to ensure long-tail coverage.

## Fixture Format
Each `.json` file is named after its `license_id` and contains:
- `license_text`: The verbatim text fetched from the official SPDX License List repository.
- `license_id`: The correct SPDX ID.
- `close_license_ids`: A list of IDs that are closely related (e.g., sharing the same stem like `GPL-`).
- `license_text_distorted_NN`: Programmatically distorted variants of the original text.
- Metadata flags: `is_high_usage`, `is_osi_approved`, `is_fsf_libre`, `is_spdx`.

## Distortion Heuristics (01, 05, 10, 20, 40)
The distortion rates represent the approximate percentage of text elements (words/paragraphs) that have been mutated. The operations randomly applied include:
1. **Word Dropping**: Simulating copy-paste errors by randomly deleting words.
2. **Typos**: Character swaps within words to simulate human error or OCR glitches.
3. **Punctuation Dropping**: Stripping non-alphanumeric characters.
4. **Structural Dropping**: For rates >= 5%, occasionally dropping entire paragraphs.
5. **Foreign Text Injection**: Inserting sentences in languages other than the original text language to simulate mixed-language documents or preamble metadata.
6. **Whitespace Mutatation**: Injecting random newlines or double spaces.

## Updating the Dataset
To regenerate these fixtures, run the script from the root directory:
```bash
python scripts/generate_dataset.py
```
