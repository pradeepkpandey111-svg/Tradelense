import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. Page Configuration
st.set_page_config(
    page_title="TradeLense Pro",
    page_icon="⚡",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 2. Modern Mobile Styling (Fixed Headers & High-Contrast Typography)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@500;700;800&family=Plus+Jakarta+Sans:wght@600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
        background-color: #0b0e14;
        color: #f1f5f9;
    }
    
    /* Responsive header to prevent cropping */
    .app-header {
        margin-top: -0.5rem;
        margin-bottom: 0.8rem;
    }
    .app-title {
        font-size: 1.45rem !important;
        font-weight: 800;
        letter-spacing: -0.5px;
        color: #ffffff;
        margin: 0;
        line-height: 1.2;
    }
    .app-subtitle {
        font-size: 0.78rem;
        color: #94a3b8;
        font-weight: 600;
        margin-top: 2px;
    }

    .block-container {
        padding-top: 1rem;
        padding-bottom: 2rem;
        padding-left: 0.6rem;
        padding-right: 0.6rem;
    }
    
    /* Glowing Execution Action Cards */
    .signal-card {
        background: linear-gradient(145deg, #111722, #182030);
        border-radius: 12px;
        padding: 14px;
        margin-bottom: 12px;
        border: 1px solid #1e293b;
    }
    .call-card {
        border-left: 5px solid #10b981;
        background: linear-gradient(145deg, #07271e, #0e372b);
        border-top: 1px solid #10b98144;
    }
    .put-card {
        border-left: 5px solid #f43f5e;
        background: linear-gradient(145deg, #2b0b12, #3d121c);
        border-top: 1px solid #f43f5e44;
    }

    /* Grid Layouts */
    .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin-top: 8px; }
    .grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 6px; margin-top: 6px; }

    /* Compact Stat Boxes */
    .box {
        background: #0d121c;
        border-radius: 8px;
        padding: 8px 10px;
        border: 1px solid #1e293b;
    }
    .box-title {
        font-size: 0.65rem;
        font-weight: 700;
        color: #94a3b8;
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
        padding: 4px 8px;
        font-size: 0.72rem;
        font-weight: 800;
        border-radius: 6px;
    }
    .badge-green { background: #10b981; color: #ffffff; }
    .badge-red { background: #f43f5e; color: #ffffff; }
    
    .level-item {
        display: flex;
        justify-content: space-between;
        padding: 6px 0;
        border-bottom: 1px solid #1f293d;
        font-size: 0.82rem;
        font-family: 'JetBrains Mono', monospace;
    }
</style>

<div class="app-header">
    <div class="app-title">⚡ TradeLense Pro</div>
    <div class="app-subtitle">NIFTY & F&O Signal Terminal (CE / PE Planner)</div>
</div>
""", unsafe_allow_html=True)

# 3. File Upload Drawer
with st.expander("📂 Tap to Upload Market Data", expanded=True):
    nifty_file = st.file_uploader("1. Share / NIFTY History (CSV)", key="m_hist")
    opt_file = st.file_uploader("2. Option Chain (CSV / XLSX)", key="m_opt")
    
    c1, c2 = st.columns(2)
    with c1:
        rr_choice = st.selectbox("Target Multiplier", [1.5, 2.0, 2.5, 3.0], index=1)
    with c2:
        lot_size = st.number_input("Lot / Qty Size", value=50, step=25)

# Helper: Parse OHLC
def prepare_ohlc(file):
    if file.name.lower().endswith(('.xlsx', '.xls')):
        df = pd.read_excel(file)
    else:
        df = pd.read_csv(file)
        
    df.columns = [str(c).strip().lower() for c in df.columns]
    t_col = next((c for c in df.columns if 'time' in c or 'date' in c), df.columns[0])
    df['time'] = pd.to_datetime(df[t_col], errors='coerce')
    df = df.dropna(subset=['time']).sort_values('time').reset_index(drop=True)

    for col in ['open', 'high', 'low', 'close', 'volume']:
        match = next((c for c in df.columns if col in c or (col == 'close' and 'ltp' in c)), None)
        if match:
            df[col] = pd.to_numeric(df[match].astype(str).str.replace(',', ''), errors='coerce')
        else:
            df[col] = df['close'] if 'close' in df.columns else 0.0

    return df

# Helper: Technical Indicators
def run_indicators(df):
    df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
    
    # RSI 14
    change = df['close'].diff()
    gain = change.clip(lower=0).rolling(14).mean()
    loss = (-change.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df['rsi'] = 100 - (100 / (1 + rs))
    df['rsi'] = df['rsi'].fillna(50)

    # ATR 14
    tr = pd.concat([
        df['high'] - df['low'],
        (df['high'] - df['close'].shift()).abs(),
        (df['low'] - df['close'].shift()).abs()
    ], axis=1).max(axis=1)
    df['atr'] = tr.rolling(14).mean().bfill()
    return df

# Helper: Flexible Option Chain Parser
def robust_option_chain_parser(file):
    if file.name.lower().endswith(('.xlsx', '.xls')):
        df = pd.read_excel(file)
    else:
        df = pd.read_csv(file)
        
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

# 4. Main Processing Engine
if nifty_file:
    try:
        df = prepare_ohlc(nifty_file)
        df = run_indicators(df)

        curr = df.iloc[-1]
        prev = df.iloc[-2]
        price = curr['close']
        atr = curr['atr'] if pd.notna(curr['atr']) and curr['atr'] > 0 else (price * 0.005)
        rsi = curr['rsi']
        ema9 = curr['ema9']
        ema21 = curr['ema21']

        # Pivot Floor Points
        prev_h, prev_l, prev_c = prev['high'], prev['low'], prev['close']
        pivot = (prev_h + prev_l + prev_c) / 3
        r1 = (2 * pivot) - prev_l
        s1 = (2 * pivot) - prev_h

        # Option Chain S/R fallback
        oc = None
        if opt_file:
            try:
                oc = robust_option_chain_parser(opt_file)
            except Exception:
                pass

        primary_sup = oc['support'] if oc and oc['support'] < price else round(s1, 1)
        primary_res = oc['resistance'] if oc and oc['resistance'] > price else round(r1, 1)
        
        # Determine ATM strike (Nearest 50 for Nifty)
        atm_strike = int(round(price / 50) * 50)
        call_strike_name = f"{atm_strike} CE"
        put_strike_name = f"{atm_strike} PE"

        # Confluence Score
        bull_score = 0
        bear_score = 0
        if ema9 > ema21: bull_score += 1
        else: bear_score += 1
        if rsi >= 50: bull_score += 1
        else: bear_score += 1
        if price >= pivot: bull_score += 1
        else: bear_score += 1
        if oc and oc['pcr'] >= 1.0: bull_score += 1
        elif oc: bear_score += 1

        primary_is_bull = bull_score >= bear_score

        # --- TOP LEVEL DASHBOARD ---
        st.markdown(f"""
        <div class="box" style="margin-bottom:12px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <span class="box-title">CURRENT NIFTY PRICE</span>
                    <div class="box-value txt-blue">{price:.2f}</div>
                </div>
                <div style="text-align:right;">
                    <span class="badge-pill {'badge-green' if primary_is_bull else 'badge-red'}">
                        { 'BUY CE (BULLISH)' if primary_is_bull else 'BUY PE (BEARISH)' }
                    </span>
                </div>
            </div>
            <div class="grid-3" style="margin-top:6px;">
                <div class="box" style="background:#080b11;">
                    <div class="box-title">SUPPORT (PE WALL)</div>
                    <div class="box-value txt-green">{primary_sup:.0f}</div>
                </div>
                <div class="box" style="background:#080b11;">
                    <div class="box-title">PIVOT LEVEL</div>
                    <div class="box-value txt-amber">{pivot:.0f}</div>
                </div>
                <div class="box" style="background:#080b11;">
                    <div class="box-title">RESISTANCE (CE WALL)</div>
                    <div class="box-value txt-red">{primary_res:.0f}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("#### 🎯 Execution Trade Setups")

        # --- SETUP 1: CALL (CE) TRADE PLAN ---
        ce_entry = round(price, 1)
        ce_sl = round(max(primary_sup, price - (1.2 * atr)), 1)
        ce_risk_pts = round(max(ce_entry - ce_sl, atr * 0.8), 1)
        ce_t1 = round(ce_entry + ce_risk_pts, 1)
        ce_t2 = round(ce_entry + (ce_risk_pts * rr_choice), 1)
        ce_t3 = round(ce_entry + (ce_risk_pts * (rr_choice + 1.0)), 1)
        ce_gain_rs = round(ce_risk_pts * rr_choice * lot_size, 0)
        ce_loss_rs = round(ce_risk_pts * lot_size, 0)

        st.markdown(f"""
        <div class="signal-card call-card">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <b style="color:#10b981; font-size:1.05rem;">🟢 OPTION SETUP 1: BUY CALL ({call_strike_name})</b>
                <span class="badge-pill badge-green">UPSIDE SETUP</span>
            </div>
            <p style="margin:4px 0 0 0; color:#cbd5e1; font-size:0.85rem;">
                <b>Trade Rule:</b> Buy <b>{call_strike_name}</b> if Nifty sustains above <b>{ce_entry:.1f}</b>
            </p>
            <div class="grid-2">
                <div class="box"><div class="box-title">INDEX ENTRY TRIGGER</div><div class="box-value txt-blue">{ce_entry:.1f}</div></div>
                <div class="box"><div class="box-title">STRICT STOP-LOSS (SL)</div><div class="box-value txt-red">{ce_sl:.1f}</div></div>
                <div class="box"><div class="box-title">TARGET 1 (SAFE EXIT)</div><div class="box-value txt-green">{ce_t1:.1f}</div></div>
                <div class="box"><div class="box-title">TARGET 2 ({rr_choice}x R:R)</div><div class="box-value txt-green">{ce_t2:.1f}</div></div>
            </div>
            <div style="margin-top:8px;">
                <div class="level-item"><span>Target 3 (Trail / Runner):</span><b class="txt-green">{ce_t3:.1f}</b></div>
                <div class="level-item"><span>Max Risk ({lot_size} Qty):</span><b class="txt-red">-₹{ce_loss_rs:,.0f} ({ce_risk_pts} pts)</b></div>
                <div class="level-item"><span>Est. Profit at T2 ({lot_size} Qty):</span><b class="txt-green">+₹{ce_gain_rs:,.0f} (+{ce_risk_pts*rr_choice:.1f} pts)</b></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # --- SETUP 2: PUT (PE) TRADE PLAN ---
        pe_entry = round(price, 1)
        pe_sl = round(min(primary_res, price + (1.2 * atr)), 1)
        pe_risk_pts = round(max(pe_sl - pe_entry, atr * 0.8), 1)
        pe_t1 = round(pe_entry - pe_risk_pts, 1)
        pe_t2 = round(pe_entry - (pe_risk_pts * rr_choice), 1)
        pe_t3 = round(pe_entry - (pe_risk_pts * (rr_choice + 1.0)), 1)
        pe_gain_rs = round(pe_risk_pts * rr_choice * lot_size, 0)
        pe_loss_rs = round(pe_risk_pts * lot_size, 0)

        st.markdown(f"""
        <div class="signal-card put-card">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <b style="color:#f43f5e; font-size:1.05rem;">🔴 OPTION SETUP 2: BUY PUT ({put_strike_name})</b>
                <span class="badge-pill badge-red">DOWNSIDE SETUP</span>
            </div>
            <p style="margin:4px 0 0 0; color:#cbd5e1; font-size:0.85rem;">
                <b>Trade Rule:</b> Buy <b>{put_strike_name}</b> if Nifty rejects/breaks below <b>{pe_entry:.1f}</b>
            </p>
            <div class="grid-2">
                <div class="box"><div class="box-title">INDEX ENTRY TRIGGER</div><div class="box-value txt-blue">{pe_entry:.1f}</div></div>
                <div class="box"><div class="box-title">STRICT STOP-LOSS (SL)</div><div class="box-value txt-red">{pe_sl:.1f}</div></div>
                <div class="box"><div class="box-title">TARGET 1 (SAFE EXIT)</div><div class="box-value txt-green">{pe_t1:.1f}</div></div>
                <div class="box"><div class="box-title">TARGET 2 ({rr_choice}x R:R)</div><div class="box-value txt-green">{pe_t2:.1f}</div></div>
            </div>
            <div style="margin-top:8px;">
                <div class="level-item"><span>Target 3 (Trail / Runner):</span><b class="txt-green">{pe_t3:.1f}</b></div>
                <div class="level-item"><span>Max Risk ({lot_size} Qty):</span><b class="txt-red">-₹{pe_loss_rs:,.0f} ({pe_risk_pts} pts)</b></div>
                <div class="level-item"><span>Est. Profit at T2 ({lot_size} Qty):</span><b class="txt-green">+₹{pe_gain_rs:,.0f} (+{pe_risk_pts*rr_choice:.1f} pts)</b></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # --- SETUP 3: BREAKOUT TRIGGERS (CE / PE) ---
        st.markdown(f"""
        <div class="signal-card">
            <b style="font-size:0.95rem;">⚡ SETUP 3: MOMENTUM BREAKOUT & BREAKDOWN</b>
            <div class="level-item" style="margin-top:8px;">
                <span>🟢 BUY {int(primary_res)} CE if Breaks:</span>
                <b class="txt-green">> {primary_res:.1f}</b>
            </div>
            <div class="level-item">
                <span>↳ CE Target / SL:</span>
                <b>Target: {primary_res + (1.5*atr):.1f} | SL: {primary_res - (0.8*atr):.1f}</b>
            </div>
            <div class="level-item">
                <span>🔴 BUY {int(primary_sup)} PE if Breaks:</span>
                <b class="txt-red">< {primary_sup:.1f}</b>
            </div>
            <div class="level-item">
                <span>↳ PE Target / SL:</span>
                <b>Target: {primary_sup - (1.5*atr):.1f} | SL: {primary_sup + (0.8*atr):.1f}</b>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # --- SECTION 4: INTERACTIVE CANDLESTICK CHART ---
        st.markdown("#### 📈 Interactive Candlestick Chart")
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.72, 0.28])

        sub_df = df.tail(45)
        fig.add_trace(go.Candlestick(
            x=sub_df['time'], open=sub_df['open'], high=sub_df['high'], low=sub_df['low'], close=sub_df['close'],
            increasing_line_color='#10b981', decreasing_line_color='#f43f5e', name="Price"
        ), row=1, col=1)

        fig.add_trace(go.Scatter(x=sub_df['time'], y=sub_df['ema9'], line=dict(color='#38bdf8', width=1.5), name="EMA 9"), row=1, col=1)
        fig.add_trace(go.Scatter(x=sub_df['time'], y=sub_df['ema21'], line=dict(color='#f59e0b', width=1.5), name="EMA 21"), row=1, col=1)

        fig.add_hline(y=primary_sup, line_dash="dash", line_color="#10b981", annotation_text=f"Support (PE Wall) {primary_sup:.0f}", row=1, col=1)
        fig.add_hline(y=primary_res, line_dash="dash", line_color="#f43f5e", annotation_text=f"Resistance (CE Wall) {primary_res:.0f}", row=1, col=1)

        fig.add_trace(go.Scatter(x=sub_df['time'], y=sub_df['rsi'], line=dict(color='#c084fc', width=1.5), name="RSI"), row=2, col=1)
        fig.add_hline(y=70, line_dash="dot", line_color="#f43f5e", row=2, col=1)
        fig.add_hline(y=30, line_dash="dot", line_color="#10b981", row=2, col=1)

        fig.update_layout(
            height=440,
            margin=dict(l=5, r=5, t=10, b=10),
            xaxis_rangeslider_visible=False,
            template="plotly_dark",
            paper_bgcolor="#0b0e14",
            plot_bgcolor="#0b0e14",
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    except Exception as e:
        st.error(f"Execution Error: {e}")
else:
    st.info("👆 Tap 'Tap to Upload Market Data' above to load your data.")
    
