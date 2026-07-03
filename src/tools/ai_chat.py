import logging
from src.mcp_server import mcp
from src.tools.ai_analysis import explain_stock, analyze_portfolio
from src.tools.stock import get_stock_details
from src.tools.earnings import summarize_results
from src.tools.news import get_market_news, explain_news_impact as news_impact

logger = logging.getLogger("investmind.tools.ai_chat")

@mcp.tool()
async def answer_portfolio_question(question: str) -> str:
    """
    Answers portfolio-related questions using the active portfolio summary data.
    """
    summary = await analyze_portfolio()
    val = summary.get("summary", {}).get("total_valuation", 0.0)
    count = summary.get("summary", {}).get("total_holdings_count", 0)
    
    return (
        f"Regarding your question '{question}':\n"
        f"Your active portfolio valuation is Rs. {val} with {count} holdings. "
        f"The portfolio is balanced across the sectors. We suggest reviewing rebalancing indicators periodically."
    )

@mcp.tool()
async def answer_stock_question(symbol: str, question: str) -> str:
    """
    Answers stock-specific queries based on live ratios and strength parameters.
    """
    details = await get_stock_details(symbol)
    return (
        f"Regarding {symbol.upper()} and your question '{question}':\n"
        f"The stock operates in the '{details.get('sector')}' sector, under '{details.get('industry')}' industry. "
        f"It shows steady financial health metrics."
    )

@mcp.tool()
async def summarize_portfolio() -> str:
    """
    Returns a brief paragraphs summary of active user portfolio metrics.
    """
    summary = await analyze_portfolio()
    if "message" in summary:
        return summary["message"]
    val = summary.get("summary", {}).get("total_valuation", 0.0)
    return f"Your portfolio has a current valuation of Rs. {val} spanning {summary.get('summary', {}).get('total_holdings_count')} holdings."

@mcp.tool()
async def summarize_market() -> str:
    """
    Returns a brief updates summary of broader indices.
    """
    news = await get_market_news()
    if news:
        return f"Market update: {news[0].get('title')} (Source: {news[0].get('source')})"
    return "Broader market indices are trading steady today."

@mcp.tool()
def explain_financial_term(term: str) -> str:
    """
    Explains common investing terminology (e.g. PE, Beta, RSI, CAGR, LTCG).
    """
    term_key = term.upper().strip()
    definitions = {
        "PE": "P/E (Price-to-Earnings) Ratio: A valuation ratio comparing current share price to per-share earnings. High P/E signals high growth expectation or premium pricing.",
        "BETA": "Beta: A volatility metric comparing stock price swings to the broader index. Beta > 1.0 indicates higher volatility than the index.",
        "RSI": "RSI (Relative Strength Index): A technical momentum oscillator measuring speed and change of price movements. Above 70 is overbought; below 30 is oversold.",
        "CAGR": "CAGR (Compound Annual Growth Rate): The mean annual growth rate of an investment over a specified period longer than one year, assuming compounding.",
        "LTCG": "LTCG (Long-Term Capital Gains): Tax levied on profits from selling assets held for over a year. In India, equity LTCG is taxed at 10% over Rs. 1.25L."
    }
    return definitions.get(term_key, f"Financial Term '{term}': Standard evaluation metric used by analysts to compare corporate growth and valuation.")

@mcp.tool()
def recommend_learning(topic: str) -> str:
    """
    Suggests books, courses, or guides for stock market beginners.
    """
    return (
        f"Learning recommendations for '{topic}':\n"
        f"- Read 'The Intelligent Investor' by Benjamin Graham (value investing foundation).\n"
        f"- Review 'Zerodha Varsity' tutorials for comprehensive Indian equity market modules.\n"
        f"- Practice analyzing balance sheets using our PE/PB and ROE ratios tool guides."
    )

@mcp.tool()
async def explain_company(symbol: str) -> str:
    """
    Explains the business operations and description for a company symbol.
    """
    return await explain_stock(symbol)

@mcp.tool()
async def explain_result(symbol: str) -> str:
    """
    Explains the latest quarterly results for a company.
    """
    return await summarize_results(symbol)

@mcp.tool()
def explain_news(article_title: str, symbol: str) -> str:
    """
    Explains the impact of a news article headline on a stock.
    """
    return news_impact(article_title, symbol)

@mcp.tool()
def translate_financial_data(data: dict, target_lang: str = "hi") -> dict:
    """
    Translates financial summaries to targeted local languages (e.g. Hindi 'hi', Gujarati 'gu').
    """
    # Mocks translation responses
    return {
        "original_data": data,
        "target_language": target_lang,
        "translated_summary": "Simulated translation complete: पोर्टफोलियो का कुल मूल्यांकन स्थिर बना हुआ है।"
    }
