import pytest
import sqlite3
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../scripts')))

from structure import save_to_db, get_company_data, DB_PATH

@pytest.fixture(autouse=True)
def setup_database():
    # Ensure a clean database for each test
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    yield
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

def test_save_to_db_new_data():
    company_name = "TestCo"
    ticker = "TCO"
    structured_data = {
        "2024 Financials": {
            "Income Statement": {"Revenue": "1000", "Expenses": "500"},
            "Balance Sheet": {"Assets": "2000"}
        },
        "Historical Data (2014–2023)": {
            "Income Statement": {
                "2023": {"Revenue": "900"},
                "2022": {"Expenses": "450"}
            }
        }
    }

    save_to_db(company_name, ticker, structured_data)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM Company")
    count = cursor.fetchone()[0]
    assert count == 5 # 2 (2024) + 2 (2023) + 1 (2022)

    cursor.execute("SELECT metric, value, year, statement_type FROM Company WHERE ticker = ? ORDER BY year DESC, metric", (ticker,))
    rows = cursor.fetchall()
    conn.close()

    expected_rows = [
        ("Assets", 2000.0, 2024, "Balance Sheet"),
        ("Expenses", 500.0, 2024, "Income Statement"),
        ("Revenue", 1000.0, 2024, "Income Statement"),
        ("Revenue", 900.0, 2023, "Income Statement"),
        ("Expenses", 450.0, 2022, "Income Statement"),
    ]
    # Sort both lists for comparison as order might vary slightly
    assert sorted(rows) == sorted(expected_rows)

def test_save_to_db_insert_or_ignore():
    company_name = "TestCo"
    ticker = "TCO"
    structured_data_initial = {
        "2024 Financials": {
            "Income Statement": {"Revenue": "1000"}
        }
    }
    structured_data_duplicate = {
        "2024 Financials": {
            "Income Statement": {"Revenue": "1000"}
        }
    }

    save_to_db(company_name, ticker, structured_data_initial)
    save_to_db(company_name, ticker, structured_data_duplicate) # Should be ignored

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM Company WHERE ticker = ?", (ticker,))
    count = cursor.fetchone()[0]
    assert count == 1 # Only one entry for Revenue 2024
    conn.close()

def test_get_company_data():
    company_name = "TestCo"
    ticker = "TCO"
    structured_data = {
        "2024 Financials": {
            "Income Statement": {"Revenue": "1000"},
            "Balance Sheet": {"Assets": "2000"}
        },
        "Historical Data (2014–2023)": {
            "Income Statement": {"2023": {"Revenue": "900"}}
        }
    }
    save_to_db(company_name, ticker, structured_data)

    retrieved_data = get_company_data(ticker)

    expected_data = {
        "Income Statement": {
            2024: {"Revenue": 1000.0},
            2023: {"Revenue": 900.0}
        },
        "Balance Sheet": {
            2024: {"Assets": 2000.0}
        },
        "Cash Flow Statement": {}
    }
    assert retrieved_data == expected_data

def test_get_company_data_no_data():
    retrieved_data = get_company_data("NONEXISTENT")
    assert retrieved_data == {
        "Income Statement": {},
        "Balance Sheet": {},
        "Cash Flow Statement": {}
    }
