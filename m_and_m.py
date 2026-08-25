import streamlit as pd_st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

# ==========================================
# 1. SYSTEM CONFIGURATION & FIXED DARK THEME
# ==========================================
pd_st.set_page_config(
    page_title="M&M Institutional Quant Terminal",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Premium Matte Dark Charcoal Palette
pd_st.markdown("""
    <style>
        html, body, [data-testid="stAppViewContainer"] { 
            background-color: #0b0f19 !important; 
            color: #d1d4dc !important; 
        }
        .block-container {
            max-width: 100% !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
            padding-top: 1.5rem !important;
            padding-bottom: 1.5rem !important;
        }
        h1, h2, h3 { color: #ffffff !important; font-family: 'Inter', sans-serif; }
        div[data-testid="stMetricValue"] { color: #00e676 !important; font-weight: bold; font-size: 26px !important; }
        .stDataFrame div { background-color: #12161a !important; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. DATA ENGINE & CORE QUANT OPERATIONS
# ==========================================
@pd_st.cache_data(ttl=120)
def fetch_ticker_data(symbol: str, period: str = "60d", interval: str = "15m"):
    """Fetches real-time institutional data feeds from yfinance with safe level flattening"""
    try:
        raw_df = yf.download(tickers=symbol, period=period, interval=interval)
        if raw_df.empty:
            return pd.DataFrame()
            
        if isinstance(raw_df.columns, pd.MultiIndex):
            raw_df.columns = raw_df.columns.get_level_values(0)
            
        raw_df.columns = [str(col).strip() for col in raw_df.columns]
        raw_df = raw_df.reset_index()
        
        rename_dict = {
            'Date': 'Date', 'Datetime': 'Datetime', 'Open': 'Open', 
            'High': 'High', 'Low': 'Low', 'Close': 'Close', 'Volume': 'Volume'
        }
        raw_df = raw_df.rename(columns=rename_dict)
        return raw_df
    except Exception:
        return pd.DataFrame()

def calculate_quant_matrix(df: pd.DataFrame):
    """Executes Complete Vectorized Quant Passes: RSI, MACD, ATR, SuperTrend & Chandelier"""
    df = df.copy()
    if len(df) < 30:
        return df

    close_ser = pd.Series(df['Close'].values.flatten(), name='Close')
    high_ser = pd.Series(df['High'].values.flatten(), name='High')
    low_ser = pd.Series(df['Low'].values.flatten(), name='Low')

    # RSI 14 Pass
    close_delta = close_ser.diff()
    gain = (close_delta.clip(lower=0)).rolling(window=14).mean()
    loss = (-close_delta.clip(upper=0)).rolling(window=14).mean()
    rs = gain / (loss + 1e-10)
    df['RSI_14'] = (100 - (100 / (1 + rs))).values

    # MACD Pass (12, 26, 9)
    df['EMA_12'] = close_ser.ewm(span=12, adjust=False).mean().values
    df['EMA_26'] = close_ser.ewm(span=26, adjust=False).mean().values
    df['MACD_Line'] = df['EMA_12'] - df['EMA_26']
    df['MACD_Signal'] = df['MACD_Line'].ewm(span=9, adjust=False).mean().values

    # ATR Matrix
    h_l = high_ser - low_ser
    h_pc = (high_ser - close_ser.shift(1)).abs()
    l_pc = (low_ser - close_ser.shift(1)).abs()
    tr = pd.concat([h_l, h_pc, l_pc], axis=1).max(axis=1)
    df['ATR_14'] = tr.rolling(window=14).mean().values

    # Chandelier Momentum Channel
    df['Highest_High_22'] = high_ser.rolling(window=22).max().values
    df['Chandelier_Long'] = df['Highest_High_22'] - (df['ATR_14'] * 3.0)

    # SuperTrend Pass
    st_atr = df['ATR_14'].values * 3.0
    hl2 = ((high_ser + low_ser) / 2).values
    basic_ub = hl2 + st_atr
    basic_lb = hl2 - st_atr
    
    ub_arr = basic_ub.flatten()
    lb_arr = basic_lb.flatten()
    close_arr = close_ser.values.flatten()
    
    st_arr = np.zeros(len(df))
    dir_arr = np.ones(len(df))

    for i in range(1, len(df)):
        if close_arr[i-1] > ub_arr[i-1]:
            dir_arr[i] = 1
        elif close_arr[i-1] < lb_arr[i-1]:
            dir_arr[i] = -1
        else:
            dir_arr[i] = dir_arr[i-1]
            if dir_arr[i] == 1 and lb_arr[i] < lb_arr[i-1]: 
                lb_arr[i] = lb_arr[i-1]
            if dir_arr[i] == -1 and ub_arr[i] > ub_arr[i-1]: 
                ub_arr[i] = ub_arr[i-1]
        st_arr[i] = lb_arr[i] if dir_arr[i] == 1 else ub_arr[i]

    df['SuperTrend'] = st_arr
    df['Trend_Direction'] = dir_arr
    return df

def generate_execution_signals(df: pd.DataFrame):
    """Institutional Multi-Algo Confluence Signals Module"""
    df = df.copy()
    df['Signal'] = "HOLD / NEUTRAL"
    df['Target_1'] = 0.0
    df['Target_2'] = 0.0
    
    if len(df) < 2:
        return df

    trend_dir = df['Trend_Direction'].values
    close_vals = df['Close'].values
    chand_long = df['Chandelier_Long'].values
    rsi_vals = df['RSI_14'].values
    macd_line = df['MACD_Line'].values
    macd_sig = df['MACD_Signal'].values
    atr_vals = df['ATR_14'].values
    
    # 4-Factor Confluence: SuperTrend + Chandelier Channel + RSI Safety + MACD Crossover
    bullish_confluence = (trend_dir == 1) & (close_vals > chand_long) & (rsi_vals < 65) & (macd_line > macd_sig)
    bearish_confluence = (trend_dir == -1) & (close_vals < chand_long) & (rsi_vals > 35) & (macd_line < macd_sig)
    
    df.loc[bullish_confluence, 'Signal'] = "STRONG_BUY_CALL"
    df.loc[bearish_confluence, 'Signal'] = "STRONG_SELL_CALL"
    
    # Targets calculations using ATR expansion factors
    df['Target_1'] = np.where(bullish_confluence, close_vals + (atr_vals * 1.5), np.where(bearish_confluence, close_vals - (atr_vals * 1.5), 0.0))
    df['Target_2'] = np.where(bullish_confluence, close_vals + (atr_vals * 3.0), np.where(bearish_confluence, close_vals - (atr_vals * 3.0), 0.0))
    return df

# ==========================================
# 3. INTERACTIVE DASHBOARD & SIDEBAR INPUTS
# ==========================================
pd_st.title("⚡ M&M Institutional Multi-Algo Trading Terminal")
pd_st.caption("Pure Quant Alpha Signal Matrix Engine | High Precision Call Desk (No Charts Mode)")
pd_st.markdown("---")

nse_universe = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS", "BHARTIARTL.NS", 
    "SBIN.NS", "LTIM.NS", "HINDUNILVR.NS", "ITC.NS", "LT.NS", "BAJFINANCE.NS",
    "AXISBANK.NS", "KOTAKBANK.NS", "M&M.NS", "TATASTEEL.NS", "NTPC.NS", "POWERGRID.NS",
    "ADANIENT.NS", "COALINDIA.NS", "BPCL.NS", "ONGC.NS", "SUNPHARMA.NS", "DRREDDY.NS",
    "CIPLA.NS", "APOLLOHOSP.NS", "TATAMOTORS.NS", "MARUTI.NS", "EICHERMOT.NS", "HEROMOTOCO.NS",
    "JSWSTEEL.NS", "HINDALCO.NS", "TATACONSUM.NS", "BRITANNIA.NS", "NESTLEIND.NS", "GRASIM.NS",
    "ULTRACEMCO.NS", "TECHM.NS", "WIPRO.NS", "HCLTECH.NS", "ASIANPAINT.NS", "TITAN.NS", 
    "BAJAJ-AUTO.NS", "DIVISLAB.NS", "SBILIFE.NS", "HDFCLIFE.NS", "BAJAJFINSV.NS", "INDUSINDBK.NS"
]

with pd_st.sidebar:
    pd_st.header("🔎 Algo Matrix Controls")
    target_stock = pd_st.selectbox("Select Target Stock Node", nse_universe, index=0)
    time_window = pd_st.selectbox("Time Horizon Interval", ["15m", "30m", "1h", "1d"], index=0)
    capital_allocation = pd_st.number_input("Vault Portfolio Size (INR)", min_value=100000, value=2500000, step=50000)
    max_risk_per_trade = pd_st.slider("Max Execution Risk Per Trade (%)", 0.25, 3.0, 1.0, 0.25)

# Execution Pipeline
raw_stock_data = fetch_ticker_data(symbol=target_stock, period="60d", interval=time_window)

if raw_stock_data.empty:
    pd_st.error("❌ Data Sync Failed. Please verify NSE Exchange parameters or network connectivity.")
else:
    processed_matrix = calculate_quant_matrix(raw_stock_data)
    signal_ledger = generate_execution_signals(processed_matrix)
    latest_tick = signal_ledger.iloc[-1]
    prev_tick = signal_ledger.iloc[-2]
    
    time_col = 'Datetime' if 'Datetime' in signal_ledger.columns else 'Date'

    # ==========================================
    # 4. LIVE ALGO EXECUTION DESK (TOP CLASS ALGO CALLS)
    # ==========================================
    pd_st.subheader("🚨 Institutional Live Signal Desk")
    
    sig_status = str(latest_tick['Signal'])
    entry_price = float(latest_tick['Close'])
    atr_val = float(latest_tick['ATR_14'])
    
    # Calculate Stop Loss based on Signal Type
    if "BUY" in sig_status:
        stop_loss = entry_price - (atr_val * 2.0)
        t1 = float(latest_tick['Target_1'])
        t2 = float(latest_tick['Target_2'])
        display_color = "green"
    elif "SELL" in sig_status:
        stop_loss = entry_price + (atr_val * 2.0)
        t1 = float(latest_tick['Target_1'])
        t2 = float(latest_tick['Target_2'])
        display_color = "red"
    else:
        stop_loss = entry_price - (atr_val * 2.0)
        t1 = entry_price * 1.01
        t2 = entry_price * 1.02
        display_color = "orange"

    # FIXED: Built pure safe HTML using standard concatenation without f-string quote collision
    html_string = '<div style="background-color: #171b26; padding: 25px; border-radius: 10px; border-left: 8px solid ' + display_color + '; margin-bottom: 20px;">'
    html_string += '<h2 style="margin: 0; color: #ffffff;">SYSTEM CALL: <span style="color: ' + display_color + ';">' + sig_status.replace('_', ' ') + '</span></h2>'
    html_string += '<p style="color: #848e9c; margin-top: 5px; font-size: 13px;">Asset ID: ' + str(target_stock) + ' | Generation Timestamp: ' + str(latest_tick[time_col]) + ' (Live Sync)</p>'
    html_string += '<hr style="border: 0; border-top: 1px solid #2a2e39; margin: 15px 0;">'
    html_string += '<div style="display: flex; justify-content: space-between; flex-wrap: wrap; gap: 15px;">'
