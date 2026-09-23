import streamlit as st, pandas as pd, numpy as np, plotly.graph_objects as go, yfinance as yf, feedparser, requests
from plotly.subplots import make_subplots
from streamlit_autorefresh import st_autorefresh
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))

st.set_page_config(page_title="TradeLense AI Terminal", page_icon="⚡", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""<style>
header[data-testid="stHeader"]{visibility:hidden!important;height:0!important;}
html,body,[class*="css"],.stMarkdown{font-family:'Plus Jakarta Sans',sans-serif!important;background:#07090e;color:#fff!important;}
.block-container{padding:1.5rem 0.6rem 2.5rem 0.6rem!important;}
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
  <div style="font-size:0.75rem;color:#94a3b8;">Multi-Confluence Intraday Execution: Indices Options & Cash Shares</div>
</div>""", unsafe_allow_html=True)

# ---------- SESSION STATE ----------
if "position" not in st.session_state:
    st.session_state.position = None
if "oi_log" not in st.session_state:
    st.session_state.oi_log = []

# ---------- ASSET CLASSIFICATION & SELECTION ----------
c_top1, c_top2 = st.columns([1, 1.2])
asset_tab = c_top1.radio("Trading Module", ["Option Indices", "Shares"], horizontal=True)

POPULAR_STOCKS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS",
    "TATAMOTORS.NS", "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "LT.NS", "Custom Ticker"
]

if asset_tab == "Option Indices":
    inst = c_top2.selectbox("Target Index", ["NIFTY 50", "BANK NIFTY"])
    sym = "^NSEI" if inst == "NIFTY 50" else "^NSEBANK"
    nse_sym = "NIFTY" if inst == "NIFTY 50" else "BANKNIFTY"
    step_k, lot_sz = (50, 50) if inst == "NIFTY 50" else (100, 15)
    is_stock = False
else:
    pick = c_top2.selectbox("Select NSE Share", POPULAR_STOCKS)
    if pick == "Custom Ticker":
        c_sym = st.text_input("Enter NSE Ticker (e.g. AXISBANK.NS)", value="AXISBANK.NS").strip().upper()
        sym = c_sym if c_sym.endswith(".NS") else f"{c_sym}.NS"
    else:
        sym = pick
    inst = sym.replace(".NS", "")
    nse_sym = inst
    step_k, lot_sz = 1, 1
    is_stock = True

m_c1, m_c2 = st.columns([1.2, 1])
mode = m_c1.radio("Data Mode", ["⚡ Live Stream", "📁 Upload CSV"], horizontal=True)
trading_capital = m_c2.number_input("Risk Capital (₹)", value=100000, step=25000) if is_stock else 50000

# ---------- REAL AUTO-SYNC ----------
if mode == "⚡ Live Stream":
    a1, a2, a3 = st.columns([1, 1, 1.4])
    auto_on = a1.toggle("Auto-sync", value=True)
    refresh_sec = a2.selectbox("Every", [10, 15, 30, 60], index=1, format_func=lambda x: f"{x}s")
    if auto_on:
        st_autorefresh(interval=refresh_sec * 1000, key="auto_sync_timer")
    if a3.button("🔄 Sync Now", use_container_width=True, type="primary"):
        st.cache_data.clear()
        st.rerun()
    ist_time = datetime.now(IST).strftime("%d-%b-%Y | %I:%M:%S %p")
    st.markdown(f"<div style='font-size:0.75rem;color:#94a3b8;font-weight:700;'>🕒 Synced: <span style='color:#38bdf8;'>{ist_time}</span></div>", unsafe_allow_html=True)

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

# ---------- NEWS & FUNDAMENTALS / EVENTS GATING ENGINE ----------
@st.cache_data(ttl=300)
def fetch_fundamentals_events_and_news(q_sym, is_stk):
    # RSS News Sentiment Scoped
    query = f"{q_sym}+share+price" if is_stk else "Nifty+Indian+stock+market"
    f = feedparser.parse(f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en")
    items, b_w, be_w, sc = [], ['surge', 'rally', 'jump', 'gain', 'profit', 'expansion', 'buy', 'upgrade'], ['slump', 'drop', 'fall', 'probe', 'cut', 'loss', 'fraud', 'miss', 'downgrade'], 0
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
        "sector": "Indices / Derivatives" if not is_stk else "N/A",
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

            # Earnings / Results Gating (Block entries on / 1-day before earnings)
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
                    today = datetime.now(timezone.utc).date()
                    delta_days = (e_date.date() - today).days
                    fund["days_to_earnings"] = delta_days
                    if 0 <= delta_days <= 1:
                        fund["earnings_block"] = True

            # Last Corporate Action
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

# Macro & Sentiment Ribbon
st.markdown(f"""<div class="tile" style="margin-bottom:8px;">
<div style="display:flex;justify-content:space-between;"><span class="lbl">🌐 GLOBAL MACRO & MARKET SENTIMENT</span><span class="lbl ca">{news_sent}</span></div>
<div class="g4">
<div class="tile"><span class="lbl">S&P 500</span><div class="val {'cg' if mac['S&P 500']['pct']>=0 else 'cr'}">{mac['S&P 500']['pct']:+.2f}%</div></div>
<div class="tile"><span class="lbl">NASDAQ</span><div class="val {'cg' if mac['Nasdaq']['pct']>=0 else 'cr'}">{mac['Nasdaq']['pct']:+.2f}%</div></div>
<div class="tile"><span class="lbl">CRUDE OIL</span><div class="val {'cr' if mac['Crude']['pct']>0 else 'cg'}">{mac['Crude']['pct']:+.2f}%</div></div>
<div class="tile"><span class="lbl">INDIA VIX</span><div class="val ca">{mac['VIX']['val']:.2f}</div></div>
</div></div>""", unsafe_allow_html=True)

# Stock Fundamentals ribbon
if is_stock:
    st.markdown(f"""<div class="tile" style="margin-bottom:8px;">
    <div style="display:flex;justify-content:space-between;"><span class="lbl">🏢 FUNDAMENTALS & EVENTS CONTEXT</span><span class="lbl ca">NIFTY VOTE: {broad_market_vote}</span></div>
    <div class="g4">
      <div class="tile"><span class="lbl">SECTOR</span><div class="val cb" style="font-size:0.75rem;">{fund_data['sector'][:14]}</div></div>
      <div class="tile"><span class="lbl">MKT CAP / P/E</span><div class="val ca" style="font-size:0.75rem;">{fund_data['market_cap']} | {fund_data['pe']}</div></div>
      <div class="tile"><span class="lbl">EARNINGS WINDOW</span><div class="val {'cr' if fund_data['earnings_block'] else 'cg'}" style="font-size:0.75rem;">{str(fund_data['days_to_earnings'])+'d away' if fund_data['days_to_earnings'] is not None else 'No Date'}</div></div>
      <div class="tile"><span class="lbl">LAST CORP ACTION</span><div class="val cb" style="font-size:0.75rem;">{fund_data['corp_action']}</div></div>
    </div></div>""", unsafe_allow_html=True)

# ---------- SHARED UNIFIED INDICATOR ENGINE ----------
def compute_indicators(df):
    """Unified indicator engine used across both Shares and Indices tabs."""
    for col in ['open', 'high', 'low', 'close', 'volume']:
        match = next((x for x in df.columns if col in x or (col == 'close' and 'ltp' in x)), None)
        df[col] = pd.to_numeric(df[match].astype(str).str.replace(',', ''), errors='coerce') if match else (1.0 if col == 'volume' else df['close'])

    # EMAs
    df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()

    # RSI (14)
    delta = df['close'].diff()
    up = delta.clip(lower=0).rolling(14).mean()
    down = -delta.clip(upper=0).rolling(14).mean().replace(0, np.nan)
    df['rsi'] = (100 - (100 / (1 + (up / down)))).fillna(50)

    # MACD (12, 26, 9)
    ema12 = df['close'].ewm(span=12, adjust=False).mean()
    ema26 = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = ema12 - ema26
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['macd_hist'] = df['macd'] - df['macd_signal']

    # Bollinger Bands (20, 2)
    bb_mid = df['close'].rolling(20).mean()
    bb_std = df['close'].rolling(20).std()
    df['bb_upper'] = bb_mid + (2 * bb_std)
    df['bb_lower'] = bb_mid - (2 * bb_std)
    df['bb_bandwidth'] = ((df['bb_upper'] - df['bb_lower']) / bb_mid) * 100

    # ATR (14)
    tr = pd.concat([df['high'] - df['low'], (df['high'] - df['close'].shift()).abs(), (df['low'] - df['close'].shift()).abs()], axis=1).max(axis=1)
    df['atr'] = tr.rolling(14).mean().bfill()
    df['atr_avg20'] = df['atr'].rolling(20).mean().bfill()

    # Supertrend (10, 3)
    hl2 = (df['high'] + df['low']) / 2
    upper_b = hl2 + (3 * df['atr'])
    lower_b = hl2 - (3 * df['atr'])
    st_dir = np.ones(len(df))
    st_line = np.zeros(len(df))
    for i in range(1, len(df)):
        if df['close'].iloc[i] > upper_b.iloc[i-1]:
            st_dir[i] = 1
        elif df['close'].iloc[i] < lower_b.iloc[i-1]:
            st_dir[i] = -1
        else:
            st_dir[i] = st_dir[i-1]
            if st_dir[i] == 1 and lower_b.iloc[i] < lower_b.iloc[i-1]:
                lower_b.iloc[i] = lower_b.iloc[i-1]
            if st_dir[i] == -1 and upper_b.iloc[i] > upper_b.iloc[i-1]:
                upper_b.iloc[i] = upper_b.iloc[i-1]
        st_line[i] = lower_b.iloc[i] if st_dir[i] == 1 else upper_b.iloc[i]
    df['supertrend_dir'] = st_dir
    df['supertrend'] = st_line

    # Intraday VWAP
    cum_v = df['volume'].cumsum()
    cum_pv = (df['volume'] * ((df['high'] + df['low'] + df['close']) / 3)).cumsum()
    df['vwap'] = (cum_pv / cum_v.replace(0, np.nan)).bfill()

    # ADX (14)
    up_m = df['high'].diff()
    dn_m = -df['low'].diff()
    plus_dm = np.where((up_m > dn_m) & (up_m > 0), up_m, 0.0)
    minus_dm = np.where((dn_m > up_m) & (dn_m > 0), dn_m, 0.0)
    atr_w = tr.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    p_di = 100 * pd.Series(plus_dm, index=df.index).ewm(alpha=1/14, min_periods=14, adjust=False).mean() / atr_w
    m_di = 100 * pd.Series(minus_dm, index=df.index).ewm(alpha=1/14, min_periods=14, adjust=False).mean() / atr_w
    dx = 100 * (p_di - m_di).abs() / (p_di + m_di).replace(0, np.nan)
    df['adx'] = dx.ewm(alpha=1/14, min_periods=14, adjust=False).mean().fillna(0)

    # Relative Volume (RVOL) vs 20-period volume average
    df['vol_ma20'] = df['volume'].rolling(20).mean().bfill()
    df['rvol'] = df['volume'] / df['vol_ma20'].replace(0, 1)

    return df

# ---------- DATA LOADING ----------
df = None
if mode == "📁 Upload CSV":
    with st.expander(f"📂 Upload Candle Data for {inst}", expanded=True):
        up_file = st.file_uploader("Upload CSV", key="df_upload")
        if up_file:
            df = pd.read_csv(up_file)
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
        st.error(f"Error reading live feed: {ex}")

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
    sup = round(min(curr['low'] - (0.5 * atr_val), (2 * piv) - curr['high']), 2)
    res = round(max(curr['high'] + (0.5 * atr_val), (2 * piv) - curr['low']), 2)

    # 52-Week Distance
    h52 = fund_data['high52'] if fund_data['high52'] > 0 else (day_high * 1.15)
    l52 = fund_data['low52'] if fund_data['low52'] > 0 else (day_low * 0.85)
    dist_52h = ((h52 - live_p) / h52) * 100
    dist_52l = ((live_p - l52) / l52) * 100

    # Display Top Metrics Grid
    st.markdown(f"""<div class="tile" style="margin-bottom:8px;">
    <div style="display:flex;justify-content:space-between;"><span class="lbl">{inst} SPOT PRICE</span><span class="lbl cb">VWAP: ₹{vwap_val:.2f}</span></div>
    <div class="val cb" style="font-size:1.35rem;">₹{live_p:,.2f}</div>
    <div class="g4">
      <div class="tile"><span class="lbl">DAY HIGH</span><div class="val cg">₹{day_high:,.2f}</div></div>
      <div class="tile"><span class="lbl">DAY LOW</span><div class="val cr">₹{day_low:,.2f}</div></div>
      <div class="tile"><span class="lbl">DISTANCE 52W H</span><div class="val ca">{dist_52h:.1f}% below</div></div>
      <div class="tile"><span class="lbl">DISTANCE 52W L</span><div class="val ca">{dist_52l:.1f}% above</div></div>
    </div>
    <div class="g3" style="margin-top:4px;">
      <div class="tile"><span class="lbl">ADX TREND</span><div class="val {'cg' if adx_val>=20 else 'ca'}">{adx_val:.1f} ({'Trending' if adx_val>=20 else 'Choppy'})</div></div>
      <div class="tile"><span class="lbl">RELATIVE VOL (RVOL)</span><div class="val {'cg' if rvol_val>=1.2 else 'cb'}">{rvol_val:.2f}x</div></div>
      <div class="tile"><span class="lbl">SUPERTREND</span><div class="val {'cg' if curr['supertrend_dir']==1 else 'cr'}">{'BULLISH' if curr['supertrend_dir']==1 else 'BEARISH'}</div></div>
    </div>
    </div>""", unsafe_allow_html=True)

    # ---------- EXECUTION ENGINE & SCORING ----------
    st.markdown("#### 🎯 Execution Setup")

    pos = st.session_state.position

    # 1. Check Active Tracked Position
    if pos is not None and pos.get('status') == 'open':
        is_long = pos['direction'] == 'BUY'
        pnl_pts = (live_p - pos['entry']) if is_long else (pos['entry'] - live_p)

        if (is_long and live_p <= pos['sl']) or (not is_long and live_p >= pos['sl']):
            pos['status'] = 'SL Hit'; pos['exit_price'] = pos['sl']
        elif (is_long and live_p >= pos['t2']) or (not is_long and live_p <= pos['t2']):
            pos['status'] = 'Target 2 Hit'; pos['exit_price'] = pos['t2']
        elif ((is_long and live_p >= pos['t1']) or (not is_long and live_p <= pos['t1'])) and not pos.get('t1_hit'):
            pos['t1_hit'] = True; pos['sl'] = pos['entry']

        st.session_state.position = pos
        pnl_cash = pnl_pts * pos['qty']
        pnl_col = 'cg' if pnl_pts >= 0 else 'cr'

        st.markdown(f"""<div class="card-locked">
          <div style="display:flex;justify-content:space-between;"><b style="font-size:1.1rem;">📌 LIVE TRADE: {pos['label']}</b><span class="ca">Entry ₹{pos['entry']:.2f}</span></div>
          <div class="g2">
            <div class="tile"><span class="lbl">NET P&L ({pos['qty']} QTY)</span><div class="val {pnl_col}">{pnl_pts:+.2f} pts (₹{pnl_cash:+,.2f})</div></div>
            <div class="tile"><span class="lbl">PROTECTIVE SL</span><div class="val ca">₹{pos['sl']:.2f}{' · Trailed to Cost' if pos.get('t1_hit') else ''}</div></div>
          </div>
          <div class="reasons">Target 1: ₹{pos['t1']:.2f} · Target 2: ₹{pos['t2']:.2f}</div>
        </div>""", unsafe_allow_html=True)
        if st.button("✖ Close Active Trade", use_container_width=True):
            st.session_state.position = None
            st.rerun()

    elif pos is not None and pos.get('status') != 'open':
        pnl = ((pos['exit_price'] - pos['entry']) if pos['direction'] == 'BUY' else (pos['entry'] - pos['exit_price'])) * pos['qty']
        col = 'cg' if pnl >= 0 else 'cr'
        st.markdown(f"""<div class="card-locked">
          <div style="display:flex;justify-content:space-between;"><b>🏁 Outcome: {pos['status']}</b><span class="ca">{pos['label']}</span></div>
          <div class="tile"><span class="lbl">FINAL REALIZED P&L</span><div class="val {col}">₹{pnl:+,.2f}</div></div>
        </div>""", unsafe_allow_html=True)
        if st.button("🔍 Scan Next Setup", use_container_width=True, type="primary"):
            st.session_state.position = None
            st.rerun()

    else:
        # Check Earnings Hard-Gating
        if is_stock and fund_data['earnings_block']:
            st.markdown(f"""<div class="card-blocked">
              <b style="color:#ef4444;font-size:1rem;">🛑 RESULTS / EARNINGS GATING ACTIVE</b>
              <p style="margin:4px 0 0 0;font-size:0.84rem;color:#fecaca;">Company results/AGM are scheduled today or tomorrow ({fund_data['days_to_earnings']}d). Fresh intraday entries are hard-blocked to avoid extreme binary-event volatility.</p>
            </div>""", unsafe_allow_html=True)
        else:
            # Multi-parameter Confluence Assessment
            b_sc, be_sc = 0, 0
            b_reas, be_reas = [], []

            # 1. EMA Ribbon
            if curr['ema9'] > curr['ema21']: b_sc += 1; b_reas.append("EMA 9 > EMA 21 Bullish Stack")
            else: be_sc += 1; be_reas.append("EMA 9 < EMA 21 Bearish Stack")

            if curr['close'] > curr['ema50']: b_sc += 1; b_reas.append("Price Above 50 EMA Baseline")
            else: be_sc += 1; be_reas.append("Price Below 50 EMA Baseline")

            # 2. RSI & Slope
            if 52 <= curr['rsi'] <= 72: b_sc += 1; b_reas.append(f"RSI ({curr['rsi']:.1f}) in Bullish Acceleration Zone")
            elif 28 <= curr['rsi'] <= 48: be_sc += 1; be_reas.append(f"RSI ({curr['rsi']:.1f}) in Bearish Distribution Zone")

            if curr['rsi'] > prev['rsi']: b_sc += 1; b_reas.append("RSI Slope Pointing Upward")
            else: be_sc += 1; be_reas.append("RSI Slope Pointing Downward")

            # 3. MACD Cross & Histogram Momentum
            if curr['macd'] > curr['macd_signal'] and curr['macd_hist'] > 0:
                b_sc += 1; b_reas.append("MACD Bullish Cross + Expanding Positive Histogram")
            elif curr['macd'] < curr['macd_signal'] and curr['macd_hist'] < 0:
                be_sc += 1; be_reas.append("MACD Bearish Cross + Expanding Negative Histogram")

            # 4. Supertrend
            if curr['supertrend_dir'] == 1: b_sc += 1; b_reas.append("Supertrend (10,3) Bullish Support")
            else: be_sc += 1; be_reas.append("Supertrend (10,3) Bearish Resistance")

            # 5. VWAP & Intraday Levels
            if curr['close'] > vwap_val: b_sc += 1; b_reas.append("Holding Above Institutional VWAP")
            else: be_sc += 1; be_reas.append("Trading Below Institutional VWAP")

            if curr['close'] > prev['high']: b_sc += 1; b_reas.append("Previous-Candle High Breakout")
            elif curr['close'] < prev['low']: be_sc += 1; be_reas.append("Previous-Candle Low Breakdown")

            # 6. RVOL Confirmation
            if rvol_val >= 1.25 and curr['close'] > curr['open']: b_sc += 1; b_reas.append(f"High RVOL ({rvol_val:.1f}x) Bullish Participation")
            elif rvol_val >= 1.25 and curr['close'] < curr['open']: be_sc += 1; be_reas.append(f"High RVOL ({rvol_val:.1f}x) Bearish Selling Volume")

            # 7. Sentiment & Broad Market Vote
            if news_sc > 0: b_sc += 1; b_reas.append("Stock/Index News Sentiment Bullish")
            elif news_sc < 0: be_sc += 1; be_reas.append("Stock/Index News Sentiment Bearish")

            if is_stock:
                if nifty_pct >= 0.2: b_sc += 1; b_reas.append(f"Nifty Directional Tailwind (+{nifty_pct:.2f}%)")
                elif nifty_pct <= -0.2: be_sc += 1; be_reas.append(f"Nifty Directional Headwind ({nifty_pct:.2f}%)")

            MAX_CONF = 11
            def stars(score): return "★" * min(score, MAX_CONF) + "☆" * max(0, MAX_CONF - score)

            is_long_sig = b_sc >= 7 and adx_val >= 18
            is_short_sig = be_sc >= 7 and b_sc < 6 and adx_val >= 18

            if is_long_sig:
                entry = round(max(curr['high'] + (0.15 * atr_val), live_p + 0.05), 2)
                sl = round(max(sup, entry - (1.3 * atr_val)), 2)
                risk = round(max(entry - sl, atr_val * 0.8), 2)
                t1, t2 = round(entry + risk, 2), round(entry + (2 * risk), 2)

                if is_stock:
                    qty = max(1, int((trading_capital * 0.01) / risk))
                    label = f"INTRADAY BUY: {inst} (CASH/FUT)"
                else:
                    strike = int(round(live_p / step_k) * step_k)
                    qty = lot_sz
                    label = f"BUY {strike} CE"

                st.session_state.position = {
                    "direction": "BUY", "label": label, "entry": entry, "sl": sl,
                    "t1": t1, "t2": t2, "qty": qty, "status": "open", "t1_hit": False
                }

                st.markdown(f"""<div class="card-buy">
                  <div style="display:flex;justify-content:space-between;"><b class="cg" style="font-size:1.1rem;">🟢 NEW CONFLUENCE SIGNAL: {label}</b><span class="ca">{stars(b_sc)} ({b_sc}/{MAX_CONF})</span></div>
                  <div class="g2">
                    <div class="tile"><span class="lbl">ENTRY TRIGGER</span><div class="val cb">Buy Above ₹{entry:.2f}</div></div>
                    <div class="tile"><span class="lbl">STOP LOSS</span><div class="val cr">₹{sl:.2f} (-₹{risk:.2f})</div></div>
                  </div>
                  <div style="background:#090e17;border:1px solid #334155;border-radius:8px;padding:8px;margin-top:6px;">
                    <div class="rw"><span>🎯 Target 1 (50% Offload):</span><b class="cg">₹{t1:.2f} (+₹{risk:.2f})</b></div>
                    <div class="rw"><span>🏁 Target 2 (Runner Target):</span><b class="cg">₹{t2:.2f} (+₹{2*risk:.2f})</b></div>
                    <div class="rw"><span>Recommended Size:</span><b class="ca">{qty} Qty (Risk: ₹{risk * qty:,.0f})</b></div>
                  </div>
                  <div class="reasons"><span>CONFIRMING PILLARS:</span><br>• {'<br>• '.join(b_reas)}</div>
                </div>""", unsafe_allow_html=True)

            elif is_short_sig:
                entry = round(min(curr['low'] - (0.15 * atr_val), live_p - 0.05), 2)
                sl = round(min(res, entry + (1.3 * atr_val)), 2)
                risk = round(max(sl - entry, atr_val * 0.8), 2)
                t1, t2 = round(entry - risk, 2), round(entry - (2 * risk), 2)

                if is_stock:
                    qty = max(1, int((trading_capital * 0.01) / risk))
                    label = f"INTRADAY SHORT: {inst} (CASH/FUT)"
                else:
                    strike = int(round(live_p / step_k) * step_k)
                    qty = lot_sz
                    label = f"BUY {strike} PE"

                st.session_state.position = {
                    "direction": "SELL", "label": label, "entry": entry, "sl": sl,
                    "t1": t1, "t2": t2, "qty": qty, "status": "open", "t1_hit": False
                }

                st.markdown(f"""<div class="card-sell">
                  <div style="display:flex;justify-content:space-between;"><b class="cr" style="font-size:1.1rem;">🔴 NEW CONFLUENCE SIGNAL: {label}</b><span class="ca">{stars(be_sc)} ({be_sc}/{MAX_CONF})</span></div>
                  <div class="g2">
                    <div class="tile"><span class="lbl">ENTRY TRIGGER</span><div class="val cb">Sell Below ₹{entry:.2f}</div></div>
                    <div class="tile"><span class="lbl">STOP LOSS</span><div class="val cr">₹{sl:.2f} (-₹{risk:.2f})</div></div>
                  </div>
                  <div style="background:#090e17;border:1px solid #334155;border-radius:8px;padding:8px;margin-top:6px;">
                    <div class="rw"><span>🎯 Target 1 (50% Offload):</span><b class="cg">₹{t1:.2f} (+₹{risk:.2f})</b></div>
                    <div class="rw"><span>🏁 Target 2 (Runner Target):</span><b class="cg">₹{t2:.2f} (+₹{2*risk:.2f})</b></div>
                    <div class="rw"><span>Recommended Size:</span><b class="ca">{qty} Qty (Risk: ₹{risk * qty:,.0f})</b></div>
                  </div>
                  <div class="reasons"><span>CONFIRMING PILLARS:</span><br>• {'<br>• '.join(be_reas)}</div>
                </div>""", unsafe_allow_html=True)

            else:
                top_sc = max(b_sc, be_sc)
                st.markdown(f"""<div class="card-no">
                  <div style="display:flex;justify-content:space-between;"><b style="color:#fbbf24;">⛔ CONFLUENCE THRESHOLD NOT MET</b><span class="ca">{stars(top_sc)} ({top_sc}/{MAX_CONF})</span></div>
                  <p style="margin:4px 0 0 0;font-size:0.84rem;">Score: {top_sc}/{MAX_CONF}. Requires ≥ 7 confluent indicators with ADX ≥ 18. Consolidating between Support ₹{sup:.2f} and Resistance ₹{res:.2f}.</p>
                </div>""", unsafe_allow_html=True)

    # ---------- MULTI-PANEL CHART ----------
    st.markdown("#### 📈 Multi-Indicator Technical Chart")
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.58, 0.22, 0.20])
    sub = df.tail(50)

    # Candlestick + Supertrend + Bollinger Bands + EMAs + VWAP
    fig.add_trace(go.Candlestick(x=sub['time'], open=sub['open'], high=sub['high'], low=sub['low'], close=sub['close'], increasing_line_color='#10b981', decreasing_line_color='#f43f5e', name="Price"), row=1, col=1)
    fig.add_trace(go.Scatter(x=sub['time'], y=sub['ema9'], line=dict(color='#38bdf8', width=1.2), name="EMA 9"), row=1, col=1)
    fig.add_trace(go.Scatter(x=sub['time'], y=sub['ema21'], line=dict(color='#f59e0b', width=1.2), name="EMA 21"), row=1, col=1)
    fig.add_trace(go.Scatter(x=sub['time'], y=sub['vwap'], line=dict(color='#c084fc', width=1.5, dash="dot"), name="VWAP"), row=1, col=1)
    fig.add_trace(go.Scatter(x=sub['time'], y=sub['supertrend'], line=dict(color='#10b981' if curr['supertrend_dir']==1 else '#f43f5e', width=1.5), name="Supertrend"), row=1, col=1)
    fig.add_trace(go.Scatter(x=sub['time'], y=sub['bb_upper'], line=dict(color='rgba(148,163,184,0.4)', width=1), name="BB Upper"), row=1, col=1)
    fig.add_trace(go.Scatter(x=sub['time'], y=sub['bb_lower'], line=dict(color='rgba(148,163,184,0.4)', width=1), name="BB Lower"), row=1, col=1)

    # MACD + Histogram
    hist_cols = ['#10b981' if val >= 0 else '#f43f5e' for val in sub['macd_hist']]
    fig.add_trace(go.Bar(x=sub['time'], y=sub['macd_hist'], marker_color=hist_cols, name="MACD Hist"), row=2, col=1)
    fig.add_trace(go.Scatter(x=sub['time'], y=sub['macd'], line=dict(color='#38bdf8', width=1.2), name="MACD"), row=2, col=1)
    fig.add_trace(go.Scatter(x=sub['time'], y=sub['macd_signal'], line=dict(color='#f59e0b', width=1.2), name="Signal"), row=2, col=1)

    # RSI
    fig.add_trace(go.Scatter(x=sub['time'], y=sub['rsi'], line=dict(color='#c084fc', width=1.3), name="RSI"), row=3, col=1)
    fig.add_hline(y=70, line_dash="dot", line_color="#f43f5e", row=3, col=1)
    fig.add_hline(y=30, line_dash="dot", line_color="#10b981", row=3, col=1)

    fig.update_layout(height=540, margin=dict(l=5, r=5, t=10, b=10), xaxis_rangeslider_visible=False, template="plotly_dark", paper_bgcolor="#07090e", plot_bgcolor="#07090e", showlegend=False)
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

else:
    st.info("Awaiting live stream data. Click '🔄 Sync Now' above or upload a CSV file.")
