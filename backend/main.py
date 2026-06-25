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
CACHE_DURATION_SECONDS = 10  # Reduced cache duration for high-frequency short wins

def fetch_data_safe(symbol, period, interval, is_gold=False):
    try:
        if is_gold:
            ticker_obj = yf.Ticker(symbol, session=session)
            df = ticker_obj.history(period=period, interval=interval, raise_errors=False)
        else:
            df = yf.download(tickers=symbol, period=period, interval=interval, session=session, progress=False, multi_level_index=False)
            
        if df is not None and not df.empty and len(df) >= 20:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df.columns = [str(col).strip().capitalize() for col in df.columns]
            return df.dropna()
    except Exception:
        pass
    return None

def get_scalping_data(pair):
    config = PAIRS_CONFIG.get(pair)
    if not config:
        return None, None
        
    current_time = time.time()
    if pair in MARKET_CACHE:
        cache = MARKET_CACHE[pair]
        if current_time - cache["timestamp"] < CACHE_DURATION_SECONDS:
            return cache["df_15m"], cache["df_anchor"]
            
    # SCALPING ORIENTATION: 15-Minute Entry Chart paired with 1-Hour Trend Anchor
    df_15m = fetch_data_safe(config["symbol"], "5d", "15m", config["is_gold"])
    df_anchor = fetch_data_safe(config["symbol"], "14d", "1h", config["is_gold"])
    
    if df_15m is not None and not df_15m.empty:
        MARKET_CACHE[pair] = {
            "timestamp": current_time,
            "df_15m": df_15m,
            "df_anchor": df_anchor
        }
    return df_15m, df_anchor

def analyze_anchor_trend(df_anchor):
    if df_anchor is None or df_anchor.empty or len(df_anchor) < 15:
        return "NEUTRAL"
        
    close_m = df_anchor["Close"]
    ema_fast = close_m.ewm(span=9, adjust=False).mean().iloc[-1]
    ema_slow = close_m.ewm(span=21, adjust=False).mean().iloc[-1]
    
    if ema_fast > ema_slow:
        return "BULLISH"
    elif ema_fast < ema_slow:
        return "BEARISH"
    return "NEUTRAL"

def calculate_scalping_metrics(df_15m, anchor_trend):
    close = df_15m["Close"]
    high = df_15m["High"]
    low = df_15m["Low"]
    last_close = float(close.iloc[-1])
    
    # Fast ATR for quick scalping targets
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = float(tr.ewm(span=10, adjust=False).mean().iloc[-1])
    atr_cleansed = atr if atr > 0 else last_close * 0.0008

    # Highly responsive short-term liquidity sweeps (10-bar lookback)
    lookback_high = high.iloc[-10:-1].max()
    lookback_low = low.iloc[-10:-1].min()
    
    minor_bullish_sweep = bool((low.iloc[-1] < lookback_low) and (last_close > lookback_low))
    minor_bearish_sweep = bool((high.iloc[-1] > lookback_high) and (last_close < lookback_high))
    
    # Momentum breakouts
    fast_ema = close.ewm(span=7, adjust=False).mean()
    momentum_up = bool(last_close > fast_ema.iloc[-1] and close.iloc[-2] <= fast_ema.iloc[-2])
    momentum_down = bool(last_close < fast_ema.iloc[-1] and close.iloc[-2] >= fast_ema.iloc[-2])
    
    struct_low = float(low.iloc[-8:].min())
    struct_high = float(high.iloc[-8:].max())
    
    return {
        "close": last_close,
        "atr": atr_cleansed,
        "bullish_sweep": minor_bullish_sweep,
        "bearish_sweep": minor_bearish_sweep,
        "momentum_up": momentum_up,
        "momentum_down": momentum_down,
        "struct_low": struct_low,
        "struct_high": struct_high,
        "anchor_trend": anchor_trend
    }

