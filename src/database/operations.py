import json
import logging
from datetime import datetime
from src.database.connection import get_db
from src.security.auth import current_decryption_key
from src.security.encryption import EncryptionManager

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
    Encrypts and saves the user's watchlist symbols in MongoDB.
    """
    try:
        db = await get_db()
        if db is None:
            logger.error("MongoDB not available.")
            return False
            
        key = current_decryption_key.get()
        if not key:
            raise ValueError("Decryption/Encryption key missing for this session.")
            
        # Normalize and serialize
        clean_symbols = [s.upper().strip() for s in symbols if s]
        serialized = json.dumps(clean_symbols)
        
        # Encrypt the watchlist payload
        encrypted_symbols = EncryptionManager.encrypt(serialized, key)
        
        collection = db["watchlists"]
        await collection.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "encrypted_symbols": encrypted_symbols,
                    "last_updated": datetime.utcnow()
                }
            },
            upsert=True
        )
        logger.info(f"Successfully saved encrypted watchlist for user: {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error saving watchlist for user {user_id}: {e}")
        return False

async def get_watchlist(user_id: str) -> list[str]:
    """
    Retrieves and decrypts the user's watchlist symbols from MongoDB.
    """
    try:
        db = await get_db()
        if db is None:
            logger.error("MongoDB not available.")
            return []
            
        key = current_decryption_key.get()
        if not key:
            raise ValueError("Decryption/Encryption key missing for this session.")
            
        collection = db["watchlists"]
        doc = await collection.find_one({"user_id": user_id})
        if doc:
            encrypted_symbols = doc.get("encrypted_symbols")
            if encrypted_symbols:
                decrypted = EncryptionManager.decrypt(encrypted_symbols, key)
                return json.loads(decrypted)
        return []
    except Exception as e:
        logger.error(f"Error retrieving watchlist for user {user_id}: {e}")
        return []
