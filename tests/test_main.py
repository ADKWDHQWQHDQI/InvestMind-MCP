import pytest
import os
import json
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from src.main import app
from src.tools.portfolio import get_holdings, get_portfolio_summary
from src.tools.news import get_portfolio_news
from src.tools.watchlist import update_watchlist, get_watchlist_summary
from src.security.auth import current_user_id, current_decryption_key, create_access_token
from src.security.encryption import EncryptionManager
from src.config import settings

client = TestClient(app)

from src.security.auth import register_session

def hash_password(password: str, salt: bytes) -> str:
    import hashlib
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000).hex()

# Helper to generate a valid test token
def get_test_token(user_id="user_test_1"):
    key, _ = EncryptionManager.derive_key("my-secure-passphrase")
    session_id = register_session(user_id, key)
    return create_access_token(user_id, session_id), key

@patch("src.main.get_db")
def test_api_auth_token_endpoint(mock_get_db):
    """Tests exchanging passphrase and password for JWT."""
    mock_db = MagicMock()
    mock_get_db.return_value = mock_db
    
    salt = os.urandom(16)
    pwd_hash = hash_password("my-password", salt)
    
    async def mock_find_one(*args, **kwargs):
        return {
            "user_id": "user_test_1",
            "salt": salt.hex(),
            "password_hash": pwd_hash
        }
    mock_db["users"].find_one = MagicMock()
    mock_db["users"].find_one.side_effect = mock_find_one
    
    with patch("src.main.get_portfolio") as mock_get_portfolio:
        async def mock_portfolio(*args, **kwargs):
            return {"salt": os.urandom(16).hex()}
        mock_get_portfolio.side_effect = mock_portfolio
        
        response = client.post(
            "/api/auth/token",
            json={
                "user_id": "user_test_1",
                "password": "my-password",
                "passphrase": "my-secure-passphrase"
            }
        )
        assert response.status_code == 200
        assert "token" in response.json()

def test_api_portfolio_upload_unauthorized():
    """Tests upload fails without Authorization header."""
    response = client.post(
        "/api/portfolio/upload",
        files={"file": ("test.pdf", b"%PDF-1.4...", "application/pdf")},
        data={"password": "PAN_PASSWORD"}
    )
    assert response.status_code == 401

@patch("src.main.parse_cas_pdf")
@patch("src.main.save_portfolio")
@patch("src.main.get_portfolio")
def test_api_portfolio_upload_authorized(mock_get_portfolio, mock_save_portfolio, mock_parse_cas_pdf):
    """Tests successful CAS upload with token."""
    token, key = get_test_token()
    mock_parse_cas_pdf.return_value = [{"isin": "INE020B01018", "name": "REC LTD", "quantity": 100.0}]
    mock_save_portfolio.return_value = True
    mock_get_portfolio.return_value = None  # New user
    
    response = client.post(
        "/api/portfolio/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("test.pdf", b"%PDF-1.4...", "application/pdf")},
        data={"password": "PAN_PASSWORD"}
    )
    
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert "Successfully parsed and encrypted" in response.json()["message"]

@pytest.mark.anyio
async def test_mcp_tool_unauthorized_access():
    """MCP tools should fail if ContextVars are not set (unauthorized)."""
    current_user_id.set("")
    current_decryption_key.set(b"")
    
    with pytest.raises(ValueError, match="Unauthorized or session key missing"):
        await get_holdings()

@pytest.mark.anyio
@patch("src.tools.portfolio.get_portfolio")
async def test_get_holdings_tool_authorized(mock_get_portfolio):
    """MCP tools retrieve holdings for authenticated context."""
    user_id = "user_test_1"
    raw_holdings = [{"symbol": "REC", "isin": "INE020B01018", "name": "REC LTD", "quantity": 100.0, "average_price": 0.0, "asset_class": "Equity"}]
    
    token, key = get_test_token(user_id)
    encrypted_blob = EncryptionManager.encrypt(json.dumps(raw_holdings), key)
    
    mock_get_portfolio.return_value = {
        "encrypted_holdings": encrypted_blob,
        "salt": os.urandom(16).hex()
    }
    
    # Simulate ContextVar population
    current_user_id.set(user_id)
    current_decryption_key.set(key)
    
    holdings = await get_holdings()
    assert len(holdings) == 1
    assert holdings[0]["symbol"] == "REC"
    assert holdings[0]["quantity"] == 100.0

@pytest.mark.anyio
@patch("src.tools.portfolio.get_holdings")
@patch("src.tools.portfolio.get_live_prices")
@patch("src.tools.portfolio.get_ticker_info")
@patch("src.tools.portfolio.resolve_ticker")
async def test_get_portfolio_summary_tool(mock_resolve_ticker, mock_ticker_info, mock_live_prices, mock_get_holdings):
    user_id = "user_test_1"
    _, key = get_test_token(user_id)
    
    current_user_id.set(user_id)
    current_decryption_key.set(key)
    
    mock_resolve_ticker.return_value = "REC"
    mock_get_holdings.return_value = [
        {"symbol": "REC", "isin": "INE020B01018", "name": "REC LTD", "quantity": 10.0}
    ]
    mock_live_prices.return_value = {"REC": 500.0}
    mock_ticker_info.return_value = {
        "sector": "Financial Services (NBFC)",
        "dividend_yield": 0.05,
        "name": "REC Ltd"
    }
    
    summary = await get_portfolio_summary()
    assert summary["summary"]["total_valuation"] == 5000.0
    assert summary["summary"]["total_holdings_count"] == 1

@pytest.mark.anyio
@patch("src.tools.news.get_holdings")
@patch("src.tools.news.get_stock_news")
@patch("src.tools.news.resolve_ticker")
async def test_get_portfolio_news_tool(mock_resolve_ticker, mock_stock_news, mock_get_holdings):
    user_id = "user_test_1"
    _, key = get_test_token(user_id)
    current_user_id.set(user_id)
    current_decryption_key.set(key)
    
    mock_resolve_ticker.return_value = "REC"
    mock_get_holdings.return_value = [
        {"symbol": "REC", "isin": "INE020B01018", "name": "REC LTD", "quantity": 10.0}
    ]
    mock_stock_news.return_value = [
        {"symbol": "REC", "title": "REC Board interim dividend.", "source": "Mint", "link": "", "timestamp": ""}
    ]
    
    news = await get_portfolio_news()
    assert len(news) == 1
    assert news[0]["symbol"] == "REC"
