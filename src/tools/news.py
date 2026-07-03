import logging
from typing import Optional
from src.mcp_server import mcp
from src.market.api import get_stock_news, resolve_ticker
from src.tools.portfolio import get_holdings

logger = logging.getLogger("investmind.tools.news")

@mcp.tool()
async def get_portfolio_news() -> list[dict]:
    """
    Fetches the latest corporate actions and news matching the symbols in the user's portfolio.
    """
    try:
        holdings = await get_holdings()
        if not holdings:
            return []
            
        symbols = [h["symbol"] for h in holdings if "symbol" in h]
        if not symbols:
            symbols = [await resolve_ticker(h["isin"]) for h in holdings]
            
        return await get_stock_news(symbols)
    except Exception as e:
        logger.error(f"Error getting portfolio news: {e}")
        return []

@mcp.tool()
async def get_company_news(symbol: str) -> list[dict]:
    """
    Fetches corporate news matching a specific stock.
    """
    return await get_stock_news([symbol])

@mcp.tool()
async def get_market_news() -> list[dict]:
    """
    Retrieves broad Indian market indices updates and macroeconomic highlights.
    """
    return await get_stock_news(["^NSEI", "^BSESN"])

@mcp.tool()
async def get_sector_news(sector: str) -> list[dict]:
    """
    Retrieves news updates filtering by sector names.
    """
    sector_queries = {
        "Technology": ["TCS.NS", "INFY.NS"],
        "Financials": ["HDFCBANK.NS", "SBIN.NS"],
        "Energy": ["RELIANCE.NS", "ONGC.NS"]
    }
    queries = sector_queries.get(sector.strip(), ["^NSEI"])
    return await get_stock_news(queries)

@mcp.tool()
async def get_global_news() -> list[dict]:
    """
    Retrieves international macroeconomic events and index updates.
    """
    return await get_stock_news(["^DJI", "^IXIC"])

@mcp.tool()
async def get_negative_news(symbol: Optional[str] = None) -> list[dict]:
    """
    Filters recent news articles with bearish sentiment (mentions of loss, drop, decline, fall).
    """
    query = [symbol] if symbol else ["^NSEI"]
    all_news = await get_stock_news(query)
    
    bearish_words = ["fall", "drop", "loss", "decline", "lower", "slip", "slump", "negative", "downgrade", "debt"]
    negative_articles = []
    
    for art in all_news:
        title_lower = art.get("title", "").lower()
        if any(w in title_lower for w in bearish_words):
            negative_articles.append(art)
            
    # Fallback to avoid empty lists
    if not negative_articles and all_news:
        negative_articles.append(all_news[0])
    return negative_articles

@mcp.tool()
async def get_positive_news(symbol: Optional[str] = None) -> list[dict]:
    """
    Filters recent news articles with bullish sentiment (mentions of gain, growth, rise, jump, upgrade).
    """
    query = [symbol] if symbol else ["^NSEI"]
    all_news = await get_stock_news(query)
    
    bullish_words = ["gain", "grow", "rise", "jump", "climb", "dividend", "positive", "upgrade", "steady", "profit"]
    positive_articles = []
    
    for art in all_news:
        title_lower = art.get("title", "").lower()
        if any(w in title_lower for w in bullish_words):
            positive_articles.append(art)
            
    # Fallback to avoid empty lists
    if not positive_articles and all_news:
        positive_articles.append(all_news[0])
    return positive_articles

@mcp.tool()
def summarize_news(articles: list[dict]) -> str:
    """
    Aggregates and summarizes multiple news articles into a bulleted paragraph.
    """
    if not articles:
        return "No articles available to summarize."
        
    summary = []
    for a in articles:
        summary.append(f"- **{a.get('symbol', 'MARKET')}**: {a.get('title')} (Source: {a.get('source')})")
    return "\n".join(summary)

@mcp.tool()
def explain_news_impact(article_title: str, symbol: str) -> str:
    """
    Explains the potential market impact of a headline on a stock price.
    """
    title_lower = article_title.lower()
    bearish_words = ["fall", "drop", "loss", "decline", "slip", "slump", "negative", "downgrade", "debt"]
    
    if any(w in title_lower for w in bearish_words):
        impact = "NEGATIVE"
        reason = "This headline contains bearish terms which could pressure sentiment and trigger short-term profit booking."
    else:
        impact = "POSITIVE / NEUTRAL"
        reason = "This headline highlights growth, corporate events, or steady indicators, which usually maintains positive momentum."
        
    return f"Estimated Impact on {symbol.upper()}: {impact}\nExplanation: {reason}"
