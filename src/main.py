import argparse
import base64
import json
import logging
import uvicorn
import os
import sys

# Ensure project root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import FastAPI, Request
from mcp.server.fastmcp import FastMCP
from mcp.server.sse import SseServerTransport

from src.config import settings
from src.security.encryption import EncryptionManager
from src.database.operations import save_portfolio, get_portfolio, save_watchlist, get_watchlist
from src.parser.cas_parser import parse_cas_pdf
from src.parser.normalizer import normalize_holdings
from src.market.api import get_live_prices, get_stock_news, resolve_ticker, get_ticker_info
from src.analysis.metrics import analyze_portfolio

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("investmind.main")

# Initialize FastMCP Server
mcp = FastMCP("InvestMind")

@mcp.tool()
def hello_mcp() -> str:
    """A hello tool to verify connectivity."""
    return "Hello Sandeep! MCP is working."

@mcp.tool()
async def upload_cas(
    user_id: str,
    cas_base64: str,
    password: str,
    encryption_passphrase: str = None
) -> dict:
    """
    Decrypts, parses, and normalizes a password-protected CAS statement PDF (passed as base64).
    Encrypts the normalized holdings list using AES-256-GCM and stores it in MongoDB.
    
    Parameters:
      - user_id: A unique identifier for the user.
      - cas_base64: The base64-encoded bytes of the CAS PDF statement.
      - password: The password to decrypt the CAS PDF (usually user's PAN card number in uppercase).
      - encryption_passphrase: Optional passphrase to secure the holdings. If provided, the data 
                               can only be decrypted when this passphrase is provided (Zero-Knowledge style).
    """
    try:
        logger.info(f"Received CAS upload request for user: {user_id}")
        
        # 1. Decode PDF bytes in memory
        try:
            pdf_bytes = base64.b64decode(cas_base64)
        except Exception as e:
            return {"success": False, "error": f"Invalid base64 encoding: {str(e)}"}
            
        # 2. Parse PDF in memory
        raw_holdings = parse_cas_pdf(pdf_bytes, password)
        if not raw_holdings:
            return {"success": False, "error": "No holdings found or failed to parse PDF."}
            
        # 3. Normalize holdings
        normalized = normalize_holdings(raw_holdings)
        
        # 4. Resolve symbols dynamically using Yahoo Finance search
        for holding in normalized:
            symbol = await resolve_ticker(holding["isin"])
            holding["symbol"] = symbol
        
        # 5. Encrypt holdings
        passphrase = encryption_passphrase or settings.SERVER_ENCRYPTION_PASSPHRASE
        key, salt = EncryptionManager.derive_key(passphrase)
        
        holdings_json = json.dumps(normalized)
        encrypted_data = EncryptionManager.encrypt(holdings_json, key)
        
        # 6. Save to MongoDB
        success = await save_portfolio(user_id, encrypted_data, salt.hex())
        if not success:
            return {"success": False, "error": "Failed to save portfolio to database."}
            
        return {
            "success": True,
            "message": f"Successfully parsed and stored {len(normalized)} holdings.",
            "holdings_count": len(normalized)
        }
    except Exception as e:
        logger.error(f"Error in upload_cas: {e}")
        return {"success": False, "error": str(e)}

@mcp.tool()
async def get_holdings(user_id: str, encryption_passphrase: str = None) -> list[dict]:
    """
    Retrieves the user's holdings from the secure MongoDB store and decrypts them in memory.
    
    Parameters:
      - user_id: Unique identifier for the user.
      - encryption_passphrase: Passphrase if custom encryption was used during upload.
    """
    try:
        doc = await get_portfolio(user_id)
        if not doc:
            return []
            
        encrypted_holdings = doc["encrypted_holdings"]
        salt_hex = doc["salt"]
        
        passphrase = encryption_passphrase or settings.SERVER_ENCRYPTION_PASSPHRASE
        key, _ = EncryptionManager.derive_key(passphrase, bytes.fromhex(salt_hex))
        
        decrypted_json = EncryptionManager.decrypt(encrypted_holdings, key)
        return json.loads(decrypted_json)
    except Exception as e:
        logger.error(f"Error in get_holdings: {e}")
        raise ValueError(f"Could not retrieve holdings: {str(e)}")

@mcp.tool()
async def get_portfolio_summary(user_id: str, encryption_passphrase: str = None) -> dict:
    """
    Retrieves the user's decrypted holdings, fetches live market prices, and calculates 
    comprehensive portfolio metrics including total valuation, sector allocations, 
    and concentration risks. All metrics and company data are queried dynamically.
    """
    try:
        holdings = await get_holdings(user_id, encryption_passphrase)
        if not holdings:
            return {"message": "No portfolio found. Please upload your CAS statement first."}
            
        symbols = [h["symbol"] for h in holdings]
        live_prices = await get_live_prices(symbols)
        
        # Fetch company metadata dynamically (sector, names, dividend yields)
        ticker_infos = {}
        for s in symbols:
            ticker_infos[s] = await get_ticker_info(s)
            
        analysis = analyze_portfolio(holdings, live_prices, ticker_infos)
        return analysis
    except Exception as e:
        logger.error(f"Error in get_portfolio_summary: {e}")
        return {"error": str(e)}

@mcp.tool()
async def get_portfolio_news(user_id: str, encryption_passphrase: str = None) -> list[dict]:
    """
    Fetches the latest relevant corporate actions, dividends, and news matching the symbols 
    in the user's portfolio dynamically.
    """
    try:
        holdings = await get_holdings(user_id, encryption_passphrase)
        if not holdings:
            return []
            
        symbols = [h["symbol"] for h in holdings]
        news = await get_stock_news(symbols)
        return news
    except Exception as e:
        logger.error(f"Error in get_portfolio_news: {e}")
        return [{"error": str(e)}]

@mcp.tool()
async def update_watchlist(user_id: str, symbols: list[str]) -> dict:
    """
    Updates the list of stock symbols monitored in the user's watchlist.
    """
    success = await save_watchlist(user_id, symbols)
    if success:
        return {"success": True, "message": "Watchlist updated successfully."}
    return {"success": False, "message": "Failed to update watchlist."}

@mcp.tool()
async def get_watchlist_summary(user_id: str) -> dict:
    """
    Retrieves the user's watchlist stock symbols along with their live prices.
    """
    symbols = await get_watchlist(user_id)
    if not symbols:
        return {"message": "Your watchlist is empty."}
        
    prices = await get_live_prices(symbols)
    watchlist_items = [{"symbol": s, "price": prices.get(s)} for s in symbols]
    return {
        "user_id": user_id,
        "watchlist": watchlist_items
    }

# Setup FastAPI App (for SSE/remote connections)
app = FastAPI(title="InvestMind MCP Server")
sse = SseServerTransport("/messages")

@app.get("/sse")
async def handle_sse(request: Request):
    async with sse.connect_sse(
        request.scope, request.receive, request._send
    ) as (read_stream, write_stream):
        await mcp._mcp_server.run(
            read_stream,
            write_stream,
            mcp._mcp_server.create_initialization_options()
        )

@app.post("/messages")
async def handle_messages(request: Request):
    await sse.handle_post_message(request.scope, request.receive, request._send)

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
        mcp.run(transport="stdio")
    elif args.transport == "sse":
        uvicorn.run(app, host=args.host, port=args.port)

if __name__ == "__main__":
    main()
