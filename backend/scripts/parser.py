import os
import fitz
import openai
import re
import json
import pdfplumber
from typing import List, Dict, Tuple

PDF_FOLDER = os.path.join(os.path.dirname(__file__), "../pdfs")
MODEL = "gpt-4o"
openai.api_key = os.getenv("OPENAI_API_KEY")
BATCH_SIZE = 2

def get_pdf_year(pdf_path: str) -> int:
    match = re.search(r"(\d{4})", os.path.basename(pdf_path))
    return int(match.group(1)) if match else 2024 

KEYWORDS = [
    "income statement", "statement of operations", "statement of income", "profit and loss",
    "balance sheet", "statement of financial position", "financial condition",
    "cash flow", "statement of cash flows", "financial statements", "sheet"
]

SIGNAL_PHRASES = [
    "for the year ended", "consolidated statement", "statement of cash flows",
    "statement of financial position", "balance sheet", "income statement", "euros in millions",
    "amounts in", "(in millions)", "operating activities", "investing activities",
    "financing activities", "cash flows", "financial statements", "fiscal year",
    "depreciation and amortization", "accounts payable", "cash and cash equivalents"
]

TABLE_SECTION_HEADERS = [
    "assets", "liabilities", "equity", "revenue", "sales", "expenses", "cost", "cash",
    "operating", "investing", "financing", "depreciation", "interest", "income", "tax",
    "amortization", "rd", "property", "equipment", "compensation", "dividend",
    "receivable", "payable", "proceeds", "purchase", "share", "lease", "inventory"
]

def has_numbers(text: str) -> bool:
    return bool(re.search(r"\$?\(?[\d,]+(?:\.\d+)?\)?", text)) or "€" in text or "million" in text.lower()

def is_relevant_financial_table(text: str) -> bool:
    text_lower = text.lower()
    numeric_lines = sum(1 for line in text.split("\n") if has_numbers(line))
    return (
        numeric_lines >= 4 and
        any(kw in text_lower for kw in SIGNAL_PHRASES) and
        any(h in text_lower for h in TABLE_SECTION_HEADERS)
    )

def strong_structural_signal_adjusted(text: str) -> bool:
    lines = text.lower().split("\n")
    numeric_rows = sum(1 for line in lines if has_numbers(line))
    signal_phrase_match = any(any(sig in line for sig in SIGNAL_PHRASES) for line in lines)

    year_pattern = r"\b(2024|2023|2022|2021|2020|2019|2018|2017|2016|2015|2014)\b"
    year_hits = sum(1 for line in lines if len(re.findall(year_pattern, line)) >= 2)

    header_hits = sum(any(h in line for h in TABLE_SECTION_HEADERS) for line in lines)

    consistent_columns = sum(
        1 for line in lines if len(re.findall(r"\d[\d,.\s]{3,}", line)) >= 2
    )

    return (
        numeric_rows >= 3 and
        signal_phrase_match and
        (year_hits >= 2 or header_hits >= 3 or consistent_columns >= 2)
    )

def get_page_text(pdf_path: str, page_num: int) -> str:
    with fitz.open(pdf_path) as doc:
        return doc[page_num].get_text("text")  # type: ignore

def extract_text_with_pdfplumber(pdf_path: str, pages: List[int]) -> str:
    merged_text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for p in pages:
            try:
                merged_text += pdf.pages[p].extract_text() + "\n"
            except:
                continue
    return merged_text.strip()

def safe_parse_json(content: str) -> Dict:
    try:
        if content.startswith("```json"):
            content = content.replace("```json", "").replace("```", "").strip()
        elif content.startswith("```"):
            content = content.replace("```", "").strip()
        first = content.find("{")
        last = content.rfind("}")
        return json.loads(content[first:last + 1])
    except Exception as e:
        print(f"   Failed to parse JSON: {e}")
        return {}

