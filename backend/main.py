from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf
import numpy as np
import random

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
# PAIRS MAP
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
# DATA
# =========================
def get_data(pair, interval="1h", period="7d"):
    symbol = PAIRS.get(pair)
    if not symbol:
        return None

    try:
        df = yf.Ticker(symbol).history(period=period, interval=interval)

        if df is None or df.empty or len(df) < 20:
            return None

        return df.dropna()

    except:
        return None


# =========================
# INDICATORS
# =========================
def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()


def rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()

    rs = gain / loss
    rs = rs.replace([np.inf, -np.inf], np.nan).fillna(50)

    return 100 - (100 / (1 + rs))


# =========================
# VOLATILITY
# =========================
def volatility(df):
    returns = df["Close"].pct_change().dropna()
    vol = float(np.std(returns)) if len(returns) > 0 else 0.01

    if vol < 0.005:
        regime = "LOW_VOL"
    elif vol < 0.015:
        regime = "NORMAL"
    else:
        regime = "HIGH_VOL"

    return {"volatility": vol, "regime": regime}


# =========================
# SENTIMENT (REALISTIC MOMENTUM-BASED)
# =========================
def sentiment_engine(df):
    returns = df["Close"].pct_change().dropna()
    momentum = returns.tail(10).mean()

    if momentum > 0.0005:
        return {"sentiment": "BULLISH", "score": 70, "bias": 1}
    elif momentum < -0.0005:
        return {"sentiment": "BEARISH", "score": 30, "bias": -1}
    else:
        return {"sentiment": "NEUTRAL", "score": 50, "bias": 0}


# =========================
# MULTI-TIMEFRAME SCORE
# =========================
def multi_timeframe_score(df):
    close = df["Close"]

    r = rsi(close)
    e1 = ema(close, 9)
    e2 = ema(close, 21)

    score = 0

    if e1.iloc[-1] > e2.iloc[-1]:
        score += 1
    else:
        score -= 1

    if r.iloc[-1] < 45:
        score += 1
    elif r.iloc[-1] > 55:
        score -= 1

    return score


# =========================
# RISK ENGINE
# =========================
def risk_engine(balance, risk):
    risk_amount = balance * (risk / 100)

    stop_loss = 50
    pip_value = 10

    lot_size = risk_amount / (stop_loss * pip_value)

    return {
        "risk_amount": round(risk_amount, 2),
        "lot_size": round(lot_size, 2),
        "stop_loss_pips": stop_loss,
        "take_profit_pips": stop_loss * 2
    }


# =========================
# MONTE CARLO (VOLATILITY AWARE)
# =========================
def monte_carlo(balance, confidence, vol_regime):

    results = []

    noise = 0.01 if vol_regime == "LOW_VOL" else 0.02 if vol_regime == "NORMAL" else 0.03

    for _ in range(300):
        val = balance

        for _ in range(15):
            if random.randint(1, 100) < confidence:
                val *= (1 + noise)
            else:
                val *= (1 - noise)

        results.append(val)

    return {
        "expected": round(np.mean(results), 2),
        "best": round(max(results), 2),
        "worst": round(min(results), 2)
    }


# =========================
# MAIN ENDPOINT
# =========================
@app.get("/trade")
def trade(pair: str, balance: float, risk: float):

    df = get_data(pair)

    if df is None:
        return {
            "pair": pair,
            "error": "No market data available",
            "signal": {
                "direction": "HOLD",
                "confidence": 50,
                "score": 0
            }
        }

    price = float(df["Close"].iloc[-1])

    # =========================
    # CORE ENGINE
    # =========================
    trend_score = multi_timeframe_score(df)
    vol = volatility(df)
    news = sentiment_engine(df)

    # =========================
    # FINAL SCORE MODEL
    # =========================
    score = (
        trend_score * 2.0 +
        news["bias"] * 1.5
    )

    # volatility adjustment
    if vol["regime"] == "HIGH_VOL":
        score *= 0.7
    elif vol["regime"] == "LOW_VOL":
        score *= 1.1

    # =========================
    # PROBABILITY MODEL
    # =========================
    buy_prob = 50 + score * 12
    buy_prob = max(5, min(95, buy_prob))

    sell_prob = 100 - buy_prob

    # =========================
    # DECISION
    # =========================
    if buy_prob > 65:
        direction = "BUY"
    elif buy_prob < 35:
        direction = "SELL"
    else:
        direction = "HOLD"

    confidence = round(max(buy_prob, sell_prob), 2)

    # =========================
    # RISK + SIMULATION
    # =========================
    risk_data = risk_engine(balance, risk)
    mc = monte_carlo(balance, confidence, vol["regime"])

    return {
        "pair": pair,
        "price": price,

        "signal": {
            "direction": direction,
            "confidence": confidence,
            "score": round(score, 3),
            "buy_probability": round(buy_prob, 2),
            "sell_probability": round(sell_prob, 2)
        },

        "volatility": vol,
        "news": news,

        "risk": risk_data,
        "simulation": mc,

        "final_projection": {
            "start_balance": balance,
            "expected_end_balance": mc["expected"]
        }
    }
help me improve my trade alsgorithm without making it run slowly or adding things that need payments
