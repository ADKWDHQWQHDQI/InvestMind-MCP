import logging
from src.mcp_server import mcp
from src.tools.portfolio import get_holdings, get_portfolio_summary
from src.tools.stock import get_stock_ratios, get_stock_analysis
from src.tools.technical import (
    calculate_rsi, 
    calculate_macd, 
    detect_breakdown, 
    detect_breakout
)

logger = logging.getLogger("investmind.tools.portfolio_intelligence")

@mcp.tool()
async def analyze_portfolio() -> dict:
    """
    Performs complete quantitative and qualitative review of user holdings.
    Use this to get an overview of the portfolio, including sector allocations and overall value.
    """
    return await get_portfolio_summary()

@mcp.tool()
async def analyze_stock(symbol: str) -> dict:
    """
    Runs an AI valuation, growth, quality, and technical review on a stock.
    Aggregates fundamental ratios, financial strength, RSI, and MACD into one report.
    """
    analysis = await get_stock_analysis(symbol)
    ratios = await get_stock_ratios(symbol)
    rsi = await calculate_rsi(symbol) or 50.0
    macd = await calculate_macd(symbol)
    
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
        "rsi_14": rsi,
        "macd": macd
    }

@mcp.tool()
async def ask_portfolio(query: str) -> dict:
    """
    Natural language entry point to ask questions about the portfolio.
    Example queries: "Why is my portfolio down?", "Am I overexposed to tech?", "How much dividend will I get?"
    """
    # This tool acts as an intent router / generic data fetcher for the LLM
    summary = await get_portfolio_summary()
    
    # In a full implementation, this might call an embedding search or a specialized agent.
    # For MCP, providing the summary and acknowledging the query lets the LLM reason over the raw data.
    return {
        "query": query,
        "context": "The LLM should use this portfolio summary to answer the user's natural language query.",
        "portfolio_summary": summary
    }

@mcp.tool()
async def why_portfolio_down() -> dict:
    """
    Analyzes recent negative changes and technical breakdowns in active holdings 
    to explain why the portfolio might be losing value.
    """
    holdings = await get_holdings()
    breakdowns = []
    
    # Check for technical breakdowns in top holdings
    for h in sorted(holdings, key=lambda x: x.get("invested_value", 0), reverse=True)[:5]:
        symbol = h.get("symbol")
        if symbol:
            bd = await detect_breakdown(symbol)
            if bd.get("breakdown"):
                breakdowns.append(bd)
                
    return {
        "analysis_type": "portfolio_decline_analysis",
        "technical_breakdowns": breakdowns,
        "market_context": "If breakdowns are empty, the decline might be due to broader market conditions rather than specific asset support failures."
    }

@mcp.tool()
async def largest_risks() -> dict:
    """
    Aggregates concentration risks, high P/E (overvalued) stocks, and technical warnings.
    """
    summary = await get_portfolio_summary()
    concentration_risks = summary.get("concentration_risks", [])
    
    holdings = await get_holdings()
    overvalued = []
    
    for h in holdings:
        symbol = h.get("symbol")
        if symbol:
            ratios = await get_stock_ratios(symbol)
            pe = ratios.get("pe_ratio")
            if pe and pe > 45.0:
                overvalued.append({"symbol": symbol, "pe_ratio": pe})
                
    return {
        "concentration_risks": concentration_risks,
        "overvalued_holdings_pe_gt_45": overvalued,
        "risk_level": "HIGH" if len(concentration_risks) > 2 or len(overvalued) > 2 else "MODERATE"
    }

@mcp.tool()
async def largest_opportunities() -> dict:
    """
    Aggregates undervalued (low P/E) stocks, technical breakouts, and high dividend yields in the portfolio.
    """
    holdings = await get_holdings()
    undervalued = []
    breakouts = []
    
    for h in holdings:
        symbol = h.get("symbol")
        if symbol:
            # Check valuation
            ratios = await get_stock_ratios(symbol)
            pe = ratios.get("pe_ratio")
            if pe and pe < 15.0 and pe > 0:
                undervalued.append({"symbol": symbol, "pe_ratio": pe})
                
            # Check technicals
            bo = await detect_breakout(symbol)
            if bo.get("breakout"):
                breakouts.append(bo)
                
    return {
        "undervalued_holdings_pe_lt_15": undervalued,
        "technical_breakouts": breakouts
    }

