import streamlit as st, pandas as pd, numpy as np, plotly.graph_objects as go, yfinance as yf, feedparser, requests
from plotly.subplots import make_subplots
from datetime import datetime

st.set_page_config(page_title="TradeLense AI", page_icon="⚡", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@600;700;800&family=Plus+Jakarta+Sans:wght@600;700;800&display=swap');
    header[data-testid="stHeader"] { visibility: hidden !important; height: 0 !important; }
    html, body, [class*="css"], .stMarkdown { font-family: 'Plus Jakarta Sans', sans-serif !important; background: #07090e; color: #ffffff !important; }
    .block-container { padding: 1.8rem 0.6rem 2.5rem 0.6rem !important; }
    .banner { background: linear-gradient(135deg, #0f172a, #1e293b); border: 1px solid #334155; border-radius: 12px; padding: 12px; margin-bottom: 10px; }
    .news-card { background: #0d121c; border: 1px solid #1e293b; border-radius: 8px; padding: 8px 10px; margin-bottom: 6px; }
    .card-ce { background: #062b20; border-left: 5px solid #10b981; border-radius: 10px; padding: 14px; margin-bottom: 10px; border-top: 1px solid #10b98144; }
    .card-pe { background: #2d0c13; border-left: 5px solid #f43f5e; border-radius: 10px; padding: 14px; margin-bottom: 10px; border-top: 1px solid #f43f5e44; }
    .card-no { background: #241703; border-left: 5px solid #f59e0b; border-radius: 10px; padding: 14px; margin-bottom: 10px; border-top: 1px solid #f59e0b44; }
    .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin-top: 6px; }
    .grid-4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 4px; margin-top: 6px; }
    .tile { background: #090e17; border-radius: 8px; padding: 8px 10px; border: 1px solid #1e293b; }
    .lbl { font-size: 0.65rem; font-weight: 700; color: #94a3b8 !important; text-transform: uppercase; letter-spacing: 0.5px; }
    .val { font-family: 'JetBrains Mono', monospace; font-size: 1.05rem; font-weight: 700; }
    .cg { color: #10b981 !important; } .cr { color: #f43f5e !important; } .cb { color: #38bdf8 !important; } .ca { color: #fbbf24 !important; }
    .row { display: flex; justify-content: space-between; align-items: center; padding: 6px 0; border-bottom: 1px solid rgba(255,255,255,0.15); font-size: 0.84rem; font-family: 'JetBrains Mono', monospace; }
    .row span { color: #ffffff !important; font-weight: 700 !important; }
    .row b { font-weight: 800 !important; }
    .reasons-box { margin-top: 10px; padding-top: 8px; border-top: 1px solid rgba(255,255,255,0.2); }
    .reasons-box ul { margin: 4px 0 0 16px; padding: 0; font-size: 0.82rem; color: #ffffff !important; font-weight: 700; line-height: 1.45; }
    .reasons-box li { color: #ffffff !important; margin-bottom: 2px; }
</style>
<div class="banner">
    <div style="font-size:1.35rem; font-weight:800; color:#fff;">⚡ TradeLense AI Terminal</div>
    <div style="font-size:0.75rem; color:#94a3b8; font-weight:600;">Automated Live NSE Confluence & Execution Matrix</div>
</div>
""", unsafe_allow_html=True)

@st.cache_data(ttl=60)
def get_live_indices():
    res = {}
    for name, s in [("NIFTY 50", "^NSEI"), ("BANK NIFTY", "^NSEBANK")]:
        try:
            h = yf.Ticker(s).history(period="5d")
            if len(h) >= 2:
                ltp, prev_c = float(h['Close'].iloc[-1]), float(h['Close'].iloc[-2])
                res[name] = {"ltp": ltp, "pct": ((ltp - prev_c) / prev_c) * 100}
            else: res[name] = {"ltp": 0.0, "pct": 0.0}
        except: res[name] = {"ltp": 0.0, "pct": 0.0}
    return res

live_idx = get_live_indices()
st.markdown(f"""
<div class="grid-2" style="margin-bottom:10px;">
    <div class="tile"><div style="display:flex; justify-content:space-between;"><span class="lbl">NIFTY 50</span><span class="lbl {'cg' if live_idx['NIFTY 50']['pct']>=0 else 'cr'}">{live_idx['NIFTY 50']['pct']:+.2f}%</span></div><div class="val cb">{live_idx['NIFTY 50']['ltp']:,.2f}</div></div>
    <div class="tile"><div style="display:flex; justify-content:space-between;"><span class="lbl">BANK NIFTY</span><span class="lbl {'cg' if live_idx['BANK NIFTY']['pct']>=0 else 'cr'}">{live_idx['BANK NIFTY']['pct']:+.2f}%</span></div><div class="val cb">{live_idx['BANK NIFTY']['ltp']:,.2f}</div></div>
</div>
""", unsafe_allow_html=True)

c_top1, c_top2 = st.columns([1.2, 1])
inst = c_top1.radio("Target Index", ["NIFTY 50", "BANK NIFTY"], horizontal=True)
mode = c_top2.radio("Mode", ["⚡ Live Stream", "📁 Upload CSV"], horizontal=True)
sym, step_k, lot_sz, nse_sym = ("^NSEI", 50, 50, "NIFTY") if inst == "NIFTY 50" else ("^NSEBANK", 100, 15, "BANKNIFTY")

if mode == "⚡ Live Stream":
    c_btn, c_time = st.columns([1.2, 1])
    if c_btn.button("🔄 Sync Live Feed", use_container_width=True, type="primary"):
        st.cache_data.clear()
        st.rerun()
    c_time.caption(f"Synced: {datetime.now().strftime('%H:%M:%S')}")

@st.cache_data(ttl=180)
def get_macro():
    d = {}
    for k, s in [("S&P 500", "^GSPC"), ("Nasdaq", "^IXIC"), ("Crude", "CL=F"), ("VIX", "^INDIAVIX")]:
        try:
            r = yf.download(s, period="2d", interval="1d", progress=False)['Close'].dropna()
            if isinstance(r, pd.DataFrame): r = r.iloc[:, 0]
            d[k] = {"val": float(r.iloc[-1]), "pct": float(((r.iloc[-1] - r.iloc[-2]) / r.iloc[-2]) * 100) if len(r) >= 2 else 0.0}
        except: d[k] = {"val": 0.0, "pct": 0.0}
    return d

@st.cache_data(ttl=300)
def get_news_articles():
    f = feedparser.parse("https://news.google.com/rss/search?q=Nifty+Indian+stock+market&hl=en-IN&gl=IN&ceid=IN:en")
    items, bull_w, bear_w, score = [], ['rally','gain','surge','rate cut','record','high','jump'], ['fall','plunge','slump','inflation','war','drop'], 0
    for e in f.entries[:3]:
        t = e.title
        src = e.source.title if 'source' in e and 'title' in e.source else "FINANCE"
        is_p, is_n = any(w in t.lower() for w in bull_w), any(w in t.lower() for w in bear_w)
        if is_p: score += 1
        if is_n: score -= 1
        items.append({"title": t, "source": src, "tag": "🟢 Bullish" if is_p else ("🔴 Bearish" if is_n else "⚪ Neutral")})
    return ("Bullish (+)" if score > 0 else ("Bearish (-)" if score < 0 else "Neutral")), items

macro, (news_sent, news_items) = get_macro(), get_news_articles()
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

with st.expander("📰 Live Breaking Market Headlines", expanded=False):
    for itm in news_items:
        st.markdown(f"""<div class="news-card"><div style="display:flex; justify-content:space-between;"><span style="font-size:0.68rem; font-weight:700; color:#38bdf8;">{itm['source']}</span><span style="font-size:0.68rem; font-weight:700;">{itm['tag']}</span></div><div style="font-size:0.8rem; font-weight:600; color:#e2e8f0; margin-top:2px;">{itm['title']}</div></div>""", unsafe_allow_html=True)

@st.cache_data(ttl=180)
def fetch_nse_chain(symbol):
    try:
        s = requests.Session()
        hdrs = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36', 'Referer': 'https://www.nseindia.com/option-chain'}
        s.get("https://www.nseindia.com", headers=hdrs, timeout=5)
        resp = s.get(f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}", headers=hdrs, timeout=5)
        if resp.status_code == 200:
            recs = resp.json().get('filtered', {}).get('data', []) or resp.json().get('records', {}).get('data', [])
            t_ce, t_pe, m_ce, m_pe, r_s, s_s = 0, 0, 0, 0, 0, 0
            for r in recs:
                stk = r.get('strikePrice', 0)
                if 'CE' in r:
                    c = r['CE'].get('openInterest', 0); t_ce += c
                    if c > m_ce: m_ce, r_s = c, stk
                if 'PE' in r:
                    p = r['PE'].get('openInterest', 0); t_pe += p
                    if p > m_pe: m_pe, s_s = p, stk
            if t_ce > 0 and s_s > 0 and r_s > 0:
                return {"pcr": round(t_pe / t_ce, 2), "s": float(s_s), "r": float(r_s), "src": "NSE Live"}
    except: pass
    return None

oc = fetch_nse_chain(nse_sym) if mode == "⚡ Live Stream" else None
df = None

with st.expander("📂 Option Chain & Data Uploader (Optional)", expanded=(mode == "📁 Upload CSV")):
    if mode == "📁 Upload CSV":
        hf = st.file_uploader(f"1. Upload {inst} History (CSV)", key="h")
        if hf:
            df = pd.read_csv(hf)
            df.columns = [str(x).strip().lower() for x in df.columns]
            t = next((x for x in df.columns if 'time' in x or 'date' in x), df.columns[0])
            df['time'] = pd.to_datetime(df[t], errors='coerce')
            df = df.dropna(subset=['time']).sort_values('time').reset_index(drop=True)
    opf = st.file_uploader("2. Override Option Chain (CSV / XLSX)", key="o")
    if opf:
        odf = pd.read_excel(opf) if opf.name.lower().endswith(('.xlsx', '.xls')) else pd.read_csv(opf)
        odf.columns = [str(x).strip().lower().replace(" ", "_") for x in odf.columns]
        c_c, p_c, s_c = next((x for x in odf.columns if 'ce' in x and 'oi' in x), None), next((x for x in odf.columns if 'pe' in x and 'oi' in x), None), next((x for x in odf.columns if 'strike' in x), None)
        if c_c and p_c and s_c:
            for x in [c_c, p_c, s_c]: odf[x] = pd.to_numeric(odf[x].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            pcr = round(odf[p_c].sum() / odf[c_c].sum(), 2) if odf[c_c].sum() > 0 else 1.0
            oc = {"pcr": pcr, "s": float(odf.loc[odf[p_c].idxmax(), s_c]), "r": float(odf.loc[odf[c_c].idxmax(), s_c]), "src": "Manual File"}

if mode == "⚡ Live Stream" and df is None:
    try:
        raw = yf.download(sym, period="5d", interval="5m", progress=False)
        if len(raw) < 10: raw = yf.download(sym, period="1mo", interval="1d", progress=False)
        if len(raw) > 5:
            raw.columns = [c[0].lower() if isinstance(c, tuple) else c.lower() for c in raw.columns]
            raw = raw.reset_index()
            t_col = next((x for x in raw.columns if 'time' in x or 'date' in x), raw.columns[0])
            raw['time'] = pd.to_datetime(raw[t_col])
            df = raw.sort_values('time').reset_index(drop=True)
    except: pass

if df is not None and len(df) > 5:
    for k in ['open', 'high', 'low', 'close']:
        m = next((x for x in df.columns if k in x or (k == 'close' and 'ltp' in x)), None)
        df[k] = pd.to_numeric(df[m].astype(str).str.replace(',', ''), errors='coerce') if m else df['close']
    df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
    chg = df['close'].diff()
    df['rsi'] = (100 - (100 / (1 + (chg.clip(lower=0).rolling(14).mean() / (-chg.clip(upper=0)).rolling(14).mean().replace(0, np.nan))))).fillna(50)
    tr = pd.concat([df['high'] - df['low'], (df['high'] - df['close'].shift()).abs(), (df['low'] - df['close'].shift()).abs()], axis=1).max(axis=1)
    df['atr'] = tr.rolling(14).mean().bfill()
    curr, prev = df.iloc[-1], df.iloc[-2]
    p, atr, rsi = curr['close'], curr['atr'] if pd.notna(curr['atr']) and curr['atr'] > 0 else curr['close'] * 0.005, curr['rsi']
    prev_h, prev_l = max(prev['high'], p + (0.5 * atr)), min(prev['low'], p - (0.5 * atr))
    piv = (prev_h + prev_l + curr['close']) / 3
    sup = oc['s'] if oc and oc['s'] < p else round(min((2 * piv) - prev_h, p - (0.8 * atr)), 1)
    res = oc['r'] if oc and oc['r'] > p else round(max((2 * piv) - prev_l, p + (0.8 * atr)), 1)
    strike = int(round(p / step_k) * step_k)

    b_s, be_s, b_reasons, be_reasons = 0, 0, [], []
    if curr['ema9'] > curr['ema21']: b_s += 1; b_reasons.append("EMA 9 > EMA 21 (Bullish Momentum)")
    else: be_s += 1; be_reasons.append("EMA 9 < EMA 21 (Bearish Momentum)")
    if p >= curr['ema50']: b_s += 1; b_reasons.append("Price Above EMA 50 (Macro Uptrend)")
    else: be_s += 1; be_reasons.append("Price Below EMA 50 (Macro Downtrend)")
    if 52 <= rsi <= 72: b_s += 1; b_reasons.append(f"RSI ({rsi:.1f}) in Bullish Acceleration")
    elif 28 <= rsi <= 48: be_s += 1; be_reasons.append(f"RSI ({rsi:.1f}) in Bearish Breakdown")
    if curr['close'] > prev['high']: b_s += 1; b_reasons.append("Candle closed above previous high")
    elif curr['close'] < prev['low']: be_s += 1; be_reasons.append("Candle closed below previous low")
    if oc:
        src_tag = oc.get('src', 'NSE')
        if oc['pcr'] >= 1.05 and p >= sup: b_s += 1; b_reasons.append(f"{src_tag} PCR {oc['pcr']} Bullish + Put Support ({sup:.0f})")
        elif oc['pcr'] <= 0.88 and p <= res: be_s += 1; be_reasons.append(f"{src_tag} PCR {oc['pcr']} Bearish + Call Wall ({res:.0f})")
        else: b_reasons.append(f"{src_tag} PCR {oc['pcr']} Neutral / Rangebound"); be_reasons.append(f"{src_tag} PCR {oc['pcr']} Neutral / Rangebound")
    else:
        if p > piv: b_s += 1; b_reasons.append("Price sustained above Central Pivot")
        else: be_s += 1; be_reasons.append("Price rejected below Central Pivot")

    def stars(n): return "★" * n + "☆" * (5 - n)
    is_ce, is_pe = b_s >= 3, (be_s >= 3 and b_s < 3)
    oc_badge = f"<span class='cg'>● {oc['src']} (PCR: {oc['pcr']})</span>" if oc else "<span class='ca'>● Dynamic Pivot Mode</span>"

    st.markdown(f"""
    <div class="tile" style="margin-bottom:10px;">
        <div style="display:flex; justify-content:space-between; align-items:center;"><span class="lbl">{inst} SPOT LEVEL</span><span class="lbl">CHAIN: {oc_badge}</span></div>
        <div class="val cb" style="font-size:1.25rem; margin-top:2px;">{p:.2f}</div>
        <div class="grid-2" style="margin-top:4px;">
            <div class="tile"><span class="lbl">SUPPORT (PE WALL)</span><div class="val cg">{sup:.0f}</div></div>
            <div class="tile"><span class="lbl">RESISTANCE (CE WALL)</span><div class="val cr">{res:.0f}</div></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("#### 🎯 Execution Setups")
    if not is_ce and not is_pe:
        best_sc = max(b_s, be_s)
        st.markdown(f"""<div class="card-no"><div style="display:flex; justify-content:space-between;"><b style="color:#fbbf24;">⛔ NO TRADE ZONE</b><span class="ca" style="font-family:'JetBrains Mono';">{stars(best_sc)} ({best_sc}/5)</span></div><p style="margin:4px 0 0 0; font-size:0.84rem; color:#ffffff; font-weight:700;">Indicators scored only {best_sc}/5 stars. Rangebound between {sup:.0f} and {res:.0f}. Capital protection active.</p></div>""", unsafe_allow_html=True)
    elif is_ce:
        sl, rk = round(max(sup, p - (1.2 * atr)), 1), round(max(p - round(max(sup, p - (1.2 * atr)), 1), atr * 0.8), 1)
        st.markdown(f"""
        <div class="card-ce">
            <div style="display:flex; justify-content:space-between;"><b class="cg" style="font-size:1.05rem;">🟢 BUY {strike} CE</b><span class="ca" style="font-family:'JetBrains Mono'; font-weight:700;">{stars(b_s)} ({b_s}/5)</span></div>
            <div class="grid-2"><div class="tile"><span class="lbl">ENTRY TRIGGER</span><div class="val cb">{p:.1f}</div></div><div class="tile"><span class="lbl">STOP LOSS</span><div class="val cr">{sl:.1f}</div></div><div class="tile"><span class="lbl">TARGET 1</span><div class="val cg">{p+rk:.1f}</div></div><div class="tile"><span class="lbl">TARGET 2 (2R)</span><div class="val cg">{p+(2*rk):.1f}</div></div></div>
            <div style="margin-top:8px;"><div class="row"><span>Target 3 (Extension):</span><b class="cg">{p+(3*rk):.1f}</b></div><div class="row"><span>Max Risk ({lot_sz} Qty):</span><b class="cr">-₹{rk*lot_sz:,.0f} ({rk} pts)</b></div><div class="row"><span>Est. Gain at T2:</span><b class="cg">+₹{rk*2*lot_sz:,.0f} (+{rk*2:.1f} pts)</b></div></div>
            <div class="reasons-box"><span class="lbl" style="color:#ffffff !important;">WHY THIS CALL (CONFIRMING PILLARS):</span><ul>{''.join(f'<li>{r}</li>' for r in b_reasons)}</ul></div>
        </div>
        """, unsafe_allow_html=True)
    elif is_pe:
        sl, rk = round(min(res, p + (1.2 * atr)), 1), round(max(round(min(res, p + (1.2 * atr)), 1) - p, atr * 0.8), 1)
        st.markdown(f"""
        <div class="card-pe">
            <div style="display:flex; justify-content:space-between;"><b class="cr" style="font-size:1.05rem;">🔴 BUY {strike} PE</b><span class="ca" style="font-family:'JetBrains Mono'; font-weight:700;">{stars(be_s)} ({be_s}/5)</span></div>
            <div class="grid-2"><div class="tile"><span class="lbl">ENTRY TRIGGER</span><div class="val cb">{p:.1f}</div></div><div class="tile"><span class="lbl">STOP LOSS</span><div class="val cr">{sl:.1f}</div></div><div class="tile"><span class="lbl">TARGET 1</span><div class="val cg">{p-rk:.1f}</div></div><div class="tile"><span class="lbl">TARGET 2 (2R)</span><div class="val cg">{p-(2*rk):.1f}</div></div></div>
            <div style="margin-top:8px;"><div class="row"><span>Target 3 (Extension):</span><b class="cg">{p-(3*rk):.1f}</b></div><div class="row"><span>Max Risk ({lot_sz} Qty):</span><b class="cr">-₹{rk*lot_sz:,.0f} ({rk} pts)</b></div><div class="row"><span>Est. Gain at T2:</span><b class="cg">+₹{rk*2*lot_sz:,.0f} (+{rk*2:.1f} pts)</b></div></div>
            <div class="reasons-box"><span class="lbl" style="color:#ffffff !important;">WHY THIS CALL (CONFIRMING PILLARS):</span><ul>{''.join(f'<li>{r}</li>' for r in be_reasons)}</ul></div>
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
    fig.update_layout(height=420, margin=dict(l=5, r=5, t=10, b=10), xaxis_rangeslider_visible=False, template="plotly_dark", paper_bgcolor="#07090e", plot_bgcolor="#07090e", showlegend=False)
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
else:
    st.info("Tap '🔄 Sync Live Feed' above to pull live market data.")
    
