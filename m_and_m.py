import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import altair as alt
from datetime import datetime, timedelta

# 1. STREAMLIT PAGE CONFIG & GROWW DARK THEME
st.set_page_config(page_title="M&M Institutional Quant Terminal", layout="wide", initial_sidebar_state="expanded")

# Custom CSS for Groww Dark Theme
st.markdown("""
    <style>
        .stApp { background-color: #0b0f19; color: #e2e8f0; }
        div[data-testid="stSidebarUserContent"] { background-color: #121826; }
        .stDataFrame { background-color: #121826; border-radius: 8px; }
        h1, h2, h3 { color: #ffffff; font-family: 'Inter', sans-serif; }
        div.stButton > button:first-child { background-color: #00d09c; color: white; border: none; }
    </style>
""", unsafe_allow_html=True)

# 2. AUTO CACHE CLEAR ON NEW DEPLOYMENT
if "init_deployment_check" not in st.session_state:
    st.cache_data.clear()
    st.cache_resource.clear()
    st.session_state["init_deployment_check"] = True

st.title("📊 M and M Institutional Quant Terminal")

# 3. 70+ INTERNAL NSE STOCKS DATABASE
NSE_STOCKS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS", 
    "BHARTIARTL.NS", "SBI.NS", "LTIM.NS", "ITC.NS", "HINDUNILVR.NS",
    "LT.NS", "BAJFINANCE.NS", "HCLTECH.NS", "MARUTI.NS", "SUNPHARMA.NS",
    "TITAN.NS", "ADANIENT.NS", "TATAMOTORS.NS", "AXISBANK.NS", "NTPC.NS",
    "KOTAKBANK.NS", "ONGC.NS", "POWERGRID.NS", "ADANIPORTS.NS", "COALINDIA.NS",
    "ASIANPAINT.NS", "BAJAJFINSV.NS", "TATASTEEL.NS", "M&M.NS", "JIOFIN.NS",
    "ULTRACEMCO.NS", "GRASIM.NS", "HINDALCO.NS", "NESTLEIND.NS", "JSWSTEEL.NS",
    "TECHM.NS", "WIPRO.NS", "ADANIGREEN.NS", "ADANIPOWER.NS", "INDUSINDBK.NS",
    "BPCL.NS", "CIPLA.NS", "EICHERMOT.NS", "DRREDDY.NS", "TATACONSUM.NS",
    "BRITANNIA.NS", "SBILIFE.NS", "VBL.NS", "HAL.NS", "BEL.NS",
    "BAJAJ-AUTO.NS", "DIVISLAB.NS", "APOLLOHOSP.NS", "SHRIRAMFIN.NS", "DLF.NS",
    "HEROMOTOCO.NS", "TRENT.NS", "LICI.NS", "ZOMATO.NS", "IRFC.NS",
    "PFC.NS", "RECLTD.NS", "CHOLAFIN.NS", "HAVELLS.NS", "IOC.NS",
    "GAIL.NS", "MOTHERSON.NS", "MANAPPURAM.NS", "FEDERALBNK.NS", "IDFCFIRSTB.NS"
]

# 4. QUANT ENGINE INDICATORS (VECTORIZED)
def calculate_indicators(df):
    if len(df) < 30:
        return df
        
    # RSI 14
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / (loss + 1e-10)
    df['RSI_14'] = 100 - (100 / (1 + rs))
    
    # MACD (12, 26, 9)
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['MACD'] - df['Signal_Line']
    
    # TR / ATR 14
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    df['TR'] = ranges.max(axis=1)
    df['ATR_14'] = df['TR'].rolling(window=14).mean()
    
    # Bollinger Bands (20, 2)
    df['BB_Middle'] = df['Close'].rolling(window=20).mean()
    df['BB_Std'] = df['Close'].rolling(window=20).std()
    df['BB_Upper'] = df['BB_Middle'] + (df['BB_Std'] * 2)
    df['BB_Lower'] = df['BB_Middle'] - (df['BB_Std'] * 2)
    
    # SuperTrend Loop (10, 3)
    df['ST_Upper'] = ((df['High'] + df['Low']) / 2) + (3 * df['ATR_14'])
    df['ST_Lower'] = ((df['High'] + df['Low']) / 2) - (3 * df['ATR_14'])
    df['SuperTrend'] = df['ST_Lower'] # Placeholder for loop stability
    
    # Candlestick Pattern Alerts
    df['Bullish_Engulfing'] = (df['Close'] > df['Open']) & \
                             (df['Close'].shift(1) < df['Open'].shift(1)) & \
                             (df['Close'] >= df['Open'].shift(1)) & \
                             (df['Open'] <= df['Close'].shift(1))
                             
    df['Hammer'] = ((df['High'] - df['Low']) > 3 * (df['Open'] - df['Close']).abs()) & \
                   ((df['Close'] - df['Low']) / (.001 + df['High'] - df['Low']) > 0.6) & \
                   ((df['Open'] - df['Low']) / (.001 + df['High'] - df['Low']) > 0.6)
                   
    return df.replace([np.inf, -np.inf], np.nan).fillna(0)

