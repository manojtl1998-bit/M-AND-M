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
# 3. 2,200+ NSE ಮ್ಯಾಸ್ಸಿವ್ ಸ್ಟಾಕ್ ಲೋಡರ್ ಇಂಜಿನ್ (FIXED FOR ALL STOCKS)
@st.cache_data
def init_stock_database():
    import requests
    import io
    
    # 2200+ ಅಧಿಕೃತ ಸ್ಟಾಕ್‌ಗಳ ಲಿಸ್ಟ್ ಪಡೆಯಲು ಎನ್‌ಎಸ್‌ಇ ಲೈವ್ ಯುಆರ್‌ಎಲ್
    url = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        # ಆನ್‌ಲೈನ್‌ನಲ್ಲಿ ಲೈವ್ ಎನ್‌ಎಸ್‌ಇ ಲಿಸ್ಟ್ ಡೌನ್‌ಲೋಡ್ ಮಾಡುವುದು
        response = requests.get(url, headers=headers, timeout=10)
        df_nse = pd.read_csv(io.StringIO(response.text))
        df_nse.columns = df_nse.columns.str.strip()
        
        master_stocks = {}
        for _, row in df_nse.iterrows():
            symbol = str(row['SYMBOL']).strip()
            name = str(row['NAME OF COMPANY']).strip()
            if symbol and symbol != "SYMBOL":
                ticker_ns = f"{symbol}.NS"
                display_name = f"{name} ({ticker_ns})"
                master_stocks[display_name] = ticker_ns
        
        if len(master_stocks) > 50:
            return master_stocks
            
    except Exception:
        pass
        
    # ಒಂದು ವೇಳೆ ಎನ್‌ಎಸ್‌ಇ ಸರ್ವರ್ ಡೌನ್ ಇದ್ದರೆ ಬ್ಯಾಕಪ್ ಲಿಸ್ಟ್
    return {
        "Reliance Industries Limited (RELIANCE.NS)": "RELIANCE.NS",
        "Tata Consultancy Services Limited (TCS.NS)": "TCS.NS",
        "Infosys Limited (INFY.NS)": "INFY.NS",
        "HDFC Bank Limited (HDFCBANK.NS)": "HDFCBANK.NS",
        "ICICI Bank Limited (ICICIBANK.NS)": "ICICIBANK.NS",
        "State Bank of India (SBIN.NS)": "SBIN.NS",
        "Bharti Airtel Limited (BHARTIARTL.NS)": "BHARTIARTL.NS",
        "ITC Limited (ITC.NS)": "ITC.NS",
        "Larsen & Toubro Limited (LT.NS)": "LT.NS",
        "Axis Bank Limited (AXISBANK.NS)": "AXISBANK.NS",
        "Mahindra & Mahindra Limited (M&M.NS)": "M&M.NS",
        "Tata Motors Limited (TATAMOTORS.NS)": "TATAMOTORS.NS"
    }

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
        st.subheader(f"⚡ {st.session_state.stored_title} ಇಂದಿನ ಸ್ಥಿತಿ")
        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        m_col1.metric("ಬೆಲೆ (INR)", f"₹{latest_close:.2f}", f"{price_change:+.2f} ({pct_change:+.2f}%)")
        m_col2.metric("RSI (14)", f"{df['RSI'].iloc[-1]:.2f}")
        m_col3.metric("MACD Line", f"{df['MACD'].iloc[-1]:.2f}")
        m_col4.metric("ATR (Volatility)", f"{df['ATR'].iloc[-1]:.2f}")

        # ಸಿಗ್ನಲ್ಸ್ ಬಾಕ್ಸ್
        st.write("### 🚨 M and M ಆಟೋಮ್ಯಾಟಿಕ್ ಟ್ರೇಡಿಂಗ್ ಸಿಗ್ನಲ್ಸ್")
        rsi_now = df['RSI'].iloc[-1]
        macd_now = df['MACD'].iloc[-1]
        signal_now = df['Signal'].iloc[-1]
        
        is_bullish_engulfing = (df['Close'].iloc[-1] > df['Open'].iloc[-1]) and (df['Close'].iloc[-2] < df['Open'].iloc[-2]) and (df['Close'].iloc[-1] >= df['Open'].iloc[-2])
        is_hammer = ((df['High'].iloc[-1] - df['Low'].iloc[-1]) > 3 * np.abs(df['Open'].iloc[-1] - df['Close'].iloc[-1])) and ((df['Close'].iloc[-1] - df['Low'].iloc[-1]) / (.001 + df['High'].iloc[-1] - df['Low'].iloc[-1]) > 0.6)

        sig_col1, sig_col2 = st.columns(2)
        with sig_col1:
            st.info("📊 **ತಾಂತ್ರಿಕ ಸೂಚಕ ಸಿಗ್ನಲ್:**")
            if rsi_now < 35 or (macd_now > signal_now and df['MACD'].iloc[-2] <= df['Signal'].iloc[-2]):
                st.success("🟢 **BUY SIGNAL (ಖರೀದಿಸಿ)**")
            elif rsi_now > 70 or (macd_now < signal_now and df['MACD'].iloc[-2] >= df['Signal'].iloc[-2]):
                st.error("🔴 **SELL SIGNAL (ಮಾರಾಟ ಮಾಡಿ)**")
            else:
                st.warning("🟡 **HOLD SIGNAL (ಕಾಯ್ದುಕೊಳ್ಳಿ)**")

        with sig_col2:
            st.info("🔍 **ಕ್ಯಾಂಡಲ್‌ಸ್ಟಿಕ್ ಪ್ಯಾಟರ್ನ್ ಅಲರ್ಟ್:**")
            if is_bullish_engulfing:
                st.success("🔥 **BULLISH ENGULFING ಕಂಡುಬಂದಿದೆ!**")
            elif is_hammer:
                st.success("🔨 **HAMMER PATTERN ಮೂಡಿದೆ!**")
            else:
                st.write("ಪ್ರಸ್ತುತ ಯಾವುದೇ ಪ್ರಮುಖ ರಿವರ್ಸಲ್ ಕ್ಯಾಂಡಲ್ ಪ್ಯಾಟರ್ನ್ ಮೂಡಿಲ್ಲ.")

        # --------------- REAL TRADINGVIEW STYLE CANDLESTICK CHART (ALTAIR) ---------------
        st.write("### 🕯️ TradingView ಶೈಲಿಯ ಕ್ಯಾಂಡಲ್‌ಸ್ಟಿಕ್ ಚಾರ್ಟ್")
        
        chart_df = df.copy().reset_index()
        chart_df['Date'] = pd.to_datetime(chart_df['Date'])
        
        # ಹಸಿರು ಮತ್ತು ಕೆಂಪು ಕಂಡೀಷನ್ ಮ್ಯಾಟ್ರಿಕ್ಸ್
        open_close_color = alt.condition(
            "datum.Open <= datum.Close",
            alt.value("#26a69a"), # TradingView Green
            alt.value("#ef5350")  # TradingView Red
        )

        # 1. ಕ್ಯಾಂಡಲ್‌ನ ಮಧ್ಯದ ಕೋಲು (Wick/Rule)
        wick = alt.Chart(chart_df).mark_rule(color="#d1d4dc", strokeWidth=1).encode(
            x=alt.X('Date:T', title="ದಿನಾಂಕ", axis=alt.Axis(format='%d %b', grid=False)),
            y=alt.Y('Low:Q', title="ಬೆಲೆ (INR)", scale=alt.Scale(zero=False)),
            y2='High:Q'
        )

        # 2. ಕ್ಯಾಂಡಲ್‌ನ ಬಾಡಿ (Body/Bar)
        body = alt.Chart(chart_df).mark_bar(width=6).encode(
            x='Date:T',
            y='Open:Q',
            y2='Close:Q',
            color=open_close_color
        )

        # ಎರಡನ್ನೂ ಒಟ್ಟಿಗೆ ಸೇರಿಸಿ ಚಾರ್ಟ್ ಪ್ರದರ್ಶಿಸುವುದು
        candles = (wick + body).properties(height=400, background='#0b0f19').configure_view(strokeWidth=0)
        st.altair_chart(candles, use_container_width=True)
        # ----------------------------------------------------------------------------------

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
