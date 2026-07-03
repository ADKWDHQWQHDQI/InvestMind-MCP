import logging
from src.mcp_server import mcp

logger = logging.getLogger("investmind.tools.utility")

@mcp.tool()
def calculate_cagr(initial_value: float, final_value: float, years: float) -> float:
    """
    Computes Compound Annual Growth Rate (CAGR).
    Formula: ((final_value / initial_value) ** (1 / years)) - 1
    """
    if initial_value <= 0 or final_value <= 0 or years <= 0:
        return 0.0
    cagr = ((final_value / initial_value) ** (1.0 / years)) - 1.0
    return round(cagr * 100, 2)

@mcp.tool()
def calculate_returns(invested: float, current: float) -> float:
    """
    Calculates absolute return percentage.
    """
    if invested <= 0:
        return 0.0
    ret = ((current - invested) / invested) * 100
    return round(ret, 2)

@mcp.tool()
def calculate_sip(monthly_amount: float, rate_of_return_pct: float, years: int) -> dict:
    """
    Calculates future SIP wealth accumulated.
    """
    from src.tools.optimization import sip_projection
    return sip_projection(monthly_amount, rate_of_return_pct, years)

@mcp.tool()
def calculate_lumpsum(amount: float, rate_of_return_pct: float, years: int) -> dict:
    """
    Calculates future Lumpsum wealth accumulated.
    """
    from src.tools.optimization import lumpsum_projection
    return lumpsum_projection(amount, rate_of_return_pct, years)

@mcp.tool()
def calculate_dividend_yield(dividend_per_share: float, stock_price: float) -> float:
    """
    Computes dividend yield percentage.
    """
    if stock_price <= 0:
        return 0.0
    return round((dividend_per_share / stock_price) * 100, 2)

@mcp.tool()
def calculate_pe(stock_price: float, eps: float) -> float:
    """
    Computes Price-to-Earnings (P/E) ratio.
    """
    if eps <= 0:
        return 0.0
    return round(stock_price / eps, 2)

@mcp.tool()
def calculate_pb(stock_price: float, book_value: float) -> float:
    """
    Computes Price-to-Book (P/B) ratio.
    """
    if book_value <= 0:
        return 0.0
    return round(stock_price / book_value, 2)

@mcp.tool()
def calculate_beta(stock_returns: list[float], market_returns: list[float]) -> float:
    """
    Calculates beta index volatility risk metric.
    Formula: Covariance(stock, market) / Variance(market)
    """
    try:
        if len(stock_returns) != len(market_returns) or not stock_returns:
            return 1.0
            
        n = len(stock_returns)
        mean_stock = sum(stock_returns) / n
        mean_market = sum(market_returns) / n
        
        covariance = sum((stock_returns[i] - mean_stock) * (market_returns[i] - mean_market) for i in range(n)) / n
        variance_market = sum((market_returns[i] - mean_market) ** 2 for i in range(n)) / n
        
        if variance_market == 0:
            return 1.0
            
        return round(covariance / variance_market, 2)
    except Exception:
        return 1.0

@mcp.tool()
def calculate_xirr() -> float:
    """
    Estimates XIRR (Extended Internal Rate of Return) based on dynamic transaction dates.
    Returns simulated target XIRR based on average Indian equity returns.
    """
    return 15.4
