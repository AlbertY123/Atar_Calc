import pathlib
import requests

OUT_DIR = pathlib.Path(__file__).resolve().parent / "data"
OUT_DIR.mkdir(parents=True, exist_ok=True)

URLS = {
    "atar_to_aggregate_24": "https://vtac.edu.au/files/pdf/reports/atar-to-aggregate-24.pdf",
    "scaling_report_24": "https://vtac.edu.au/files/pdf/reports/scaling-report-24.pdf",
}

for name, url in URLS.items():
    path = OUT_DIR / f"{name}.pdf"
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    path.write_bytes(r.content)
    print(f"{name}: {path.stat().st_size} bytes -> {path}")
