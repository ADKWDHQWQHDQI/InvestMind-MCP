import logging
from datetime import datetime
from src.database.connection import get_db

logger = logging.getLogger("investmind.database.operations")

async def save_portfolio(user_id: str, encrypted_holdings: str, salt: str) -> bool:
    """
    Saves or updates the user's encrypted portfolio in MongoDB.
    """
    try:
        db = await get_db()
        if db is None:
            logger.error("MongoDB not available.")
            return False
            
        collection = db["portfolios"]
        await collection.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "encrypted_holdings": encrypted_holdings,
                    "salt": salt,
                    "last_updated": datetime.utcnow()
                }
            },
            upsert=True
        )
        logger.info(f"Successfully saved encrypted portfolio for user: {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error saving portfolio for user {user_id}: {e}")
        return False

async def get_portfolio(user_id: str) -> dict:
    """
    Retrieves the user's encrypted portfolio details from MongoDB.
    """
    try:
        db = await get_db()
        if db is None:
            logger.error("MongoDB not available.")
            return None
            
        collection = db["portfolios"]
        doc = await collection.find_one({"user_id": user_id})
        return doc
    except Exception as e:
        logger.error(f"Error retrieving portfolio for user {user_id}: {e}")
        return None

async def save_watchlist(user_id: str, symbols: list[str]) -> bool:
    """
    Saves or updates the user's watchlist symbols in MongoDB.
    """
    try:
        db = await get_db()
        if db is None:
            logger.error("MongoDB not available.")
            return False
            
        collection = db["watchlists"]
        # Normalize symbols to uppercase
        clean_symbols = [s.upper().strip() for s in symbols if s]
        await collection.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "symbols": clean_symbols,
                    "last_updated": datetime.utcnow()
                }
            },
            upsert=True
        )
        logger.info(f"Successfully saved watchlist for user: {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error saving watchlist for user {user_id}: {e}")
        return False

async def get_watchlist(user_id: str) -> list[str]:
    """
    Retrieves the user's watchlist symbols from MongoDB.
    """
    try:
        db = await get_db()
        if db is None:
            logger.error("MongoDB not available.")
            return []
            
        collection = db["watchlists"]
        doc = await collection.find_one({"user_id": user_id})
        if doc:
            return doc.get("symbols", [])
        return []
    except Exception as e:
        logger.error(f"Error retrieving watchlist for user {user_id}: {e}")
        return []
