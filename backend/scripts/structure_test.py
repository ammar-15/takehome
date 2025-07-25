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

REFERENCE_METRICS_PATH = os.path.join(os.path.dirname(__file__), "../parsed_json/reference_keys_2024.json")


def clean_value(value):
    try:
        return float(str(value).replace(",", "").replace("$", "").replace("€", "").strip())
    except ValueError:
        return None


def ensure_tables(cursor):
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
PARSED_JSON_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../parsed_json"))


def load_all_json_files(folder_path: str):
    files = Path(folder_path).glob("*.json")
    return [json.load(open(file, "r")) for file in files if file.name.endswith(".json")]


def detect_filing_year(data: dict) -> int:
    years = set()
    for section in ["Income Statement", "Balance Sheet", "Cash Flow Statement"]:
        for k in data.get(section, {}).keys():
            for y in range(2014, 2026):
                if str(y) in k:
                    years.add(y)
    return max(years) if years else 2024


def openai_deduplicate_2024(rows_2024, filing_year: int):
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

        name = parsed.get("name", parsed["ticker"])
        ir_url = parsed.get("ir_url", "")
        ticker = parsed["ticker"]
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

        def match_metric(ref_metric: str, available_metrics: dict) -> str:
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
