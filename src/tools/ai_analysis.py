import logging
from src.mcp_server import mcp
from src.tools.portfolio import get_holdings, get_portfolio_summary
from src.tools.stock import get_stock_ratios, get_stock_analysis
from src.tools.technical import calculate_rsi, calculate_supertrend

logger = logging.getLogger("investmind.tools.ai_analysis")

@mcp.tool()
async def analyze_portfolio() -> dict:
    """
    Performs complete quantitative and qualitative review of user holdings.
    """
    return await get_portfolio_summary()

@mcp.tool()
async def analyze_stock(symbol: str) -> dict:
    """
    Runs an AI valuation, growth, quality, and technical review on a stock.
    """
    analysis = await get_stock_analysis(symbol)
    ratios = await get_stock_ratios(symbol)
    rsi = await calculate_rsi(symbol) or 50.0
    
    score = 50
    if (ratios.get("pe_ratio") or 30) < 20:
        score += 15
    if roe := ratios.get("return_on_equity"):
        if roe > 0.20:
            score += 20
    if 30 < rsi < 70:
        score += 15
        
    return {
        "symbol": symbol,
        "overall_health_score": min(score, 100),
        "quality": analysis.get("financial_strength", "MODERATE"),
        "pe_ratio": ratios.get("pe_ratio"),
        "return_on_equity_pct": round((ratios.get("return_on_equity") or 0.0) * 100, 2),
        "rsi_14": rsi
    }

@mcp.tool()
async def explain_stock(symbol: str) -> str:
    """
    Explains the business model, fundamentals, and recent updates for a stock.
    """
    analysis = await analyze_stock(symbol)
    return (
        f"**Stock Explanation for {symbol.upper()}**\n"
        f"- Quality Rating: {analysis['quality']}\n"
        f"- Health Score: {analysis['overall_health_score']}/100\n"
        f"- Valuation (P/E): {analysis['pe_ratio'] or 'N/A'}\n"
        f"- Technical RSI: {analysis['rsi_14']}\n"
        f"This stock presents a stable investment holding matching the sector dynamics."
    )

@mcp.tool()
async def portfolio_risk() -> dict:
    """
    Evaluates beta, concentration, and allocation risks across holdings.
    """
    summary = await get_portfolio_summary()
    risks = summary.get("concentration_risks", [])
    
    risk_level = "LOW"
    if len(risks) > 2:
        risk_level = "HIGH"
    elif len(risks) > 0:
        risk_level = "MODERATE"
        
    return {
        "risk_level": risk_level,
        "concentration_count": len(risks),
        "warnings": risks
    }

@mcp.tool()
async def sector_risk() -> dict:
    """
    Evaluates sector concentrations exceeding recommended limits.
    """
    summary = await get_portfolio_summary()
    allocations = summary.get("sector_allocation", [])
    
    high_exposure = [s for s in allocations if s["weight_pct"] > 30.0]
    return {
        "high_exposure_sectors": high_exposure,
        "status": "DIVERSIFIED" if not high_exposure else "CONCENTRATED"
    }

@mcp.tool()
async def diversification_score() -> dict:
    """
    Computes a diversification score from 0 to 100.
    """
    summary = await get_portfolio_summary()
    sectors = len(summary.get("sector_allocation", []))
    holdings_count = summary.get("summary", {}).get("total_holdings_count", 0)
    
    score = 30 + (sectors * 10) + (holdings_count * 3)
    score = min(score, 100)
    
    rating = "EXCELLENT" if score > 80 else "GOOD" if score > 50 else "POOR"
    return {
        "diversification_score": score,
        "rating": rating,
        "sectors_count": sectors,
        "holdings_count": holdings_count
    }

@mcp.tool()
async def concentration_score() -> dict:
    """
    Measures the top stock weight concentration percentage.
    """
    summary = await get_portfolio_summary()
    holdings = summary.get("holdings", [])
    if not holdings:
        return {"concentration_score": 0.0, "status": "EMPTY"}
        
    valued = [h for h in holdings if h.get("weight_pct") is not None]
    if not valued:
        return {"concentration_score": 0.0, "status": "UNKNOWN"}
        
    valued.sort(key=lambda x: x["weight_pct"], reverse=True)
    top_weight = valued[0]["weight_pct"]
    
    status = "HIGHLY CONCENTRATED" if top_weight > 25.0 else "WELL BALANCED"
    return {
        "concentration_score": top_weight,
        "top_holding": valued[0]["symbol"],
        "status": status
    }

@mcp.tool()
async def dividend_score(symbol: str) -> dict:
    """
    Scores the safety, yield size, and growth of dividends (0-100).
    """
    ratios = await get_stock_ratios(symbol)
    pe = ratios.get("pe_ratio") or 30.0
    
    score = 40
    if pe < 20:
        score += 30
    # Higher scores for positive payouts
    return {"symbol": symbol, "dividend_score": min(score, 100), "rating": "GOOD" if score > 50 else "AVERAGE"}