def ask_openai_batch(text: str, page_ids: List[int], current_year: int) -> Tuple[Dict, Dict]:
    print(f"   GPT validating pages {', '.join(str(p+1) for p in page_ids)}")

    try:
        response = openai.ChatCompletion.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a financial data extractor and cleaner."},
                {
                    "role": "user",
                    "content": f"""
This is extracted text from a company's annual report. It may contain parts of the Income Statement, Balance Sheet, or Cash Flow Statement.

Please extract **only the exact line items** (no renaming) related to:
- Revenue / Net Sales
- Cost of Revenues / Cost of Sales
- Operating Expenses (R&D, SG&A, Amortization, etc.)
- Any lines found in those three statements

Return only data for **{current_year}** under `"Data"` and anything from **before {current_year}** under `"Historical Data"`.

Strict JSON format:
{{
  "Statement Type": "...",
  "Data": {{ "Line Item": "Value", ... }},
  "Historical Data": {{ "Line Item": "Value", ... }}
}}

Text:
{text}
"""
                }
            ],
            temperature=0,
            max_tokens=1500
        )

        content = response.choices[0].message["content"].strip() # type: ignore
        usage = response['usage'] # type: ignore

        with open("openai_responses_debug.txt", "a") as f:
            f.write(f"\n\n--- Pages {page_ids} ---\n{content}\n")

        return safe_parse_json(content), usage

    except Exception as e:
        print(f"   GPT failed on pages {page_ids}: {e}")
        return {}, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

def parsed_pdf(pdf_path: str) -> Dict:
    print(f"\n Parsing: {pdf_path}")
    year = get_pdf_year(pdf_path)

    matched_pages = []
    with fitz.open(pdf_path) as doc:
        for i, page in enumerate(doc):  # type: ignore
            text = page.get_text("text")
            if any(k in text.lower() for k in KEYWORDS) and has_numbers(text):
                matched_pages.append(i)

    print(f"\n🔍 First-pass matched pages: {len(matched_pages)} → {[p+1 for p in matched_pages]}")

    second_pass = []
    for p in matched_pages:
        text = get_page_text(pdf_path, p)
        if is_relevant_financial_table(text):
            second_pass.append(p)

    print(f"\n🔎 Second-pass (financial table signals): {len(second_pass)} → {[p+1 for p in second_pass]}")

    filtered_pages = []
    for p in second_pass:
        text = get_page_text(pdf_path, p)
        if strong_structural_signal_adjusted(text):
            filtered_pages.append(p)

    print(f"\n Final filtered pages: {len(filtered_pages)} → {[p+1 for p in filtered_pages]}")

    extracted = {"Income Statement": {}, "Balance Sheet": {}, "Cash Flow Statement": {}}
    historical = {"Income Statement": {}, "Balance Sheet": {}, "Cash Flow Statement": {}}
    total_tokens = 0

    for i in range(0, len(filtered_pages), BATCH_SIZE):
        batch = filtered_pages[i:i + BATCH_SIZE]
        batch_text = extract_text_with_pdfplumber(pdf_path, batch)
        if not batch_text.strip():
            continue

        result, usage = ask_openai_batch(batch_text, batch, year)
        total_tokens += usage["total_tokens"]

        if result and "Statement Type" in result:
            st_type = result["Statement Type"]
            if st_type in extracted:
                extracted[st_type].update(result.get("Data", {}))
                historical[st_type].update(result.get("Historical Data", {}))

    output = {
        "Income Statement": extracted["Income Statement"],
        "Balance Sheet": extracted["Balance Sheet"],
        "Cash Flow Statement": extracted["Cash Flow Statement"],
        "Historical Data": {
            **historical["Income Statement"],
            **historical["Balance Sheet"],
            **historical["Cash Flow Statement"]
        },
        "Total Tokens Used": total_tokens
    }

    print(f"\n📆 Final {year} Extracted: {json.dumps(extracted, indent=2)}")
    print(f"\n📊 Historical Data: {json.dumps(output['Historical Data'], indent=2)}")

    return output
