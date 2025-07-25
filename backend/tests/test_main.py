import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import os
import json
import sys # Added sys import

# Assuming your main.py is in backend/scripts
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../scripts')))
from backend.scripts.main import app, PDF_DIR, COMPANY_TABLE_PATH 

client = TestClient(app)

@pytest.fixture(autouse=True)
def mock_dependencies():
    with (
        patch('main.quick_scrape') as mock_quick_scrape,
        patch('main.deep_scrape') as mock_deep_scrape,
        patch('main.parse_pdf_final') as mock_parse_pdf_final,
        patch('main.save_to_db') as mock_save_to_db,
        patch('main.get_company_data') as mock_get_company_data,
        patch('os.listdir') as mock_listdir,
        patch('os.path.exists') as mock_exists,
        patch('builtins.open', new_callable=MagicMock) as mock_open,
    ): 
        yield {
            "mock_quick_scrape": mock_quick_scrape,
            "mock_deep_scrape": mock_deep_scrape,
            "mock_parse_pdf_final": mock_parse_pdf_final,
            "mock_save_to_db": mock_save_to_db,
            "mock_get_company_data": mock_get_company_data,
            "mock_listdir": mock_listdir,
            "mock_exists": mock_exists,
            "mock_open": mock_open,
        }

@pytest.fixture
def setup_company_table(mock_dependencies):
    mock_dependencies["mock_exists"].return_value = True
    mock_dependencies["mock_open"].return_value.__enter__.return_value.read.return_value = json.dumps({
        "TEST": {"name": "Test Company", "ticker": "TEST", "investor_relations_url": "http://test.com"}
    })


def test_scrape_success(mock_dependencies):
    mock_dependencies["mock_quick_scrape"].return_value = ("Test Company", "TEST", "http://test.com", True)
    mock_dependencies["mock_listdir"].side_effect = [[], ["TEST_2024.pdf"]]
    mock_dependencies["mock_parse_pdf_final"].return_value = {"Income Statement": {"Revenue": 100}}

    response = client.get("/scrape/TEST")

    assert response.status_code == 200
    assert response.json()["message"] == "Pipeline completed successfully."
    mock_dependencies["mock_quick_scrape"].assert_called_once_with("TEST")
    mock_dependencies["mock_parse_pdf_final"].assert_called_once()
    mock_dependencies["mock_save_to_db"].assert_called_once()

def test_scrape_quick_scrape_fails_deep_scrape_succeeds(mock_dependencies):
    mock_dependencies["mock_quick_scrape"].side_effect = Exception("Quick scrape failed")
    mock_dependencies["mock_deep_scrape"].return_value = ("Test Company", "TEST", "http://test.com", True)
    mock_dependencies["mock_listdir"].side_effect = [[], ["TEST_2024.pdf"]]
    mock_dependencies["mock_parse_pdf_final"].return_value = {"Income Statement": {"Revenue": 100}}

    response = client.get("/scrape/TEST")

    assert response.status_code == 200
    assert response.json()["message"] == "Pipeline completed successfully."
    mock_dependencies["mock_quick_scrape"].assert_called_once_with("TEST")
    mock_dependencies["mock_deep_scrape"].assert_called_once_with("TEST")
    mock_dependencies["mock_parse_pdf_final"].assert_called_once()
    mock_dependencies["mock_save_to_db"].assert_called_once()

def test_scrape_both_scrapes_fail(mock_dependencies):
    mock_dependencies["mock_quick_scrape"].side_effect = Exception("Quick scrape failed")
    mock_dependencies["mock_deep_scrape"].side_effect = Exception("Deep scrape failed")

    response = client.get("/scrape/TEST")

    assert response.status_code == 500
    assert response.json()["detail"] == "Both scraping methods failed."
    mock_dependencies["mock_quick_scrape"].assert_called_once_with("TEST")
    mock_dependencies["mock_deep_scrape"].assert_called_once_with("TEST")
    mock_dependencies["mock_parse_pdf_final"].assert_not_called()
    mock_dependencies["mock_save_to_db"].assert_not_called()

def test_get_company_data_success(mock_dependencies):
    mock_dependencies["mock_get_company_data"].return_value = {"Income Statement": {"2024": {"Revenue": 100}}}

    response = client.get("/api/company_data/TEST")

    assert response.status_code == 200
    assert response.json() == {"Income Statement": {"2024": {"Revenue": 100}}}
    mock_dependencies["mock_get_company_data"].assert_called_once_with("TEST")

def test_get_company_data_not_found(mock_dependencies):
    mock_dependencies["mock_get_company_data"].return_value = {}

    response = client.get("/api/company_data/NONEXISTENT")

    assert response.status_code == 404
    assert response.json()["detail"] == "No financial data found for NONEXISTENT"
    mock_dependencies["mock_get_company_data"].assert_called_once_with("NONEXISTENT")
