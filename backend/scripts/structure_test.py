import os
import json
import re
import openai
import sqlite3
from pathlib import Path
import difflib
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# 💾 DB Setup
DB_PATH = os.path.join(os.path.dirname(__file__), "../../data.sqlite")

REFERENCE_METRICS_PATH = os.path.join(os.path.dirname(__file__), "../parsed_jsonAYDEN2/reference_keys_2024.json")

SELECTED_KEYS = {
    "Income Statement": [
        "Revenue", "Cost of Revenue", "Gross Profit", "Operating Expenses",
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


def clean_value(value):
    """
    Cleans and converts a financial value to raw float.
    - Converts billion/million to raw number
    - Removes non-numeric symbols
    - Multiplies 5-digit or smaller numbers by 1,000
    """
    if value is None:
        return None

    raw = str(value).lower()

    # Remove non-numeric symbols and brackets
    raw = re.sub(r"[^\d.,\s\-a-z]", "", raw)
    raw = raw.replace(",", "").replace("(", "").replace(")", "").replace("+", "").replace("-", "").strip()

    multiplier = 1
    if "billion" in raw:
        multiplier = 1_000_000_000
        raw = raw.replace("billion", "")
    elif "million" in raw:
        multiplier = 1_000_000
        raw = raw.replace("million", "")
    elif "thousand" in raw:
        multiplier = 1_000
        raw = raw.replace("thousand", "")

    try:
        num = float(raw.strip()) * multiplier
        if abs(num) <= 99999:
            num *= 1000
        return round(num, 1)
    except:
        return None



def ensure_tables(cursor):
    """
    Ensures that the necessary SQLite tables (CompanyMetadata, Company) exist.
    Creates them if they do not already exist.
    """
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS CompanyMetadata (
            ticker TEXT PRIMARY KEY,
            name TEXT,
            ir_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Company (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            ticker TEXT,
            year INTEGER,
            statement_type TEXT,
            metric TEXT,
            value REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(name, ticker, year, statement_type, metric)
        )
    """)


# Where parsed JSONs live
PARSED_JSON_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../parsed_jsonROG"))


def load_all_json_files(folder_path: str):
    """
    Loads all JSON files from a specified folder path.
    Returns a list of parsed JSON objects.
    """
    files = Path(folder_path).glob("*.json")
    return [json.load(open(file, "r")) for file in files if file.name.endswith(".json")]


def detect_filing_year(data: dict) -> int:
    """
    Detects the filing year from the parsed financial data.
    Searches for year patterns within the data sections.
    """
    years = set()
    for section in ["Income Statement", "Balance Sheet", "Cash Flow Statement"]:
        for k in data.get(section, {}).keys():
            for y in range(2014, 2026):
                if str(y) in k:
                    years.add(y)
    return max(years) if years else 2024


def openai_deduplicate_2024(rows_2024, filing_year: int):
    """
    Uses OpenAI to deduplicate and normalize financial line items for the 2024 report.
    Returns a cleaned JSON object with standardized metrics.
    """
    system_prompt = f"""You are a financial data cleaning assistant. You will receive a JSON object containing Income Statement, Balance Sheet, and Cash Flow Statement line items for the year {filing_year}.

Your job is to:
1. Deduplicate similar line items (e.g., 'Net Income', 'Net Income Attributable to Common Shareholders').
2. Rename and normalize metrics to standardized labels.
3. Return a single cleaned version of the data as:
{{
  "Income Statement": {{ "Revenue": "...", "Gross Profit": "...", ... }},
  "Balance Sheet": {{ ... }},
  "Cash Flow Statement": {{ ... }}
}}
Limit to ~15 rows per section.

Output valid JSON only. No explanations, no markdown.
"""

    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(rows_2024)}
        ],
        temperature=0.3,
        max_tokens=1500,
    )

    raw = response.choices[0].message.content.strip() # type: ignore
    print("[\U0001f4be RAW OPENAI OUTPUT]", raw)
    raw = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(raw)


def check_existing_in_db(ticker: str, year: int, statement_type: str, metric: str):
    """
    Checks if a specific financial metric for a company and year already exists in the database.
    Prevents duplicate entries.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    ensure_tables(cursor)

    cursor.execute("""
        SELECT value FROM Company
        WHERE ticker = ? AND year = ? AND statement_type = ? AND metric = ?
    """, (ticker, year, statement_type, metric))

    result = cursor.fetchone()
    conn.close()
    return result


def safe_save_to_db(company_name: str, ticker: str, ir_url: str, filing_year: int, structured_data: dict):
    """
    Saves structured financial data to the SQLite database.
    Handles metadata and financial metrics, ensuring no duplicate entries.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    ensure_tables(cursor)

    cursor.execute("""
        INSERT OR IGNORE INTO CompanyMetadata (ticker, name, ir_url)
        VALUES (?, ?, ?)
    """, (ticker, company_name, ir_url))

    for stype in ["Income Statement", "Balance Sheet", "Cash Flow Statement"]:
        for metric, value in structured_data.get(stype, {}).items():
            val = clean_value(value)
            if val is None:
                continue

            if check_existing_in_db(ticker, filing_year, stype, metric):
                continue

            cursor.execute("""
                INSERT INTO Company (name, ticker, year, statement_type, metric, value)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (company_name, ticker, filing_year, stype, metric, val))

    for metric, year_vals in structured_data.get("Historical Data", {}).items():
        for year_str, value in year_vals.items():
            try:
                year = int(year_str)
            except ValueError:
                continue
            val = clean_value(value)
            if val is None:
                continue

            if check_existing_in_db(ticker, year, "Historical", metric):
                continue

            cursor.execute("""
                INSERT INTO Company (name, ticker, year, statement_type, metric, value)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (company_name, ticker, year, "Historical", metric, val))

    conn.commit()
    conn.close()
    print(f"[ SAVED] {company_name} ({ticker}) — filing year {filing_year}")


def process_all():
    """
    Main function to process all parsed JSON files.
    Handles 2024 reports first for reference key generation, then other years.
    """
    print("[🚀 Starting structure_test.py...]")
    files = sorted(Path(PARSED_JSON_DIR).glob("*.json"))
    print(f"[Loaded files from: {PARSED_JSON_DIR}]")
    print(f"[ File count: {len(files)}]")

    reference_keys = {}

    # Pass 1: Handle 2024 first
    for path in files:
        if path.name == "reference_keys_2024.json":
            continue

        if "2024" not in path.name:
            continue

        try:
            parsed = json.load(open(path, "r"))
        except Exception as e:
            print(f"[ Failed to load {path.name}] {e}")
            continue

        name = parsed.get("name", parsed.get("ticker", "Unknown"))
        ticker = parsed.get("ticker", "???")
        ir_url = parsed.get("ir_url", "")
        data = parsed["data"]
        canonical_data = {
            stype: metrics for stype, metrics in data.items()
            if stype in ["Income Statement", "Balance Sheet", "Cash Flow Statement"]
        }

        print(f"[ CLEANING 2024] {path.name} → {name}")
        try:
            deduped = openai_deduplicate_2024(canonical_data, 2024)
            with open(REFERENCE_METRICS_PATH, "w") as ref:
                json.dump(deduped, ref, indent=2)
            reference_keys = deduped
            final_clean = deduped.copy()
            final_clean["Historical Data"] = {
                metric: {"2024": val}
                for stype in deduped
                for metric, val in deduped[stype].items()
            }
            safe_save_to_db(name, ticker, ir_url, 2024, final_clean)
        except Exception as e:
            print(f"[ OpenAI Error] {e}")
            continue

    # Load reference keys from saved file
    try:
        reference_keys = json.load(open(REFERENCE_METRICS_PATH, "r"))
    except:
        print("[ Could not load reference_keys_2024.json after pass 1]")
        return

    # Pass 2: Process all other years
        # Process all years (2023–2015) using OpenAI to extract 10 best metrics per section
    for path in files:
        if path.name == "reference_keys_2024.json" or "2024" in path.name:
            continue

        try:
            parsed = json.load(open(path, "r"))
        except Exception as e:
            print(f"[ Failed to load {path.name}] {e}")
            continue

        if "data" not in parsed or "ticker" not in parsed:
            print(f"[⚠️ SKIPPED] {path.name} — missing required keys: {list(parsed.keys())}")
            continue

        name = parsed.get("name", parsed.get("ticker", "ROG"))
        ticker = "ROG"
        ir_url = parsed.get("ir_url", "")
        data = parsed["data"]

        try:
            match = re.search(r"_(\d{4})", path.name)
            filing_year = int(match.group(1)) if match else detect_filing_year(data)
        except:
            filing_year = detect_filing_year(data)

        canonical_data = {
            stype: metrics for stype, metrics in data.items()
            if stype in ["Income Statement", "Balance Sheet", "Cash Flow Statement"]
        }

        # 🧠 Use OpenAI to reduce to 10 useful rows per section
        system_prompt = f"""You are a financial statement assistant.

You will be given raw financial data with many line items under:
- Income Statement
- Balance Sheet
- Cash Flow Statement

Your task is to:
1. Pick the 10 most important and informative metrics **for each section**.
2. Discard irrelevant, redundant, or overly specific ones.
3. Return exactly 3 objects: Income Statement, Balance Sheet, and Cash Flow Statement.

Only output valid compact JSON like:
{{
  "Income Statement": {{ "Revenue": ..., "Net Income": ... }},
  "Balance Sheet": {{ ... }},
  "Cash Flow Statement": {{ ... }}
}}

Do not explain anything. Just valid JSON.
"""

        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(canonical_data)}
                ],
                temperature=0.3,
                max_tokens=1500,
            )
            raw = response.choices[0].message.content.strip()  # type: ignore
            print(f"[🧠 OpenAI reduced {filing_year}]", path.name)
            raw = raw.replace("```json", "").replace("```", "").strip()
            deduped = json.loads(raw)
        except Exception as e:
            print(f"[❌ OpenAI error on {path.name}] {e}")
            continue

        # Construct Historical format
        historical_data = {}
        for stype in deduped:
            for metric, val in deduped[stype].items():
                historical_data.setdefault(metric, {})[str(filing_year)] = val

        deduped["Historical Data"] = historical_data

        # Save
        safe_save_to_db(name, ticker, ir_url, filing_year, deduped)


def match_metric(ref_metric: str, available_metrics: dict) -> str:
    """
    Finds the best matching metric from available metrics based on a reference metric.
    Uses difflib for fuzzy matching.
    """
    keys = list(available_metrics.keys())
    for k in keys:
        if k.lower().strip() == ref_metric.lower().strip():
            return k
    matches = difflib.get_close_matches(ref_metric, keys, n=1, cutoff=0.5)
    return matches[0] if matches else ""

    final_clean = {stype: {} for stype in reference_keys}
    for stype in reference_keys:
        if stype not in canonical_data:
            continue
        for ref_metric in reference_keys[stype]:
            matched_key = match_metric(ref_metric, canonical_data[stype])
            if matched_key:
                val = canonical_data[stype][matched_key]
                final_clean[stype][ref_metric] = val

        historical_data = {}
        for stype in final_clean:
            for metric, val in final_clean[stype].items():
                historical_data.setdefault(metric, {})[str(filing_year)] = val

        final_clean["Historical Data"] = historical_data
        safe_save_to_db(name, ticker, ir_url, filing_year, final_clean)

if __name__ == "__main__":
    process_all()
