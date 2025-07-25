import pytest
from unittest.mock import patch, MagicMock
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../scripts')))

from parser import parse_pdf_final, safe_parse_json, ask_openai_batch

@pytest.fixture
def mock_pdf_file(tmp_path):
    # Create a dummy PDF file for testing
    pdf_content = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R>>endobj\n4 0 obj<</Length 55>>stream\nBT /F1 12 Tf 100 700 Td (Hello World) Tj ET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f\n0000000009 00000 n\n0000000074 00000 n\n0000000120 00000 n\n0000000210 00000 n\ntrailer<</Size 5/Root 1 0 R>>startxref\n290\n%%EOF"
    pdf_path = tmp_path / "test.pdf"
    pdf_path.write_bytes(pdf_content)
    return str(pdf_path)

@pytest.fixture(autouse=True)
def mock_openai_api():
    with patch('parser.openai.ChatCompletion.create') as mock_create:
        mock_create.return_value = MagicMock(
            choices=[MagicMock(message={'content': '```json\n{"Statement Type": "Income Statement", "Data": {"Revenue": "100"}, "Historical Data": {"2023": {"Revenue": "90"}}}\n```'})],
            usage={'prompt_tokens': 10, 'completion_tokens': 10, 'total_tokens': 20}
        )
        yield mock_create

@pytest.fixture(autouse=True)
def mock_fitz_open():
    with patch('parser.fitz.open') as mock_fitz:
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_page.get_text.return_value = "Income Statement\nRevenue 100\n2023 Revenue 90"
        mock_doc.__enter__.return_value = [mock_page]
        mock_doc.__exit__.return_value = None
        yield mock_fitz

@pytest.fixture(autouse=True)
def mock_pdfplumber_open():
    with patch('parser.pdfplumber.open') as mock_pdfplumber:
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Income Statement\nRevenue 100\n2023 Revenue 90"
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__.return_value = mock_pdf
        mock_pdf.__exit__.return_value = None
        yield mock_pdfplumber

def test_parse_pdf_final_success(mock_pdf_file):
    result = parse_pdf_final(mock_pdf_file)
    assert "Revenue" in result
    assert result["Revenue"] == 100 # Assuming the mock returns this

def test_safe_parse_json_valid_json():
    content = '```json\n{"key": "value"}\n```'
    result = safe_parse_json(content)
    assert result == {"key": "value"}

def test_safe_parse_json_invalid_json():
    content = 'invalid json'
    result = safe_parse_json(content)
    assert result == {}

def test_ask_openai_batch_success(mock_openai_api):
    text = "Some financial text"
    page_ids = [0, 1]
    result, usage = ask_openai_batch(text, page_ids)
    assert "Statement Type" in result
    assert usage["total_tokens"] == 20
