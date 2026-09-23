import streamlit as st, pandas as pd, numpy as np, yfinance as yf
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
.g4{display:grid;grid-template-columns:repeat(4,1fr);gap:4px;margin-top:4px;}
.tile{background:#090e17;border-radius:8px;padding:8px 10px;border:1px solid #1e293b;}
.lbl{font-size:0.65rem;font-weight:700;color:#94a3b8!important;text-transform:uppercase;}
.val{font-family:monospace;font-size:0.95rem;font-weight:700;}
.cg{color:#10b981!important;}.cr{color:#f43f5e!important;}.cb{color:#38bdf8!important;}.ca{color:#fbbf24!important;}
</style>
<div class="banner">
  <div style="font-size:1.3rem;font-weight:800;">⚡ TradeLense AI Terminal</div>
  <div style="font-size:0.75rem;color:#94a3b8;">Adaptive Confluence Engine (Zero-Volume & Index Safe)</div>
</div>""", unsafe_allow_html=True)

if "positions" not in st.session_state:
    st.session_state.positions = {}

col_tab1, col_tab2 = st.columns([1, 1.2])
asset_tab = col_tab1.radio("Trading Module", ["Option Indices", "Shares"], horizontal=True)

if asset_tab == "Option Indices":
    inst = col_tab2.selectbox("Target Index", ["NIFTY 50", "BANK NIFTY"])
    sym = "^NSEI" if inst == "NIFTY 50" else "^NSEBANK"
    step_k = 50 if inst == "NIFTY 50" else 100
    is_stock = False
else:
    pick = col_tab2.selectbox("Select Share", ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS", "TATAMOTORS.NS", "SBIN.NS"])
    sym, inst = pick, pick.replace(".NS", "")
    step_k = 1
    is_stock = True

c_m1, c_m2 = st.columns([1.2, 1])
timeframe = c_m1.selectbox("Candle Timeframe", ["5m", "15m"], index=0)
auto_on = c_m2.toggle("Auto-refresh", value=True)
if auto_on:
    st_autorefresh(interval=15000, key="desk_refresh_sync")

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

    d = df['close'].diff()
    u = d.clip(lower=0).rolling(14).mean()
    dn = -d.clip(upper=0).rolling(14).mean().replace(0, np.nan)
    df['rsi'] = (100 - (100 / (1 + (u / dn)))).fillna(50)

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

    curr = df.iloc[-2]
    live_p = float(df['close'].iloc[-1])
    day_high, day_low = float(df['high'].tail(50).max()), float(df['low'].tail(50).min())
    atr_val = float(curr['atr']) if curr['atr'] > 0 else live_p * 0.005
    vwap_val = float(curr['vwap'])
    adx_val = float(curr['adx'])
    st.markdown(f"""<div class="tile" style="margin-bottom:8px;">
    <div style="display:flex;justify-content:space-between;"><span class="lbl">{inst} SPOT</span><span class="lbl cb">Timeframe: {timeframe}</span></div>
    <div class="val cb" style="font-size:1.4rem;">₹{live_p:,.2f}</div>
    <div class="g4">
      <div class="tile"><span class="lbl">DAY HIGH</span><div class="val cg">₹{day_high:,.1f}</div></div>
      <div class="tile"><span class="lbl">DAY LOW</span><div class="val cr">₹{day_low:,.1f}</div></div>
      <div class="tile"><span class="lbl">ADX TREND</span><div class="val {'cg' if adx_val>=18 else 'ca'}">{adx_val:.1f}</div></div>
      <div class="tile"><span class="lbl">SESSION VWAP</span><div class="val cb">₹{vwap_val:,.1f}</div></div>
    </div></div>""", unsafe_allow_html=True)

    b_sc, be_sc = 0, 0
    active_pillars = 6

    if curr['ema9'] >= curr['ema21']: b_sc += 1
    else: be_sc += 1

    if curr['close'] >= curr['ema50']: b_sc += 1
    else: be_sc += 1

    if curr['supertrend_dir'] == 1: b_sc += 1
    else: be_sc += 1

    if curr['close'] >= vwap_val: b_sc += 1
    else: be_sc += 1

    if curr['rsi'] >= 50: b_sc += 1
    else: be_sc += 1

    if curr['macd_hist'] >= 0: b_sc += 1
    else: be_sc += 1

    needed = 4
    is_buy = (b_sc >= needed) and (adx_val >= 18)
    is_sell = (be_sc >= needed) and (b_sc < needed) and (adx_val >= 18)

    st.markdown("#### 🎯 Execution Desk")
    pos = st.session_state.positions.get(inst)

    if pos is not None and pos.get('status') == 'active':
        is_l = pos['direction'] == 'BUY'
        pnl = (live_p - pos['entry']) if is_l else (pos['entry'] - live_p)
        col = 'cg' if pnl >= 0 else 'cr'
        st.markdown(f"""<div class="card-locked">
          <div style="display:flex;justify-content:space-between;"><b style="color:#38bdf8;">📌 ACTIVE: {pos['label']}</b><span class="ca">Entry ₹{pos['entry']:.2f}</span></div>
          <div class="tile" style="margin-top:4px;"><span class="lbl">LIVE SPOT P&L</span><div class="val {col}">{pnl:+.2f} pts</div></div>
          <div style="font-size:0.75rem;margin-top:4px;color:#94a3b8;">T1: ₹{pos['t1']:.2f} | T2: ₹{pos['t2']:.2f} | SL: ₹{pos['sl']:.2f}</div>
        </div>""", unsafe_allow_html=True)
        if st.button(f"Square Off {inst}", use_container_width=True):
            st.session_state.positions[inst] = None
            st.rerun()
    else:
        if is_buy:
            entry = round(curr['high'] + 0.5, 2)
            sl = round(entry - (1.4 * atr_val), 2)
            t1, t2 = round(entry + (1.2 * (entry - sl)), 2), round(entry + (2.0 * (entry - sl)), 2)
            lbl = f"BUY {int(round(live_p/step_k)*step_k)} CE" if not is_stock else f"BUY {inst}"
            st.session_state.positions[inst] = {"direction": "BUY", "label": lbl, "entry": entry, "sl": sl, "t1": t1, "t2": t2, "status": "active"}
            st.rerun()
        elif is_sell:
            entry = round(curr['low'] - 0.5, 2)
            sl = round(entry + (1.4 * atr_val), 2)
            t1, t2 = round(entry - (1.2 * (sl - entry)), 2), round(entry - (2.0 * (sl - entry)), 2)
            lbl = f"BUY {int(round(live_p/step_k)*step_k)} PE" if not is_stock else f"SHORT {inst}"
            st.session_state.positions[inst] = {"direction": "SELL", "label": lbl, "entry": entry, "sl": sl, "t1": t1, "t2": t2, "status": "active"}
            st.rerun()
        else:
            top_s = max(b_sc, be_sc)
            st.markdown(f"""<div class="card-no">
              <div style="display:flex;justify-content:space-between;"><b style="color:#fbbf24;">⛔ MARKET CONSOLIDATING / RETRACING</b><span class="ca">{top_s}/{active_pillars} Active Score</span></div>
              <p style="margin:4px 0 0 0;font-size:0.84rem;">RSI ({curr['rsi']:.1f}) and MACD ({curr['macd_hist']:+.2f}) indicate a pullback rather than breakout momentum. Waiting for alignment.</p>
            </div>""", unsafe_allow_html=True)
else:
    st.info("Pulling clean market feed...")
