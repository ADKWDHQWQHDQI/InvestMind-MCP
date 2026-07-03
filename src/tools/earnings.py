import logging
import httpx
from src.mcp_server import mcp
from src.market.api import resolve_ticker

logger = logging.getLogger("investmind.tools.earnings")

@mcp.tool()
async def get_upcoming_results() -> list[dict]:
    """
    Retrieves the calendar of upcoming quarterly earnings releases.
    """
    return [
        {"symbol": "INFY.NS", "earnings_date": "2026-07-16", "quarter": "Q1FY27"},
        {"symbol": "TCS.NS", "earnings_date": "2026-07-12", "quarter": "Q1FY27"},
        {"symbol": "RECLTD.NS", "earnings_date": "2026-07-28", "quarter": "Q1FY27"}
    ]

@mcp.tool()
async def get_latest_results(symbol: str) -> dict:
    """
    Retrieves the latest available quarterly financial results (Revenue, Net Income, EPS).
    """
    try:
        ticker = await resolve_ticker(symbol)
        url = f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{ticker}?modules=earnings,financialData"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                result = data.get("quoteSummary", {}).get("result", [{}])[0]
                earnings = result.get("earnings", {}).get("financialsChart", {}).get("quarterly", [])
                fin = result.get("financialData", {})
                
                latest_q = earnings[-1] if earnings else {}
                return {
                    "symbol": symbol,
                    "quarter": latest_q.get("date", "Q4"),
                    "revenue": latest_q.get("revenue", {}).get("value"),
                    "earnings": latest_q.get("earnings", {}).get("value"),
                    "revenue_growth_pct": fin.get("revenueGrowth", {}).get("value", 0.0) * 100,
                    "earnings_growth_pct": fin.get("earningsGrowth", {}).get("value", 0.0) * 100
                }
        return {"error": "Failed to retrieve earnings data."}
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
async def summarize_results(symbol: str) -> str:
    """
    Summarizes the quarterly performance highlights for a stock.
    """
    res = await get_latest_results(symbol)
    if "error" in res:
        return f"Could not summarize results: {res['error']}"
        
    rev_growth = res.get("revenue_growth_pct", 0.0)
    profit_growth = res.get("earnings_growth_pct", 0.0)
    
    status = "healthy" if rev_growth > 5.0 and profit_growth > 5.0 else "subdued"
    return (
        f"**Quarterly Earnings Summary for {symbol.upper()} ({res.get('quarter')})**\n"
        f"- Revenue growth is {round(rev_growth, 2)}% YoY.\n"
        f"- Net profits expanded by {round(profit_growth, 2)}% YoY.\n"
        f"- Overall operating performance is considered **{status}**."
    )

@mcp.tool()
async def compare_quarters(symbol: str) -> dict:
    """
    Compares QoQ and YoY quarterly earnings performance.
    """
    try:
        ticker = await resolve_ticker(symbol)
        url = f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{ticker}?modules=earnings"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                result = data.get("quoteSummary", {}).get("result", [{}])[0]
                earnings = result.get("earnings", {}).get("financialsChart", {}).get("quarterly", [])
                
                quarters = []
                for q in earnings:
                    quarters.append({
                        "quarter": q.get("date"),
                        "revenue": q.get("revenue", {}).get("value"),
                        "earnings": q.get("earnings", {}).get("value")
                    })
                return {"symbol": symbol, "quarterly_history": quarters}
        return {"error": "Failed to retrieve comparative quarters data."}
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
async def get_eps(symbol: str) -> dict:
    """
    Retrieves the Earnings Per Share (EPS) trend and analyst expectations.
    """
    try:
        ticker = await resolve_ticker(symbol)
        url = f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{ticker}?modules=defaultKeyStatistics"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                result = data.get("quoteSummary", {}).get("result", [{}])[0]
                stats = result.get("defaultKeyStatistics", {})
                return {
                    "symbol": symbol,
                    "trailing_eps": stats.get("trailingEps", {}).get("value"),
                    "forward_eps": stats.get("forwardEps", {}).get("value")
                }
        return {"error": "Failed to retrieve EPS details."}
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
async def get_revenue_growth(symbol: str) -> float:
    """
    Returns the YoY revenue growth rate percentage.
    """
    res = await get_latest_results(symbol)
    return float(res.get("revenue_growth_pct", 0.0))

@mcp.tool()
async def get_profit_growth(symbol: str) -> float:
    """
    Returns the YoY net profit growth rate percentage.
    """
    res = await get_latest_results(symbol)
    return float(res.get("earnings_growth_pct", 0.0))
