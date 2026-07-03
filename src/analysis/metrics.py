import logging

logger = logging.getLogger("investmind.analysis")

SECTOR_MAP = {
    "RELIANCE": "Energy / Oil & Gas",
    "ADANIENT": "Conglomerates",
    "ITC": "FMCG",
    "ICICIBANK": "Financial Services (Banking)",
    "HDFCBANK": "Financial Services (Banking)",
    "INFY": "Technology (IT)",
    "TCS": "Technology (IT)",
    "NTPC": "Power & Utilities",
    "PFC": "Financial Services (NBFC)",
    "REC": "Financial Services (NBFC)",
    "HAL": "Defense & Aerospace",
    "BEL": "Defense & Aerospace",
    "TATAMOTORS": "Automotive",
}

# Estimated annual dividend yields (e.g. 0.05 = 5% yield)
DIVIDEND_YIELD_MAP = {
    "REC": 0.052,
    "PFC": 0.048,
    "ITC": 0.038,
    "NTPC": 0.028,
    "TCS": 0.021,
    "INFY": 0.019,
    "RELIANCE": 0.008,
    "HDFCBANK": 0.012,
    "ICICIBANK": 0.009,
    "HAL": 0.015,
    "BEL": 0.018,
    "TATAMOTORS": 0.006,
}

def analyze_portfolio(holdings: list[dict], live_prices: dict[str, float]) -> dict:
    """
    Computes portfolio analytics including valuations, sector weights, concentration risks,
    and projected dividend incomes.
    """
    total_value = 0.0
    detailed_holdings = []
    sector_valuations = {}
    
    # 1. Valuations and sector accumulation
    for holding in holdings:
        symbol = holding["symbol"].upper()
        quantity = holding["quantity"]
        current_price = live_prices.get(symbol, 150.0)  # Default fallback price
        
        value = round(quantity * current_price, 2)
        total_value += value
        
        sector = SECTOR_MAP.get(symbol, "Others")
        div_yield = DIVIDEND_YIELD_MAP.get(symbol, 0.005)
        est_dividend = round(value * div_yield, 2)
        
        detailed_holdings.append({
            "symbol": symbol,
            "name": holding["name"],
            "isin": holding["isin"],
            "quantity": quantity,
            "current_price": current_price,
            "valuation": value,
            "sector": sector,
            "estimated_annual_dividend": est_dividend
        })
        
        sector_valuations[sector] = sector_valuations.get(sector, 0.0) + value
        
    # 2. Sector Allocation Calculations
    sector_allocation = []
    for sector, val in sector_valuations.items():
        weight = round((val / total_value * 100), 2) if total_value > 0 else 0.0
        sector_allocation.append({
            "sector": sector,
            "valuation": round(val, 2),
            "weight_pct": weight
        })
    sector_allocation.sort(key=lambda x: x["weight_pct"], reverse=True)

    # 3. Individual stock weights & Concentration Risk analysis
    concentration_risks = []
    for h in detailed_holdings:
        weight = round((h["valuation"] / total_value * 100), 2) if total_value > 0 else 0.0
        h["weight_pct"] = weight
        
        if weight > 25.0:
            concentration_risks.append({
                "type": "Single Stock Concentration",
                "item": h["symbol"],
                "weight_pct": weight,
                "message": f"{h['symbol']} represents {weight}% of your portfolio. Consider diversifying if this exceeds your target threshold."
            })
            
    for s in sector_allocation:
        if s["weight_pct"] > 50.0:
            concentration_risks.append({
                "type": "Sector Concentration",
                "item": s["sector"],
                "weight_pct": s["weight_pct"],
                "message": f"Sector '{s['sector']}' represents {s['weight_pct']}% of your portfolio. High sector exposure might increase volatility."
            })
            
    # 4. Total Projected Dividends
    total_est_dividend = round(sum(h["estimated_annual_dividend"] for h in detailed_holdings), 2)
    overall_dividend_yield = round((total_est_dividend / total_value * 100), 2) if total_value > 0 else 0.0

    return {
        "summary": {
            "total_valuation": round(total_value, 2),
            "estimated_annual_dividend": total_est_dividend,
            "overall_dividend_yield_pct": overall_dividend_yield,
            "total_holdings_count": len(holdings)
        },
        "holdings": detailed_holdings,
        "sector_allocation": sector_allocation,
        "concentration_risks": concentration_risks
    }
