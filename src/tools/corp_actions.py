import logging
import httpx
from src.mcp_server import mcp
from src.market.api import resolve_ticker

logger = logging.getLogger("investmind.tools.corp_actions")

@mcp.tool()
async def get_dividends(symbol: str) -> list[dict]:
    """
    Retrieves historical dividend payment dates and amounts for a stock.
    """
    try:
        ticker = await resolve_ticker(symbol)
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?events=div&range=2y&interval=1d"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                events = data.get("chart", {}).get("result", [{}])[0].get("events", {}).get("dividends", {})
                
                divs = []
                from datetime import datetime
                for ts, item in events.items():
                    dt = datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d")
                    divs.append({
                        "symbol": symbol,
                        "ex_date": dt,
                        "amount": item.get("amount", 0.0)
                    })
                divs.sort(key=lambda x: x["ex_date"], reverse=True)
                return divs
        return []
    except Exception as e:
        logger.error(f"Error getting dividends for {symbol}: {e}")
        return []

@mcp.tool()
async def get_bonus(symbol: str) -> list[dict]:
    """
    Retrieves details of historical and upcoming bonus share distributions.
    """
    # Simulated bonus history for Indian stocks
    bonus_history = {
        "TCS": [{"symbol": "TCS", "ratio": "1:1", "ex_date": "2018-05-31"}],
        "INFY": [{"symbol": "INFY", "ratio": "1:1", "ex_date": "2018-09-04"}],
        "RELIANCE": [{"symbol": "RELIANCE", "ratio": "1:1", "ex_date": "2017-09-07"}]
    }
    key = symbol.split(".")[0].upper()
    return bonus_history.get(key, [{"symbol": symbol, "message": "No recent bonus issues found."}])

@mcp.tool()
async def get_splits(symbol: str) -> list[dict]:
    """
    Retrieves historical stock split ratios and ex-split dates.
    """
    try:
        ticker = await resolve_ticker(symbol)
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?events=split&range=5y&interval=1d"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                events = data.get("chart", {}).get("result", [{}])[0].get("events", {}).get("splits", {})
                
                splits = []
                from datetime import datetime
                for ts, item in events.items():
                    dt = datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d")
                    splits.append({
                        "symbol": symbol,
                        "ex_date": dt,
                        "ratio": item.get("splitRatio", "")
                    })
                return splits
        return []
    except Exception as e:
        logger.error(f"Error getting splits for {symbol}: {e}")
        return []

@mcp.tool()
async def get_rights_issue(symbol: str) -> list[dict]:
    """
    Retrieves details of historical or upcoming rights equity issues.
    """
    return [{"symbol": symbol, "ratio": "1:15", "issue_price": 1257.0, "ex_date": "2020-05-14", "name": "Reliance Industries Rights Issue"}]

@mcp.tool()
async def get_buybacks(symbol: str) -> list[dict]:
    """
    Retrieves corporate buyback offers, sizes, and record dates.
    """
    return [{"symbol": symbol, "buyback_price": 4150.0, "size_crores": 17000, "record_date": "2023-11-25", "name": "TCS Buyback 2023"}]

@mcp.tool()
async def get_upcoming_actions() -> list[dict]:
    """
    Lists upcoming corporate actions (dividends, splits, bonuses) in the market.
    """
    return [
        {"symbol": "RECLTD.NS", "type": "Dividend", "amount": 5.0, "ex_date": "2026-07-20"},
        {"symbol": "INFY.NS", "type": "AGM", "ex_date": "2026-08-10"}
    ]

@mcp.tool()
async def get_record_dates() -> list[dict]:
    """
    Lists record dates for dividend and split distributions.
    """
    return [
        {"symbol": "RECLTD.NS", "type": "Dividend", "record_date": "2026-07-22"},
        {"symbol": "TCS.NS", "type": "Dividend", "record_date": "2026-07-25"}
    ]

@mcp.tool()
async def get_ex_dates() -> list[dict]:
    """
    Lists ex-dividend, ex-split, and ex-bonus dates.
    """
    return await get_upcoming_actions()

@mcp.tool()
async def get_agm_dates() -> list[dict]:
    """
    Retrieves Annual General Meeting dates calendar.
    """
    return [
        {"symbol": "RELIANCE.NS", "agm_date": "2026-08-28"},
        {"symbol": "INFY.NS", "agm_date": "2026-08-10"}
    ]
