import logging
from src.mcp_server import mcp
from src.tools.portfolio import get_holdings, get_portfolio_pnl
from src.market.api import get_live_prices, get_ticker_info, resolve_ticker

logger = logging.getLogger("investmind.tools.tax")

# Mock realized transactions for capital gains tax calculations
MOCK_REALIZED_TRANSACTIONS = [
    {
        "symbol": "INFY.NS",
        "qty": 20,
        "buy_price": 1350.0,
        "sell_price": 1450.0,
        "buy_date": "2025-06-10",
        "sell_date": "2026-06-15"  # Held > 1 year: LTCG
    },
    {
        "symbol": "TCS.NS",
        "qty": 10,
        "buy_price": 3400.0,
        "sell_price": 3200.0,
        "buy_date": "2026-01-15",
        "sell_date": "2026-06-15"  # Held <= 1 year: Short-term Loss
    },
    {
        "symbol": "RECLTD.NS",
        "qty": 50,
        "buy_price": 380.0,
        "sell_price": 450.0,
        "buy_date": "2026-03-01",
        "sell_date": "2026-06-20"  # Held <= 1 year: STCG
    }
]

@mcp.tool()
async def calculate_capital_gains() -> dict:
    """
    Computes Indian STCG and LTCG taxes on equity holdings from realized transactions.
    STCG: 20% on holdings <= 365 days.
    LTCG: 10% on gains exceeding ₹1.25L on holdings > 365 days.
    """
    stcg_gains = 0.0
    ltcg_gains = 0.0
    
    from datetime import datetime
    
    details = []
    for tx in MOCK_REALIZED_TRANSACTIONS:
        buy_dt = datetime.strptime(tx["buy_date"], "%Y-%m-%d")
        sell_dt = datetime.strptime(tx["sell_date"], "%Y-%m-%d")
        holding_days = (sell_dt - buy_dt).days
        
        gain_per_share = tx["sell_price"] - tx["buy_price"]
        total_gain = gain_per_share * tx["qty"]
        
        is_long_term = holding_days > 365
        
        if is_long_term:
            ltcg_gains += total_gain
            category = "LTCG"
        else:
            stcg_gains += total_gain
            category = "STCG"
            
        details.append({
            "symbol": tx["symbol"],
            "qty": tx["qty"],
            "holding_period_days": holding_days,
            "category": category,
            "realized_gain": round(total_gain, 2)
        })
        
    # Calculate Indian Capital Gains Tax (2026 rates)
    # LTCG exempt up to 1.25L (125,000 INR)
    taxable_ltcg = max(0.0, ltcg_gains - 125000.0)
    ltcg_tax = taxable_ltcg * 0.10
    
    # STCG taxed at 20%
    stcg_tax = max(0.0, stcg_gains) * 0.20
    
    return {
        "summary": {
            "total_realized_stcg": round(stcg_gains, 2),
            "total_realized_ltcg": round(ltcg_gains, 2),
            "exempt_ltcg": min(max(0.0, ltcg_gains), 125000.0),
            "estimated_stcg_tax": round(stcg_tax, 2),
            "estimated_ltcg_tax": round(ltcg_tax, 2),
            "total_capital_gains_tax": round(stcg_tax + ltcg_tax, 2)
        },
        "transactions": details
    }

@mcp.tool()
async def calculate_tax() -> dict:
    """
    Computes total tax liability by summing capital gains and dividend income tax.
    """
    gains = await calculate_capital_gains()
    div_income = await dividend_income()
    
    # Dividend income in India is taxed at slab rates. We assume a conservative 20% slab rate.
    div_tax = div_income.get("total_estimated_dividend", 0.0) * 0.20
    
    total_tax = gains["summary"]["total_capital_gains_tax"] + div_tax
    return {
        "capital_gains_tax": gains["summary"]["total_capital_gains_tax"],
        "dividend_tax": round(div_tax, 2),
        "total_estimated_tax": round(total_tax, 2)
    }