def risk_engine_scalper(balance, risk_pct, metrics, pair, config, direction, rr_multiplier):
    current_price = metrics["close"]
    precision = config["precision"]
    
    # Scalping Risk allocation is fixed and steady since setups pass quickly
    risk_capital = float(balance) * (float(risk_pct) / 100.0)
    
    # Ultra tight stop losses (1.1x ATR or structural extreme)
    if direction == "BUY":
        sl_distance = max(current_price - metrics["struct_low"], metrics["atr"] * 1.1)
    elif direction == "SELL":
        sl_distance = max(metrics["struct_high"] - current_price, metrics["atr"] * 1.1)
    else:
        sl_distance = metrics["atr"] * 1.5

    if config["is_gold"]:
        lot_size = risk_capital / (sl_distance * 100.0)
        pips_factor = 10.0
    elif config["is_jpy"]:
        lot_size = risk_capital / (sl_distance * 100.0)
        pips_factor = 100.0
    else:
        lot_size = risk_capital / (sl_distance * 100000.0)
        pips_factor = 10000.0

    sl_pips = max(5.0, round(sl_distance * pips_factor, 1)) # Smaller minimum floor for tight trades
    tp_pips = round(sl_pips * float(rr_multiplier), 1) 

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
        "sl_pips": float(sl_pips),
        "tp_pips": float(tp_pips),
        "active_rr_ratio": float(rr_multiplier)
    }

@app.get("/trade")
def trade(pair: str, balance: float, risk: float):
    pair = pair.upper()
    config = PAIRS_CONFIG.get(pair)
    
    if not config:
        return {"error": f"Pair {pair} is missing configuration details."}

    df_15m, df_anchor = get_scalping_data(pair)
    if df_15m is None or df_15m.empty:
        return {
            "pair": pair,
            "error": "Data stream connectivity issues.",
            "signal": {"direction": "HOLD", "confidence": 50.0, "score": 0.0}
        }

    anchor_trend = analyze_anchor_trend(df_anchor)
    metrics = calculate_scalping_metrics(df_15m, anchor_trend)
    
    # Highly responsive scoring system tuned for high volume entries
    score = 0.0
    if metrics["bullish_sweep"]: score += 2.0
    if metrics["bearish_sweep"]: score -= 2.0
    if metrics["momentum_up"]:    score += 1.5
    if metrics["momentum_down"]:  score -= 1.5

    # Trend filter overlay with responsive amplification
    if metrics["anchor_trend"] == "BULLISH":
        score += 1.0
    elif metrics["anchor_trend"] == "BEARISH":
        score -= 1.0

    buy_prob = max(5.0, min(95.0, 50.0 + (score * 15.0)))
    sell_prob = 100.0 - buy_prob

    # Relaxed baseline boundaries to easily pass execution signals
    if buy_prob > 58:
        direction = "BUY"
    elif buy_prob < 42:
        direction = "SELL"
    else:
        direction = "HOLD"

    confidence = round(max(buy_prob, sell_prob), 2)
    pct_vol = metrics["atr"] / metrics["close"]
    
    # SHORT WINS TARGETING: Compressed Risk-Reward ratios for fast execution turnaround
    if pct_vol < 0.004:
        regime, rr_multiplier = "LOW_VOL", 1.2
    elif pct_vol < 0.012:
        regime, rr_multiplier = "NORMAL", 1.4
    else:
        regime, rr_multiplier = "HIGH_VOL", 1.6

    risk_data = risk_engine_scalper(balance, risk, metrics, pair, config, direction, rr_multiplier)
    
    # Simulation calculation blocks
    simulations, horizons = 500, 15
    prob_win = float(confidence) / 100.0
    risk_dollar = float(risk_data["risk_amount"])
    target_mult = float(rr_multiplier)
    start_bal = float(balance)
    
    draws = np.random.uniform(0, 1, size=(simulations, horizons))
    trade_outcomes = np.where(draws < prob_win, risk_dollar * target_mult, -risk_dollar)
    
    if direction == "HOLD":
        trade_outcomes = np.zeros_like(trade_outcomes)
        
    final_returns = start_bal + np.sum(trade_outcomes, axis=1)
    
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
            "applied_target_ratio": target_mult
        },
        "news": {
            "sentiment": "BULLISH" if direction == "BUY" else "BEARISH" if direction == "SELL" else "NEUTRAL",
            "score": int(confidence),
            "bias": 1 if direction == "BUY" else -1 if direction == "SELL" else 0
        },
        "risk": risk_data,
        "simulation": mc_data,
        "final_projection": {
            "start_balance": start_bal,
            "expected_end_balance": float(mc_data["expected"])
        }
    }
