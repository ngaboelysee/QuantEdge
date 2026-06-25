from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf
import numpy as np
import pandas as pd
import requests
import time

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://ai-quant-trade-engine.vercel.app",
        "https://myapp-hmksnzqkd-nrelysee-s-projects1.vercel.app",
        "http://localhost:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PAIRS_CONFIG = {
    "EURUSD": {"symbol": "EURUSD=X", "is_jpy": False, "is_gold": False, "precision": 5},
    "GBPUSD": {"symbol": "GBPUSD=X", "is_jpy": False, "is_gold": False, "precision": 5},
    "USDJPY": {"symbol": "USDJPY=X", "is_jpy": True,  "is_gold": False, "precision": 3},
    "USDCHF": {"symbol": "USDCHF=X", "is_jpy": False, "is_gold": False, "precision": 5},
    "USDCAD": {"symbol": "USDCAD=X", "is_jpy": False, "is_gold": False, "precision": 5},
    "AUDUSD": {"symbol": "AUDUSD=X", "is_jpy": False, "is_gold": False, "precision": 5},
    "NZDUSD": {"symbol": "NZDUSD=X", "is_jpy": False, "is_gold": False, "precision": 5},
    "XAUUSD": {"symbol": "GC=F",     "is_jpy": False, "is_gold": True,  "precision": 2}
}

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
})

MARKET_CACHE = {}
CACHE_DURATION_SECONDS = 30 

def fetch_data_safe(symbol, period, interval, is_gold=False):
    try:
        if is_gold:
            ticker_obj = yf.Ticker(symbol, session=session)
            df = ticker_obj.history(period=period, interval=interval, raise_errors=False)
        else:
            df = yf.download(tickers=symbol, period=period, interval=interval, session=session, progress=False, multi_level_index=False)
            
        if df is not None and not df.empty and len(df) >= 25:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df.columns = [str(col).strip().capitalize() for col in df.columns]
            return df.dropna()
    except Exception:
        pass
    return None

def get_dual_timeframe_data(pair):
    config = PAIRS_CONFIG.get(pair)
    if not config:
        return None, None
        
    current_time = time.time()
    if pair in MARKET_CACHE:
        cache = MARKET_CACHE[pair]
        if current_time - cache["timestamp"] < CACHE_DURATION_SECONDS:
            return cache["df_1h"], cache["df_macro"]
            
    # Fetch Execution timeframe (1-Hour) and Macro Anchor timeframe (4-Hour)
    df_1h = fetch_data_safe(config["symbol"], "14d", "1h", config["is_gold"])
    df_macro = fetch_data_safe(config["symbol"], "60d", "4h", config["is_gold"])
    
    if df_1h is not None and not df_1h.empty:
        MARKET_CACHE[pair] = {
            "timestamp": current_time,
            "df_1h": df_1h,
            "df_macro": df_macro
        }
    return df_1h, df_macro

def analyze_macro_trend(df_macro):
    """Calculates macro institutional direction using moving average matrices and structural tracking"""
    if df_macro is None or df_macro.empty or len(df_macro) < 20:
        return "NEUTRAL"
        
    close_m = df_macro["Close"]
    ema_fast = close_m.ewm(span=12, adjust=False).mean().iloc[-1]
    ema_slow = close_m.ewm(span=26, adjust=False).mean().iloc[-1]
    
    # Identify macro-pivot structural high/low direction
    macro_high = float(df_macro["High"].iloc[-15:-1].max())
    macro_low = float(df_macro["Low"].iloc[-15:-1].min())
    current_close = float(close_m.iloc[-1])
    
    if ema_fast > ema_slow and current_close > ((macro_high + macro_low) / 2):
        return "BULLISH"
    elif ema_fast < ema_slow and current_close < ((macro_high + macro_low) / 2):
        return "BEARISH"
    return "NEUTRAL"

