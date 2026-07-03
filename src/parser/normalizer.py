import re

# Popular Indian stocks ISIN to NSE Ticker mapping
ISIN_TO_TICKER = {
    "INE002A01018": "RELIANCE",
    "INE742F01042": "ADANIENT",
    "INE154A01025": "ITC",
    "INE090A01021": "ICICIBANK",
    "INE040A01034": "HDFCBANK",
    "INE009A01021": "INFY",
    "INE467B01029": "TCS",
    "INE205A01025": "NTPC",
    "INE134E01011": "PFC",
    "INE020B01018": "REC",
    "INE302A01020": "HAL",
    "INE263A01024": "BEL",
    "INE155A01022": "TATAMOTORS",
}

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
    Groups duplicate symbols and maps ISINs to clean tickers.
    """
    normalized_map = {}
    
    for holding in raw_holdings:
        isin = holding.get("isin", "").upper().strip()
        name = holding.get("name", "").strip()
        quantity = float(holding.get("quantity", 0.0))
        
        if not isin or quantity <= 0:
            continue
            
        symbol = ISIN_TO_TICKER.get(isin)
        if not symbol:
            cleaned = clean_company_name(name)
            words = cleaned.split()
            if words:
                symbol = "".join(words[:2])
            else:
                symbol = isin
                
        # Group duplicates (e.g. if listed multiple times)
        if symbol in normalized_map:
            normalized_map[symbol]["quantity"] += quantity
        else:
            normalized_map[symbol] = {
                "symbol": symbol,
                "isin": isin,
                "name": name,
                "quantity": quantity,
                "average_price": 0.0,  # Default, can be refined if statements contain purchase prices
                "asset_class": "Mutual Fund" if "MUTUAL FUND" in name.upper() or "MF" in name.upper() else "Equity"
            }
            
    return list(normalized_map.values())
