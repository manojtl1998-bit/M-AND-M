import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go  # 🌟 ಅಲ್ಟೇರ್ ಬದಲಿಗೆ ಪ್ಲಾಟ್ಲಿ ಇಂಪೋರ್ಟ್ ಮಾಡಲಾಗಿದೆ
from datetime import datetime

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
    
    # SuperTrend Loop Placeholder
    df['ST_Upper'] = ((df['High'] + df['Low']) / 2) + (3 * df['ATR_14'])
    df['ST_Lower'] = ((df['High'] + df['Low']) / 2) - (3 * df['ATR_14'])
    df['SuperTrend'] = df['ST_Lower']
    
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
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = [col for col in df.columns]
                df.columns = df.columns.map(str)
                master_data[stock] = calculate_indicators(df)
        except Exception:
            continue
    return master_data

data_load_state = st.info("🔄 Institutional Data Grid ಪ್ರೊಸೆಸ್ ಆಗುತ್ತಿದೆ...")
all_data = fetch_terminal_data()
data_load_state.empty()

# 6. MARKET MOVEMENT DASHBOARD (NIFTY & SENSEX METRICS FIX)
st.sidebar.markdown("### 🏢 Market Indices")

# --- A. NIFTY 50 FETCH ---
try:
    nifty = yf.Ticker("^NSEI").history(period="2d")
    if not nifty.empty:
        if isinstance(nifty.columns, pd.MultiIndex):
            nifty.columns = [col for col in nifty.columns]
        nifty.columns = nifty.columns.map(str)
        nifty_close = float(nifty['Close'].iloc[-1])
        nifty_change = float(((nifty['Close'].iloc[-1] - nifty['Close'].iloc[-2]) / nifty['Close'].iloc[-2]) * 100)
        st.sidebar.metric("NIFTY 50", f"{nifty_close:.2f}", f"{nifty_change:+.2f}%")
except Exception:
    st.sidebar.write("⚠️ NIFTY data temporarily delayed")

# --- B. SENSEX FETCH (🌟 ಹೊಸದಾಗಿ ಸೇರಿಸಲಾದ ಲೇಯರ್ 🌟) ---
try:
    sensex = yf.Ticker("^BSESN").history(period="2d")
    if not sensex.empty:
        if isinstance(sensex.columns, pd.MultiIndex):
            sensex.columns = [col for col in sensex.columns]
        sensex.columns = sensex.columns.map(str)
        sensex_close = float(sensex['Close'].iloc[-1])
        sensex_change = float(((sensex['Close'].iloc[-1] - sensex['Close'].iloc[-2]) / sensex['Close'].iloc[-2]) * 100)
        st.sidebar.metric("BSE SENSEX", f"{sensex_close:.2f}", f"{sensex_change:+.2f}%")
except Exception:
    st.sidebar.write("⚠️ SENSEX data temporarily delayed")


# 7. LIVE SIGNAL DESK (COMBINED LEDGER)
st.header("📊 Live Signal Desk")
signal_desk_container = st.empty()

signals_list = []
matrix_rows = []

for stock, df in all_data.items():
    if df.empty:
        continue
    last_row = df.iloc[-1]
    
    pattern = "NORMAL"
    if bool(last_row['Bullish_Engulfing']):
        pattern = "🟢 BULLISH ENGULFING"
    elif bool(last_row['Hammer']):
        pattern = "🔨 HAMMER DETECTED"
        
    if pattern != "NORMAL":
        signals_list.append({
            "Stock": stock,
            "Price": f"₹{float(last_row['Close']):.2f}",
            "RSI 14": f"{float(last_row['RSI_14']):.2f}",
            "Pattern Alert": pattern,
            "Time": datetime.now().strftime("%H:%M:%S")
        })
        
    matrix_rows.append({
        "Stock": stock,
        "LTP": round(float(last_row['Close']), 2),
        "RSI 14": round(float(last_row['RSI_14']), 2),
        "MACD Hist": round(float(last_row['MACD_Hist']), 2),
        "ATR 14": round(float(last_row['ATR_14']), 2),
        "BB Upper": round(float(last_row['BB_Upper']), 2),
        "BB Lower": round(float(last_row['BB_Lower']), 2)
    })

with signal_desk_container.container():
    if signals_list:
        st.dataframe(pd.DataFrame(signals_list), use_container_width=True)
    else:
        st.success("✅ No critical institutional risk or breakout patterns detected in the last session.")

# 8. TECHNICAL MATRIX PASS
st.header("⚡ Technical Matrix Pass")
if matrix_rows:
    matrix_df = pd.DataFrame(matrix_rows)
    matrix_df = matrix_df.replace([np.inf, -np.inf], np.nan).fillna(0)
    st.dataframe(matrix_df, use_container_width=True)
else:
    st.warning("Technical Matrix builds are empty.")
# 9. NATIVE INSTITUTIONAL PRICE PASS (100% ERROR-FREE RENDER)
st.sidebar.markdown("### 🔍 Stock Analysis")
selected_stock = st.sidebar.selectbox("Select Asset for Deep Pass", NSE_STOCKS)

if selected_stock in all_data:
    raw_df = all_data[selected_stock].copy()
    chart_df = raw_df.reset_index()
    
    # 🌟 ಸರಿಯಾದ ಪರಿಹಾರ: ಮೊದಲ ಕಾಲಂ ಅನ್ನು ಮಾತ್ರ ಕಡ್ಡಾಯವಾಗಿ 'Date' ಎಂದು ಬದಲಾಯಿಸುವುದು 🌟
    chart_df.columns.values[0] = 'Date'
    
    # ಡೇಟ್ ಫಾರ್ಮ್ಯಾಟ್ ಕ್ಲೀನ್ ಮಾಡುವುದು
    chart_df['Date'] = pd.to_datetime(chart_df['Date']).dt.date
    
    # ಕೊನೆಯ 30 ದಿನಗಳ ಕ್ಲೋಸಿಂಗ್ ಪ್ರೈಸ್ ಮಾತ್ರ ಫಿಲ್ಟರ್ ಮಾಡಿ ಇಂಡೆಕ್ಸ್ ಮಾಡುವುದು
    plot_data = chart_df[['Date', 'Close']].tail(30).set_index('Date')
    
    st.header(f"📈 Institutional Closing Price Pass: {selected_stock}")
    
    # ಸ್ಟ್ರೀಮ್‌ಲಿಟ್‌ನದ್ದೇ ಆದ ನೇರ ಗ್ರಾಫ್ - ಇದು ಎಂದಿಗೂ ಫೇಲ್ ಆಗುವುದಿಲ್ಲ
    st.line_chart(plot_data, use_container_width=True, height=400)


