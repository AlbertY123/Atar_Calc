from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd


RAW_POINTS = np.array([20, 25, 30, 35, 40, 45, 50], dtype=float)


@dataclass(frozen=True)
class ScalingCurve:
    """Piecewise-linear approximation of study-score scaling from VTAC scaling summary."""

    study: str
    code: str
    scaled_points: np.ndarray  # shape (7,)

    def scaled_score(self, raw_study_score: float) -> float:
        """Approximate scaled score for a raw VCAA study score.

        VTAC uses 2-decimal scaling; the public scaling report table is rounded integers
        at the anchor raw study scores (20,25,...,50). We interpolate linearly.
        """
        x = float(raw_study_score)
        # Clamp to the published range for stability
        x = max(20.0, min(50.0, x))
        return float(np.interp(x, RAW_POINTS, self.scaled_points.astype(float)))


def build_scaling_curves(scaling_df: pd.DataFrame) -> dict[str, ScalingCurve]:
    curves: dict[str, ScalingCurve] = {}
    for _, r in scaling_df.iterrows():
        code = str(r["code"]).strip()
        curves[code] = ScalingCurve(
            study=str(r["study"]).strip(),
            code=code,
            scaled_points=np.array(
                [r["s20"], r["s25"], r["s30"], r["s35"], r["s40"], r["s45"], r["s50"]],
                dtype=float,
            ),
        )
    return curves


def scaled_aggregate_from_scaled_scores(scaled_scores: Iterable[float]) -> float:
    """Compute the VTAC-style scaled aggregate from scaled study scores.

    This is the standard VCE aggregate structure:
      - sum of best 4 scaled scores
      - plus 10% of the next two (5th and 6th)

    Notes:
      - Some study rules apply (English requirement, allowed combinations, etc.)
      - We treat the inputs as already valid scaled study scores.
    """
    ss = sorted([float(x) for x in scaled_scores], reverse=True)
    if len(ss) < 4:
        raise ValueError("Need at least 4 study scores to form an aggregate")

    top4 = sum(ss[:4])
    next2 = sum(ss[4:6]) if len(ss) >= 6 else sum(ss[4:])
    return float(top4 + 0.1 * next2)


def _round_to_step(x: float, step: float) -> float:
    step = float(step)
    if step <= 0:
        return float(x)
    return float(round(float(x) / step) * step)


def atar_from_aggregate_lookup(aggregate: float, atar_table_df: pd.DataFrame, *, step: float = 0.05) -> float:
    """Predict ATAR by interpolating the official aggregate→ATAR table.

    ATARs are published in increments of 0.05, so we round to that by default.
    """

    df = atar_table_df.sort_values("aggregate_mid")
    x = df["aggregate_mid"].to_numpy(dtype=float)
    y = df["atar"].to_numpy(dtype=float)

    a = float(aggregate)
    # Clamp: outside published range we return min/max ATAR in the table
    if a <= float(x.min()):
        return _round_to_step(float(y[0]), step)
    if a >= float(x.max()):
        return _round_to_step(float(y[-1]), step)

    pred = float(np.interp(a, x, y))
    # Keep within VTAC bounds
    pred = min(float(y.max()), max(float(y.min()), pred))
    return _round_to_step(pred, step)
