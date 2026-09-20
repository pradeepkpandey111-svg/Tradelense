import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. Mobile Terminal Configuration
st.set_page_config(
    page_title="TradeLense Pro",
    page_icon="⚡",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 2. High-Contrast Modern Theme (Fixes all dark/dim subtext issues)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@500;700;800&family=Plus+Jakarta+Sans:wght@500;600;700;800&display=swap');
    
    html, body, [class*="css"], .stMarkdown {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
        background-color: #080b11;
        color: #f8fafc !important;
    }

    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 2rem !important;
        padding-left: 0.7rem !important;
        padding-right: 0.7rem !important;
    }
    
    /* Clean, non-clipped header */
    .brand-container {
        background: linear-gradient(135deg, #0f172a, #1e293b);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 12px 14px;
        margin-bottom: 12px;
    }
    .brand-title {
        font-size: 1.35rem !important;
        font-weight: 800;
        color: #ffffff !important;
        margin: 0;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    .brand-tagline {
        font-size: 0.75rem;
        color: #94a3b8 !important;
        font-weight: 600;
        margin-top: 2px;
    }

    /* Signal Execution Cards */
    .trade-card {
        background: #0f172a;
        border-radius: 12px;
        padding: 14px;
        margin-bottom: 12px;
        border: 1px solid #1e293b;
    }
    .call-card {
        border-left: 6px solid #10b981;
        background: linear-gradient(145deg, #06281e, #0c382b);
        border-top: 1px solid #10b98144;
        border-right: 1px solid #10b98122;
        border-bottom: 1px solid #10b98122;
    }
    .put-card {
        border-left: 6px solid #f43f5e;
        background: linear-gradient(145deg, #2b0b12, #3d121c);
        border-top: 1px solid #f43f5e44;
        border-right: 1px solid #f43f5e22;
        border-bottom: 1px solid #f43f5e22;
    }
    .block-card {
        border-left: 6px solid #f59e0b;
        background: linear-gradient(145deg, #241802, #382405);
        border-top: 1px solid #f59e0b44;
        border-right: 1px solid #f59e0b22;
        border-bottom: 1px solid #f59e0b22;
    }

    /* High Visibility Grid Boxes */
    .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 8px; }
    .grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 6px; margin-top: 6px; }

    .box {
        background: #090d16;
        border-radius: 8px;
        padding: 9px 10px;
        border: 1px solid #26334d;
    }
    .box-title {
        font-size: 0.68rem;
        font-weight: 700;
        color: #94a3b8 !important; /* Visible bright slate */
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
    .txt-white { color: #ffffff !important; }

    .star-rating {
        font-size: 1.15rem;
        color: #fbbf24;
        letter-spacing: 2px;
        font-weight: 800;
    }

    .level-item {
        display: flex;
        justify-content: space-between;
        padding: 7px 0;
        border-bottom: 1px solid #222f46;
        font-size: 0.85rem;
        color: #cbd5e1 !important; /* Bright high contrast text */
        font-family: 'JetBrains Mono', monospace;
    }
    .level-item span {
        color: #cbd5e1 !important;
    }
    .level-item b {
        color: #ffffff !important;
    }
</style>

<div class="brand-container">
    <div class="brand-title">⚡ TradeLense Pro</div>
    <div class="brand-tagline">Strict Confluence & 5-Star Signal Evaluator</div>
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
    df = pd.read_excel(file) if file.name.lower().endswith(('.xlsx', '.xls')) else pd.read_csv(file)
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

# Helper: Compute Pure Pandas Indicators
def run_indicators(df):
    df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
    
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
def parse_option_chain(file):
    df = pd.read_excel(file) if file.name.lower().endswith(('.xlsx', '.xls')) else pd.read_csv(file)
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
        ema50 = curr['ema50']

        # Pivot Floor Points
        prev_h, prev_l, prev_c = prev['high'], prev['low'], prev['close']
        pivot = (prev_h + prev_l + prev_c) / 3
        r1 = (2 * pivot) - prev_l
        s1 = (2 * pivot) - prev_h

        # Option Chain S/R fallback
        oc = None
        if opt_file:
            try:
                oc = parse_option_chain(opt_file)
            except Exception:
                pass

        primary_sup = oc['support'] if oc and oc['support'] < price else round(s1, 1)
        primary_res = oc['resistance'] if oc and oc['resistance'] > price else round(r1, 1)
        
        atm_strike = int(round(price / 50) * 50)
        call_strike_name = f"{atm_strike} CE"
        put_strike_name = f"{atm_strike} PE"

        # ----------------- 5-STAR CONFLUENCE SCORING ENGINE -----------------
        bull_stars = 0
        bear_stars = 0
        bull_reasons = []
        bear_reasons = []

        # Indicator 1: Fast Trend Alignment (EMA 9 vs EMA 21)
        if ema9 > ema21:
            bull_stars += 1
            bull_reasons.append("EMA 9 crossed above EMA 21 (Bullish Momentum)")
        else:
            bear_stars += 1
            bear_reasons.append("EMA 9 crossed below EMA 21 (Bearish Momentum)")

        # Indicator 2: Macro Trend (Price vs EMA 50)
        if price >= ema50:
            bull_stars += 1
            bull_reasons.append("Price trading above EMA 50 (Macro Uptrend)")
        else:
            bear_stars += 1
            bear_reasons.append("Price trading below EMA 50 (Macro Downtrend)")

        # Indicator 3: Momentum Filter (RSI 14)
        if 52 <= rsi <= 72:
            bull_stars += 1
            bull_reasons.append(f"RSI {rsi:.1f} in strong Bullish acceleration zone (52-72)")
        elif 28 <= rsi <= 48:
            bear_stars += 1
            bear_reasons.append(f"RSI {rsi:.1f} in Bearish breakdown zone (28-48)")

        # Indicator 4: Candlestick Confirmation
        if curr['close'] > prev['high']:
            bull_stars += 1
            bull_reasons.append("Candle breakout: Closed above previous candle high")
        elif curr['close'] < prev['low']:
            bear_stars += 1
            bear_reasons.append("Candle breakdown: Closed below previous candle low")

        # Indicator 5: Option Chain PCR & Walls
        if oc:
            if oc['pcr'] >= 1.05 and price >= oc['support']:
                bull_stars += 1
                bull_reasons.append(f"F&O PCR {oc['pcr']} Bullish + Holding Put Support {oc['support']:.0f}")
            elif oc['pcr'] <= 0.88 and price <= oc['resistance']:
                bear_stars += 1
                bear_reasons.append(f"F&O PCR {oc['pcr']} Bearish + Resisted by Call Wall {oc['resistance']:.0f}")
        else:
            # Fallback to Pivot positioning if no option chain uploaded
            if price > pivot:
                bull_stars += 1
                bull_reasons.append("Price sustained above Central Pivot")
            else:
                bear_stars += 1
                bear_reasons.append("Price rejected below Central Pivot")

        # Visual star generator
        def get_star_str(count):
            return "★" * count + "☆" * (5 - count)

        # Strict Filter Rule: Require AT LEAST 3 Stars to trigger any trade
        has_valid_buy = bull_stars >= 3
        has_valid_sell = bear_stars >= 3 and not has_valid_buy

        # --- TOP LEVEL SUMMARY STATS ---
        st.markdown(f"""
        <div class="box" style="margin-bottom:12px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <span class="box-title">CURRENT NIFTY PRICE</span>
                    <div class="box-value txt-blue">{price:.2f}</div>
                </div>
                <div style="text-align:right;">
                    <span class="box-title">CONFIDENCE RATING</span>
                    <div class="star-rating">{get_star_str(max(bull_stars, bear_stars))} ({max(bull_stars, bear_stars)}/5)</div>
                </div>
            </div>
            <div class="grid-3" style="margin-top:6px;">
                <div class="box">
                    <div class="box-title">SUPPORT (PE WALL)</div>
                    <div class="box-value txt-green">{primary_sup:.0f}</div>
                </div>
                <div class="box">
                    <div class="box-title">PIVOT POINT</div>
                    <div class="box-value txt-amber">{pivot:.0f}</div>
                </div>
                <div class="box">
                    <div class="box-title">RESISTANCE (CE WALL)</div>
                    <div class="box-value txt-red">{primary_res:.0f}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("#### 🎯 Algorithmic Execution Calls")

        # STRICT SIGNAL CHECK: NO TRADE ZONE IF INDICATORS DO NOT CONCUR
        if not has_valid_buy and not has_valid_sell:
            st.markdown(f"""
            <div class="trade-card block-card">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <b style="color:#fbbf24; font-size:1.05rem;">⛔ NO TRADE ZONE: INSUFFICIENT CONFLUENCE</b>
                    <span class="star-rating">{get_star_str(max(bull_stars, bear_stars))}</span>
                </div>
                <p style="margin:8px 0 4px 0; color:#cbd5e1; font-size:0.86rem; line-height:1.4;">
                    <b>App Protection Triggered:</b> The market is currently consolidating. Indicators do not align with sufficient confidence (scored only <b>{max(bull_stars, bear_stars)}/5 stars</b>).<br>
                    • No trade is issued to protect capital from whipsaws.<br>
                    • Wait for price to break <b>{primary_res:.1f}</b> for CE or break <b>{primary_sup:.1f}</b> for PE.
                </p>
            </div>
            """, unsafe_allow_html=True)

        # CALL (CE) TRADE CARD - ONLY SHOWN WHEN INDICATORS SUPPORT
        elif has_valid_buy:
            ce_entry = round(price, 1)
            ce_sl = round(max(primary_sup, price - (1.2 * atr)), 1)
            ce_risk_pts = round(max(ce_entry - ce_sl, atr * 0.8), 1)
            ce_t1 = round(ce_entry + ce_risk_pts, 1)
            ce_t2 = round(ce_entry + (ce_risk_pts * rr_choice), 1)
            ce_t3 = round(ce_entry + (ce_risk_pts * (rr_choice + 1.0)), 1)
            ce_gain_rs = round(ce_risk_pts * rr_choice * lot_size, 0)
            ce_loss_rs = round(ce_risk_pts * lot_size, 0)

            st.markdown(f"""
            <div class="trade-card call-card">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <b style="color:#10b981; font-size:1.05rem;">🟢 BUY SIGNAL: BUY {call_strike_name}</b>
                    <span class="star-rating">{get_star_str(bull_stars)} ({bull_stars}/5)</span>
                </div>
                <p style="margin:4px 0 0 0; color:#f1f5f9; font-size:0.85rem;">
                    <b>Trade Action:</b> Strong Bullish Confluence. Buy <b>{call_strike_name}</b> at <b>{ce_entry:.1f}</b>.
                </p>
                <div class="grid-2">
                    <div class="box"><div class="box-title">INDEX ENTRY TRIGGER</div><div class="box-value txt-blue">{ce_entry:.1f}</div></div>
                    <div class="box"><div class="box-title">STRICT STOP-LOSS (SL)</div><div class="box-value txt-red">{ce_sl:.1f}</div></div>
                    <div class="box"><div class="box-title">TARGET 1 (1:1 EXIT)</div><div class="box-value txt-green">{ce_t1:.1f}</div></div>
                    <div class="box"><div class="box-title">TARGET 2 ({rr_choice}x R:R)</div><div class="box-value txt-green">{ce_t2:.1f}</div></div>
                </div>
                <div style="margin-top:8px;">
                    <div class="level-item"><span>Target 3 (Trail / Runner):</span><b>{ce_t3:.1f}</b></div>
                    <div class="level-item"><span>Max Risk ({lot_size} Qty):</span><b class="txt-red">-₹{ce_loss_rs:,.0f} ({ce_risk_pts} pts)</b></div>
                    <div class="level-item"><span>Est. Profit at T2 ({lot_size} Qty):</span><b class="txt-green">+₹{ce_gain_rs:,.0f} (+{ce_risk_pts*rr_choice:.1f} pts)</b></div>
                </div>
                <div style="margin-top:8px; padding-top:6px; border-top:1px solid #10b98133;">
                    <span class="box-title">WHY THIS CALL (CONFIRMING PILLARS):</span>
                    <ul style="margin:4px 0 0 16px; padding:0; color:#cbd5e1; font-size:0.82rem;">
                        {"".join([f"<li>{r}</li>" for r in bull_reasons])}
                    </ul>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # PUT (PE) TRADE CARD - ONLY SHOWN WHEN INDICATORS SUPPORT
        elif has_valid_sell:
            pe_entry = round(price, 1)
            pe_sl = round(min(primary_res, price + (1.2 * atr)), 1)
            pe_risk_pts = round(max(pe_sl - pe_entry, atr * 0.8), 1)
            pe_t1 = round(pe_entry - pe_risk_pts, 1)
            pe_t2 = round(pe_entry - (pe_risk_pts * rr_choice), 1)
            pe_t3 = round(pe_entry - (pe_risk_pts * (rr_choice + 1.0)), 1)
            pe_gain_rs = round(pe_risk_pts * rr_choice * lot_size, 0)
            pe_loss_rs = round(pe_risk_pts * lot_size, 0)

            st.markdown(f"""
            <div class="trade-card put-card">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <b style="color:#f43f5e; font-size:1.05rem;">🔴 BUY SIGNAL: BUY {put_strike_name}</b>
                    <span class="star-rating">{get_star_str(bear_stars)} ({bear_stars}/5)</span>
                </div>
                <p style="margin:4px 0 0 0; color:#f1f5f9; font-size:0.85rem;">
                    <b>Trade Action:</b> Strong Bearish Confluence. Buy <b>{put_strike_name}</b> at <b>{pe_entry:.1f}</b>.
                </p>
                <div class="grid-2">
                    <div class="box"><div class="box-title">INDEX ENTRY TRIGGER</div><div class="box-value txt-blue">{pe_entry:.1f}</div></div>
                    <div class="box"><div class="box-title">STRICT STOP-LOSS (SL)</div><div class="box-value txt-red">{pe_sl:.1f}</div></div>
                    <div class="box"><div class="box-title">TARGET 1 (1:1 EXIT)</div><div class="box-value txt-green">{pe_t1:.1f}</div></div>
                    <div class="box"><div class="box-title">TARGET 2 ({rr_choice}x R:R)</div><div class="box-value txt-green">{pe_t2:.1f}</div></div>
                </div>
                <div style="margin-top:8px;">
                    <div class="level-item"><span>Target 3 (Trail / Runner):</span><b>{pe_t3:.1f}</b></div>
                    <div class="level-item"><span>Max Risk ({lot_size} Qty):</span><b class="txt-red">-₹{pe_loss_rs:,.0f} ({pe_risk_pts} pts)</b></div>
                    <div class="level-item"><span>Est. Profit at T2 ({lot_size} Qty):</span><b class="txt-green">+₹{pe_gain_rs:,.0f} (+{pe_risk_pts*rr_choice:.1f} pts)</b></div>
                </div>
                <div style="margin-top:8px; padding-top:6px; border-top:1px solid #f43f5e33;">
                    <span class="box-title">WHY THIS CALL (CONFIRMING PILLARS):</span>
                    <ul style="margin:4px 0 0 16px; padding:0; color:#cbd5e1; font-size:0.82rem;">
                        {"".join([f"<li>{r}</li>" for r in bear_reasons])}
                    </ul>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # ----------------- INTERACTIVE CHART -----------------
        st.markdown("#### 📈 Interactive Candlestick Chart")
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.72, 0.28])

        sub_df = df.tail(45)
        fig.add_trace(go.Candlestick(
            x=sub_df['time'], open=sub_df['open'], high=sub_df['high'], low=sub_df['low'], close=sub_df['close'],
            increasing_line_color='#10b981', decreasing_line_color='#f43f5e', name="Price"
        ), row=1, col=1)

        fig.add_trace(go.Scatter(
