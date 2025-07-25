import pytest
from unittest.mock import patch, MagicMock
import os
import sys

# Add the scripts directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../scripts')))

from quick_scrape import scrapeticker, PDF_FOLDER

@pytest.fixture(autouse=True)
def mock_external_dependencies():
    with (
        patch('quick_scrape.openai.ChatCompletion.create') as mock_openai_create,
        patch('quick_scrape.sync_playwright') as mock_sync_playwright,
        patch('quick_scrape.requests.get') as mock_requests_get,
        patch('os.path.exists') as mock_os_path_exists,
        patch('builtins.open', new_callable=MagicMock) as mock_open,
        patch('os.remove') as mock_os_remove,
        patch('quick_scrape.os.makedirs') as mock_makedirs,
    ): 
        # Mock OpenAI response for find_ir_url_via_ai and ai_pick_best_link
        mock_openai_create.return_value.choices[0].message.content = "http://example.com/ir"

        # Mock Playwright page scan
        mock_page = MagicMock()
        mock_page.query_selector_all.return_value = []
        mock_page.inner_text.return_value = ""
        mock_page.url = "http://example.com"
        mock_page.get_attribute.return_value = None

        mock_browser = MagicMock()
        mock_browser.new_page.return_value = mock_page

        mock_sync_playwright.return_value.__enter__.return_value.chromium.launch.return_value = mock_browser

        # Mock requests.get for PDF download
        mock_requests_get.return_value.status_code = 200
        mock_requests_get.return_value.content = b'%PDF-1.4\n%\xed\xe0\xf3\xe2\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Count 0>>endobj\nxref\n0 3\n0000000000 65535 f\n0000000009 00000 n\n0000000074 00000 n\ntrailer<</Size 3/Root 1 0 R>>startxref\n123\n%%EOF' # Minimal valid PDF content

        yield {
            "mock_openai_create": mock_openai_create,
            "mock_sync_playwright": mock_sync_playwright,
            "mock_requests_get": mock_requests_get,
            "mock_os_path_exists": mock_os_path_exists,
            "mock_open": mock_open,
            "mock_os_remove": mock_os_remove,
            "mock_makedirs": mock_makedirs,
            "mock_page": mock_page,
        }

def test_scrapeticker_2024_pdf_found_and_other_years_attempted(mock_external_dependencies):
    # Mock that 2024 PDF link is found and downloaded
    mock_external_dependencies["mock_page"].query_selector_all.return_value = [
        MagicMock(get_attribute=lambda x: "http://example.com/report_2024.pdf")
    ]
    mock_external_dependencies["mock_requests_get"].return_value.status_code = 200
    mock_external_dependencies["mock_requests_get"].return_value.content = b'%PDF-1.4' # Valid PDF

    # Simulate that some PDFs are already downloaded for try_other_years
    mock_external_dependencies["mock_os_path_exists"].side_effect = lambda x: "TEST_2023.pdf" in x or "TEST_2022.pdf" in x

    company_name, ticker, ir_url, all_pdfs_found = scrapeticker("TEST")

    assert company_name == "TEST"
    assert ticker == "TEST"
    assert ir_url == "http://example.com/ir"
    # Expecting False because we only mocked 2024 and some others, not all 10 years
    assert all_pdfs_found == False

    # Verify calls
    mock_external_dependencies["mock_openai_create"].assert_called()
    mock_external_dependencies["mock_sync_playwright"].assert_called()
    mock_external_dependencies["mock_requests_get"].assert_called()
    mock_external_dependencies["mock_open"].assert_called()

def test_scrapeticker_2024_pdf_not_found(mock_external_dependencies):
    # Mock that no PDF link is found for 2024
    mock_external_dependencies["mock_page"].query_selector_all.return_value = []
    mock_external_dependencies["mock_openai_create"].return_value.choices[0].message.content = "http://example.com/ir"

    company_name, ticker, ir_url, all_pdfs_found = scrapeticker("TEST")

    assert company_name == "TEST"
    assert ticker == "TEST"
    assert ir_url == "http://example.com/ir"
    assert all_pdfs_found == False # No 2024 PDF means not all found

    # Verify calls
    mock_external_dependencies["mock_openai_create"].assert_called()
    mock_external_dependencies["mock_sync_playwright"].assert_called()
    # requests.get should not be called for PDF download if no PDF link is found
    mock_external_dependencies["mock_requests_get"].assert_not_called()

def test_download_pdf_invalid_file(mock_external_dependencies):
    # Mock requests.get to return non-PDF content
    mock_external_dependencies["mock_requests_get"].return_value.content = b'NOT A PDF'
    mock_external_dependencies["mock_requests_get"].return_value.status_code = 200

    # Call download_pdf directly
    result = scrapeticker.download_pdf("http://example.com/invalid.pdf", 2024, "TEST")

    assert result == False
    mock_external_dependencies["mock_os_remove"].assert_called_once()

def test_download_pdf_already_exists(mock_external_dependencies):
    # Mock that the file already exists
    mock_external_dependencies["mock_os_path_exists"].return_value = True

    # Call download_pdf directly
    result = scrapeticker.download_pdf("http://example.com/existing.pdf", 2024, "TEST")

    assert result == True
    mock_external_dependencies["mock_requests_get"].assert_not_called()
    mock_external_dependencies["mock_open"].assert_not_called()

