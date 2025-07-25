import os
import fitz  # PyMuPDF
import openai
import re
import json
import pdfplumber
from typing import List, Dict, Tuple
from dotenv import load_dotenv

load_dotenv()

PDF_FOLDER = os.path.join(os.path.dirname(__file__), "../pdfs")
OUTPUT_FOLDER = os.path.join(os.path.dirname(__file__), "../parsed_json")
REFERENCE_KEYS_FILE = os.path.join(OUTPUT_FOLDER, "reference_keys_2024.json")
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

MODEL = "gpt-4o"
openai.api_key = os.getenv("OPENAI_API_KEY")
BATCH_SIZE = 2

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


def get_pdf_year(pdf_path: str) -> int:
    """
    Extracts the year from the PDF filename.
    Assumes the year is a four-digit number in the filename.
    """
    match = re.search(r"(\d{4})", os.path.basename(pdf_path))
    return int(match.group(1)) if match else 2024  # fallback

def has_numbers(text: str) -> bool:
    """
    Checks if the given text contains numbers or currency symbols.
    Used to identify lines with potential financial data.
    """
    return bool(re.search(r"\$?\(?[\d,]+(?:\.\d+)?\)?", text)) or "€" in text or "million" in text.lower()

def is_relevant_financial_table(text: str) -> bool:
    """
    Determines if a given text block is likely a relevant financial table.
    Checks for a minimum number of numeric lines, signal phrases, and section headers.
    """
    text_lower = text.lower()
    numeric_lines = sum(1 for line in text.split("\n") if has_numbers(line))
    return (
        numeric_lines >= 4 and
        any(kw in text_lower for kw in SIGNAL_PHRASES) and
        any(h in text_lower for h in TABLE_SECTION_HEADERS)
    )

def strong_structural_signal_adjusted(text: str) -> bool:
    """
    Analyzes text for strong structural signals indicating a well-formed financial table.
    Looks for numeric rows, signal phrases, year hits, header hits, and consistent columns.
    """
    lines = text.lower().split("\n")

    numeric_rows = sum(1 for line in lines if has_numbers(line))
    signal_phrase_match = any(any(sig in line for sig in SIGNAL_PHRASES) for line in lines)

    year_hits = 0
    year_pattern = r"\b(2024|2023|2022|2021|2020|2019|2018|2017|2016|2015|2014)\b"
    for line in lines:
        if len(re.findall(year_pattern, line)) >= 2:
            year_hits += 1

    header_hits = sum(any(h in line for h in TABLE_SECTION_HEADERS) for line in lines)
    consistent_columns = sum(1 for line in lines if len(re.findall(r"\d[\d,.\s]{3,}", line)) >= 2)

    return (
        numeric_rows >= 3 and
        signal_phrase_match and
        (year_hits >= 2 or header_hits >= 3 or consistent_columns >= 2)
    )

def get_page_text(pdf_path: str, page_num: int) -> str:
    """
    Extracts plain text content from a specific page of a PDF document.
    Uses PyMuPDF (fitz) for text extraction.
    """
    with fitz.open(pdf_path) as doc:
        return doc[page_num].get_text("text")  # type: ignore

def extract_text_with_pdfplumber(pdf_path: str, pages: List[int]) -> str:
    """
    Extracts and merges text content from specified pages of a PDF using pdfplumber.
    Useful for more precise text extraction from tables.
    """
    merged_text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for p in pages:
            try:
                merged_text += pdf.pages[p].extract_text() + "\n"
            except:
                continue
    return merged_text.strip()

def safe_parse_json(content: str) -> Dict:
    """
    Safely parses a JSON string, handling common formatting issues from AI responses.
    Extracts the JSON object from within code blocks if present.
    """
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
    """
    Sends a batch of text from PDF pages to OpenAI for financial data extraction.
    Focuses on extracting data for the current year and categorizing historical data.
    """
    print(f"  🧠 GPT validating pages {', '.join(str(p+1) for p in page_ids)}")

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
- Focus only on data for year {current_year} under "Data"
- Put older years under "Historical Data"
- Do not guess or include unlabeled data
- Only include numeric values

The document you're reading is the official annual report for the year {current_year}. You must focus on extracting financial data for **exactly the year {current_year}**, even if the text contains numbers for other years like 2023 or 2024.

Only include data that explicitly corresponds to the year {current_year} under "Data".

If values for the same metric are shown for multiple years, select the one that is labeled for year {current_year}. Any values from years **before {current_year}** should go under "Historical Data".

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

        content = response.choices[0].message["content"].strip()  # type: ignore
        usage = response['usage']  # type: ignore

        with open("openai_responses_debug.txt", "a") as f:
            f.write(f"\n\n--- Pages {page_ids} ---\n{content}\n")

        return safe_parse_json(content), usage

    except Exception as e:
        print(f"   GPT failed on pages {page_ids}: {e}")
        return {}, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    
