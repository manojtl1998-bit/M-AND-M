import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import altair as alt
import json
import os

# 1. ಪೇಜ್ ಸೆಟಪ್
st.set_page_config(page_title="M and M Quant Terminal", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0b0f19; color: #ffffff; }
    div[data-testid="stMetric"] { background-color: #141a29; border: 1px solid #1e293b; padding: 15px; border-radius: 8px; }
    [data-testid="stHeader"] {display: none !important;}
    [data-testid="stToolbar"] {display: none !important;}
    [data-testid="stDecoration"] {display: none !important;}
    footer {visibility: hidden !important; display: none !important;}
    #MainMenu {visibility: hidden !important;}
    .block-container {padding-top: 1rem !important; padding-bottom: 0rem !important;}
    </style>
""", unsafe_allow_html=True)

if 'stored_ticker' not in st.session_state:
    st.session_state.stored_ticker = "RELIANCE.NS"
if 'stored_title' not in st.session_state:
    st.session_state.stored_title = "Reliance Industries"

@st.cache_data
def init_stock_database():
    import requests
    import io
    url = "https://nseindia.com"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        df_nse = pd.read_csv(io.StringIO(response.text))
        df_nse.columns = df_nse.columns.str.strip()
        master_stocks = {}
        for _, row in df_nse.iterrows():
            symbol = str(row['SYMBOL']).strip()
            name = str(row['NAME OF COMPANY']).strip()
            if symbol and symbol != "SYMBOL":
                ticker_ns = f"{symbol}.NS"
                master_stocks[f"{name} ({ticker_ns})"] = ticker_ns
        if len(master_stocks) > 50:
            return master_stocks
    except Exception:
        pass
    return {"Reliance Industries Limited (RELIANCE.NS)": "RELIANCE.NS"}

nse_stocks = init_stock_database()

st.title("🚀 M and M Institutional Quant Terminal")

selected_display = st.selectbox("NSE Stock ಹುಡುಕಿ ಅಥವಾ ಆಯ್ಕೆ ಮಾಡಿ (2,200+ Stocks):", options=list(nse_stocks.keys()))

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

        # ಕ್ವಾಂಟ್ ಲಾಜಿಕ್ ಮತ್ತು ಅಲ್ಗಾರಿದಮಿಕ್ ಇಂಡಿಕೇಟರ್ ಮ್ಯಾಟ್ರಿಕ್ಸ್
        delta = df['Close'].diff()
        gain = np.where(delta > 0, delta, 0)
        loss = np.where(delta < 0, -delta, 0)
        avg_gain = pd.Series(gain).ewm(com=13, adjust=False).mean()
        avg_loss = pd.Series(loss).ewm(com=13, adjust=False).mean()
        df['RSI'] = 100 - (100 / (1 + (avg_gain / (avg_loss + 1e-10)))).values

        df['EMA12'] = df['Close'].ewm(span=12, adjust=False).mean()
        df['EMA26'] = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = df['EMA12'] - df['EMA26']
        df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()

        df['H-L'] = df['High'] - df['Low']
        df['H-PC'] = np.abs(df['High'] - df['Close'].shift(1))
        df['L-PC'] = np.abs(df['Low'] - df['Close'].shift(1))
        df['TR'] = df[['H-L', 'H-PC', 'L-PC']].max(axis=1)
        df['ATR'] = df['TR'].ewm(span=14, adjust=False).mean()

        # 1. BOLLINGER BANDS ಅಲ್ಗಾರಿದಮ್ (20-Period, 2x Std Dev)
        df['BB_Middle'] = df['Close'].rolling(window=20).mean()
        df['BB_Std'] = df['Close'].rolling(window=20).std()
        df['BB_Upper'] = df['BB_Middle'] + (2 * df['BB_Std'])
        df['BB_Lower'] = df['BB_Middle'] - (2 * df['BB_Std'])

        # 2. SUPERTREND ಅಲ್ಗಾರಿದಮ್ (Period 10, Multiplier 3)
        hl2 = (df['High'] + df['Low']) / 2
        df['Basic_Upper'] = hl2 + (3 * df['ATR'])
        df['Basic_Lower'] = hl2 - (3 * df['ATR'])
        df['Final_Upper'] = df['Basic_Upper']
        df['Final_Lower'] = df['Basic_Lower']
        df['SuperTrend_Signal'] = "BUY"
        
        # ವೆಕ್ಟರೈಸ್ಡ್ ಸೂಪರ್ ಟ್ರೆಂಡ್ ಲೂಪ್ ಲೆಕ್ಕಾಚಾರ
        for i in range(1, len(df)):
            if df['Close'].iloc[i-1] <= df['Final_Upper'].iloc[i-1]:
                df.loc[df.index[i], 'Final_Upper'] = min(df['Basic_Upper'].iloc[i], df['Final_Upper'].iloc[i-1]) if df['Basic_Upper'].iloc[i] < df['Final_Upper'].iloc[i-1] or df['Close'].iloc[i-1] > df['Final_Upper'].iloc[i-1] else df['Final_Upper'].iloc[i-1]
            if df['Close'].iloc[i-1] >= df['Final_Lower'].iloc[i-1]:
                df.loc[df.index[i], 'Final_Lower'] = max(df['Basic_Lower'].iloc[i], df['Final_Lower'].iloc[i-1])
            
            if df['Close'].iloc[i] <= df['Final_Upper'].iloc[i]:
                df.loc[df.index[i], 'SuperTrend_Signal'] = "SELL"
            else:
                df.loc[df.index[i], 'SuperTrend_Signal'] = "BUY"

        # UI ಮೆಟ್ರಿಕ್ಸ್
        st.subheader(f"⚡ {st.session_state.stored_title} ಇಂದಿನ ಸ್ಥಿತಿ")
        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        m_col1.metric("ಬೆಲೆ (INR)", f"₹{latest_close:.2f}", f"{price_change:+.2f} ({pct_change:+.2f}%)")
        m_col2.metric("RSI (14)", f"{df['RSI'].iloc[-1]:.2f}")
        m_col3.metric("MACD Line", f"{df['MACD'].iloc[-1]:.2f}")
        m_col4.metric("ATR (Volatility)", f"{df['ATR'].iloc[-1]:.2f}")

        # ಸಿಗ್ನಲ್ಸ್ ಬಾಕ್ಸ್
        st.write("### 🚨 M and M ಅಲ್ಗಾರಿದಮಿಕ್ ಟ್ರೇಡಿಂಗ್ ಸಿಗ್ನಲ್ಸ್")
        st_signal = df['SuperTrend_Signal'].iloc[-1]
        bb_upper = df['BB_Upper'].iloc[-1]
        bb_lower = df['BB_Lower'].iloc[-1]

        sig_col1, sig_col2 = st.columns(2)
        with sig_col1:
            st.info("🤖 **SuperTrend ಅಲ್ಗಾರಿದಮ್ ಸಿಗ್ನಲ್:**")
            if st_signal == "BUY":
                st.success("🟢 **ALGO: STRONG BUY (ಬಲವಾದ ಖರೀದಿ)**\n\nಸೂಪರ್ ಟ್ರೆಂಡ್ ಅಲ್ಗಾರಿದಮ್ ಬುಲ್ಲಿಷ್ ವಲಯವನ್ನು ಖಚಿತಪಡಿಸಿದೆ.")
            else:
                st.error("🔴 **ALGO: STRONG SELL (ಬಲವಾದ ಮಾರಾಟ)**\n\nಸೂಪರ್ ಟ್ರೆಂಡ್ ಅಲ್ಗಾರಿದಮ್ ಬೇರಿಷ್ ಟ್ರೆಂಡ್ ಸೂಚಿಸಿದೆ.")

        with sig_col2:
            st.info("📊 **Bollinger Bands ಬ್ರೇಕ್‌ಔಟ್ ಅಲರ್ಟ್:**")
            if latest_close >= bb_upper:
                st.success("🔥 **UPPER BAND BREAKOUT!**\n\nಬೆಲೆಯು ಬೋಲಿಂಜರ್ ಮೇಲ್ಭಾಗದ ಬ್ಯಾಂಡ್ ದಾಟಿದೆ. ತೀವ್ರ ಏರಿಕೆಯ ಸಾಧ್ಯತೆ.")
            elif latest_close <= bb_lower:
                st.error("⚠️ **LOWER BAND BREAKOUT!**\n\nಬೆಲೆಯು ಕೆಳಭಾಗದ ಬ್ಯಾಂಡ್ಗಿಂತ ಕೆಳಗೆ ಹೋಗಿದೆ. ಓವರ್‌ಸೋಲ್ಡ್ ಸೂಚನೆ.")
            else:
                st.warning("🟡 **ಬ್ಯಾಂಡ್ ಒಳಗಡೆ ಚಲನೆ:** ಬೆಲೆಯು ಸ್ಥಿರ ವಲಯದಲ್ಲಿದೆ (Normal Range).")

        # TradingView ಶೈಲಿಯ ಕ್ಯಾಂಡಲ್‌ಸ್ಟಿಕ್ ಚಾರ್ಟ್ (ALTAIR)
        st.write("### 🕯️ TradingView ಶೈಲಿಯ ಕ್ಯಾಂಡಲ್‌ಸ್ಟಿಕ್ ಚಾರ್ಟ್")
        chart_df = df.copy().reset_index()
        chart_df['Date'] = pd.to_datetime(chart_df['Date'])
        
        open_close_color = alt.condition("datum.Open <= datum.Close", alt.value("#26a69a"), alt.value("#ef5350"))
        wick = alt.Chart(chart_df).mark_rule(color="#d1d4dc", strokeWidth=1).encode(
            x=alt.X('Date:T', title="ದಿನಾಂک", axis=alt.Axis(format='%d %b', grid=False)),
            y=alt.Y('Low:Q', title="ಬೆಲೆ (INR)", scale=alt.Scale(zero=False)), y2='High:Q'
        )
        body = alt.Chart(chart_df).mark_bar(width=6).encode(x='Date:T', y='Open:Q', y2='Close:Q', color=open_close_color)
        
        candles = (wick + body).properties(height=400, background='#0b0f19').configure_view(strokeWidth=0)
        st.altair_chart(candles, use_container_width=True)

        # ರಿಸ್ಕ್ ಮ್ಯಾನೇಜ್ಮೆಂಟ್ ಗ್ರಿಡ್
        st.write("### 🛡️ ಇನ್ಸ್ಟಿಟ್ಯೂಷನಲ್ ರಿಸ್ಕ್ ಮ್ಯಾನೇಜ್ಮೆಂಟ್ ಗ್ರಿಡ್")
        atr_now = float(df['ATR'].iloc[-1])
        r_col1, r_col2, r_col3, r_col4 = st.columns(4)
        r_col1.info(f"**Entry Limit:**\n₹{latest_close:.2f}")
        r_col2.error(f"**Stop-Loss (2x ATR):**\n₹{(latest_close - (2 * atr_now)):.2f}")
        r_col3.success(f"**Target 1 (3x ATR):**\n₹{(latest_close + (3 * atr_now)):.2f}")
        r_col4.warning(f"**Max Target (5x ATR):**\n₹{(latest_close + (5 * atr_now)):.2f}")

except Exception as e:
    st.error(f"⚠️ ರನ್‌ಟೈಮ್ ದೋಷ ಉಂಟಾಗಿದೆ: {e}")
