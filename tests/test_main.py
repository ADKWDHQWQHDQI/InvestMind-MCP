import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.main import upload_cas, get_holdings, get_portfolio_summary, get_portfolio_news, update_watchlist, get_watchlist_summary

DUMMY_PDF_BASE64 = "JVBERi0xLjQKJVRlc3QgUERGIA=="

@pytest.mark.anyio
@patch("src.main.parse_cas_pdf")
@patch("src.main.save_portfolio")
@patch("src.main.resolve_ticker")
async def test_upload_cas_tool(mock_resolve_ticker, mock_save_portfolio, mock_parse_cas_pdf):
    # Set up mock outputs
    mock_parse_cas_pdf.return_value = [
        {"isin": "INE020B01018", "name": "REC LTD", "quantity": 100.0}
    ]
    mock_save_portfolio.return_value = True
    mock_resolve_ticker.return_value = "REC"
    
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
    mock_resolve_ticker.assert_called_once()

@pytest.mark.anyio
@patch("src.main.get_portfolio")
async def test_get_holdings_tool(mock_get_portfolio):
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
@patch("src.main.get_ticker_info")
async def test_get_portfolio_summary_tool(mock_ticker_info, mock_live_prices, mock_get_holdings):
    mock_get_holdings.return_value = [
        {"symbol": "REC", "isin": "INE020B01018", "name": "REC LTD", "quantity": 10.0}
    ]
    mock_live_prices.return_value = {"REC": 500.0}
    mock_ticker_info.return_value = {
        "sector": "Financial Services (NBFC)",
        "dividend_yield": 0.05,
        "name": "REC Ltd"
    }
    
    summary = await get_portfolio_summary(user_id="user_test_1")
    
    assert "summary" in summary
    assert summary["summary"]["total_valuation"] == 5000.0  # 10 * 500
    assert summary["summary"]["total_holdings_count"] == 1
    assert len(summary["holdings"]) == 1
    assert summary["holdings"][0]["valuation"] == 5000.0
    assert summary["holdings"][0]["sector"] == "Financial Services (NBFC)"

@pytest.mark.anyio
@patch("src.main.get_holdings")
@patch("src.main.get_stock_news")
async def test_get_portfolio_news_tool(mock_stock_news, mock_get_holdings):
    mock_get_holdings.return_value = [
        {"symbol": "REC", "isin": "INE020B01018", "name": "REC LTD", "quantity": 10.0}
    ]
    mock_stock_news.return_value = [
        {"symbol": "REC", "title": "REC Board declares an interim dividend.", "source": "Mint", "link": "", "timestamp": "2026-07-03 12:00:00"}
    ]
    
    news = await get_portfolio_news(user_id="user_test_1")
    assert len(news) == 1
    assert news[0]["symbol"] == "REC"
    assert "dividend" in news[0]["title"].lower()

@pytest.mark.anyio
@patch("src.main.save_watchlist")
@patch("src.main.get_watchlist")
@patch("src.main.get_live_prices")
async def test_watchlist_tools(mock_live_prices, mock_get_watchlist, mock_save_watchlist):
    mock_save_watchlist.return_value = True
    mock_get_watchlist.return_value = ["REC", "INFY"]
    mock_live_prices.return_value = {"REC": 500.0, "INFY": 1500.0}
    
    update_res = await update_watchlist("user_test_1", ["REC", "INFY"])
    assert update_res["success"] is True
    
    watchlist_summary = await get_watchlist_summary("user_test_1")
    assert watchlist_summary["user_id"] == "user_test_1"
    assert len(watchlist_summary["watchlist"]) == 2
    assert watchlist_summary["watchlist"][0]["symbol"] == "REC"
    assert watchlist_summary["watchlist"][0]["price"] == 500.0
