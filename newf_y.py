# =============================================
# 🌍 WORLD FINANCE AI DASHBOARD (PRO VERSION)
# Secure + Efficient + AI Enhanced
# =============================================

import os
import time
import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import requests
from dotenv import load_dotenv
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from streamlit_autorefresh import st_autorefresh

# -----------------------------
# LOAD ENV
# -----------------------------
load_dotenv()
NEWS_KEY = os.getenv("NEWS_API_KEY")

# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(page_title="🌍 Finance AI PRO", layout="wide")

# -----------------------------
# RATE LIMIT (SECURITY)
# -----------------------------
if "last_call" in st.session_state:
    if time.time() - st.session_state.last_call < 1:
        st.warning("Too many requests. Slow down.")
        st.stop()
st.session_state.last_call = time.time()

# -----------------------------
# AUTO REFRESH
# -----------------------------
refresh = st.sidebar.slider("Refresh (sec)", 30, 600, 120)
st_autorefresh(interval=refresh * 1000)

# -----------------------------
# MARKETS
# -----------------------------
TICKERS = ["AAPL","MSFT","TSLA","NVDA","RELIANCE.NS","TCS.NS","BTC-USD","ETH-USD"]

tickers = st.sidebar.multiselect("Select Assets", TICKERS, default=TICKERS[:3])

custom = st.sidebar.text_input("Custom Symbol")
if custom:
    if custom.isalnum():
        tickers.append(custom.upper())
    else:
        st.warning("Invalid symbol")

if len(tickers) > 8:
    st.error("Max 8 tickers allowed")
    st.stop()

period = st.sidebar.selectbox("Period", ["1mo","3mo","6mo","1y"])

# -----------------------------
# INDICATORS
# -----------------------------
def RSI(data, window=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# -----------------------------
# DATA LOADER (OPTIMIZED)
# -----------------------------
@st.cache_data(ttl=300)
def load_data(symbol):
    df = yf.download(symbol, period=period, progress=False)[["Open","High","Low","Close","Volume"]]
    if df.empty:
        return df

    close = df["Close"]
    df["MA20"] = close.rolling(20).mean()
    df["MA50"] = close.rolling(50).mean()
    df["RSI"] = RSI(close)

    return df

# -----------------------------
# LOAD DATA
# -----------------------------
data = {t: load_data(t) for t in tickers if not load_data(t).empty}

if not data:
    st.error("No data")
    st.stop()

# -----------------------------
# TITLE
# -----------------------------
st.title("🌍 Finance AI Dashboard PRO")

# -----------------------------
# KPIs
# -----------------------------
cols = st.columns(len(data))
for col, (t, df) in zip(cols, data.items()):
    price = df["Close"].iloc[-1]
    prev = df["Close"].iloc[-2]
    pct = (price - prev) / prev * 100
    col.metric(t, f"{price:.2f}", f"{pct:.2f}%")

# -----------------------------
# AI SIGNALS
# -----------------------------
st.subheader("🤖 AI Signals")
signals = []
for t, df in data.items():
    rsi = df["RSI"].iloc[-1]
    price = df["Close"].iloc[-1]
    ma50 = df["MA50"].iloc[-1]

    if rsi < 30 and price > ma50:
        rec = "STRONG BUY"
        risk = "Low"
    elif rsi > 70:
        rec = "SELL"
        risk = "High"
    else:
        rec = "HOLD"
        risk = "Medium"

    signals.append({"Ticker": t, "RSI": round(rsi,2), "Signal": rec, "Risk": risk})

st.dataframe(pd.DataFrame(signals), use_container_width=True)

# -----------------------------
# CHART
# -----------------------------
focus = st.selectbox("Select Chart", list(data.keys()))
df = data[focus]

fig = make_subplots(rows=3, cols=1, shared_xaxes=True)

fig.add_trace(go.Candlestick(x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"]), row=1, col=1)
fig.add_trace(go.Scatter(x=df.index, y=df["MA20"], name="MA20"), row=1, col=1)
fig.add_trace(go.Bar(x=df.index, y=df["Volume"]), row=2, col=1)
fig.add_trace(go.Scatter(x=df.index, y=df["RSI"], name="RSI"), row=3, col=1)

fig.update_layout(height=700, xaxis_rangeslider_visible=False)
st.plotly_chart(fig, use_container_width=True)

# -----------------------------
# PORTFOLIO
# -----------------------------
st.subheader("💼 Portfolio")
portfolio = []

for t, df in data.items():
    qty = st.number_input(f"{t} Qty", value=0, key=t)
    buy = st.number_input(f"{t} Buy Price", value=0.0, key=t+"b")
    price = df["Close"].iloc[-1]

    pnl = (price - buy) * qty
    portfolio.append({"Ticker": t, "Value": price*qty, "PnL": pnl})

pdf = pd.DataFrame(portfolio)
st.metric("Total Value", round(pdf["Value"].sum(),2))
st.metric("Total PnL", round(pdf["PnL"].sum(),2))

# -----------------------------
# RISK METRICS
# -----------------------------
returns = pd.DataFrame({t: data[t]["Close"].pct_change() for t in data})

vol = returns.std() * np.sqrt(252) * 100
sharpe = returns.mean() / returns.std()

st.write("📊 Volatility %")
st.dataframe(vol)

st.write("📊 Sharpe Ratio")
st.dataframe(sharpe)

# -----------------------------
# NEWS
# -----------------------------
st.subheader("📰 News")

if NEWS_KEY:
    try:
        r = requests.get(f"https://newsapi.org/v2/top-headlines?category=business&apiKey={NEWS_KEY}").json()
        for n in r.get("articles", [])[:5]:
            st.markdown(f"**{n['title']}**")
            st.markdown(n['description'] or "")
            st.markdown("---")
    except:
        st.warning("News error")
else:
    st.warning("Add NEWS_API_KEY")

# -----------------------------
# EXPORT
# -----------------------------
csv = pdf.to_csv().encode()
st.download_button("Download Portfolio", csv, "portfolio.csv")

st.success("🚀 PRO Dashboard Ready")
