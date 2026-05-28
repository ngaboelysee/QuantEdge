from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf
import numpy as np
import pandas as pd

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
    "EURUSD": {"symbol": "EURUSD=X", "is_jpy": False, "is_gold": False},
    "GBPUSD": {"symbol": "GBPUSD=X", "is_jpy": False, "is_gold": False},
    "USDJPY": {"symbol": "USDJPY=X", "is_jpy": True, "is_gold": False},
    "USDCHF": {"symbol": "USDCHF=X", "is_jpy": False, "is_gold": False},
    "USDCAD": {"symbol": "USDCAD=X", "is_jpy": False, "is_gold": False},
    "AUDUSD": {"symbol": "AUDUSD=X", "is_jpy": False, "is_gold": False},
    "NZDUSD": {"symbol": "NZDUSD=X", "is_jpy": False, "is_gold": False},
    "XAUUSD": {"symbol": "GC=F", "is_jpy": False, "is_gold": True}
}

def safe_float(x):
    """prevents Series → float crash"""
    if isinstance(x, pd.Series):
        return float(x.iloc[-1])
    return float(x)

def format_price(price, pair):
    config = PAIRS_CONFIG[pair]
    price = safe_float(price)

    if config["is_gold"]:
        return round(price, 2)
    if config["is_jpy"]:
        return round(price, 3)
    return round(price, 5)

def calculate_pips(entry, target, pair):
    config = PAIRS_CONFIG[pair]

    entry = float(entry)
    target = float(target)

    if config["is_gold"]:
        pip_size = 0.1
    elif config["is_jpy"]:
        pip_size = 0.01
    else:
        pip_size = 0.0001

    return int(round(abs(target - entry) / pip_size))

def calculate_advanced_metrics(df):
    close = df["Close"]
    high = df["High"]
    low = df["Low"]

    last_close = float(close.iloc[-1])

    lookback_highs = float(high.iloc[-25:-1].max())
    lookback_lows = float(low.iloc[-25:-1].min())

    bullish_sweep = low.iloc[-1] < lookback_lows and last_close > lookback_lows
    bearish_sweep = high.iloc[-1] > lookback_highs and last_close < lookback_highs

    bullish_fvg = low.iloc[-1] > high.iloc[-3]
    bearish_fvg = high.iloc[-1] < low.iloc[-3]

    recent_pivot_high = float(high.iloc[-6:-1].max())
    recent_pivot_low = float(low.iloc[-6:-1].min())

    bullish_choch = last_close > recent_pivot_high
    bearish_choch = last_close < recent_pivot_low

    struct_low = float(low.iloc[-12:].min())
    struct_high = float(high.iloc[-12:].max())

    tr = (high - low).astype(float)
    atr_series = tr.ewm(span=14).mean()

    atr = float(atr_series.iloc[-1]) if len(atr_series) else float(last_close * 0.0015)

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

def get_data(pair):
    config = PAIRS_CONFIG[pair]

    df = yf.download(
        config["symbol"],
        period="14d",
        interval="1h",
        progress=False
    )

    if df is None or df.empty or len(df) < 20:
        return None

    return df

def risk_engine(balance, risk_pct, metrics, pair, config, direction):

    risk_capital = balance * (risk_pct / 100.0)
    current_price = metrics["close"]

    if direction == "BUY":
        stop_loss_price = metrics["struct_low"]
        sl_distance = current_price - stop_loss_price

    elif direction == "SELL":
        stop_loss_price = metrics["struct_high"]
        sl_distance = stop_loss_price - current_price

    else:
        sl_distance = metrics["atr"] * 2.0
        stop_loss_price = current_price - sl_distance

    sl_distance = max(sl_distance, metrics["atr"] * 0.5)
    tp_distance = sl_distance * 3.0

    take_profit_price = (
        current_price + tp_distance
        if direction == "BUY"
        else current_price - tp_distance
    )

    if config["is_gold"]:
        lot_size = risk_capital / (sl_distance * 100.0)
    elif config["is_jpy"]:
        lot_size = risk_capital / (sl_distance * 1000.0)
    else:
        lot_size = risk_capital / (sl_distance * 100000.0)

    sl_pips = calculate_pips(current_price, stop_loss_price, pair)
    tp_pips = calculate_pips(current_price, take_profit_price, pair)

    rr = round(tp_pips / sl_pips, 2) if sl_pips > 0 else 0

    return {
        "risk_amount": round(risk_capital, 2),
        "lot_size": max(0.01, round(lot_size, 2)),
        "entry_price": format_price(current_price, pair),
        "stop_loss_price": format_price(stop_loss_price, pair),
        "take_profit_price": format_price(take_profit_price, pair),
        "stop_loss_pips": sl_pips,
        "take_profit_pips": tp_pips,
        "risk_reward_ratio": rr
    }

@app.get("/trade")
def trade(pair: str, balance: float, risk: float):

    pair = pair.upper()

    if pair not in PAIRS_CONFIG:
        return {"error": "Pair not supported"}

    df = get_data(pair)

    if df is None:
        return {"error": "No data from Yahoo Finance"}

    metrics = calculate_advanced_metrics(df)

    score = 0
    if metrics["bullish_sweep"]: score += 2
    if metrics["bearish_sweep"]: score -= 2
    if metrics["bullish_choch"]: score += 1.5
    if metrics["bearish_choch"]: score -= 1.5
    if metrics["bullish_fvg"]: score += 1
    if metrics["bearish_fvg"]: score -= 1

    buy_prob = max(5, min(95, 50 + score * 15))
    sell_prob = 100 - buy_prob

    direction = (
        "BUY" if buy_prob > 60
        else "SELL" if buy_prob < 40
        else "HOLD"
    )

    confidence = max(buy_prob, sell_prob)

    risk_data = risk_engine(balance, risk, metrics, pair, PAIRS_CONFIG[pair], direction)

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
