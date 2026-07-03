from datetime import datetime
from src.database.models import PortfolioDocument, WatchlistDocument

def test_portfolio_document_validation():
    doc = PortfolioDocument(
        user_id="user_123",
        encrypted_holdings="encrypted_blob_data==",
        salt="0123456789abcdef",
    )
    assert doc.user_id == "user_123"
    assert doc.encrypted_holdings == "encrypted_blob_data=="
    assert doc.salt == "0123456789abcdef"
    assert isinstance(doc.last_updated, datetime)

def test_watchlist_document_validation():
    doc = WatchlistDocument(
        user_id="user_123",
        encrypted_symbols="encrypted_watchlist_data=="
    )
    assert doc.user_id == "user_123"
    assert doc.encrypted_symbols == "encrypted_watchlist_data=="
    assert isinstance(doc.last_updated, datetime)
