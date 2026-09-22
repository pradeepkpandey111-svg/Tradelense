import streamlit as st, pandas as pd, numpy as np, plotly.graph_objects as go, yfinance as yf, feedparser, requests
from plotly.subplots import make_subplots
from streamlit_autorefresh import st_autorefresh
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))

st.set_page_config(page_title="TradeLense AI", page_icon="⚡", layout="centered", initial_sidebar_state="collapsed")
st.markdown("""<style>
header[data-testid="stHeader"]{visibility:hidden!important;height:0!important;}
html,body,[class*="css"],.stMarkdown{font-family:'Plus Jakarta Sans',sans-serif!important;background:#07090e;color:#fff!important;}
.block-container{padding:1.8rem 0.6rem 2.5rem 0.6rem!important;}
.banner{background:linear-gradient(135deg,#0f172a,#1e293b);border:1px solid #334155;border-radius:12px;padding:12px;margin-bottom:8px;}
.news-box{background:#0d121c;border:1px solid #1e293b;border-radius:8px;padding:8px 10px;margin-bottom:6px;}
.news-meta{display:flex;justify-content:space-between;align-items:center;margin-bottom:2px;}
.news-pub{font-size:0.68rem;font-weight:700;color:#38bdf8;text-transform:uppercase;}
.news-tag{font-size:0.68rem;font-weight:700;}
.news-headline{font-size:0.82rem;font-weight:600;color:#e2e8f0;line-height:1.35;}
.card-ce{background:#062b20;border-left:5px solid #10b981;border-radius:10px;padding:12px;margin-bottom:8px;}
.card-pe{background:#2d0c13;border-left:5px solid #f43f5e;border-radius:10px;padding:12px;margin-bottom:8px;}
.card-no{background:#241703;border-left:5px solid #f59e0b;border-radius:10px;padding:12px;margin-bottom:8px;}
.card-locked{background:#0c1a2b;border-left:5px solid #38bdf8;border-radius:10px;padding:12px;margin-bottom:8px;}
.g2{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:4px;}
.g4{display:grid;grid-template-columns:repeat(4,1fr);gap:4px;margin-top:4px;}
.tile{background:#090e17;border-radius:8px;padding:8px 10px;border:1px solid #1e293b;}
.lbl{font-size:0.65rem;font-weight:700;color:#94a3b8!important;text-transform:uppercase;}
.val{font-family:monospace;font-size:1rem;font-weight:700;}
.cg{color:#10b981!important;}.cr{color:#f43f5e!important;}.cb{color:#38bdf8!important;}.ca{color:#fbbf24!important;}
.rw{display:flex;justify-content:space-between;align-items:center;padding:5px 0;border-bottom:1px solid rgba(255,255,255,0.15);font-size:0.82rem;font-family:monospace;}
.rw span{color:#fff!important;font-weight:700!important;}
.reasons{margin-top:8px;padding-top:6px;border-top:1px solid rgba(255,255,255,0.2);font-size:0.8rem;color:#fff!important;font-weight:700;}
</style><div class="banner"><div style="font-size:1.3rem;font-weight:800;">⚡ TradeLense AI Terminal</div><div style="font-size:0.75rem;color:#94a3b8;">Automated Confluence & Clear Entry/Exit Levels</div></div>""", unsafe_allow_html=True)

# ---------- SESSION STATE: locked position survives every auto-refresh ----------
if "position" not in st.session_state:
    st.session_state.position = None   # dict once a call is live, else None

@st.cache_data(ttl=60)
def get_idx():
    res = {}
    for n, s in [("NIFTY 50", "^NSEI"), ("BANK NIFTY", "^NSEBANK")]:
        try:
            h = yf.Ticker(s).history(period="5d")
            p, pr = float(h['Close'].iloc[-1]), float(h['Close'].iloc[-2])
            res[n] = {"ltp": p, "pct": ((p - pr) / pr) * 100}
        except: res[n] = {"ltp": 0.0, "pct": 0.0}
    return res