def calculate_advanced_metrics(df_1h, macro_trend):
    close = df_1h["Close"]
    high = df_1h["High"]
    low = df_1h["Low"]
    last_close = float(close.iloc[-1])
    
    # Volatility parsing
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = float(tr.ewm(span=14, adjust=False).mean().iloc[-1])
    atr_cleansed = atr if atr > 0 else last_close * 0.0015

    # Structural levels tracking
    lookback_highs = high.iloc[-25:-1].max()
    lookback_lows = low.iloc[-25:-1].min()
    
    bullish_sweep = bool((low.iloc[-1] < lookback_lows) and (last_close > lookback_lows))
    bearish_sweep = bool((high.iloc[-1] > lookback_highs) and (last_close < lookback_highs))
    
    recent_pivot_high = high.iloc[-8:-1].max()
    recent_pivot_low = low.iloc[-8:-1].min()
    displacement_val = atr_cleansed * 0.15
    
    bullish_choch = bool(last_close > (recent_pivot_high + displacement_val) and close.iloc[-2] <= recent_pivot_high)
    bearish_choch = bool(last_close < (recent_pivot_low - displacement_val) and close.iloc[-2] >= recent_pivot_low)
    
    bullish_fvg = bool(low.iloc[-1] > high.iloc[-3] and close.iloc[-2] > high.iloc[-3])
    bearish_fvg = bool(high.iloc[-1] < low.iloc[-3] and close.iloc[-2] < low.iloc[-3])
    
    struct_low = float(low.iloc[-12:].min())
    struct_high = float(high.iloc[-12:].max())
    
    return {
        "close": last_close,
        "atr": atr_cleansed,
        "bullish_sweep": bullish_sweep,
        "bearish_sweep": bearish_sweep,
        "bullish_fvg": bullish_fvg,
        "bearish_fvg": bearish_fvg,
        "bullish_choch": bullish_choch,
        "bearish_choch": bearish_choch,
        "struct_low": struct_low,
        "struct_high": struct_high,
        "macro_trend": macro_trend
    }

def risk_engine(balance, risk_pct, metrics, pair, config, direction, rr_multiplier, confidence):
    current_price = metrics["close"]
    precision = config["precision"]
    
    confidence_scale = max(0.4, (confidence - 50.0) / 50.0)
    calibrated_risk = risk_pct * confidence_scale
    risk_capital = balance * (calibrated_risk / 100.0)
    
    if direction == "BUY":
        sl_distance = max(current_price - metrics["struct_low"], metrics["atr"] * 1.5)
    elif direction == "SELL":
        sl_distance = max(metrics["struct_high"] - current_price, metrics["atr"] * 1.5)
    else:
        sl_distance = metrics["atr"] * 2.0

    if config["is_gold"]:
        lot_size = risk_capital / (sl_distance * 100.0)
        pips_factor = 10.0
    elif config["is_jpy"]:
        lot_size = risk_capital / (sl_distance * 100.0)
        pips_factor = 100.0
    else:
        lot_size = risk_capital / (sl_distance * 100000.0)
        pips_factor = 10000.0

    sl_pips = max(15.0, round(sl_distance * pips_factor, 1))
    tp_pips = round(sl_pips * rr_multiplier, 1) 

    if direction == "BUY":
        sl_price = current_price - (sl_pips / pips_factor)
        tp_price = current_price + (tp_pips / pips_factor)
    elif direction == "SELL":
        sl_price = current_price + (sl_pips / pips_factor)
        tp_price = current_price - (tp_pips / pips_factor)
    else:
        sl_price, tp_price = current_price, current_price

    return {
        "risk_amount": round(float(risk_capital), 2),
        "lot_size": max(0.01, round(float(lot_size), 2)),
        "entry": f"{current_price:.{precision}f}",
        "stop_loss": f"{sl_price:.{precision}f}",
        "take_profit": f"{tp_price:.{precision}f}",
        "sl_pips": sl_pips,
        "tp_pips": tp_pips,
        "active_rr_ratio": rr_multiplier
    }

