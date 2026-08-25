import streamlit as pd_st
import pandas as pd
import numpy as np
import yfinance as yf
import altair as alt
from datetime import datetime, timedelta

# ==========================================
# 1. SYSTEM CONFIGURATION & GROWW DARK THEME
# ==========================================
pd_st.set_page_config(
    page_title="M&M Institutional Quant Terminal",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Premium Groww Dark Theme Palette
pd_st.markdown("""
    <style>
        .reportview-container { background: #0b0e11; color: #9aa0a6; }
        .sidebar .sidebar-content { background: #12161a; }
        h1, h2, h3 { color: #ffffff !important; font-family: 'Inter', sans-serif; }
        div[data-testid="stMetricValue"] { color: #00d09c !important; font-size: 24px !important; font-weight: 700; }
        div[data-testid="stMetricDelta"] { color: #eb5b3c !important; }
        .stButton>button { background-color: #00d09c; color: #ffffff; border-radius: 6px; border: none; font-weight: bold;}
        .stButton>button:hover { background-color: #00b386; color: #ffffff; }
        div.block-container { padding-top: 2rem; padding-bottom: 2rem; }
    </style>
""", unsafe_style_html=True)

# ==========================================
# 2. DATA ENGINE & CORE QUANT OPERATIONS
# ==========================================
@pd_st.cache_data(ttl=600)
def fetch_ticker_data(symbol: str, period: str = "60d", interval: str = "15m"):
    """Fetches real-time institutional data feeds from yfinance"""
    try:
        raw_df = yf.download(tickers=symbol, period=period, interval=interval)
        if raw_df.empty:
            return pd.DataFrame()
        # Clean multi-index columns if any
        if isinstance(raw_df.columns, pd.MultiIndex):
            raw_df.columns = raw_df.columns.get_level_values(0)
        return raw_df.reset_index()
    except Exception:
        return pd.DataFrame()

def calculate_quant_matrix(df: pd.DataFrame):
    """Executes Vectorized Quant Passes: RSI, MACD, ATR, SuperTrend, and Chandelier Exit"""
    df = df.copy()
    if len(df) < 30:
        return df

    # Core Vector Calculations
    close_delta = df['Close'].diff()
    gain = (close_delta.clip(lower=0)).rolling(window=14).mean()
    loss = (-close_delta.clip(upper=0)).rolling(window=14).mean()
    rs = gain / (loss + 1e-10)
    df['RSI_14'] = 100 - (100 / (1 + rs))

    # MACD Setup
    df['EMA_12'] = df['Close'].ewm(span=12, adjust=False).mean()
    df['EMA_26'] = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD_Line'] = df['EMA_12'] - df['EMA_26']
    df['MACD_Signal'] = df['MACD_Line'].ewm(span=9, adjust=False).mean()

    # ATR Matrix
    df['H-L'] = df['High'] - df['Low']
    df['H-PC'] = (df['High'] - df['Close'].shift(1)).abs()
    df['L-PC'] = (df['Low'] - df['Close'].shift(1)).abs()
    df['TR'] = df[['H-L', 'H-PC', 'L-PC']].max(axis=1)
    df['ATR_14'] = df['TR'].rolling(window=14).mean()

    # [NEW QUANT INDICATOR] Institutional Chandelier Momentum Channel
    df['Highest_High_22'] = df['High'].rolling(window=22).max()
    df['Chandelier_Long'] = df['Highest_High_22'] - (df['ATR_14'] * 3.0)

    # SuperTrend Loop Integration
    st_atr = df['ATR_14'] * 3.0
    hl2 = (df['High'] + df['Low']) / 2
    df['Basic_UB'] = hl2 + st_atr
    df['Basic_LB'] = hl2 - st_atr
    
    # Fast vectorized allocation for bounds
    ub_arr, lb_arr = df['Basic_UB'].values, df['Basic_LB'].values
    close_arr = df['Close'].values
    st_arr = np.zeros(len(df))
    dir_arr = np.ones(len(df)) # 1 for bull, -1 for bear

    for i in range(1, len(df)):
        if close_arr[i-1] > ub_arr[i-1]:
            dir_arr[i] = 1
        elif close_arr[i-1] < lb_arr[i-1]:
            dir_arr[i] = -1
        else:
            dir_arr[i] = dir_arr[i-1]
            if dir_arr[i] == 1 and lb_arr[i] < lb_arr[i-1]: lb_arr[i] = lb_arr[i-1]
            if dir_arr[i] == -1 and ub_arr[i] > ub_arr[i-1]: ub_arr[i] = ub_arr[i-1]
        st_arr[i] = lb_arr[i] if dir_arr[i] == 1 else ub_arr[i]

    df['SuperTrend'] = st_arr
    df['Trend_Direction'] = dir_arr
    return df

def generate_execution_signals(df: pd.DataFrame):
    """[NEW TRADING STRATEGY] Confluence Framework (SuperTrend + Chandelier Reversal + RSI Filter)"""
    df = df.copy()
    df['Signal'] = "HOLD"
    
    if len(df) < 2:
        return df

    # Vectorized conditional masks
    bullish_confluence = (df['Trend_Direction'] == 1) & (df['Close'] > df['Chandelier_Long']) & (df['RSI_14'] < 68)
    bearish_confluence = (df['Trend_Direction'] == -1) & (df['Close'] < df['Chandelier_Long']) & (df['RSI_14'] > 32)
    
    df.loc[bullish_confluence, 'Signal'] = "INSTITUTIONAL_BUY"
    df.loc[bearish_confluence, 'Signal'] = "INSTITUTIONAL_SHORT"
    return df

# ==========================================
# 3. INTERACTIVE DASHBOARD & SIDEBAR INPUTS
# ==========================================
pd_st.title("📊 M&M Institutional Quant Terminal")
pd_st.caption("Live Alpha Generation Engine & Portfolio Risk Matrix | Institutional Grade v2.0")
pd_st.markdown("---")

# 70+ Internal NSE Stocks Database Node
nse_universe = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS", "BHARTIARTL.NS", 
    "SBI-N.NS", "LTIM.NS", "HITC.NS", "HINDUNILVR.NS", "ITC.NS", "LT.NS", "BAJFINANCE.NS",
    "AXISBANK.NS", "KOTAKBANK.NS", "M&M.NS", "TATASTEEL.NS", "NTPC.NS", "POWERGRID.NS",
    "ADANIENT.NS", "COALINDIA.NS", "BPCL.NS", "ONGC.NS", "SUNPHARMA.NS", "DRREDDY.NS",
    "CIPLA.NS", "APOLLOHOSP.NS", "TATAMOTORS.NS", "MARUTI.NS", "EICHERMOT.NS", "HEROMOTOCO.NS",
    "JSWSTEEL.NS", "HINDALCO.NS", "TATACONSUM.NS", "BRITANNIA.NS", "NESTLEIND.NS", "GRASIM.NS",
    "ULTRACEMCO.NS", "TECHM.NS", "WIPRO.NS", "HCLTECH.NS", "ASIANPAINT.NS", "TITAN.NS", 
    "BAJAJ-AUTO.NS", "DIVISLAB.NS", "SBILIFE.NS", "HDFCLIFE.NS", "BAJAJFINSV.NS", "INDUSINDBK.NS"
]

