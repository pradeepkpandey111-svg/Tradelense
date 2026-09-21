import streamlit as st

# 1. Page Config
st.set_page_config(page_title="TradeLense AI", layout="wide", initial_sidebar_state="collapsed")

# 2. Inject CSS for the Dark Modern Theme (matching your HTML)
st.markdown("""
<style>
    /* Background and text colors */
    .stApp { background-color: #07111f; color: #e8eef7; font-family: 'Inter', sans-serif; }
    header, footer { visibility: hidden; }
    
    /* Style Metric Cards to look like your HTML dashboard */
    div[data-testid="metric-container"] {
        background-color: #0c1929; border: 1px solid #1c2d43; border-radius: 12px;
        padding: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }
    
    /* Input Fields */
    .stNumberInput > div > div > input {
        background-color: #07111f !important; color: white !important;
        border: 1px solid #263a53 !important; border-radius: 8px !important;
    }
    
    /* Execute Button */
    .stButton > button {
        background-color: #176b52; color: white; border: 1px solid #239b73;
        border-radius: 8px; width: 100%; font-weight: bold; padding: 10px;
    }
    .stButton > button:hover { background-color: #1a7a5d; color: white; border-color: #6ee7b7; }
</style>
""", unsafe_allow_html=True)

# 3. Top Banner (Static market state)
st.markdown("### TradeLense AI")
col1, col2, col3 = st.columns([1.5, 2, 1])

with col1:
    st.metric("NIFTY 50 INDICES", "25,620.40", "+118.20 (+0.46%)")
with col2:
    st.markdown("<h4 style='color:#63e6a9; margin-bottom:0;'>Nifty 50 CE Setup Confirmed</h4>", unsafe_allow_html=True)
    st.caption("5-Factor Confluence: EMA 9 > 21, Price > 50 EMA, RSI 52-72, and Breakout.")
with col3:
    st.metric("Factor Alignment", "5 / 5")

st.divider()

# 4. Interactive Calculator (Restoring Yesterday's Functionality)
st.markdown("#### ⚡ Dynamic Lot & Risk Calculator")

in1, in2 = st.columns(2)
with in1:
    capital = st.number_input("Trading Capital (₹)", value=25000, step=1000)
with in2:
    ltp = st.number_input("Option Premium LTP (₹)", value=88.0, step=1.0)

# Dynamic Math Logic (from yesterday)
lot_size = 65
cost_per_lot = ltp * lot_size
lots = max(1, int(capital // cost_per_lot)) if cost_per_lot > 0 else 0
total_qty = lots * lot_size
total_invested = lots * cost_per_lot
sl_price = ltp * 0.85
tp_price = ltp * 1.30
max_risk = total_invested * 0.15
max_profit = total_invested * 0.30

# Display Results Dynamically based on the inputs
r1, r2, r3, r4 = st.columns(4)
r1.metric("Allocated", f"{lots} Lots ({total_qty} Qty)")
r2.metric("Required Capital", f"₹{total_invested:,.2f}")
r3.metric("Stop Loss (-15%)", f"₹{sl_price:.2f}")
r4.metric("Target (+30%)", f"₹{tp_price:.2f}")

r5, r6, r7, r8 = st.columns(4)
r5.metric("LTP Entry", f"₹{ltp:.2f}")
r6.metric("Max Risk", f"-₹{max_risk:,.2f}")
r7.metric("Max Profit", f"+₹{max_profit:,.2f}")
r8.metric("Risk/Reward", "1 : 2.0")

st.write("") # spacing
if st.button("Execute Order via Kite"):
    st.success(f"Order trigger prepared for {lots} lots at ₹{ltp:.2f} with 15% SL attached.")
    
