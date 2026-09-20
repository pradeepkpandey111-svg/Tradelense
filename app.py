import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. Page Configuration & Mobile Layout
st.set_page_config(
    page_title="F&O Signal Mobile",
    page_icon="📈",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("""
    <style>
        .block-container { padding-top: 1rem; padding-bottom: 2rem; padding-left: 0.8rem; padding-right: 0.8rem; }
        .stMetric { background-color: #1e222d; padding: 10px; border-radius: 8px; margin-bottom: 8px; }
        div[data-testid="stMetricValue"] { font-size: 1.3rem !important; }
        .buy-card { background-color: #0e4429; padding: 14px; border-radius: 8px; border: 1px solid #00e676; margin-bottom: 12px; }
        .sell-card { background-color: #4a151b; padding: 14px; border-radius: 8px; border: 1px solid #ff5252; margin-bottom: 12px; }
        .hold-card { background-color: #2a2e39; padding: 14px; border-radius: 8px; margin-bottom: 12px; }
    </style>
""", unsafe_allow_html=True)

st.title("📱 TradeLense Signal Terminal")

# 2. File Upload Section
with st.expander("📂 Tap to Upload Market Data", expanded=True):
    stock_file = st.file_uploader("1. Share History (CSV)", type=["csv"], key="m_stock")
    opt_file = st.file_uploader("2. Option Chain (CSV / XLSX)", type=["csv", "xlsx"], key="m_opt")
    nifty_file = st.file_uploader("3. Nifty 50 History (CSV)", type=["csv"], key="m_nifty")
    
    st.markdown("**Risk Configuration**")
    risk_reward = st.slider("Target Multiplier (R:R)", 1.0, 3.0, 2.0, 0.5)
    atr_mult = st.slider("ATR Multiplier (Stop Loss)", 1.0, 2.5, 1.5, 0.1)

# Pure Pandas Indicator Calculators
def calculate_indicators(df):
    # Exponential Moving Averages
    df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()

    # Relative Strength Index (RSI 14)
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / (loss.replace(0, np.nan))
    df['rsi'] = 100 - (100 / (1 + rs))
    df['rsi'] = df['rsi'].fillna(50)

    # Average True Range (ATR 14)
    tr1 = df['high'] - df['low']
    tr2 = (df['high'] - df['close'].shift()).abs()
    tr3 = (df['low'] - df['close'].shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df['atr'] = tr.rolling(window=14).mean()
    df['atr'] = df['atr'].bfill()
    return df

def clean_history(df):
    df.columns = [c.strip().lower() for c in df.columns]
    rename_map = {'datetime': 'time', 'timestamp': 'time', 'date': 'time'}
    df = df.rename(columns=rename_map)
    df['time'] = pd.to_datetime(df['time'])
    df = df.sort_values('time').reset_index(drop=True)
    for col in ['open', 'high', 'low', 'close', 'volume']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce')
    return df

def process_option_chain(opt_df):
    opt_df.columns = [c.strip().lower().replace(" ", "_") for c in opt_df.columns]
    call_oi = next((c for c in opt_df.columns if 'ce_oi' in c or ('call' in c and 'oi' in c)), None)
    put_oi = next((c for c in opt_df.columns if 'pe_oi' in c or ('put' in c and 'oi' in c)), None)
    strike_col = next((c for c in opt_df.columns if 'strike' in c), None)

    if not all([call_oi, put_oi, strike_col]):
        return None

    for col in [call_oi, put_oi, strike_col]:
        opt_df[col] = pd.to_numeric(opt_df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)

    total_call = opt_df[call_oi].sum()
    total_put = opt_df[put_oi].sum()
    pcr = (total_put / total_call) if total_call > 0 else 1.0

    return {
        "pcr": round(pcr, 2),
        "support": opt_df.loc[opt_df[put_oi].idxmax(), strike_col],
        "resistance": opt_df.loc[opt_df[call_oi].idxmax(), strike_col],
        "sentiment": "Bullish" if pcr >= 1.1 else ("Bearish" if pcr <= 0.8 else "Neutral")
    }

# 3. Main Processing Pipeline
if stock_file:
    try:
        df = clean_history(pd.read_csv(stock_file))
        df = calculate_indicators(df)

        oc_data = None
        if opt_file:
            opt_raw = pd.read_excel(opt_file) if opt_file.name.endswith('.xlsx') else pd.read_csv(opt_file)
            oc_data = process_option_chain(opt_raw)

        nifty_sentiment = "Neutral"
        if nifty_file:
            n_df = clean_history(pd.read_csv(nifty_file))
            n_df['ema21'] = n_df['close'].ewm(span=21, adjust=False).mean()
            nifty_sentiment = "Bullish" if n_df.iloc[-1]['close'] > n_df.iloc[-1]['ema21'] else "Bearish"

        curr = df.iloc[-1]
        prev = df.iloc[-2]
        price = curr['close']
        atr = curr['atr'] if pd.notna(curr['atr']) else (price * 0.01)

        ema_bull = curr['ema9'] > curr['ema21']
        ema_cross_up = (prev['ema9'] <= prev['ema21']) and ema_bull
        rsi_bull = 50 <= curr['rsi'] <= 70
        fno_buy = (oc_data is None) or (oc_data['sentiment'] in ["Bullish", "Neutral"] and price >= oc_data['support'])

        ema_bear = curr['ema9'] < curr['ema21']
        ema_cross_down = (prev['ema9'] >= prev['ema21']) and ema_bear
        rsi_bear = 30 <= curr['rsi'] <= 50
        fno_sell = (oc_data is None) or (oc_data['sentiment'] in ["Bearish", "Neutral"] and price <= oc_data['resistance'])

        signal = "NO SIGNAL / HOLD"
        entry, sl, target = price, 0.0, 0.0

        if (ema_cross_up or (ema_bull and rsi_bull)) and fno_buy:
            signal = "BUY"
            sl_cand = oc_data['support'] if (oc_data and oc_data['support'] < price) else (price - (atr_mult * atr))
            sl = round(min(sl_cand, price - (0.5 * atr)), 2)
            risk = entry - sl
            target = round(entry + (risk * risk_reward), 2)
        elif (ema_cross_down or (ema_bear and rsi_bear)) and fno_sell:
            signal = "SELL"
            sl_cand = oc_data['resistance'] if (oc_data and oc_data['resistance'] > price) else (price + (atr_mult * atr))
            sl = round(max(sl_cand, price + (0.5 * atr)), 2)
            risk = sl - entry
            target = round(entry - (risk * risk_reward), 2)

        # 4. Result Displays
        if signal == "BUY":
            st.markdown(f"""
                <div class="buy-card">
                    <h3 style="margin:0; color:#00e676;">🟢 STRONG BUY SIGNAL</h3>
                    <p style="margin:4px 0 0 0;">LTP: <b>{price:.2f}</b> | Confluence: EMA + RSI + F&O Support</p>
                </div>
            """, unsafe_allow_html=True)
        elif signal == "SELL":
            st.markdown(f"""
                <div class="sell-card">
                    <h3 style="margin:0; color:#ff5252;">🔴 STRONG SELL SIGNAL</h3>
                    <p style="margin:4px 0 0 0;">LTP: <b>{price:.2f}</b> | Confluence: EMA + RSI + F&O Resistance</p>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
                <div class="hold-card">
                    <h3 style="margin:0; color:#b2b5be;">⏸️ NO TRADE / HOLD</h3>
                    <p style="margin:4px 0 0 0;">LTP: <b>{price:.2f}</b> | Waiting for confluence confirmation</p>
                </div>
            """, unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        c1.metric("Entry Level", f"{entry:.2f}")
        c2.metric("Stop Loss", f"{sl:.2f}" if signal != "NO SIGNAL / HOLD" else "-")

        c3, c4 = st.columns(2)
        c3.metric("Target Exit", f"{target:.2f}" if signal != "NO SIGNAL / HOLD" else "-")
        pnl_pts = f"+{(abs(target - entry)):.2f} / -{(abs(entry - sl)):.2f}" if signal != "NO SIGNAL / HOLD" else "-"
        c4.metric("Est. P&L", pnl_pts)

        if oc_data:
            st.markdown(f"**Levels:** 🟢 Support: `{oc_data['support']}` | 🔴 Resistance: `{oc_data['resistance']}` | PCR: `{oc_data['pcr']}`")

        # 5. Mobile Candlestick Chart
        st.markdown("### Chart & Indicators")
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
        
        plot_df = df.tail(45)
        fig.add_trace(go.Candlestick(
            x=plot_df['time'], open=plot_df['open'], high=plot_df['high'], low=plot_df['low'], close=plot_df['close'], name="Price"
        ), row=1, col=1)
        fig.add_trace(go.Scatter(x=plot_df['time'], y=plot_df['ema9'], line=dict(color='orange', width=1), name="EMA 9"), row=1, col=1)
        fig.add_trace(go.Scatter(x=plot_df['time'], y=plot_df['ema21'], line=dict(color='#2196f3', width=1), name="EMA 21"), row=1, col=1)

        if oc_data:
            fig.add_hline(y=oc_data['support'], line_dash="dash", line_color="green", row=1, col=1)
            fig.add_hline(y=oc_data['resistance'], line_dash="dash", line_color="red", row=1, col=1)

        fig.add_trace(go.Scatter(x=plot_df['time'], y=plot_df['rsi'], line=dict(color='#ba68c8', width=1), name="RSI"), row=2, col=1)
        fig.add_hline(y=70, line_dash="dot", line_color="red", row=2, col=1)
        fig.add_hline(y=30, line_dash="dot", line_color="green", row=2, col=1)

        fig.update_layout(
            height=420,
            margin=dict(l=5, r=5, t=10, b=10),
            xaxis_rangeslider_visible=False,
            template="plotly_dark",
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    except Exception as e:
        st.error(f"Error parsing uploaded files: {e}")
else:
    st.info("👆 Tap the upload box above to load your stock CSV and begin analysis.")
