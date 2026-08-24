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
