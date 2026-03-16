import pdfplumber
from pathlib import Path

pdf_path = Path(__file__).resolve().parent / "data" / "scaling_report_24.pdf"

with pdfplumber.open(str(pdf_path)) as pdf:
    print('pages', len(pdf.pages))
    for i in [0,1,2,3,4]:
        page = pdf.pages[i]
        text = page.extract_text() or ''
        print('\n--- page', i+1, '---')
        print(text[:2000])
