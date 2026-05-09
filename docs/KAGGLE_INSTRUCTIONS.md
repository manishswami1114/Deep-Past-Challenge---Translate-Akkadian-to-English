# Kaggle Upload & Submission Instructions

## Overview

The solution has two phases:
1. **Training** (Kaggle notebook with H100) → produces fine-tuned model
2. **Inference** (Kaggle notebook with T4x2) → produces submission.csv

---

## Step 1: Upload Processed Training Data to Kaggle

The processed data is in `data_processed/combined/`. Upload it as a Kaggle dataset:

### Using Kaggle CLI:
```bash
cd /Users/manishswami/developer/deep_past_akkadina_challenge/new_start
kaggle datasets init -p data_processed/combined/
# Edit the metadata file, set:
#   "title": "akkadian-processed-data"
#   "id": "YOUR_USERNAME/akkadian-processed-data"
kaggle datasets create -p data_processed/combined/
```

### Using Kaggle Web UI:
1. Go to https://www.kaggle.com/datasets → "New Dataset"
2. Upload these 2 files from `data_processed/combined/`:
   - `train_split.csv` (14,741 training pairs, ~10MB)
   - `val_split.csv` (208 validation pairs, ~53KB)
3. Name the dataset: `akkadian-processed-data`
4. Set visibility: Private

### Data contents:
| File | Rows | Description |
|------|------|-------------|
| train_split.csv | 14,741 | Combined training data (Strategy A+B+C + ORACC + lexicon) |
| val_split.csv | 208 | Validation set (sentence-level from 50 held-out documents) |

---

## Step 2: Create Training Notebook on Kaggle

1. Go to https://www.kaggle.com/code → "New Notebook"
2. Upload or paste the contents of `notebooks/kaggle_training.ipynb`
3. Settings:
   - **Accelerator**: GPU H100 (or P100 if not available)
   - **Internet**: ON
   - **Language**: Python
4. Add Input Datasets:
   - `akkadian-processed-data` (your uploaded dataset from Step 1)
   - `deep-past-initiative-machine-translation` (competition data)
5. Run all cells
6. After training completes, download the model from `/kaggle/working/model/final/`

### Training time estimates:
- H100: ~2-3 hours for all 3 phases
- P100: ~6-8 hours for all 3 phases
- T4: May exceed 9 hours — reduce epochs or use byt5-base

### If using byt5-base instead of byt5-large:
Change `MODEL_NAME = "google/byt5-large"` to `MODEL_NAME = "google/byt5-base"`
This is faster (~1 hour on H100) but may score lower.

---

## Step 3: Upload Fine-Tuned Model to Kaggle

After training, download the model files from `/kaggle/working/model/final/` and upload as a new Kaggle dataset:

### Files to download from training output:
```
model/final/
├── config.json
├── generation_config.json
├── model.safetensors (or pytorch_model.bin)
├── special_tokens_map.json
├── spiece.model (or tokenizer.json)
└── tokenizer_config.json
```

### Upload:
1. Go to https://www.kaggle.com/datasets → "New Dataset"
2. Upload ALL files from `model/final/`
3. Name the dataset: `byt5-akkadian-finetuned`
4. Important: Put files in a subfolder called `final` OR update the MODEL_PATH in the inference notebook

---

## Step 4: Create Inference/Submission Notebook

1. Go to the competition page → "Submit Prediction" → "New Notebook"
2. Upload or paste contents of `notebooks/kaggle_submission.ipynb`
3. Settings:
   - **Accelerator**: GPU T4x2
   - **Internet**: OFF (required for submission)
   - **Language**: Python
4. Add Input Datasets:
   - `byt5-akkadian-finetuned` (your uploaded model from Step 3)
   - `deep-past-initiative-machine-translation` (competition data — auto-attached)
5. Verify MODEL_PATH matches your dataset structure:
   ```python
   MODEL_PATH = "/kaggle/input/byt5-akkadian-finetuned/final"
   # or if files are at root:
   MODEL_PATH = "/kaggle/input/byt5-akkadian-finetuned"
   ```
6. Click "Submit" → the notebook runs and produces `submission.csv`

### Expected inference time: 30-60 minutes for ~4,000 sentences

---

## Troubleshooting

### OOM during training
- Reduce BATCH_SIZE to 2, increase GRAD_ACCUM to 16
- Use byt5-base instead of byt5-large
- Reduce MAX_SRC_LEN to 512

### OOM during inference
- Reduce BATCH_SIZE to 4
- The dynamic beam size already handles long sequences

### Model path not found
- Check `!ls /kaggle/input/` to see dataset names
- Check `!ls /kaggle/input/byt5-akkadian-finetuned/` for folder structure
- Update MODEL_PATH accordingly

### Low scores
- Ensure preprocessing in inference matches training exactly
- Check that the model trained for enough epochs (Phase 2 should show improving geo_mean)
- Try increasing NUM_BEAMS to 8 (slower but potentially better)

---

## Quick Start (Minimum Viable Submission)

For the fastest possible submission:

1. Upload `train_split.csv` and `val_split.csv` to Kaggle as dataset
2. Create training notebook, change `MODEL_NAME = "google/byt5-base"` (faster)
3. Run training (1-2 hours on H100)
4. Upload model, create inference notebook
5. Submit

This gets you a baseline score. Then iterate with:
- Switch to byt5-large
- Tune hyperparameters
- Add more training data
