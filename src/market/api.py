import random
import logging
from datetime import datetime

logger = logging.getLogger("investmind.market")

# Baseline prices for popular Indian stocks (in INR)
BASE_PRICES = {
    "RELIANCE": 2450.0,
    "ADANIENT": 3100.0,
    "ITC": 430.0,
    "ICICIBANK": 980.0,
    "HDFCBANK": 1650.0,
    "INFY": 1560.0,
    "TCS": 3850.0,
    "NTPC": 360.0,
    "PFC": 420.0,
    "REC": 510.0,
    "HAL": 3400.0,
    "BEL": 180.0,
    "TATAMOTORS": 920.0,
}

# Simulated corporate news database
MOCK_NEWS_DATABASE = [
    {"symbol": "RELIANCE", "title": "Reliance Industries announces new solar gigafactory in Gujarat.", "source": "Mint", "sentiment": "Positive"},
    {"symbol": "INFY", "title": "Infosys expands AI partnership with Microsoft to accelerate enterprise adoption.", "source": "Economic Times", "sentiment": "Positive"},
    {"symbol": "TCS", "title": "TCS signs $800M digital transformation deal with European retail giant.", "source": "Business Standard", "sentiment": "Positive"},
    {"symbol": "REC", "title": "REC Board declares an interim dividend of Rs 5 per equity share.", "source": "Moneycontrol", "sentiment": "Positive"},
    {"symbol": "PFC", "title": "PFC reports 18% growth in quarterly profit, net NPA drops below 1%.", "source": "Financial Express", "sentiment": "Positive"},
    {"symbol": "NTPC", "title": "NTPC green energy arm targets 3GW capacity addition by Q4.", "source": "LiveMint", "sentiment": "Positive"},
    {"symbol": "TATAMOTORS", "title": "Tata Motors commercial vehicle sales see 5% growth month-on-month.", "source": "CNBC-TV18", "sentiment": "Neutral"},
    {"symbol": "HAL", "title": "HAL receives defense ministry RFP for 97 light combat aircraft (LCA Tejas).", "source": "PIB", "sentiment": "Positive"},
    {"symbol": "BEL", "title": "Bharat Electronics registers order book expansion with defense contracts worth Rs 3,000 Cr.", "source": "Economic Times", "sentiment": "Positive"},
    {"symbol": "HDFCBANK", "title": "HDFC Bank opens 100 new branches across semi-urban districts.", "source": "Mint", "sentiment": "Neutral"},
]

def get_live_prices(symbols: list[str]) -> dict[str, float]:
    """
    Simulates fetching live stock prices from BSE/NSE.
    Returns a dictionary mapping symbols to current prices in INR.
    """
    prices = {}
    for sym in symbols:
        sym_upper = sym.upper().strip()
        base = BASE_PRICES.get(sym_upper, 150.0)  # Default fallback price
        # Add minor random fluctuation (-1.5% to +1.5%) to simulate real-time price action
        change_pct = random.uniform(-0.015, 0.015)
        prices[sym_upper] = round(base * (1 + change_pct), 2)
    return prices

def get_stock_news(symbols: list[str]) -> list[dict]:
    """
    Fetches latest corporate news for the provided list of stock symbols.
    """
    matched_news = []
    symbol_set = {s.upper().strip() for s in symbols}
    
    # Filter news matching user's portfolio symbols
    for item in MOCK_NEWS_DATABASE:
        if item["symbol"] in symbol_set:
            matched_news.append({
                "symbol": item["symbol"],
                "title": item["title"],
                "source": item["source"],
                "sentiment": item["sentiment"],
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            
    # Add a fallback market news item if no portfolio-specific news matches
    if not matched_news:
        matched_news.append({
            "symbol": "MARKET",
            "title": "Nifty holds 24,000 support level; auto and defense stocks show strength.",
            "source": "BSE India",
            "sentiment": "Neutral",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
    return matched_news