l_idx = get_idx()
st.markdown(f"""<div class="g2" style="margin-bottom:8px;">
<div class="tile"><div style="display:flex;justify-content:space-between;"><span class="lbl">NIFTY 50</span><span class="lbl {'cg' if l_idx['NIFTY 50']['pct']>=0 else 'cr'}">{l_idx['NIFTY 50']['pct']:+.2f}%</span></div><div class="val cb">{l_idx['NIFTY 50']['ltp']:,.2f}</div></div>
<div class="tile"><div style="display:flex;justify-content:space-between;"><span class="lbl">BANK NIFTY</span><span class="lbl {'cg' if l_idx['BANK NIFTY']['pct']>=0 else 'cr'}">{l_idx['BANK NIFTY']['pct']:+.2f}%</span></div><div class="val cb">{l_idx['BANK NIFTY']['ltp']:,.2f}</div></div>
</div>""", unsafe_allow_html=True)

c1, c2 = st.columns([1.2, 1])
inst = c1.radio("Target Index", ["NIFTY 50", "BANK NIFTY"], horizontal=True)
mode = c2.radio("Mode", ["⚡ Live Stream", "📁 Upload CSV"], horizontal=True)
sym, step_k, lot_sz, nse_sym = ("^NSEI", 50, 50, "NIFTY") if inst == "NIFTY 50" else ("^NSEBANK", 100, 15, "BANKNIFTY")

# ---------- REAL AUTO-SYNC ----------
if mode == "⚡ Live Stream":
    a1, a2, a3 = st.columns([1, 1, 1.4])
    auto_on = a1.toggle("Auto-sync", value=True)
    refresh_sec = a2.selectbox("Every", [10, 15, 30, 60], index=1, format_func=lambda x: f"{x}s")
    if auto_on:
        st_autorefresh(interval=refresh_sec * 1000, key="live_refresh")
    if a3.button("🔄 Sync Now", use_container_width=True, type="primary"):
        st.cache_data.clear(); st.rerun()
    ist_now = datetime.now(IST).strftime("%d-%b-%Y | %I:%M:%S %p")
    st.markdown(f"<div style='font-size:0.75rem; color:#94a3b8; font-weight:700; margin-top:2px;'>🕒 Synced: <span style='color:#38bdf8;'>{ist_now}</span>{' · auto-sync every '+str(refresh_sec)+'s' if auto_on else ' · auto-sync off'}</div>", unsafe_allow_html=True)
    st.caption("⚠️ 3-second refresh isn't offered on purpose — that fast, you'd be reacting to noise inside a single forming candle, not a real signal change. 10–15s is fast enough to stay current without chasing flicker.")

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
def get_news_styled():
    f = feedparser.parse("https://news.google.com/rss/search?q=Nifty+Indian+stock+market&hl=en-IN&gl=IN&ceid=IN:en")
    items, b_w, be_w, sc = [], ['rally','gain','surge','rate cut','high','jump'], ['fall','plunge','slump','inflation','drop','war'], 0
    for e in f.entries[:3]:
        t = e.title
        src = e.source.title if 'source' in e and 'title' in e.source else "FINANCE"
        p = any(w in t.lower() for w in b_w); n = any(w in t.lower() for w in be_w)
        if p: sc += 1
        if n: sc -= 1
        tag = "<span class='cg'>🟢 Bullish</span>" if p else ("<span class='cr'>🔴 Bearish</span>" if n else "<span class='ca'>⚪ Neutral</span>")
        items.append({"title": t, "source": src, "tag": tag})
    return ("Bullish (+)" if sc > 0 else ("Bearish (-)" if sc < 0 else "Neutral")), items

mac, (ns_sent, news_cards) = get_macro(), get_news_styled()
st.markdown(f"""<div class="tile" style="margin-bottom:8px;"><div style="display:flex;justify-content:space-between;"><span class="lbl">🌐 GLOBAL MACRO</span><span class="lbl ca">NEWS: {ns_sent}</span></div><div class="g4">
<div class="tile"><span class="lbl">S&P 500</span><div class="val {'cg' if mac['S&P 500']['pct']>=0 else 'cr'}" style="font-size:0.8rem;">{mac['S&P 500']['pct']:+.2f}%</div></div>
<div class="tile"><span class="lbl">NASDAQ</span><div class="val {'cg' if mac['Nasdaq']['pct']>=0 else 'cr'}" style="font-size:0.8rem;">{mac['Nasdaq']['pct']:+.2f}%</div></div>
<div class="tile"><span class="lbl">CRUDE</span><div class="val {'cr' if mac['Crude']['pct']>0 else 'cg'}" style="font-size:0.8rem;">{mac['Crude']['pct']:+.2f}%</div></div>
<div class="tile"><span class="lbl">INDIA VIX</span><div class="val ca" style="font-size:0.8rem;">{mac['VIX']['val']:.2f}</div></div>
</div></div>""", unsafe_allow_html=True)

