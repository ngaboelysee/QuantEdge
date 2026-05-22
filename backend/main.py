from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf
import numpy as np
import random
import math
import time
from datetime import datetime

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

# =========================
# PAIRS
# =========================
PAIRS = {
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X",
    "USDJPY": "USDJPY=X",
    "USDCHF": "USDCHF=X",
    "USDCAD": "USDCAD=X",
    "AUDUSD": "AUDUSD=X",
    "NZDUSD": "NZDUSD=X",
    "XAUUSD": "GC=F"
}

# =========================
# TRADE JOURNAL
# =========================
TRADE_JOURNAL = []

# =========================
# CACHE (MAJOR SPEED BOOST)
# =========================
DATA_CACHE = {}
CACHE_TTL = 60  # seconds


# =========================
# DATA (CACHED)
# =========================
def get_data(pair, interval="1h", period="10d"):
    key = f"{pair}_{interval}_{period}"
    now = time.time()

    if key in DATA_CACHE:
        df, ts = DATA_CACHE[key]
        if now - ts < CACHE_TTL:
            return df

    symbol = PAIRS.get(pair)
    if not symbol:
        return None

    try:
        df = yf.Ticker(symbol).history(period=period, interval=interval)
        if df is None or df.empty or len(df) < 30:
            return None

        df = df.dropna()
        DATA_CACHE[key] = (df, now)
        return df

    except:
        return None


# =========================
# INDICATORS (UNCHANGED LOGIC)
# =========================
def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()


def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()

    rs = gain / loss.replace(0, np.nan)
    rs = rs.fillna(0)

    return 100 - (100 / (1 + rs))


def atr(df, period=14):
    high = df["High"]
    low = df["Low"]
    close = df["Close"]
    prev_close = close.shift(1)

    tr = np.maximum(
        high - low,
        np.maximum(abs(high - prev_close),
                   abs(low - prev_close))
    )

    return tr.rolling(period).mean().fillna(0)


# =========================
# REGIME DETECTION (UNCHANGED)
# =========================
def detect_regime(df):
    returns = df["Close"].pct_change().dropna()
    vol = returns.std()

    adx_proxy = abs(df["Close"].diff(5)).mean()

    if vol < 0.004 and adx_proxy < 0.2:
        return "LOW_VOL_RANGE"
    elif vol > 0.01:
        return "HIGH_VOL"
    else:
        return "TRENDING"


# =========================
# MOMENTUM (UNCHANGED LOGIC)
# =========================
def momentum_bias(df):
    returns = df["Close"].pct_change().dropna()
    short = returns.tail(8).mean()
    long = returns.tail(30).mean()

    bias = short - long

    if bias > 0:
        return 1
    elif bias < 0:
        return -1
    return 0


# =========================
# SCORE ENGINE (UNCHANGED)
# =========================
def compute_score(df):
    close = df["Close"]

    r = rsi(close)
    e1 = ema(close, 9)
    e2 = ema(close, 21)

    score = 0.0

    if e1.iloc[-1] > e2.iloc[-1]:
        score += 0.6
    else:
        score -= 0.6

    rsi_val = r.iloc[-1]
    if rsi_val < 40:
        score += 0.4
    elif rsi_val > 60:
        score -= 0.4

    score += momentum_bias(df) * 0.5

    return score


# =========================
# SIGMOID (UNCHANGED)
# =========================
def sigmoid(x):
    return 1 / (1 + math.exp(-x))


# =========================
# RISK ENGINE (UNCHANGED)
# =========================
def risk_engine(df, balance, risk_pct):
    a = atr(df).iloc[-1]
    price = df["Close"].iloc[-1]

    if a == 0:
        a = price * 0.01

    stop_loss = float(a * 2)
    risk_amount = balance * (risk_pct / 100)

    pip_value = 1

    lot_size = risk_amount / (stop_loss * pip_value)

    return {
        "risk_amount": round(risk_amount, 2),
        "stop_loss_dynamic": round(stop_loss, 5),
        "lot_size": round(lot_size, 4),
        "take_profit": round(stop_loss * 2, 5)
    }


# =========================
# MONTE CARLO (OPTIMIZED ONLY)
# =========================
def monte_carlo(df, balance, confidence):
    returns = df["Close"].pct_change().dropna().values

    if len(returns) < 10:
        returns = np.array([0.001, -0.001, 0.002, -0.002])

    sims = 100   # reduced from 300 (no logic change, same model)
    steps = 20

    results = np.empty(sims)

    for i in range(sims):
        val = balance
        sampled = np.random.choice(returns, size=steps, replace=True)

        for r in sampled:
            if random.random() < confidence / 100:
                val *= (1 + r)
            else:
                val *= (1 - abs(r))

        results[i] = val

    return {
        "expected": round(results.mean(), 2),
        "best": round(results.max(), 2),
        "worst": round(results.min(), 2)
    }


# =========================
# TRADE LOGGER
# =========================
def log_trade(pair, direction, confidence, score, balance):
    TRADE_JOURNAL.append({
        "time": str(datetime.utcnow()),
        "pair": pair,
        "direction": direction,
        "confidence": confidence,
        "score": score,
        "balance": balance
    })


# =========================
# MAIN ENDPOINT
# =========================
@app.get("/trade")
def trade(pair: str, balance: float, risk: float):

    df = get_data(pair)

    if df is None:
        return {
            "pair": pair,
            "error": "No data",
            "signal": {"direction": "HOLD", "confidence": 50}
        }

    price = float(df["Close"].iloc[-1])

    regime = detect_regime(df)
    score = compute_score(df)

    if regime == "HIGH_VOL":
        score *= 0.7
    elif regime == "LOW_VOL_RANGE":
        score *= 1.1

    prob = sigmoid(score * 2.2)
    confidence = round(prob * 100, 2)

    if confidence > 65:
        direction = "BUY"
    elif confidence < 35:
        direction = "SELL"
    else:
        direction = "HOLD"

    risk_data = risk_engine(df, balance, risk)
    mc = monte_carlo(df, balance, confidence)

    if direction != "HOLD":
        log_trade(pair, direction, confidence, score, balance)

    return {
        "pair": pair,
        "price": price,

        "signal": {
            "direction": direction,
            "confidence": confidence,
            "score": round(score, 4),
            "probability": round(prob, 4)
        },

        "regime": regime,
        "risk": risk_data,
        "simulation": mc,
        "journal_size": len(TRADE_JOURNAL),

        "projection": {
            "start_balance": balance,
            "expected_end_balance": mc["expected"]
        }
    }


# =========================
# JOURNAL ENDPOINT
# =========================
@app.get("/journal")
def journal():
    return {"trades": TRADE_JOURNAL}
