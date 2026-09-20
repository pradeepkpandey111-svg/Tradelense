import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="TradeLense Pro", page_icon="⚡", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@500;700&family=Plus+Jakarta+Sans:wght@600;700;800&display=swap');
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif !important; background: #080b11; color: #f8fafc !important; }
    .block-container { padding: 1rem 0.6rem 2rem 0.6rem !important; }
    .brand-box { background: #0f172a; border: 1px solid #334155; border-radius: 10px; padding: 10px 12px; margin-bottom: 10px; }
    .trade-card { background: #0f172a; border-radius: 10px; padding: 12px; margin-bottom: 10px; border: 1px solid #1e293b; }
    .call-card { border-left: 5px solid #10b981; background: #06281e; }
    .put-card { border-left: 5px solid #f43f5e; background: #2b0b12; }
    .block-card { border-left: 5px solid #f59e0b; background: #241802; }
    .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin-top: 6px; }
    .grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 4px; margin-top: 6px; }
    .box { background: #090d16; border-radius: 6px; padding: 6px 8px; border: 1px solid #26334d; }
    .box-lbl { font-size: 0.65rem; font-weight: 700; color: #94a3b8 !important; text-transform: uppercase; }
    .box-val { font-family: 'JetBrains Mono', monospace; font-size: 1rem; font-weight: 700; }
    .c-green { color: #10b981 !important; }
    .c-red { color: #f43f5e !important; }
    .c-blue { color: #38bdf8 !important; }
    .c-amber { color: #fbbf24 !important; }
    .stars { font-size: 1.1rem; color: #fbbf24; font-weight: 800; letter-spacing: 1px; }
    .lvl-row { display: flex; justify-content: space-between; padding: 5px 0; border-bottom: 1px solid #1e293b; font-size: 0.8rem; font-family: 'JetBrains Mono'; }
</style>
<div class="brand-box">
    <div style="font-size:1.25rem; font-weight:800; color:#fff;">⚡ TradeLense Pro</div>
    <div style="font-size:0.75rem; color:#94a3b8;">5-Star Algorithmic F&O Signal Terminal</div>
</div>
""", unsafe_allow_html=True)

with st.expander("📂 Tap to Upload Market Data", expanded=True):
    nifty_file = st.file_uploader("1. Share / NIFTY History (CSV)", key="h")
    opt_file = st.file_uploader("2. Option Chain (CSV / XLSX)", key="o")
    col1, col2 = st.columns(2)
    rr = col1.selectbox("Target Multiplier", [1.5, 2.0, 2.5, 3.0], index=1)
    lots = col2.number_input("Lot / Qty Size", value=50, step=25)

def clean_data(f):
    df = pd.read_excel(f) if f.name.lower().endswith(('.xlsx', '.xls')) else pd.read_csv(f)
    df.columns = [str(c).strip().lower() for c in df.columns]
    t = next((c for c in df.columns if 'time' in c or 'date' in c), df.columns[0])
    df['time'] = pd.to_datetime(df[t], errors='coerce')
    df = df.dropna(subset=['time']).sort_values('time').reset_index(drop=True)
    for k in ['open', 'high', 'low', 'close']:
        m = next((c for c in df.columns if k in c or (k == 'close' and 'ltp' in c)), None)
        df[k] = pd.to_numeric(df[m].astype(str).str.replace(',', ''), errors='coerce') if m else df['close']
    return df

def get_indicators(df):
    df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
    chg = df['close'].diff()
    rs = chg.clip(lower=0).rolling(14).mean() / (-chg.clip(upper=0)).rolling(14).mean().replace(0, np.nan)
    df['rsi'] = (100 - (100 / (1 + rs))).fillna(50)
    tr = pd.concat([df['high'] - df['low'], (df['high'] - df['close'].shift()).abs(), (df['low'] - df['close'].shift()).abs()], axis=1).max(axis=1)
    df['atr'] = tr.rolling(14).mean().bfill()
    return df

def get_chain(f):
    df = pd.read_excel(f) if f.name.lower().endswith(('.xlsx', '.xls')) else pd.read_csv(f)
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    c_col = next((c for c in df.columns if ('ce' in c and 'oi' in c) or ('call' in c and 'oi' in c)), None)
    p_col = next((c for c in df.columns if ('pe' in c and 'oi' in c) or ('put' in c and 'oi' in c)), None)
    s_col = next((c for c in df.columns if 'strike' in c), None)
    if c_col and p_col and s_col:
        for x in [c_col, p_col, s_col]: df[x] = pd.to_numeric(df[x].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
        pcr = round(df[p_col].sum() / df[c_col].sum(), 2) if df[c_col].sum() > 0 else 1.0
        return {"pcr": pcr, "s": float(df.loc[df[p_col].idxmax(), s_col]), "r": float(df.loc[df[c_col].idxmax(), s_col])}
    return None

if nifty_file:
    try:
        df = get_indicators(clean_data(nifty_file))
        curr, prev = df.iloc[-1], df.iloc[-2]
        p, atr, rsi = curr['close'], curr['atr'] if pd.notna(curr['atr']) and curr['atr'] > 0 else curr['close'] * 0.005, curr['rsi']
        piv = (prev['high'] + prev['low'] + prev['close']) / 3
        r1, s1 = (2 * piv) - prev['low'], (2 * piv) - prev['high']
        oc = get_chain(opt_file) if opt_file else None
        sup = oc['s'] if oc and oc['s'] < p else round(s1, 1)
        res = oc['r'] if oc and oc['r'] > p else round(r1, 1)
        strike = int(round(p / 50) * 50)

        bull_s, bear_s, b_reasons, be_reasons = 0, 0, [], []
        if curr['ema9'] > curr['ema21']: bull_s += 1; b_reasons.append("EMA 9 > EMA 21 (Bullish)")
        else: bear_s += 1; be_reasons.append("EMA 9 < EMA 21 (Bearish)")
        if p >= curr['ema50']: bull_s += 1; b_reasons.append("Price above EMA 50 (Uptrend)")
        else: bear_s += 1; be_reasons.append("Price below EMA 50 (Downtrend)")
        if 52 <= rsi <= 72: bull_s += 1; b_reasons.append(f"RSI ({rsi:.1f}) in Bullish zone")
        elif 28 <= rsi <= 48: bear_s += 1; be_reasons.append(f"RSI ({rsi:.1f}) in Bearish zone")
        if curr['close'] > prev['high']: bull_s += 1; b_reasons.append("Closed above Prev High")
        elif curr['close'] < prev['low']: bear_s += 1; be_reasons.append("Closed below Prev Low")
        if oc:
            if oc['pcr'] >= 1.05 and p >= sup: bull_s += 1; b_reasons.append(f"PCR {oc['pcr']} Bullish + Put Support")
            elif oc['pcr'] <= 0.88 and p <= res: bear_s += 1; be_reasons.append(f"PCR {oc['pcr']} Bearish + Call Wall")
        else:
            if p > piv: bull_s += 1; b_reasons.append("Price sustained above Pivot")
            else: bear_s += 1; be_reasons.append("Price below Pivot")

        def star_txt(c): return "★" * c + "☆" * (5 - c)
        best_stars = max(bull_s, bear_s)
        is_buy, is_sell = bull_s >= 3, (bear_s >= 3 and bull_s < 3)

        st.markdown(f"""
        <div class="box" style="margin-bottom:10px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div><span class="box-lbl">NIFTY PRICE</span><div class="box-val c-blue">{p:.2f}</div></div>
                <div style="text-align:right;"><span class="box-lbl">CONFIDENCE</span><div class="stars">{star_txt(best_stars)} ({best_stars}/5)</div></div>
            </div>
            <div class="grid-3">
                <div class="box"><span class="box-lbl">SUPPORT</span><div class="box-val c-green">{sup:.0f}</div></div>
                <div class="box"><span class="box-lbl">PIVOT</span><div class="box-val c-amber">{piv:.0f}</div></div>
                <div class="box"><span class="box-lbl">RESISTANCE</span><div class="box-val c-red">{res:.0f}</div></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("#### 🎯 Execution Setups")

        if not is_buy and not is_sell:
            st.markdown(f"""
            <div class="trade-card block-card">
                <b style="color:#fbbf24; font-size:1rem;">⛔ NO TRADE ZONE: INSUFFICIENT CONFLUENCE</b>
                <p style="margin:4px 0 0 0; color:#cbd5e1; font-size:0.82rem;">Only scored {best_stars}/5 stars. Avoid trading choppy conditions until breakout above {res:.0f} or breakdown below {sup:.0f}.</p>
            </div>
            """, unsafe_allow_html=True)
        elif is_buy:
            sl = round(max(sup, p - (1.2 * atr)), 1)
            risk = round(max(p - sl, atr * 0.8), 1)
            t1, t2, t3 = round(p + risk, 1), round(p + (risk * rr), 1), round(p + (risk * (rr + 1)), 1)
            st.markdown(f"""
            <div class="trade-card call-card">
                <div style="display:flex; justify-content:space-between;"><b style="color:#10b981; font-size:1rem;">🟢 BUY {strike} CE</b><span class="stars">{star_txt(bull_s)} ({bull_s}/5)</span></div>
                <div class="grid-2">
                    <div class="box"><span class="box-lbl">ENTRY</span><div class="box-val c-blue">{p:.1f}</div></div>
                    <div class="box"><span class="box-lbl">STOP LOSS</span><div class="box-val c-red">{sl:.1f}</div></div>
                    <div class="box"><span class="box-lbl">TARGET 1</span><div class="box-val c-green">{t1:.1f}</div></div>
                    <div class="box"><span class="box-lbl">TARGET 2 ({rr}R)</span><div class="box-val c-green">{t2:.1f}</div></div>
                </div>
                <div style="margin-top:6px;">
                    <div class="lvl-row"><span>Target 3 (Runner):</span><b>{t3:.1f}</b></div>
                    <div class="lvl-row"><span>Max Risk ({lots} Qty):</span><b class="c-red">-₹{risk * lots:,.0f} ({risk} pts)</b></div>
                    <div class="lvl-row"><span>Est. Gain at T2:</span><b class="c-green">+₹{risk * rr * lots:,.0f} (+{risk * rr:.1f} pts)</b></div>
                </div>
                <ul style="margin:4px 0 0 16px; padding:0; color:#cbd5e1; font-size:0.75rem;">{''.join([f'<li>{r}</li>' for r in b_reasons])}</ul>
            </div>
            """, unsafe_allow_html=True)
        elif is_sell:
            sl = round(min(res, p + (1.2 * atr)), 1)
            risk = round(max(sl - p, atr * 0.8), 1)
            t1, t2, t3 = round(p - risk, 1), round(p - (risk * rr), 1), round(p - (risk * (rr + 1)), 1)
            st.markdown(f"""
            <div class="trade-card put-card">
                <div style="display:flex; justify-content:space-between;"><b style="color:#f43f5e; font-size:1rem;">🔴 BUY {strike} PE</b><span class="stars">{star_txt(bear_s)} ({bear_s}/5)</span></div>
                <div class="grid-2">
                    <div class="box"><span class="box-lbl">ENTRY</span><div class="box-val c-blue">{p:.1f}</div></div>
                    <div class="box"><span class="box-lbl">STOP LOSS</span><div class="box-val c-red">{sl:.1f}</div></div>
                    <div class="box"><span class="box-lbl">TARGET 1</span><div class="box-val c-green">{t1:.1f}</div></div>
                    <div class="box"><span class="box-lbl">TARGET 2 ({rr}R)</span><div class="box-val c-green">{t2:.1f}</div></div>
                </div>
                <div style="margin-top:6px;">
                    <div class="lvl-row"><span>Target 3 (Runner):</span><b>{t3:.1f}</b></div>
                    <div class="lvl-row"><span>Max Risk ({lots} Qty):</span><b class="c-red">-₹{risk * lots:,.0f} ({risk} pts)</b></div>
                    <div class="lvl-row"><span>Est. Gain at T2:</span><b class="c-green">+₹{risk * rr * lots:,.0f} (+{risk * rr:.1f} pts)</b></div>
                </div>
                <ul style="margin:4px 0 0 16px; padding:0; color:#cbd5e1; font-size:0.75rem;">{''.join([f'<li>{r}</li>' for r in be_reasons])}</ul>
            </div>
            """, unsafe_allow_html=True)

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
        fig.update_layout(height=440, margin=dict(l=5, r=5, t=10, b=10), xaxis_rangeslider_visible=False, template="plotly_dark", showlegend=False)
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    except Exception as e:
        st.error(f"Execution Error: {e}")
else:
    st.info("👆 Tap 'Tap to Upload Market Data' above to load your data.")
            
