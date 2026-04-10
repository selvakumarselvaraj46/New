# =============================================
# 🌍 WORLD FINANCE AI DASHBOARD (PRO VERSION)
# =============================================

import os
import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import requests
from dotenv import load_dotenv
import plotly.graph_objects as go
from datetime import datetime

# =============================================
# PAGE CONFIG
# =============================================
st.set_page_config(
    page_title="🌍 Finance AI PRO",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================
# LOAD ENV
# =============================================
load_dotenv()
NEWS_KEY = os.getenv("NEWS_API_KEY")

# =============================================
# SESSION STATE
# =============================================
if "portfolio" not in st.session_state:
    st.session_state.portfolio = {}
if "selected_tickers" not in st.session_state:
    st.session_state.selected_tickers = ["AAPL", "MSFT", "TSLA"]

# =============================================
# CONSTANTS
# =============================================
TICKERS = ["AAPL", "MSFT", "TSLA", "NVDA", "RELIANCE.NS", "TCS.NS", "BTC-USD", "ETH-USD"]
CACHE_TTL = 300

# =============================================
# INDICATORS
# =============================================
def calculate_RSI(data, window=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_MACD(data):
    ema_fast = data.ewm(span=12).mean()
    ema_slow = data.ewm(span=26).mean()
    macd = ema_fast - ema_slow
    signal = macd.ewm(span=9).mean()
    hist = macd - signal
    return macd, signal, hist

def calculate_BB(data):
    sma = data.rolling(20).mean()
    std = data.rolling(20).std()
    return sma + 2*std, sma, sma - 2*std

# =============================================
# DATA LOADER
# =============================================
@st.cache_data(ttl=CACHE_TTL)
def load_data(symbol, period):
    df = yf.download(symbol, period=period, progress=False)

    if df.empty:
        return None

    df = df[["Open","High","Low","Close","Volume"]]

    close = df["Close"]
    df["MA20"] = close.rolling(20).mean()
    df["MA50"] = close.rolling(50).mean()
    df["RSI"] = calculate_RSI(close)
    df["MACD"], df["Signal"], df["Histogram"] = calculate_MACD(close)
    df["Upper_BB"], df["SMA_BB"], df["Lower_BB"] = calculate_BB(close)

    return df

# =============================================
# SIDEBAR
# =============================================
st.sidebar.title("⚙️ Settings")

selected_tickers = st.sidebar.multiselect(
    "Select Assets",
    TICKERS,
    default=st.session_state.selected_tickers
)

period = st.sidebar.selectbox("Time Period", ["1mo","3mo","6mo","1y"], index=2)

st.session_state.selected_tickers = selected_tickers

# =============================================
# LOAD DATA
# =============================================
data = {}
with st.spinner("Loading data..."):
    for t in selected_tickers:
        df = load_data(t, period)
        if df is not None:
            data[t] = df

if not data:
    st.error("No data found")
    st.stop()

# =============================================
# HEADER
# =============================================
st.title("🌍 Finance AI Dashboard PRO")

# =============================================
# KPI CARDS (FIXED)
# =============================================
st.subheader("📊 Market Overview")

cols = st.columns(len(data))

for col, (ticker, df) in zip(cols, data.items()):
    with col:
        # ✅ FORCE SCALAR VALUES
        price = float(df["Close"].iloc[-1])
        prev = float(df["Close"].iloc[-2])

        pct = ((price - prev) / prev) * 100

        # ✅ SAFE CONDITION
        delta_color = "normal" if pct >= 0 else "inverse"

        col.metric(
            ticker,
            f"${price:.2f}",
            f"{pct:+.2f}%",
            delta_color=delta_color
        )

# =============================================
# SIMPLE CHART
# =============================================
st.subheader("📈 Price Chart")

ticker = st.selectbox("Select Ticker", list(data.keys()))
df = data[ticker]

fig = go.Figure()
fig.add_trace(go.Scatter(x=df.index, y=df["Close"], name="Price"))
fig.add_trace(go.Scatter(x=df.index, y=df["MA20"], name="MA20"))
fig.add_trace(go.Scatter(x=df.index, y=df["MA50"], name="MA50"))

fig.update_layout(template="plotly_dark")

st.plotly_chart(fig, use_container_width=True)

# =============================================
# NEWS
# =============================================
st.subheader("📰 News")

if NEWS_KEY:
    try:
        res = requests.get(
            f"https://newsapi.org/v2/top-headlines?category=business&apiKey={NEWS_KEY}"
        )
        news = res.json()

        for a in news.get("articles", [])[:5]:
            st.markdown(f"**{a['title']}**")
            st.caption(a.get("description",""))
            st.divider()

    except:
        st.error("News API error")
else:
    st.info("Add NEWS_API_KEY in .env")

# =============================================
# FOOTER
# =============================================
st.markdown("---")
st.markdown("🚀 Finance AI Dashboard PRO")
