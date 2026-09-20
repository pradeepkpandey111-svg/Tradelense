import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Page configuration
st.set_page_config(
    page_title="TradeLense Pro Signal Terminal",
    page_icon="⚡",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# High-Contrast Mobile Styling (Fixes invisible dark text)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
    * { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }
    
    .block-container { padding-top: 1rem; padding-bottom: 2rem; padding-left: 0.8rem; padding-right: 0.8rem; }
    
    /* Trade Plan Card */
    .trade-card {
        background: #1e293b;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 14px;
        border-left: 6px solid #3b82f6;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    .bullish-card { border-left-color: #10b981; background: #064e3b22; border: 1px solid #10b98155; }
    .bearish-card { border-left-color: #ef4444; background: #7f1d1d22; border: 1px solid #ef444455; }
    
    .badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 800;
        font-size: 0.85rem;
        letter-spacing: 0.5px;
    }
    .badge-buy { background: #10b981; color: #ffffff; }
    .badge-sell { background: #ef4444; color: #ffffff; }
    .badge-wait { background: #f59e0b; color: #ffffff; }
    
    /* High contrast metrics */
    .matrix-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 8px;
        margin-top: 10px;
    }
    .metric-box {
        background: #0f172a;
        padding: 10px 12px;
        border-radius: 8px;
        border: 1px solid #334155;
    }
    .metric-label {
        font-size: 0.75rem;
        color: #94a3b8;
        font-weight: 600;
        text-transform: uppercase;
    }
    .metric-val {
        font-size: 1.15rem;
        font-weight: 700;
        color: #f8fafc;
        margin-top: 2px;
    }
    .val-green { color: #34d399 !important; }
    .val-red { color: #f87171 !important; }
    .val-blue { color: #60a5fa !important; }
    
    .level-row {
        display: flex;
        justify-content: space-between;
        padding: 6px 0;
        border-bottom: 1px solid #334155;
        font-size: 0.88rem;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("## ⚡ TradeLense Pro Terminal")
st.caption("F&O Algorithmic Confluence & Execution Planner")

# File Upload Drawer
with st.expander("📂 Upload Options Chain & Market History", expanded=True):
    nifty_file = st.file_uploader("1. Share / NIFTY History (CSV)", key="m_hist")
    opt_file = st.file_uploader("2. Option Chain (CSV / XLSX)", key="m_opt")
    
    col_r1, col_r2 = st.columns(2)
    with col_r1:
        rr_ratio = st.selectbox("Target R:R Ratio", [1.5, 2.0, 2.5, 3.0], index=1)
    with col_r2:
        lot_size = st.number_input("Lot / Qty Size", value=50, step=25)
        
    btn_calc = st.button("🚀 Run Deep Trade Analysis", type="primary", use_container_width=True)

# Calculation Core
def load_data(file):
    if file.name.lower().endswith(('.xlsx', '.xls')):
        return pd.read_excel(file)
    return pd.read_csv(file)

def clean_ohlc(df):
    df.columns = [str(c).strip().lower() for c in df.columns]
    time_col = next((c for c in df.columns if 'time' in c or 'date' in c), df.columns[0])
    df = df.rename(columns={time_col: 'time'})
    df['time'] = pd.to_datetime(df['time'], errors='coerce')
    df = df.dropna(subset=['time']).sort_values('time').reset_index(drop=True)

    # Standardize column labels
    for standard in ['open', 'high', 'low', 'close', 'volume']:
        found = next((c for c in df.columns if standard in c or (standard == 'close' and 'ltp' in c)), None)
        if found:
            df[standard] = pd.to_numeric(df[found].astype(str).str.replace(',', ''), errors='coerce')
        else:
            df[standard] = df['close'] if 'close' in df.columns else 0.0

    return df

def compute_indicators(df):
    # EMAs
    df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()

    # RSI (14)
    change = df['close'].diff()
    gain = change.clip(lower=0).rolling(14).mean()
    loss = (-change.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df['rsi'] = 100 - (100 / (1 + rs))
    df['rsi'] = df['rsi'].fillna(50)

    # ATR (14)
    tr = pd.concat([
        df['high'] - df['low'],
        (df['high'] - df['close'].shift()).abs(),
        (df['low'] - df['close'].shift()).abs()
    ], axis=1).max(axis=1)
    df['atr'] = tr.rolling(14).mean().bfill()
    return df

def parse_option_chain(df):
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    call_col = next((c for c in df.columns if 'ce_oi' in c or ('call' in c and 'oi' in c)), None)
    put_col = next((c for c in df.columns if 'pe_oi' in c or ('put' in c and 'oi' in c)), None)
    strike_col = next((c for c in df.columns if 'strike' in c), None)

    if not (call_col and put_col and strike_col):
        return None

    for c in [call_col, put_col, strike_col]:
        df[c] = pd.to_numeric(df[c].astype(str).str.replace(',', ''), errors='coerce').fillna(0)

    total_ce = df[call_col].sum()
    total_pe = df[put_col].sum()
    pcr = round(total_pe / total_ce, 2) if total_ce > 0 else 1.0

    support = df.loc[df[put_col].idxmax(), strike_col]
    resistance = df.loc[df[call_col].idxmax(), strike_col]

    return {
        "pcr": pcr,
        "support": support,
        "resistance": resistance,
        "sentiment": "Bullish (Put Writing Heavy)" if pcr > 1.1 else ("Bearish (Call Writing Heavy)" if pcr < 0.85 else "Neutral / Rangebound")
    }

# Execution Pipeline
if nifty_file:
    try:
        df = clean_ohlc(load_data(nifty_file))
        df = compute_indicators(df)
        
        oc_data = None
        if opt_file:
            try:
                oc_data = parse_option_chain(load_data(opt_file))
            except Exception as e:
                st.warning(f"Option Chain error: {e}")

        # Market Snapshot
        curr = df.iloc[-1]
        prev = df.iloc[-2]
        price = curr['close']
        atr = curr['atr'] if pd.notna(curr['atr']) and curr['atr'] > 0 else (price * 0.006)
        rsi = curr['rsi']
        ema9 = curr['ema9']
        ema21 = curr['ema21']

        # Determine Primary Bias
        bull_votes = 0
        bear_votes = 0
        if ema9 > ema21: bull_votes += 1
        else: bear_votes += 1
        if price > ema21: bull_votes += 1
        else: bear_votes += 1
        if rsi > 52: bull_votes += 1
        elif rsi < 48: bear_votes += 1
        if oc_data:
            if oc_data['pcr'] >= 1.05: bull_votes += 1
            elif oc_data['pcr'] <= 0.85: bear_votes += 1

        is_bullish = bull_votes >= 3
        is_bearish = bear_votes >= 3

        # Suggested Strikes
        atm_strike = round(price / 50) * 50

        # Detailed Signal Badge
        if is_bullish:
            bias_title = "🟢 PRIMARY BIAS: STRONG BULLISH (BUY CE / LONG)"
            card_class = "bullish-card"
            rec_action = f"BUY {int(atm_strike)} CALL (CE)"
        elif is_bearish:
            bias_title = "🔴 PRIMARY BIAS: STRONG BEARISH (BUY PE / SHORT)"
            card_class = "bearish-card"
            rec_action = f"BUY {int(atm_strike)} PUT (PE)"
        else:
            bias_title = "⏸️ PRIMARY BIAS: CONSOLIDATION / NEUTRAL"
            card_class = "trade-card"
            rec_action = f"Wait for Breakout above {price + (0.5*atr):.1f} or Breakdown below {price - (0.5*atr):.1f}"

        st.markdown(f"""
        <div class="trade-card {card_class}">
            <h4 style="margin:0; color:#f8fafc;">{bias_title}</h4>
            <p style="margin:4px 0 0 0; color:#94a3b8; font-size:0.9rem;">
                Action: <b style="color:#ffffff;">{rec_action}</b> | LTP: <b>{price:.2f}</b>
            </p>
        </div>
        """, unsafe_allow_html=True)

        # Tabbed Comprehensive Trade Levels
        tab_long, tab_short, tab_confluence = st.tabs(["📈 Call (CE) Setup", "📉 Put (PE) Setup", "🔍 Indicator Breakdown"])

        with tab_long:
            long_entry = round(price, 2)
            long_sl = round((oc_data['support'] if oc_data and oc_data['support'] < price else price - (1.2 * atr)), 2)
            long_risk = max(long_entry - long_sl, atr * 0.8)
            long_t1 = round(long_entry + (long_risk * 1.0), 2)
            long_t2 = round(long_entry + (long_risk * rr_ratio), 2)
            long_t3 = round(long_entry + (long_risk * (rr_ratio + 1.0)), 2)
            profit_t2 = round((long_t2 - long_entry) * lot_size, 0)
            max_loss = round((long_entry - long_sl) * lot_size, 0)

            st.markdown(f"""
            <div class="matrix-grid">
                <div class="metric-box">
                    <div class="metric-label">Trigger / Entry</div>
                    <div class="metric-val val-blue">{long_entry:.2f}</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">Stop-Loss (SL)</div>
                    <div class="metric-val val-red">{long_sl:.2f}</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">Target 1 (1:1)</div>
                    <div class="metric-val val-green">{long_t1:.2f}</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">Target 2 ({rr_ratio}R)</div>
                    <div class="metric-val val-green">{long_t2:.2f}</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">Max Risk / Lot</div>
                    <div class="metric-val val-red">-₹{max_loss:,.0f}</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">Est. Gain (T2)</div>
                    <div class="metric-val val-green">+₹{profit_t2:,.0f}</div>
                </div>
            </div>
            <br>
            <div class="metric-box">
                <div class="level-row"><span style="color:#94a3b8;">Target 3 (Runner):</span><b>{long_t3:.2f}</b></div>
                <div class="level-row"><span style="color:#94a3b8;">Risk per Share/Index:</span><b>{long_risk:.2f} pts</b></div>
                <div class="level-row"><span style="color:#94a3b8;">Ideal Option Contract:</span><b>{int(atm_strike)} CE</b></div>
            </div>
            """, unsafe_allow_html=True)

        with tab_short:
            short_entry = round(price, 2)
            short_sl = round((oc_data['resistance'] if oc_data and oc_data['resistance'] > price else price + (1.2 * atr)), 2)
            short_risk = max(short_sl - short_entry, atr * 0.8)
            short_t1 = round(short_entry - (short_risk * 1.0), 2)
            short_t2 = round(short_entry - (short_risk * rr_ratio), 2)
            short_t3 = round(short_entry - (short_risk * (rr_ratio + 1.0)), 2)
            profit_short_t2 = round((short_entry - short_t2) * lot_size, 0)
            loss_short = round((short_sl - short_entry) * lot_size, 0)

            st.markdown(f"""
            <div class="matrix-grid">
                <div class="metric-box">
                    <div class="metric-label">Trigger / Entry</div>
                    <div class="metric-val val-blue">{short_entry:.2f}</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">Stop-Loss (SL)</div>
                    <div class="metric-val val-red">{short_sl:.2f}</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">Target 1 (1:1)</div>
                    <div class="metric-val val-green">{short_t1:.2f}</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">Target 2 ({rr_ratio}R)</div>
                    <div class="metric-val val-green">{short_t2:.2f}</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">Max Risk / Lot</div>
                    <div class="metric-val val-red">-₹{loss_short:,.0f}</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">Est. Gain (T2)</div>
                    <div class="metric-val val-green">+₹{profit_short_t2:,.0f}</div>
                </div>
            </div>
            <br>
            <div class="metric-box">
                <div class="level-row"><span style="color:#94a3b8;">Target 3 (Runner):</span><b>{short_t3:.2f}</b></div>
                <div class="level-row"><span style="color:#94a3b8;">Risk per Share/Index:</span><b>{short_risk:.2f} pts</b></div>
                <div class="level-row"><span style="color:#94a3b8;">Ideal Option Contract:</span><b>{int(atm_strike)} PE</b></div>
            </div>
            """, unsafe_allow_html=True)

        with tab_confluence:
            st.markdown(f"""
            <div class="metric-box">
                <div class="level-row"><span>RSI (14 Momentum):</span><b>{rsi:.1f} ({'Bullish (>50)' if rsi > 50 else 'Bearish (<50)'})</b></div>
                <div class="level-row"><span>Fast Trend (EMA 9):</span><b>{ema9:.2f}</b></div>
                <div class="level-row"><span>Slow Trend (EMA 21):</span><b>{ema21:.2f}</b></div>
                <div class="level-row"><span>ATR (Volatility / Candle):</span><b>± {atr:.2f} pts</b></div>
                <div class="level-row"><span>Option Put-Call Ratio:</span><b>{oc_data['pcr'] if oc_data else 'N/A'}</b></div>
                <div class="level-row"><span>Major Support (Max PE OI):</span><b style="color:#34d399;">{oc_data['support'] if oc_data else 'N/A'}</b></div>
                <div class="level-row"><span>Major Resistance (Max CE OI):</span><b style="color:#f87171;">{oc_data['resistance'] if oc_data else 'N/A'}</b></div>
            </div>
            """, unsafe_allow_html=True)

        # High-Contrast Mobile Chart
        st.markdown("### 📊 Interactive Chart View")
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.04, row_heights=[0.72, 0.28])
        
        plot_df = df.tail(50)
        fig.add_trace(go.Candlestick(
            x=plot_df['time'], open=plot_df['open'], high=plot_df['high'], low=plot_df['low'], close=plot_df['close'],
            increasing_line_color='#10b981', decreasing_line_color='#ef4444', name="Price"
        ), row=1, col=1)
        
        fig.add_trace(go.Scatter(x=plot_df['time'], y=plot_df['ema9'], line=dict(color='#f59e0b', width=1.5), name="EMA 9"), row=1, col=1)
        fig.add_trace(go.Scatter(x=plot_df['time'], y=plot_df['ema21'], line=dict(color='#3b82f6', width=1.5), name="EMA 21"), row=1, col=1)

        if oc_data:
            fig.add_hline(y=oc_data['support'], line_dash="dash", line_color="#10b981", annotation_text="Support (Max PE)", row=1, col=1)
            fig.add_hline(y=oc_data['resistance'], line_dash="dash", line_color="#ef4444", annotation_text="Resistance (Max CE)", row=1, col=1)

        fig.add_trace(go.Scatter(x=plot_df['time'], y=plot_df['rsi'], line=dict(color='#a855f7', width=1.5), name="RSI"), row=2, col=1)
        fig.add_hline(y=70, line_dash="dot", line_color="#ef4444", row=2, col=1)
        fig.add_hline(y=30, line_dash="dot", line_color="#10b981", row=2, col=1)

        fig.update_layout(
            height=460,
            margin=dict(l=5, r=5, t=10, b=10),
            xaxis_rangeslider_visible=False,
            template="plotly_dark",
            paper_bgcolor="#0f172a",
            plot_bgcolor="#0f172a",
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    except Exception as e:
        st.error(f"Analysis error: {e}")
else:
    st.info("👆 Tap 'Upload Options Chain & Market History' above, select your files, and tap 'Run Deep Trade Analysis'.")
