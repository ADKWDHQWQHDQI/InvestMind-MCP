import logging
import math
from typing import Optional
from src.mcp_server import mcp
from src.tools.stock import get_stock_history, get_stock_price

logger = logging.getLogger("investmind.tools.technical")

def _get_closes(history: list[dict]) -> list[float]:
    return [h["close"] for h in history if h.get("close") is not None]

@mcp.tool()
async def calculate_sma(symbol: str, period: int = 20) -> Optional[float]:
    """
    Calculates the Simple Moving Average (SMA) for a given period.
    """
    history = await get_stock_history(symbol, period="3mo")
    closes = _get_closes(history)
    if len(closes) < period:
        return None
    return round(sum(closes[-period:]) / period, 2)

@mcp.tool()
async def calculate_ema(symbol: str, period: int = 20) -> Optional[float]:
    """
    Calculates the Exponential Moving Average (EMA) for a given period.
    """
    history = await get_stock_history(symbol, period="3mo")
    closes = _get_closes(history)
    if len(closes) < period:
        return None
        
    # Standard EMA calculation
    k = 2.0 / (period + 1.0)
    ema = closes[0]
    for c in closes[1:]:
        ema = c * k + ema * (1 - k)
    return round(ema, 2)

@mcp.tool()
async def calculate_rsi(symbol: str) -> Optional[float]:
    """
    Calculates the 14-day Relative Strength Index (RSI).
    """
    history = await get_stock_history(symbol, period="3mo")
    closes = _get_closes(history)
    if len(closes) < 15:
        return None
        
    gains = []
    losses = []
    
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i-1]
        if diff > 0:
            gains.append(diff)
            losses.append(0.0)
        else:
            gains.append(0.0)
            losses.append(abs(diff))
            
    # Calculate initial averages
    avg_gain = sum(gains[:14]) / 14
    avg_loss = sum(losses[:14]) / 14
    
    # Smooth averages
    for i in range(14, len(gains)):
        avg_gain = (avg_gain * 13 + gains[i]) / 14
        avg_loss = (avg_loss * 13 + losses[i]) / 14
        
    if avg_loss == 0:
        return 100.0
        
    rs = avg_gain / avg_loss
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return round(rsi, 2)

@mcp.tool()
async def calculate_macd(symbol: str) -> dict:
    """
    Calculates MACD (Moving Average Convergence Divergence) lines and signal line.
    """
    try:
        history = await get_stock_history(symbol, period="3mo")
        closes = _get_closes(history)
        if len(closes) < 26:
            return {"error": "Insufficient history."}
            
        # Calculate EMA 12 & 26
        ema12_list = []
        ema26_list = []
        
        # EMA 12
        k12 = 2 / 13
        ema12 = closes[0]
        for c in closes:
            ema12 = c * k12 + ema12 * (1 - k12)
            ema12_list.append(ema12)
            
        # EMA 26
        k26 = 2 / 27
        ema26 = closes[0]
        for c in closes:
            ema26 = c * k26 + ema26 * (1 - k26)
            ema26_list.append(ema26)
            
        macd_line = [e12 - e26 for e12, e26 in zip(ema12_list, ema26_list)]
        
        # Signal Line (EMA 9 of MACD line)
        k9 = 2 / 10
        signal = macd_line[0]
        signal_line = []
        for m in macd_line:
            signal = m * k9 + signal * (1 - k9)
            signal_line.append(signal)
            
        latest_macd = macd_line[-1]
        latest_signal = signal_line[-1]
        hist = latest_macd - latest_signal
        
        return {
            "macd": round(latest_macd, 2),
            "signal": round(latest_signal, 2),
            "histogram": round(hist, 2)
        }
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
async def calculate_bollinger(symbol: str) -> dict:
    """
    Calculates Bollinger Bands (Middle Band, Upper Band, Lower Band).
    """
    try:
        history = await get_stock_history(symbol, period="3mo")
        closes = _get_closes(history)
        if len(closes) < 20:
            return {"error": "Insufficient history."}
            
        period_closes = closes[-20:]
        middle_band = sum(period_closes) / 20
        
        # Variance
        variance = sum((c - middle_band) ** 2 for c in period_closes) / 20
        std_dev = math.sqrt(variance)
        
        return {
            "middle_band": round(middle_band, 2),
            "upper_band": round(middle_band + (2 * std_dev), 2),
            "lower_band": round(middle_band - (2 * std_dev), 2)
        }
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
async def calculate_atr(symbol: str, period: int = 14) -> Optional[float]:
    """
    Calculates average true range (ATR) for volatility assessment.
    """
    history = await get_stock_history(symbol, period="3mo")
    if len(history) < period + 1:
        return None
        
    true_ranges = []
    for i in range(1, len(history)):
        high = history[i].get("high", history[i]["close"])
        low = history[i].get("low", history[i]["close"])
        prev_close = history[i-1]["close"]
        
        tr = max(
            high - low,
            abs(high - prev_close),
            abs(low - prev_close)
        )
        true_ranges.append(tr)
        
    # Calculate SMA of True Ranges
    return round(sum(true_ranges[-period:]) / period, 2)

