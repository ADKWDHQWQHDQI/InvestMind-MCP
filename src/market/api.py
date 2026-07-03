import httpx
import logging
from datetime import datetime

logger = logging.getLogger("investmind.market")

async def resolve_ticker(query: str) -> str:
    """
    Queries Yahoo Finance search API dynamically to resolve an ISIN, symbol, 
    or company name to its Yahoo stock ticker symbol (e.g. 'RELIANCE.NS').
    """
    try:
        # URL encode query automatically via httpx params
        url = "https://query2.finance.yahoo.com/v1/finance/search"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        params = {"q": query}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, params=params, timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                quotes = data.get("quotes", [])
                
                # Prioritize Indian exchanges (ending in .NS or .BO)
                for q in quotes:
                    symbol = q.get("symbol", "")
                    if symbol.endswith(".NS") or symbol.endswith(".BO"):
                        return symbol
                if quotes:
                    return quotes[0].get("symbol")
    except Exception as e:
        logger.error(f"Error resolving ticker for '{query}': {e}")
    return query  # Fallback to the query string itself

from typing import Optional

async def get_live_price(ticker: str) -> Optional[float]:
    """
    Fetches the current live stock price from Yahoo Finance.
    Returns None if fetching fails.
    """
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                result = data.get("chart", {}).get("result", [{}])[0]
                meta = result.get("meta", {})
                price = meta.get("regularMarketPrice")
                if price is not None:
                    return float(price)
    except Exception as e:
        logger.error(f"Error fetching live price for {ticker}: {e}")
    return None

async def get_ticker_info(ticker: str) -> dict:
    """
    Retrieves the company details (sector, actual dividend yield, name)
    dynamically from Yahoo Finance.
    """
    info = {"sector": "Others", "dividend_yield": 0.0, "name": ""}
    try:
        url = f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{ticker}?modules=assetProfile,summaryDetail,price"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                result = data.get("quoteSummary", {}).get("result", [{}])[0]
                
                # Get Sector / Industry
                asset_profile = result.get("assetProfile", {})
                info["sector"] = asset_profile.get("sector", "Others")
                
                # Get Dividend Yield
                summary_detail = result.get("summaryDetail", {})
                div_yield = summary_detail.get("dividendYield", {}).get("value")
                if div_yield is not None:
                    info["dividend_yield"] = float(div_yield)
                
                market_cap = summary_detail.get("marketCap", {}).get("value")
                if market_cap is not None:
                    info["market_cap"] = float(market_cap)
                
                # Get Long Name
                price_module = result.get("price", {})
                info["name"] = price_module.get("longName", "")
    except Exception as e:
        logger.error(f"Error fetching profile info for {ticker}: {e}")
    return info


import random

DECOY_TICKERS = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "BHARTIARTL.NS", "SBIN.NS"]

def _mix_decoys(queries: list[str]) -> tuple[list[str], set[str]]:
    """
    Mixes in random decoy symbols to anonymize the portfolio composition.
    Returns a shuffled list of queries (user + decoys) and the set of decoys.
    """
    user_set = set(queries)
    possible_decoys = [d for d in DECOY_TICKERS if d not in user_set]
    decoys_to_add = random.sample(possible_decoys, min(3, len(possible_decoys)))
    
    mixed_list = list(queries) + decoys_to_add
    random.shuffle(mixed_list)
    return mixed_list, set(decoys_to_add)

async def get_live_prices(queries: list[str]) -> dict[str, float]:
    """
    Resolves tickers and fetches live quotes in bulk with query anonymization.
    """
    if not queries:
        return {}
        
    mixed_queries, decoys = _mix_decoys(queries)
    prices = {}
    
    for q in mixed_queries:
        ticker = await resolve_ticker(q)
        price = await get_live_price(ticker)
        # Store quotes for both queries and resolved tickers to ease lookup mapping
        prices[q] = price
        if ticker != q:
            prices[ticker] = price
            
    # Filter out decoy keys to protect user context
    clean_prices = {}
    for q in queries:
        clean_prices[q] = prices.get(q)
    return clean_prices

async def get_stock_news(queries: list[str]) -> list[dict]:
    """
    Fetches real news dynamically from Yahoo Finance matching user's holdings with query anonymization.
    """
    if not queries:
        return []
        
    mixed_queries, decoys = _mix_decoys(queries)
    news_items = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    async with httpx.AsyncClient() as client:
        for q in mixed_queries:
            # Skip fetching if it's a decoy to save network calls, OR fetch anyway to blend traffic.
            # To achieve complete cryptographic blending, we perform the fetch for decoys too.
            ticker = await resolve_ticker(q)
            try:
                url = "https://query2.finance.yahoo.com/v1/finance/search"
                params = {"q": ticker}
                response = await client.get(url, headers=headers, params=params, timeout=5.0)
                if response.status_code == 200:
                    data = response.json()
                    articles = data.get("news", [])
                    # Take up to 2 news articles per stock
                    for art in articles[:2]:
                        publish_time = art.get("providerPublishTime")
                        timestamp = datetime.fromtimestamp(publish_time).strftime("%Y-%m-%d %H:%M:%S") if publish_time else ""
                        
                        # Only add to results if the query is not in the decoy set
                        if q not in decoys:
                            news_items.append({
                                "symbol": q,
                                "title": art.get("title", ""),
                                "source": art.get("publisher", ""),
                                "link": art.get("link", ""),
                                "timestamp": timestamp
                            })
            except Exception as e:
                logger.error(f"Error fetching news for {ticker}: {e}")
    return news_items

