import logging
from typing import Optional
from datetime import datetime
from src.mcp_server import mcp
from src.database.connection import get_db
from src.security.auth import get_authenticated_context
from src.database.operations import get_portfolio, get_watchlist
from src.security.encryption import EncryptionManager
import json

logger = logging.getLogger("investmind.tools.preferences")

@mcp.tool()
async def get_preferences() -> dict:
    """
    Retrieves the authenticated user's preferences.
    """
    try:
        uid, _ = get_authenticated_context()
        db = await get_db()
        if db is None:
            return {"success": False, "message": "Database connection unavailable."}
            
        pref = await db["preferences"].find_one({"user_id": uid})
        if not pref:
            # Default preferences
            return {
                "success": True,
                "preferences": {
                    "user_id": uid,
                    "currency": "INR",
                    "language": "en",
                    "market": "IN",
                    "theme": "dark"
                }
            }
        return {
            "success": True,
            "preferences": {
                "user_id": pref["user_id"],
                "currency": pref.get("currency", "INR"),
                "language": pref.get("language", "en"),
                "market": pref.get("market", "IN"),
                "theme": pref.get("theme", "dark")
            }
        }
    except ValueError as ve:
        return {"success": False, "message": str(ve)}

@mcp.tool()
async def update_preferences(
    currency: Optional[str] = None,
    language: Optional[str] = None,
    market: Optional[str] = None,
    theme: Optional[str] = None
) -> dict:
    """
    Updates preferences for currency, language, market, and visual theme.
    """
    try:
        uid, _ = get_authenticated_context()
        db = await get_db()
        if db is None:
            return {"success": False, "message": "Database connection unavailable."}
            
        updates = {}
        if currency:
            updates["currency"] = currency.upper().strip()
        if language:
            updates["language"] = language.lower().strip()
        if market:
            updates["market"] = market.upper().strip()
        if theme:
            updates["theme"] = theme.lower().strip()
            
        if not updates:
            return {"success": False, "message": "No updates provided."}
            
        updates["last_updated"] = datetime.utcnow()
        
        await db["preferences"].update_one(
            {"user_id": uid},
            {"$set": updates},
            upsert=True
        )
        return {"success": True, "message": "Preferences updated successfully."}
    except ValueError as ve:
        return {"success": False, "message": str(ve)}

@mcp.tool()
async def set_currency(currency: str) -> dict:
    """Sets default display currency (e.g. INR, USD)."""
    return await update_preferences(currency=currency)

@mcp.tool()
async def set_language(language: str) -> dict:
    """Sets interface language (e.g. en, hi)."""
    return await update_preferences(language=language)

@mcp.tool()
async def set_market(market: str) -> dict:
    """Sets target region/market (e.g. IN, US)."""
    return await update_preferences(market=market)

@mcp.tool()
async def set_theme(theme: str) -> dict:
    """Sets visual theme (e.g. dark, light)."""
    return await update_preferences(theme=theme)

@mcp.tool()
async def export_data() -> dict:
    """
    Decrypts and exports all of the user's encrypted holdings, watchlists, and preferences in JSON format.
    """
    try:
        uid, key = get_authenticated_context()
        db = await get_db()
        if db is None:
            return {"success": False, "message": "Database connection unavailable."}
            
        # 1. Fetch & Decrypt Portfolio
        portfolio_doc = await get_portfolio(uid)
        holdings = []
        if portfolio_doc and portfolio_doc.get("encrypted_holdings"):
            decrypted = EncryptionManager.decrypt(portfolio_doc["encrypted_holdings"], key)
            holdings = json.loads(decrypted)
            
        # 2. Fetch & Decrypt Watchlist
        watchlist_doc = await db["watchlists"].find_one({"user_id": uid})
        watchlist = []
        if watchlist_doc and watchlist_doc.get("encrypted_symbols"):
            decrypted = EncryptionManager.decrypt(watchlist_doc["encrypted_symbols"], key)
            watchlist = json.loads(decrypted)
            
        # 3. Fetch Preferences
        pref = await get_preferences()
        
        return {
            "success": True,
            "export_timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            "data": {
                "user_id": uid,
                "holdings": holdings,
                "watchlist": watchlist,
                "preferences": pref.get("preferences", {})
            }
        }
    except ValueError as ve:
        return {"success": False, "message": str(ve)}
    except Exception as e:
        return {"success": False, "message": str(e)}

@mcp.tool()
async def delete_data() -> dict:
    """
    Wipes portfolio holdings and watchlists while keeping the user account profile.
    """
    try:
        uid, _ = get_authenticated_context()
        db = await get_db()
        if db is None:
            return {"success": False, "message": "Database connection unavailable."}
            
        await db["portfolios"].update_one(
            {"user_id": uid},
            {"$set": {"encrypted_holdings": "", "last_updated": datetime.utcnow()}}
        )
        await db["watchlists"].delete_one({"user_id": uid})
        await db["alerts"].delete_many({"user_id": uid})
        
        return {"success": True, "message": "All financial and analytical portfolio data has been deleted."}
    except ValueError as ve:
        return {"success": False, "message": str(ve)}