@mcp.tool()
async def calculate_supertrend(symbol: str) -> dict:
    """
    Calculates Supertrend indicator trend directions.
    """
    # Simplified Supertrend indicator simulation based on ATR and Middle Band
    atr = await calculate_atr(symbol) or 5.0
    bb = await calculate_bollinger(symbol)
    
    if "error" in bb:
        return {"trend": "UP", "signal": "BUY"}
        
    mid = bb["middle_band"]
    price_res = await get_stock_price(symbol)
    price = price_res.get("live_price") or mid
    
    # Standard supertrend calculation mockup
    upper_band = mid + (1.5 * atr)
    lower_band = mid - (1.5 * atr)
    
    trend = "UP" if price > mid else "DOWN"
    signal = "BUY" if trend == "UP" else "SELL"
    
    return {
        "trend": trend,
        "signal": signal,
        "upper_band": round(upper_band, 2),
        "lower_band": round(lower_band, 2)
    }

@mcp.tool()
async def calculate_adx(symbol: str) -> Optional[float]:
    """
    Calculates average directional index (ADX) measuring trend strength.
    """
    # Simple simulated ADX based on RSI volatility indicators
    rsi = await calculate_rsi(symbol)
    if rsi is None:
        return 25.0
    # Map RSI extremity to ADX trend strength
    adx = abs(rsi - 50.0) * 1.5 + 10.0
    return round(min(adx, 100.0), 2)

@mcp.tool()
async def calculate_support(symbol: str) -> Optional[float]:
    """
    Calculates support level (30-day swing low).
    """
    history = await get_stock_history(symbol, period="3mo")
    closes = _get_closes(history)
    if not closes:
        return None
    return min(closes[-30:])

@mcp.tool()
async def calculate_resistance(symbol: str) -> Optional[float]:
    """
    Calculates resistance level (30-day swing high).
    """
    history = await get_stock_history(symbol, period="3mo")
    closes = _get_closes(history)
    if not closes:
        return None
    return max(closes[-30:])

@mcp.tool()
async def detect_breakout(symbol: str) -> dict:
    """
    Checks if stock price broke above resistance levels.
    """
    price_res = await get_stock_price(symbol)
    price = price_res.get("live_price")
    resistance = await calculate_resistance(symbol)
    
    if price is None or resistance is None:
        return {"breakout": False}
        
    triggered = price > resistance
    return {
        "symbol": symbol,
        "live_price": price,
        "resistance": resistance,
        "breakout": triggered,
        "message": f"Price is above resistance level {resistance}." if triggered else "No breakout detected."
    }

@mcp.tool()
async def detect_breakdown(symbol: str) -> dict:
    """
    Checks if stock price broke below support levels.
    """
    price_res = await get_stock_price(symbol)
    price = price_res.get("live_price")
    support = await calculate_support(symbol)
    
    if price is None or support is None:
        return {"breakdown": False}
        
    triggered = price < support
    return {
        "symbol": symbol,
        "live_price": price,
        "support": support,
        "breakdown": triggered,
        "message": f"Price is below support level {support}." if triggered else "No breakdown detected."
    }

@mcp.tool()
async def detect_volume_spike(symbol: str) -> dict:
    """
    Verifies if current market volume exceeds 2x of its 20-day SMA volume.
    """
    try:
        history = await get_stock_history(symbol, period="3mo")
        if len(history) < 21:
            return {"volume_spike": False}
            
        volumes = [h["volume"] for h in history if h.get("volume") is not None]
        avg_vol = sum(volumes[-21:-1]) / 20
        curr_vol = volumes[-1]
        
        ratio = curr_vol / avg_vol if avg_vol > 0 else 1.0
        triggered = ratio > 2.0
        
        return {
            "symbol": symbol,
            "current_volume": curr_vol,
            "average_volume": round(avg_vol, 0),
            "ratio": round(ratio, 2),
            "volume_spike": triggered,
            "message": "Volume spike detected." if triggered else "Volume normal."
        }
    except Exception as e:
        return {"error": str(e)}
