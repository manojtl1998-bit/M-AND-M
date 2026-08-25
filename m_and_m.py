import streamlit as pd_st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ==========================================
# 1. SYSTEM CONFIGURATION & FIXED DARK THEME
# ==========================================
pd_st.set_page_config(
    page_title="M&M Institutional Quant Terminal",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Premium Full-Width Layout & Zero-Padding Configuration
pd_st.markdown("""
    <style>
        html, body, [data-testid="stAppViewContainer"] { 
            background-color: #0b0f19 !important; 
            color: #f0f2f5 !important; 
        }
        .block-container {
            max-width: 100% !important;
            padding-left: 1.5rem !important;
            padding-right: 1.5rem !important;
            padding-top: 1.5rem !important;
            padding-bottom: 1.5rem !important;
        }
        h1, h2, h3 { color: #ffffff !important; font-family: 'Inter', sans-serif; }
        div[data-testid="stMetricValue"] { color: #00e676 !important; font-weight: bold; font-size: 24px !important; }
        .stDataFrame div { background-color: #12161a !important; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. DATA ENGINE & CORE QUANT OPERATIONS
# ==========================================
@pd_st.cache_data(ttl=600)
def fetch_ticker_data(symbol: str, period: str = "60d", interval: str = "15m"):
    """Fetches real-time institutional data feeds from yfinance with safe flattening"""
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
    """Executes Vectorized Quant Passes with absolute 1D array flattening"""
    df = df.copy()
    if len(df) < 30:
        return df

    close_ser = pd.Series(df['Close'].values.flatten(), name='Close')
    high_ser = pd.Series(df['High'].values.flatten(), name='High')
    low_ser = pd.Series(df['Low'].values.flatten(), name='Low')

    # Core Vector Calculations
    close_delta = close_ser.diff()
    gain = (close_delta.clip(lower=0)).rolling(window=14).mean()
    loss = (-close_delta.clip(upper=0)).rolling(window=14).mean()
    rs = gain / (loss + 1e-10)
    df['RSI_14'] = (100 - (100 / (1 + rs))).values

    # MACD Setup
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

    # SuperTrend Loop Integration
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
    """Confluence Framework (SuperTrend + Chandelier Reversal + RSI Filter)"""
    df = df.copy()
    df['Signal'] = "HOLD"
    
    if len(df) < 2:
        return df

    trend_dir = df['Trend_Direction'].values
    close_vals = df['Close'].values
    chand_long = df['Chandelier_Long'].values
    rsi_vals = df['RSI_14'].values
    
    bullish_confluence = (trend_dir == 1) & (close_vals > chand_long) & (rsi_vals < 68)
    bearish_confluence = (trend_dir == -1) & (close_vals < chand_long) & (rsi_vals > 32)
    
    df.loc[bullish_confluence, 'Signal'] = "INSTITUTIONAL_BUY"
    df.loc[bearish_confluence, 'Signal'] = "INSTITUTIONAL_SHORT"
    return df

# ==========================================
# 3. INTERACTIVE DASHBOARD & SIDEBAR INPUTS
# ==========================================
pd_st.title("📊 M&M Institutional Quant Terminal")
pd_st.caption("Advanced Alpha Matrix & Global Risk Infrastructure | Version 3.0")
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
    pd_st.header("🔎 Quant Parameters")
    target_stock = pd_st.selectbox("Select Asset Architecture", nse_universe, index=0)
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

    # Market Indicators Row
    m1, m2, m3, m4 = pd_st.columns(4)
    price_delta = ((float(latest_tick['Close']) - float(prev_tick['Close'])) / float(prev_tick['Close'])) * 100
    m1.metric("LTP (Last Traded Price)", f"₹{float(latest_tick['Close']):.2f}", f"{price_delta:+.2f}%")
    m2.metric("RSI (14 Vectors)", f"{float(latest_tick['RSI_14']):.2f}", "Neutral" if 30 <= float(latest_tick['RSI_14']) <= 70 else "Extreme")
    m3.metric("ATR Volatility Span", f"₹{float(latest_tick['ATR_14']):.2f}")
    m4.metric("Active Algo Signal", str(latest_tick['Signal']))

    pd_st.markdown("---")

    # ==========================================
    # 4. HIGH-PERFORMANCE PLOTLY CANDLESTICK MATRIX (VISIBLE)
    # ==========================================
    pd_st.subheader("📈 Institutional Candlestick Matrix & Chandelier Momentum Line")
    
    chart_df = signal_ledger.tail(60).copy()
    time_col = 'Datetime' if 'Datetime' in chart_df.columns else 'Date'
    
    fig = go.Figure()
    
    # Add Candlesticks
    fig.add_trace(go.Candlestick(
        x=chart_df[time_col].values.flatten(),
        open=chart_df['Open'].values.flatten(),
        high=chart_df['High'].values.flatten(),
        low=chart_df['Low'].values.flatten(),
        close=chart_df['Close'].values.flatten(),
        name='Price Feed',
        increasing_line_color='#00e676',
        decreasing_line_color='#ff1744',
        increasing_fillcolor='#00e676',
        decreasing_fillcolor='#ff1744'
    ))
    
    # Add Chandelier Target Line Overlay
    fig.add_trace(go.Scatter(
        x=chart_df[time_col].values.flatten(),
        y=chart_df['Chandelier_Long'].values.flatten(),
        mode='lines',
        name='Chandelier Line',
        line=dict(color='#ffea00', width=2)
    ))
    
    fig.update_layout(
        plot_bgcolor='#0b0f19',
        paper_bgcolor='#0b0f19',
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(
            gridcolor='#1e2638',
            tickfont=dict(color='#8892b0'),
            rangeslider=dict(visible=False)
        ),
        yaxis=dict(
            gridcolor='#1e2638',
            tickfont=dict(color='#8892b0'),
            side='right'
        ),
        legend=dict(font=dict(color='#ffffff')),
        height=450
    )
    
    pd_st.plotly_chart(fig, use_container_width=True)

    pd_st.markdown("---")

    # ==========================================
    # 5. PORTFOLIO RISK MATRIX GRID
    # ==========================================
    pd_st.subheader("🛡️ Institutional Risk Matrix & Automated Sizing Ledger")
    
    entry_price = float(latest_tick['Close'])
    atr_value = float(latest_tick['ATR_14'])
    stop_loss = entry_price - (atr_value * 2.0)
