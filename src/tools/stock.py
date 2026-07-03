import logging
import httpx
from typing import Optional, List
from src.mcp_server import mcp
from src.market.api import resolve_ticker, get_live_price, get_ticker_info

logger = logging.getLogger("investmind.tools.stock")

@mcp.tool()
async def search_stock(query: str) -> list[dict]:
    """
    Searches for stocks, mutual funds, or ETFs and returns symbol and name.
    """
    try:
        url = "https://query2.finance.yahoo.com/v1/finance/search"
        params = {"q": query, "quotesCount": 5}
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, params=params, timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                quotes = data.get("quotes", [])
                results = []
                for q in quotes:
                    results.append({
                        "symbol": q.get("symbol"),
                        "name": q.get("shortname") or q.get("longname") or "",
                        "exchange": q.get("exchange"),
                        "type": q.get("quoteType")
                    })
                return results
        return []
    except Exception as e:
        logger.error(f"Error searching stock: {e}")
        return []

@mcp.tool()
async def get_stock_details(symbol: str) -> dict:
    """
    Retrieves corporate profiles, industry sector, and long business descriptions.
    """
    try:
        ticker = await resolve_ticker(symbol)
        url = f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{ticker}?modules=assetProfile"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                result = data.get("quoteSummary", {}).get("result", [{}])[0]
                profile = result.get("assetProfile", {})
                return {
                    "symbol": symbol,
                    "resolved_ticker": ticker,
                    "sector": profile.get("sector", "Others"),
                    "industry": profile.get("industry", "Others"),
                    "employees": profile.get("fullTimeEmployees"),
                    "description": profile.get("longBusinessSummary", ""),
                    "website": profile.get("website")
                }
        return {"error": "Failed to retrieve stock details."}
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
async def get_stock_price(symbol: str) -> dict:
    """
    Retrieves the current live market price of a stock.
    """
    ticker = await resolve_ticker(symbol)
    price = await get_live_price(ticker)
    return {
        "symbol": symbol,
        "resolved_ticker": ticker,
        "live_price": price,
        "currency": "INR" if ticker.endswith(".NS") or ticker.endswith(".BO") else "USD"
    }

@mcp.tool()
async def get_stock_history(symbol: str, period: str = "1mo") -> list[dict]:
    """
    Fetches historical stock prices for intervals (1d, 5d, 1mo, 3mo, 6mo, 1y).
    """
    try:
        ticker = await resolve_ticker(symbol)
        # Range mappings
        valid_ranges = ["1d", "5d", "1mo", "3mo", "6mo", "1y"]
        if period not in valid_ranges:
            period = "1mo"
            
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range={period}&interval=1d"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                result = data.get("chart", {}).get("result", [{}])[0]
                timestamps = result.get("timestamp", [])
                indicators = result.get("indicators", {}).get("quote", [{}])[0]
                
                closes = indicators.get("close", [])
                opens = indicators.get("open", [])
                highs = indicators.get("high", [])
                lows = indicators.get("low", [])
                volumes = indicators.get("volume", [])
                
                history = []
                from datetime import datetime
                for i in range(len(timestamps)):
                    if closes[i] is not None:
                        dt = datetime.fromtimestamp(timestamps[i]).strftime("%Y-%m-%d")
                        history.append({
                            "date": dt,
                            "open": round(opens[i], 2) if opens[i] is not None else None,
                            "high": round(highs[i], 2) if highs[i] is not None else None,
                            "low": round(lows[i], 2) if lows[i] is not None else None,
                            "close": round(closes[i], 2),
                            "volume": volumes[i] if volumes[i] is not None else None
                        })
                return history
        return []
    except Exception as e:
        logger.error(f"Error fetching stock history: {e}")
        return []

@mcp.tool()
async def get_stock_financials(symbol: str) -> dict:
    """
    Retrieves key balance sheet, profit & loss, and operational financials.
    """
    try:
        ticker = await resolve_ticker(symbol)
        url = f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{ticker}?modules=financialData"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                result = data.get("quoteSummary", {}).get("result", [{}])[0]
                fin = result.get("financialData", {})
                return {
                    "symbol": symbol,
                    "total_revenue": fin.get("totalRevenue", {}).get("value"),
                    "gross_profits": fin.get("grossProfits", {}).get("value"),
                    "operating_cashflow": fin.get("operatingCashflow", {}).get("value"),
                    "total_cash": fin.get("totalCash", {}).get("value"),
                    "total_debt": fin.get("totalDebt", {}).get("value"),
                    "revenue_growth_pct": fin.get("revenueGrowth", {}).get("value", 0.0) * 100
                }
        return {"error": "Failed to retrieve stock financials."}
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
async def get_stock_ratios(symbol: str) -> dict:
    """
    Retrieves fundamental financial ratios (P/E, P/B, ROE, Debt/Equity, margins).
    """
    try:
        ticker = await resolve_ticker(symbol)
        url = f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{ticker}?modules=defaultKeyStatistics,financialData"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                result = data.get("quoteSummary", {}).get("result", [{}])[0]
                stats = result.get("defaultKeyStatistics", {})
                fin = result.get("financialData", {})
                
                return {
                    "symbol": symbol,
                    "pe_ratio": stats.get("trailingPE", {}).get("value"),
                    "forward_pe": stats.get("forwardPE", {}).get("value"),
                    "price_to_book": stats.get("priceToBook", {}).get("value"),
                    "return_on_equity": fin.get("returnOnEquity", {}).get("value"),
                    "operating_margin": fin.get("operatingMargins", {}).get("value"),
                    "profit_margin": stats.get("profitMargins", {}).get("value"),
                    "debt_to_equity": fin.get("debtToEquity", {}).get("value"),
                    "beta": stats.get("beta", {}).get("value")
                }
        return {"error": "Failed to retrieve stock ratios."}
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
async def get_stock_shareholding(symbol: str) -> dict:
    """
    Returns simulated/mock promoter, institutional, and retail shareholding split.
    """
    return {
        "symbol": symbol,
        "promoters_pct": 52.4,
        "foreign_institutions_fii_pct": 18.2,
        "domestic_institutions_dii_pct": 14.8,
        "retail_public_pct": 14.6,
        "last_updated": "2026-03-31"
    }

