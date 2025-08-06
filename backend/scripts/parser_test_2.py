import os
import re
import json
import pdfplumber
from typing import Dict

# --------------------------
# CONFIGURATION
# --------------------------
BASE_DIR = os.getcwd()
PDF_FOLDER = os.path.join(BASE_DIR, "pdfsASML")
OUTPUT_FOLDER = os.path.join(BASE_DIR, "parsed_json")
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Statement Section Keywords
STATEMENT_SECTIONS = {
    "Income Statement": [
        "income statement", "statement of income", "statement of operations", "profit and loss"
    ],
    "Balance Sheet": [
        "balance sheet", "statement of financial position", "statement of financial condition"
    ],
    "Cash Flow Statement": [
        "cash flow", "statement of cash flows"
    ]
}

# --------------------------
# FUNCTIONS
# --------------------------

from typing import Optional

def get_section_type(line: str) -> Optional[str]:
    """Identify which financial statement section a line belongs to."""
    line = line.lower()
    for section, keywords in STATEMENT_SECTIONS.items():
        for keyword in keywords:
            if keyword in line:
                return section
    return None

def extract_values(line: str) -> Dict[str, str]:
    """
    Extract key-value pairs from lines with dots, tabs, or space alignment.
    Example: "Net Revenue ............ 1,234,567" → {"Net Revenue": "1234567"}
    """
    extracted = {}
    if re.search(r'\d', line):  # contains number
        parts = re.split(r'\.{2,}| {2,}|\t+', line.strip())
        if len(parts) >= 2:
            key = parts[0].strip()
            value = parts[-1].strip().replace(",", "").replace("$", "")
            if re.match(r"^\(?-?\d[\d,\.]*\)?$", value):  # Only numeric-like values
                extracted[key] = value
    return extracted

def parse_pdf_to_json(pdf_path: str, ticker: str, year: int) -> Dict:
    """
    Parse a single PDF and return structured JSON data.
    """
    output = {
        "ticker": ticker,
        "year": year,
        "name": ticker,
        "ir_url": "",
        "data": {
            "Income Statement": {},
            "Balance Sheet": {},
            "Cash Flow Statement": {}
        }
    }

    current_section = None

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue

                lines = text.split('\n')
                for line in lines:
                    section = get_section_type(line)
                    if section:
                        current_section = section
                        continue

                    if current_section:
                        values = extract_values(line)
                        output["data"][current_section].update(values)
    except Exception as e:
        print(f"Error processing {pdf_path}: {e}")

    return output

# --------------------------
# MAIN SCRIPT
# --------------------------

def main():
    for year in range(2024, 2014, -1):
        for filename in os.listdir(PDF_FOLDER):
            if filename.endswith(f"{year}.pdf"):
                match = re.match(r"([A-Z]+)_(\d{4})\.pdf", filename)
                if match:
                    ticker, year_str = match.groups()
                    pdf_path = os.path.join(PDF_FOLDER, filename)
                    print(f"Parsing {filename}...")

                    parsed_json = parse_pdf_to_json(pdf_path, ticker, int(year_str))

                    # Save output
                    output_path = os.path.join(OUTPUT_FOLDER, f"{ticker}_{year_str}.json")
                    with open(output_path, 'w') as f:
                        json.dump(parsed_json, f, indent=2)

    print("✅ All PDFs parsed and saved to parsed_json/")

if __name__ == "__main__":
    main()
