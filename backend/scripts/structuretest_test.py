import os
import json
import re
import sqlite3
from pathlib import Path
from dotenv import load_dotenv

# Load .env
load_dotenv()

# Paths
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data.sqlite"))
PARSED_JSON_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../parsed_jsonAYDEN2"))

def clean_value(value):
    """
    Cleans and standardizes a financial value:
    - Removes letters, symbols, parentheses
    - Converts values ≤ 99999 to raw by multiplying by 1,000,000
    """
    if value is None:
        return None
    try:
        raw = str(value)
        raw = re.sub(r"[^\d.]", "", raw)
        num = float(raw)
        if abs(num) < 100000:
            num *= 1_000_000
        return round(num, 1)
    except:
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

# Explicit ordering to preserve JSON output structure
METRIC_ORDER = {
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


def override_and_save_to_db(name, ticker, ir_url, year, data):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    ensure_tables(cursor)

    # Save company info
    cursor.execute("""
        INSERT OR IGNORE INTO CompanyMetadata (ticker, name, ir_url)
        VALUES (?, ?, ?)
    """, (ticker, name, ir_url))

    # Delete previous entries for this ticker+year
    cursor.execute("DELETE FROM Company WHERE ticker = ? AND year = ?", (ticker, year))

    # Insert cleaned data
    for stype in ["Income Statement", "Balance Sheet", "Cash Flow Statement"]:
        section = data.get(stype, {})
        for metric in METRIC_ORDER.get(stype, []):
            val = section.get(metric)
            cleaned = clean_value(val)
            if cleaned is not None:
                cursor.execute("""
                    INSERT INTO Company (name, ticker, year, statement_type, metric, value)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (name, ticker, year, stype, metric, cleaned))

    conn.commit()
    conn.close()
    print(f"[💾 SAVED] {name} ({ticker}) — {year}")

def detect_year_from_filename(filename):
    match = re.search(r"_(\d{4})", filename)
    return int(match.group(1)) if match else None

def process_all():
    print("[🚀 Running structure_test.py]")
    def extract_year(path):
        match = re.search(r"_(\d{4})", path.name)
        return int(match.group(1)) if match else 0

    files = sorted(Path(PARSED_JSON_DIR).glob("*.json"), key=extract_year, reverse=True)
    print(f"[📂 Found {len(files)} files]")

    for path in files:
        try:
            with open(path, "r") as f:
                parsed = json.load(f)
        except Exception as e:
            print(f"[❌ ERROR] Could not load {path.name}: {e}")
            continue

        if "data" not in parsed or "ticker" not in parsed:
            print(f"[⚠️ Skipped] {path.name} — missing 'data' or 'ticker'")
            continue

        name = parsed.get("name", parsed["ticker"])
        ticker = parsed["ticker"]
        ir_url = parsed.get("ir_url", "")
        year = detect_year_from_filename(path.name) or parsed.get("year", 2024)
        data = parsed["data"]

        override_and_save_to_db(name, ticker, ir_url, year, data)

if __name__ == "__main__":
    process_all()
