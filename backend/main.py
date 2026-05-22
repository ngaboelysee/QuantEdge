from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf
import numpy as np

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
# PAIRS MAP & SPECIFICATIONS
# =========================
# Added asset specifications to prevent catastrophic sizing errors
PAIRS_CONFIG = {
    "EURUSD": {"symbol": "EURUSD=X", "is_jpy": False, "is_gold": False},
    "GBPUSD": {"symbol": "GBPUSD=X", "is_jpy": False, "is_gold": False},
    "USDJPY": {"symbol": "USDJPY=X", "is_jpy": True,  "is_gold": False},
    "USDCHF": {"symbol": "USDCHF=X", "is_jpy": False, "is_gold": False},
    "USDCAD": {"symbol": "USDCAD=X", "is_jpy": False, "is_gold": False},
    "AUDUSD": {"symbol": "AUDUSD=X", "is_jpy": False, "is_gold": False},
    "NZDUSD": {"symbol": "NZDUSD=X", "is_jpy": False, "is_gold": False},
    "XAUUSD": {"symbol": "GC=F",     "is_jpy": False, "is_gold": True}
}

# =========================
# DATA FETCHING (OPTIMIZED)
# =========================
def get_data(pair, interval="1h", period="7d"):
    config = PAIRS_CONFIG.get(pair)
    if not config:
        return None

    try:
        # yf.download is faster and handles connection sessions more efficiently than Ticker().history()
        df = yf.download(tickers=config["symbol"], period=period, interval=interval, progress=False)

        if df is None or df.empty or len(df) < 20:
            return None

        return df.dropna()
    except:
        return None


# =========================
# INDICATORS (SPEED OPTIMIZED)
# =========================
def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()


def rsi(series, period=14):
    delta = series.diff()
    # Fast vectorized rolling lookups instead of filtering masks
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

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
# SENTIMENT ENGINE
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

    # Tweaked bounds slightly to accurately capture overbought/oversold momentum regimes
    if r.iloc[-1] < 40:
        score += 1
    elif r.iloc[-1] > 60:
        score -= 1

    return score


# =========================
# DYNAMIC RISK ENGINE
# =========================
def risk_engine(balance, risk, pair, current_price):
    risk_amount = balance * (risk / 100)
    config = PAIRS_CONFIG.get(pair, {"is_jpy": False, "is_gold": False})

    # Standardize stops dynamically based on what asset is trading
    if config["is_gold"]:
        stop_loss_distance = 5.0  # $5.00 move on Gold
        # Lot calculation for standard Gold contract size (100 oz)
        lot_size = risk_amount / (stop_loss_distance * 100) 
        stop_display = 500  # Displaying as ticks/points
    else:
        pip_size = 0.01 if config["is_jpy"] else 0.0001
        stop_loss_pips = 50
        stop_loss_distance = stop_loss_pips * pip_size
        
        # Standard FX lot size calculation (100,000 units of base currency)
        # Risk = Lot Size * Units * Pip Distance
        lot_size = risk_amount / (stop_loss_distance * 100000) if current_price > 0 else 0.01
        stop_display = stop_loss_pips

    return {
        "risk_amount": round(risk_amount, 2),
        "lot_size": max(0.01, round(lot_size, 2)), # Prevent 0.0 lots on small balances
        "stop_loss_pips": stop_display,
        "take_profit_pips": stop_display * 2
    }


# =========================
# VECTORIZED MONTE CARLO (BLAZING FAST)
# =========================
def monte_carlo(balance, confidence, vol_regime):
    simulations = 500  # Upgraded simulation scale safely
    horizons = 15
    
    noise = 0.005 if vol_regime == "LOW_VOL" else 0.012 if vol_regime == "NORMAL" else 0.025
    prob_win = confidence / 100.0

    # Draw all coin flips instantly using uniform distributions across the matrix space
    draws = np.random.uniform(0, 1, size=(simulations, horizons))
    multipliers = np.where(draws < prob_win, 1 + noise, 1 - noise)
    
    # Take the compounding product across every row path
    final_returns = balance * np.prod(multipliers, axis=1)

    return {
        "expected": round(float(np.mean(final_returns)), 2),
        "best": round(float(np.max(final_returns)), 2),
        "worst": round(float(np.min(final_returns)), 2)
    }


# =========================
# MAIN ENDPOINT
# =========================
@app.get("/trade")
def trade(pair: str, balance: float, risk: float):
    pair = pair.upper()
    df = get_data(pair)

    if df is None:
        return {
            "pair": pair,
            "error": "No market data available",
            "signal": {"direction": "HOLD", "confidence": 50, "score": 0}
        }

    price = float(df["Close"].iloc[-1])

    trend_score = multi_timeframe_score(df)
    vol = volatility(df)
    news = sentiment_engine(df)

    # Composite signal framework
    score = (trend_score * 2.0) + (news["bias"] * 1.5)

    if vol["regime"] == "HIGH_VOL":
        score *= 0.7
    elif vol["regime"] == "LOW_VOL":
        score *= 1.1

    buy_prob = 50 + score * 12
    buy_prob = max(5, min(95, buy_prob))
    sell_prob = 100 - buy_prob

    if buy_prob > 65:
        direction = "BUY"
    elif buy_prob < 35:
        direction = "SELL"
    else:
        direction = "HOLD"

    confidence = round(max(buy_prob, sell_prob), 2)

    # Upgraded engines passed down contextually
    risk_data = risk_engine(balance, risk, pair, price)
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
