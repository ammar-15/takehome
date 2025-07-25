# structure.py

import sqlite3
import os
from typing import Dict

DB_PATH = os.path.join(os.path.dirname(__file__), "../data.sqlite")

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

def clean_value(value):
    """
    Cleans and converts a financial value to a float.
    Removes currency symbols and commas, handles non-numeric values.
    """
    try:
        return float(str(value).replace(",", "").replace("$", "").replace("€", "").strip())
    except ValueError:
        return None

def save_to_db(company_name: str, structured_data: Dict):
    """
    Saves structured financial data to the SQLite database.
    Handles metadata and financial metrics, ensuring no duplicate entries.
    """
    ticker = structured_data.get("ticker")
    ir_url = structured_data.get("ir_url")
    data = structured_data.get("data", {})

    if not ticker or not data:
        print("[ERROR] Missing ticker or data.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    ensure_tables(cursor)

    # 🏢 Save company metadata
    cursor.execute("""
        INSERT OR IGNORE INTO CompanyMetadata (ticker, name, ir_url)
        VALUES (?, ?, ?)
    """, (ticker, company_name, ir_url))

    # 🧾 Save 2024 data first (preferred, always inserted)
    for statement_type in ["Income Statement", "Balance Sheet", "Cash Flow Statement"]:
        items = data.get(statement_type, {})
        for metric, value in items.items():
            value_float = clean_value(value)
            if value_float is None:
                continue
            cursor.execute("""
                INSERT OR REPLACE INTO Company (name, ticker, year, statement_type, metric, value)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (company_name, ticker, 2024, statement_type, metric, value_float))

    # 📆 Save historical data (2014–2023), but only if row does not already exist
    historical = data.get("Historical Data", {})
    for metric, year_values in historical.items():
        for year_str, value in year_values.items():
            try:
                year = int(year_str)
            except ValueError:
                continue
            value_float = clean_value(value)
            if value_float is None:
                continue

            # Skip if this (ticker, year, metric) already exists
            cursor.execute("""
                SELECT 1 FROM Company WHERE ticker = ? AND year = ? AND metric = ?
            """, (ticker, year, metric))
            exists = cursor.fetchone()

            if not exists:
                cursor.execute("""
                    INSERT INTO Company (name, ticker, year, statement_type, metric, value)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (company_name, ticker, year, "Historical", metric, value_float))

    conn.commit()
    conn.close()
    print(f"[DB] Data saved for {company_name} ({ticker})")

def load_from_db(ticker: str) -> dict:
    """
    Loads structured financial data for a given ticker from the database.
    Returns data organized by statement type and year.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    #  Ensure the table exists before querying
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

    cursor.execute("""
        SELECT year, statement_type, metric, value
        FROM Company
        WHERE ticker = ?
        ORDER BY year DESC
    """, (ticker,))

    rows = cursor.fetchall()
    conn.close()

    structured = {}

    for year, st_type, metric, value in rows:
        if st_type not in structured:
            structured[st_type] = {}
        if year not in structured[st_type]:
            structured[st_type][year] = {}
        structured[st_type][year][metric] = value

    return structured

