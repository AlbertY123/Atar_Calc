from __future__ import annotations

import argparse
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import Ridge

from vtac_extract import extract_atar_to_aggregate_table


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--atar-pdf",
        default=str(Path(__file__).resolve().parent.parent / "data" / "atar_to_aggregate_24.pdf"),
        help="Path to VTAC ATAR-to-aggregate PDF",
    )
    ap.add_argument(
        "--out",
        default=str(Path(__file__).resolve().parent.parent / "models" / "atar_from_aggregate.joblib"),
        help="Where to save the trained model",
    )
    args = ap.parse_args()

    df = extract_atar_to_aggregate_table(args.atar_pdf)

    # Supervised dataset: X = aggregate midpoint, y = ATAR
    X = df[["aggregate_mid"]].to_numpy(dtype=float)
    y = df["atar"].to_numpy(dtype=float)

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = Pipeline(
        [
            ("poly", PolynomialFeatures(degree=3, include_bias=False)),
            ("ridge", Ridge(alpha=1e-3)),
        ]
    )

    model.fit(X_train, y_train)
    pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, pred)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "mae": mae, "n_rows": int(len(df))}, out_path)

    print(f"Trained model saved to: {out_path}")
    print(f"Rows: {len(df)} | Test MAE: {mae:.4f} ATAR points")


if __name__ == "__main__":
    main()
