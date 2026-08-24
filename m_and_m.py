import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import altair as alt
import json
import os

# 1. ಪೇಜ್ ಸೆಟಪ್ (Groww ಬ್ರ್ಯಾಂಡ್ ಡಾರ್ಕ್ ಥೀಮ್)
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

# 2. ಪ್ರಮುಖ 70+ NSE ಸ್ಟಾಕ್‌ಗಳ ಇನ್‌ಬಿಲ್ಟ್ ಡೇಟಾಬೇಸ್
def init_stock_database():
    return {
        "Reliance Industries Limited (RELIANCE.NS)": "RELIANCE.NS",
        "Mahindra & Mahindra Limited (M&M.NS)": "M&M.NS",
        "State Bank of India (SBIN.NS)": "SBIN.NS",
        "Tata Consultancy Services Limited (TCS.NS)": "TCS.NS",
        "Infosys Limited (INFY.NS)": "INFY.NS",
        "HDFC Bank Limited (HDFCBANK.NS)": "HDFCBANK.NS",
        "ICICI Bank Limited (ICICIBANK.NS)": "ICICIBANK.NS",
        "Bharti Airtel Limited (BHARTIARTL.NS)": "BHARTIARTL.NS",
        "ITC Limited (ITC.NS)": "ITC.NS",
        "Larsen & Toubro Limited (LT.NS)": "LT.NS",
        "Axis Bank Limited (AXISBANK.NS)": "AXISBANK.NS",
        "Tata Motors Limited (TATAMOTORS.NS)": "TATAMOTORS.NS",
        "Wipro Limited (WIPRO.NS)": "WIPRO.NS",
        "HCL Technologies Limited (HCLTECH.NS)": "HCLTECH.NS",
        "Adani Ports and SEZ Limited (ADANIPORTS.NS)": "ADANIPORTS.NS",
        "Asian Paints Limited (ASIANPAINT.NS)": "ASIANPAINT.NS",
        "Bajaj Finance Limited (BAJFINANCE.NS)": "BAJFINANCE.NS",
        "Bajaj Finserv Limited (BAJAJFINSV.NS)": "BAJAJFINSV.NS",
        "Bharat Petroleum Corporation Limited (BPCL.NS)": "BPCL.NS",
        "Cipla Limited (CIPLA.NS)": "CIPLA.NS",
        "Coal India Limited (COALINDIA.NS)": "COALINDIA.NS",
        "Dr. Reddy's Laboratories Limited (DRREDDY.NS)": "DRREDDY.NS",
        "Eicher Motors Limited (EICHERMOT.NS)": "EICHERMOT.NS",
        "Grasim Industries Limited (GRASIM.NS)": "GRASIM.NS",
        "Hindalco Industries Limited (HINDALCO.NS)": "HINDALCO.NS",
        "Hindustan Unilever Limited (HUL.NS)": "HUL.NS",
        "JSW Steel Limited (JSWSTEEL.NS)": "JSWSTEEL.NS",
        "Kotak Mahindra Bank Limited (KOTAKBANK.NS)": "KOTAKBANK.NS",
        "Maruti Suzuki India Limited (MARUTI.NS)": "MARUTI.NS",
        "National Thermal Power Corporation (NTPC.NS)": "NTPC.NS",
        "Oil & Natural Gas Corporation Limited (ONGC.NS)": "ONGC.NS",
        "Power Grid Corporation of India Limited (POWERGRID.NS)": "POWERGRID.NS",
        "Sun Pharmaceutical Industries Limited (SUNPHARMA.NS)": "SUNPHARMA.NS",
        "Tata Consumer Products Limited (TATACONSUM.NS)": "TATACONSUM.NS",
        "Tata Steel Limited (TATASTEEL.NS)": "TATASTEEL.NS",
        "Tech Mahindra Limited (TECHM.NS)": "TECHM.NS",
        "Titan Company Limited (TITAN.NS)": "TITAN.NS",
        "UltraTech Cement Limited (ULTRACEMCO.NS)": "ULTRACEMCO.NS",
        "Apollo Hospitals Enterprise Limited (APOLLOHOSP.NS)": "APOLLOHOSP.NS",
        "Britannia Industries Limited (BRITANNIA.NS)": "BRITANNIA.NS",
        "Hero MotoCorp Limited (HEROMOTOCO.NS)": "HEROMOTOCO.NS",
        "IndusInd Bank Limited (INDUSINDBK.NS)": "INDUSINDBK.NS",
        "LTIMindtree Limited (LTIM.NS)": "LTIM.NS",
        "Divi's Laboratories Limited (DIVISLAB.NS)": "DIVISLAB.NS",
        "Bajaj Auto Limited (BAJAJ-AUTO.NS)": "BAJAJ-AUTO.NS",
        "Adani Enterprises Limited (ADANIENT.NS)": "ADANIENT.NS",
        "Adani Green Energy Limited (ADANIGREEN.NS)": "ADANIGREEN.NS",
        "Adani Total Gas Limited (ATGL.NS)": "ATGL.NS",
        "Avenue Supermarts Limited (DMART.NS)": "DMART.NS",
        "Ambuja Cements Limited (AMBUJACEM.NS)": "AMBUJACEM.NS",
        "Bank of Baroda (BANKBARODA.NS)": "BANKBARODA.NS",
        "Bharat Electronics Limited (BEL.NS)": "BEL.NS",
        "Canara Bank (CANBK.NS)": "CANBK.NS",
        "DLF Limited (DLF.NS)": "DLF.NS",
        "Hindustan Aeronautics Limited (HAL.NS)": "HAL.NS",
        "Indian Oil Corporation Limited (IOC.NS)": "IOC.NS",
        "IRCTC Limited (IRCTC.NS)": "IRCTC.NS",
        "Jindal Steel & Power Limited (JINDALSTEL.NS)": "JINDALSTEL.NS",
        "Lupin Limited (LUPIN.NS)": "LUPIN.NS",
        "MRF Limited (MRF.NS)": "MRF.NS",
        "Muthoot Finance Limited (MUTHOOTFIN.NS)": "MUTHOOTFIN.NS",
        "NMDC Limited (NMDC.NS)": "NMDC.NS",
        "Punjab National Bank (PNB.NS)": "PNB.NS",
        "REC Limited (RECLTD.NS)": "RECLTD.NS",
        "Siemens Limited (SIEMENS.NS)": "SIEMENS.NS",
        "SRF Limited (SRF.NS)": "SRF.NS",
        "Steel Authority of India Limited (SAIL.NS)": "SAIL.NS",
        "Trent Limited (TRENT.NS)": "TRENT.NS",
        "Varun Beverages Limited (VBL.NS)": "VBL.NS",
        "Zomato Limited (ZOMATO.NS)": "ZOMATO.NS"
    }

