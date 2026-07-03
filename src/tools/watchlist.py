import logging
import json
from datetime import datetime
from src.mcp_server import mcp
from src.database.connection import get_db
from src.security.auth import get_authenticated_context
from src.security.encryption import EncryptionManager
from src.market.api import get_live_prices

logger = logging.getLogger("investmind.tools.watchlist")

@mcp.tool()
async def create_watchlist(name: str) -> dict:
    """
    Creates a new custom watchlist.
    """
    try:
        uid, key = get_authenticated_context()
        db = await get_db()
        if db is None:
            return {"success": False, "message": "Database connection unavailable."}
            
        name = name.strip()
        existing = await db["watchlists"].find_one({"user_id": uid, "name": name})
        if existing:
            return {"success": False, "message": f"Watchlist '{name}' already exists."}
            
        # Encrypt empty list
        encrypted_empty = EncryptionManager.encrypt(json.dumps([]), key)
        
        await db["watchlists"].insert_one({
            "user_id": uid,
            "name": name,
            "encrypted_symbols": encrypted_empty,
            "last_updated": datetime.utcnow()
        })
        return {"success": True, "message": f"Watchlist '{name}' created successfully."}
    except ValueError as ve:
        return {"success": False, "message": str(ve)}
    except Exception as e:
        return {"success": False, "message": str(e)}

@mcp.tool()
async def get_watchlist(name: str) -> list[str]:
    """
    Retrieves and decrypts the symbol list inside a specific watchlist.
    """
    try:
        uid, key = get_authenticated_context()
        db = await get_db()
        if db is None:
            return []
            
        name = name.strip()
        doc = await db["watchlists"].find_one({"user_id": uid, "name": name})
        if doc and doc.get("encrypted_symbols"):
            decrypted = EncryptionManager.decrypt(doc["encrypted_symbols"], key)
            return json.loads(decrypted)
        return []
    except Exception as e:
        logger.error(f"Error getting watchlist {name}: {e}")
        return []

@mcp.tool()
async def delete_watchlist(name: str) -> dict:
    """
    Deletes a specific watchlist.
    """
    try:
        uid, _ = get_authenticated_context()
        db = await get_db()
        if db is None:
            return {"success": False, "message": "Database connection unavailable."}
            
        name = name.strip()
        result = await db["watchlists"].delete_one({"user_id": uid, "name": name})
        if result.deleted_count > 0:
            return {"success": True, "message": f"Watchlist '{name}' deleted successfully."}
        return {"success": False, "message": f"Watchlist '{name}' not found."}
    except ValueError as ve:
        return {"success": False, "message": str(ve)}
    except Exception as e:
        return {"success": False, "message": str(e)}

@mcp.tool()
async def rename_watchlist(old_name: str, new_name: str) -> dict:
    """
    Renames an existing watchlist.
    """
    try:
        uid, _ = get_authenticated_context()
        db = await get_db()
        if db is None:
            return {"success": False, "message": "Database connection unavailable."}
            
        old_name = old_name.strip()
        new_name = new_name.strip()
        
        result = await db["watchlists"].update_one(
            {"user_id": uid, "name": old_name},
            {"$set": {"name": new_name, "last_updated": datetime.utcnow()}}
        )
        if result.matched_count > 0:
            return {"success": True, "message": f"Watchlist renamed from '{old_name}' to '{new_name}'."}
        return {"success": False, "message": f"Watchlist '{old_name}' not found."}
    except ValueError as ve:
        return {"success": False, "message": str(ve)}
    except Exception as e:
        return {"success": False, "message": str(e)}

