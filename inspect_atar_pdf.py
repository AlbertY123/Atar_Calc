import pdfplumber
from pathlib import Path

pdf_path = Path(__file__).resolve().parent / "data" / "atar_to_aggregate_24.pdf"

with pdfplumber.open(str(pdf_path)) as pdf:
    print('pages', len(pdf.pages))
    page = pdf.pages[0]
    text = page.extract_text()
    print(text[:2000] if text else None)