@mcp.tool()
async def portfolio_health() -> dict:
    """
    Returns a composite health score based on diversification, quality, and risk.
    """
    summary = await get_portfolio_summary()
    sectors = len(summary.get("sector_allocation", []))
    holdings_count = summary.get("summary", {}).get("total_holdings_count", 0)
    
    div_score = min(30 + (sectors * 10) + (holdings_count * 3), 100)
    
    risks = await largest_risks()
    risk_deduction = len(risks["concentration_risks"]) * 10 + len(risks["overvalued_holdings_pe_gt_45"]) * 5
    
    health_score = max(min(div_score - risk_deduction, 100), 0)
    
    return {
        "overall_health_score": health_score,
        "rating": "EXCELLENT" if health_score > 80 else "FAIR" if health_score > 50 else "POOR",
        "diversification_metric": div_score,
        "risk_deductions": risk_deduction
    }

@mcp.tool()
async def rebalance_portfolio() -> dict:
    """
    Provides concrete buy/sell suggestions to align with standard diversification rules 
    and reduce sector concentration.
    """
    summary = await get_portfolio_summary()
    sectors = summary.get("sector_allocation", [])
    
    suggestions = []
    for s in sectors:
        if s["weight_pct"] > 30.0:
            suggestions.append({
                "sector": s["sector"],
                "current_weight": s["weight_pct"],
                "action": "REDUCE",
                "reason": f"Exposure exceeds 30%. Consider trimming positions in {s['sector']}."
            })
        elif s["weight_pct"] < 5.0 and s["sector"] != "Unknown":
            suggestions.append({
                "sector": s["sector"],
                "current_weight": s["weight_pct"],
                "action": "INCREASE",
                "reason": f"Underweight exposure. Consider adding to {s['sector']} for better diversification."
            })
            
    return {
        "status": "REBALANCE REQUIRED" if suggestions else "ALIGNED",
        "suggestions": suggestions
    }

@mcp.tool()
async def dividend_projection() -> dict:
    """
    Calculates projected annual dividend income based on current holdings and historical yields.
    """
    holdings = await get_holdings()
    total_projected_income = 0.0
    dividend_payers = []
    
    for h in holdings:
        symbol = h.get("symbol")
        qty = h.get("quantity", 0)
        if symbol and qty > 0:
            ratios = await get_stock_ratios(symbol)
            yield_pct = ratios.get("dividend_yield")
            if yield_pct and yield_pct > 0:
                # Estimate income based on invested value * yield (simplified)
                # For more accuracy, we'd need live price * qty * yield, but invested_value is a proxy
                val = h.get("invested_value", 0)
                if val > 0:
                    annual_income = val * yield_pct
                    total_projected_income += annual_income
                    dividend_payers.append({
                        "symbol": symbol,
                        "yield_pct": round(yield_pct * 100, 2),
                        "projected_annual_income": round(annual_income, 2)
                    })
                    
    return {
        "total_projected_annual_income": round(total_projected_income, 2),
        "dividend_payers": sorted(dividend_payers, key=lambda x: x["projected_annual_income"], reverse=True)
    }

@mcp.tool()
async def upcoming_events() -> dict:
    """
    Checks for earnings, splits, and dividends in the near future for active holdings.
    """
    from src.tools.stock import get_stock_events
    holdings = await get_holdings()
    events_found = []
    
    # Check top holdings for events to save API calls
    for h in sorted(holdings, key=lambda x: x.get("invested_value", 0), reverse=True)[:10]:
        symbol = h.get("symbol")
        if symbol:
            events = await get_stock_events(symbol)
            if events and isinstance(events, dict) and events.get("earnings"):
                events_found.append({
                    "symbol": symbol,
                    "events": events
                })
                
    return {
        "upcoming_events": events_found,
        "note": "Checked events for top 10 holdings."
    }
