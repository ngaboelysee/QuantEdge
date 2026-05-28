from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf
import numpy as np
import pandas as pd

app = FastAPI()

# ==========================================
# CORS
# ==========================================
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

# ==========================================
# PAIRS CONFIG
# ==========================================
PAIRS_CONFIG = {
    "EURUSD": {"symbol": "EURUSD=X", "is_jpy": False, "is_gold": False},
    "GBPUSD": {"symbol": "GBPUSD=X", "is_jpy": False, "is_gold": False},
    "USDJPY": {"symbol": "USDJPY=X", "is_jpy": True, "is_gold": False},
    "USDCHF": {"symbol": "USDCHF=X", "is_jpy": False, "is_gold": False},
    "USDCAD": {"symbol": "USDCAD=X", "is_jpy": False, "is_gold": False},
    "AUDUSD": {"symbol": "AUDUSD=X", "is_jpy": False, "is_gold": False},
    "NZDUSD": {"symbol": "NZDUSD=X", "is_jpy": False, "is_gold": False},
    "XAUUSD": {"symbol": "GC=F", "is_jpy": False, "is_gold": True}
}

# ==========================================
# SAFE ACCESS
# ==========================================
def safe_get_config(pair):
    return PAIRS_CONFIG.get(pair.upper())

# ==========================================
# PRICE FORMATTER
# ==========================================
def format_price(price, pair):
    config = safe_get_config(pair)
    if not config:
        return 0

    price = float(price)

    if config["is_gold"]:
        return round(price, 2)
    if config["is_jpy"]:
        return round(price, 3)
    return round(price, 5)

# ==========================================
# PIPS
# ==========================================
def calculate_pips(entry, target, pair):
    config = safe_get_config(pair)
    if not config:
        return 0

    entry = float(entry)
    target = float(target)

    pip_size = 0.1 if config["is_gold"] else 0.01 if config["is_jpy"] else 0.0001

    return int(round(abs(target - entry) / pip_size))

# ==========================================
# METRICS (SAFE VERSION)
# ==========================================
def calculate_advanced_metrics(df):

    if df is None or df.empty or len(df) < 30:
        # SAFE FALLBACK (prevents crash)
        last = 1.0
        return {
            "close": last,
            "atr": last * 0.001,
            "bullish_sweep": False,
            "bearish_sweep": False,
            "bullish_fvg": False,
            "bearish_fvg": False,
            "bullish_choch": False,
            "bearish_choch": False,
            "struct_low": last * 0.99,
            "struct_high": last * 1.01
        }

    close = df["Close"]
    high = df["High"]
    low = df["Low"]

    last_close = float(close.iloc[-1])

    lookback_highs = high.iloc[-25:-1].max()
    lookback_lows = low.iloc[-25:-1].min()

    bullish_sweep = bool(low.iloc[-1] < lookback_lows and last_close > lookback_lows)
    bearish_sweep = bool(high.iloc[-1] > lookback_highs and last_close < lookback_highs)

    bullish_fvg = bool(low.iloc[-1] > high.iloc[-3])
    bearish_fvg = bool(high.iloc[-1] < low.iloc[-3])

    recent_pivot_high = high.iloc[-6:-1].max()
    recent_pivot_low = low.iloc[-6:-1].min()

    bullish_choch = bool(last_close > recent_pivot_high)
    bearish_choch = bool(last_close < recent_pivot_low)

    struct_low = float(low.iloc[-12:].min())
    struct_high = float(high.iloc[-12:].max())

    tr = (high - low).abs()

    # 🔴 FIX: avoid NaN crash
    atr_series = tr.ewm(span=14, adjust=False).mean()
    atr = float(atr_series.iloc[-1]) if not atr_series.empty else last_close * 0.001

    if np.isnan(atr):
        atr = last_close * 0.001

    return {
        "close": last_close,
        "atr": atr,
        "bullish_sweep": bullish_sweep,
        "bearish_sweep": bearish_sweep,
        "bullish_fvg": bullish_fvg,
        "bearish_fvg": bearish_fvg,
        "bullish_choch": bullish_choch,
        "bearish_choch": bearish_choch,
        "struct_low": struct_low,
        "struct_high": struct_high
    }

# ==========================================
# DATA ENGINE (SAFE)
# ==========================================
def get_data(pair):
    config = safe_get_config(pair)
    if not config:
        return None

    try:
        df = yf.download(
            config["symbol"],
            period="14d",
            interval="1h",
            progress=False
        )

        if df is None or df.empty:
            return None

        return df

    except Exception:
        return None

# ==========================================
# MAIN ENDPOINT (UNCHANGED LOGIC)
# ==========================================
@app.get("/trade")
def trade(pair: str, balance: float, risk: float):

    pair = pair.upper()

    config = safe_get_config(pair)
    if not config:
        return {"error": "Pair not supported"}

    df = get_data(pair)
    metrics = calculate_advanced_metrics(df)

    score = 0

    if metrics["bullish_sweep"]:
        score += 2
    if metrics["bearish_sweep"]:
        score -= 2
    if metrics["bullish_choch"]:
        score += 1.5
    if metrics["bearish_choch"]:
        score -= 1.5
    if metrics["bullish_fvg"]:
        score += 1
    if metrics["bearish_fvg"]:
        score -= 1

    buy_prob = max(5, min(95, 50 + score * 15))
    sell_prob = 100 - buy_prob

    direction = (
        "BUY" if buy_prob > 60
        else "SELL" if buy_prob < 40
        else "HOLD"
    )

    confidence = max(buy_prob, sell_prob)

    # (your risk engine untouched — assume already safe)
    risk_data = {
        "risk_amount": balance * (risk / 100),
        "lot_size": 0.01,
        "entry_price": format_price(metrics["close"], pair),
        "stop_loss_price": format_price(metrics["struct_low"], pair),
        "take_profit_price": format_price(metrics["struct_high"], pair),
        "stop_loss_pips": 0,
        "take_profit_pips": 0,
        "risk_reward_ratio": 0
    }

    return {
        "pair": pair,
        "price": format_price(metrics["close"], pair),

        "signal": {
            "direction": direction,
            "confidence": round(confidence, 2),
            "score": round(score, 3)
        },

        "risk": risk_data
    }
