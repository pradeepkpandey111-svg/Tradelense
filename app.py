import streamlit as st, pandas as pd, numpy as np, yfinance as yf, feedparser, requests
from streamlit_autorefresh import st_autorefresh
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))

st.set_page_config(page_title="TradeLense AI Terminal", page_icon="⚡", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""<style>
header[data-testid="stHeader"]{visibility:hidden!important;height:0!important;}
html,body,[class*="css"],.stMarkdown{font-family:'Plus Jakarta Sans',sans-serif!important;background:#07090e;color:#fff!important;}
.block-container{padding:1.2rem 0.6rem 2.5rem 0.6rem!important;}
.banner{background:linear-gradient(135deg,#0f172a,#1e293b);border:1px solid #334155;border-radius:12px;padding:12px;margin-bottom:8px;}
.news-box{background:#0d121c;border:1px solid #1e293b;border-radius:8px;padding:8px 10px;margin-bottom:6px;}
.news-meta{display:flex;justify-content:space-between;align-items:center;margin-bottom:2px;}
.news-pub{font-size:0.68rem;font-weight:700;color:#38bdf8;text-transform:uppercase;}
.news-tag{font-size:0.68rem;font-weight:700;}
.news-headline{font-size:0.82rem;font-weight:600;color:#e2e8f0;line-height:1.35;}
.card-buy{background:#062b20;border-left:5px solid #10b981;border-radius:10px;padding:12px;margin-bottom:8px;}
.card-sell{background:#2d0c13;border-left:5px solid #f43f5e;border-radius:10px;padding:12px;margin-bottom:8px;}
.card-no{background:#241703;border-left:5px solid #f59e0b;border-radius:10px;padding:12px;margin-bottom:8px;}
.card-locked{background:#0c1a2b;border:1px solid #38bdf8;border-left:6px solid #38bdf8;border-radius:10px;padding:14px;margin-bottom:8px;}
.card-waiting{background:#18181b;border:1px dashed #fbbf24;border-left:6px solid #fbbf24;border-radius:10px;padding:14px;margin-bottom:8px;}
.card-blocked{background:#3b1116;border-left:5px solid #ef4444;border-radius:10px;padding:12px;margin-bottom:8px;}
.g2{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:4px;}
.g3{display:grid;grid-template-columns:repeat(3,1fr);gap:4px;margin-top:4px;}
.g4{display:grid;grid-template-columns:repeat(4,1fr);gap:4px;margin-top:4px;}
.tile{background:#090e17;border-radius:8px;padding:8px 10px;border:1px solid #1e293b;}
.lbl{font-size:0.65rem;font-weight:700;color:#94a3b8!important;text-transform:uppercase;}
.val{font-family:monospace;font-size:0.95rem;font-weight:700;}
.cg{color:#10b981!important;}.cr{color:#f43f5e!important;}.cb{color:#38bdf8!important;}.ca{color:#fbbf24!important;}
.rw{display:flex;justify-content:space-between;align-items:center;padding:5px 0;border-bottom:1px solid rgba(255,255,255,0.12);font-size:0.82rem;font-family:monospace;}
.rw span{color:#94a3b8!important;font-weight:600!important;}
.reasons{margin-top:8px;padding-top:6px;border-top:1px solid rgba(255,255,255,0.2);font-size:0.8rem;color:#fff!important;font-weight:700;}
.status-pill{background:#1e293b;border-radius:4px;padding:2px 6px;font-size:0.7rem;font-weight:700;color:#38bdf8;}
</style>
<div class="banner">
  <div style="display:flex;justify-content:space-between;align-items:center;">
    <div style="font-size:1.3rem;font-weight:800;">⚡ TradeLense AI Terminal</div>
    <span class="status-pill">PRO INTRADAY DESK</span>
  </div>
  <div style="font-size:0.75rem;color:#94a3b8;">Multi-Confluence Engine: Session VWAP, Multi-EMA, Supertrend, MACD, BB, Events & Level Trailing</div>
</div>""", unsafe_allow_html=True)

# ---------- PERSISTENT MULTI-ASSET STATE ----------
if "positions" not in st.session_state:
    st.session_state.positions = {}
if "oi_log" not in st.session_state:
    st.session_state.oi_log = []

# ---------- ASSET PICKER ----------
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

# Auto-sync
if mode == "⚡ Live Stream":
    a1, a2, a3 = st.columns([1, 1, 1.4])
    auto_on = a1.toggle("Auto-sync", value=True)
    refresh_sec = a2.selectbox("Interval", [10, 15, 30, 60], index=1, format_func=lambda x: f"{x}s")
    if auto_on:
        st_autorefresh(interval=refresh_sec * 1000, key="desk_refresh_sync")
    if a3.button("🔄 Sync Now", use_container_width=True, type="primary"):
        st.cache_data.clear()
        st.rerun()
    ist_time = datetime.now(IST).strftime("%d-%b-%Y | %I:%M:%S %p")
    st.markdown(f"<div style='font-size:0.75rem;color:#94a3b8;font-weight:700;'>🕒 Synced: <span style='color:#38bdf8;'>{ist_time}</span></div>", unsafe_allow_html=True)

# ---------- OPTION CHAIN HELPERS ----------
def oi_walls(chain_list, spot):
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

# ---------- GLOBAL MACRO & BROAD SENTIMENT ----------
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

# ---------- CORPORATE ACTIONS, RESULTS & RSS SENTIMENT ----------
@st.cache_data(ttl=300)
def fetch_fundamentals_events_and_news(q_sym, is_stk):
    query = f"{q_sym}+share+price" if is_stk else "Nifty+Indian+stock+market"
    f = feedparser.parse(f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en")
    items, b_w, be_w, sc = [], ['surge', 'rally', 'jump', 'gain', 'profit', 'expansion', 'buy', 'high', 'breakout'], ['slump', 'drop', 'fall', 'probe', 'cut', 'loss', 'fraud', 'miss', 'breakdown'], 0
    for e in f.entries[:3]:
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

# Macro ribbon
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
      <div class="tile"><span class="lbl">EARNINGS GATING</span><div class="val {'cr' if fund_data['earnings_block'] else 'cg'}" style="font-size:0.75rem;">{str(fund_data['days_to_earnings'])+'d away' if fund_data['days_to_earnings'] is not None else 'Clear'}</div></div>
      <div class="tile"><span class="lbl">LAST CORP ACTION</span><div class="val cb" style="font-size:0.75rem;">{fund_data['corp_action']}</div></div>
    </div></div>""", unsafe_allow_html=True)

# ---------- UNIFIED INDICATOR ENGINE (DAILY SESSION VWAP FIX) ----------
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

    # Trend EMAs
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
    df_out['bb_width'] = ((df_out['bb_upper'] - df_out['bb_lower']) / bb_mid) * 100
    df_out['bb_squeeze'] = df_out['bb_width'] < df_out['bb_width'].rolling(20).mean()

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

    # Daily Resetted VWAP (Fixes multi-day distortion)
    df_out['date_grp'] = df_out['time'].dt.date
    df_out['pv'] = (df_out['high'] + df_out['low'] + df_out['close']) / 3 * df_out['volume']
    df_out['vwap'] = df_out.groupby('date_grp')['pv'].cumsum() / df_out.groupby('date_grp')['volume'].cumsum().replace(0, np.nan)
    df_out['vwap'] = df_out['vwap'].ffill().bfill()

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

    # RVOL vs 20 SMA
    df_out['vol_ma20'] = df_out['volume'].rolling(20).mean().bfill()
    df_out['rvol'] = df_out['volume'] / df_out['vol_ma20'].replace(0, 1)

    return df_out

# ---------- DATA LOADING ----------
df = None
if mode == "📁 Upload CSV":
    with st.expander(f"📂 Upload Data for {inst}", expanded=True):
        up_f = st.file_uploader("Upload CSV", key="desk_csv_upload")
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
        st.error(f"Feed error: {ex}")

if df is not None and len(df) > 20:
    df = compute_indicators(df)

    sig_idx = -2 if (mode == "⚡ Live Stream" and len(df) >= 10) else -1
    curr, prev = df.iloc[sig_idx], df.iloc[sig_idx - 1]
    live_p = float(df['close'].iloc[-1])

    # Current Day High / Low
    today_date = df['time'].iloc[-1].date()
    today_candles = df[df['time'].dt.date == today_date]
    day_high = float(today_candles['high'].max()) if not today_candles.empty else float(df['high'].tail(50).max())
    day_low = float(today_candles['low'].min()) if not today_candles.empty else float(df['low'].tail(50).min())

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

    oc_badge = f"<span class='cg'>● {oc['src']} (PCR: {oc['pcr']})</span>" if oc else "<span class='ca'>● Dynamic Pivot Mode</span>"

    # Spot & Metric Bar
    st.markdown(f"""<div class="tile" style="margin-bottom:8px;">
    <div style="display:flex;justify-content:space-between;"><span class="lbl">{inst} SPOT</span><span class="lbl">{oc_badge}</span></div>
    <div class="val cb" style="font-size:1.35rem;">₹{live_p:,.2f}</div>
    <div class="g4">
      <div class="tile"><span class="lbl">SUPPORT</span><div class="val cg">₹{sup:,.1f}</div></div>
      <div class="tile"><span class="lbl">RESISTANCE</span><div class="val cr">₹{res:,.1f}</div></div>
      <div class="tile"><span class="lbl">DAY HIGH</span><div class="val cg">₹{day_high:,.1f}</div></div>
      <div class="tile"><span class="lbl">DAY LOW</span><div class="val cr">₹{day_low:,.1f}</div></div>
    </div>
    <div class="g3" style="margin-top:4px;">
      <div class="tile"><span class="lbl">ADX TREND</span><div class="val {'cg' if adx_val>=18 else 'ca'}">{adx_val:.1f} ({'Trending' if adx_val>=18 else 'Choppy'})</div></div>
      <div class="tile"><span class="lbl">SESSION VWAP</span><div class="val {'cg' if live_p>=vwap_val else 'cr'}">₹{vwap_val:.1f}</div></div>
      <div class="tile"><span class="lbl">52W PROXIMITY</span><div class="val ca">-{dist_52h:.1f}% / +{dist_52l:.1f}%</div></div>
    </div>
    </div>""", unsafe_allow_html=True)

    # Technical Confluence Radar (Compact Display)
    st.markdown(f"""<div class="tile" style="margin-bottom:8px;">
    <div style="display:flex;justify-content:space-between;"><span class="lbl">⚡ TECHNICAL RADAR</span><span class="lbl cb">RSI: {curr['rsi']:.1f}</span></div>
    <div class="g4">
      <div class="tile"><span class="lbl">EMA 9 / 21 / 50</span><div class="val {'cg' if (curr['ema9']>curr['ema21'] and curr['close']>curr['ema50']) else 'cr'}">{'BULL ALIGNED' if (curr['ema9']>curr['ema21'] and curr['close']>curr['ema50']) else 'BEAR / MIXED'}</div></div>
      <div class="tile"><span class="lbl">SUPERTREND</span><div class="val {'cg' if curr['supertrend_dir']==1 else 'cr'}">{'BULLISH' if curr['supertrend_dir']==1 else 'BEARISH'}</div></div>
      <div class="tile"><span class="lbl">MACD HIST</span><div class="val {'cg' if curr['macd_hist']>=0 else 'cr'}">{curr['macd_hist']:+.2f}</div></div>
      <div class="tile"><span class="lbl">RVOL (20MA)</span><div class="val {'cg' if rvol_val>=1.2 else 'ca'}">{rvol_val:.2f}x</div></div>
    </div>
    </div>""", unsafe_allow_html=True)

    # ---------- TWO-STAGE TRADE LIFECYCLE CONTROLLER ----------
    st.markdown("#### 🎯 Execution Desk")
    pos = st.session_state.positions.get(sym)

    # STATE 1: Trade is awaiting breakout trigger
    if pos is not None and pos.get('status') == 'waiting_trigger':
        is_long = pos['direction'] == 'BUY'
        # Check if entry breakout has occurred
        triggered = (live_p >= pos['entry']) if is_long else (live_p <= pos['entry'])
        invalidated = (live_p <= pos['sl']) if is_long else (live_p >= pos['sl'])

        if triggered:
            pos['status'] = 'active'
            pos['fill_price'] = live_p
            pos['fill_time'] = datetime.now(IST).strftime("%I:%M %p")
            st.session_state.positions[sym] = pos
            st.rerun()
        elif invalidated:
            st.session_state.positions[sym] = None
            st.warning(f"⚠️ Setup for {pos['label']} was invalidated before trigger. Scanner reset.")
            st.rerun()
        else:
            pts_away = abs(pos['entry'] - live_p)
            st.markdown(f"""<div class="card-waiting">
              <div style="display:flex;justify-content:space-between;"><b style="font-size:1.05rem;color:#fbbf24;">⏳ SETUP FOUND — AWAITING BREAKOUT: {pos['label']}</b><span class="ca">{pts_away:.2f} pts to trigger</span></div>
              <div class="g2">
                <div class="tile"><span class="lbl">TRIGGER CONDITION</span><div class="val cb">{'Break Above' if is_long else 'Break Below'} ₹{pos['entry']:.2f}</div></div>
                <div class="tile"><span class="lbl">INVALIDATION LEVEL</span><div class="val cr">₹{pos['sl']:.2f}</div></div>
              </div>
              <div class="reasons">
                🎯 Targets: T1 ₹{pos['t1']:.2f} &nbsp;|&nbsp; 🏁 T2 ₹{pos['t2']:.2f}<br>
                Institutional Note: Order stays in pending state until spot actually prints beyond trigger level.
              </div>
            </div>""", unsafe_allow_html=True)
            if st.button(f"✖ Cancel Pending Order ({inst})", use_container_width=True):
                st.session_state.positions[sym] = None
                st.rerun()

    # STATE 2: Trade is active and live
    elif pos is not None and pos.get('status') == 'active':
        is_long = pos['direction'] == 'BUY'
        entry_price = pos.get('fill_price', pos['entry'])
        pnl_spot_pts = (live_p - entry_price) if is_long else (entry_price - live_p)

        # SL and Target monitoring
        if (is_long and live_p <= pos['sl']) or (not is_long and live_p >= pos['sl']):
            pos['status'] = 'SL Hit'; pos['exit_price'] = pos['sl']
        elif (is_long and live_p >= pos['t2']) or (not is_long and live_p <= pos['t2']):
            pos['status'] = 'Target 2 Hit'; pos['exit_price'] = pos['t2']
        elif ((is_long and live_p >= pos['t1']) or (not is_long and live_p <= pos['t1'])) and not pos.get('t1_hit'):
            pos['t1_hit'] = True
            pos['sl'] = entry_price  # Move SL to breakeven after T1

        st.session_state.positions[sym] = pos
        approx_pts = pnl_spot_pts * pos.get('delta', 1.0)
        pnl_cash = approx_pts * pos['qty']
        col_pnl = 'cg' if pnl_spot_pts >= 0 else 'cr'

        st.markdown(f"""<div class="card-locked">
          <div style="display:flex;justify-content:space-between;"><b style="font-size:1.1rem;color:#38bdf8;">📌 LIVE POSITION LOCKED: {pos['label']}</b><span class="ca">Filled @ ₹{entry_price:.2f}</span></div>
          <div class="g2">
            <div class="tile"><span class="lbl">EST. P&L ({pos['qty']} QTY)</span><div class="val {col_pnl}">{pnl_spot_pts:+.2f} pts spot (₹{pnl_cash:+,.2f})</div></div>
            <div class="tile"><span class="lbl">PROTECTIVE SL</span><div class="val ca">₹{pos['sl']:.2f}{' · Trailed to Breakeven' if pos.get('t1_hit') else ''}</div></div>
          </div>
          <div class="reasons">
            🎯 Target 1: ₹{pos['t1']:.2f} &nbsp;|&nbsp; 🏁 Target 2: ₹{pos['t2']:.2f}<br>
            🔒 Position is actively managed. Pullbacks while holding above SL do not invalidate your trade.
          </div>
        </div>""", unsafe_allow_html=True)
        if st.button(f"✖ Square Off Position Manually ({inst})", use_container_width=True):
            st.session_state.positions[sym] = None
            st.rerun()

    # STATE 3: Trade finished
    elif pos is not None and pos.get('status') not in ['waiting_trigger', 'active']:
        entry_price = pos.get('fill_price', pos['entry'])
        pnl_realized = (((pos['exit_price'] - entry_price) if pos['direction'] == 'BUY' else (entry_price - pos['exit_price'])) * pos.get('delta', 1.0)) * pos['qty']
        col_r = 'cg' if pnl_realized >= 0 else 'cr'
        st.markdown(f"""<div class="card-locked">
          <div style="display:flex;justify-content:space-between;"><b>🏁 Completed Trade: {pos['status']}</b><span class="ca">{pos['label']}</span></div>
          <div class="tile"><span class="lbl">FINAL REALIZED P&L</span><div class="val {col_r}">₹{pnl_realized:+,.2f}</div></div>
        </div>""", unsafe_allow_html=True)
        if st.button("🔍 Clear & Scan for Next High-Confluence Setup", use_container_width=True, type="primary"):
            st.session_state.positions[sym] = None
            st.rerun()

    # STATE 4: Scanner running fresh confluence checks
    else:
        if is_stock and fund_data['earnings_block']:
            st.markdown(f"""<div class="card-blocked">
              <b style="color:#ef4444;font-size:1.05rem;">🛑 RESULTS / EARNINGS GATING ACTIVE</b>
              <p style="margin:4px 0 0 0;font-size:0.84rem;color:#fecaca;">Company results/AGM are scheduled within 24h ({fund_data['days_to_earnings']}d away). New trades are hard-gated to avoid event volatility.</p>
            </div>""", unsafe_allow_html=True)
        else:
            b_sc, be_sc = 0, 0
            b_reas, be_reas = [], []
            total_active_pillars = 0

            # 1. EMA Ribbon & Structure
            total_active_pillars += 2
            if curr['ema9'] > curr['ema21']: b_sc += 1; b_reas.append("EMA 9 > EMA 21 Bullish Stack")
            else: be_sc += 1; be_reas.append("EMA 9 < EMA 21 Bearish Stack")

            if curr['close'] >= curr['ema50']: b_sc += 1; b_reas.append("Price Above EMA 50 Structural Baseline")
            else: be_sc += 1; be_reas.append("Price Below EMA 50 Structural Baseline")

            # 2. RSI Momentum
            total_active_pillars += 2
            rsi_val = curr['rsi']
            if rsi_val >= 52:
                b_sc += 1
                b_reas.append(f"RSI ({rsi_val:.1f}) in Bullish Acceleration Zone" + (" (Momentum Expansion)" if rsi_val >= 62 else ""))
            elif rsi_val <= 48:
                be_sc += 1
                be_reas.append(f"RSI ({rsi_val:.1f}) in Bearish Distribution Zone" + (" (Downside Expansion)" if rsi_val <= 38 else ""))

            if rsi_val >= prev['rsi']: b_sc += 1; b_reas.append("RSI Slope Pointing Upward")
            else: be_sc += 1; be_reas.append("RSI Slope Pointing Downward")

            # 3. MACD Cross & Histogram Expansion
            total_active_pillars += 1
            if curr['macd'] >= curr['macd_signal'] and curr['macd_hist'] >= 0:
                b_sc += 1; b_reas.append("MACD Bullish Cross with Expanding Histogram")
            elif curr['macd'] <= curr['macd_signal'] and curr['macd_hist'] <= 0:
                be_sc += 1; be_reas.append("MACD Bearish Cross with Expanding Histogram")

            # 4. Supertrend
            total_active_pillars += 1
            if curr['supertrend_dir'] == 1: b_sc += 1; b_reas.append("Supertrend (10,3) Bullish Support")
            else: be_sc += 1; be_reas.append("Supertrend (10,3) Bearish Resistance")

            # 5. Session VWAP
            total_active_pillars += 1
            if curr['close'] >= vwap_val: b_sc += 1; b_reas.append("Holding Above Session-Resetted VWAP")
            else: be_sc += 1; be_reas.append("Trading Below Session-Resetted VWAP")

            # 6. Bollinger Bands Momentum / Riding Bands
            total_active_pillars += 1
            if curr['close'] >= curr['bb_upper'] * 0.995:
                b_sc += 1; b_reas.append("Riding Upper Bollinger Band (High Volatility Expansion)")
            elif curr['close'] <= curr['bb_lower'] * 1.005:
                be_sc += 1; be_reas.append("Riding Lower Bollinger Band (Downside Volatility Expansion)")

            # 7. Price Action & Candle Structure
            total_active_pillars += 1
            if curr['close'] > prev['high']:
                b_sc += 1; b_reas.append("Candle Closed Above Previous Candle High")
            elif curr['close'] < prev['low']:
                be_sc += 1; be_reas.append("Candle Closed Below Previous Candle Low")
            else:
                if curr['close'] > curr['ema9']: b_sc += 1; b_reas.append("Consolidation Holding EMA 9 Support")
                elif curr['close'] < curr['ema9']: be_sc += 1; be_reas.append("Consolidation Holding EMA 9 Resistance")

            # 8. Sentiment & Market Flow
            total_active_pillars += 1
            if news_sc > 0: b_sc += 1; b_reas.append("Scattered News Sentiment Positive")
            elif news_sc < 0: be_sc += 1; be_reas.append("Scattered News Sentiment Negative")

            if is_stock:
                total_active_pillars += 1
                if nifty_pct >= 0.15: b_sc += 1; b_reas.append(f"Nifty Directional Tailwind (+{nifty_pct:.2f}%)")
                elif nifty_pct <= -0.15: be_sc += 1; be_reas.append(f"Nifty Directional Headwind ({nifty_pct:.2f}%)")

            # 9. Option Chain PCR & OI Buildup (When active)
            if oc:
                total_active_pillars += 2
                if oc['pcr'] >= 1.05 and live_p >= sup: b_sc += 1; b_reas.append(f"Option Chain PCR {oc['pcr']} Bullish Support")
                elif oc['pcr'] <= 0.88 and live_p <= res: be_sc += 1; be_reas.append(f"Option Chain PCR {oc['pcr']} Bearish Resistance")

                now_ist = datetime.now(IST)
                st.session_state.oi_log.append({"t": now_ist, "tce": oc.get('tce', 0), "tpe": oc.get('tpe', 0), "price": live_p})
                st.session_state.oi_log = [x for x in st.session_state.oi_log if (now_ist - x['t']).total_seconds() <= 600][-40:]
                if len(st.session_state.oi_log) >= 2:
                    p_chg = st.session_state.oi_log[-1]['price'] - st.session_state.oi_log[0]['price']
                    oi_chg = (st.session_state.oi_log[-1]['tce'] + st.session_state.oi_log[-1]['tpe']) - (st.session_state.oi_log[0]['tce'] + st.session_state.oi_log[0]['tpe'])
                    if p_chg > 0 and oi_chg > 0: b_sc += 1; b_reas.append("OI Buildup Confirms Fresh Institutional Longs")
                    elif p_chg < 0 and oi_chg > 0: be_sc += 1; be_reas.append("OI Buildup Confirms Fresh Institutional Shorts")

            needed_score = max(5, int(np.ceil(total_active_pillars * 0.62)))
            def stars(sc, total=total_active_pillars): return "★" * min(sc, total) + "☆" * max(0, total - sc)

            is_long_setup = b_sc >= needed_score and adx_val >= 18
            is_short_setup = be_sc >= needed_score and b_sc < needed_score and adx_val >= 18

            if is_long_setup:
                buffer = round(max(0.15 * atr_val, 0.10), 2)
                entry = round(curr['high'] + buffer, 2)
                sl = round(max(sup, entry - (1.4 * atr_val)), 2)
                risk_pts = round(max(entry - sl, atr_val * 0.8), 2)
                t1, t2 = round(entry + (1.2 * risk_pts), 2), round(entry + (2.2 * risk_pts), 2)

                if is_stock:
                    qty = max(1, int((trading_capital * 0.01) / risk_pts))
                    label = f"INTRADAY BUY: {inst}"
                    calc_delta = 1.0
                else:
                    strike = int(round(live_p / step_k) * step_k)
                    qty = lot_sz
                    label = f"BUY {strike} CE"
                    calc_delta = delta_approx

                st.session_state.positions[sym] = {
                    "direction": "BUY", "label": label, "entry": entry, "sl": sl,
                    "t1": t1, "t2": t2, "qty": qty, "status": "waiting_trigger",
                    "t1_hit": False, "delta": calc_delta,
                    "setup_time": datetime.now(IST).strftime("%I:%M %p")
                }
                st.rerun()

            elif is_short_setup:
                buffer = round(max(0.15 * atr_val, 0.10), 2)
                entry = round(curr['low'] - buffer, 2)
                sl = round(min(res, entry + (1.4 * atr_val)), 2)
                risk_pts = round(max(sl - entry, atr_val * 0.8), 2)
                t1, t2 = round(entry - (1.2 * risk_pts), 2), round(entry - (2.2 * risk_pts), 2)

                if is_stock:
                    qty = max(1, int((trading_capital * 0.01) / risk_pts))
                    label = f"INTRADAY SHORT: {inst}"
                    calc_delta = 1.0
                else:
                    strike = int(round(live_p / step_k) * step_k)
                    qty = lot_sz
                    label = f"BUY {strike} PE"
                    calc_delta = delta_approx

                st.session_state.positions[sym] = {
                    "direction": "SELL", "label": label, "entry": entry, "sl": sl,
                    "t1": t1, "t2": t2, "qty": qty, "status": "waiting_trigger",
                    "t1_hit": False, "delta": calc_delta,
                    "setup_time": datetime.now(IST).strftime("%I:%M %p")
                }
                st.rerun()

            else:
                top_sc = max(b_sc, be_sc)
                st.markdown(f"""<div class="card-no">
                  <div style="display:flex;justify-content:space-between;"><b style="color:#fbbf24;">⛔ SCANNING CONFLUENCE CRITERIA</b><span class="ca">{stars(top_sc)} ({top_sc}/{total_active_pillars})</span></div>
                  <p style="margin:4px 0 0 0;font-size:0.84rem;">Score: {top_sc}/{total_active_pillars} (Requires ≥ {needed_score} with ADX ≥ 18). Support: ₹{sup:.1f} | Resistance: ₹{res:.1f}.</p>
                </div>""", unsafe_allow_html=True)

else:
    st.info("Awaiting live stream data. Click '🔄 Sync Now' above or upload a CSV file.")