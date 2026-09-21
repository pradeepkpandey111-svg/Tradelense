import streamlit as st
import numpy as np
import pandas as pd

st.set_page_config(page_title="TradeAI — Market Intelligence", layout="wide")

st.title("TradeAI — Market Intelligence")
st.caption("Market simulation • Educational & Analytics Prototype")

# Top Metrics Row
col1, col2, col3 = st.columns([1.2, 2, 1])

with col1:
    symbol = st.text_input("Instrument", value="NIFTY 50")
    st.metric(label=symbol, value="25,620.40", delta="+118.20 (+0.46%)")

with col2:
    st.subheader("AI Market View")
    st.write("**Potential bullish setup**")
    st.caption("Price is above VWAP and short-term EMA structure is positive. Confirmation is still required above resistance.")

with col3:
    st.subheader("Setup strength")
    st.metric(label="Score", value="78/100")
    st.caption("4 of 6 conditions aligned • Not a guaranteed prediction")

st.divider()

# Main Layout: Chart & Setup vs Side Scanner
left_col, right_col = st.columns([2, 1])

with left_col:
    # Timeframe selection
    tf = st.radio("Timeframe", ["15m", "1h", "1D", "1W"], horizontal=True)
    
    # Simulated chart line data
    np.random.seed(42)
    chart_data = pd.DataFrame(
        np.random.randn(50, 1).cumsum() + 25500,
        columns=["Price"]
    )
    st.line_chart(chart_data)
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Trend", "Bullish")
    m2.metric("RSI", "61.4")
    m3.metric("VWAP", "25,548")
    m4.metric("ATR", "126.8")
    
    st.subheader("🚦 Trade Signal — POTENTIAL BUY")
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Buy trigger", "25,670")
    s2.metric("Stop loss", "25,520")
    s3.metric("Target 1", "25,820")
    s4.metric("Target 2", "25,950")
    
    # Interactive Trade Risk Calculator
    st.subheader("💰 Trade Risk Calculator")
    c1, c2, c3, c4 = st.columns(4)
    capital = c1.number_input("Capital (₹)", value=100000, step=5000)
    risk_pct = c2.number_input("Risk / trade %", value=1.0, step=0.1)
    entry = c3.number_input("Entry", value=25670)
    sl = c4.number_input("SL", value=25520)
    
    risk_per_unit = abs(entry - sl)
    budget = capital * (risk_pct / 100.0)
    qty = int(budget // risk_per_unit) if risk_per_unit > 0 else 0
    t1, t2 = 25820, 25950
    loss = qty * risk_per_unit
    p1 = qty * abs(t1 - entry)
    p2 = qty * abs(t2 - entry)
    
    st.info(f"**Risk budget:** ₹{budget:,.2f} | **Suggested quantity:** {qty} | **Max loss at SL:** ₹{loss:,.2f} | **Profit @ T1:** ₹{p1:,.2f} | **Profit @ T2:** ₹{p2:,.2f}")

with right_col:
    st.subheader("Market Scanner")
    scanner_df = pd.DataFrame({
        "Stock": ["RELIANCE", "ICICIBANK", "SBIN", "INFY"],
        "Signal": ["LONG", "LONG", "SHORT", "WAIT"],
        "Pattern": ["Breakout watch", "VWAP reclaim", "Support breakdown", "Conflicting signals"],
        "Strength": [81, 76, 73, 48]
    })
    st.dataframe(scanner_df, use_container_width=True, hide_index=True)
    
    st.subheader("Analysis Checklist")
    checks = {
        "Price vs VWAP": "PASS",
        "EMA structure": "PASS",
        "RSI": "PASS",
        "Volume": "PASS",
        "Resistance breakout": "WAIT",
        "Risk/reward": "PASS"
    }
    for item, status in checks.items():
        st.write(f"**{item}:** {status}")

st.divider()

# Signal Engine & Backtest Section
st.subheader("🧪 Signal Engine & Backtest")
b1, b2, b3, b4 = st.columns(4)
min_score = b1.number_input("Minimum score", value=70, min_value=50, max_value=95)
bt_risk = b2.number_input("Risk / trade (%)", value=1.0, step=0.1)
rr = b3.number_input("Reward target (R:R)", value=2.0, step=0.1)
trades = b4.number_input("Lookback trades", value=100, min_value=20, max_value=500)

if st.button("Run signal backtest"):
    wins = int(trades * 0.58)
    losses = trades - wins
    win_rate = (wins / trades) * 100
    avg_r = ((wins * rr) - losses) / trades
    
    res1, res2, res3, res4 = st.columns(4)
    res1.metric("Signals tested", trades)
    res2.metric("Trades taken", trades)
    res3.metric("Demo win rate", f"{win_rate:.1f}%")
    res4.metric("Avg R", f"{avg_r:.2f}R")
    st.caption("Software test using deterministic demo assumptions. Historical validation requires market replay.")
    