nse_stocks = init_stock_database()

st.title("🚀 M and M Institutional Quant Terminal")

selected_display = st.selectbox("NSE Stock ಹುಡುಕಿ ಅಥವಾ ಆಯ್ಕೆ ಮಾಡಿ:", options=list(nse_stocks.keys()))

if selected_display:
    st.session_state.stored_ticker = nse_stocks[selected_display]
    st.session_state.stored_title = selected_display.split(" (")

# ಸುರಕ್ಷಿತ ಲೋಡಿಂಗ್ ಇಂಜಿನ್ (ORDER FIXED HERE)
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

        # ಕ್ವಾಂಟ್ ಲಾಜಿಕ್
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

        # Bollinger Bands ಅಲ್ಗಾರಿದಮ್
        df['BB_Middle'] = df['Close'].rolling(window=20).mean()
        df['BB_Std'] = df['Close'].rolling(window=20).std()
        df['BB_Upper'] = df['BB_Middle'] + (2 * df['BB_Std'])
        df['BB_Lower'] = df['BB_Middle'] - (2 * df['BB_Std'])

        # SuperTrend ಅಲ್ಗಾರಿದಮ್
        hl2 = (df['High'] + df['Low']) / 2
        df['Basic_Upper'] = hl2 + (3 * df['ATR'])
        df['Basic_Lower'] = hl2 - (3 * df['ATR'])
        df['Final_Upper'] = df['Basic_Upper'].copy()
        df['Final_Lower'] = df['Basic_Lower'].copy()
        
        st_signals = []
        current_signal = "BUY"
        
        for i in range(len(df)):
            if i == 0:
                st_signals.append("BUY")
                continue
                
            if df['Close'].iloc[i-1] <= df['Final_Upper'].iloc[i-1]:
                df.iloc[i, df.columns.get_loc('Final_Upper')] = min(df['Basic_Upper'].iloc[i], df['Final_Upper'].iloc[i-1])
            if df['Close'].iloc[i-1] >= df['Final_Lower'].iloc[i-1]:
                df.iloc[i, df.columns.get_loc('Final_Lower')] = max(df['Basic_Lower'].iloc[i], df['Final_Lower'].iloc[i-1])
            
            if df['Close'].iloc[i] <= df['Final_Upper'].iloc[i]:
                current_signal = "SELL"
            else:
                current_signal = "BUY"
            st_signals.append(current_signal)
            
        df['SuperTrend_Signal'] = st_signals

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
                st.success("🟢 **ALGO: STRONG BUY (ಬಲವಾದ ಖರೀದಿ)**")
            else:
                st.error("🔴 **ALGO: STRONG SELL (ಬಲವಾದ ಮಾರಾಟ)**")

        with sig_col2:
            st.info("📊 **Bollinger Bands ಬ್ರೇಕ್‌ಔಟ್ ಅಲರ್ಟ್:**")
            if latest_close >= bb_upper:
                st.success("🔥 **UPPER BAND BREAKOUT!**")
            elif latest_close <= bb_lower:
                st.error("⚠️ **LOWER BAND BREAKOUT!**")