# 5. DATA FETCHING (yfinance)
@st.cache_data(ttl=300)
def fetch_terminal_data():
    master_data = {}
    for stock in NSE_STOCKS:
        try:
            ticker = yf.Ticker(stock)
            df = ticker.history(period="3mo", interval="1d")
            if not df.empty:
                master_data[stock] = calculate_indicators(df)
        except Exception:
            continue
    return master_data

data_load_state = st.info("🔄 Institutional Data Grid ಪ್ರೊಸೆಸ್ ಆಗುತ್ತಿದೆ...")
all_data = fetch_terminal_data()
data_load_state.empty()

# 6. MARKET MOVEMENT DASHBOARD (NIFTY / SENSEX METRICS)
st.sidebar.markdown("### 🏢 Market Indices")
try:
    nifty = yf.Ticker("^NSEI").history(period="2d")
    if not nifty.empty:
        nifty_close = nifty['Close'].iloc[-1]
        nifty_change = ((nifty['Close'].iloc[-1] - nifty['Close'].iloc[-2]) / nifty['Close'].iloc[-2]) * 100
        st.sidebar.metric("NIFTY 50", f"{nifty_close:.2f}", f"{nifty_change:+.2f}%")
except Exception:
    st.sidebar.write("Indices data temporarily delayed")

# 7. LIVE SIGNAL DESK (COMBINED LEDGER WITH CONTAINERS)
st.header("📊 Live Signal Desk")
signal_desk_container = st.empty()

signals_list = []
matrix_rows = []

for stock, df in all_data.items():
    if df.empty:
        continue
    last_row = df.iloc[-1]
    
    # Check Alerts
    pattern = "NORMAL"
    if last_row['Bullish_Engulfing']:
        pattern = "🟢 BULLISH ENGULFING"
    elif last_row['Hammer']:
        pattern = "🔨 HAMMER DETECTED"
        
    if pattern != "NORMAL":
        signals_list.append({
            "Stock": stock,
            "Price": f"₹{last_row['Close']:.2f}",
            "RSI 14": f"{last_row['RSI_14']:.2f}",
            "Pattern Alert": pattern,
            "Time": datetime.now().strftime("%H:%M:%S")
        })
        
    # Technical Matrix Rows
    matrix_rows.append({
        "Stock": stock,
        "LTP": round(last_row['Close'], 2),
        "RSI 14": round(last_row['RSI_14'], 2),
        "MACD Hist": round(last_row['MACD_Hist'], 2),
        "ATR 14": round(last_row['ATR_14'], 2),
        "BB Upper": round(last_row['BB_Upper'], 2),
        "BB Lower": round(last_row['BB_Lower'], 2)
    })

with signal_desk_container.container():
    if signals_list:
        st.dataframe(pd.DataFrame(signals_list), use_container_width=True)
    else:
        st.success("✅ No critical institutional risk or breakout patterns detected in the last session.")

# 8. TECHNICAL MATRIX (SAFE FROM NAN AND PARTIAL RENDERING)
st.header("⚡ Technical Matrix Pass")
if matrix_rows:
    matrix_df = pd.DataFrame(matrix_rows)
    # Security layer against NameError or blank data pass
    matrix_df = matrix_df.replace([np.inf, -np.inf], np.nan).fillna(0)
    st.dataframe(matrix_df, use_container_width=True)
else:
    st.warning("Technical Matrix builds are empty. Reloading database...")

# 9. WICK-PERFECT ALTAIR CANDLESTICK CHART
st.sidebar.markdown("### 🔍 Stock Analysis")
selected_stock = st.sidebar.selectbox("Select Asset for Deep Pass", NSE_STOCKS)

if selected_stock in all_data:
    chart_df = all_data[selected_stock].reset_index()
    
    # Base chart for Candlestick
    base = alt.Chart(chart_df.tail(30)).encode(
        x=alt.X('Date:T', axis=alt.Axis(title="Timeline")),
        color=alt.condition("datum.Open <= datum.Close", alt.value("#00d09c"), alt.value("#ff5353"))
    )
    
    # Wick
    rule = base.mark_rule().encode(
        y=alt.Y('Low:Q', title="Price (INR)", scale=alt.Scale(zero=False)),
        y2=alt.Y('High:Q')
    )
    
    # Body
    bar = base.mark_bar().encode(
        y='Open:Q',
        y2='Close:Q'
    )
    
    st.header(f"📈 Wick-Perfect Altair View: {selected_stock}")
    st.altair_chart(rule + bar, use_container_width=True)
