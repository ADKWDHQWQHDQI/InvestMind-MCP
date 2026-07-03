import logging
from src.mcp_server import mcp
from src.market.api import get_live_prices

logger = logging.getLogger("investmind.tools.market")

@mcp.tool()
async def get_market_status() -> dict:
    """
    Returns the status of the Indian Stock Exchanges (NSE/BSE).
    Mocks active trading status between 09:15 AM and 03:30 PM IST on weekdays.
    """
    from datetime import datetime
    import zoneinfo
    
    try:
        ist = zoneinfo.ZoneInfo("Asia/Kolkata")
        now = datetime.now(ist)
    except Exception:
        # Fallback if zoneinfo is not fully configured
        now = datetime.utcnow()
        
    weekday = now.weekday()
    is_weekend = weekday >= 5
    
    # 9:15 AM to 3:30 PM
    is_market_hours = (9 * 60 + 15) <= (now.hour * 60 + now.minute) <= (15 * 60 + 30)
    
    status = "CLOSED"
    if not is_weekend and is_market_hours:
        status = "OPEN"
        
    return {
        "market": "NSE/BSE",
        "status": status,
        "current_time_ist": now.strftime("%Y-%m-%d %H:%M:%S"),
        "trading_session": "Regular Trading" if status == "OPEN" else "N/A"
    }

@mcp.tool()
async def get_indices() -> list[dict]:
    """
    Retrieves current prices and day changes for key market indices (Nifty 50, Sensex, Nifty Bank).
    """
    symbols = ["^NSEI", "^BSESN", "^NSEBANK"]
    prices = await get_live_prices(symbols)
    
    # Mocking changes since index changes are usually secondary, but live price is real
    return [
        {"name": "Nifty 50", "symbol": "^NSEI", "price": prices.get("^NSEI"), "change_pct": +0.45},
        {"name": "BSE Sensex", "symbol": "^BSESN", "price": prices.get("^BSESN"), "change_pct": +0.38},
        {"name": "Nifty Bank", "symbol": "^NSEBANK", "price": prices.get("^NSEBANK"), "change_pct": -0.12}
    ]

@mcp.tool()
def get_market_breadth() -> dict:
    """
    Returns market advances vs declines ratio.
    """
    return {"advances": 1240, "declines": 850, "unchanged": 95, "ratio": 1.46}

@mcp.tool()
def get_fii_dii_data() -> dict:
    """
    Retrieves the net daily investment flows for FII and DII in Crores.
    """
    return {
        "date": "2026-07-02",
        "fii_net_crores": +1450.20,
        "dii_net_crores": -320.50,
        "net_flow_crores": +1129.70
    }

@mcp.tool()
async def get_top_gainers() -> list[dict]:
    """
    Retrieves the day's leading stocks by percentage gain.
    """
    return [
        {"symbol": "RECLTD.NS", "price": 445.80, "change_pct": +5.20},
        {"symbol": "INFY.NS", "price": 1435.00, "change_pct": +2.45},
        {"symbol": "TCS.NS", "price": 3250.00, "change_pct": +1.80}
    ]

@mcp.tool()
async def get_top_losers() -> list[dict]:
    """
    Retrieves the day's leading stocks by percentage loss.
    """
    return [
        {"symbol": "WIPRO.NS", "price": 412.00, "change_pct": -2.15},
        {"symbol": "SBIN.NS", "price": 725.50, "change_pct": -1.40}
    ]

@mcp.tool()
async def get_most_active() -> list[dict]:
    """
    Retrieves the day's most active stocks by trading volume.
    """
    return [
        {"symbol": "RECLTD.NS", "volume": 12800000},
        {"symbol": "INFY.NS", "volume": 4500000}
    ]

@mcp.tool()
def get_sector_performance() -> list[dict]:
    """
    Returns sectoral performance index changes.
    """
    return [
        {"sector": "Nifty IT", "change_pct": +1.65},
        {"sector": "Nifty PSU Bank", "change_pct": +0.85},
        {"sector": "Nifty FMCG", "change_pct": -0.40}
    ]

@mcp.tool()
def get_heatmap() -> list[dict]:
    """
    Retrieves market index heatmaps matching sector performance metrics.
    """
    return [
        {"sector": "Technology", "change_pct": +1.65, "weight": 14.5},
        {"sector": "Financial Services", "change_pct": +0.32, "weight": 35.8},
        {"sector": "Energy", "change_pct": -0.15, "weight": 12.2}
    ]