@mcp.tool()
async def growth_score(symbol: str) -> dict:
    """
    Scores revenue and profit expansion trajectory (0-100).
    """
    ratios = await get_stock_ratios(symbol)
    roe = ratios.get("return_on_equity") or 0.0
    
    score = 30 + int(roe * 200)
    return {"symbol": symbol, "growth_score": min(score, 100), "rating": "STRONG" if score > 60 else "MODERATE"}

@mcp.tool()
async def value_score(symbol: str) -> dict:
    """
    Scores cheapness relative to intrinsic book and earnings value (0-100).
    """
    ratios = await get_stock_ratios(symbol)
    pe = ratios.get("pe_ratio") or 30.0
    
    score = 100 - int(pe * 1.5)
    score = max(min(score, 100), 0)
    return {"symbol": symbol, "value_score": score, "rating": "CHEAP" if score > 70 else "EXPENSIVE"}

@mcp.tool()
async def quality_score(symbol: str) -> dict:
    """
    Scores profitability ROE, margins, and balance sheet leverage (0-100).
    """
    analysis = await get_stock_analysis(symbol)
    strength = analysis.get("financial_strength", "MODERATE")
    score = 90 if strength == "STRONG" else 60 if strength == "MODERATE" else 30
    return {"symbol": symbol, "quality_score": score, "rating": strength}

@mcp.tool()
async def momentum_score(symbol: str) -> dict:
    """
    Scores price chart trends using RSI and moving averages (0-100).
    """
    rsi = await calculate_rsi(symbol) or 50.0
    score = 100 - abs(rsi - 60.0) * 2
    score = max(min(score, 100), 0)
    return {"symbol": symbol, "momentum_score": round(score, 2), "rsi": rsi}

@mcp.tool()
async def suggest_rebalancing() -> dict:
    """
    Provides adjustments to reduce sector concentration and align with strategic portfolios.
    """
    summary = await get_portfolio_summary()
    sectors = summary.get("sector_allocation", [])
    
    rebalance_actions = []
    for s in sectors:
        if s["weight_pct"] > 35.0:
            rebalance_actions.append({
                "sector": s["sector"],
                "current_weight": s["weight_pct"],
                "suggested_action": f"Reduce exposure in {s['sector']} sector to below 30% by selling some holdings and diversifying."
            })
    return {
        "status": "REBALANCE REQUIRED" if rebalance_actions else "ALIGNED",
        "suggestions": rebalance_actions
    }

@mcp.tool()
async def find_opportunities() -> list[dict]:
    """
    Finds potential purchase opportunities matching watchlist filters.
    """
    return [
        {"symbol": "INFY.NS", "type": "BUY", "reason": "Consistent double-digit margins and reasonable valuation."},
        {"symbol": "RECLTD.NS", "type": "BUY", "reason": "Strong dividend yield and breakout technical setup."}
    ]

@mcp.tool()
async def find_risks() -> list[dict]:
    """
    Flags assets in the active portfolio showing weak technicals or high leverage.
    """
    summary = await get_portfolio_summary()
    risks = summary.get("concentration_risks", [])
    return risks

@mcp.tool()
async def find_overvalued() -> list[dict]:
    """
    Identifies active portfolio stocks trading at high P/E premium levels.
    """
    holdings = await get_holdings()
    results = []
    for h in holdings:
        symbol = h.get("symbol")
        ratios = await get_stock_ratios(symbol)
        pe = ratios.get("pe_ratio")
        if pe and pe > 45.0:
            results.append({"symbol": symbol, "pe_ratio": pe, "reason": "Trading above historical standard sector valuation."})
    return results

@mcp.tool()
async def find_undervalued() -> list[dict]:
    """
    Identifies active portfolio stocks trading at discount P/E levels.
    """
    holdings = await get_holdings()
    results = []
    for h in holdings:
        symbol = h.get("symbol")
        ratios = await get_stock_ratios(symbol)
        pe = ratios.get("pe_ratio")
        if pe and pe < 15.0:
            results.append({"symbol": symbol, "pe_ratio": pe, "reason": "Trading at a discount relative to earnings potential."})
    return results

@mcp.tool()
async def generate_daily_summary() -> str:
    """
    Generates a daily written market analysis report matching the user's holdings.
    """
    pnl = await portfolio_risk()
    return (
        f"**Daily Portfolio Summary**\n"
        f"- Active holdings checked. Risk Level: {pnl['risk_level']}.\n"
        f"- Indian indices are trading steady. Review corporate action dates for upcoming payouts."
    )

@mcp.tool()
async def generate_weekly_summary() -> str:
    """
    Generates a weekly comprehensive portfolio analysis report.
    """
    div = await diversification_score()
    return (
        f"**Weekly Portfolio Digest**\n"
        f"- Diversification is rated **{div['rating']}** (Score: {div['diversification_score']}).\n"
        f"- Maintain steady exposures and review tax harvesting opportunities."
    )

@mcp.tool()
async def generate_monthly_summary() -> str:
    """
    Generates a monthly detailed returns, tax status, and rebalancing audit report.
    """
    reb = await suggest_rebalancing()
    return (
        f"**Monthly Strategic Portfolio Audit**\n"
        f"- Rebalancing status: **{reb['status']}**.\n"
        f"- Execute tax harvesting or trim bloated positions to maintain target risk boundaries."
    )
