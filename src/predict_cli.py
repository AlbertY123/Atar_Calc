from __future__ import annotations

import argparse
from pathlib import Path

import joblib

from atar_predictor import (
    atar_from_aggregate_lookup,
    build_scaling_curves,
    scaled_aggregate_from_scaled_scores,
)
from vtac_extract import extract_atar_to_aggregate_table, extract_scaling_summary


def main() -> None:
    ap = argparse.ArgumentParser(description="Predict VCE ATAR (approx) using VTAC public PDFs")
    ap.add_argument(
        "--scaling-pdf",
        default=str(Path(__file__).resolve().parent.parent / "data" / "scaling_report_24.pdf"),
    )
    ap.add_argument(
        "--atar-pdf",
        default=str(Path(__file__).resolve().parent.parent / "data" / "atar_to_aggregate_24.pdf"),
    )
    ap.add_argument(
        "--model",
        default=str(Path(__file__).resolve().parent.parent / "models" / "atar_from_aggregate.joblib"),
        help="Optional trained ML model (otherwise uses table interpolation)",
    )
    ap.add_argument(
        "--use-ml",
        action="store_true",
        help="If set, use the trained ML model instead of direct interpolation",
    )
    ap.add_argument(
        "--scores",
        nargs="+",
        required=True,
        metavar="CODE=RAW",
        help="Study scores as CODE=RAW (e.g., EN=35 NJ=40 BI=38 CH=33)",
    )
    args = ap.parse_args()

    scaling_df = extract_scaling_summary(args.scaling_pdf)
    curves = build_scaling_curves(scaling_df)

    scaled_scores = []
    for pair in args.scores:
        if "=" not in pair:
            raise SystemExit(f"Bad score format: {pair} (expected CODE=RAW)")
        code, raw_s = pair.split("=", 1)
        code = code.strip()
        raw = float(raw_s)
        if code not in curves:
            known = ", ".join(sorted(curves.keys())[:15]) + ("..." if len(curves) > 15 else "")
            raise SystemExit(f"Unknown code {code}. Known codes include: {known}")
        scaled = curves[code].scaled_score(raw)
        scaled_scores.append(scaled)
        print(f"{code} {curves[code].study}: raw {raw:.1f} -> scaled ~{scaled:.2f}")

    agg = scaled_aggregate_from_scaled_scores(scaled_scores)
    print(f"\nScaled aggregate (approx): {agg:.2f}")

    atar_table_df = extract_atar_to_aggregate_table(args.atar_pdf)

    if args.use_ml:
        bundle = joblib.load(args.model)
        model = bundle["model"]
        pred = float(model.predict([[agg]])[0])
        print(f"Predicted ATAR (ML): {pred:.2f}  (model test MAE ~ {bundle['mae']:.3f})")
    else:
        pred = atar_from_aggregate_lookup(agg, atar_table_df)
        print(f"Predicted ATAR (table interpolation): {pred:.2f}")


if __name__ == "__main__":
    main()
