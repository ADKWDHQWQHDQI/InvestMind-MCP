import re

def clean_company_name(name: str) -> str:
    """
    Removes common suffixes from company names to clean them up.
    """
    name = name.upper()
    suffixes = [
        r"\bLTD\b", r"\bLIMITED\b", r"\bEQUITY\b", r"\bEQ\b", r"\bCORP\b", 
        r"\bCORPORATION\b", r"\bIND\b", r"\bINDIA\b", r"\bINDUSTRIES\b"
    ]
    for s in suffixes:
        name = re.sub(s, "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name

def normalize_holdings(raw_holdings: list[dict]) -> list[dict]:
    """
    Normalizes raw holdings into a standard schema.
    Groups duplicate holdings by ISIN.
    """
    normalized_map = {}
    
    for holding in raw_holdings:
        isin = holding.get("isin", "").upper().strip()
        name = holding.get("name", "").strip()
        quantity = float(holding.get("quantity", 0.0))
        
        if not isin or quantity <= 0:
            continue
            
        # Group duplicates by ISIN
        if isin in normalized_map:
            normalized_map[isin]["quantity"] += quantity
        else:
            normalized_map[isin] = {
                "symbol": isin,  # Placeholder, resolved asynchronously during upload
                "isin": isin,
                "name": name,
                "quantity": quantity,
                "average_price": 0.0,
                "asset_class": "Mutual Fund" if "MUTUAL FUND" in name.upper() or "MF" in name.upper() else "Equity"
            }
            
    return list(normalized_map.values())
