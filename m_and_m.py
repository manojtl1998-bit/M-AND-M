import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import json
import os

# 1. ಪೇಜ್ ಸೆಟಪ್ (ಆಪ್ ಹೆಸರು "M and M" ಎಂದು ಬದಲಾಯಿಸಲಾಗಿದೆ)
st.set_page_config(page_title="M and M Quant Terminal", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0b0f19; color: #ffffff; }
    div[data-testid="stMetric"] { background-color: #141a29; border: 1px solid #1e293b; padding: 15px; border-radius: 8px; }
    </style>
""", unsafe_allow_html=True)

if 'stored_ticker' not in st.session_state:
    st.session_state.stored_ticker = "RELIANCE.NS"
if 'stored_title' not in st.session_state:
    st.session_state.stored_title = "Reliance Industries"

def init_stock_database():
    json_file = "nse_stocks_live.json"
    if not os.path.exists(json_file):
        master_stocks = {
            "Reliance Industries Limited (RELIANCE.NS)": "RELIANCE.NS",
            "Tata Consultancy Services (TCS.NS)": "TCS.NS",
            "Infosys Limited (INFY.NS)": "INFY.NS",
            "HDFC Bank Limited (HDFCBANK.NS)": "HDFCBANK.NS",
            "ICICI Bank Limited (ICICIBANK.NS)": "ICICIBANK.NS",
            "State Bank of India (SBIN.NS)": "SBIN.NS",
            "Bharti Airtel Limited (BHARTIARTL.NS)": "BHARTIARTL.NS",
            "ITC Limited (ITC.NS)": "ITC.NS",
            "Larsen & Toubro Limited (LT.NS)": "LT.NS",
            "Axis Bank Limited (AXISBANK.NS)": "AXISBANK.NS"
        }
        with open(json_file, "w") as f:
            json.dump(master_stocks, f, indent=4)
    with open(json_file, "r") as f:
        return json.load(f)

nse_stocks = init_stock_database()

# ಹೆಡರ್ ಬ್ರ್ಯಾಂಡಿಂಗ್ ಬದಲಾವಣೆ
st.title("🚀 M and M Institutional Quant Terminal")

selected_display = st.selectbox(
    "NSE Stock ಹುಡುಕಿ ಅಥವಾ ಆಯ್ಕೆ ಮಾಡಿ (2,200+ Stocks):", 
    options=list(nse_stocks.keys())
)

if selected_display:
    st.session_state.stored_ticker = nse_stocks[selected_display]
    st.session_state.stored_title = selected_display.split(" (")[0]

@st.cache_data(ttl=5)
def get_market_data(ticker):
    stock = yf.Ticker(ticker)
    data = stock.history(period="60d", interval="15m")
    return data

try:
    df = get_market_data(st.session_state.stored_ticker)
    
    if df.empty:
        st.error("⚠️ ಲೈವ್ ಡೇಟಾ ಸಿಗುತ್ತಿಲ್ಲ. ದಯವಿಟ್ಟು ಇಂಟರ್ನೆಟ್ ಪರಿಶೀಲಿಸಿ.")
    else:
        latest_close = float(df['Close'].iloc[-1])
        prev_close = float(df['Close'].iloc[-2]) if len(df) > 1 else latest_close
        price_change = latest_close - prev_close
        pct_change = (price_change / prev_close) * 100

        # ಕ್ವಾಂಟ್ ಲಾಜಿಕ್ ಮ್ಯಾಟ್ರಿಕ್ಸ್
        delta = df['Close'].diff()
        gain = np.where(delta > 0, delta, 0)
        loss = np.where(delta < 0, -delta, 0)
        avg_gain = pd.Series(gain).ewm(com=13, adjust=False).mean()
        avg_loss = pd.Series(loss).ewm(com=13, adjust=False).mean()
        rs = avg_gain / (avg_loss + 1e-10)
        df['RSI'] = 100 - (100 / (1 + rs)).values

        df['EMA12'] = df['Close'].ewm(span=12, adjust=False).mean()
        df['EMA26'] = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = df['EMA12'] - df['EMA26']
        df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()

        df['H-L'] = df['High'] - df['Low']
        df['H-PC'] = np.abs(df['High'] - df['Close'].shift(1))
        df['L-PC'] = np.abs(df['Low'] - df['Close'].shift(1))
        df['TR'] = df[['H-L', 'H-PC', 'L-PC']].max(axis=1)
        df['ATR'] = df['TR'].ewm(span=14, adjust=False).mean()

        # UI ಮೆಟ್ರಿಕ್ಸ್
        st.subheader(f"⚡ {st.session_state.stored_title} ಪ್ರಸ್ತುತ ಲೈವ್ ಸ್ಥಿತಿ")
        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        m_col1.metric("ಲೈವ್ ಬೆಲೆ", f"₹{latest_close:.2f}", f"{price_change:+.2f} ({pct_change:+.2f}%)")
        m_col2.metric("RSI (14)", f"{df['RSI'].iloc[-1]:.2f}")
        m_col3.metric("MACD Line", f"{df['MACD'].iloc[-1]:.2f}")
        m_col4.metric("ATR (Volatility)", f"{df['ATR'].iloc[-1]:.2f}")

        st.write("### 📈 ಪ್ರೈಸ್ ಆಕ್ಷನ್ ಟ್ರೆಂಡ್ (Real-time Interval Chart)")
        st.line_chart(df['Close'])

        st.write("### 🛡️ ಇನ್ಸ್ಟಿಟ್ಯೂಷನಲ್ ರಿಸ್ಕ್ ಮ್ಯಾನೇಜ್ಮೆಂಟ್ ಗ್ರಿಡ್")
        atr_now = float(df['ATR'].iloc[-1])
        stop_loss = latest_close - (2 * atr_now)
        target_1 = latest_close + (3 * atr_now)
        max_exit = latest_close + (5 * atr_now)

        r_col1, r_col2, r_col3, r_col4 = st.columns(4)
        r_col1.info(f"**Entry Limit:**\n₹{latest_close:.2f}")
        r_col2.error(f"**Stop-Loss (2x ATR):**\n₹{stop_loss:.2f}")
        r_col3.success(f"**Target 1 (3x ATR):**\n₹{target_1:.2f}")
        r_col4.warning(f"**Max Target (5x ATR):**\n₹{max_exit:.2f}")

        st.write("### 🗒️ ಲೈವ್ ಡೇಟಾ ಲೆಡ್ಜರ್ (Recent Data Points)")
        st.dataframe(df[['Open', 'High', 'Low', 'Close', 'RSI', 'MACD', 'ATR']].tail(5))

except Exception as e:
    st.error(f"⚠️ ರನ್‌ಟೈಮ್ ದೋಷ ಉಂಟಾಗಿದೆ: {e}")
