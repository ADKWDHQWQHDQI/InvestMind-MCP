import argparse
import base64
import json
import logging
import uvicorn
import os
import sys
from typing import Optional

# Ensure project root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import FastAPI, Request, Depends, HTTPException, status, File, UploadFile, Form
from pydantic import BaseModel
from mcp.server.sse import SseServerTransport

from src.config import settings
from src.mcp_server import mcp

# Import all tool modules to register them on the shared mcp server instance
import src.tools.auth
import src.tools.portfolio_conn
import src.tools.portfolio
import src.tools.stock
import src.tools.news
import src.tools.corp_actions
import src.tools.earnings
import src.tools.watchlist
import src.tools.alerts
import src.tools.technical
import src.tools.ai_analysis
import src.tools.tax
import src.tools.market
import src.tools.optimization
import src.tools.search
import src.tools.preferences
import src.tools.admin
import src.tools.utility
import src.tools.ai_chat
import src.tools.agents

from src.database.connection import get_db
from src.security.auth import (
    current_user_id,
    current_decryption_key,
    create_access_token,
    authenticate_request,
    register_session
)
from src.security.encryption import EncryptionManager
from src.database.operations import save_portfolio, get_portfolio
from src.parser.cas_parser import parse_cas_pdf
from src.parser.normalizer import normalize_holdings

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("investmind.main")

# Enforce secure secrets on startup
DEFAULT_SECRET_KEY = "investmind-super-secure-jwt-signing-secret-change-me"
if settings.JWT_SECRET_KEY == DEFAULT_SECRET_KEY:
    if os.environ.get("ENV") == "production":
        logger.critical("JWT_SECRET_KEY must be configured in environment in production mode!")
        sys.exit("FATAL: JWT_SECRET_KEY is the default signing key in production.")
    else:
        import secrets
        settings.JWT_SECRET_KEY = secrets.token_urlsafe(32)
        logger.warning("JWT_SECRET_KEY was not set. Generated a random one-time key for this process.")

# FastAPI Models
class TokenRequest(BaseModel):
    user_id: str
    password: str
    passphrase: str

# Setup FastAPI App (for SSE/remote connections and user file uploads)
app = FastAPI(title="InvestMind MCP Server")
sse = SseServerTransport("/messages")

def hash_password(password: str, salt: bytes) -> str:
    import hashlib
    return hashlib.sha256(salt + password.encode()).hexdigest()

@app.post("/api/auth/token")
async def generate_token(req: TokenRequest):
    """
    Exchanges user credentials and their master passphrase for an authenticated JWT session token.
    Derives the AES-256-GCM key using the user's permanent salt (or creates a new one).
    Verifies user's identity against the users collection.
    """
    try:
        user_id = req.user_id.strip()
        password = req.password
        passphrase = req.passphrase
        
        if not user_id or not password or not passphrase:
            raise HTTPException(status_code=400, detail="Missing user_id, password, or passphrase.")
            
        # 1. Fetch user credentials from database
        db = await get_db()
        if db is None:
            raise HTTPException(status_code=500, detail="Database connection unavailable.")
            
        user = await db["users"].find_one({"user_id": user_id})
        if not user:
            raise HTTPException(status_code=401, detail="Invalid username or password.")
            
        # 2. Verify password hash
        salt_bytes = bytes.fromhex(user["salt"])
        expected_hash = hash_password(password, salt_bytes)
        if user["password_hash"] != expected_hash:
            raise HTTPException(status_code=401, detail="Invalid username or password.")
            
        # 3. Retrieve or create portfolio salt
        doc = await get_portfolio(user_id)
        if doc and "salt" in doc:
            p_salt_bytes = bytes.fromhex(doc["salt"])
        else:
            p_salt_bytes = os.urandom(16)
            await save_portfolio(user_id, "", p_salt_bytes.hex())
            
        # 4. Derive decryption key from passphrase
        key, _ = EncryptionManager.derive_key(passphrase, p_salt_bytes)
        
        # 5. Register session in-memory, mapping session_id -> key
        session_id = register_session(user_id, key)
        
        # 6. Generate secure JWT carrying sub and sid (no raw key!)
        token = create_access_token(user_id, session_id)
        return {"token": token}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating token: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/portfolio/upload")
