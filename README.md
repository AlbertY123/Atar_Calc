# VCE ATAR Predictor (VTAC data + ML demo)

This project builds an **ATAR predictor** using **public VTAC PDFs** and a simple **machine learning regression model**.

## What it does

1. **Downloads / uses VTAC public data**:
   - **Scaling report** (study-score scaling summary by subject code)
   - **Aggregate→ATAR table** (mapping from scaled aggregate ranges to ATAR)
2. Converts **raw VCE study scores** (your predicted results) into an **approx scaled score** using the scaling report’s anchor points (20/25/…/50).
3. Computes a **scaled aggregate** (top 4 + 10% of 5th/6th).
4. Predicts ATAR either by:
   - **Direct interpolation** of the official table (recommended), or
   - A trained **polynomial Ridge regression** model (ML demo).

## Data sources (official)

- VTAC Reports & Statistics page (contains links to both PDFs):
  https://vtac.edu.au/reports

Example files used here (2025 selection cycle / 2024 results):
- Scaling report: https://vtac.edu.au/files/pdf/reports/scaling-report-24.pdf
- Aggregate to ATAR table: https://vtac.edu.au/files/pdf/reports/atar-to-aggregate-24.pdf

## Accuracy notes / limitations

- VTAC scaling uses **2-decimal scaled scores** and a cohort-based process.
- The scaling report table is **rounded** and only provides scaling at **raw 20/25/30/35/40/45/50**.
- So this tool is best used as a **rough predictor**, not an official calculator.

## Install

```bash
pip install -r requirements.txt
```

## Train the ML model

```bash
python src/train_model.py
```

## Predict (CLI)

Example (codes must match VTAC scaling report codes):

```bash
python src/predict_cli.py --scores EN=35 NJ=40 BI=38 CH=33 BM=36 NF=32
```

To use the ML model instead of direct table interpolation:

```bash
python src/predict_cli.py --use-ml --scores EN=35 NJ=40 BI=38 CH=33 BM=36 NF=32
```