@app.get("/trade")
def trade(pair: str, balance: float, risk: float):
    pair = pair.upper()
    config = PAIRS_CONFIG.get(pair)
    
    if not config:
        return {"error": f"Pair {pair} is missing configuration details."}

    df_1h, df_macro = get_dual_timeframe_data(pair)
    if df_1h is None or df_1h.empty:
        return {
            "pair": pair,
            "error": "Upstream historical data arrays missing.",
            "signal": {"direction": "HOLD", "confidence": 50.0, "score": 0.0}
        }

    macro_trend = analyze_macro_trend(df_macro)
    metrics = calculate_advanced_metrics(df_1h, macro_trend)
    
    score = 0.0
    if metrics["bullish_sweep"]: score += 2.0
    if metrics["bearish_sweep"]: score -= 2.0
    if metrics["bullish_choch"]:  score += 1.5
    if metrics["bearish_choch"]:  score -= 1.5
    if metrics["bullish_fvg"]:   score += 1.0
    if metrics["bearish_fvg"]:   score -= 1.0

    # --- THE TIME-FRAME CONFLUENCE GATEKEEPER ---
    if metrics["macro_trend"] == "BULLISH":
        if score > 0:
            score += 1.5  # Reward executing setups aligned with higher-timeframe order flow
        else:
            score *= 0.2  # Crush counter-trend sell setups down to near-zero impact
    elif metrics["macro_trend"] == "BEARISH":
        if score < 0:
            score -= 1.5  # Reward execution aligned with higher-timeframe macro shorts
        else:
            score *= 0.2  # Crush counter-trend buy setups down to near-zero impact

    buy_prob = max(5.0, min(95.0, 50.0 + (score * 13.0)))
    sell_prob = 100.0 - buy_prob

    if buy_prob > 63:
        direction = "BUY"
    elif buy_prob < 37:
        direction = "SELL"
    else:
        direction = "HOLD"

    confidence = round(max(buy_prob, sell_prob), 2)
    pct_vol = metrics["atr"] / metrics["close"]
    
    if pct_vol < 0.005:
        regime, rr_multiplier = "LOW_VOL", 1.8
    elif pct_vol < 0.015:
        regime, rr_multiplier = "NORMAL", 2.5
    else:
        regime, rr_multiplier = "HIGH_VOL", 3.4

    risk_data = risk_engine(balance, risk, metrics, pair, config, direction, rr_multiplier, confidence)
    
    simulations, horizons = 500, 15
    prob_win = confidence / 100.0
    risk_dollar = risk_data["risk_amount"]
    
    draws = np.random.uniform(0, 1, size=(simulations, horizons))
    trade_outcomes = np.where(draws < prob_win, risk_dollar * rr_multiplier, -risk_dollar)
    if direction == "HOLD":
        trade_outcomes = np.zeros_like(trade_outcomes)
        
    final_returns = balance + np.sum(trade_outcomes, axis=1)
    mc_data = {
        "expected": round(float(np.mean(final_returns)), 2),
        "best": round(float(np.max(final_returns)), 2),
        "worst": round(float(np.min(final_returns)), 2)
    }

    precision = config["precision"]

    return {
        "pair": pair,
        "price": f"{float(metrics['close']):.{precision}f}",
        "signal": {
            "direction": direction,
            "confidence": float(confidence),
            "score": round(float(score), 3),
            "buy_probability": round(float(buy_prob), 2),
            "sell_probability": round(float(sell_prob), 2)
        },
        "volatility": {
            "volatility": float(pct_vol), 
            "regime": regime,
            "applied_target_ratio": rr_multiplier
        },
        "news": {
            "sentiment": "BULLISH" if direction == "BUY" else "BEARISH" if direction == "SELL" else "NEUTRAL",
            "score": int(confidence),
            "bias": 1 if direction == "BUY" else -1 if direction == "SELL" else 0
        },
        "risk": risk_data,
        "simulation": mc_data,
        "final_projection": {
            "start_balance": float(balance),
            "expected_end_balance": float(mc_data["expected"])
        }
    }
