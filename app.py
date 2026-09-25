import streamlit as st, pandas as pd, numpy as np, yfinance as yf, requests
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
.card-no{background:#18181b;border-left:5px solid #f59e0b;border-radius:10px;padding:14px;margin-bottom:8px;}
.card-locked{background:#0c1a2b;border:1px solid #38bdf8;border-left:6px solid #38bdf8;border-radius:10px;padding:14px;margin-bottom:8px;}
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
  <div style="font-size:0.75rem;color:#94a3b8;">Smart Name Search & Real-Time Confluence Signals</div>
</div>""", unsafe_allow_html=True)

if "positions" not in st.session_state:
    st.session_state.positions = {}

col_tab1, col_tab2 = st.columns([1, 1.2])
asset_tab = col_tab1.radio("Trading Module", ["Option Indices", "Shares"], horizontal=True)

NIFTY_50_STOCKS = [
    "🔍 Search by Name / Company",
    "RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "BHARTIARTL", "INFY", "ITC", "LT",
    "SBIN", "HINDUNILVR", "TATAMOTORS", "BAJFINANCE", "MARUTI", "SUNPHARMA", "AXISBANK",
    "KOTAKBANK", "NTPC", "TITAN", "ONGC", "M&M", "ADANIENT", "POWERGRID", "TATASTEEL",
    "COALINDIA", "BAJAJFINSV", "ASIANPAINT", "HCLTECH", "ADANIPORTS", "WIPRO", "NESTLEIND",
    "ULTRACEMCO", "GRASIM", "JSWSTEEL", "TECHM", "BPCL", "HEROMOTOCO", "EICHERMOT",
    "DRREDDY", "CIPLA", "INDUSINDBK", "SBILIFE", "BRITANNIA", "HDFCLIFE", "DIVISLAB",
    "APOLLOHOSP", "TATACONSUM", "BAJAJ-AUTO", "LTIM", "HINDALCO", "SHRIRAMFIN"
]

@st.cache_data(ttl=3600)
def search_stock_symbols(query):
    if not query or len(query.strip()) < 2:
        return []
    url = f"https://autoc.finance.yahoo.com/autoc?query={query}&region=1&lang=en"
    try:
        r = requests.get(url, timeout=4).json()
        results = []
        for item in r.get('ResultSet', {}).get('Result', []):
            sym = item.get('symbol', '')
            name = item.get('name', '')
            exch = item.get('exchDisp', '')
            # Filter specifically for Indian NSE/BSE listed equities
            if sym.endswith('.NS') or sym.endswith('.BO') or 'NSE' in exch or 'BSE' in exch:
                clean_sym = sym if sym.endswith('.NS') else f"{sym.split('.')[0]}.NS"
                results.append(f"{name} ({clean_sym})")
        return results[:8]
    except:
        return []

if asset_tab == "Option Indices":
    inst = col_tab2.selectbox("Target Index", ["NIFTY 50", "BANK NIFTY"])
    sym = "^NSEI" if inst == "NIFTY 50" else "^NSEBANK"
    step_k, lot_sz, delta_approx = (50, 50, 0.52) if inst == "NIFTY 50" else (100, 15, 0.52)
    is_stock = False
else:
    pick = col_tab2.selectbox("Select Stock", NIFTY_50_STOCKS, index=1)
    if pick == "🔍 Search by Name / Company":
        search_query = st.text_input("Enter Company Name or Word", value="Policy bazaar", placeholder="e.g. Policy bazaar, Tata Motors, Zomato").strip()
        matches = search_stock_symbols(search_query)
        if matches:
            chosen = st.selectbox("Select Matching Company", matches)
            # Extract symbol inside parenthesis
            sym = chosen.split('(')[-1].replace(')', '').strip()
            inst = sym.replace('.NS', '')
        else:
            # Fallback
            clean = search_query.upper().replace(' ', '')
            sym = f"{clean}.NS"
            inst = clean
    else:
        inst = pick
        sym = f"{pick}.NS"
    step_k, lot_sz, delta_approx = 1, 1, 1.0
    is_stock = True

c_m1, c_m2 = st.columns([1.2, 1])
timeframe = c_m1.selectbox("Candle Timeframe", ["5m", "15m"], index=0)
auto_on = c_m2.toggle("Auto-refresh", value=True)
trading_capital = st.number_input("Account Capital (₹)", value=100000, step=25000) if is_stock else 50000

if auto_on:
    st_autorefresh(interval=15000, key="desk_refresh_sync")

now_ist = datetime.now(IST)
m_mins = now_ist.hour * 60 + now_ist.minute
is_market_open = (9 * 60 + 15) <= m_mins <= (15 * 60 + 30)

@st.cache_data(ttl=15)
def get_clean_candles(s, tf):
    try:
        raw = yf.download(s, period="5d", interval=tf, progress=False)
        if len(raw) >= 15:
            raw.columns = [c[0].lower() if isinstance(c, tuple) else c.lower() for c in raw.columns]
            raw = raw.reset_index()
            t_col = next((x for x in raw.columns if 'time' in x or 'date' in x), raw.columns[0])
            raw['time'] = pd.to_datetime(raw[t_col])
            raw = raw.dropna(subset=['close']).sort_values('time').reset_index(drop=True)
            return raw
    except: pass
    return None

df = get_clean_candles(sym, timeframe)
if df is not None and len(df) > 20:
    for c in ['open', 'high', 'low', 'close']:
        m = next((x for x in df.columns if c in x), None)
        df[c] = pd.to_numeric(df[m].astype(str).str.replace(',', ''), errors='coerce')
    
    vol_col = next((x for x in df.columns if 'volume' in x), None)
    df['volume'] = pd.to_numeric(df[vol_col], errors='coerce').fillna(0) if vol_col else 0

    df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()

    delta = df['close'].diff()
    up = delta.clip(lower=0).rolling(14).mean()
    down = -delta.clip(upper=0).rolling(14).mean().replace(0, np.nan)
    df['rsi'] = (100 - (100 / (1 + (up / down)))).fillna(50)

    e12, e26 = df['close'].ewm(span=12, adjust=False).mean(), df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = e12 - e26
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['macd_hist'] = df['macd'] - df['macd_signal']

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

    if df['volume'].sum() > 0:
        df['date_grp'] = df['time'].dt.date
        df['pv'] = (df['high'] + df['low'] + df['close']) / 3 * df['volume']
        df['vwap'] = df.groupby('date_grp')['pv'].cumsum() / df.groupby('date_grp')['volume'].cumsum().replace(0, np.nan)
        df['vwap'] = df['vwap'].ffill().bfill()
    else:
        df['vwap'] = ((df['high'] + df['low'] + df['close']) / 3).ewm(span=20, adjust=False).mean()

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

    sup = round(min(curr['low'] - (0.3 * atr_val), live_p - (0.6 * atr_val)), 1)
    res = round(max(curr['high'] + (0.3 * atr_val), live_p + (0.6 * atr_val)), 1)

    st.markdown(f"""<div class="tile" style="margin-bottom:8px;">
    <div style="display:flex;justify-content:space-between;"><span class="lbl">{inst} SPOT</span><span class="lbl cb">TF: {timeframe} | ADX: {adx_val:.1f}</span></div>
    <div class="val cb" style="font-size:1.4rem;">₹{live_p:,.2f}</div>
    <div class="g4">
      <div class="tile"><span class="lbl">SUPPORT</span><div class="val cg">₹{sup:,.1f}</div></div>
      <div class="tile"><span class="lbl">RESISTANCE</span><div class="val cr">₹{res:,.1f}</div></div>
      <div class="tile"><span class="lbl">DAY HIGH</span><div class="val cg">₹{day_high:,.1f}</div></div>
      <div class="tile"><span class="lbl">DAY LOW</span><div class="val cr">₹{day_low:,.1f}</div></div>
    </div></div>""", unsafe_allow_html=True)

    st.markdown(f"""<div class="tile" style="margin-bottom:8px;">
    <div style="display:flex;justify-content:space-between;"><span class="lbl">⚡ TECHNICAL RADAR</span><span class="lbl cb">STATUS: {'MARKET OPEN' if is_market_open else 'PRE/POST MARKET'}</span></div>
    <div class="g4">
      <div class="tile"><span class="lbl">EMA 9/21/50</span><div class="val {'cg' if (curr['ema9']>curr['ema21'] and curr['close']>curr['ema50']) else 'cr'}">{'BULL' if (curr['ema9']>curr['ema21'] and curr['close']>curr['ema50']) else 'BEAR'}</div></div>
      <div class="tile"><span class="lbl">RSI (14)</span><div class="val {'cg' if curr['rsi']>=50 else 'cr'}">{curr['rsi']:.1f}</div></div>
      <div class="tile"><span class="lbl">SUPERTREND</span><div class="val {'cg' if curr['supertrend_dir']==1 else 'cr'}">{'BULL' if curr['supertrend_dir']==1 else 'BEAR'}</div></div>
      <div class="tile"><span class="lbl">VWAP BIAS</span><div class="val {'cg' if live_p>=vwap_val else 'cr'}">{'ABOVE' if live_p>=vwap_val else 'BELOW'}</div></div>
    </div></div>""", unsafe_allow_html=True)

    b_sc, be_sc = 0, 0
    b_reas, be_reas = [], []
    total_pillars = 7

    if curr['ema9'] > curr['ema21']: b_sc += 1; b_reas.append("EMA 9 > 21 Bullish Stack")
    else: be_sc += 1; be_reas.append("EMA 9 < 21 Bearish Stack")

    if curr['close'] >= curr['ema50']: b_sc += 1; b_reas.append("Above 50 EMA Baseline")
    else: be_sc += 1; be_reas.append("Below 50 EMA Baseline")

    if curr['rsi'] >= 52: b_sc += 1; b_reas.append(f"RSI Bullish ({curr['rsi']:.1f})")
    elif curr['rsi'] <= 48: be_sc += 1; be_reas.append(f"RSI Bearish ({curr['rsi']:.1f})")

    if curr['supertrend_dir'] == 1: b_sc += 1; b_reas.append("Supertrend Bullish")
    else: be_sc += 1; be_reas.append("Supertrend Bearish")

    if live_p >= vwap_val: b_sc += 1; b_reas.append("Above Session VWAP")
    else: be_sc += 1; be_reas.append("Below Session VWAP")

    if curr['macd_hist'] >= 0: b_sc += 1; b_reas.append("MACD Bullish Histogram")
    else: be_sc += 1; be_reas.append("MACD Bearish Histogram")

    if curr['close'] > prev['high']: b_sc += 1; b_reas.append("Prior Candle High Breakout")
    elif curr['close'] < prev['low']: be_sc += 1; be_reas.append("Prior Candle Low Breakdown")

    needed = 5
    is_buy = (b_sc >= needed) and (adx_val >= 18) and is_market_open
    is_sell = (be_sc >= needed) and (b_sc < needed) and (adx_val >= 18) and is_market_open

    st.markdown("#### 🎯 Execution Desk")
    pos = st.session_state.positions.get(inst)

    if pos is not None and pos.get('status') == 'active':
        is_l = pos['direction'] == 'BUY'
        pnl_pts = (live_p - pos['entry']) if is_l else (pos['entry'] - live_p)
        col_p = 'cg' if pnl_pts >= 0 else 'cr'

        if (is_l and live_p <= pos['sl']) or (not is_l and live_p >= pos['sl']):
            pos['status'] = 'SL Hit'
        elif (is_l and live_p >= pos['t2']) or (not is_l and live_p <= pos['t2']):
            pos['status'] = 'Target 2 Hit'
        elif ((is_l and live_p >= pos['t1']) or (not is_l and live_p <= pos['t1'])) and not pos.get('t1_hit'):
            pos['t1_hit'] = True; pos['sl'] = pos['entry']

        st.session_state.positions[inst] = pos
        st.markdown(f"""<div class="card-locked">
          <div style="display:flex;justify-content:space-between;"><b style="color:#38bdf8;">📌 ACTIVE TRADE: {pos['label']}</b><span class="ca">Entry ₹{pos['entry']:.2f}</span></div>
          <div class="tile" style="margin-top:4px;"><span class="lbl">LIVE SPOT P&L</span><div class="val {col_p}">{pnl_pts:+.2f} pts</div></div>
          <div style="background:#090e17;border:1px solid #334155;border-radius:8px;padding:8px;margin-top:6px;">
            <div class="rw"><span>🎯 Target 1:</span><b class="cg">₹{pos['t1']:.2f}</b></div>
            <div class="rw"><span>🏁 Target 2:</span><b class="cg">₹{pos['t2']:.2f}</b></div>
            <div class="rw"><span>🛑 Stop Loss:</span><b class="cr">₹{pos['sl']:.2f}</b></div>
          </div>
        </div>""", unsafe_allow_html=True)
        if st.button(f"Square Off {inst}", use_container_width=True):
            st.session_state.positions[inst] = None
            st.rerun()

    else:
        if not is_market_open:
            st.markdown("""<div class="card-no"><b style="color:#fbbf24;">⏳ MARKET CLOSED / PRE-OPEN</b><p style="margin:4px 0 0 0;font-size:0.84rem;color:#cbd5e1;">Live trade setups only trigger during NSE market hours (9:15 AM – 3:30 PM IST). Signals are held to avoid pre-market false prints.</p></div>""", unsafe_allow_html=True)

        elif is_buy:
            entry = round(curr['high'] + max(0.15 * atr_val, 0.5), 2)
            sl = round(max(sup, entry - (1.3 * atr_val)), 2)
            risk = round(max(entry - sl, atr_val * 0.8), 2)
            t1, t2 = round(entry + (1.2 * risk), 2), round(entry + (2.0 * risk), 2)
            strike = int(round(live_p / step_k) * step_k)
            lbl = f"BUY {strike} CE" if not is_stock else f"BUY {inst}"

            st.markdown(f"""<div class="card-buy">
              <div style="display:flex;justify-content:space-between;"><b class="cg" style="font-size:1.1rem;">🟢 CONFLUENCE TRIGGER: {lbl}</b><span class="ca">{b_sc}/{total_pillars} Confluent</span></div>
              <div class="g2">
                <div class="tile"><span class="lbl">ENTRY TRIGGER</span><div class="val cb">Buy Above ₹{entry:.2f}</div></div>
                <div class="tile"><span class="lbl">STOP LOSS</span><div class="val cr">₹{sl:.2f} (-{risk:.2f})</div></div>
              </div>
              <div style="background:#090e17;border:1px solid #334155;border-radius:8px;padding:8px;margin-top:6px;">
                <div class="rw"><span>🎯 Target 1:</span><b class="cg">₹{t1:.2f} (+{t1-entry:.2f} pts)</b></div>
                <div class="rw"><span>🏁 Target 2:</span><b class="cg">₹{t2:.2f} (+{t2-entry:.2f} pts)</b></div>
              </div>
              <div class="reasons"><span>PILLARS:</span><br>• {'<br>• '.join(b_reas)}</div>
            </div>""", unsafe_allow_html=True)
            if st.button(f"⚡ Take & Track {lbl} Call", use_container_width=True, type="primary"):
                st.session_state.positions[inst] = {"direction": "BUY", "label": lbl, "entry": entry, "sl": sl, "t1": t1, "t2": t2, "status": "active", "t1_hit": False}
                st.rerun()

        elif is_sell:
            entry = round(curr['low'] - max(0.15 * atr_val, 0.5), 2)
            sl = round(min(res, entry + (1.3 * atr_val)), 2)
            risk = round(max(sl - entry, atr_val * 0.8), 2)
            t1, t2 = round(entry - (1.2 * risk), 2), round(entry - (2.0 * risk), 2)
            strike = int(round(live_p / step_k) * step_k)
            lbl = f"BUY {strike} PE" if not is_stock else f"SHORT {inst}"

            st.markdown(f"""<div class="card-sell">
              <div style="display:flex;justify-content:space-between;"><b class="cr" style="font-size:1.1rem;">🔴 CONFLUENCE TRIGGER: {lbl}</b><span class="ca">{be_sc}/{total_pillars} Confluent</span></div>
              <div class="g2">
                <div class="tile"><span class="lbl">ENTRY TRIGGER</span><div class="val cb">Sell Below ₹{entry:.2f}</div></div>
                <div class="tile"><span class="lbl">STOP LOSS</span><div class="val cr">₹{sl:.2f} (-{risk:.2f})</div></div>
              </div>
              <div style="background:#090e17;border:1px solid #334155;border-radius:8px;padding:8px;margin-top:6px;">
                <div class="rw"><span>🎯 Target 1:</span><b class="cg">₹{t1:.2f} (+{entry-t1:.2f} pts)</b></div>
                <div class="rw"><span>🏁 Target 2:</span><b class="cg">₹{t2:.2f} (+{entry-t2:.2f} pts)</b></div>
              </div>
              <div class="reasons"><span>PILLARS:</span><br>• {'<br>• '.join(be_reas)}</div>
            </div>""", unsafe_allow_html=True)
            if st.button(f"⚡ Take & Track {lbl} Put", use_container_width=True, type="primary"):
                st.session_state.positions[inst] = {"direction": "SELL", "label": lbl, "entry": entry, "sl": sl, "t1": t1, "t2": t2, "status": "active", "t1_hit": False}
                st.rerun()

        else:
            top_s = max(b_sc, be_sc)
            st.markdown(f"""<div class="card-no">
              <div style="display:flex;justify-content:space-between;"><b style="color:#fbbf24;">⛔ SCANNING FOR CONFLUENCE (NO TRADE)</b><span class="ca">{top_s}/{total_pillars} Pillars</span></div>
              <p style="margin:4px 0 0 0;font-size:0.84rem;color:#cbd5e1;">Consolidating between Support ₹{sup:,.1f} and Resistance ₹{res:,.1f}. Current score is {top_s}/{total_pillars} (Requires ≥ 5 with ADX ≥ 18). No targets or triggers are generated until verified confluence aligns.</p>
            </div>""", unsafe_allow_html=True)
else:
    st.info("Fetching real-time market data... (Ensure the company name selected is listed on NSE)")
