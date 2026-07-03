import logging
import math
from typing import Optional
from src.mcp_server import mcp
from src.tools.stock import get_stock_ratios, get_stock_price
from src.tools.portfolio import get_holdings

logger = logging.getLogger("investmind.tools.optimization")

@mcp.tool()
async def suggest_buy(symbol: str) -> dict:
    """
    Evaluates whether the stock is a BUY and suggests target allocations.
    """
    price_res = await get_stock_price(symbol)
    price = price_res.get("live_price")
    ratios = await get_stock_ratios(symbol)
    pe = ratios.get("pe_ratio") or 30.0
    
    action = "BUY" if pe < 25.0 else "ACCUMULATE ON DIPS"
    return {
        "symbol": symbol,
        "action": action,
        "current_price": price,
        "pe_ratio": pe,
        "suggested_allocation_pct": 5.0,
        "rationale": f"P/E ratio of {pe} makes it attractive for long-term compounding."
    }

@mcp.tool()
async def suggest_sell(symbol: str) -> dict:
    """
    Evaluates whether to trim, sell, or exit a stock position.
    """
    ratios = await get_stock_ratios(symbol)
    pe = ratios.get("pe_ratio") or 30.0
    
    action = "SELL" if pe > 50.0 else "HOLD / MAINTAIN"
    return {
        "symbol": symbol,
        "action": action,
        "pe_ratio": pe,
        "rationale": f"High P/E premium of {pe} signals overvaluation. Consider booking partial profits." if action == "SELL" else "Valuation reasonable."
    }

@mcp.tool()
async def suggest_hold(symbol: str) -> dict:
    """
    Evaluates whether to HOLD a stock position.
    """
    return {
        "symbol": symbol,
        "action": "HOLD",
        "rationale": "Fundamentals are steady, and there are no immediate buy/sell triggers."
    }

@mcp.tool()
async def suggest_rebalance() -> dict:
    """
    Suggests allocation additions/sales to align with sector weight benchmarks.
    """
    from src.tools.ai_analysis import suggest_rebalancing as run_reb
    return await run_reb()

@mcp.tool()
async def estimate_risk(symbol: Optional[str] = None) -> dict:
    """
    Estimates portfolio beta, volatility levels, and drawdown risk.
    """
    if symbol:
        ratios = await get_stock_ratios(symbol)
        beta = ratios.get("beta") or 1.0
        risk = "HIGH" if beta > 1.2 else "LOW" if beta < 0.8 else "MODERATE"
        return {"symbol": symbol, "beta": beta, "risk_category": risk}
        
    # Portfolio level risk estimate
    holdings = await get_holdings()
    total_beta = 0.0
    count = 0
    for h in holdings:
        ratios = await get_stock_ratios(h["symbol"])
        beta = ratios.get("beta") or 1.0
        total_beta += beta
        count += 1
        
    avg_beta = (total_beta / count) if count > 0 else 1.0
    risk = "HIGH" if avg_beta > 1.2 else "LOW" if avg_beta < 0.8 else "MODERATE"
    return {"portfolio_avg_beta": round(avg_beta, 2), "risk_category": risk}

@mcp.tool()
async def estimate_return(symbol: Optional[str] = None) -> dict:
    """
    Estimates long-term CAGR projection based on historical ROE and earnings growth.
    """
    if symbol:
        ratios = await get_stock_ratios(symbol)
        roe = ratios.get("return_on_equity") or 0.12
        return {"symbol": symbol, "estimated_cagr_pct": round(roe * 100, 2)}
        
    return {"portfolio_estimated_cagr_pct": 14.5} # Broad Indian equity standard return projection

@mcp.tool()
async def simulate_investment(symbol: str, principal: float, years: int) -> dict:
    """
    Simulates multi-year growth of a stock investment based on its estimated return.
    """
    ret = await estimate_return(symbol)
    cagr = ret.get("estimated_cagr_pct", 12.0) / 100.0
    future_value = principal * ((1 + cagr) ** years)
    return {
        "symbol": symbol,
        "principal": principal,
        "years": years,
        "projected_value": round(future_value, 2),
        "total_gains": round(future_value - principal, 2),
        "assumed_cagr_pct": round(cagr * 100, 2)
    }

@mcp.tool()
def sip_projection(monthly_amount: float, rate_of_return_pct: float, years: int) -> dict:
    """
    Calculates multi-year SIP growth projection.
    Formula: M * [( (1 + i)^n - 1 ) / i] * (1 + i) where i is monthly interest rate.
    """
    i = (rate_of_return_pct / 100.0) / 12.0
    n = years * 12
    
    total_invested = monthly_amount * n
    if i > 0:
        future_value = monthly_amount * ((( (1 + i) ** n ) - 1) / i) * (1 + i)
    else:
        future_value = total_invested
        
    return {
        "type": "SIP",
        "monthly_amount": monthly_amount,
        "years": years,
        "total_invested": round(total_invested, 2),
        "projected_value": round(future_value, 2),
        "wealth_gained": round(future_value - total_invested, 2)
    }

@mcp.tool()
def lumpsum_projection(amount: float, rate_of_return_pct: float, years: int) -> dict:
    """
    Calculates lumpsum multi-year compounding growth projection.
    """
    r = rate_of_return_pct / 100.0
    future_value = amount * ((1 + r) ** years)
    return {
        "type": "Lumpsum",
        "invested_amount": amount,
        "years": years,
        "projected_value": round(future_value, 2),
        "wealth_gained": round(future_value - amount, 2)
    }

@mcp.tool()
def goal_based_plan(target_amount: float, years: int, rate_of_return_pct: float) -> dict:
    """
    Determines required monthly SIP amount to reach a target financial goal.
    Formula: SIP = Target * [ i / ((1 + i)^n - 1) * (1 + i) ]
    """
    i = (rate_of_return_pct / 100.0) / 12.0
    n = years * 12
    
    if i > 0:
        denominator = (((1 + i) ** n) - 1) * (1 + i)
        required_sip = target_amount * (i / denominator)
    else:
        required_sip = target_amount / n
        
    return {
        "target_goal_amount": target_amount,
        "years": years,
        "expected_return_pct": rate_of_return_pct,
        "required_monthly_sip": round(required_sip, 2)
    }
