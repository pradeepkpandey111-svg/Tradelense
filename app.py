import streamlit as st, pandas as pd, numpy as np, yfinance as yf, feedparser
from streamlit_autorefresh import st_autorefresh
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))

st.set_page_config(page_title="TradeLense AI Terminal", page_icon="⚡", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""<style>
header[data-testid="stHeader"]{visibility:hidden!important;height:0!important;}
html,body,[class*="css"],.stMarkdown{font-family:'Plus Jakarta Sans',sans-serif!important;background:#07090e;color:#fff!important;}
.block-container{padding:1.2rem 0.6rem 2.5rem 0.6rem!important;}
.banner{background:linear-gradient(135deg,#0f172a,#1e293b);border:1px solid #334155;border-radius:12px;padding:12px;margin-bottom:8px;}
.card-buy{background:#062b20;border-left:5px solid #10b981;border-radius:10px;padding:12px;margin-bottom:8px;}
.card-sell{background:#2d0c13;border-left:5px solid #f43f5e;border-radius:10px;padding:12px;margin-bottom:8px;}
.card-no{background:#241703;border-left:5px solid #f59e0b;border-radius:10px;padding:12px;margin-bottom:8px;}
.card-locked{background:#0c1a2b;border:1px solid #38bdf8;border-left:6px solid #38bdf8;border-radius:10px;padding:14px;margin-bottom:8px;}
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
  <div style="font-size:1.3rem;font-weight:800;">⚡ TradeLense AI Pro Terminal</div>
  <div style="font-size:0.75rem;color:#94a3b8;">Full Confluence: Price Action, Technicals, Fundamentals, News & Macro</div>
</div>""", unsafe_allow_html=True)

if "positions" not in st.session_state:
    st.session_state.positions = {}

col_tab1, col_tab2 = st.columns([1, 1.2])
asset_tab = col_tab1.radio("Trading Module", ["Option Indices", "Shares"], horizontal=True)

POPULAR_STOCKS = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS", "TATAMOTORS.NS", "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "LT.NS"]

if asset_tab == "Option Indices":
    inst = col_tab2.selectbox("Target Index", ["NIFTY 50", "BANK NIFTY"])
    sym = "^NSEI" if inst == "NIFTY 50" else "^NSEBANK"
    nse_sym = "NIFTY" if inst == "NIFTY 50" else "BANKNIFTY"
    step_k, lot_sz, delta_approx = (50, 50, 0.52) if inst == "NIFTY 50" else (100, 15, 0.52)
    is_stock = False
else:
    pick = col_tab2.selectbox("Select Share", POPULAR_STOCKS)
    sym, inst = pick, pick.replace(".NS", "")
    nse_sym = inst
    step_k, lot_sz, delta_approx = 1, 1, 1.0
    is_stock = True

c_m1, c_m2 = st.columns([1.2, 1])
timeframe = c_m1.selectbox("Candle Timeframe", ["5m", "15m"], index=0)
auto_on = c_m2.toggle("Auto-refresh", value=True)
trading_capital = st.number_input("Account Capital (₹)", value=100000, step=25000) if is_stock else 50000

if auto_on:
    st_autorefresh(interval=15000, key="desk_refresh_sync")

# 1. Global Macro Data
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

# 2. News & Corporate Fundamentals Engine
@st.cache_data(ttl=300)
def fetch_news_and_fundamentals(q_sym, is_stk):
    query = f"{q_sym}+share+price" if is_stk else "Nifty+Indian+stock+market"
    f = feedparser.parse(f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en")
    items, b_w, be_w, sc = [], ['surge', 'rally', 'jump', 'gain', 'profit', 'expansion', 'buy', 'high'], ['slump', 'drop', 'fall', 'probe', 'cut', 'loss', 'fraud', 'miss'], 0
    for e in f.entries[:3]:
        t = e.title
        src = e.source.title if 'source' in e and 'title' in e.source else "FINANCE"
        p = any(w in t.lower() for w in b_w)
        n = any(w in t.lower() for w in be_w)
        if p: sc += 1
        if n: sc -= 1
        tag = "<span class='cg'>🟢 Bullish</span>" if p else ("<span class='cr'>🔴 Bearish</span>" if n else "<span class='ca'>⚪ Neutral</span>")
        items.append({"title": t, "source": src, "tag": tag})

    fund = {"sector": "Indices / Derivatives" if not is_stk else "Equities", "market_cap": "N/A", "pe": "N/A", "high52": 0.0, "low52": 0.0, "days_to_earnings": None, "earnings_block": False, "corp_action": "None"}
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
                    if "Earnings Date" in cal.index: e_date = pd.to_datetime(cal.loc["Earnings Date"].iloc[0])
                    elif 0 in cal.columns: e_date = pd.to_datetime(cal.iloc[0, 0])
                elif isinstance(cal, dict) and "Earnings Date" in cal: e_date = pd.to_datetime(cal["Earnings Date"][0])
                if e_date is not None:
                    delta_days = (e_date.date() - datetime.now(timezone.utc).date()).days
                    fund["days_to_earnings"] = delta_days
                    if 0 <= delta_days <= 1: fund["earnings_block"] = True
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

news_sent, news_sc, news_feed, fund_data = fetch_news_and_fundamentals(nse_sym, is_stock)

# Macro Display Ribbon
st.markdown(f"""<div class="tile" style="margin-bottom:8px;">
<div style="display:flex;justify-content:space-between;"><span class="lbl">🌐 GLOBAL MACRO</span><span class="lbl ca">{news_sent}</span></div>
<div class="g4">
<div class="tile"><span class="lbl">S&P 500</span><div class="val {'cg' if mac['S&P 500']['pct']>=0 else 'cr'}">{mac['S&P 500']['pct']:+.2f}%</div></div>
<div class="tile"><span class="lbl">NASDAQ</span><div class="val {'cg' if mac['Nasdaq']['pct']>=0 else 'cr'}">{mac['Nasdaq']['pct']:+.2f}%</div></div>
<div class="tile"><span class="lbl">CRUDE (INV)</span><div class="val {'cr' if mac['Crude']['pct']>0 else 'cg'}">{mac['Crude']['pct']:+.2f}%</div></div>
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

# 3. Candle Ingestion & Indicator Math
@st.cache_data(ttl=15)
def get_data(s, tf):
    try:
        raw = yf.download(s, period="5d", interval=tf, progress=False)
        if len(raw) > 5:
            raw.columns = [c[0].lower() if isinstance(c, tuple) else c.lower() for c in raw.columns]
            raw = raw.reset_index()
            t_col = next((x for x in raw.columns if 'time' in x or 'date' in x), raw.columns[0])
            raw['time'] = pd.to_datetime(raw[t_col])
            return raw.sort_values('time').reset_index(drop=True)
    except: pass
    return None

df = get_data(sym, timeframe)
if df is not None and len(df) > 20:
    for c in ['open', 'high', 'low', 'close']:
        m = next((x for x in df.columns if c in x), None)
        df[c] = pd.to_numeric(df[m].astype(str).str.replace(',', ''), errors='coerce')
    
    vol_col = next((x for x in df.columns if 'volume' in x), None)
    df['volume'] = pd.to_numeric(df[vol_col], errors='coerce').fillna(0) if vol_col else 0

    df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()

    # RSI (14)
    d = df['close'].diff()
    u = d.clip(lower=0).rolling(14).mean()
    dn = -d.clip(upper=0).rolling(14).mean().replace(0, np.nan)
    df['rsi'] = (100 - (100 / (1 + (u / dn)))).fillna(50)

    # MACD (12, 26, 9)
    e12, e26 = df['close'].ewm(span=12, adjust=False).mean(), df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = e12 - e26
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['macd_hist'] = df['macd'] - df['macd_signal']

    # Bollinger Bands (20, 2)
    bb_mid = df['close'].rolling(20).mean()
    bb_std = df['close'].rolling(20).std()
    df['bb_upper'] = bb_mid + (2 * bb_std)
    df['bb_lower'] = bb_mid - (2 * bb_std)

    # ATR & Supertrend
    tr = pd.concat([df['high'] - df['low'], (df['high'] - df['close'].shift()).abs(), (df['low'] - df['close'].shift()).abs()], axis=1).max(axis=1)
    df['atr'] = tr.rolling(14).mean().bfill()
    hl2 = (df['high'] + df['low']) / 2
    u_b, l_b = hl2 + (3 * df['atr']), hl2 - (3 * df['atr'])
    st_dir = np.ones(len(df))
    for i in range(1, len(df)):
        if df['close'].iloc[i] > u_b.iloc[i-1]: st_dir[i] = 1
        elif df['close'].iloc[i] < l_b.iloc[i-1]: st_dir[i] = -1
        else: st_dir[i] = st_dir[i-1]
    df['supertrend_dir'] = st_dir

    # Fixed Session VWAP
    has_valid_vol = df['volume'].sum() > 0
    if has_valid_vol:
        df['date_grp'] = df['time'].dt.date
        df['pv'] = (df['high'] + df['low'] + df['close']) / 3 * df['volume']
        df['vwap'] = df.groupby('date_grp')['pv'].cumsum() / df.groupby('date_grp')['volume'].cumsum().replace(0, np.nan)
        df['vwap'] = df['vwap'].ffill().bfill()
        df['vol_ma20'] = df['volume'].rolling(20).mean().bfill()
        df['rvol'] = df['volume'] / df['vol_ma20'].replace(0, 1)
    else:
        df['vwap'] = ((df['high'] + df['low'] + df['close']) / 3).ewm(span=20, adjust=False).mean()
        df['rvol'] = 1.0

    # ADX (14)
    up_m, dn_m = df['high'].diff(), -df['low'].diff()
    p_dm = np.where((up_m > dn_m) & (up_m > 0), up_m, 0.0)
    m_dm = np.where((dn_m > up_m) & (dn_m > 0), dn_m, 0.0)
    atr_w = tr.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    p_di = 100 * pd.Series(p_dm, index=df.index).ewm(alpha=1/14, min_periods=14, adjust=False).mean() / atr_w
    m_di = 100 * pd.Series(m_dm, index=df.index).ewm(alpha=1/14, min_periods=14, adjust=False).mean() / atr_w
    df['adx'] = (100 * (p_di - m_di).abs() / (p_di + m_di).replace(0, np.nan)).ewm(alpha=1/14, min_periods=14, adjust=False).mean().fillna(0)

    curr, prev = df.iloc[-2], df.iloc[-3]
    live_p = float(df['close'].iloc[-1])
    day_high, day_low = float(df['high'].tail(50).max()), float(df['low'].tail(50).min())
    atr_val = float(curr['atr']) if curr['atr'] > 0 else live_p * 0.005
    vwap_val = float(curr['vwap'])
    adx_val = float(curr['adx'])
    rvol_val = float(curr['rvol'])

    piv = (curr['high'] + curr['low'] + curr['close']) / 3
    sup = round(min(curr['low'] - (0.4 * atr_val), (2 * piv) - curr['high']), 1)
    res = round(max(curr['high'] + (0.4 * atr_val), (2 * piv) - curr['low']), 1)

    h52 = fund_data['high52'] if fund_data['high52'] > 0 else (day_high * 1.15)
    l52 = fund_data['low52'] if fund_data['low52'] > 0 else (day_low * 0.85)
    dist_52h = ((h52 - live_p) / h52) * 100
    dist_52l = ((live_p - l52) / l52) * 100

    # Display Top Metrics Grid
    st.markdown(f"""<div class="tile" style="margin-bottom:8px;">
    <div style="display:flex;justify-content:space-between;"><span class="lbl">{inst} SPOT</span><span class="lbl cb">TF: {timeframe}</span></div>
    <div class="val cb" style="font-size:1.4rem;">₹{live_p:,.2f}</div>
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

    # Technical Radar
    st.markdown(f"""<div class="tile" style="margin-bottom:8px;">
    <div style="display:flex;justify-content:space-between;"><span class="lbl">⚡ TECHNICAL RADAR</span><span class="lbl cb">RSI: {curr['rsi']:.1f}</span></div>
    <div class="g4">
      <div class="tile"><span class="lbl">EMA 9 / 21 / 50</span><div class="val {'cg' if (curr['ema9']>curr['ema21'] and curr['close']>curr['ema50']) else 'cr'}">{'BULL ALIGNED' if (curr['ema9']>curr['ema21'] and curr['close']>curr['ema50']) else 'BEAR / MIXED'}</div></div>
      <div class="tile"><span class="lbl">SUPERTREND</span><div class="val {'cg' if curr['supertrend_dir']==1 else 'cr'}">{'BULLISH' if curr['supertrend_dir']==1 else 'BEARISH'}</div></div>
      <div class="tile"><span class="lbl">MACD HIST</span><div class="val {'cg' if curr['macd_hist']>=0 else 'cr'}">{curr['macd_hist']:+.2f}</div></div>
      <div class="tile"><span class="lbl">RVOL (20MA)</span><div class="val {'cg' if rvol_val>=1.2 else 'ca'}">{rvol_val:.2f}x</div></div>
    </div></div>""", unsafe_allow_html=True)

    # Confluence Scoring Engine
    b_sc, be_sc = 0, 0
    b_reas, be_reas = [], []
    total_active_pillars = 0

    # 1. EMA Structure
    total_active_pillars += 2
    if curr['ema9'] > curr['ema21']: b_sc += 1; b_reas.append("EMA 9 > EMA 21 Bullish Stack")
    else: be_sc += 1; be_reas.append("EMA 9 < EMA 21 Bearish Stack")
    if curr['close'] >= curr['ema50']: b_sc += 1; b_reas.append("Holding Above EMA 50 Baseline")
    else: be_sc += 1; be_reas.append("Trading Below EMA 50 Baseline")

    # 2. RSI Momentum
    total_active_pillars += 2
    rsi_val = curr['rsi']
    if rsi_val >= 52: b_sc += 1; b_reas.append(f"RSI ({rsi_val:.1f}) in Bullish Zone")
    elif rsi_val <= 48: be_sc += 1; be_reas.append(f"RSI ({rsi_val:.1f}) in Bearish Zone")
    if rsi_val >= prev['rsi']: b_sc += 1; b_reas.append("RSI Slope Rising")
    else: be_sc += 1; be_reas.append("RSI Slope Falling")

    # 3. MACD Cross & Hist
    total_active_pillars += 1
    if curr['macd'] >= curr['macd_signal'] and curr['macd_hist'] >= 0: b_sc += 1; b_reas.append("MACD Bullish Cross + Positive Histogram")
    elif curr['macd'] <= curr['macd_signal'] and curr['macd_hist'] <= 0: be_sc += 1; be_reas.append("MACD Bearish Cross + Negative Histogram")

    # 4. Supertrend
    total_active_pillars += 1
    if curr['supertrend_dir'] == 1: b_sc += 1; b_reas.append("Supertrend (10,3) Bullish Support")
    else: be_sc += 1; be_reas.append("Supertrend (10,3) Bearish Resistance")

    # 5. Session VWAP
    total_active_pillars += 1
    if curr['close'] >= vwap_val: b_sc += 1; b_reas.append("Holding Above Session VWAP")
    else: be_sc += 1; be_reas.append("Trading Below Session VWAP")

    # 6. Bollinger Bands
    total_active_pillars += 1
    if curr['close'] >= curr['bb_upper'] * 0.995: b_sc += 1; b_reas.append("Riding Upper Bollinger Band (Expansion)")
    elif curr['close'] <= curr['bb_lower'] * 1.005: be_sc += 1; be_reas.append("Riding Lower Bollinger Band (Expansion)")

    # 7. Price Action & Candle Structure
    total_active_pillars += 1
    if curr['close'] > prev['high']: b_sc += 1; b_reas.append("Closed Above Prior Candle High")
    elif curr['close'] < prev['low']: be_sc += 1; be_reas.append("Closed Below Prior Candle Low")
    else:
        if curr['close'] > curr['ema9']: b_sc += 1; b_reas.append("Consolidation Holding EMA 9 Support")
        elif curr['close'] < curr['ema9']: be_sc += 1; be_reas.append("Consolidation Holding EMA 9 Resistance")

    # 8. Sentiment & Market Vote
    total_active_pillars += 1
    if news_sc > 0: b_sc += 1; b_reas.append("Live News Feed Sentiment Bullish")
    elif news_sc < 0: be_sc += 1; be_reas.append("Live News Feed Sentiment Bearish")

    if is_stock:
        total_active_pillars += 1
        if nifty_pct >= 0.15: b_sc += 1; b_reas.append(f"Nifty Market Tailwind (+{nifty_pct:.2f}%)")
        elif nifty_pct <= -0.15: be_sc += 1; be_reas.append(f"Nifty Market Headwind ({nifty_pct:.2f}%)")

    # Require >= 60% of testable factors + Trending ADX
    needed_score = max(5, int(np.ceil(total_active_pillars * 0.60)))
    def stars(sc, total=total_active_pillars): return "★" * min(sc, total) + "☆" * max(0, total - sc)

    is_long = (b_sc >= needed_score) and (adx_val >= 18)
    is_short = (be_sc >= needed_score) and (b_sc < needed_score) and (adx_val >= 18)

    st.markdown("#### 🎯 Execution Desk")
    pos = st.session_state.positions.get(inst)

    if pos is not None and pos.get('status') == 'active':
        is_l = pos['direction'] == 'BUY'
        pnl_pts = (live_p - pos['entry']) if is_l else (pos['entry'] - live_p)
        pnl_cash = pnl_pts * pos.get('delta', 1.0) * pos['qty']
        col_p = 'cg' if pnl_pts >= 0 else 'cr'

        if (is_l and live_p <= pos['sl']) or (not is_l and live_p >= pos['sl']):
            pos['status'] = 'SL Hit'; pos['exit_price'] = pos['sl']
        elif (is_l and live_p >= pos['t2']) or (not is_l and live_p <= pos['t2']):
            pos['status'] = 'Target 2 Hit'; pos['exit_price'] = pos['t2']
        elif ((is_l and live_p >= pos['t1']) or (not is_l and live_p <= pos['t1'])) and not pos.get('t1_hit'):
            pos['t1_hit'] = True; pos['sl'] = pos['entry']

        st.session_state.positions[inst] = pos
        st.markdown(f"""<div class="card-locked">
          <div style="display:flex;justify-content:space-between;"><b style="color:#38bdf8;">📌 ACTIVE: {pos['label']}</b><span class="ca">Entry ₹{pos['entry']:.2f}</span></div>
          <div class="g2">
            <div class="tile"><span class="lbl">P&L ({pos['qty']} QTY)</span><div class="val {col_p}">{pnl_pts:+.2f} pts (₹{pnl_cash:+,.2f})</div></div>
            <div class="tile"><span class="lbl">ACTIVE SL</span><div class="val ca">₹{pos['sl']:.2f}{' · Breakeven' if pos.get('t1_hit') else ''}</div></div>
          </div>
          <div class="reasons">🎯 Targets: T1 ₹{pos['t1']:.2f} | T2 ₹{pos['t2']:.2f}</div>
        </div>""", unsafe_allow_html=True)
        if st.button(f"Square Off {inst}", use_container_width=True):
            st.session_state.positions[inst] = None
            st.rerun()

    elif pos is not None and pos.get('status') != 'active':
        realized = (((pos['exit_price'] - pos['entry']) if pos['direction'] == 'BUY' else (pos['entry'] - pos['exit_price'])) * pos.get('delta', 1.0)) * pos['qty']
        st.markdown(f"""<div class="card-locked">
          <div style="display:flex;justify-content:space-between;"><b>🏁 Outcome: {pos['status']}</b><span class="ca">{pos['label']}</span></div>
          <div class="tile"><span class="lbl">REALIZED P&L</span><div class="val {'cg' if realized>=0 else 'cr'}">₹{realized:+,.2f}</div></div>
        </div>""", unsafe_allow_html=True)
        if st.button("🔍 Scan Next Setup", use_container_width=True, type="primary"):
            st.session_state.positions[inst] = None
            st.rerun()

    else:
        if is_stock and fund_data['earnings_block']:
            st.markdown(f"""<div class="card-blocked"><b style="color:#ef4444;">🛑 EARNINGS EVENT GATING ACTIVE</b><p style="margin:4px 0 0 0;font-size:0.84rem;">Company results are scheduled within 24 hours. Trades are blocked to prevent binary gap risk.</p></div>""", unsafe_allow_html=True)
        elif is_long:
            entry = round(curr['high'] + max(0.15 * atr_val, 0.10), 2)
            sl = round(max(sup, entry - (1.4 * atr_val)), 2)
            risk = round(max(entry - sl, atr_val * 0.8), 2)
            t1, t2 = round(entry + (1.2 * risk), 2), round(entry + (2.2 * risk), 2)
            qty = max(1, int((trading_capital * 0.01) / risk)) if is_stock else lot_sz
            lbl = f"INTRADAY BUY: {inst}" if is_stock else f"BUY {int(round(live_p/step_k)*step_k)} CE"
            st.session_state.positions[inst] = {"direction": "BUY", "label": lbl, "entry": entry, "sl": sl, "t1": t1, "t2": t2, "qty": qty, "status": "active", "delta": delta_approx, "t1_hit": False}
            st.rerun()
        elif is_short:
            entry = round(curr['low'] - max(0.15 * atr_val, 0.10), 2)
            sl = round(min(res, entry + (1.4 * atr_val)), 2)
            risk = round(max(sl - entry, atr_val * 0.8), 2)
            t1, t2 = round(entry - (1.2 * risk), 2), round(entry - (2.2 * risk), 2)
            qty = max(1, int((trading_capital * 0.01) / risk)) if is_stock else lot_sz
            lbl = f"INTRADAY SHORT: {inst}" if is_stock else f"BUY {int(round(live_p/step_k)*step_k)} PE"
            st.session_state.positions[inst] = {"direction": "SELL", "label": lbl, "entry": entry, "sl": sl, "t1": t1, "t2": t2, "qty": qty, "status": "active", "delta": delta_approx, "t1_hit": False}
            st.rerun()
        else:
            top_sc = max(b_sc, be_sc)
            st.markdown(f"""<div class="card-no">
              <div style="display:flex;justify-content:space-between;"><b style="color:#fbbf24;">⛔ SCANNING CONFLUENCE CRITERIA</b><span class="ca">{stars(top_sc)} ({top_sc}/{total_active_pillars})</span></div>
              <p style="margin:4px 0 0 0;font-size:0.84rem;">Score: {top_sc}/{total_active_pillars} (Requires ≥ {needed_score} with ADX ≥ 18). Support: ₹{sup:,.1f} | Resistance: ₹{res:,.1f}.</p>
            </div>""", unsafe_allow_html=True)
else:
    st.info("Pulling clean market feed...")