with pd_st.sidebar:
    pd_st.header("🔎 Quant Parameters")
    target_stock = pd_st.selectbox("Select Asset Asset Architecture", nse_universe, index=0)
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
    price_delta = ((latest_tick['Close'] - prev_tick['Close']) / prev_tick['Close']) * 100
    m1.metric("LTP (Last Traded Price)", f"₹{latest_tick['Close']:.2f}", f"{price_delta:+.2f}%")
    m2.metric("RSI (14 Vectors)", f"{latest_tick['RSI_14']:.2f}", "Neutral" if 30 <= latest_tick['RSI_14'] <= 70 else "Extreme")
    m3.metric("ATR Volatility Span", f"₹{latest_tick['ATR_14']:.2f}")
    m4.metric("Active Algo Signal", str(latest_tick['Signal']))

    pd_st.markdown("---")

    # ==========================================
    # 4. WICK-PERFECT ALTAIR CANDLESTICK CHART (UI IMPROVED)
    # ==========================================
    pd_st.subheader("📈 Institutional Candlestick Matrix & Chandelier Band")
    
    base_chart = alt.Chart(signal_ledger.tail(100)).encode(
        x=alt.X('Datetime:T' if 'Datetime' in signal_ledger.columns else 'Date:T', title="Timeline Matrix"),
        color=alt.condition("datum.Open <= datum.Close", alt.value("#00d09c"), alt.value("#eb5b3c")) # Groww Bull/Bear Palette
    )

    # Wick Layer
    rule_layer = base_chart.mark_rule(opacity=0.7).encode(
        y=alt.Y('Low:Q', scale=alt.Scale(zero=False)),
        y2='High:Q'
    )

    # Candle Body Layer
    bar_layer = base_chart.mark_bar().encode(
        y='Open:Q',
        y2='Close:Q'
    )

    # Chandelier Trailing Band Overlap
    chandelier_layer = alt.Chart(signal_ledger.tail(100)).mark_line(
        color='#ffb703', strokeDash=[4, 4], strokeWidth=2
    ).encode(
        x='Datetime:T' if 'Datetime' in signal_ledger.columns else 'Date:T',
        y='Chandelier_Long:Q'
    )

    integrated_terminal_chart = alt.layer(rule_layer, bar_layer, chandelier_layer).properties(
        width=1100, height=450
    ).configure_axis(
        gridColor='#1f262e', labelColor='#9aa0a6', titleColor='#ffffff'
    ).configure_view(
        strokeOpacity=0
    )

    pd_st.altair_chart(integrated_terminal_chart, use_container_width=True)

    pd_st.markdown("---")

    # ==========================================
    # 5. [NEW FEATURE] PORTFOLIO RISK MATRIX GRID
    # ==========================================
    pd_st.subheader("🛡️ Institutional Risk Matrix & Automated Sizing Ledger")
    
    # Real-Time Risk Processing Engine Calculations via Risk Matrix Rules
    entry_price = latest_tick['Close']
    atr_value = latest_tick['ATR_14']
    stop_loss = entry_price - (atr_value * 2.0)
    risk_rupees = capital_allocation * (max_risk_per_trade / 100.0)
    per_share_risk = entry_price - stop_loss
    
    # Check for divide by zero safety
    allocated_position_size = int(risk_rupees / per_share_risk) if per_share_risk > 0 else 0
    total_trade_commitment = allocated_position_size * entry_price
    leverage_multiple = total_trade_commitment / capital_allocation

    # UI Grid Display
    r1, r2, r3, r4 = pd_st.columns(4)
    with r1:
        pd_st.info("**Absolute Risk Buffer**")
        pd_st.markdown(f"### ₹{risk_rupees:,.2f}")
        pd_st.caption(f"Strict {max_risk_per_trade}% configuration threshold limit.")
    with r2:
