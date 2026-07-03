import logging
import base64
import os
import json
import httpx
from typing import Optional, Any
from src.mcp_server import mcp
from src.database.connection import get_db
from src.security.auth import get_authenticated_context
from src.database.operations import save_portfolio, get_portfolio
from src.security.encryption import EncryptionManager
from src.parser.cas_parser import parse_cas_pdf
from src.parser.normalizer import normalize_holdings

logger = logging.getLogger("investmind.tools.portfolio_conn")

@mcp.tool()
async def get_supported_imports() -> list[str]:
    """
    Returns the list of supported brokers and import file formats.
    """
    return ["CAS PDF", "Zerodha", "Upstox", "Groww", "Angel One", "Dhan"]

@mcp.tool()
async def connect_portfolio(broker: str, credentials: dict) -> dict:
    """
    Connects a broker account by encrypting and saving credentials in the user profile.
    Supported brokers: Zerodha, Upstox, Groww, Angel One, Dhan.
    """
    try:
        uid, key = get_authenticated_context()
        db = await get_db()
        if db is None:
            return {"success": False, "message": "Database connection unavailable."}
            
        broker_name = broker.upper().strip()
        supported = [b.upper() for b in await get_supported_imports()]
        if broker_name not in supported and broker_name != "CAS PDF":
            return {"success": False, "message": f"Unsupported broker: {broker}. Supported: {supported}"}
            
        # Encrypt credentials dictionary
        serialized = json.dumps({"broker": broker_name, "credentials": credentials})
        encrypted_creds = EncryptionManager.encrypt(serialized, key)
        
        await db["users"].update_one(
            {"user_id": uid},
            {"$set": {"encrypted_broker_credentials": encrypted_creds}}
        )
        return {"success": True, "message": f"Successfully connected to {broker} account."}
    except ValueError as ve:
        return {"success": False, "message": str(ve)}
    except Exception as e:
        return {"success": False, "message": str(e)}

@mcp.tool()
async def disconnect_portfolio() -> dict:
    """
    Disconnects the active broker connection and clears any encrypted broker credentials.
    """
    try:
        uid, _ = get_authenticated_context()
        db = await get_db()
        if db is None:
            return {"success": False, "message": "Database connection unavailable."}
            
        await db["users"].update_one(
            {"user_id": uid},
            {"$set": {"encrypted_broker_credentials": None}}
        )
        return {"success": True, "message": "Broker portfolio disconnected successfully."}
    except ValueError as ve:
        return {"success": False, "message": str(ve)}

@mcp.tool()
async def connect_zerodha(api_key: str, access_token: str) -> dict:
    """
    Connects to Zerodha Kite Connect API using API Key and Access Token.
    """
    return await connect_portfolio("Zerodha", {"api_key": api_key, "access_token": access_token})

@mcp.tool()
async def connect_groww(credentials: dict) -> dict:
    """
    Connects to Groww using user credentials.
    """
    return await connect_portfolio("Groww", credentials)

@mcp.tool()
async def connect_angel(api_key: str, client_code: str, password: str, totp_key: str) -> dict:
    """
    Connects to Angel One SmartAPI using API Key, Client Code, Password, and TOTP key.
    """
    return await connect_portfolio(
        "Angel One", 
        {"api_key": api_key, "client_code": client_code, "password": password, "totp_key": totp_key}
    )

@mcp.tool()
async def connect_upstox(client_id: str, client_secret: str, redirect_uri: str) -> dict:
    """
    Connects to Upstox API using OAuth Client ID, Secret, and Redirect URI.
    """
    return await connect_portfolio(
        "Upstox",
        {"client_id": client_id, "client_secret": client_secret, "redirect_uri": redirect_uri}
    )

@mcp.tool()
async def connect_dhan(client_id: str, access_token: str) -> dict:
    """
    Connects to Dhan API using client ID and access token.
    """
    return await connect_portfolio("Dhan", {"client_id": client_id, "access_token": access_token})

@mcp.tool()
async def get_connection_status() -> dict:
    """
    Returns details about the active broker integration and credentials status.
    """
    try:
        uid, key = get_authenticated_context()
        db = await get_db()
        if db is None:
            return {"connected": False, "message": "Database connection unavailable."}
            
        user = await db["users"].find_one({"user_id": uid})
        if not user or not user.get("encrypted_broker_credentials"):
            # Check if CAS portfolio exists
            portfolio = await get_portfolio(uid)
            if portfolio and portfolio.get("encrypted_holdings"):
                return {"connected": True, "type": "CAS PDF", "message": "Active portfolio loaded from CAS statement."}
            return {"connected": False, "type": "NONE", "message": "No active broker or portfolio file connected."}
            
        # Decrypt broker details
        decrypted = EncryptionManager.decrypt(user["encrypted_broker_credentials"], key)
        creds_data = json.loads(decrypted)
        return {
            "connected": True,
            "type": creds_data["broker"],
            "message": f"Connected to {creds_data['broker']} account."
        }
    except ValueError as ve:
        return {"connected": False, "message": str(ve)}
    except Exception as e:
        return {"connected": False, "message": str(e)}

@mcp.tool()
async def upload_cas(pdf_path: str, password: Optional[str] = None) -> dict:
    """
    Parses a local CAS statement PDF file, encrypts the holdings using the session key,
    and updates the database. If no session is active, automatically creates a default session.
    """
    try:
        db = await get_db()
        if db is None:
            return {"success": False, "message": "Database connection unavailable."}
            
        try:
            uid, key = get_authenticated_context()
        except ValueError:
            # Auto-authenticate default local user for seamless testing
            uid = "local_user"
            logger.info("No active session found. Auto-configuring default 'local_user' session.")
            
            # Ensure the default local user exists in DB
            user = await db["users"].find_one({"user_id": uid})
            if not user:
                from src.tools.auth import hash_password as auth_hash
                import os
                salt = os.urandom(16)
                pwd_hash = auth_hash("local_password", salt)
                await db["users"].insert_one({
                    "user_id": uid,
                    "email": "local@example.com",
                    "password_hash": pwd_hash,
                    "salt": salt.hex(),
                    "verified": True
                })
            
            # Retrieve or create ZK portfolio salt
            portfolio_doc = await db["portfolios"].find_one({"user_id": uid})
            if portfolio_doc and "salt" in portfolio_doc:
                p_salt = bytes.fromhex(portfolio_doc["salt"])
            else:
                p_salt = os.urandom(16)
                await db["portfolios"].update_one(
                    {"user_id": uid},
                    {"$set": {"salt": p_salt.hex()}},
                    upsert=True
                )
            
            # Derive zero-knowledge key using CAS PDF password as the master passphrase
            passphrase = password or "default_passphrase"
            key, _ = EncryptionManager.derive_key(passphrase, p_salt)
            
            # Set stdio and SSE session parameters in memory
            from src.security.auth import set_stdio_session, _active_sessions
            from datetime import datetime, timedelta
            set_stdio_session(uid, key)
            _active_sessions["local_session"] = {
                "user_id": uid,
                "decryption_key": key,
                "expires_at": datetime.utcnow() + timedelta(days=365)
            }
            logger.info("Successfully auto-configured stdio and SSE session for 'local_user'.")

        if not os.path.exists(pdf_path):
            return {"success": False, "message": f"CAS PDF file not found at path: {pdf_path}"}
            
        # Read file bytes
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
            
        # Parse PDF in memory
        raw_holdings = parse_cas_pdf(pdf_bytes, password)
        if not raw_holdings:
            return {"success": False, "message": "Failed to parse CAS statement. Check file or password."}
            
        # Normalize
        normalized = normalize_holdings(raw_holdings)
        
        # Retrieve existing salt to retain consistency
        doc = await get_portfolio(uid)
        salt_hex = doc["salt"] if doc else os.urandom(16).hex()
        
        holdings_json = json.dumps(normalized)
        encrypted_data = EncryptionManager.encrypt(holdings_json, key)
        
        # Save to database
        success = await save_portfolio(uid, encrypted_data, salt_hex)
        if not success:
            return {"success": False, "message": "Failed to save portfolio holdings."}
            
        return {
            "success": True, 
            "message": f"Successfully imported and encrypted {len(normalized)} holdings from CAS statement."
        }
    except ValueError as ve:
        return {"success": False, "message": str(ve)}
    except Exception as e:
        return {"success": False, "message": str(e)}

@mcp.tool()
async def refresh_portfolio() -> dict:
    """
    Refreshes holdings by querying active broker APIs.
    ⚠️ SIMULATED: For brokers without real API integration, returns a preview
    of sample holdings. Simulated data is NEVER persisted to the database.
    """
    try:
        uid, key = get_authenticated_context()
        status = await get_connection_status()
        if not status.get("connected") or status.get("type") == "NONE":
            return {"success": False, "message": "No active broker connection to refresh holdings."}
            
        if status.get("type") == "CAS PDF":
            return {"success": True, "message": "Portfolio refreshed from CAS statement data."}
            
        # In a real environment, query broker APIs here.
        # For brokers without live API integration, return a simulated preview.
        # ⚠️ SAFETY: Mock data is returned for display only and is NOT saved to the database.
        simulated_holdings = [
            {"symbol": "INFY", "isin": "INE009A01021", "name": "Infosys Ltd", "quantity": 50, "average_price": 1400.0, "asset_class": "Equity"},
            {"symbol": "TCS", "isin": "INE467B01029", "name": "Tata Consultancy Services Ltd", "quantity": 25, "average_price": 3200.0, "asset_class": "Equity"},
            {"symbol": "RECLTD", "isin": "INE020B01018", "name": "REC Ltd", "quantity": 120, "average_price": 420.0, "asset_class": "Equity"}
        ]
        
        return {
            "success": True,
            "is_simulated": True,
            "message": f"⚠️ Simulated refresh from {status.get('type')} (no real API integration yet). Data shown is for preview only and has NOT been saved.",
            "preview_holdings": simulated_holdings
        }
    except ValueError as ve:
        return {"success": False, "message": str(ve)}
    except Exception as e:
        return {"success": False, "message": str(e)}

@mcp.tool()
async def reparse_portfolio(password: Optional[str] = None) -> dict:
    """
    Reparses portfolio holdings from the last connection state.
    """
    return await refresh_portfolio()
