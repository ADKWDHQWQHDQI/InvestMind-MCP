import pytest
from unittest.mock import MagicMock, patch
from src.parser.cas_parser import parse_cas_pdf
from src.parser.normalizer import normalize_holdings

def test_normalize_holdings():
    raw = [
        {"isin": "INE020B01018", "name": "REC LTD", "quantity": 100.0},
        {"isin": "INE020B01018", "name": "REC LIMITED", "quantity": 50.0},  # Duplicate
        {"isin": "INE009A01021", "name": "INFOSYS LIMITED", "quantity": 10.0},
    ]
    normalized = normalize_holdings(raw)
    assert len(normalized) == 2
    
    # Check REC duplicate merged
    rec_holding = next(h for h in normalized if h["symbol"] == "REC")
    assert rec_holding["quantity"] == 150.0
    assert rec_holding["isin"] == "INE020B01018"
    
    # Check Infosys mapped
    infy_holding = next(h for h in normalized if h["symbol"] == "INFY")
    assert infy_holding["quantity"] == 10.0

@patch("src.parser.cas_parser.pypdf.PdfReader")
def test_parse_cas_pdf(mock_reader_cls):
    # Set up mock reader
    mock_reader = MagicMock()
    mock_reader.is_encrypted = True
    mock_reader.decrypt.return_value = 1  # Success
    
    mock_page = MagicMock()
    mock_page.extract_text.return_value = (
        "INE020B01018 REC LTD 100.00\n"
        "INE009A01021 INFY 50.00\n"
    )
    mock_reader.pages = [mock_page]
    mock_reader_cls.return_value = mock_reader
    
    holdings = parse_cas_pdf(b"dummy_pdf_bytes", "my-pan-password")
    assert len(holdings) == 2
    assert holdings[0]["isin"] == "INE020B01018"
    assert holdings[0]["quantity"] == 100.0
    assert holdings[1]["isin"] == "INE009A01021"
    assert holdings[1]["quantity"] == 50.0

@patch("src.parser.cas_parser.pypdf.PdfReader")
def test_parse_cas_pdf_wrong_password(mock_reader_cls):
    # Set up mock reader for password failure
    mock_reader = MagicMock()
    mock_reader.is_encrypted = True
    mock_reader.decrypt.return_value = 0  # Failure
    mock_reader_cls.return_value = mock_reader
    
    with pytest.raises(ValueError, match="Incorrect password for CAS PDF."):
        parse_cas_pdf(b"dummy_pdf_bytes", "wrong-password")
