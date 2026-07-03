import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.main import upload_cas, get_holdings, get_portfolio_summary, get_portfolio_news, update_watchlist, get_watchlist_summary

# Test base64 of standard text dummy CAS
DUMMY_PDF_BASE64 = "JVBERi0xLjQKJVRlc3QgUERGIA=="  # %PDF-1.4 %Test PDF in base64

@pytest.mark.anyio
@patch("src.main.parse_cas_pdf")
@patch("src.main.save_portfolio")
async def test_upload_cas_tool(mock_save_portfolio, mock_parse_cas_pdf):
    # Set up mock parser output
    mock_parse_cas_pdf.return_value = [
        {"isin": "INE020B01018", "name": "REC LTD", "quantity": 100.0}
    ]
    # Set up mock DB output
    mock_save_portfolio.return_value = True
    
    response = await upload_cas(
        user_id="user_test_1",
        cas_base64=DUMMY_PDF_BASE64,
        password="PAN_PASSWORD"
    )
    
    assert response["success"] is True
    assert response["holdings_count"] == 1
    assert "Successfully parsed" in response["message"]
    
    mock_parse_cas_pdf.assert_called_once()
    mock_save_portfolio.assert_called_once()

@pytest.mark.anyio
@patch("src.main.get_portfolio")
async def test_get_holdings_tool(mock_get_portfolio):
    # Prepare encrypted payload mock
    from src.security.encryption import EncryptionManager
    from src.config import settings
    
    raw_holdings = [{"symbol": "REC", "isin": "INE020B01018", "name": "REC LTD", "quantity": 100.0, "average_price": 0.0, "asset_class": "Equity"}]
    key, salt = EncryptionManager.derive_key(settings.SERVER_ENCRYPTION_PASSPHRASE)
    encrypted_blob = EncryptionManager.encrypt(str(raw_holdings).replace("'", '"'), key)
    
    mock_get_portfolio.return_value = {
        "encrypted_holdings": encrypted_blob,
        "salt": salt.hex()
    }
    
    holdings = await get_holdings(user_id="user_test_1")
    assert len(holdings) == 1
    assert holdings[0]["symbol"] == "REC"
    assert holdings[0]["quantity"] == 100.0

@pytest.mark.anyio
@patch("src.main.get_holdings")
@patch("src.main.get_live_prices")
async def test_get_portfolio_summary_tool(mock_live_prices, mock_get_holdings):
    mock_get_holdings.return_value = [
        {"symbol": "REC", "isin": "INE020B01018", "name": "REC LTD", "quantity": 10.0}
    ]
    mock_live_prices.return_value = {"REC": 500.0}
    
    summary = await get_portfolio_summary(user_id="user_test_1")
    
    assert "summary" in summary
    assert summary["summary"]["total_valuation"] == 5000.0  # 10 * 500
    assert summary["summary"]["total_holdings_count"] == 1
    assert len(summary["holdings"]) == 1
    assert summary["holdings"][0]["valuation"] == 5000.0
    assert summary["holdings"][0]["sector"] == "Financial Services (NBFC)"

@pytest.mark.anyio
@patch("src.main.get_holdings")
async def test_get_portfolio_news_tool(mock_get_holdings):
    mock_get_holdings.return_value = [
        {"symbol": "REC", "isin": "INE020B01018", "name": "REC LTD", "quantity": 10.0}
    ]
    
    news = await get_portfolio_news(user_id="user_test_1")
    assert len(news) > 0
    assert news[0]["symbol"] == "REC"
    assert "dividend" in news[0]["title"].lower()

@pytest.mark.anyio
@patch("src.main.save_watchlist")
@patch("src.main.get_watchlist")
async def test_watchlist_tools(mock_get_watchlist, mock_save_watchlist):
    mock_save_watchlist.return_value = True
    mock_get_watchlist.return_value = ["REC", "INFY"]
    
    update_res = await update_watchlist("user_test_1", ["REC", "INFY"])
    assert update_res["success"] is True
    
    watchlist_summary = await get_watchlist_summary("user_test_1")
    assert watchlist_summary["user_id"] == "user_test_1"
    assert len(watchlist_summary["watchlist"]) == 2
    assert watchlist_summary["watchlist"][0]["symbol"] == "REC"
    assert watchlist_summary["watchlist"][0]["price"] is not None