@mcp.tool()
async def download_tax_report() -> dict:
    """
    Generates a structured, downloadable text-format capital gains tax report.
    """
    tax = await calculate_tax()
    gains = await calculate_capital_gains()
    
    report = []
    report.append("==================================================")
    report.append("      INVESTMIND ANNUAL CAPITAL GAINS TAX REPORT  ")
    report.append("==================================================")
    report.append(f"STCG Realized Gain: Rs. {gains['summary']['total_realized_stcg']}")
    report.append(f"LTCG Realized Gain: Rs. {gains['summary']['total_realized_ltcg']}")
    report.append(f"Exempt LTCG Limit: Rs. 1,25,000")
    report.append("--------------------------------------------------")
    report.append(f"Estimated STCG Tax (20%): Rs. {gains['summary']['estimated_stcg_tax']}")
    report.append(f"Estimated LTCG Tax (10%): Rs. {gains['summary']['estimated_ltcg_tax']}")
    report.append(f"Estimated Dividend Tax (Slab-20%): Rs. {tax['dividend_tax']}")
    report.append("--------------------------------------------------")
    report.append(f"TOTAL TAX PAYABLE: Rs. {tax['total_estimated_tax']}")
    report.append("==================================================")
    
    return {"success": True, "report_text": "\n".join(report)}

@mcp.tool()
async def realized_pnl() -> dict:
    """
    Returns total realized profit/loss from completed transactions.
    """
    gains = await calculate_capital_gains()
    total = gains["summary"]["total_realized_stcg"] + gains["summary"]["total_realized_ltcg"]
    return {
        "total_realized_pnl": round(total, 2),
        "stcg_pnl": gains["summary"]["total_realized_stcg"],
        "ltcg_pnl": gains["summary"]["total_realized_ltcg"]
    }

@mcp.tool()
async def unrealized_pnl() -> dict:
    """
    Returns unrealized profit/loss on current active holdings.
    """
    pnl = await get_portfolio_pnl()
    return {
        "unrealized_pnl": pnl.get("total_pnl", 0.0),
        "unrealized_pnl_pct": pnl.get("pnl_pct", 0.0)
    }

@mcp.tool()
async def dividend_income() -> dict:
    """
    Estimates annual dividend payouts matching current active portfolio holdings.
    """
    try:
        holdings = await get_holdings()
        if not holdings:
            return {"total_estimated_dividend": 0.0}
            
        symbols = [await resolve_ticker(h.get("isin", h["symbol"])) for h in holdings]
        prices = await get_live_prices(symbols)
        
        total_dividend = 0.0
        details = []
        for h, sym in zip(holdings, symbols):
            qty = h["quantity"]
            price = prices.get(sym) or h.get("average_price", 0.0)
            val = qty * price
            
            info = await get_ticker_info(sym)
            div_yield = info.get("dividend_yield", 0.0)
            est_div = round(val * div_yield, 2)
            
            total_dividend += est_div
            details.append({
                "symbol": sym,
                "dividend_yield": div_yield,
                "estimated_payout": est_div
            })
            
        return {
            "total_estimated_dividend": round(total_dividend, 2),
            "dividend_by_stock": details
        }
    except Exception as e:
        logger.error(f"Error in dividend_income: {e}")
        return {"total_estimated_dividend": 0.0}

@mcp.tool()
async def tax_loss_harvesting() -> dict:
    """
    Scans portfolio for stocks currently trading at a loss to harvest and offset capital gains.
    """
    try:
        holdings = await get_holdings()
        if not holdings:
            return {"message": "Your portfolio is empty.", "harvestable_loss": 0.0, "opportunities": []}
            
        symbols = [await resolve_ticker(h.get("isin", h["symbol"])) for h in holdings]
        prices = await get_live_prices(symbols)
        
        total_loss = 0.0
        opportunities = []
        
        for h, sym in zip(holdings, symbols):
            qty = h["quantity"]
            avg_price = h.get("average_price", 0.0)
            live_price = prices.get(sym)
            
            if live_price is not None and live_price < avg_price:
                loss_per_share = avg_price - live_price
                loss_val = round(loss_per_share * qty, 2)
                total_loss += loss_val
                
                opportunities.append({
                    "symbol": sym,
                    "quantity": qty,
                    "avg_price": avg_price,
                    "live_price": live_price,
                    "harvestable_loss": loss_val,
                    "suggestion": f"Sell {sym} to realize Rs. {loss_val} loss, which can reduce your taxable capital gains. You can buy it back after 30 days if you wish to maintain exposure."
                })
                
        return {
            "total_harvestable_loss": round(total_loss, 2),
            "opportunities": opportunities
        }
    except Exception as e:
        logger.error(f"Error in tax_loss_harvesting: {e}")
        return {"error": str(e)}
