import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. Terminal Mobile Config
st.set_page_config(
    page_title="TradeLense Neo Terminal",
    page_icon="⚡",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 2. Modern Cyberpunk / TradingView Dark Styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Plus+Jakarta+Sans:wght@500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
        background-color: #0b0e14;
        color: #f1f5f9;
    }
    
    .block-container {
        padding: 0.8rem 0.6rem 2.5rem 0.6rem;
    }
    
    /* Neon Glow Signal Cards */
    .signal-card {
        background: linear-gradient(145deg, #131822, #182030);
        border-radius: 14px;
        padding: 16px;
        margin-bottom: 14px;
        border: 1px solid #1e293b;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
    }
    .bullish-glow {
        border-top: 4px solid #10b981;
        box-shadow: 0 4px 20px rgba(16, 185, 129, 0.15);
    }
    .bearish-glow {
        border-top: 4px solid #f43f5e;
        box-shadow: 0 4px 20px rgba(244, 63, 94, 0.15);
    }
    .neutral-glow {
        border-top: 4px solid #f59e0b;
    }

    /* Grid Layouts */
    .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 10px; }
    .grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 6px; margin-top: 8px; }

    /* Compact Metric Boxes */
    .box {
        background: #0d121c;
        border-radius: 8px;
        padding: 10px;
        border: 1px solid #1e293b;
    }
    .box-title {
        font-size: 0.68rem;
        font-weight: 700;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .box-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.05rem;
        font-weight: 700;
        margin-top: 2px;
    }
    
    .txt-green { color: #10b981 !important; }
    .txt-red { color: #f43f5e !important; }
    .txt-blue { color: #38bdf8 !important; }
    .txt-amber { color: #fbbf24 !important; }

    .badge-pill {
        display: inline-block;
        padding: 3px 8px;
        font-size: 0.72rem;
        font-weight: 700;
        border-radius: 6px;
        letter-spacing: 0.5px;
    }
    .badge-green { background: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid #10b98144; }
    .badge-red { background: rgba(244, 63, 94, 0.15); color: #f43f5e; border: 1px solid #f43f5e44; }
    
    /* Level row */
    .level-item {
        display: flex;
        justify-content: space-between;
        padding: 5px 0;
        border-bottom: 1px solid #1a2233;
        font-size: 0.84rem;
        font-family: 'JetBrains Mono', monospace;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("### ⚡ TradeLense Neo Terminal")
st.caption("AI Confluence & Multi-Signal Execution Matrix")

# File Upload Drawer
with st.expander("📂 Upload Options Chain & Market History", expanded=True):
    nifty_file = st.file_uploader("1. Share / NIFTY History (CSV)", key="m_hist")
    opt_file = st.file_uploader("2. Option Chain (CSV / XLSX)", key="m_opt")
    
    c1, c2 = st.columns(2)
    with c1:
        rr_choice = st.selectbox("Risk:Reward Target", [1.5, 2.0, 2.5, 3.0], index=1)
    with c2:
        lot_size = st.number_input("Lot Size / Quantity", value=50, step=25)

# --- CORE PARSING & MATHEMATICAL ENGINES ---
def load_file(file):
    if file.name.lower().endswith(('.xlsx', '.xls')):
        return pd.read_excel(file)
    return pd.read_csv(file)

def prepare_ohlc(df):
    df.columns = [str(c).strip().lower() for c in df.columns]
    
    # Locate Date / Time column
    t_col = next((c for c in df.columns if 'time' in c or 'date' in c), df.columns[0])
    df['time'] = pd.to_datetime(df[t_col], errors='coerce')
    df = df.dropna(subset=['time']).sort_values('time').reset_index(drop=True)

    # Standardize OHLCV
    for col in ['open', 'high', 'low', 'close', 'volume']:
        match = next((c for c in df.columns if col in c or (col == 'close' and 'ltp' in c)), None)
        if match:
            df[col] = pd.to_numeric(df[match].astype(str).str.replace(',', ''), errors='coerce')
        else:
            df[col] = df['close'] if 'close' in df.columns else 0.0

    return df

def run_indicators(df):
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

    # Swing Highs & Lows (for Price-Action S/R)
    df['swing_high'] = df['high'].rolling(15).max()
    df['swing_low'] = df['low'].rolling(15).min()

    return df

def robust_option_chain_parser(df):
    """Deep search for call/put columns across different NSE / broker formats"""
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    
    call_col = next((c for c in df.columns if ('ce' in c and 'oi' in c) or ('call' in c and 'oi' in c)), None)
    put_col = next((c for c in df.columns if ('pe' in c and 'oi' in c) or ('put' in c and 'oi' in c)), None)
    strike_col = next((c for c in df.columns if 'strike' in c), None)

    if call_col and put_col and strike_col:
        for c in [call_col, put_col, strike_col]:
            df[c] = pd.to_numeric(df[c].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
        
        ce_sum = df[call_col].sum()
        pe_sum = df[put_col].sum()
        pcr = round(pe_sum / ce_sum, 2) if ce_sum > 0 else 1.0
        
        sup = df.loc[df[put_col].idxmax(), strike_col]
        res = df.loc[df[call_col].idxmax(), strike_col]
        return {"pcr": pcr, "support": float(sup), "resistance": float(res)}
    return None

# --- EXECUTION ENGINE ---
if nifty_file:
    try:
        raw_df = load_file(nifty_file)
        df = prepare_ohlc(raw_df)
        df = run_indicators(df)

        curr = df.iloc[-1]
        prev = df.iloc[-2]
        price = curr['close']
        atr = curr['atr'] if pd.notna(curr['atr']) and curr['atr'] > 0 else (price * 0.005)
        rsi = curr['rsi']
        ema9 = curr['ema9']
        ema21 = curr['ema21']

        # Pivot Points Calculation (High/Low/Close of previous period)
        prev_h = prev['high']
        prev_l = prev['low']
        prev_c = prev['close']
        pivot = (prev_h + prev_l + prev_c) / 3
        r1 = (2 * pivot) - prev_l
        s1 = (2 * pivot) - prev_h
        r2 = pivot + (prev_h - prev_l)
        s2 = pivot - (prev_h - prev_l)

        # Option Chain S/R vs Technical S/R
        oc = None
        if opt_file:
            try:
                oc = robust_option_chain_parser(load_file(opt_file))
            except Exception:
                pass

        # Confluence Support & Resistance Levels
        primary_sup = oc['support'] if oc and oc['support'] < price else round(s1, 1)
        primary_res = oc['resistance'] if oc and oc['resistance'] > price else round(r1, 1)
        atm_strike = int(round(price / 50) * 50)

        # --- SECTION 1: KEY LEVELS SUMMARY BAR ---
        st.markdown(f"""
        <div class="box" style="margin-bottom:12px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <span class="box-title">CURRENT MARKET PRICE (LTP)</span>
                    <div class="box-value txt-blue">{price:.2f}</div>
                </div>
                <div style="text-align:right;">
                    <span class="badge-pill {'badge-green' if rsi > 50 else 'badge-red'}">RSI {rsi:.1f}</span>
                    <span class="badge-pill {'badge-green' if ema9 > ema21 else 'badge-red'}">EMA 9/21 {'BULL' if ema9 > ema21 else 'BEAR'}</span>
                </div>
            </div>
            <div class="grid-3" style="margin-top:8px;">
                <div class="box" style="background:#080b11;">
                    <div class="box-title">SUPPORT (S1 / PE WALL)</div>
                    <div class="box-value txt-green">{primary_sup:.1f}</div>
                </div>
                <div class="box" style="background:#080b11;">
                    <div class="box-title">PIVOT LEVEL</div>
                    <div class="box-value txt-amber">{pivot:.1f}</div>
                </div>
                <div class="box" style="background:#080b11;">
                    <div class="box-title">RESISTANCE (R1 / CE WALL)</div>
                    <div class="box-value txt-red">{primary_res:.1f}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # --- SECTION 2: MULTIPLE ACTIONABLE SIGNALS ---
        st.markdown("#### 🎯 Active Execution Setups")

        # SIGNAL 1: Primary Trend Follower
        is_bullish = ema9 > ema21 and rsi >= 48
        s1_title = f"🟢 SETUP 1: TREND SCALP ({atm_strike} CE)" if is_bullish else f"🔴 SETUP 1: TREND SCALP ({atm_strike} PE)"
        s1_class = "bullish-glow" if is_bullish else "bearish-glow"
        s1_entry = price
        s1_sl = round(price - (1.2 * atr), 1) if is_bullish else round(price + (1.2 * atr), 1)
        s1_risk = abs(s1_entry - s1_sl)
        s1_t1 = round(s1_entry + (s1_risk * 1.0), 1) if is_bullish else round(s1_entry - (s1_risk * 1.0), 1)
        s1_t2 = round(s1_entry + (s1_risk * rr_choice), 1) if is_bullish else round(s1_entry - (s1_risk * rr_choice), 1)
        pnl_s1 = round(s1_risk * rr_choice * lot_size, 0)
        risk_s1 = round(s1_risk * lot_size, 0)

        st.markdown(f"""
        <div class="signal-card {s1_class}">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <b style="font-size:0.95rem;">{s1_title}</b>
                <span class="badge-pill {'badge-green' if is_bullish else 'badge-red'}">MOMENTUM CONFIRMED</span>
            </div>
            <div class="grid-2">
                <div class="box"><div class="box-title">ENTRY TRIGGER</div><div class="box-value txt-blue">{s1_entry:.1f}</div></div>
                <div class="box"><div class="box-title">STOP LOSS</div><div class="box-value txt-red">{s1_sl:.1f}</div></div>
                <div class="box"><div class="box-title">TARGET 1 (SAFE EXIT)</div><div class="box-value txt-green">{s1_t1:.1f}</div></div>
                <div class="box"><div class="box-title">TARGET 2 ({rr_choice}x R:R)</div><div class="box-value txt-green">{s1_t2:.1f}</div></div>
            </div>
            <div style="display:flex; justify-content:space-between; margin-top:10px; font-size:0.85rem; font-family:'JetBrains Mono';">
                <span>Max Risk: <b class="txt-red">-₹{risk_s1:,.0f}</b></span>
                <span>Est. Profit: <b class="txt-green">+₹{pnl_s1:,.0f}</b></span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # SIGNAL 2: Breakout / Breakdown Setup
        breakout_trigger = round(max(primary_res, curr['swing_high']), 1)
        breakdown_trigger = round(min(primary_sup, curr['swing_low']), 1)
        
        st.markdown(f"""
        <div class="signal-card">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <b style="font-size:0.95rem;">⚡ SETUP 2: BREAKOUT / BREAKDOWN RADAR</b>
                <span class="badge-pill" style="background:#334155; color:#94a3b8;">TRIGGER ON CONFIRM</span>
            </div>
            <div class="level-item" style="margin-top:10px;">
                <span>🟢 Bullish Breakout Entry (Above R1):</span>
                <b class="txt-green">> {breakout_trigger}</b>
            </div>
            <div class="level-item">
                <span>↳ Upside Target / Extension:</span>
                <b>{breakout_trigger + (1.5 * atr):.1f} (SL: {breakout_trigger - (0.8 * atr):.1f})</b>
            </div>
            <div class="level-item">
                <span>🔴 Bearish Breakdown Entry (Below S1):</span>
                <b class="txt-red">< {breakdown_trigger}</b>
            </div>
            <div class="level-item">
                <span>↳ Downside Target / Extension:</span>
                <b>{breakdown_trigger - (1.5 * atr):.1f} (SL: {breakdown_trigger + (0.8 * atr):.1f})</b>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # SIGNAL 3: Reversal / Value Area Pullback
        st.markdown(f"""
        <div class="signal-card">
            <b style="font-size:0.95rem;">🔄 SETUP 3: SUPPORT REBOUND / PULLBACK BUY</b>
            <div class="grid-2">
                <div class="box">
                    <div class="box-title">BUY ZONE (ACCUMULATE)</div>
                    <div class="box-value txt-green">{primary_sup:.1f} - {primary_sup + (0.5*atr):.1f}</div>
                </div>
                <div class="box">
                    <div class="box-title">HARD INVALIDATION (SL)</div>
                    <div class="box-value txt-red">< {primary_sup - (0.8*atr):.1f}</div>
                </div>
            </div>
            <div class="level-item" style="margin-top:8px;">
                <span>Take-Profit 1 (Rebound to Pivot):</span>
                <b class="txt-green">{pivot:.1f}</b>
            </div>
            <div class="level-item">
                <span>Take-Profit 2 (Rebound to R1):</span>
                <b class="txt-green">{primary_res:.1f}</b>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # --- SECTION 3: INTERACTIVE MULTI-PANE CHART ---
        st.markdown("#### 📈 Interactive Candlestick Chart")
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.72, 0.28])

        # Plot 45 most recent candles
        sub_df = df.tail(45)
        fig.add_trace(go.Candlestick(
            x=sub_df['time'], open=sub_df['open'], high=sub_df['high'], low=sub_df['low'], close=sub_df['close'],
            increasing_line_color='#10b981', decreasing_line_color='#f43f5e', name="Price"
        ), row=1, col=1)

        # Moving Averages
        fig.add_trace(go.Scatter(x=sub_df['time'], y=sub_df['ema9'], line=dict(color='#38bdf8', width=1.5), name="EMA 9"), row=1, col=1)
        fig.add_trace(go.Scatter(x=sub_df['time'], y=sub_df['ema21'], line=dict(color='#f59e0b', width=1.5), name="EMA 21"), row=1, col=1)

        # Support & Resistance Overlays
        fig.add_hline(y=primary_sup, line_dash="dash", line_color="#10b981", annotation_text=f"Support {primary_sup:.0f}", row=1, col=1)
        fig.add_hline(y=primary_res, line_dash="dash", line_color="#f43f5e", annotation_text=f"Resistance {primary_res:.0f}", row=1, col=1)

        # RSI Panel
        fig.add_trace(go.Scatter(x=sub_df['time'], y=sub_df['rsi'], line=dict(color='#c084fc', width=1.5), name="RSI"), row=2, col=1)
        fig.add_hline(y=70, line_dash="dot", line_color="#f43f5e", row=2, col=1)
        fig.add_hline(y=30, line_dash="dot", line_color="#10b981", row=2, col=1)

        fig.update_layout(
            height=460,
            margin=dict(l=5, r=5, t=10, b=10),
            xaxis_rangeslider_visible=False,
            template="plotly_dark",
            paper_bgcolor="#0b0e14",
            plot_bgcolor="#0b0e14",
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    except Exception as e:
        st.error(f"Analysis failed: {e}")
else:
    st.info("👆 Tap 'Upload Options Chain & Market History' above to begin.")
