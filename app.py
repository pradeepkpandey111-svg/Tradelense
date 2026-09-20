import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. Page Configuration
st.set_page_config(
    page_title="TradeLense Pro Terminal",
    page_icon="⚡",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 2. Modern Terminal UI Styling (Fixes header cut-off & modernizes cards)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@500;700;800&family=Plus+Jakarta+Sans:wght@500;600;700;800&display=swap');
    
    html, body, [class*="css"], .stMarkdown {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        background-color: #07090e;
        color: #f1f5f9 !important;
    }

    /* Extra top padding so header is never clipped by mobile navigation */
    .block-container {
        padding-top: 2.4rem !important;
        padding-bottom: 2.5rem !important;
        padding-left: 0.7rem !important;
        padding-right: 0.7rem !important;
    }
    
    /* Modern Glassmorphism Dock Header */
    .hero-banner {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 14px;
        padding: 14px 16px;
        margin-bottom: 12px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
    }
    .hero-title {
        font-size: 1.35rem !important;
        font-weight: 800;
        letter-spacing: -0.5px;
        color: #ffffff !important;
        margin: 0;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .hero-subtitle {
        font-size: 0.75rem;
        color: #94a3b8 !important;
        font-weight: 600;
        margin-top: 3px;
    }

    /* Trade Action Cards */
    .call-card {
        background: linear-gradient(145deg, #062b20, #0a3d2e);
        border-radius: 12px;
        padding: 14px;
        border: 1px solid #10b98155;
        border-left: 6px solid #10b981;
        margin-bottom: 12px;
    }
    .put-card {
        background: linear-gradient(145deg, #2d0c13, #45121e);
        border-radius: 12px;
        padding: 14px;
        border: 1px solid #f43f5e55;
        border-left: 6px solid #f43f5e;
        margin-bottom: 12px;
    }
    .block-card {
        background: linear-gradient(145deg, #241703, #382405);
        border-radius: 12px;
        padding: 14px;
        border: 1px solid #f59e0b55;
        border-left: 6px solid #f59e0b;
        margin-bottom: 12px;
    }

    /* Grid Layouts */
    .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 8px; }
    .grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 6px; margin-top: 6px; }

    .tile {
        background: #090e17;
        border-radius: 8px;
        padding: 9px 10px;
        border: 1px solid #1e293b;
    }
    .tile-lbl {
        font-size: 0.65rem;
        font-weight: 700;
        color: #94a3b8 !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .tile-val {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.05rem;
        font-weight: 700;
        margin-top: 2px;
    }

    .c-green { color: #10b981 !important; }
    .c-red { color: #f43f5e !important; }
    .c-blue { color: #38bdf8 !important; }
    .c-amber { color: #fbbf24 !important; }

    .stars-badge {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.95rem;
        color: #fbbf24;
        font-weight: 800;
        letter-spacing: 1.5px;
    }

    .level-row {
        display: flex;
        justify-content: space-between;
        padding: 6px 0;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        font-size: 0.82rem;
        font-family: 'JetBrains Mono', monospace;
        color: #cbd5e1 !important;
    }
    .level-row span { color: #94a3b8 !important; }
    .level-row b { color: #f8fafc !important; }
</style>

<div class="hero-banner">
    <div class="hero-title">⚡ TradeLense Neo Pro</div>
    <div class="hero-subtitle">Algorithmic Confluence & Execution Matrix</div>
</div>
""", unsafe_allow_html=True)

# 3. Modernized Upload Drawer
with st.expander("📂 Market Data Control Dock", expanded=True):
    nifty_file = st.file_uploader("1. Share / NIFTY 50 History (CSV)", key="h")
    opt_file = st.file_uploader("2. Option Chain (CSV / XLSX)", key="o")
    
    c1, c2 = st.columns(2)
    with c1:
        rr = st.selectbox("Target Multiplier", [1.5, 2.0, 2.5, 3.0], index=1)
    with c2:
        lots = st.number_input("Lot / Qty Size", value=50, step=25)

# Helper Functions
def parse_ohlc(f):
    df = pd.read_excel(f) if f.name.lower().endswith(('.xlsx', '.xls')) else pd.read_csv(f)
    df.columns = [str(c).strip().lower() for c in df.columns]
    t = next((c for c in df.columns if 'time' in c or 'date' in c), df.columns[0])
    df['time'] = pd.to_datetime(df[t], errors='coerce')
    df = df.dropna(subset=['time']).sort_values('time').reset_index(drop=True)
    for col in ['open', 'high', 'low', 'close']:
        match = next((c for c in df.columns if col in c or (col == 'close' and 'ltp' in c)), None)
        df[col] = pd.to_numeric(df[match].astype(str).str.replace(',', ''), errors='coerce') if match else df['close']
    return df

def run_indicators(df):
    df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
    chg = df['close'].diff()
    gain = chg.clip(lower=0).rolling(14).mean()
    loss = (-chg.clip(upper=0)).rolling(14).mean().replace(0, np.nan)
    df['rsi'] = (100 - (100 / (1 + (gain / loss)))).fillna(50)
    tr = pd.concat([df['high'] - df['low'], (df['high'] - df['close'].shift()).abs(), (df['low'] - df['close'].shift()).abs()], axis=1).max(axis=1)
    df['atr'] = tr.rolling(14).mean().bfill()
    return df

def parse_chain(f):
    df = pd.read_excel(f) if f.name.lower().endswith(('.xlsx', '.xls')) else pd.read_csv(f)
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    c_col = next((c for c in df.columns if ('ce' in c and 'oi' in c) or ('call' in c and 'oi' in c)), None)
    p_col = next((c for c in df.columns if ('pe' in c and 'oi' in c) or ('put' in c and 'oi' in c)), None)
    s_col = next((c for c in df.columns if 'strike' in c), None)
    if c_col and p_col and s_col:
        for x in [c_col, p_col, s_col]:
            df[x] = pd.to_numeric(df[x].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
        ce_sum = df[c_col].sum()
        pe_sum = df[p_col].sum()
        pcr = round(pe_sum / ce_sum, 2) if ce_sum > 0 else 1.0
        return {"pcr": pcr, "s": float(df.loc[df[p_col].idxmax(), s_col]), "r": float(df.loc[df[c_col].idxmax(), s_col])}
    return None

def star_icons(count):
    return "★" * count + "☆" * (5 - count)

# 4. Analysis Execution
if nifty_file:
    try:
        df = run_indicators(parse_ohlc(nifty_file))
        curr, prev = df.iloc[-1], df.iloc[-2]
        p = curr['close']
        atr = curr['atr'] if pd.notna(curr['atr']) and curr['atr'] > 0 else curr['close'] * 0.005
        rsi = curr['rsi']

        # Pivot Points
        piv = (prev['high'] + prev['low'] + prev['close']) / 3
        r1 = (2 * piv) - prev['low']
        s1 = (2 * piv) - prev['high']

        oc = parse_chain(opt_file) if opt_file else None
        sup = oc['s'] if oc and oc['s'] < p else round(s1, 1)
        res = oc['r'] if oc and oc['r'] > p else round(r1, 1)
        strike = int(round(p / 50) * 50)

        # Separate Scoring for Call (CE) & Put (PE) Setups
        bull_stars = 0
        bear_stars = 0
        b_reasons, be_reasons = [], []

        # 1. EMA Momentum
        if curr['ema9'] > curr['ema21']:
            bull_stars += 1
            b_reasons.append("EMA 9 crossed above EMA 21 (Bullish)")
        else:
            bear_stars += 1
            be_reasons.append("EMA 9 crossed below EMA 21 (Bearish)")

        # 2. Macro Trend (EMA 50)
        if p >= curr['ema50']:
            bull_stars += 1
            b_reasons.append("Price trading above EMA 50 (Uptrend)")
        else:
            bear_stars += 1
            be_reasons.append("Price trading below EMA 50 (Downtrend)")

        # 3. RSI Momentum Filter
        if 52 <= rsi <= 72:
            bull_stars += 1
            b_reasons.append(f"RSI ({rsi:.1f}) in Bullish momentum zone (52-72)")
        elif 28 <= rsi <= 48:
            bear_stars += 1
            be_reasons.append(f"RSI ({rsi:.1f}) in Bearish momentum zone (28-48)")

        # 4. Price Action Breakout
        if curr['close'] > prev['high']:
            bull_stars += 1
            b_reasons.append("Candle closed above previous candle high")
        elif curr['close'] < prev['low']:
            bear_stars += 1
            be_reasons.append("Candle closed below previous candle low")

        # 5. F&O Open Interest Support/Resistance
        if oc:
            if oc['pcr'] >= 1.05 and p >= sup:
                bull_stars += 1
                b_reasons.append(f"PCR {oc['pcr']} Bullish + Holding Put Support ({sup:.0f})")
            elif oc['pcr'] <= 0.88 and p <= res:
                bear_stars += 1
                be_reasons.append(f"PCR {oc['pcr']} Bearish + Call Wall Resistance ({res:.0f})")
        else:
            if p > piv:
                bull_stars += 1
                b_reasons.append("Price sustained above Central Pivot")
            else:
                bear_stars += 1
                be_reasons.append("Price rejected below Central Pivot")

        # NIFTY BENCHMARK STATUS BAR
        st.markdown(f"""
        <div class="tile" style="margin-bottom:12px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <span class="tile-lbl">CURRENT NIFTY PRICE</span>
                    <div class="tile-val c-blue">{p:.2f}</div>
                </div>
                <div style="text-align:right;">
                    <span class="tile-lbl">INTRADAY STATUS</span>
                    <div class="tile-val {'c-green' if bull_stars > bear_stars else 'c-red'}">
                        {'BULLISH BIAS' if bull_stars > bear_stars else ('BEARISH BIAS' if bear_stars > bull_stars else 'SIDEWAYS')}
                    </div>
                </div>
            </div>
            <div class="grid-3" style="margin-top:6px;">
                <div class="tile"><span class="tile-lbl">SUPPORT (PE WALL)</span><div class="tile-val c-green">{sup:.0f}</div></div>
                <div class="tile"><span class="tile-lbl">PIVOT POINT</span><div class="tile-val c-amber">{piv:.0f}</div></div>
                <div class="tile"><span class="tile-lbl">RESISTANCE (CE WALL)</span><div class="tile-val c-red">{res:.0f}</div></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("#### 🎯 Execution Trade Setups")

        # Setup Selection: Only trigger trades with >= 3 Stars
        has_buy_call = bull_stars >= 3
        has_buy_put = bear_stars >= 3 and not has_buy_call

        if not has_buy_call and not has_buy_put:
            best_score = max(bull_stars, bear_stars)
            st.markdown(f"""
            <div class="block-card">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <b style="color:#fbbf24; font-size:0.98rem;">⛔ NO TRADE ZONE: INSUFFICIENT CONFLUENCE</b>
                    <span class="stars-badge">{star_icons(best_score)} ({best_score}/5)</span>
                </div>
                <p style="margin:6px 0 0 0; color:#cbd5e1; font-size:0.82rem; line-height:1.4;">
                    Indicators only scored <b>{best_score}/5 stars</b>. Market is consolidating. Wait for breakout above <b>{res:.0f}</b> for CE or breakdown below <b>{sup:.0f}</b> for PE before taking positions.
                </p>
            </div>
            """, unsafe_allow_html=True)
        elif has_buy_call:
            sl = round(max(sup, p - (1.2 * atr)), 1)
            risk = round(max(p - sl, atr * 0.8), 1)
            t1 = round(p + risk, 1)
            t2 = round(p + (risk * rr), 1)
            t3 = round(p + (risk * (rr + 1)), 1)

            reasons_html = "".join([f"<li>{r}</li>" for r in b_reasons])
            st.markdown(f"""
            <div class="call-card">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <b style="color:#10b981; font-size:1.05rem;">🟢 BUY {strike} CE</b>
                    <span class="stars-badge">{star_icons(bull_stars)} ({bull_stars}/5)</span>
                </div>
                <div class="grid-2">
                    <div class="tile"><span class="tile-lbl">ENTRY TRIGGER</span><div class="tile-val c-blue">{p:.1f}</div></div>
                    <div class="tile"><span class="tile-lbl">STRICT SL</span><div class="tile-val c-red">{sl:.1f}</div></div>
                    <div class="tile"><span class="tile-lbl">TARGET 1</span><div class="tile-val c-green">{t1:.1f}</div></div>
                    <div class="tile"><span class="tile-lbl">TARGET 2 ({rr}R)</span><div class="tile-val c-green">{t2:.1f}</div></div>
                </div>
                <div style="margin-top:8px;">
                    <div class="level-row"><span>Target 3 (Extension):</span><b>{t3:.1f}</b></div>
                    <div class="level-row"><span>Max Risk ({lots} Qty):</span><b class="c-red">-₹{risk * lots:,.0f} ({risk} pts)</b></div>
                    <div class="level-row"><span>Est. Gain at T2:</span><b class="c-green">+₹{risk * rr * lots:,.0f} (+{risk * rr:.1f} pts)</b></div>
                </div>
                <div style="margin-top:8px; padding-top:6px; border-top:1px solid #10b98133;">
                    <span class="tile-lbl">CONFIRMING CONFLUENCE PILLARS:</span>
                    <ul style="margin:4px 0 0 16px; padding:0; color:#cbd5e1; font-size:0.78rem;">
                        {reasons_html}
                    </ul>
                </div>
            </div>
            """, unsafe_allow_html=True)
        elif has_buy_put:
            sl = round(min(res, p + (1.2 * atr)), 1)
            risk = round(max(sl - p, atr * 0.8), 1)
            t1 = round(p - risk, 1)
            t2 = round(p - (risk * rr), 1)
            t3 = round(p - (risk * (rr + 1)), 1)

            reasons_html = "".join([f"<li>{r}</li>" for r in be_reasons])
            st.markdown(f"""
            <div class="put-card">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <b style="color:#f43f5e; font-size:1.05rem;">🔴 BUY {strike} PE</b>
                    <span class="stars-badge">{star_icons(bear_stars)} ({bear_stars}/5)</span>
                </div>
                <div class="grid-2">
                    <div class="tile"><span class="tile-lbl">ENTRY TRIGGER</span><div class="tile-val c-blue">{p:.1f}</div></div>
                    <div class="tile"><span class="tile-lbl">STRICT SL</span><div class="tile-val c-red">{sl:.1f}</div></div>
                    <div class="tile"><span class="tile-lbl">TARGET 1</span><div class="tile-val c-green">{t1:.1f}</div></div>
                    <div class="tile"><span class="tile-lbl">TARGET 2 ({rr}R)</span><div class="tile-val c-green">{t2:.1f}</div></div>
                </div>
                <div style="margin-top:8px;">
                    <div class="level-row"><span>Target 3 (Extension):</span><b>{t3:.1f}</b></div>
                    <div class="level-row"><span>Max Risk ({lots} Qty):</span><b class="c-red">-₹{risk * lots:,.0f} ({risk} pts)</b></div>
                    <div class="level-row"><span>Est. Gain at T2:</span><b class="c-green">+₹{risk * rr * lots:,.0f} (+{risk * rr:.1f} pts)</b></div>
                </div>
                <div style="margin-top:8px; padding-top:6px; border-top:1px solid #f43f5e33;">
                    <span class="tile-lbl">CONFIRMING CONFLUENCE PILLARS:</span>
                    <ul style="margin:4px 0 0 16px; padding:0; color:#cbd5e1; font-size:0.78rem;">
                        {reasons_html}
                    </ul>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # 5. Interactive Chart Panel
        st.markdown("#### 📈 Interactive Candlestick Chart")
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.72, 0.28])
        sub = df.tail(45)
        fig.add_trace(go.Candlestick(x=sub['time'], open=sub['open'], high=sub['high'], low=sub['low'], close=sub['close'], increasing_line_color='#10b981', decreasing_line_color='#f43f5e', name="Price"), row=1, col=1)
        fig.add_trace(go.Scatter(x=sub['time'], y=sub['ema9'], line=dict(color='#38bdf8', width=1.5), name="EMA 9"), row=1, col=1)
        fig.add_trace(go.Scatter(x=sub['time'], y=sub['ema21'], line=dict(color='#f59e0b', width=1.5), name="EMA 21"), row=1, col=1)
        fig.add_hline(y=sup, line_dash="dash", line_color="#10b981", annotation_text=f"Sup {sup:.0f}", row=1, col=1)
        fig.add_hline(y=res, line_dash="dash", line_color="#f43f5e", annotation_text=f"Res {res:.0f}", row=1, col=1)
        fig.add_trace(go.Scatter(x=sub['time'], y=sub['rsi'], line=dict(color='#c084fc', width=1.5), name="RSI"), row=2, col=1)
        fig.add_hline(y=70, line_dash="dot", line_color="#f43f5e", row=2, col=1)
        fig.add_hline(y=30, line_dash="dot", line_color="#10b981", row=2, col=1)
        fig.update_layout(height=440, margin=dict(l=5, r=5, t=10, b=10), xaxis_rangeslider_visible=False, template="plotly_dark", paper_bgcolor="#07090e", plot_bgcolor="#07090e", showlegend=False)
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    except Exception as e:
        st.error(f"Execution Error: {e}")
else:
    st.info("👆 Tap 'Market Data Control Dock' above to load your data.")
    
