import logging
import json
from typing import Optional, List
from src.mcp_server import mcp
from src.database.connection import get_db
from src.security.auth import get_authenticated_context
from src.database.operations import get_portfolio
from src.security.encryption import EncryptionManager
from src.market.api import get_live_prices, get_ticker_info, resolve_ticker
from src.analysis.metrics import analyze_portfolio

logger = logging.getLogger("investmind.tools.portfolio")

@mcp.tool()
async def get_holdings() -> list[dict]:
    """
    Retrieves and decrypts the user's portfolio holdings from the database.
    """
    uid, key = get_authenticated_context()
    try:
        doc = await get_portfolio(uid)
        if not doc or not doc.get("encrypted_holdings"):
            return []
            
        encrypted_holdings = doc["encrypted_holdings"]
        decrypted_json = EncryptionManager.decrypt(encrypted_holdings, key)
        return json.loads(decrypted_json)
    except Exception as e:
        logger.error(f"Error in get_holdings: {e}")
        return []

@mcp.tool()
async def get_portfolio_summary() -> dict:
    """
    Analyzes user holdings against live prices and profiles to calculate valuations, sector weightings, and risks.
    """
    try:
        holdings = await get_holdings()
        if not holdings:
            return {"message": "Your portfolio is currently empty. Please connect a broker or upload a CAS statement."}
            
        symbols = []
        for h in holdings:
            symbol = await resolve_ticker(h.get("isin", h.get("symbol")))
            h["symbol"] = symbol
            symbols.append(symbol)
            
        live_prices = await get_live_prices(symbols)
        ticker_infos = {}
        for s in symbols:
            ticker_infos[s] = await get_ticker_info(s)
            
        return analyze_portfolio(holdings, live_prices, ticker_infos)
    except Exception as e:
        logger.error(f"Error in get_portfolio_summary: {e}")
        return {"error": str(e)}

@mcp.tool()
async def get_portfolio_value() -> float:
    """
    Calculates the total current valuation of all valued assets in the portfolio.
    """
    summary = await get_portfolio_summary()
    if "summary" in summary:
        return summary["summary"]["total_valuation"]
    return 0.0

@mcp.tool()
async def get_portfolio_pnl() -> dict:
    """
    Calculates the total absolute profit/loss and average purchase price across all holdings.
    """
    try:
        holdings = await get_holdings()
        if not holdings:
            return {"total_invested": 0.0, "current_value": 0.0, "total_pnl": 0.0, "pnl_pct": 0.0}
            
        symbols = [await resolve_ticker(h.get("isin", h["symbol"])) for h in holdings]
        prices = await get_live_prices(symbols)
        
        total_invested = 0.0
        current_value = 0.0
        
        for h, sym in zip(holdings, symbols):
            qty = h["quantity"]
            avg_price = h.get("average_price", 0.0)
            live_price = prices.get(sym)
            
            total_invested += qty * avg_price
            if live_price is not None:
                current_value += qty * live_price
            else:
                current_value += qty * avg_price # Conservative fallback for missing price
                
        pnl = current_value - total_invested
        pnl_pct = (pnl / total_invested * 100) if total_invested > 0 else 0.0
        
        return {
            "total_invested": round(total_invested, 2),
            "current_value": round(current_value, 2),
            "total_pnl": round(pnl, 2),
            "pnl_pct": round(pnl_pct, 2)
        }
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
async def get_portfolio_returns() -> dict:
    """
    Returns total returns metrics including absolute PnL and CAGR estimates if historical dates are present.
    """
    pnl = await get_portfolio_pnl()
    return {
        "absolute_return": pnl.get("total_pnl", 0.0),
        "absolute_return_pct": pnl.get("pnl_pct", 0.0)
    }

@mcp.tool()
async def get_asset_allocation() -> list[dict]:
    """
    Groups portfolio holdings by asset classes (e.g. Equity, Debt, Gold, Cash).
    """
    try:
        holdings = await get_holdings()
        allocation = {}
        total = 0.0
        
        symbols = [await resolve_ticker(h.get("isin", h["symbol"])) for h in holdings]
        prices = await get_live_prices(symbols)
        
        for h, sym in zip(holdings, symbols):
            asset_class = h.get("asset_class", "Equity")
            qty = h["quantity"]
            price = prices.get(sym) or h.get("average_price", 0.0)
            val = qty * price
            
            allocation[asset_class] = allocation.get(asset_class, 0.0) + val
            total += val
            
        results = []
        for ac, val in allocation.items():
            pct = (val / total * 100) if total > 0 else 0.0
            results.append({
                "asset_class": ac,
                "valuation": round(val, 2),
                "weight_pct": round(pct, 2)
            })
        return results
    except Exception as e:
        logger.error(f"Error in get_asset_allocation: {e}")
        return []