with st.expander("📰 Live Breaking Market Headlines", expanded=False):
    for itm in news_cards:
        st.markdown(f"""<div class="news-box"><div class="news-meta"><span class="news-pub">{itm['source']}</span><span class="news-tag">{itm['tag']}</span></div><div class="news-headline">{itm['title']}</div></div>""", unsafe_allow_html=True)

@st.cache_data(ttl=180)
def fetch_chain(s_sym):
    try:
        s = requests.Session()
        h = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36', 'Referer': 'https://www.nseindia.com/option-chain'}
        s.get("https://www.nseindia.com", headers=h, timeout=5)
        resp = s.get(f"https://www.nseindia.com/api/option-chain-indices?symbol={s_sym}", headers=h, timeout=5)
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
            if t_ce > 0 and s_s > 0 and r_s > 0: return {"pcr": round(t_pe / t_ce, 2), "s": float(s_s), "r": float(r_s), "src": "NSE Live"}
    except: pass
    return None

oc = fetch_chain(nse_sym) if mode == "⚡ Live Stream" else None
df = None

if mode == "📁 Upload CSV":
    with st.expander(f"📂 Upload Data for {inst}", expanded=True):
        hf = st.file_uploader(f"1. Upload {inst} Historical Candles (CSV)", key="hist_upload")
        if hf:
            df = pd.read_csv(hf); df.columns = [str(x).strip().lower() for x in df.columns]
            t = next((x for x in df.columns if 'time' in x or 'date' in x), df.columns[0])
            df['time'] = pd.to_datetime(df[t], errors='coerce')
            df = df.dropna(subset=['time']).sort_values('time').reset_index(drop=True)
            st.success(f"✓ Loaded {len(df)} candles for {inst}")

        opf = st.file_uploader(f"2. Upload {inst} Option Chain (CSV / XLSX)", key="oc_upload")
        if opf:
            odf = pd.read_excel(opf) if opf.name.lower().endswith(('.xlsx', '.xls')) else pd.read_csv(opf)
            odf.columns = [str(x).strip().lower().replace(" ", "_") for x in odf.columns]
            c_c, p_c, s_c = next((x for x in odf.columns if 'ce' in x and 'oi' in x), None), next((x for x in odf.columns if 'pe' in x and 'oi' in x), None), next((x for x in odf.columns if 'strike' in x), None)
            if c_c and p_c and s_c:
                for x in [c_c, p_c, s_c]: odf[x] = pd.to_numeric(odf[x].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
                pcr = round(odf[p_c].sum() / odf[c_c].sum(), 2) if odf[c_c].sum() > 0 else 1.0
                oc = {"pcr": pcr, "s": float(odf.loc[odf[p_c].idxmax(), s_c]), "r": float(odf.loc[odf[c_c].idxmax(), s_c]), "src": "Manual File"}
                st.success(f"✓ Loaded {inst} Option Chain (PCR: {pcr})")

if mode == "⚡ Live Stream" and df is None:
    try:
        raw = yf.download(sym, period="5d", interval="5m", progress=False)
        if len(raw) < 10: raw = yf.download(sym, period="1mo", interval="1d", progress=False)
        if len(raw) > 5:
            raw.columns = [c[0].lower() if isinstance(c, tuple) else c.lower() for c in raw.columns]
            raw = raw.reset_index(); t_c = next((x for x in raw.columns if 'time' in x or 'date' in x), raw.columns[0])
            raw['time'] = pd.to_datetime(raw[t_c]); df = raw.sort_values('time').reset_index(drop=True)
    except: pass
        if df is not None and len(df) > 6:
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

    # ---------- FIX: score off the LAST FULLY CLOSED candle, not a candle still forming ----------
    sig_idx = -2 if (mode == "⚡ Live Stream" and len(df) >= 10) else -1
    curr, prev = df.iloc[sig_idx], df.iloc[sig_idx - 1]
    live_price = float(df['close'].iloc[-1])   # true latest price, used for spot display and P&L only

    p = live_price
    atr = curr['atr'] if pd.notna(curr['atr']) and curr['atr'] > 0 else curr['close'] * 0.005
    rsi = curr['rsi']
    prev_h, prev_l = max(prev['high'], curr['close'] + (0.5 * atr)), min(prev['low'], curr['close'] - (0.5 * atr))
    piv = (prev_h + prev_l + curr['close']) / 3
    sup = oc['s'] if oc and oc['s'] < p else round(min((2 * piv) - prev_h, p - (0.8 * atr)), 1)
    res = oc['r'] if oc and oc['r'] > p else round(max((2 * piv) - prev_l, p + (0.8 * atr)), 1)
    strike = int(round(p / step_k) * step_k)

    buf = round(max(2.0, atr * 0.20), 1)
    ce_entry, pe_entry = round(max(curr['high'] + buf, curr['close'] + 2.0), 1), round(min(curr['low'] - buf, curr['close'] - 2.0), 1)

    def stars(n): return "★" * n + "☆" * (5 - n)
    oc_badge = f"<span class='cg'>● {oc['src']} (PCR: {oc['pcr']})</span>" if oc else "<span class='ca'>● Dynamic Pivot</span>"

    st.markdown(f"""<div class="tile" style="margin-bottom:8px;">
    <div style="display:flex;justify-content:space-between;"><span class="lbl">{inst} CURRENT SPOT</span><span class="lbl">CHAIN: {oc_badge}</span></div>
    <div class="val cb" style="font-size:1.25rem;">{p:.2f}</div>
    <div class="g2"><div class="tile"><span class="lbl">SUPPORT (PE WALL)</span><div class="val cg">{sup:.0f}</div></div><div class="tile"><span class="lbl">RESISTANCE (CE WALL)</span><div class="val cr">{res:.0f}</div></div></div>
    </div>""", unsafe_allow_html=True)

    st.markdown("#### 🎯 Execution Setup")

    # ---------- FIX: if a call is already live, track it — do NOT recompute a new one ----------
    pos = st.session_state.position
    if pos is not None and pos.get('status') == 'open':
        if pos['type'] == 'CE':
            pnl_pts = live_price - pos['entry']
            if live_price <= pos['sl']:
                pos['status'] = 'SL Hit'; pos['exit_price'] = pos['sl']
            elif live_price >= pos['t2']:
                pos['status'] = 'Target 2 Hit'; pos['exit_price'] = pos['t2']
            elif live_price >= pos['t1'] and not pos.get('t1_hit'):
                pos['t1_hit'] = True; pos['sl'] = pos['entry']
        else:
            pnl_pts = pos['entry'] - live_price
            if live_price >= pos['sl']:
                pos['status'] = 'SL Hit'; pos['exit_price'] = pos['sl']
            elif live_price <= pos['t2']:
                pos['status'] = 'Target 2 Hit'; pos['exit_price'] = pos['t2']
            elif live_price <= pos['t1'] and not pos.get('t1_hit'):
                pos['t1_hit'] = True; pos['sl'] = pos['entry']
        st.session_state.position = pos
        pnl_rs = pnl_pts * lot_sz
        col = 'cg' if pnl_pts >= 0 else 'cr'
        badge = "🟢 CE" if pos['type'] == 'CE' else "🔴 PE"
        st.markdown(f"""<div class="card-locked">
            <div style="display:flex;justify-content:space-between;"><b style="font-size:1.1rem;">📌 TRACKING: {badge} {pos['strike']}</b><span class="ca">Entry {pos['entry']:.1f}</span></div>
            <div class="g2">
                <div class="tile"><span class="lbl">LIVE P&L ({lot_sz} qty)</span><div class="val {col}">{pnl_pts:+.1f} pts (₹{pnl_rs:+,.0f})</div></div>
                <div class="tile"><span class="lbl">CURRENT SL</span><div class="val ca">{pos['sl']:.1f}{' · trailed to cost' if pos.get('t1_hit') else ''}</div></div>
            </div>
            <div class="reasons">Targets: T1 {pos['t1']:.1f} · T2 {pos['t2']:.1f}. This call stays locked — it will not silently change to a new suggestion while it's open.</div>
        </div>""", unsafe_allow_html=True)
        if st.button("✖ Close this position manually", use_container_width=True):
            st.session_state.position = None; st.rerun()

    elif pos is not None:  # SL or Target hit — show result, wait for user to clear it
        realized_pts = (pos['exit_price'] - pos['entry']) if pos['type'] == 'CE' else (pos['entry'] - pos['exit_price'])
        realized_rs = realized_pts * lot_sz
        col = 'cg' if realized_pts >= 0 else 'cr'
        icon = "✅" if realized_pts >= 0 else "🛑"
        st.markdown(f"""<div class="card-locked">
            <div style="display:flex;justify-content:space-between;"><b style="font-size:1.1rem;">{icon} {pos['status']}</b><span class="ca">{pos['type']} {pos['strike']}</span></div>
            <div class="tile"><span class="lbl">REALIZED RESULT ({lot_sz} qty)</span><div class="val {col}">{realized_pts:+.1f} pts (₹{realized_rs:+,.0f})</div></div>
        </div>""", unsafe_allow_html=True)
        if st.button("🔍 Start looking for the next setup", use_container_width=True, type="primary"):
            st.session_state.position = None; st.rerun()

    else:
        # No open position — safe to evaluate a fresh signal off the last CLOSED candle
        b_s, be_s, b_reasons, be_reasons = 0, 0, [], []
        if curr['ema9'] > curr['ema21']: b_s += 1; b_reasons.append("EMA 9 > EMA 21 (Bullish)")
        else: be_s += 1; be_reasons.append("EMA 9 < EMA 21 (Bearish)")
        if curr['close'] >= curr['ema50']: b_s += 1; b_reasons.append("Price Above EMA 50 (Uptrend)")
        else: be_s += 1; be_reasons.append("Price Below EMA 50 (Downtrend)")
        if 52 <= rsi <= 72: b_s += 1; b_reasons.append(f"RSI ({rsi:.1f}) Bullish")
        elif 28 <= rsi <= 48: be_s += 1; be_reasons.append(f"RSI ({rsi:.1f}) Bearish")
        if curr['close'] > prev['high']: b_s += 1; b_reasons.append("Candle closed above previous high")
        elif curr['close'] < prev['low']: be_s += 1; be_reasons.append("Candle closed below previous low")
        if oc:
            stg = oc.get('src', 'NSE')
            if oc['pcr'] >= 1.05 and p >= sup: b_s += 1; b_reasons.append(f"{stg} PCR {oc['pcr']} Bullish")
            elif oc['pcr'] <= 0.88 and p <= res: be_s += 1; be_reasons.append(f"{stg} PCR {oc['pcr']} Bearish")
            else: b_reasons.append(f"{stg} PCR {oc['pcr']} Neutral"); be_reasons.append(f"{stg} PCR {oc['pcr']} Neutral")
        else:
            if p > piv: b_s += 1; b_reasons.append("Above Central Pivot")
            else: be_s += 1; be_reasons.append("Below Central Pivot")

        is_ce, is_pe = b_s >= 3, (be_s >= 3 and b_s < 3)

        if not is_ce and not is_pe:
            best_sc = max(b_s, be_s)
            st.markdown(f"""<div class="card-no"><div style="display:flex;justify-content:space-between;"><b style="color:#fbbf24;">⛔ NO TRADE ZONE</b><span class="ca">{stars(best_sc)} ({best_sc}/5)</span></div><p style="margin:4px 0 0 0;font-size:0.84rem;color:#fff;font-weight:700;">Score {best_sc}/5 stars. Market rangebound between {sup:.0f} and {res:.0f}. No position opened — checked off the last closed candle, not the live tick.</p></div>""", unsafe_allow_html=True)
        elif is_ce:
            sl = round(max(sup, curr['close'] - (1.2 * atr)), 1); rk = round(max(ce_entry - sl, atr * 0.8), 1)
            t1, t2 = round(ce_entry + rk, 1), round(ce_entry + (2 * rk), 1)
            st.session_state.position = {"type": "CE", "strike": strike, "entry": ce_entry, "sl": sl, "t1": t1, "t2": t2,
                                          "entry_time": datetime.now(IST).strftime("%d-%b %I:%M %p"), "status": "open", "t1_hit": False}
            st.markdown(f"""
            <div class="card-ce">
                <div style="display:flex;justify-content:space-between;"><b class="cg" style="font-size:1.1rem;">🟢 NEW SIGNAL: BUY {strike} CE</b><span class="ca">{stars(b_s)} ({b_s}/5)</span></div>
                <div class="g2">
                    <div class="tile"><span class="lbl">ENTRY TRIGGER</span><div class="val cb">Buy Above {ce_entry:.1f}</div></div>
                    <div class="tile"><span class="lbl">STOP LOSS (SL)</span><div class="val cr">{sl:.1f} (-{rk:.1f} pts)</div></div>
                </div>
                <div style="background:#090e17;border:1px solid #334155;border-radius:8px;padding:8px;margin-top:6px;">
                    <div style="font-size:0.7rem;font-weight:800;color:#38bdf8;">🏁 EXIT PLAN (TARGETS & RISK)</div>
                    <div class="rw"><span>🎯 Target 1 (T1) — Book 50%:</span><b class="cg">{t1:.1f} (+{rk:.1f} pts)</b></div>
                    <div class="rw"><span>🏁 Target 2 (T2) — Book All:</span><b class="cg">{t2:.1f} (+{2*rk:.1f} pts)</b></div>
                    <div class="rw"><span>🛡️ Trailing SL (After T1 Hit):</span><b class="cb">Move SL to Cost ({ce_entry:.1f})</b></div>
                    <div class="rw"><span>Max Risk ({lot_sz} Qty):</span><b class="cr">-₹{rk * lot_sz:,.0f}</b></div>
                    <div class="rw"><span>Full Profit at T2:</span><b class="cg">+₹{2 * rk * lot_sz:,.0f}</b></div>
                </div>
                <div class="reasons"><span>CONFIRMING PILLARS:</span><br>• {'<br>• '.join(b_reasons)}</div>
                <div class="reasons" style="color:#38bdf8!important;">🔒 This call is now locked and will be tracked until it hits target or stop-loss — it won't be replaced by a new suggestion mid-trade.</div>
            </div>""", unsafe_allow_html=True)
        elif is_pe:
            sl = round(min(res, curr['close'] + (1.2 * atr)), 1); rk = round(max(sl - pe_entry, atr * 0.8), 1)
            t1, t2 = round(pe_entry - rk, 1), round(pe_entry - (2 * rk), 1)
            st.session_state.position = {"type": "PE", "strike": strike, "entry": pe_entry, "sl": sl, "t1": t1, "t2": t2,
                                          "entry_time": datetime.now(IST).strftime("%d-%b %I:%M %p"), "status": "open", "t1_hit": False}
            st.markdown(f"""
            <div class="card-pe">
                <div style="display:flex;justify-content:space-between;"><b class="cr" style="font-size:1.1rem;">🔴 NEW SIGNAL: BUY {strike} PE</b><span class="ca">{stars(be_s)} ({be_s}/5)</span></div>
                <div class="g2">
                    <div class="tile"><span class="lbl">ENTRY TRIGGER</span><div class="val cb">Sell Below {pe_entry:.1f}</div></div>
                    <div class="tile"><span class="lbl">STOP LOSS (SL)</span><div class="val cr">{sl:.1f} (-{rk:.1f} pts)</div></div>
                </div>
                <div style="background:#090e17;border:1px solid #334155;border-radius:8px;padding:8px;margin-top:6px;">
                    <div style="font-size:0.7rem;font-weight:800;color:#38bdf8;">🏁 EXIT PLAN (TARGETS & RISK)</div>
                    <div class="rw"><span>🎯 Target 1 (T1) — Book 50%:</span><b class="cg">{t1:.1f} (+{rk:.1f} pts)</b></div>
                    <div class="rw"><span>🏁 Target 2 (T2) — Book All:</span><b class="cg">{t2:.1f} (+{2*rk:.1f} pts)</b></div>
                    <div class="rw"><span>🛡️ Trailing SL (After T1 Hit):</span><b class="cb">Move SL to Cost ({pe_entry:.1f})</b></div>
                    <div class="rw"><span>Max Risk ({lot_sz} Qty):</span><b class="cr">-₹{rk * lot_sz:,.0f}</b></div>
                    <div class="rw"><span>Full Profit at T2:</span><b class="cg">+₹{2 * rk * lot_sz:,.0f}</b></div>
                </div>
                <div class="reasons"><span>CONFIRMING PILLARS:</span><br>• {'<br>• '.join(be_reasons)}</div>
                <div class="reasons" style="color:#38bdf8!important;">🔒 This call is now locked and will be tracked until it hits target or stop-loss — it won't be replaced by a new suggestion mid-trade.</div>
            </div>""", unsafe_allow_html=True)

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
    st.info("Tap '🔄 Sync Now' above to pull live market data, or upload a CSV.")