def ask_openai_for_known_keys(text: str, page_ids: List[int], year: int, keymap: Dict[str, List[str]]) -> Tuple[Dict, Dict]:
    """
    Asks OpenAI to extract values for a predefined set of financial keys from text.
    Used for consistent extraction once key structures are known.
    """
    print(f"  🧠 GPT extracting known keys for {year} from pages {', '.join(str(p+1) for p in page_ids)}")

    prompt_sections = []
    for st_type, keys in keymap.items():
        lines = "\n".join(f'- {k}' for k in keys)
        prompt_sections.append(f"{st_type}:\n{lines}")

    prompt_block = "\n\n".join(prompt_sections)

    try:
        response = openai.ChatCompletion.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a financial data extractor."},
                {
                    "role": "user",
                    "content": f"""
This is extracted text from a company's annual report. Please only extract **values** for the exact line items below. Do not guess anything else.

Use this format:
{{
  "Statement Type": "...",
  "Data": {{ "Line Item": "Value", ... }}
}}

Only include numeric values for the year {year}. If a value isn’t present, skip it.

Requested line items:
{prompt_block}

Text:
{text}
"""
                }
            ],
            temperature=0,
            max_tokens=1200
        )

        content = response.choices[0].message["content"].strip()  # type: ignore
        usage = response['usage']  # type: ignore

        with open("openai_responses_debug.txt", "a") as f:
            f.write(f"\n\n--- Pages {page_ids} (known keys for {year}) ---\n{content}\n")

        return safe_parse_json(content), usage

    except Exception as e:
        print(f"   GPT (known keys) failed on pages {page_ids}: {e}")
        return {}, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

if __name__ == "__main__":
    pdf_files = [f for f in os.listdir(PDF_FOLDER) if f.lower().endswith(".pdf")]
    if not pdf_files:
        print(" No  pdfs found in /pdfs")
        exit(1)

    # Optional: skip already parsed files in /parsed_json
    parsed_filenames = set(f.replace(".json", "") for f in os.listdir(OUTPUT_FOLDER))

    # Sort from most recent year to oldest
    sorted_pdfs = sorted(pdf_files, key=lambda x: get_pdf_year(x), reverse=True)
    reference_keymap = {}

    global_reference_keymap = {}

    # Delay loading reference keys until 2024 is parsed
    if any("2024" in f for f in pdf_files):
        if os.path.exists(REFERENCE_KEYS_FILE):
            with open(REFERENCE_KEYS_FILE, "r") as f:
                global_reference_keymap = json.load(f)
        else:
            print("⚠️ reference_keys_2024.json not found. It will be created when 2024 is parsed.")
    else:
        print(" No 2024 report found. Cannot continue without a 2024 file to extract reference keys.")
        exit(1)

    for idx, pdf_filename in enumerate(sorted_pdfs):
        pdf_path = os.path.join(PDF_FOLDER, pdf_filename)
        basename = os.path.splitext(pdf_filename)[0]
        TICKER = basename.split("_")[0].upper()
        year = get_pdf_year(pdf_path)

        if basename in parsed_filenames:
            print(f"⏩ Skipping already parsed file: {basename}")
            continue

        print(f"\n📄 Parsing: {pdf_path}")

        # First-pass: pages with keywords and numbers
        matched_pages = []
        with fitz.open(pdf_path) as doc:
            for i in range(doc.page_count):
                page = doc[i]
                text = page.get_text("text") # type: ignore
                if any(k in text.lower() for k in KEYWORDS) and has_numbers(text):
                    matched_pages.append(i)
        print(f"\n🔍 First-pass matched pages (keywords + numbers): {len(matched_pages)} → {[p+1 for p in matched_pages]}")

        # Second-pass: pages with relevant financial tables
        second_pass = []
        for p in matched_pages:
            text = get_page_text(pdf_path, p)
            if is_relevant_financial_table(text):
                second_pass.append(p)
        print(f"\n🔎 Second-pass filtered pages (financial tables): {len(second_pass)} → {[p+1 for p in second_pass]}")

        # Third-pass: pages with strong structure
        filtered_pages = []
        for p in second_pass:
            text = get_page_text(pdf_path, p)
            if strong_structural_signal_adjusted(text):
                filtered_pages.append(p)
        print(f"\nFinal filtered pages (well-structured tables): {len(filtered_pages)} → {[p+1 for p in filtered_pages]}")

        extracted = {
            "Income Statement": {},
            "Balance Sheet": {},
            "Cash Flow Statement": {}
        }
        total_tokens = 0

        for i in range(0, len(filtered_pages), BATCH_SIZE):
            batch = filtered_pages[i:i + BATCH_SIZE]
            batch_text = extract_text_with_pdfplumber(pdf_path, batch)
            if not batch_text.strip():
                continue

            if idx == 0:
                result, usage = ask_openai_batch(batch_text, batch, year)
            else:
                result, usage = ask_openai_for_known_keys(batch_text, batch, year, global_reference_keymap)


            total_tokens += usage["total_tokens"]

            if result and "Statement Type" in result:
                st_type = result["Statement Type"]
                if st_type in extracted:
                    extracted[st_type].update(result.get("Data", {}))

        if idx == 0:
            reference_keymap = {
                st: list(extracted[st].keys())
                for st in ["Income Statement", "Balance Sheet", "Cash Flow Statement"]
                if extracted[st]
            }

            with open(os.path.join(OUTPUT_FOLDER, f"reference_keys_{year}.json"), "w") as f:
                json.dump(reference_keymap, f, indent=2)
            print(f"💾 Saved reference keys to reference_keys_{year}.json")


        print(f"\n {year} Extracted Data for {TICKER}:")
        for st, items in extracted.items():
            if items:
                print(f"\n📘 {st}")
                for k, v in items.items():
                    print(f"  - {k}: {v}")

        filename = os.path.join(OUTPUT_FOLDER, f"{TICKER}_{year}.json")
        with open(filename, "w") as f:
            json.dump({
                "ticker": TICKER,
                "year": year,
                "name": TICKER,
                "ir_url": "",
                "data": {
                    "Income Statement": extracted["Income Statement"],
                    "Balance Sheet": extracted["Balance Sheet"],
                    "Cash Flow Statement": extracted["Cash Flow Statement"]
                },
                "tokens_used": total_tokens
            }, f, indent=2)

        print(f"\nSaved to {filename} — Tokens used: {total_tokens}")
