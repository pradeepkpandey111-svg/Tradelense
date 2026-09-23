import streamlit as st, pandas as pd, numpy as np, plotly.graph_objects as go, yfinance as yf, feedparser, requests
from plotly.subplots import make_subplots
from streamlit_autorefresh import st_autorefresh
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))

st.set_page_config(page_title="TradeLense Pro Terminal", page_icon="⚡", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""<style>
header[data-testid="stHeader"]{visibility:hidden!important;height:0!important;}
html,body,[class*="css"],.stMarkdown{font-family:'Plus Jakarta Sans',sans-serif!important;background:#07090e;color:#fff!important;}
.block-container{padding:1.4rem 0.6rem 2.5rem 0.6rem!important;}
.banner{background:linear-gradient(135deg,#0f172a,#1e293b);border:1px solid #334155;border-radius:12px;padding:12px;margin-bottom:8px;}
.news-box{background:#0d121c;border:1px solid #1e293b;border-radius:8px;padding:8px 10px;margin-bottom:6px;}
.news-meta{display:flex;justify-content:space-between;align-items:center;margin-bottom:2px;}
.news-pub{font-size:0.68rem;font-weight:700;color:#38bdf8;text-transform:uppercase;}
.news-tag{font-size:0.68rem;font-weight:700;}
.news-headline{font-size:0.82rem;font-weight:600;color:#e2e8f0;line-height:1.35;}
.card-buy{background:#062b20;border-left:5px solid #10b981;border-radius:10px;padding:12px;margin-bottom:8px;}
.card-sell{background:#2d0c13;border-left:5px solid #f43f5e;border-radius:10px;padding:12px;margin-bottom:8px;}
.card-no{background:#241703;border-left:5px solid #f59e0b;border-radius:10px;padding:12px;margin-bottom:8px;}
.card-locked{background:#0c1a2b;border-left:5px solid #38bdf8;border-radius:10px;padding:12px;margin-bottom:8px;}
.card-blocked{background:#3b1116;border-left:5px solid #ef4444;border-radius:10px;padding:12px;margin-bottom:8px;}
.g2{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:4px;}
.g3{display:grid;grid-template-columns:repeat(3,1fr);gap:4px;margin-top:4px;}
.g4{display:grid;grid-template-columns:repeat(4,1fr);gap:4px;margin-top:4px;}
.tile{background:#090e17;border-radius:8px;padding:8px 10px;border:1px solid #1e293b;}
.lbl{font-size:0.65rem;font-weight:700;color:#94a3b8!important;text-transform:uppercase;}
.val{font-family:monospace;font-size:0.92rem;font-weight:700;}
.cg{color:#10b981!important;}.cr{color:#f43f5e!important;}.cb{color:#38bdf8!important;}.ca{color:#fbbf24!important;}
.rw{display:flex;justify-content:space-between;align-items:center;padding:5px 0;border-bottom:1px solid rgba(255,255,255,0.12);font-size:0.82rem;font-family:monospace;}
.rw span{color:#94a3b8!important;font-weight:600!important;}
.reasons{margin-top:8px;padding-top:6px;border-top:1px solid rgba(255,255,255,0.2);font-size:0.8rem;color:#fff!important;font-weight:700;}
</style>
<div class="banner">
  <div style="font-size:1.3rem;font-weight:800;">⚡ TradeLense AI Terminal</div>
  <div style="font-size:0.75rem;color:#94a3b8;">Unified Confluence Engine: Options Indices & Cash Shares</div>
</div>""", unsafe_allow_html=True)

# ---------- SESSION STATE ----------
if "position" not in st.session_state:
    st.session_state.position = None
if "oi_log" not in st.session_state:
    st.session_state.oi_log = []

# ---------- ASSET SELECTION ----------
col_tab1, col_tab2 = st.columns([1, 1.2])
asset_tab = col_tab1.radio("Trading Module", ["Option Indices", "Shares"], horizontal=True)

POPULAR_STOCKS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS",
    "TATAMOTORS.NS", "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "LT.NS", "Custom Ticker"
]

if asset_tab == "Option Indices":
    inst = col_tab2.selectbox("Target Index", ["NIFTY 50", "BANK NIFTY"])
    sym = "^NSEI" if inst == "NIFTY 50" else "^NSEBANK"
    nse_sym = "NIFTY" if inst == "NIFTY 50" else "BANKNIFTY"
    step_k, lot_sz = (50, 50) if inst == "NIFTY 50" else (100, 15)
    delta_approx = 0.52
    is_stock = False
else:
    pick = col_tab2.selectbox("Select NSE Share", POPULAR_STOCKS)
    if pick == "Custom Ticker":
        c_sym = st.text_input("Enter NSE Ticker (e.g. AXISBANK.NS)", value="AXISBANK.NS").strip().upper()
        sym = c_sym if c_sym.endswith(".NS") else f"{c_sym}.NS"
    else:
        sym = pick
    inst = sym.replace(".NS", "")
    nse_sym = inst
    step_k, lot_sz = 1, 1
    delta_approx = 1.0
    is_stock = True

c_m1, c_m2 = st.columns([1.2, 1])
mode = c_m1.radio("Feed Mode", ["⚡ Live Stream", "📁 Upload CSV"], horizontal=True)
trading_capital = c_m2.number_input("Account Capital (₹)", value=100000, step=25000) if is_stock else 50000

# ---------- AUTO-SYNC ----------
if mode == "⚡ Live Stream":
    a1, a2, a3 = st.columns([1, 1, 1.4])
    auto_on = a1.toggle("Auto-sync", value=True)
    refresh_sec = a2.selectbox("Interval", [10, 15, 30, 60], index=1, format_func=lambda x: f"{x}s")
    if auto_on:
        st_autorefresh(interval=refresh_sec * 1000, key="auto_sync_interval")
    if a3.button("🔄 Sync Now", use_container_width=True, type="primary"):
        st.cache_data.clear()
        st.rerun()
    ist_time = datetime.now(IST).strftime("%d-%b-%Y | %I:%M:%S %p")
    st.markdown(f"<div style='font-size:0.75rem;color:#94a3b8;font-weight:700;'>🕒 Synced: <span style='color:#38bdf8;'>{ist_time}</span></div>", unsafe_allow_html=True)

# ---------- OI WALLS & OPTION CHAIN (CRASH BUG FIX) ----------
def oi_walls(chain_list, spot):
    """Computes sorted resistance (Call OI) and support (Put OI) walls around spot price."""
    ce_strikes = [x for x in chain_list if x.get('strike', 0) >= spot and x.get('ce_oi', 0) > 0]
    pe_strikes = [x for x in chain_list if x.get('strike', 0) <= spot and x.get('pe_oi', 0) > 0]
    ce_sorted = sorted(ce_strikes, key=lambda x: x.get('ce_oi', 0), reverse=True)
    pe_sorted = sorted(pe_strikes, key=lambda x: x.get('pe_oi', 0), reverse=True)
    return ce_sorted[:3], pe_sorted[:3]

@st.cache_data(ttl=120)
def fetch_chain(s_sym):
    try:
        s = requests.Session()
        h = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36', 'Referer': 'https://www.nseindia.com/option-chain'}
        s.get("https://www.nseindia.com", headers=h, timeout=4)
        resp = s.get(f"https://www.nseindia.com/api/option-chain-indices?symbol={s_sym}", headers=h, timeout=4)
        if resp.status_code == 200:
            data = resp.json()
            recs = data.get('filtered', {}).get('data', []) or data.get('records', {}).get('data', [])
            t_ce, t_pe, m_ce, m_pe, r_s, s_s = 0, 0, 0, 0, 0, 0
            chain_list = []
            for r in recs:
                stk = float(r.get('strikePrice', 0))
                c_oi = r.get('CE', {}).get('openInterest', 0)
                p_oi = r.get('PE', {}).get('openInterest', 0)
                t_ce += c_oi; t_pe += p_oi
                if c_oi > m_ce: m_ce, r_s = c_oi, stk
                if p_oi > m_pe: m_pe, s_s = p_oi, stk
                chain_list.append({"strike": stk, "ce_oi": c_oi, "pe_oi": p_oi})
            if t_ce > 0 and s_s > 0 and r_s > 0:
                return {
                    "pcr": round(t_pe / t_ce, 2), "s": float(s_s), "r": float(r_s),
                    "src": "NSE Live", "tce": t_ce, "tpe": t_pe, "chain": chain_list
                }
    except: pass
    return None

oc = fetch_chain(nse_sym) if (mode == "⚡ Live Stream" and not is_stock) else None

# ---------- MACRO & BROAD SENTIMENT ----------
@st.cache_data(ttl=180)
def get_macro():
    res = {}
    for k, s in [("S&P 500", "^GSPC"), ("Nasdaq", "^IXIC"), ("Crude", "CL=F"), ("VIX", "^INDIAVIX"), ("Nifty 50", "^NSEI")]:
        try:
            r = yf.download(s, period="2d", interval="1d", progress=False)['Close'].dropna()
            if isinstance(r, pd.DataFrame): r = r.iloc[:, 0]
            pct = float(((r.iloc[-1] - r.iloc[-2]) / r.iloc[-2]) * 100) if len(r) >= 2 else 0.0
            res[k] = {"val": float(r.iloc[-1]), "pct": pct}
        except: res[k] = {"val": 0.0, "pct": 0.0}
    return res

mac = get_macro()
nifty_pct = mac.get("Nifty 50", {}).get("pct", 0.0)
broad_market_vote = "Bullish Tailwind 🟢" if nifty_pct >= 0.2 else ("Bearish Headwind 🔴" if nifty_pct <= -0.2 else "Neutral Drift ⚪")

# ---------- NEWS & FUNDAMENTALS / EVENTS GATING ----------
@st.cache_data(ttl=300)
def fetch_fundamentals_events_and_news(q_sym, is_stk):
    query = f"{q_sym}+share+price" if is_stk else "Nifty+Indian+stock+market"
    f = feedparser.parse(f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en")
    items, b_w, be_w, sc = [], ['surge', 'rally', 'jump', 'gain', 'profit', 'expansion', 'buy', 'high'], ['slump', 'drop', 'fall', 'probe', 'cut', 'loss', 'fraud', 'miss'], 0
    for e in f.entries[:4]:
        t = e.title
        src = e.source.title if 'source' in e and 'title' in e.source else "FINANCE"
        p = any(w in t.lower() for w in b_w)
        n = any(w in t.lower() for w in be_w)
        if p: sc += 1
        if n: sc -= 1
        tag = "<span class='cg'>🟢 Bullish</span>" if p else ("<span class='cr'>🔴 Bearish</span>" if n else "<span class='ca'>⚪ Neutral</span>")
        items.append({"title": t, "source": src, "tag": tag})

    fund = {
        "sector": "Indices / Derivatives" if not is_stk else "Equities",
        "market_cap": "N/A", "pe": "N/A", "high52": 0.0, "low52": 0.0,
        "days_to_earnings": None, "earnings_block": False, "corp_action": "None"
    }

    if is_stk:
        try:
            tk = yf.Ticker(q_sym)
            info = tk.info
            fund["sector"] = info.get("sector", "Equities")
            mc = info.get("marketCap", 0)
            fund["market_cap"] = f"₹{mc/1e7:,.0f} Cr" if mc else "N/A"
            pe = info.get("trailingPE", None)
            fund["pe"] = f"{pe:.1f}" if pe else "N/A"
            fund["high52"] = float(info.get("fiftyTwoWeekHigh", 0.0))
            fund["low52"] = float(info.get("fiftyTwoWeekLow", 0.0))

            cal = tk.calendar
            if cal is not None and not cal.empty:
                e_date = None
                if isinstance(cal, pd.DataFrame):
                    if "Earnings Date" in cal.index:
                        e_date = pd.to_datetime(cal.loc["Earnings Date"].iloc[0])
                    elif 0 in cal.columns:
                        e_date = pd.to_datetime(cal.iloc[0, 0])
                elif isinstance(cal, dict) and "Earnings Date" in cal:
                    e_date = pd.to_datetime(cal["Earnings Date"][0])

                if e_date is not None:
                    delta_days = (e_date.date() - datetime.now(timezone.utc).date()).days
                    fund["days_to_earnings"] = delta_days
                    if 0 <= delta_days <= 1:
                        fund["earnings_block"] = True

            acts = tk.actions
            if acts is not None and not acts.empty:
                last_act = acts.tail(1)
                div = last_act['Dividends'].iloc[0] if 'Dividends' in last_act.columns else 0
                splt = last_act['Stock Splits'].iloc[0] if 'Stock Splits' in last_act.columns else 0
                if div > 0: fund["corp_action"] = f"Div: ₹{div:.2f}"
                elif splt > 0: fund["corp_action"] = f"Split: {splt}"
        except: pass

    sent_label = "Bullish (+)" if sc > 0 else ("Bearish (-)" if sc < 0 else "Neutral")
    return sent_label, sc, items, fund

news_sent, news_sc, news_feed, fund_data = fetch_fundamentals_events_and_news(nse_sym, is_stock)

# Macro Display Ribbon
st.markdown(f"""<div class="tile" style="margin-bottom:8px;">
<div style="display:flex;justify-content:space-between;"><span class="lbl">🌐 GLOBAL MACRO</span><span class="lbl ca">{news_sent}</span></div>
<div class="g4">
<div class="tile"><span class="lbl">S&P 500</span><div class="val {'cg' if mac['S&P 500']['pct']>=0 else 'cr'}">{mac['S&P 500']['pct']:+.2f}%</div></div>
<div class="tile"><span class="lbl">NASDAQ</span><div class="val {'cg' if mac['Nasdaq']['pct']>=0 else 'cr'}">{mac['Nasdaq']['pct']:+.2f}%</div></div>
<div class="tile" title="Crude up = Bearish for India inflation"><span class="lbl">CRUDE (INV)</span><div class="val {'cr' if mac['Crude']['pct']>0 else 'cg'}">{mac['Crude']['pct']:+.2f}%</div></div>
<div class="tile"><span class="lbl">INDIA VIX</span><div class="val ca">{mac['VIX']['val']:.2f}</div></div>
</div></div>""", unsafe_allow_html=True)

if is_stock:
    st.markdown(f"""<div class="tile" style="margin-bottom:8px;">
    <div style="display:flex;justify-content:space-between;"><span class="lbl">🏢 STOCK PROFILE</span><span class="lbl ca">NIFTY VOTE: {broad_market_vote}</span></div>
    <div class="g4">
      <div class="tile"><span class="lbl">SECTOR</span><div class="val cb" style="font-size:0.75rem;">{fund_data['sector'][:14]}</div></div>
      <div class="tile"><span class="lbl">MKT CAP / P/E</span><div class="val ca" style="font-size:0.75rem;">{fund_data['market_cap']} | {fund_data['pe']}</div></div>
      <div class="tile"><span class="lbl">EARNINGS WINDOW</span><div class="val {'cr' if fund_data['earnings_block'] else 'cg'}" style="font-size:0.75rem;">{str(fund_data['days_to_earnings'])+'d away' if fund_data['days_to_earnings'] is not None else 'Clear'}</div></div>
      <div class="tile"><span class="lbl">LAST CORP ACTION</span><div class="val cb" style="font-size:0.75rem;">{fund_data['corp_action']}</div></div>
    </div></div>""", unsafe_allow_html=True)

# ---------- UNIFIED TECHNICAL ENGINE ----------
def compute_indicators(df_in):
    df_out = df_in.copy()
    close_col = next((x for x in df_out.columns if 'close' in x or 'ltp' in x), None)
    if not close_col:
        close_col = df_out.columns[1] if len(df_out.columns) > 1 else df_out.columns[0]
    df_out['close'] = pd.to_numeric(df_out[close_col].astype(str).str.replace(',', ''), errors='coerce').ffill().bfill()

    for col in ['open', 'high', 'low', 'volume']:
        match = next((x for x in df_out.columns if col in x and x != 'close'), None)
        if match:
            df_out[col] = pd.to_numeric(df_out[match].astype(str).str.replace(',', ''), errors='coerce')
        else:
            df_out[col] = 1.0 if col == 'volume' else df_out['close']

    df_out['ema9'] = df_out['close'].ewm(span=9, adjust=False).mean()
    df_out['ema21'] = df_out['close'].ewm(span=21, adjust=False).mean()
    df_out['ema50'] = df_out['close'].ewm(span=50, adjust=False).mean()

    # RSI (14)
    delta = df_out['close'].diff()
    up = delta.clip(lower=0).rolling(14).mean()
    down = -delta.clip(upper=0).rolling(14).mean().replace(0, np.nan)
    df_out['rsi'] = (100 - (100 / (1 + (up / down)))).fillna(50)

    # MACD (12, 26, 9)
    e12 = df_out['close'].ewm(span=12, adjust=False).mean()
    e26 = df_out['close'].ewm(span=26, adjust=False).mean()
    df_out['macd'] = e12 - e26
    df_out['macd_signal'] = df_out['macd'].ewm(span=9, adjust=False).mean()
    df_out['macd_hist'] = df_out['macd'] - df_out['macd_signal']

    # Bollinger Bands (20, 2)
    bb_mid = df_out['close'].rolling(20).mean()
    bb_std = df_out['close'].rolling(20).std()
    df_out['bb_upper'] = bb_mid + (2 * bb_std)
    df_out['bb_lower'] = bb_mid - (2 * bb_std)

    # ATR (14)
    tr = pd.concat([df_out['high'] - df_out['low'], (df_out['high'] - df_out['close'].shift()).abs(), (df_out['low'] - df_out['close'].shift()).abs()], axis=1).max(axis=1)
    df_out['atr'] = tr.rolling(14).mean().bfill()
    df_out['atr_avg20'] = df_out['atr'].rolling(20).mean().bfill()

    # Supertrend (10, 3)
    hl2 = (df_out['high'] + df_out['low']) / 2
    upper_b = hl2 + (3 * df_out['atr'])
    lower_b = hl2 - (3 * df_out['atr'])
    st_dir = np.ones(len(df_out))
    st_line = np.zeros(len(df_out))
    for i in range(1, len(df_out)):
        if df_out['close'].iloc[i] > upper_b.iloc[i-1]:
            st_dir[i] = 1
        elif df_out['close'].iloc[i] < lower_b.iloc[i-1]:
            st_dir[i] = -1
        else:
            st_dir[i] = st_dir[i-1]
            if st_dir[i] == 1 and lower_b.iloc[i] < lower_b.iloc[i-1]:
                lower_b.iloc[i] = lower_b.iloc[i-1]
            if st_dir[i] == -1 and upper_b.iloc[i] > upper_b.iloc[i-1]:
                upper_b.iloc[i] = upper_b.iloc[i-1]
        st_line[i] = lower_b.iloc[i] if st_dir[i] == 1 else upper_b.iloc[i]
    df_out['supertrend_dir'] = st_dir
    df_out['supertrend'] = st_line

    # Intraday VWAP
    cum_v = df_out['volume'].cumsum()
    cum_pv = (df_out['volume'] * ((df_out['high'] + df_out['low'] + df_out['close']) / 3)).cumsum()
    df_out['vwap'] = (cum_pv / cum_v.replace(0, np.nan)).bfill()

    # ADX (14)
    up_m = df_out['high'].diff()
    dn_m = -df_out['low'].diff()
    p_dm = np.where((up_m > dn_m) & (up_m > 0), up_m, 0.0)
    m_dm = np.where((dn_m > up_m) & (dn_m > 0), dn_m, 0.0)
    atr_w = tr.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    p_di = 100 * pd.Series(p_dm, index=df_out.index).ewm(alpha=1/14, min_periods=14, adjust=False).mean() / atr_w
    m_di = 100 * pd.Series(m_dm, index=df_out.index).ewm(alpha=1/14, min_periods=14, adjust=False).mean() / atr_w
    dx = 100 * (p_di - m_di).abs() / (p_di + m_di).replace(0, np.nan)
    df_out['adx'] = dx.ewm(alpha=1/14, min_periods=14, adjust=False).mean().fillna(0)

    # Relative Volume
    df_out['vol_ma20'] = df_out['volume'].rolling(20).mean().bfill()
    df_out['rvol'] = df_out['volume'] / df_out['vol_ma20'].replace(0, 1)

    return df_out

# ---------- DATA LOADING ----------
df = None
if mode == "📁 Upload CSV":
    with st.expander(f"📂 Upload Candle Data for {inst}", expanded=True):
        up_f = st.file_uploader("Upload CSV", key="main_csv_upload")
        if up_f:
            df = pd.read_csv(up_f)
            df.columns = [str(x).strip().lower() for x in df.columns]
            t_col = next((x for x in df.columns if 'time' in x or 'date' in x), df.columns[0])
            df['time'] = pd.to_datetime(df[t_col], errors='coerce')
            df = df.dropna(subset=['time']).sort_values('time').reset_index(drop=True)
            st.success(f"✓ Loaded {len(df)} candles")

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
    except Exception as ex:
        st.error(f"Error fetching live stream: {ex}")

if df is not None and len(df) > 20:
    df = compute_indicators(df)

    sig_idx = -2 if (mode == "⚡ Live Stream" and len(df) >= 10) else -1
    curr, prev = df.iloc[sig_idx], df.iloc[sig_idx - 1]
    live_p = float(df['close'].iloc[-1])

    day_high, day_low = float(df['high'].max()), float(df['low'].min())
    atr_val = float(curr['atr']) if pd.notna(curr['atr']) and curr['atr'] > 0 else live_p * 0.005
    adx_val = float(curr['adx'])
    vwap_val = float(curr['vwap'])
    rvol_val = float(curr['rvol'])

    piv = (curr['high'] + curr['low'] + curr['close']) / 3
    res_walls, sup_walls = oi_walls(oc.get('chain', []), live_p) if oc else ([], [])
    sup = sup_walls[0]['strike'] if sup_walls else (oc['s'] if oc and oc['s'] < live_p else round(min(curr['low'] - (0.4 * atr_val), (2 * piv) - curr['high']), 2))
    res = res_walls[0]['strike'] if res_walls else (oc['r'] if oc and oc['r'] > live_p else round(max(curr['high'] + (0.4 * atr_val), (2 * piv) - curr['low']), 2))

    h52 = fund_data['high52'] if fund_data['high52'] > 0 else (day_high * 1.15)
    l52 = fund_data['low52'] if fund_data['low52'] > 0 else (day_low * 0.85)
    dist_52h = ((h52 - live_p) / h52) * 100
    dist_52l = ((live_p - l52) / l52) * 100

    oc_badge = f"<span class='cg'>● {oc['src']} (PCR: {oc['pc