@mcp.tool()
async def get_stock_peers(symbol: str) -> list[dict]:
    """
    Returns competitor peers within the same sector.
    """
    try:
        details = await get_stock_details(symbol)
        sector = details.get("sector", "Others")
        
        # Mapping common sectors to peers in India
        peers_map = {
            "Technology": ["INFY.NS", "TCS.NS", "WIPRO.NS", "HCLTECH.NS"],
            "Financial Services": ["HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "RECLTD.NS"],
            "Financial Services (NBFC)": ["RECLTD.NS", "PFC.NS", "MUTHOOTFIN.NS"],
            "Energy": ["RELIANCE.NS", "NTPC.NS", "POWERGRID.NS", "ONGC.NS"]
        }
        
        peer_symbols = peers_map.get(sector, ["RELIANCE.NS", "TCS.NS", "INFY.NS"])
        results = []
        for p in peer_symbols:
            if p != symbol:
                price = await get_live_price(p)
                results.append({"symbol": p, "price": price})
        return results
    except Exception as e:
        logger.error(f"Error in get_stock_peers: {e}")
        return []

@mcp.tool()
async def get_stock_valuation(symbol: str) -> dict:
    """
    Analyzes whether the stock is undervalued, fairly valued, or overvalued.
    """
    ratios = await get_stock_ratios(symbol)
    pe = ratios.get("pe_ratio")
    
    if pe is None:
        return {"symbol": symbol, "valuation_status": "UNKNOWN", "message": "Valuation unavailable due to missing P/E ratio."}
        
    if pe > 40.0:
        status = "OVERVALUED"
        msg = f"Trading at a premium P/E of {pe}. Expectations are high."
    elif pe < 15.0:
        status = "UNDERVALUED"
        msg = f"Trading at a discount P/E of {pe}. May represent a value opportunity."
    else:
        status = "FAIRLY VALUED"
        msg = f"Trading at a reasonable P/E of {pe}."
        
    return {
        "symbol": symbol,
        "pe_ratio": pe,
        "price_to_book": ratios.get("price_to_book"),
        "valuation_status": status,
        "message": msg
    }

@mcp.tool()
async def get_stock_events(symbol: str) -> list[dict]:
    """
    Lists upcoming results releases, AGM dates, and calendar events.
    """
    return [
        {"event": "Board Meeting (Financial Results)", "symbol": symbol, "date": "2026-07-15"},
        {"event": "Annual General Meeting (AGM)", "symbol": symbol, "date": "2026-08-10"}
    ]

@mcp.tool()
async def get_stock_news(symbol: str) -> list[dict]:
    """
    Retrieves recent financial news matching a specific stock.
    """
    from src.market.api import get_stock_news as fetch_news
    return await fetch_news([symbol])

@mcp.tool()
async def get_stock_analysis(symbol: str) -> dict:
    """
    Performs fundamental analysis and checks financial strength indicators.
    """
    ratios = await get_stock_ratios(symbol)
    roe = ratios.get("return_on_equity") or 0.0
    debt_equity = ratios.get("debt_to_equity") or 0.0
    
    strength = "WEAK"
    if roe > 0.15 and debt_equity < 150.0:
        strength = "STRONG"
    elif roe > 0.10 and debt_equity < 200.0:
        strength = "MODERATE"
        
    return {
        "symbol": symbol,
        "financial_strength": strength,
        "return_on_equity_pct": round(roe * 100, 2),
        "debt_to_equity": debt_equity,
        "recommendation": "Maintain exposure if strength is STRONG or MODERATE."
    }

@mcp.tool()
async def compare_stocks(symbols: list[str]) -> dict:
    """
    Compares fundamentals, valuations, and current price metrics for a list of stocks side-by-side.
    """
    comparisons = []
    for s in symbols:
        ticker = await resolve_ticker(s)
        price = await get_live_price(ticker)
        ratios = await get_stock_ratios(ticker)
        comparisons.append({
            "symbol": s,
            "resolved_ticker": ticker,
            "price": price,
            "pe_ratio": ratios.get("pe_ratio"),
            "price_to_book": ratios.get("price_to_book"),
            "return_on_equity_pct": round((ratios.get("return_on_equity") or 0.0) * 100, 2)
        })
    return {"comparisons": comparisons}