@mcp.tool()
async def add_watchlist_stock(name: str, symbol: str) -> dict:
    """
    Adds a stock symbol to a specific watchlist.
    """
    try:
        uid, key = get_authenticated_context()
        db = await get_db()
        if db is None:
            return {"success": False, "message": "Database connection unavailable."}
            
        name = name.strip()
        symbol = symbol.upper().strip()
        
        doc = await db["watchlists"].find_one({"user_id": uid, "name": name})
        if not doc:
            return {"success": False, "message": f"Watchlist '{name}' does not exist. Create it first."}
            
        symbols = json.loads(EncryptionManager.decrypt(doc["encrypted_symbols"], key))
        if symbol in symbols:
            return {"success": True, "message": f"{symbol} is already in watchlist '{name}'."}
            
        symbols.append(symbol)
        encrypted_payload = EncryptionManager.encrypt(json.dumps(symbols), key)
        
        await db["watchlists"].update_one(
            {"user_id": uid, "name": name},
            {"$set": {"encrypted_symbols": encrypted_payload, "last_updated": datetime.utcnow()}}
        )
        return {"success": True, "message": f"Added {symbol} to watchlist '{name}'."}
    except ValueError as ve:
        return {"success": False, "message": str(ve)}
    except Exception as e:
        return {"success": False, "message": str(e)}

@mcp.tool()
async def remove_watchlist_stock(name: str, symbol: str) -> dict:
    """
    Removes a stock symbol from a specific watchlist.
    """
    try:
        uid, key = get_authenticated_context()
        db = await get_db()
        if db is None:
            return {"success": False, "message": "Database connection unavailable."}
            
        name = name.strip()
        symbol = symbol.upper().strip()
        
        doc = await db["watchlists"].find_one({"user_id": uid, "name": name})
        if not doc:
            return {"success": False, "message": f"Watchlist '{name}' does not exist."}
            
        symbols = json.loads(EncryptionManager.decrypt(doc["encrypted_symbols"], key))
        if symbol not in symbols:
            return {"success": False, "message": f"{symbol} not found in watchlist '{name}'."}
            
        symbols.remove(symbol)
        encrypted_payload = EncryptionManager.encrypt(json.dumps(symbols), key)
        
        await db["watchlists"].update_one(
            {"user_id": uid, "name": name},
            {"$set": {"encrypted_symbols": encrypted_payload, "last_updated": datetime.utcnow()}}
        )
        return {"success": True, "message": f"Removed {symbol} from watchlist '{name}'."}
    except ValueError as ve:
        return {"success": False, "message": str(ve)}
    except Exception as e:
        return {"success": False, "message": str(e)}

@mcp.tool()
async def sort_watchlist(name: str, key: str = "symbol") -> list[str]:
    """
    Sorts watchlist symbols alphabetically (key='symbol') or by price (key='price').
    """
    symbols = await get_watchlist(name)
    if not symbols:
        return []
        
    if key.lower() == "price":
        prices = await get_live_prices(symbols)
        # Sort by live price (highest first, missing prices at the end)
        symbols.sort(key=lambda s: prices.get(s, 0.0), reverse=True)
    else:
        symbols.sort()
        
    return symbols

@mcp.tool()
async def watchlist_summary(name: str) -> dict:
    """
    Retrieves symbols and live price details for a watchlist.
    """
    symbols = await get_watchlist(name)
    if not symbols:
        return {"watchlist_name": name, "symbols_count": 0, "items": []}
        
    prices = await get_live_prices(symbols)
    items = [{"symbol": s, "price": prices.get(s)} for s in symbols]
    return {
        "watchlist_name": name,
        "symbols_count": len(symbols),
        "items": items
    }

@mcp.tool()
async def update_watchlist(symbols: list[str]) -> dict:
    """
    Updates the list of stock symbols monitored in the user's default watchlist.
    """
    try:
        uid, key = get_authenticated_context()
        db = await get_db()
        if db is None:
            return {"success": False, "message": "Database connection unavailable."}
            
        encrypted_payload = EncryptionManager.encrypt(json.dumps(symbols), key)
        
        await db["watchlists"].update_one(
            {"user_id": uid, "name": "default"},
            {"$set": {"encrypted_symbols": encrypted_payload, "last_updated": datetime.utcnow()}},
            upsert=True
        )
        return {"success": True, "message": "Watchlist updated successfully."}
    except Exception as e:
        return {"success": False, "message": str(e)}

@mcp.tool()
async def get_watchlist_summary() -> dict:
    """
    Retrieves the user's default watchlist stock symbols along with their live prices.
    """
    try:
        uid, _ = get_authenticated_context()
        res = await watchlist_summary("default")
        return {
            "user_id": uid,
            "watchlist": res.get("items", [])
        }
    except Exception as e:
        return {"error": str(e)}