async def upload_cas_statement(
    file: UploadFile = File(...),
    password: str = Form(...),
    user_id: str = Depends(authenticate_request)
):
    """
    Secure file upload endpoint. Accepts the CAS statement PDF and decryption password.
    Processes the file entirely in RAM, encrypts the holdings using the authenticated 
    session key, and stores the encrypted blob in MongoDB.
    """
    try:
        logger.info(f"Processing CAS upload via API for user: {user_id}")
        
        # 1. Read file bytes in memory
        pdf_bytes = await file.read()
        
        # 2. Parse PDF in memory
        raw_holdings = parse_cas_pdf(pdf_bytes, password)
        if not raw_holdings:
            raise HTTPException(status_code=400, detail="No holdings found or failed to parse PDF.")
            
        # 3. Normalize holdings (No third-party calls are made here to protect user privacy)
        normalized = normalize_holdings(raw_holdings)
        
        # 4. Encrypt holdings using the authenticated session key
        key = current_decryption_key.get()
        if not key:
            raise HTTPException(status_code=401, detail="Session key is missing. Please re-authenticate.")
            
        # Retrieve existing salt to retain consistency
        doc = await get_portfolio(user_id)
        salt_hex = doc["salt"] if doc else os.urandom(16).hex()
        
        holdings_json = json.dumps(normalized)
        encrypted_data = EncryptionManager.encrypt(holdings_json, key)
        
        # 5. Save encrypted data to database
        success = await save_portfolio(user_id, encrypted_data, salt_hex)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save encrypted holdings to database.")
            
        return {
            "success": True,
            "message": f"Successfully parsed and encrypted {len(normalized)} holdings."
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error in upload_cas_statement API: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sse")
async def handle_sse(request: Request, user_id: str = Depends(authenticate_request)):
    """
    HTTP/SSE endpoint. Enforces Bearer token validation before starting the stream.
    """
    async with sse.connect_sse(
        request.scope, request.receive, request._send
    ) as (read_stream, write_stream):
        await mcp._mcp_server.run(
            read_stream,
            write_stream,
            mcp._mcp_server.create_initialization_options()
        )

@app.post("/messages")
async def handle_messages(request: Request, user_id: str = Depends(authenticate_request)):
    """
    POST Messages handler. Validates authentication token on every JSON-RPC interaction.
    """
    await sse.handle_post_message(request.scope, request.receive, request._send)

from src.security.auth import set_stdio_session
import asyncio

async def validate_stdio_env():
    uid = os.environ.get("INVESTMIND_USER_ID")
    pwd = os.environ.get("INVESTMIND_PASSWORD")
    passphrase = os.environ.get("INVESTMIND_PASSPHRASE")
    
    if uid and pwd and passphrase:
        logger.info(f"Attempting automatic stdio authentication for user: {uid}")
        db = await get_db()
        if db is None:
            logger.error("Database connection unavailable for stdio authentication.")
            sys.exit(1)
            
        user = await db["users"].find_one({"user_id": uid})
        if not user:
            logger.error(f"Stdio authentication failed: User {uid} not found.")
            sys.exit(1)
            
        salt_bytes = bytes.fromhex(user["salt"])
        expected_hash = hash_password(pwd, salt_bytes)
        if user["password_hash"] != expected_hash:
            logger.error("Stdio authentication failed: Invalid password.")
            sys.exit(1)
            
        # Derive decryption key
        portfolio_doc = await db["portfolios"].find_one({"user_id": uid})
        p_salt = bytes.fromhex(portfolio_doc["salt"]) if (portfolio_doc and "salt" in portfolio_doc) else os.urandom(16)
        
        key, _ = EncryptionManager.derive_key(passphrase, p_salt)
        set_stdio_session(uid, key)
        logger.info(f"Stdio session successfully authenticated for user: {uid}")

def main():
    parser = argparse.ArgumentParser(description="Run the InvestMind MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="Transport protocol to use (default: stdio)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to run FastAPI on when using SSE transport (default: 8000)"
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind FastAPI to when using SSE transport (default: 0.0.0.0)"
    )
    args = parser.parse_args()

    if args.transport == "stdio":
        # Validate and configure session parameters from env variables
        asyncio.run(validate_stdio_env())
        mcp.run(transport="stdio")
    elif args.transport == "sse":
        uvicorn.run(app, host=args.host, port=args.port)

if __name__ == "__main__":
    main()
