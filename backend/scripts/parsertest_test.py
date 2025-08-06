import os
import re
import json
import openai
import pdfplumber
import fitz # PyMuPDF
from dotenv import load_dotenv
from typing import List, Dict

# Load API Key
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Paths
BASE_DIR = os.path.dirname(__file__)
PDF_DIR = os.path.join(BASE_DIR, "../pdfs")
OUTPUT_DIR = os.path.join(BASE_DIR, "../parsed_json")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Config
MODEL = "gpt-4o"
BATCH_SIZE = 2

REFERENCE_KEYS = {
    "Income Statement": [
        "Net Revenue", "Cost of Revenue", "Gross Profit", "Operating Expenses",
        "Operating Income", "Net Income", "Interest Expense", "Other Income",
        "Income Before Tax", "Net Income After Tax"
    ],
    "Balance Sheet": [
        "Total Shareholder Equity", "Total Assets", "Total Liabilities",
        "Cash and Cash Equivalents", "Short-Term Investments", "Long-Term Debt",
        "Accounts Receivable", "Inventory", "Current Assets", "Non-Current Assets"
    ],
    "Cash Flow Statement": [
        "Net Cash from Operating Activities", "Net Cash from Investing Activities",
        "Net Cash from Financing Activities", "Capital Expenditures",
        "Depreciation & Amortization", "Free Cash Flow", "Stock Buybacks",
        "Dividends Paid", "Change in Working Capital", "Other Operating Cash Flow"
    ]
}

SECTION_KEYWORDS = {
    "Income Statement": [
        "income statement", "statement of operations", "profit and loss",
        "statement of profit or loss", "statement of earnings", "Performance KPIs",
        "consolidated income statement", "consolidated statement of operations",
        "statement of income", "results of operations", "earnings report", "Consolidated Statement of Comprehensive Income", "statement of comprehensive income"],
    "Balance Sheet": ["balance sheet", "financial position", "statement of financial position", "consolidated balance sheet"],
    "Cash Flow Statement": ["cash flow", "cashflows", "statement of cash flows", "consolidated statement of cash flows"]
}


def match_sections(text: str) -> List[str]:
    matches = []
    lower = text.lower()
    for section, keywords in SECTION_KEYWORDS.items():
        for keyword in keywords:
            if keyword in lower:
                matches.append(section)
                break
    return matches

def detect_units(text: str) -> str:
    text = text.lower()
    if "in millions" in text or "figures in millions" in text:
        return "millions"
    elif "in billions" in text or "figures in billions" in text:
        return "billions"
    elif "in thousands" in text or "figures in thousands" in text:
        return "thousands"
    return "units"

def extract_text_with_fitz(pdf_path: str, page_number: int) -> str:
    try:
        with fitz.open(pdf_path) as doc:
            return doc[page_number].get_text()
    except Exception as e:
        print(f"❌ PyMuPDF failed on page {page_number} of {pdf_path}: {e}")
        return ""

def extract_text_blocks(pdf_path: str) -> tuple[Dict[str, List[str]], Dict[str, str]]:
    section_texts = {s: [] for s in SECTION_KEYWORDS}
    section_units = {s: "units" for s in SECTION_KEYWORDS}  
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            raw_text = page.extract_text()
            if not raw_text:
                raw_text = extract_text_with_fitz(pdf_path, page.page_number - 1) 

            if not raw_text:
                continue

            if raw_text:
                print(f"📝 Page {page.page_number} text (trimmed):", raw_text[:150])
            else:
                print(f"🛑 Page {page.page_number} has no extractable text.")

            matched = match_sections(raw_text)
            unit = detect_units(raw_text)
            if not matched:
                continue

            text_block = ""

            table_found = False
            for table in page.extract_tables():
                for row in table:
                    if row and any(cell and re.search(r"\d", cell) for cell in row):
                        text_block += " | ".join(cell.strip() if cell else "" for cell in row) + "\n"
                        table_found = True

            if not table_found:
                for line in raw_text.split("\n"):
                    if re.search(r"\d", line):
                        text_block += line.strip() + "\n"

            for section in matched:
                section_texts[section].append(text_block.strip())
                section_units[section] = unit 

    return section_texts, section_units


def batch_blocks(blocks: List[str], batch_size: int = 2) -> List[str]:
    return ["\n\n".join(blocks[i:i + batch_size]) for i in range(0, len(blocks), batch_size)]


def ask_gpt_for_metrics(section: str, year: int, content: str, unit: str) -> Dict[str, float]:
    keys = REFERENCE_KEYS[section]
    json_schema = json.dumps({k: None for k in keys}, indent=2)

    messages = [
        {
            "role": "system",
            "content": "You're a strict financial data extractor. You return only JSON and never add commentary."
        },
        {
            "role": "user",
            "content": f"""
Extract values for the following {section} metrics for year {year} ONLY. If missing, return null.
All values are reported in {unit.upper()} — do NOT convert them.

Use this format:
{json_schema}

--- BEGIN FINANCIAL TEXT ---
{content}
--- END FINANCIAL TEXT ---
""",
        }
    ]

    try:
        res = openai.ChatCompletion.create(
            model=MODEL,
            messages=messages,
            temperature=0,
        )
        output = res.choices[0].message.content.strip()

        # Clean up
        if output.startswith("```json"):
            output = output[7:]
        if output.endswith("```"):
            output = output[:-3]

        start = output.find("{")
        end = output.rfind("}") + 1
        clean_json = output[start:end]

        clean_json = re.sub(r'(?<=\n)(\s*)([A-Za-z0-9 &\-/().]+):', r'\1"\2":', clean_json)

        return json.loads(clean_json)

    except Exception as e:
        print(f"❌ GPT extraction failed for {section} ({year}): {e}")
        return {k: None for k in keys}


def parse_pdf(path: str):
    filename = os.path.basename(path)
    year = int(re.search(r"\d{4}", filename).group(0))
    ticker = re.match(r"([A-Z]+)", filename).group(1)

    print(f"\n📄 Parsing: {filename} ({year})")
    sections, units = extract_text_blocks(path)

    result = {
        "ticker": ticker,
        "year": year,
        "data": {}
    }

    for section, blocks in sections.items():
        if not blocks:
            print(f"⚠️  No data found for {section}")
            continue

        print(f"🔍 Found {len(blocks)} page(s) for {section}")
        combined_result = {}
        for chunk in batch_blocks(blocks):
            parsed = ask_gpt_for_metrics(section, year, chunk, units[section])
            for key in REFERENCE_KEYS[section]:
                if key not in combined_result or combined_result[key] is None:
                    combined_result[key] = parsed.get(key)
        result["data"][section] = combined_result

    save_path = os.path.join(OUTPUT_DIR, f"{ticker}_{year}.json")
    with open(save_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"✅ Saved: {save_path}")


def main():
    for file in sorted(os.listdir(PDF_DIR)):
        if file.endswith(".pdf") and re.search(r"\d{4}", file):
            parse_pdf(os.path.join(PDF_DIR, file))


if __name__ == "__main__":
    main()
