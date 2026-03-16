from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pdfplumber
import pandas as pd


@dataclass(frozen=True)
class AtarAggregateRow:
    atar: float
    aggregate_low: float
    aggregate_high: float

    @property
    def aggregate_mid(self) -> float:
        return (self.aggregate_low + self.aggregate_high) / 2


ATAR_TRIPLE_RE = re.compile(
    r"(?P<atar>\d{2}\.\d{2})\s+(?P<low>\d{1,3}\.\d{2})\s+(?P<high>\d{1,3}\.\d{2})"
)


def extract_atar_to_aggregate_table(pdf_path: str | Path) -> pd.DataFrame:
    """Extract VTAC's Aggregate→ATAR table.

    The PDF is laid out as three repeated triplets per line:
      ATAR  lowAgg  highAgg

    Returns a DataFrame with columns: atar, aggregate_low, aggregate_high, aggregate_mid
    """

    pdf_path = Path(pdf_path)
    rows: list[AtarAggregateRow] = []

    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            for m in ATAR_TRIPLE_RE.finditer(text):
                rows.append(
                    AtarAggregateRow(
                        atar=float(m.group("atar")),
                        aggregate_low=float(m.group("low")),
                        aggregate_high=float(m.group("high")),
                    )
                )

    if not rows:
        raise ValueError(f"No ATAR rows parsed from {pdf_path}")

    df = pd.DataFrame(
        {
            "atar": [r.atar for r in rows],
            "aggregate_low": [r.aggregate_low for r in rows],
            "aggregate_high": [r.aggregate_high for r in rows],
            "aggregate_mid": [r.aggregate_mid for r in rows],
        }
    )

    # De-duplicate (some PDFs repeat headers or have overlaps depending on extraction)
    df = df.drop_duplicates().sort_values(["aggregate_mid"], ascending=True).reset_index(drop=True)
    return df


def _iter_lines_join_wrapped(text: str) -> Iterable[str]:
    """Join wrapped lines from pdfplumber extraction.

    Some rows get split across lines/pages. We accumulate until we see a line ending with
    enough numeric tokens to parse.

    Important: the scaling PDF often includes a header line like:
      "Code 2024 Study Mean St. Dev. 20 25 30 35 40 45 50"
    If we accidentally glue that header to the first data row, we can lose the first row.
    So we drop/reset when we see header markers.
    """

    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    buf: list[str] = []

    def is_complete(candidate: str) -> bool:
        toks = candidate.split()
        # We need at least: code + subject + mean + stdev + 7 ints => 11 tokens minimum.
        if len(toks) < 11:
            return False
        # Last 7 tokens should be ints.
        if not all(re.fullmatch(r"\d{1,2}", t) for t in toks[-7:]):
            return False
        # mean/stdev tokens (just before the last 7) should be floats like 30.8 7.4
        if not re.fullmatch(r"\d{1,2}\.\d", toks[-9]):
            return False
        if not re.fullmatch(r"\d{1,2}\.\d", toks[-8]):
            return False
        return True

    for ln in lines:
        # Reset buffer on table headers so they don't get glued to the first row.
        if ln.startswith("Code ") and "St." in ln and "Dev" in ln:
            buf.clear()
            continue

        # Other non-table section headers
        if ln.startswith("2024 Scaled Aggregate to ATAR Table"):
            buf.clear()
            continue

        buf.append(ln)
        candidate = " ".join(buf)
        if is_complete(candidate):
            yield candidate
            buf.clear()

    # Don't yield leftovers — incomplete fragments are more harmful than helpful.


def extract_scaling_summary(pdf_path: str | Path) -> pd.DataFrame:
    """Extract the *summary* scaling table from the VTAC scaling report.

    The 2024 scaling report (and similar) contains a table with columns:
      Code, Study, Mean, St.Dev, scaled score at raw 20,25,30,35,40,45,50

    Returns a DataFrame with:
      code, study, mean, stdev, s20, s25, s30, s35, s40, s45, s50

    Notes:
      - This is a coarse/rounded indication, not the full 2-decimal scaling VTAC uses.
      - Rows marked 'Small Study or no candidates' are skipped.
    """

    pdf_path = Path(pdf_path)

    # Get all text for pages; for 2024 it’s only 3 pages.
    all_text = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            all_text.append(page.extract_text() or "")

    text = "\n".join(all_text)

    rows = []
    for ln in _iter_lines_join_wrapped(text):
        toks = ln.split()

        # Skip headers / category lines
        if toks[0] in {"Code", "2024"}:
            continue
        if toks[0].endswith(":"):
            continue

        # Skip small-study lines
        if "Small" in toks and "Study" in toks:
            continue
        if "no" in toks and "candidates" in toks:
            continue

        # Expect: code ... mean stdev s20..s50
        if len(toks) < 11:
            continue
        if not re.fullmatch(r"\d{1,2}\.\d", toks[-9]) or not re.fullmatch(r"\d{1,2}\.\d", toks[-8]):
            continue
        if not all(re.fullmatch(r"\d{1,2}", t) for t in toks[-7:]):
            continue

        code = toks[0]
        # Codes in the table are uppercase letters/digits (e.g., EN, AC, LO49, MA10, IT02).
        # This filters out section headings like "Applied" or "Mathematics:".
        if not re.fullmatch(r"[A-Z0-9]{2,6}", code):
            continue

        mean = float(toks[-9])
        stdev = float(toks[-8])
        s20, s25, s30, s35, s40, s45, s50 = map(int, toks[-7:])
        study = " ".join(toks[1:-9])

        rows.append(
            {
                "code": code,
                "study": study,
                "mean": mean,
                "stdev": stdev,
                "s20": s20,
                "s25": s25,
                "s30": s30,
                "s35": s35,
                "s40": s40,
                "s45": s45,
                "s50": s50,
            }
        )

    if not rows:
        raise ValueError(f"No scaling rows parsed from {pdf_path}")

    df = pd.DataFrame(rows)
    df = df.drop_duplicates(subset=["code"]).sort_values(["study"]).reset_index(drop=True)
    return df
