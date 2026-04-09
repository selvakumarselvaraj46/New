# =============================
# WORLD FINANCE + AI STREAMLIT
# =============================

import os
import streamlit as st
import pandas as pd
import numpy as np

# ✅ SAFE IMPORT (prevents crash)
try:
    import yfinance as yf
except:
    st.error("❌ yfinance not installed. Add it to requirements.txt")
    st.stop()

import requests
from dotenv import load_dotenv
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from streamlit_autorefresh import st_autorefresh

# -----------------------------
# LOAD ENV KEYS
# -----------------------------
load_dotenv()
NEWS_KEY = os.getenv("NEWS_API_KEY")

# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(
    page_title="🌍 World Finance AI Dashboard",
    page_icon="📊",
    layout="wide"
)

# -----------------------------
# AUTO REFRESH
# -----------------------------
refresh = st.sidebar.slider("Auto Refresh (secs)", 30, 900, 120)
st_autorefresh(interval=refresh * 1000)

# -----------------------------
# MARKET LISTS
# -----------------------------
US_STOCKS = ["AAPL","MSFT","TSLA","NVDA","GOOGL"]
INDIAN_STOCKS = ["RELIANCE.NS","TCS.NS","INFY.NS","HDFCBANK.NS"]
CRYPTO = ["BTC-USD","ETH-USD","SOL-USD","DOGE-USD"]
INDICES = ["^GSPC","^IXIC","^FTSE","^N225"]
FOREX = ["EURUSD=X","USDINR=X","GBPUSD=X"]

# -----------------------------
# SIDEBAR
# -----------------------------
st.sidebar.title("⚙️ Dashboard Settings")

market = st.sidebar.radio(
    "Select Market Segment",
    ["US Stocks","Indian Stocks","Crypto","Indices","Forex","Mixed"]
)

if market == "US Stocks":
    tickers = st.sidebar.multiselect("Select Tickers",US_STOCKS,default=US_STOCKS[:2])
elif market == "Indian Stocks":
    tickers = st.sidebar.multiselect("Select Tickers",INDIAN_STOCKS,default=INDIAN_STOCKS[:2])
elif market == "Crypto":
    tickers = st.sidebar.multiselect("Select Cryptos",CRYPTO,default=CRYPTO[:2])
elif market == "Indices":
    tickers = st.sidebar.multiselect("Select Indices",INDICES,default=INDICES[:2])
elif market == "Forex":
    tickers = st.sidebar.multiselect("Select Forex",FOREX,default=FOREX[:2])
else:
    tickers = st.sidebar.multiselect(
        "Mixed",
        US_STOCKS+INDIAN_STOCKS+CRYPTO+INDICES+FOREX,
        default=["AAPL","RELIANCE.NS","BTC-USD"]
    )

custom = st.sidebar.text_input("Add Custom Symbol")
if custom:
    tickers.append(custom.upper())

period = st.sidebar.selectbox("Period",["1mo","3mo","6mo","1y","2y","5y"])

# -----------------------------
# TECH INDICATORS
# -----------------------------
def RSI(data,window=14):
    delta=data.diff()
    gain=(delta.where(delta>0,0)).rolling(window).mean()
    loss=(-delta.where(delta<0,0)).rolling(window).mean()
    rs=gain/loss
    return 100-(100/(1+rs))

def MACD(data):
    exp1=data.ewm(span=12).mean()
    exp2=data.ewm(span=26).mean()
    macd=exp1-exp2
    signal=macd.ewm(span=9).mean()
    return macd,signal

# -----------------------------
# DATA LOADING
# -----------------------------
@st.cache_data(ttl=600)
def load_data(symbol):
    try:
        df = yf.download(symbol, period=period, interval="1d", auto_adjust=True, progress=False)
    except:
        return pd.DataFrame()

    if df.empty:
        return df

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    close = df["Close"].astype(float)

    df["MA20"] = close.rolling(20).mean()
    df["MA50"] = close.rolling(50).mean()
    df["RSI"] = RSI(close)

    macd, signal = MACD(close)
    df["MACD"] = macd
    df["Signal"] = signal

    std = close.rolling(20).std()
    df["Upper"] = df["MA20"] + 2 * std
    df["Lower"] = df["MA20"] - 2 * std

    return df

# -----------------------------
# LOAD DATA
# -----------------------------
data = {}
for t in tickers:
    df = load_data(t)
    if not df.empty:
        data[t] = df

if not data:
    st.error("⚠️ No valid data found — check ticker or internet.")
    st.stop()

# -----------------------------
# TITLE + KPI
# -----------------------------
st.title("🌍 World Finance AI Dashboard")

cols = st.columns(len(data))
for col,(ticker,df) in zip(cols,data.items()):
    price = df["Close"].iloc[-1]
    prev = df["Close"].iloc[-2]
    pct = (price-prev)/prev*100
    col.metric(ticker,f"{price:.2f}",f"{pct:.2f}%")

# -----------------------------
# AI SIGNALS
# -----------------------------
st.subheader("🤖 AI Signals")

signals = []
for ticker,df in data.items():
    rsi = df["RSI"].iloc[-1]
    macd = df["MACD"].iloc[-1]
    signal = df["Signal"].iloc[-1]

    if rsi < 30 and macd > signal:
        rec = "BUY"
    elif rsi > 70 and macd < signal:
        rec = "SELL"
    else:
        rec = "HOLD"

    signals.append({"Ticker":ticker,"RSI":round(rsi,2),"Recommendation":rec})

st.dataframe(pd.DataFrame(signals),use_container_width=True)

# -----------------------------
# CHART
# -----------------------------
focus = st.selectbox("Select Chart",list(data.keys()))
df = data[focus]

fig = make_subplots(rows=4,cols=1,shared_xaxes=True)

fig.add_trace(go.Candlestick(x=df.index,open=df["Open"],high=df["High"],
                             low=df["Low"],close=df["Close"]),row=1,col=1)

fig.add_trace(go.Scatter(x=df.index,y=df["MA20"],name="MA20"),row=1,col=1)
fig.add_trace(go.Scatter(x=df.index,y=df["MA50"],name="MA50"),row=1,col=1)

fig.add_trace(go.Bar(x=df.index,y=df["Volume"],name="Volume"),row=2,col=1)
fig.add_trace(go.Scatter(x=df.index,y=df["RSI"],name="RSI"),row=3,col=1)

fig.add_trace(go.Scatter(x=df.index,y=df["MACD"],name="MACD"),row=4,col=1)
fig.add_trace(go.Scatter(x=df.index,y=df["Signal"],name="Signal"),row=4,col=1)

fig.update_layout(height=900,xaxis_rangeslider_visible=False)
st.plotly_chart(fig,use_container_width=True)

# -----------------------------
# NEWS
# -----------------------------
st.subheader("📰 Finance News")

if NEWS_KEY:
    try:
        r = requests.get(
            f"https://newsapi.org/v2/top-headlines?category=business&language=en&pageSize=5&apiKey={NEWS_KEY}"
        ).json()

        for n in r.get("articles",[]):
            st.markdown(f"**{n['title']}**")
            st.markdown(f"[Read more]({n['url']})")
            st.markdown("---")
    except:
        st.warning("News failed to load")
else:
    st.info("Add NEWS_API_KEY in .env")

st.success("✅ Dashboard Running Successfully")
