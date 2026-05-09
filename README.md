# Deep Past Akkadian Challenge: Translate Akkadian to English

This repository contains the solution for the **Deep Past Initiative: Machine Translation Challenge**, focusing on the translation of the ancient Akkadian language into English. The project uses the **ByT5** (Byte-level T5) architecture, which is particularly suited for morphologically rich and low-resource languages like Akkadian.

## 🚀 Overview

The solution follows a systematic pipeline:
1.  **Data Preparation**: Processing and aligning Akkadian-English pairs from various sources including ORACC, lexicons, and competition data.
2.  **Training**: Fine-tuning a `google/byt5-large` (or `byt5-base`) model on the processed dataset.
3.  **Inference**: Running the fine-tuned model on the competition test set to generate translations for submission.

## 📁 Repository Structure

```text
.
├── configs/                # Hyperparameter and environment configurations
├── data/                   # Processed datasets, proper noun dictionaries, and CSVs
├── data_external/          # External resources (ORACC, etc.)
├── docs/                   # Documentation and research papers
├── models/                 # Model checkpoints and saved weights
├── notebooks/              # Jupyter notebooks for interactive experimentation
│   ├── 01_data_preparation.ipynb
│   ├── 02_model_training.ipynb
│   ├── 03_inference_submission.ipynb
│   └── ... (additional Kaggle-specific notebooks)
├── scripts/                # Standalone Python scripts for training and inference
├── src/                    # Core source code modules
│   ├── oracc_processor.py  # Data extraction from ORACC
│   ├── preprocessing.py    # Text cleaning and tokenization
│   └── train_byt5.py       # Main training logic
├── requirements.txt        # Python dependencies
└── README.md               # Project documentation
```

## 🛠️ Installation

1.  Clone the repository:
    ```bash
    git clone https://github.com/manishswami1114/Deep-Past-Challenge---Translate-Akkadian-to-English.git
    cd Deep-Past-Challenge---Translate-Akkadian-to-English
    ```

2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## 📈 Workflow

### 1. Data Preparation
Run the data preparation scripts or follow `notebooks/01_data_preparation.ipynb` to generate the combined training and validation splits.

### 2. Training
Fine-tune the model using `scripts/train_byt5_v2.py` or the Kaggle training notebooks. The solution is optimized for **H100** or **P100** accelerators.

### 3. Inference
Generate translations for the test set using `scripts/infer_byt5_v2.py` or `notebooks/03_inference_submission.ipynb`.

## 📜 Key Research & Insights
We have explored various challenges in Akkadian translation, including:
-   **Metric Trap**: Deconstructing flaws in evaluation metrics for ancient languages.
-   **Transliteration Complexity**: Handling the nuances of Akkadian transliteration styles.

Detailed discussions can be found in the `docs/` folder.

## 🏆 Submission
Instructions for Kaggle submission are provided in `docs/KAGGLE_INSTRUCTIONS.md`.

---
*Developed for the Deep Past Initiative Challenge.*
