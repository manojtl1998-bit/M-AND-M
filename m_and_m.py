import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import json
import os

# 1. ಪೇಜ್ ಸೆಟಪ್
st.set_page_config(page_title="M and M Quant Terminal", layout="wide")

st.markdown("""
    <style>
    /* ಇಡೀ ಆಪ್ ಬ್ಯಾಕ್‌ಗ್ರೌಂಡ್ ಬದಲಾವಣೆ */
    .stApp { background-color: #0b0f19; color: #ffffff; }
    div[data-testid="stMetric"] { background-color: #141a29; border: 1px solid #1e293b; padding: 15px; border-radius: 8px; }
    
    /* ಸ್ಟ್ರೀಮ್‌ಲಿಟ್ ಲೋಗೋ ಮತ್ತು ಮೆನುವನ್ನು ಸಂಪೂರ್ಣವಾಗಿ ಹೈಡ್ ಮಾಡಲು (HIDE STREAMLIT LOGO) */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    div[data-testid="stStatusWidget"] {visibility: hidden;}
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

st.title("🚀 M and M Institutional Quant Terminal")

selected_display = st.selectbox(
    "NSE Stock ಹುಡುಕಿ ಅಥವಾ ಆಯ್ಕೆ ಮಾಡಿ (2,200+ Stocks):", 
    options=list(nse_stocks.keys())
)

if selected_display:
    st.session_state.stored_ticker = nse_stocks[selected_display]
    st.session_state.stored_title = selected_display.split(" (")

@st.cache_data(ttl=60)
def get_market_data(ticker):
    stock = yf.Ticker(ticker)
    data = stock.history(period="3mo", interval="1d")
    return data

try:
    df = get_market_data(st.session_state.stored_ticker)
    
    if df.empty:
        st.error("⚠️ Yahoo Finance ನಿಂದ ಡೇಟಾ ಸಿಗುತ್ತಿಲ್ಲ.")
    else:
        latest_close = float(df['Close'].iloc[-1])
        prev_close = float(df['Close'].iloc[-2]) if len(df) > 1 else latest_close
        price_change = latest_close - prev_close
        pct_change = (price_change / prev_close) * 100

        # ಕ್ವಾಂಟ್ ಲಾಜಿಕ್ ಮ್ಯಾಟ್ರಿಕ್ಸ್ ಪಾಸ್
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
        st.subheader(f"⚡ {st.session_state.stored_title} ಇಂದಿನ ಸ್ಥಿತಿ")
        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        m_col1.metric("ಬೆಲೆ (INR)", f"₹{latest_close:.2f}", f"{price_change:+.2f} ({pct_change:+.2f}%)")
        m_col2.metric("RSI (14)", f"{df['RSI'].iloc[-1]:.2f}")
        m_col3.metric("MACD Line", f"{df['MACD'].iloc[-1]:.2f}")
        m_col4.metric("ATR (Volatility)", f"{df['ATR'].iloc[-1]:.2f}")

        # ---------------- NEW FEATURE: AUTOMATED BUY/SELL SIGNALS ----------------
        st.write("### 🚨 M and M ಆಟೋಮ್ಯಾಟಿಕ್ ಟ್ರೇಡಿಂಗ್ ಸಿಗ್ನಲ್ಸ್")
        
        rsi_now = df['RSI'].iloc[-1]
        macd_now = df['MACD'].iloc[-1]
        signal_now = df['Signal'].iloc[-1]
        
        # ಕ್ಯಾಂಡಲ್‌ಸ್ಟಿಕ್ ಪ್ಯಾಟರ್ನ್ ಲಾಜಿಕ್ (Bullish Engulfing / Hammer)
        is_bullish_engulfing = (df['Close'].iloc[-1] > df['Open'].iloc[-1]) and (df['Close'].iloc[-2] < df['Open'].iloc[-2]) and (df['Close'].iloc[-1] >= df['Open'].iloc[-2])
        is_hammer = ((df['High'].iloc[-1] - df['Low'].iloc[-1]) > 3 * np.abs(df['Open'].iloc[-1] - df['Close'].iloc[-1])) and ((df['Close'].iloc[-1] - df['Low'].iloc[-1]) / (.001 + df['High'].iloc[-1] - df['Low'].iloc[-1]) > 0.6)

        sig_col1, sig_col2 = st.columns(2)
        
        # 1. ಇಂಡಿಕೇಟರ್ ಸಿಗ್ನಲ್ (RSI + MACD)
        with sig_col1:
            st.info("📊 **ತಾಂತ್ರಿಕ ಸೂಚಕ ಸಿಗ್ನಲ್ (Technical Indicator):**")
            if rsi_now < 35 or (macd_now > signal_now and df['MACD'].iloc[-2] <= df['Signal'].iloc[-2]):
                st.success("🟢 **BUY SIGNAL (ಖರೀದಿಸಿ)**\n\nಸ್ಟಾಕ್ ಓವರ್‌ಸೋಲ್ಡ್ ವಲಯದಲ್ಲಿದೆ ಅಥವಾ MACD ಬುಲ್ಲಿಷ್ ಕ್ರಾಸ್‌ಓವರ್ ಮಾಡಿದೆ.")
            elif rsi_now > 70 or (macd_now < signal_now and df['MACD'].iloc[-2] >= df['Signal'].iloc[-2]):
                st.error("🔴 **SELL SIGNAL (ಮಾರಾಟ ಮಾಡಿ)**\n\nಸ್ಟಾಕ್ ಓವರ್‌ಬಾಟ್ ವಲಯದಲ್ಲಿದೆ ಅಥವಾ MACD ಬೇರಿಷ್ ಕ್ರಾಸ್‌ಓವರ್ ಮಾಡಿದೆ.")
            else:
                st.warning("🟡 **HOLD SIGNAL (ಕಾಯ್ದುಕೊಳ್ಳಿ)**\n\nಪ್ರಸ್ತುತ ಮಾರುಕಟ್ಟೆಯಲ್ಲಿ ಯಾವುದೇ ಬಲವಾದ ಟ್ರೆಂಡ್ ಇಲ್ಲ.")

        # 2. ಪ್ರೈಸ್ ಆಕ್ಷನ್ ಕ್ಯಾಂಡಲ್ ಅಲರ್ಟ್
        with sig_col2:
            st.info("🔍 **ಕ್ಯಾಂಡಲ್‌ಸ್ಟಿಕ್ ಪ್ಯಾಟರ್ನ್ ಅಲರ್ಟ್ (Price Action):**")
            if is_bullish_engulfing:
                st.success("🔥 **BULLISH ENGULFING ಕಂಡುಬಂದಿದೆ!**\n\nಖರೀದಿದಾರರು ಮಾರುಕಟ್ಟೆಯನ್ನು ನಿಯಂತ್ರಿಸುತ್ತಿದ್ದಾರೆ. ಬೆಲೆ ಏರಿಕೆಯಾಗಬಹುದು.")
            elif is_hammer:
                st.success("🔨 **HAMMER PATTERN ಮೂಡಿದೆ!**\n\nಕೆಳಗಿನ ಹಂತದಿಂದ ಬಲವಾದ ರಿವರ್ಸಲ್ ಸೂಚನೆ ಸಿಗುತ್ತಿದೆ.")
            else:
                st.write("ಪ್ರಸ್ತುತ ಯಾವುದೇ ಪ್ರಮುಖ ರಿವರ್ಸಲ್ ಕ್ಯಾಂಡಲ್ ಪ್ಯಾಟರ್ನ್ ಮೂಡಿಲ್ಲ.")
        # --------------------------------------------------------------------------

        st.write("### 📈 ಪ್ರೈಸ್ ಆಕ್ಷನ್ ಟ್ರೆಂಡ್ (Trend Chart)")
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

        st.write("### 🗒️ ಹಿಸ್ಟಾರಿಕಲ್ ಡೇಟಾ ಲೆಡ್ಜರ್ (Recent Data Points)")
        st.dataframe(df[['Open', 'High', 'Low', 'Close', 'RSI', 'MACD', 'ATR']].tail(5))

except Exception as e:
    st.error(f"⚠️ ರನ್‌ಟೈಮ್ ದೋಷ ಉಂಟಾಗಿದೆ: {e}")