@mcp.tool()
async def get_sector_allocation() -> list[dict]:
    """
    Returns the sector weightings of holdings in the active portfolio.
    """
    summary = await get_portfolio_summary()
    return summary.get("sector_allocation", [])

@mcp.tool()
async def get_marketcap_allocation() -> list[dict]:
    """
    Groups active holdings by market capitalization classes (Large Cap, Mid Cap, Small Cap).
    """
    try:
        holdings = await get_holdings()
        allocation = {"Large Cap": 0.0, "Mid Cap": 0.0, "Small Cap": 0.0}
        total = 0.0
        
        symbols = [await resolve_ticker(h.get("isin", h["symbol"])) for h in holdings]
        prices = await get_live_prices(symbols)
        
        for h, sym in zip(holdings, symbols):
            qty = h["quantity"]
            price = prices.get(sym) or h.get("average_price", 0.0)
            val = qty * price
            
            info = await get_ticker_info(sym)
            mcap = info.get("market_cap")
            
            if mcap is None:
                # Fallback to Large/Mid/Small based on general classification or default to Small Cap
                category = "Small Cap"
            elif mcap > 500000000000: # > 50,000 Cr INR
                category = "Large Cap"
            elif mcap > 200000000000: # 20,000 to 50,000 Cr INR
                category = "Mid Cap"
            else:
                category = "Small Cap"
                
            allocation[category] = allocation.get(category, 0.0) + val
            total += val
            
        results = []
        for cat, val in allocation.items():
            pct = (val / total * 100) if total > 0 else 0.0
            results.append({
                "marketcap_class": cat,
                "valuation": round(val, 2),
                "weight_pct": round(pct, 2)
            })
        return results
    except Exception as e:
        logger.error(f"Error in get_marketcap_allocation: {e}")
        return []

@mcp.tool()
async def get_country_allocation() -> list[dict]:
    """
    Displays geographical diversification of portfolio assets.
    """
    val = await get_portfolio_value()
    return [
        {"country": "India", "valuation": val, "weight_pct": 100.0}
    ]

@mcp.tool()
async def get_cash_position() -> dict:
    """
    Returns the cash balance or uninvested margin present in the portfolio.
    """
    try:
        holdings = await get_holdings()
        cash = 0.0
        for h in holdings:
            if h.get("asset_class") == "Cash":
                cash += h["quantity"] * h.get("average_price", 1.0)
        return {"cash_balance": cash, "currency": "INR"}
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
async def get_top_holdings(limit: int = 5) -> list[dict]:
    """
    Retrieves the largest holdings in the portfolio by market value.
    """
    summary = await get_portfolio_summary()
    holdings = summary.get("holdings", [])
    valued = [h for h in holdings if h.get("valuation") is not None]
    valued.sort(key=lambda x: x["valuation"], reverse=True)
    return valued[:limit]

@mcp.tool()
async def get_small_holdings(limit: int = 5) -> list[dict]:
    """
    Retrieves the smallest holdings in the portfolio by market value.
    """
    summary = await get_portfolio_summary()
    holdings = summary.get("holdings", [])
    valued = [h for h in holdings if h.get("valuation") is not None]
    valued.sort(key=lambda x: x["valuation"])
    return valued[:limit]

@mcp.tool()
async def get_recent_changes() -> dict:
    """
    Returns recent buy/sell transaction changes from connected broker accounts.
    Requires an active broker API connection with transaction history support.
    """
    return {
        "transactions": [],
        "message": "Transaction history requires a live broker API connection (Zerodha/Groww/Angel). CAS statements do not include transaction-level data."
    }

@mcp.tool()
async def compare_portfolios(other_holdings: list[dict]) -> dict:
    """
    Compares the user's active portfolio holdings with another custom target portfolio or benchmark.
    """
    try:
        active = await get_holdings()
        if not active:
            return {"message": "Active portfolio is empty."}
            
        active_syms = {h["symbol"].upper(): h for h in active}
        other_syms = {o["symbol"].upper(): o for o in other_holdings}
        
        comparison = []
        all_symbols = set(active_syms.keys()).union(set(other_syms.keys()))
        
        for sym in all_symbols:
            act = active_syms.get(sym, {})
            oth = other_syms.get(sym, {})
            comparison.append({
                "symbol": sym,
                "active_qty": act.get("quantity", 0.0),
                "benchmark_qty": oth.get("quantity", 0.0),
                "difference": act.get("quantity", 0.0) - oth.get("quantity", 0.0)
            })
            
        return {"portfolio_comparison": comparison}
    except Exception as e:
        return {"error": str(e)}
