import logging
from src.mcp_server import mcp
from src.tools.stock import search_stock, get_stock_details
from src.market.api import get_stock_news

logger = logging.getLogger("investmind.tools.search")

@mcp.tool()
async def search_company(query: str) -> list[dict]:
    """
    Looks up stock symbols, names, and listings for a company name.
    """
    return await search_stock(query)

@mcp.tool()
async def search_symbol(symbol: str) -> dict:
    """
    Retrieves company profile summary and business model info matching a symbol.
    """
    return await get_stock_details(symbol)

@mcp.tool()
async def search_sector(sector: str) -> list[dict]:
    """
    Finds leading stocks listed under a specific industry sector (e.g. Technology, Energy).
    """
    sector_map = {
        "TECHNOLOGY": ["TCS.NS", "INFY.NS", "WIPRO.NS", "HCLTECH.NS"],
        "ENERGY": ["RELIANCE.NS", "NTPC.NS", "POWERGRID.NS", "ONGC.NS"],
        "FINANCIALS": ["HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "RECLTD.NS"],
        "AUTOMOBILE": ["TATAMOTORS.NS", "M&M.NS", "MARUTI.NS"]
    }
    symbols = sector_map.get(sector.upper().strip(), ["RELIANCE.NS", "TCS.NS", "INFY.NS"])
    return [{"symbol": s, "sector": sector} for s in symbols]

@mcp.tool()
async def search_theme(theme: str) -> list[dict]:
    """
    Suggests thematic stock groupings (e.g. EV, Green Energy, Defense, Railways).
    """
    theme_map = {
        "EV": [
            {"symbol": "TATAMOTORS.NS", "reason": "Market leader in electric passenger vehicles in India."},
            {"symbol": "OLECTRA.NS", "reason": "Leading EV bus manufacturer."}
        ],
        "GREEN ENERGY": [
            {"symbol": "ADANIGREEN.NS", "reason": "Largest renewable capacity developer."},
            {"symbol": "IREDA.NS", "reason": "State-backed green energy financier."}
        ],
        "DEFENSE": [
            {"symbol": "HAL.NS", "reason": "Aeronautical jet manufacturer."},
            {"symbol": "BEL.NS", "reason": "Electronics supplier for defense platforms."}
        ],
        "RAILWAYS": [
            {"symbol": "IRCTC.NS", "reason": "Online ticket booking and catering monopoly."},
            {"symbol": "RVNL.NS", "reason": "Rail infrastructure execution agency."}
        ]
    }
    
    key = theme.upper().strip()
    return theme_map.get(key, [
        {"symbol": "RELIANCE.NS", "reason": "Conglomerate with digital, retail, and green energy theme plays."}
    ])

@mcp.tool()
async def search_news(query: str) -> list[dict]:
    """
    Searches recent market news articles by keywords.
    """
    return await get_stock_news([query])

@mcp.tool()
async def search_results(query: str) -> list[dict]:
    """
    Searches quarterly financial filings by stock ticker query.
    """
    from src.tools.earnings import get_latest_results
    res = await get_latest_results(query)
    return [res] if "error" not in res else []
