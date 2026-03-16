from __future__ import annotations

import os
import sys
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template, request, url_for

# Make src imports work when running as a script
BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE / "src"))

from vtac_extract import extract_atar_to_aggregate_table, extract_scaling_summary  # noqa: E402
from atar_predictor import (  # noqa: E402
    atar_from_aggregate_lookup,
    build_scaling_curves,
    scaled_aggregate_from_scaled_scores,
)

APP = Flask(__name__, template_folder=str(BASE / "templates"), static_folder=str(BASE / "static"))
APP.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0  # reduce caching headaches during development

SCALING_PDF = BASE / "data" / "scaling_report_24.pdf"
ATAR_PDF = BASE / "data" / "atar_to_aggregate_24.pdf"


def load_tables():
    scaling_df = extract_scaling_summary(SCALING_PDF)
    curves = build_scaling_curves(scaling_df)
    atar_df = extract_atar_to_aggregate_table(ATAR_PDF)
    return scaling_df, curves, atar_df


SCALING_DF, CURVES, ATAR_TABLE = load_tables()

ASSET_VERSION = "2026-03-08.2"

ENGLISH_CODES = {"EN", "EF", "EG", "LI"}  # English, EAL, English Language, Literature


def parse_scores(text: str):
    pairs = []
    for raw_ln in (text or "").splitlines():
        ln = raw_ln.strip()
        if not ln:
            continue
        if "=" not in ln:
            raise ValueError(f"Bad line '{ln}' (expected CODE=RAW)")
        code, raw = ln.split("=", 1)
        code = code.strip()
        raw_score = float(raw.strip())
        pairs.append((code, raw_score))
    return pairs


def studies_for_ui():
    studies = []
    for code, curve in CURVES.items():
        studies.append(
            {
                "code": code,
                "study": curve.study,
                "isEnglish": code in ENGLISH_CODES or ("English" in curve.study),
            }
        )
    studies = sorted(studies, key=lambda x: (not x["isEnglish"], x["study"].lower()))
    return studies


def predict_from_pairs(pairs: list[tuple[str, float]]):
    if len(pairs) < 4:
        raise ValueError("Need at least 4 subjects")

    # Official ATAR requires at least one English-group subject.
    if not any(code in ENGLISH_CODES for code, _ in pairs):
        raise ValueError("You must include at least one English-group subject (English / EAL / English Language / Literature).")

    # Compute per-study scaled score
    details = []
    scaled_scores = []
    for code, raw in pairs:
        if code not in CURVES:
            raise ValueError(f"Unknown subject code '{code}'")
        curve = CURVES[code]
        scaled = curve.scaled_score(raw)
        details.append({"code": code, "study": curve.study, "raw": float(raw), "scaled": float(scaled)})
        scaled_scores.append(float(scaled))

    # Determine aggregate contributions
    # Sort by scaled desc, preserve mapping via indices
    order = sorted(range(len(details)), key=lambda i: details[i]["scaled"], reverse=True)
    top4_idx = set(order[:4])
    bonus_idx = set(order[4:6])

    for i, d in enumerate(details):
        d["in_top4"] = i in top4_idx
        d["is_bonus"] = i in bonus_idx

    agg = scaled_aggregate_from_scaled_scores([d["scaled"] for d in details])
    atar = atar_from_aggregate_lookup(agg, ATAR_TABLE)

    # Sort details nicely for display
    details_sorted = sorted(details, key=lambda d: d["scaled"], reverse=True)

    return {
        "aggregate": float(agg),
        "atar": float(atar),
        "n_used": int(len(details)),
        "details": details_sorted,
    }


@APP.get("/")
def index_get():
    default_rows = [
        {"code": "EN", "raw": 35},
        {"code": "NJ", "raw": 40},
        {"code": "BI", "raw": 38},
        {"code": "CH", "raw": 33},
        {"code": "BM", "raw": 36},
        {"code": "NF", "raw": 32},
    ]
    import json

    return render_template(
        "index.html",
        studies_json=json.dumps(studies_for_ui()),
        default_rows_json=json.dumps(default_rows),
        asset_version=ASSET_VERSION,
    )


@APP.post("/")
def index_post_compat():
    # Compatibility for old cached UI versions that POSTed a form.
    return redirect(url_for("index_get"), code=303)


@APP.get("/about")
def about():
    return render_template("about.html")


@APP.get("/api/studies")
def api_studies():
    return jsonify({"studies": studies_for_ui()})


@APP.post("/api/predict")
def api_predict():
    try:
        payload = request.get_json(force=True, silent=False)
        studies = payload.get("studies", [])
        pairs = []
        for s in studies:
            code = str(s.get("code", "")).strip()
            raw = float(s.get("raw_score"))
            pairs.append((code, raw))
        result = predict_from_pairs(pairs)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 400



@APP.get("/favicon.ico")
def favicon():
    # Avoid noisy 404s in logs.
    return ("", 204)


if __name__ == "__main__":
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "5000"))
    APP.run(host=host, port=port, debug=False)
