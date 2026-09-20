import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yfinance as yf
import feedparser

# 1. Mobile Terminal Configuration
st.set_page_config(
    page_title="TradeLense AI",
    page_icon="⚡",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 2. High-Contrast Mobile Styling & Safe Top Padding
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@500;700;800&family=Plus+Jakarta+Sans:wght@600;700;800&display=swap');
    header[data-testid="stHeader"] { visibility: hidden !important; height: 0 !important; }
    html, body, [class*="css"], .stMarkdown {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        background-color: #07090e;
        color: #f1f5f9 !important;
    }
    .block-container {
        padding-top: 1.8rem !important;
        padding-bottom: 2.5rem !important;
        padding-left: 0.6rem !important;
        padding-right: 0.6rem !important;
    }
    .hero-banner {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 12px 14px;
        margin-bottom: 10px;
    }
    .hero-title {
        font-size: 1.35rem !important;
        font-weight: 800;
        color: #ffffff !important;
        margin: 0;
    }
    .hero-sub {
        font-size: 0.75rem;
        color: #94a3b8 !important;
        font-weight: 600;
    }
    .live-strip {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 8px;
        margin-bottom: 10px;
    }
    .card-ce {
        background: #062b20;
        border-left: 5px solid #10b981;
        border-radius: 10px;
        padding: 12px;
        margin-bottom: 10px;
    }
    .card-pe {
        background: #2d0c13;
        border-left: 5px solid #f43f5e;
        border-radius: 10px;
        padding: 12px;
        margin-bottom: 10px;
    }
    .card-no {
        background: #241703;
        border-left: 5px solid #f59e0b;
        border-radius: 10px;
        padding: 12px;
        margin-bottom: 10px;
    }
    .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin-top: 6px; }
    .grid-4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 4px; margin-top: 6px; }
    .tile {
        background: #090e17;
        border-radius: 8px;
        padding: 8px 10px;
        border: 1px solid #1e293b;
    }
    .lbl {
        font-size: 0.65rem;
        font-weight: 700;
        color: #94a3b8 !important;
        text-transform: uppercase;
    }
    .val {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.05rem;
        font-weight: 700;
    }
    .cg { color: #10b981 !important; }
    .cr { color: #f43f5e !important; }
    .cb { color: #38bdf8 !important; }
    .ca { color: #fbbf24 !important; }
    .row {
        display: flex;
        justify-content: space-between;
        padding: 5px 0;
        border-bottom: 1px solid #1e293b;
        font-size: 0.82rem;
        font-family: 'JetBrains Mono', monospace;
    }
    .row span { color: #94a3b8 !important; }
    .row b { color: #f8fafc !important; }
</style>

<div class="hero-banner">
    <div class="hero-title">⚡ TradeLense AI Terminal</div>
    <div class="hero-sub">Live Real-Time Market Ticker & Confluence Engine</div>
</div>
""", unsafe_allow_html=True)

# 3. Live Benchmark Bar (Always visible for both indices)
@st.cache_data(ttl=60)
def get_live_indices():
    res = {}
    for name, sym in [("NIFTY 50", "^NSEI"), ("BANK NIFTY", "^NSEBANK")]:
        try:
            t = yf.Ticker(sym)
            h = t.history(period="5d")
            if len(h) >= 2:
                ltp = float(h['Close'].iloc[-1])
                prev_c = float(h['Close'].iloc[-2])
                chg = ltp - prev_c
                pct = (chg / prev_c) * 100
                res[name] = {"ltp": ltp, "chg": chg, "pct": pct}
            else:
                res[name] = {"ltp": 0.0, "chg": 0.0, "pct": 0.0}
        except Exception:
            res[name] = {"ltp": 0.0, "chg": 0.0, "pct": 0.0}
    return res

live_idx = get_live_indices()

# Display Dual Live Index Ticker Cards
st.markdown(f"""
<div class="live-strip">
    <div class="tile">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <span class="lbl">NIFTY 50 (LIVE)</span>
            <span class="lbl {'cg' if live_idx['NIFTY 50']['chg'] >= 0 else 'cr'}">
                {live_idx['NIFTY 50']['pct']:+.2f}%
            </span>
        </div>
        <div class="val cb" style="font-size:1.15rem; margin-top:2px;">
            {live_idx['NIFTY 50']['ltp']:,.2f}
        </div>
    </div>
    <div class="tile">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <span class="lbl">BANK NIFTY (LIVE)</span>
            <span class="lbl {'cg' if live_idx['BANK NIFTY']['chg'] >= 0 else 'cr'}">
                {live_idx['BANK NIFTY']['pct']:+.2f}%
            </span>
        </div>
        <div class="val cb" style="font-size:1.15rem; margin-top:2px;">
            {live_idx['BANK NIFTY']['ltp']:,.2f}
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# 4. Target Instrument & Mode Selectors
col_s1, col_s2 = st.columns([1.2, 1])
with col_s1:
    inst = st.radio("Analyze Index", ["NIFTY 50", "BANK NIFTY"], horizontal=True)
with col_s2:
    mode = st.radio("Mode", ["⚡ Live Stream", "📁 Upload CSV"], horizontal=True)

sym = "^NSEI" if inst == "NIFTY 50" else "^NSEBANK"
step_k = 50 if inst == "NIFTY 50" else 100
lot_sz = 50 if inst == "NIFTY 50" else 15

if mode == "⚡ Live Stream":
    if st.button("🔄 Sync Live Feed", use_container_width=True, type="primary"):
        st.cache_data.clear()

# Global Markets & Sentiment
@st.cache_data(ttl=300)
def get_macro():
    d = {}
    for k, s in [("S&P 500", "^GSPC"), ("Nasdaq", "^IXIC"), ("Crude", "CL=F"), ("VIX", "^INDIAVIX")]:
        try:
            r = yf.download(s, period="2d", interval="1d", progress=False)
            if 'Close' in r.columns:
                c_s = r['Close']
                if isinstance(c_s, pd.DataFrame): c_s = c_s.iloc[:, 0]
                c_s = c_s.dropna()
                if len(c_s) >= 2:
                    pct = float(((c_s.iloc[-1] - c_s.iloc[-2]) / c_s.iloc[-2]) * 100)
                    d[k] = {"val": float(c_s.iloc[-1]), "pct": pct}
                else: d[k] = {"val": 0.0, "pct": 0.0}
            else: d[k] = {"val": 0.0, "pct": 0.0}
        except: d[k] = {"val": 0.0, "pct": 0.0}
    return d

@st.cache_data(ttl=600)
def get_news():
    f = feedparser.parse("https://news.google.com/rss/search?q=Nifty+stock+market&hl=en-IN&gl=IN&ceid=IN:en")
    s = sum(1 for e in f.entries[:5] if any(w in e.title.lower() for w in ['rally','surge','gain','record','growth','bull'])) - \
        sum(1 for e in f.entries[:5] if any(w in e.title.lower() for w in ['fall','plunge','slump','drop','inflation','war','bear']))
    headlines = [e.title for e in f.entries[:3]]
    return ("Bullish (+)" if s > 0 else ("Bearish (-)" if s < 0 else "Neutral")), headlines

macro = get_macro()
news_sent, headlines = get_news()

st.markdown(f"""
<div class="tile" style="margin-bottom:8px;">
    <div style="display:flex; justify-content:space-between;"><span class="lbl">🌐 GLOBAL MACRO</span><span class="lbl ca">NEWS: {news_sent}</span></div>
    <div class="grid-4">
        <div class="tile"><span class="lbl">S&P 500</span><div class="val {'cg' if macro['S&P 500']['pct']>=0 else 'cr'}" style="font-size:0.8rem;">{macro['S&P 500']['pct']:+.2f}%</div></div>
        <div class="tile"><span class="lbl">NASDAQ</span><div class="val {'cg' if macro['Nasdaq']['pct']>=0 else 'cr'}" style="font-size:0.8rem;">{macro['Nasdaq']['pct']:+.2f}%</div></div>
        <div class="tile"><span class="lbl">CRUDE</span><div class="val {'cr' if macro['Crude']['pct']>0 else 'cg'}" style="font-size:0.8rem;">{macro['Crude']['pct']:+.2f}%</div></div>
        <div class="tile"><span class="lbl">INDIA VIX</span><div class="val ca" style="font-size:0.8rem;">{macro['VIX']['val']:.2f}</div></div>
    </div>
</div>
""", unsafe_allow_html=True)

with st.expander("📰 Live Breaking Headlines", expanded=False):
    for h in headlines:
        st.markdown(f"• {h}")

# Data Ingestion & Option Chain
df, oc = None, None
with st.expander("📂 Option Chain & Data Uploader", expanded=(mode == "📁 Upload CSV")):
    if mode == "📁 Upload CSV":
        hf = st.file_uploader(f"1. Upload {inst} History (CSV)", key="h")
        if hf:
            df = pd.read_csv(hf)
            df.columns = [str(x).strip().lower() for x in df.columns]
            t = next((x for x in df.columns if 'time' in x or 'date' in x), df.columns[0])
            df['time'] = pd.to_datetime(df[t], errors='coerce')
            df = df.dropna(subset=['time']).sort_values('time').reset_index(drop=True)
    
    opf = st.file_uploader("2. Upload Option Chain (CSV / XLSX)", key="o")
    if opf:
        odf = pd.read_excel(opf) if opf.name.lower().endswith(('.xlsx', '.xls')) else pd.read_csv(opf)
        odf.columns = [str(x).strip().lower().replace(" ", "_") for x in odf.columns]
        c_c = next((x for x in odf.columns if 'ce' in x and 'oi' in x), None)
        p_c = next((x for x in odf.columns if 'pe' in x and 'oi' in x), None)
        s_c = next((x for x in odf.columns if 'strike' in x), None)
        if c_c and p_c and s_c:
            for x in [c_c, p_c, s_c]:
                odf[x] = pd.to_numeric(odf[x].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            pcr = round(odf[p_c].sum() / odf[c_c].sum(), 2) if odf[c_c].sum() > 0 else 1.0
            oc = {"pcr": pcr, "s": float(odf.loc[odf[p_c].idxmax(), s_c]), "r": float(odf.loc[odf[c_c].idxmax(), s_c])}

# Automated Live Fetch with Weekend Fallback
if mode == "⚡ Live Stream" and df is None:
    try:
        raw = yf.download(sym, period="5d", interval="5m", progress=False)
        if len(raw) < 10:
            raw = yf.download(sym, period="1mo", interval="1d", progress=False)
        
        if len(raw) > 5:
            if isinstance(raw.columns, pd.MultiIndex):
                raw.columns = [c[0].lower() for c in raw.columns]
            else:
                raw.columns = [c.lower() for c in raw.columns]
            raw = raw.reset_index()
            t_col = next((x for x in raw.columns if 'time' in x or 'date' in x), raw.columns[0])
            raw['time'] = pd.to_datetime(raw[t_col])
            df = raw.sort_values('time').reset_index(drop=True)
    except Exception as e:
        st.error(f"Live fetch error: {e}")

# Technical Analysis & Indicator Logic
if df is not None and len(df) > 5:
    for k in ['open', 'high', 'low', 'close']:
        m = next((x for x in df.columns if k in x or (k == 'close' and 'ltp' in x)), None)
        df[k] = pd.to_numeric(df[m].astype(str).str.replace(',', ''), errors='coerce') if m else df['close']

    df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
    
    chg = df['close'].diff()
    gain = chg.clip(lower=0).rolling(14).mean()
    loss = (-chg.clip(upper=0)).rolling(14).mean().replace(0, np.nan)
    df['rsi'] = (100 - (100 / (1 + (gain / loss)))).fillna(50)

    tr = pd.concat([
        df['high'] - df['low'],
        (df['high'] - df['close'].shift()).abs(),
        (df['low'] - df['close'].shift()).abs()
    ], axis=1).max(axis=1)
    df['atr'] = tr.rolling(14).mean().bfill()

    curr, prev = df.iloc[-1], df.iloc[-2]
    p = curr['close']
    atr = curr['atr'] if pd.notna(curr['atr']) and curr['atr'] > 0 else (p * 0.005)
    rsi = curr['rsi']

    piv = (prev['high'] + prev['low'] + prev['close']) / 3
    s1 = (2 * piv) - prev['high']
    r1 = (2 * piv) - prev['low']
    sup = oc['s'] if oc and oc['s'] < p else round(s1, 1)
    res = oc['r'] if oc and oc['r'] > p else round(r1, 1)
    strike = int(round(p / step_k) * step_k)

    b_s, be_s, b_reasons, be_reasons = 0, 0, [], []
    if curr['ema9'] > curr['ema21']:
        b_s += 1
        b_reasons.append("EMA 9 > EMA 21 (Bullish)")
    else:
        be_s += 1
        be_reasons.append("EMA 9 < EMA 21 (Bearish)")

    if p >= curr['ema50']:
        b_s += 1
        b_reasons.append("Above EMA 50 (Uptrend)")
    else:
        be_s += 1
        be_reasons.append("Below EMA 50 (Downtrend)")

    if 52 <= rsi <= 72:
        b_s += 1
        b_reasons.append(f"RSI ({rsi:.1f}) Momentum Zone")
    elif 28 <= rsi <= 48:
        be_s += 1
        be_reasons.append(f"RSI ({rsi:.1f}) Breakdown Zone")

    if curr['close'] > prev['high']:
        b_s += 1
        b_reasons.append("Price closed above previous candle high")
    elif curr['close'] < prev['low']:
        be_s += 1
        be_reasons.append("Price closed below previous candle low")

    if oc:
        if oc['pcr'] >= 1.05 and p >= sup:
            b_s += 1
            b_reasons.append(f"PCR {oc['pcr']} Bullish + Holding Put Wall")
        elif oc['pcr'] <= 0.88 and p <= res:
            be_s += 1
            be_reasons.append(f"PCR {oc['pcr']} Bearish + Resisting Call Wall")
    else:
        if p > piv:
            b_s += 1
            b_reasons.append("Price Sustained Above Central Pivot")
        else:
            be_s += 1
            be_reasons.append("Price Rejected Below Central Pivot")

    def stars(n): return "★" * n + "☆" * (5 - n)
    is_ce = b_s >= 3
    is_pe = be_s >= 3 and b_s < 3

    st.markdown(f"""
    <div class="tile" style="margin-bottom:10px;">
        <div style="display:flex; justify-content:space-between;">
            <span class="lbl">{inst} SPOT LEVEL</span>
            <span class="lbl">PIVOT: {piv:.0f}</span>
        </div>
        <div class="val cb" style="font-size:1.25rem;">{p:.2f}</div>
        <div class="grid-2" style="margin-top:4px;">
            <div class="tile"><span class="lbl">SUPPORT</span><div class="val cg">{sup:.0f}</div></div>
            <div class="tile"><span class="lbl">RESISTANCE</span><div class="val cr">{res:.0f}</div></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("#### 🎯 Execution Setups")
    if not is_ce and not is_pe:
        best_score = max(b_s, be_s)
        st.markdown(f"""
        <div class="card-no">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <b style="color:#fbbf24; font-size:1rem;">⛔ NO TRADE ZONE</b>
                <span class="ca" style="font-family:'JetBrains Mono'; font-weight:700;">{stars(best_score)} ({best_score}/5)</span>
            </div>
            <p style="margin:4px 0 0 0; font-size:0.82rem; color:#cbd5e1;">
                Indicators scored only <b>{best_score}/5 stars</b>. Market is consolidating between <b>{sup:.0f}</b> and <b>{res:.0f}</b>. Capital protection active.
            </p>
        </div>
        """, unsafe_allow_html=True)
    elif is_ce:
        sl = round(max(sup, p - (1.2 * atr)), 1)
        rk = round(max(p - sl, atr * 0.8), 1)
        st.markdown(f"""
        <div class="card-ce">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <b class="cg" style="font-size:1.05rem;">🟢 BUY {strike} CE</b>
                <span class="ca" style="font-family:'JetBrains Mono'; font-weight:700;">{stars(b_s)} ({b_s}/5)</span>
            </div>
            <div class="grid-2">
                <div class="tile"><span class="lbl">ENTRY TRIGGER</span><div class="val cb">{p:.1f}</div></div>
                <div class="tile"><span class="lbl">STOP LOSS</span><div class="val cr">{sl:.1f}</div></div>
                <div class="tile"><span class="lbl">TARGET 1</span><div class="val cg">{p+rk:.1f}</div></div>
                <div class="tile"><span class="lbl">TARGET 2 (2R)</span><div class="val cg">{p+(2*rk):.1f}</div></div>
            </div>
            <div style="margin-top:6px;">
                <div class="row"><span>Target 3 (Extension):</span><b>{p+(3*rk):.1f}</b></div>
                <div class="row"><span>Max Risk ({lot_sz} Qty):</span><b class="cr">-₹{rk*lot_sz:,.0f} ({rk} pts)</b></div>
                <div class="row"><span>Est. Gain at T2:</span><b class="cg">+₹{rk*2*lot_sz:,.0f} (+{rk*2:.1f} pts)</b></div>
            </div>
            <ul style="margin:4px 0 0 16px; padding:0; font-size:0.78rem; color:#cbd5e1;">
                {''.join(f'<li>{r}</li>' for r in b_reasons)}
            </ul>
        </div>
        """, unsafe_allow_html=True)
    elif is_pe:
        sl = round(min(res, p + (1.2 * atr)), 1)
        rk = round(max(sl - p, atr * 0.8), 1)
        st.markdown(f"""
        <div class="card-pe">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <b class="cr" style="font-size:1.05rem;">🔴 BUY {strike} PE</b>
                <span class="ca" style="font-family:'JetBrains Mono'; font-weight:700;">{stars(be_s)} ({be_s}/5)</span>
            </div>
            <div class="grid-2">
                <div class="tile"><span class="lbl">ENTRY TRIGGER</span><div class="val cb">{p:.1f}</div></div>
                <div class="tile"><span class="lbl">STOP LOSS</span><div class="val cr">{sl:.1f}</div></div>
                <div class="tile"><span class="lbl">TARGET 1</span><div class="val cg">{p-rk:.1f}</div></div>
                <div class="tile"><span class="lbl">TARGET 2 (2R)</span><div class="val cg">{p-(2*rk):.1f}</div></div>
            </div>
            <div style="margin-top:6px;">
                <div class="row"><span>Target 3 (Extension):</span><b>{p-(3*rk):.1f}</b></div>
                <div class="row"><span>Max Risk ({lot_sz} Qty):</span><b class="cr">-₹{rk*lot_sz:,.0f} ({rk} pts)</b></div>
                <div class="row"><span>Est. Gain at T2:</span><b class="cg">+₹{rk*2*lot_sz:,.0f} (+{rk*2:.1f} pts)</b></div>
            </div>
            <ul style="margin:4px 0 0 16px; padding:0; font-size:0.78rem; color:#cbd5e1;">
                {''.join(f'<li>{r}</li>' for r in be_reasons)}
            </ul>
        </div>
        """, unsafe_allow_html=True)

    # Candlestick & Indicator Chart
    st.markdown("#### 📈 Interactive Candlestick Chart")
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.72, 0.28])
    sub = df.tail(45)
    fig.add_trace(go.Candlestick(
        x=sub['time'], open=sub['open'], high=sub['high'], low=sub['low'], close=sub['close'],
        increasing_line_color='#10b981', decreasing_line_color='#f43f5e', name="Price"
    ), row=1, col=1)
    fig.add_trace(go.Scatter(x=sub['time'], y=sub['ema9'], line=dict(color='#38bdf8', width=1.5), name="EMA 9"), row=1, col=1)
    fig.add_trace(go.Scatter(x=sub['time'], y=sub['ema21'], line=dict(color='#f59e0b', width=1.5), name="EMA 21"), row=1, col=1)
    fig.add_hline(y=sup, line_dash="dash", line_color="#10b981", annotation_text=f"Sup {sup:.0f}", row=1, col=1)
    fig.add_hline(y=res, line_dash="dash", line_color="#f43f5e", annotation_text=f"Res {res:.0f}", row=1, col=1)
    fig.add_trace(go.Scatter(x=sub['time'], y=sub['rsi'], line=dict(color='#c084fc', width=1.5), name="RSI"), row=2, col=1)
    fig.add_hline(y=70, line_dash="dot", line_color="#f43f5e", row=2, col=1)
    fig.add_hline(y=30, line_dash="dot", line_color="#10b981", row=2, col=1)
    fig.update_layout(
        height=420,
        margin=dict(l=5, r=5, t=10, b=10),
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        paper_bgcolor="#07090e",
        plot_bgcolor="#07090e",
        showlegend=False
    )
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
else:
    st.info("Tap '⚡ Sync Live Feed' above or upload your data to run.")
    
