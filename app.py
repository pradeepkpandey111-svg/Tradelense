import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yfinance as yf
import feedparser

# 1. Page Configuration
st.set_page_config(
    page_title="TradeLense AI Terminal",
    page_icon="⚡",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 2. Modern Cyberpunk Mobile Styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@500;700;800&family=Plus+Jakarta+Sans:wght@500;600;700;800&display=swap');
    html, body, [class*="css"], .stMarkdown {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        background-color: #07090e;
        color: #f1f5f9 !important;
    }
    .block-container {
        padding-top: 2.4rem !important;
        padding-bottom: 2.5rem !important;
        padding-left: 0.7rem !important;
        padding-right: 0.7rem !important;
    }
    .hero-banner {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 14px;
        padding: 12px 14px;
        margin-bottom: 12px;
    }
    .hero-title {
        font-size: 1.35rem !important;
        font-weight: 800;
        color: #ffffff !important;
        margin: 0;
    }
    .call-card {
        background: linear-gradient(145deg, #062b20, #0a3d2e);
        border-radius: 12px;
        padding: 14px;
        border-left: 6px solid #10b981;
        margin-bottom: 12px;
    }
    .put-card {
        background: linear-gradient(145deg, #2d0c13, #45121e);
        border-radius: 12px;
        padding: 14px;
        border-left: 6px solid #f43f5e;
        margin-bottom: 12px;
    }
    .block-card {
        background: linear-gradient(145deg, #241703, #382405);
        border-radius: 12px;
        padding: 14px;
        border-left: 6px solid #f59e0b;
        margin-bottom: 12px;
    }
    .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 8px; }
    .grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 6px; margin-top: 6px; }
    .grid-4 { display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 4px; margin-top: 6px; }

    .tile {
        background: #090e17;
        border-radius: 8px;
        padding: 8px 10px;
        border: 1px solid #1e293b;
    }
    .tile-lbl {
        font-size: 0.65rem;
        font-weight: 700;
        color: #94a3b8 !important;
        text-transform: uppercase;
    }
    .tile-val {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.05rem;
        font-weight: 700;
        margin-top: 2px;
    }
    .c-green { color: #10b981 !important; }
    .c-red { color: #f43f5e !important; }
    .c-blue { color: #38bdf8 !important; }
    .c-amber { color: #fbbf24 !important; }

    .stars-badge {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.95rem;
        color: #fbbf24;
        font-weight: 800;
        letter-spacing: 1.5px;
    }
    .level-row {
        display: flex;
        justify-content: space-between;
        padding: 6px 0;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        font-size: 0.82rem;
        font-family: 'JetBrains Mono', monospace;
        color: #cbd5e1 !important;
    }
    .level-row span { color: #94a3b8 !important; }
    .level-row b { color: #f8fafc !important; }
</style>

<div class="hero-banner">
    <div class="hero-title">⚡ TradeLense AI Terminal</div>
    <div style="font-size:0.75rem; color:#94a3b8; font-weight:600;">Real-Time Global Sentiment & Algorithmic Confluence</div>
</div>
""", unsafe_allow_html=True)

# 3. Control Panel (Instrument Selection + Live Sync)
col_ctrl1, col_ctrl2 = st.columns([1.2, 1])
with col_ctrl1:
    instrument = st.radio("Select Target Index", ["NIFTY 50", "BANK NIFTY"], horizontal=True)
with col_ctrl2:
    data_mode = st.selectbox("Data Source", ["Auto-Fetch Live", "Manual File Upload"])

ticker_sym = "^NSEI" if instrument == "NIFTY 50" else "^NSEBANK"
step_strike = 50 if instrument == "NIFTY 50" else 100
default_lot = 50 if instrument == "NIFTY 50" else 15

# Global Markets & News Feed Helper Functions
@st.cache_data(ttl=300)
def fetch_global_indicators():
    """Fetch live data for US markets, Crude Oil, and India VIX"""
    data = {}
    tickers = {
        "S&P 500": "^GSPC",
        "Nasdaq": "^IXIC",
        "Crude Oil": "CL=F",
        "India VIX": "^INDIAVIX"
    }
    try:
        raw = yf.download(list(tickers.values()), period="2d", interval="1d", progress=False)['Close']
        for name, sym in tickers.items():
            if sym in raw.columns and len(raw[sym].dropna()) >= 2:
                series = raw[sym].dropna()
                pct = ((series.iloc[-1] - series.iloc[-2]) / series.iloc[-2]) * 100
                data[name] = {"val": series.iloc[-1], "pct": pct}
            else:
                data[name] = {"val": 0.0, "pct": 0.0}
    except Exception:
        for name in tickers.keys():
            data[name] = {"val": 0.0, "pct": 0.0}
    return data

@st.cache_data(ttl=600)
def fetch_news_sentiment():
    """Reads latest Indian financial and market news via Google News RSS"""
    feed_url = "https://news.google.com/rss/search?q=Nifty+Indian+stock+market+economy&hl=en-IN&gl=IN&ceid=IN:en"
    feed = feedparser.parse(feed_url)
    bull_words = ['rally', 'gains', 'surge', 'rate cut', 'growth', 'fii buying', 'record high', 'bullish', 'expansion']
    bear_words = ['fall', 'plunge', 'inflation', 'rate hike', 'escalation', 'war', 'fii selling', 'slump', 'bearish', 'deficit']
    
    score = 0
    headlines = []
    for entry in feed.entries[:6]:
        txt = entry.title.lower()
        headlines.append(entry.title)
        for w in bull_words:
            if w in txt: score += 1
        for w in bear_words:
            if w in txt: score -= 1

    sentiment = "Bullish (+)" if score > 1 else ("Bearish (-)" if score < -1 else "Neutral")
    return {"sentiment": sentiment, "score": score, "headlines": headlines[:3]}

# Macro Bar (Global Markets)
globals_data = fetch_global_indicators()
news_info = fetch_news_sentiment()

st.markdown(f"""
<div class="tile" style="margin-bottom:10px;">
    <div style="display:flex; justify-content:space-between; align-items:center;">
        <span class="tile-lbl">🌐 GLOBAL MACRO PULSE & SENTIMENT</span>
        <span class="tile-lbl" style="color:#fbbf24 !important;">NEWS: {news_info['sentiment']}</span>
    </div>
    <div class="grid-4" style="margin-top:6px;">
        <div class="tile">
            <span class="tile-lbl">S&P 500</span>
            <div class="tile-val {'c-green' if globals_data['S&P 500']['pct'] >= 0 else 'c-red'}" style="font-size:0.85rem;">
                {globals_data['S&P 500']['pct']:+.2f}%
            </div>
        </div>
        <div class="tile">
            <span class="tile-lbl">NASDAQ</span>
            <div class="tile-val {'c-green' if globals_data['Nasdaq']['pct'] >= 0 else 'c-red'}" style="font-size:0.85rem;">
                {globals_data['Nasdaq']['pct']:+.2f}%
            </div>
        </div>
        <div class="tile">
            <span class="tile-lbl">BRENT CRUDE</span>
            <div class="tile-val {'c-red' if globals_data['Crude Oil']['pct'] > 0 else 'c-green'}" style="font-size:0.85rem;">
                {globals_data['Crude Oil']['pct']:+.2f}%
            </div>
        </div>
        <div class="tile">
            <span class="tile-lbl">INDIA VIX</span>
            <div class="tile-val c-amber" style="font-size:0.85rem;">
                {globals_data['India VIX']['val']:.2f}
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Data Ingestion
df = None
if data_mode == "Auto-Fetch Live":
    with st.spinner(f"Fetching latest intraday {instrument} candles..."):
        try:
            raw_live = yf.download(ticker_sym, period="5d", interval="5m", progress=False)
            if len(raw_live) > 20:
                raw_live = raw_live.reset_index()
                # Clean MultiIndex headers if present
                if isinstance(raw_live.columns, pd.MultiIndex):
                    raw_live.columns = [c[0].lower() for c in raw_live.columns]
                else:
                    raw_live.columns = [c.lower() for c in raw_live.columns]
                
                time_col = next((c for c in raw_live.columns if 'time' in c or 'date' in c), raw_live.columns[0])
                raw_live['time'] = pd.to_datetime(raw_live[time_col])
                df = raw_live.sort_values('time').reset_index(drop=True)
            else:
                st.error("Market closed or feed delayed. You can switch to 'Manual File Upload'.")
        except Exception as e:
            st.error(f"Live fetch error: {e}")
else:
    with st.expander("📂 Upload Custom CSV / Option Chain", expanded=True):
        up_file = st.file_uploader(f"Upload {instrument} History (CSV)", key="cust_hist")
        if up_file:
            df = pd.read_csv(up_file)
            df.columns = [str(c).strip().lower() for c in df.columns]
            t = next((c for c in df.columns if 'time' in c or 'date' in c), df.columns[0])
            df['time'] = pd.to_datetime(df[t], errors='coerce')
            df = df.dropna(subset=['time']).sort_values('time').reset_index(drop=True)

# Calculation Engine
def compute_indicators(d):
    d['ema9'] = d['close'].ewm(span=9, adjust=False).mean()
    d['ema21'] = d['close'].ewm(span=21, adjust=False).mean()
    d['ema50'] = d['close'].ewm(span=50, adjust=False).mean()
    chg = d['close'].diff()
    gain = chg.clip(lower=0).rolling(14).mean()
    loss = (-chg.clip(upper=0)).rolling(14).mean().replace(0, np.nan)
    d['rsi'] = (100 - (100 / (1 + (gain / loss)))).fillna(50)
    tr = pd.concat([d['high'] - d['low'], (d['high'] - d['close'].shift()).abs(), (d['low'] - d['close'].shift()).abs()], axis=1).max(axis=1)
    d['atr'] = tr.rolling(14).mean().bfill()
    return d

def star_icons(n):
    return "★" * n + "☆" * (5 - n)

if df is not None and len(df) > 20:
    for col in ['open', 'high', 'low', 'close']:
        df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce')

    df = compute_indicators(df)
    curr, prev = df.iloc[-1], df.iloc[-2]
    p = curr['close']
    atr = curr['atr'] if pd.notna(curr['atr']) and curr['atr'] > 0 else (p * 0.005)
    rsi = curr['rsi']

    # Pivot Point Calculation
    piv = (prev['high'] + prev['low'] + prev['close']) / 3
    r1 = (2 * piv) - prev['low']
    s1 = (2 * piv) - prev['high']
    strike = int(round(p / step_strike) * step_strike)

    # 5-Factor Score (EMAs, Macro 50, RSI, Breakout, Global/News)
    bull_stars = 0
    bear_stars = 0
    b_reasons, be_reasons = [], []

    # 1. Fast Trend (EMA 9/21)
    if curr['ema9'] > curr['ema21']:
        bull_stars += 1
        b_reasons.append("EMA 9 > EMA 21 (Bullish)")
    else:
        bear_stars += 1
        be_reasons.append("EMA 9 < EMA 21 (Bearish)")

    # 2. Trend Backbone (EMA 50)
    if p >= curr['ema50']:
        bull_stars += 1
        b_reasons.append("Above 50 EMA (Macro Uptrend)")
    else:
        bear_stars += 1
        be_reasons.append("Below 50 EMA (Macro Downtrend)")

    # 3. Momentum (RSI 14)
    if 52 <= rsi <= 72:
        bull_stars += 1
        b_reasons.append(f"RSI ({rsi:.1f}) in Bullish Acceleration")
    elif 28 <= rsi <= 48:
        bear_stars += 1
        be_reasons.append(f"RSI ({rsi:.1f}) in Bearish Breakdown")

    # 4. Candle Structure
    if curr['close'] > prev['high']:
        bull_stars += 1
        b_reasons.append("Candle closed above previous high")
    elif curr['close'] < prev['low']:
        bear_stars += 1
        be_reasons.append("Candle closed below previous low")

    # 5. Global & News Factor
    global_green = (globals_data['S&P 500']['pct'] > 0 and globals_data['Crude Oil']['pct'] < 1.0)
    if global_green and news_info['score'] >= 0:
        bull_stars += 1
        b_reasons.append("Global Markets & Macro News Tailwinds (+)")
    elif not global_green and news_info['score'] <= 0:
        bear_stars += 1
        be_reasons.append("Global Markets & Macro Headwinds (-)")

    # Status Display Bar
    st.markdown(f"""
    <div class="tile" style="margin-bottom:12px;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div>
                <span class="tile-lbl">{instrument} SPOT (LTP)</span>
                <div class="tile-val c-blue">{p:.2f}</div>
            </div>
            <div style="text-align:right;">
                <span class="tile-lbl">PIVOT POINT</span>
                <div class="tile-val c-amber">{piv:.0f}</div>
            </div>
        </div>
        <div class="grid-2" style="margin-top:6px;">
            <div class="tile"><span class="tile-lbl">SUPPORT (S1)</span><div class="tile-val c-green">{s1:.0f}</div></div>
            <div class="tile"><span class="tile-lbl">RESISTANCE (R1)</span><div class="tile-val c-red">{r1:.0f}</div></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Signal Evaluation
    has_buy_call = bull_stars >= 3
    has_buy_put = bear_stars >= 3 and not has_buy_call

    st.markdown("#### 🎯 Execution Setups")

    if not has_buy_call and not has_buy_put:
        best_s = max(bull_stars, bear_stars)
        st.markdown(f"""
        <div class="block-card">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <b style="color:#fbbf24; font-size:0.98rem;">⛔ NO TRADE ZONE: CHOPPY / NEUTRAL</b>
                <span class="stars-badge">{star_icons(best_s)} ({best_s}/5)</span>
            </div>
            <p style="margin:6px 0 0 0; color:#cbd5e1; font-size:0.82rem;">
                Confluence score is only <b>{best_s}/5 stars</b>. Market is rangebound between <b>{s1:.0f}</b> and <b>{r1:.0f}</b>. Capital protection active.
            </p>
        </div>
        """, unsafe_allow_html=True)
    elif has_buy_call:
        sl = round(max(s1, p - (1.2 * atr)), 1)
        risk = round(max(p - sl, atr * 0.8), 1)
        t1 = round(p + risk, 1)
        t2 = round(p + (risk * 2.0), 1)
        t3 = round(p + (risk * 3.0), 1)

        st.markdown(f"""
        <div class="call-card">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <b style="color:#10b981; font-size:1.05rem;">🟢 BUY {strike} CE</b>
                <span class="stars-badge">{star_icons(bull_stars)} ({bull_stars}/5)</span>
            </div>
            <div class="grid-2">
                <div class="tile"><span class="tile-lbl">INDEX ENTRY</span><div class="tile-val c-blue">{p:.1f}</div></div>
                <div class="tile"><span class="tile-lbl">STRICT SL</span><div class="tile-val c-red">{sl:.1f}</div></div>
                <div class="tile"><span class="tile-lbl">TARGET 1</span><div class="tile-val c-green">{t1:.1f}</div></div>
                <div class="tile"><span class="tile-lbl">TARGET 2 (2x R:R)</span><div class="tile-val c-green">{t2:.1f}</div></div>
            </div>
            <div style="margin-top:8px;">
                <div class="level-row"><span>Target 3 (Extension):</span><b>{t3:.1f}</b></div>
                <div class="level-row"><span>Max Risk ({default_lot} Qty):</span><b class="c-red">-₹{risk * default_lot:,.0f} ({risk} pts)</b></div>
                <div class="level-row"><span>Est. Gain at T2:</span><b class="c-green">+₹{risk * 2 * default_lot:,.0f} (+{risk * 2:.1f} pts)</b></div>
            </div>
            <div style="margin-top:8px; padding-top:6px; border-top:1px solid #10b98133;">
                <span class="tile-lbl">SUPPORTING PILLARS:</span>
                <ul style="margin:4px 0 0 16px; padding:0; color:#cbd5e1; font-size:0.78rem;">
                    {"".join([f"<li>{r}</li>" for r in b_reasons])}
                </ul>
            </div>
        </div>
        """, unsafe_allow_html=True)
    elif has_buy_put:
        sl = round(min(r1, p + (1.2 * atr)), 1)
        risk = round(max(sl - p, atr * 0.8), 1)
        t1 = round(p - risk, 1)
        t2 = round(p - (risk * 2.0), 1)
        t3 = round(p - (risk * 3.0), 1)

        st.markdown(f"""
        <div class="put-card">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <b style="color:#f43f5e; font-size:1.05rem;">🔴 BUY {strike} PE</b>
                <span class="stars-badge">{star_icons(bear_stars)} ({bear_stars}/5)</span>
            </div>
            <div class="grid-2">
                <div class="tile"><span class="tile-lbl">INDEX ENTRY</span><div class="tile-val c-blue">{p:.1f}</div></div>
                <div class="tile"><span class="tile-lbl">STRICT SL</span><div class="tile-val c-red">{sl:.1f}</div></div>
                <div class="tile"><span class="tile-lbl">TARGET 1</span><div class="tile-val c-green">{t1:.1f}</div></div>
                <div class="tile"><span class="tile-lbl">TARGET 2 (2x R:R)</span><div class="tile-val c-green">{t2:.1f}</div></div>
            </div>
            <div style="margin-top:8px;">
                <div class="level-row"><span>Target 3 (Extension):</span><b>{t3:.1f}</b></div>
                <div class="level-row"><span>Max Risk ({default_lot} Qty):</span><b class="c-red">-₹{risk * default_lot:,.0f} ({risk} pts)</b></div>
                <div class="level-row"><span>Est. Gain at T2:</span><b class="c-green">+₹{risk * 2 * default_lot:,.0f} (+{risk * 2:.1f} pts)</b></div>
            </div>
            <div style="margin-top:8px; padding-top:6px; border-top:1px solid #f43f5e33;">
                <span class="tile-lbl">SUPPORTING PILLARS:</span>
                <ul style="margin:4px 0 0 16px; padding:0; color:#cbd5e1; font-size:0.78rem;">
                    {"".join([f"<li>{r}</li>" for r in be_reasons])}
                </ul>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Interactive Chart Panel
    st.markdown("#### 📈 Candlestick & Indicator Chart")
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.72, 0.28])
    sub = df.tail(45)
    fig.add_trace(go.Candlestick(x=sub['time'], open=sub['open'], high=sub['high'], low=sub['low'], close=sub['close'], increasing_line_color='#10b981', decreasing_line_color='#f43f5e', name="Price"), row=1, col=1)
    fig.add_trace(go.Scatter(x=sub['time'], y=sub['ema9'], line=dict(color='#38bdf8', width=1.5), name="EMA 9"), row=1, col=1)
    fig.add_trace(go.Scatter(x=sub['time'], y=sub['ema21'], line=dict(color='#f59e0b', width=1.5), name="EMA 21"), row=1, col=1)
    fig.add_hline(y=s1, line_dash="dash", line_color="#10b981", annotation_text=f"S1 {s1:.0f}", row=1, col=1)
    fig.add_hline(y=r1, line_dash="dash", line_color="#f43f5e", annotation_text=f"R1 {r1:.0f}", row=1, col=1)
    fig.add_trace(go.Scatter(x=sub['time'], y=sub['rsi'], line=dict(color='#c084fc', width=1.5), name="RSI"), row=2, col=1)
    fig.add_hline(y=70, line_dash="dot", line_color="#f43f5e", row=2, col=1)
    fig.add_hline(y=30, line_dash="dot", line_color="#10b981", row=2, col=1)
    fig.update_layout(height=430, margin=dict(l=5, r=5, t=10, b=10), xaxis_rangeslider_visible=False, template="plotly_dark", paper_bgcolor="#07090e", plot_bgcolor="#07090e", showlegend=False)
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    # Recent Breaking Headlines
    with st.expander("📰 Live Breaking News Headlines"):
        for h in news_info['headlines']:
            st.markdown(f"• {h}")
else:
    st.info("Select 'Auto-Fetch Live' or upload a history file to view execution setups.")
    
