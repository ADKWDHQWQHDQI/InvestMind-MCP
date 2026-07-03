import logging

logger = logging.getLogger("investmind.analysis")

def analyze_portfolio(
    holdings: list[dict], 
    live_prices: dict[str, float], 
    ticker_infos: dict[str, dict]
) -> dict:
    """
    Computes portfolio analytics including valuations, sector weights, concentration risks,
    and projected dividend yields using dynamically fetched market metadata.
    """
    total_value = 0.0
    detailed_holdings = []
    sector_valuations = {}
    
    for holding in holdings:
        symbol = holding["symbol"].upper()
        quantity = holding["quantity"]
        current_price = live_prices.get(symbol, 150.0)
        
        value = round(quantity * current_price, 2)
        total_value += value
        
        # Retrieve dynamic info
        info = ticker_infos.get(symbol, {"sector": "Others", "dividend_yield": 0.005, "name": holding["name"]})
        sector = info.get("sector", "Others")
        div_yield = info.get("dividend_yield", 0.005)
        est_dividend = round(value * div_yield, 2)
        
        detailed_holdings.append({
            "symbol": symbol,
            "name": info.get("name") or holding["name"],
            "isin": holding["isin"],
            "quantity": quantity,
            "current_price": current_price,
            "valuation": value,
            "sector": sector,
            "estimated_annual_dividend": est_dividend
        })
        
        sector_valuations[sector] = sector_valuations.get(sector, 0.0) + value
        
    # Sector Allocation
    sector_allocation = []
    for sector, val in sector_valuations.items():
        weight = round((val / total_value * 100), 2) if total_value > 0 else 0.0
        sector_allocation.append({
            "sector": sector,
            "valuation": round(val, 2),
            "weight_pct": weight
        })
    sector_allocation.sort(key=lambda x: x["weight_pct"], reverse=True)

    # Concentration Risk
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
