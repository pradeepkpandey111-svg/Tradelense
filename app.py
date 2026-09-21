import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="TradeLense AI",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Remove Streamlit default whitespace & top bars
st.markdown("""
<style>
    #MainMenu, footer, header {visibility: hidden;}
    .block-container {padding: 0 !important; max-width: 100% !important;}
</style>
""", unsafe_allow_html=True)

# Embedded Single-File HTML Template
dashboard_html = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TradeLense AI</title>
<style>
*{box-sizing:border-box}
body{margin:0;font-family:Inter,Segoe UI,Arial,sans-serif;background:#07111f;color:#e8eef7}
header{height:60px;border-bottom:1px solid #1c2b40;display:flex;align-items:center;justify-content:space-between;padding:0 16px;background:#0a1626;position:sticky;top:0;z-index:5}
.logo{font-weight:800;font-size:19px}.logo span{color:#6ee7b7}
.actions{display:flex;gap:8px;align-items:center}
.pill,.btn{border:1px solid #263a53;background:#0e1d30;color:#dce8f5;border-radius:8px;padding:7px 11px;font-size:12px;font-weight:600}
.btn.primary{background:#176b52;border-color:#239b73;color:white}
main{padding:14px;max-width:1400px;margin:auto}
.top{display:grid;grid-template-columns:1fr;gap:12px;margin-bottom:14px}
@media(min-width:768px){.top{grid-template-columns:1.2fr 2fr 1fr}}
.card{background:#0c1929;border:1px solid #1c2d43;border-radius:12px;padding:14px;box-shadow:0 6px 20px rgba(0,0,0,0.25)}
.price{font-size:26px;font-weight:800;margin-top:4px}
.muted{color:#8ea1b8;font-size:12px}.green{color:#63e6a9}.red{color:#ff7f8b}.yellow{color:#ffd166}
.grid{display:grid;grid-template-columns:1fr;gap:14px}
@media(min-width:992px){.grid{grid-template-columns:2fr 1fr}}
.chartbox{height:280px;position:relative;margin-top:8px}
canvas{width:100%;height:100%;display:block}
.metrics{display:grid;grid-template-columns:repeat(2,1fr);gap:8px;margin-top:10px}
@media(min-width:600px){.metrics{grid-template-columns:repeat(4,1fr)}}
.metric{background:#091522;border-radius:8px;padding:10px}
.metric b{display:block;margin-top:4px}
.setup{border:1px solid #245e4d;background:#0a211d;border-radius:10px;padding:12px;margin-top:12px}
.levels{display:grid;grid-template-columns:repeat(2,1fr);gap:8px}
@media(min-width:600px){.levels{grid-template-columns:repeat(4,1fr)}}
.level{background:#071a18;padding:9px;border-radius:8px}
.level b{display:block;margin-top:3px}
.signal{display:flex;justify-content:space-between;align-items:center;padding:9px 0;border-bottom:1px solid #1b2a3e;font-size:13px}
.badge{padding:4px 8px;border-radius:6px;font-size:11px;background:#153e32;color:#6ee7b7;font-weight:700}
table{width:100%;border-collapse:collapse;font-size:12px;margin-top:6px}
th,td{text-align:left;padding:8px;border-bottom:1px solid #1b2a3e}
th{color:#91a3b9}
</style>
</head>
<body>
<header>
  <div class="logo">Trade<span>Lense</span> AI</div>
  <div class="actions">
    <span class="pill">● 5m Active</span>
    <button class="btn" onclick="alert('Broker API Linked')">Zerodha Kite</button>
  </div>
</header>

<main>
  <section class="top">
    <div class="card">
      <div class="muted">Underlying Asset</div>
      <div style="font-weight:700;font-size:15px;margin-top:3px">NIFTY 50 INDICES</div>
      <div class="price">25,620.40</div>
      <div class="green">+118.20 (+0.46%)</div>
      <div class="muted" style="margin-top:6px">5-Minute Timeframe • MIS Mode</div>
    </div>
    <div class="card">
      <div class="muted">Strategy Signal State</div>
      <h3 style="margin:4px 0" class="green">Nifty 50 CE Setup Confirmed</h3>
      <p class="muted" style="margin:0">5-Factor Confluence: EMA 9 > 21, Price > 50 EMA, RSI 52–72, and Previous High breakout.</p>
    </div>
    <div class="card">
      <div class="muted">Factor Alignment</div>
      <div class="price">5 / 5</div>
      <div class="green">High Probability Setup</div>
      <div class="muted" style="margin-top:6px">1 Lot = 65 Qty</div>
    </div>
  </section>

  <section class="grid">
    <div>
      <div class="card">
        <div style="display:flex;justify-content:space-between;align-items:center">
          <span class="muted">5-Minute Price Action</span>
          <span class="muted">Auto Exit: <b>15:15 IST</b></span>
        </div>
        <div class="chartbox"><canvas id="chart"></canvas></div>

        <div class="metrics">
          <div class="metric"><span class="muted">EMA 9 / 21</span><b class="green">Bullish (9 > 21)</b></div>
          <div class="metric"><span class="muted">50 EMA Trend</span><b class="green">Above Filter</b></div>
          <div class="metric"><span class="muted">RSI (14)</span><b>62.4</b></div>
          <div class="metric"><span class="muted">Breakout</span><b class="green">Trigger Met</b></div>
        </div>

        <div class="setup">
          <h4 style="margin:0 0 8px">⚡ Active Contract: NIFTY 25650 CE (ATM)</h4>
          <div class="levels">
            <div class="level"><span class="muted">LTP Entry</span><b>₹88.05</b></div>
            <div class="level"><span class="muted">Stop Loss (-15%)</span><b class="red">₹74.85</b></div>
            <div class="level"><span class="muted">Target (+30%)</span><b class="green">₹114.45</b></div>
            <div class="level"><span class="muted">Trailing SL</span><b>15% Step</b></div>
          </div>
          <div class="metrics">
            <div class="metric"><span class="muted">Capital / Lot</span><b>₹5,723.25</b></div>
            <div class="metric"><span class="muted">Max Risk (15%)</span><b class="red">-₹858.00</b></div>
            <div class="metric"><span class="muted">Target Gain (30%)</span><b class="green">+₹1,716.00</b></div>
            <div class="metric"><span class="muted">Risk/Reward</span><b>1 : 2.0</b></div>
          </div>
        </div>
      </div>
    </div>

    <aside>
      <div class="card">
        <h4 style="margin:0 0 6px">5-Factor Condition Checks</h4>
        <div class="signal"><span>1. EMA 9 > EMA 21</span><span class="badge">PASS</span></div>
        <div class="signal"><span>2. Price > EMA 50</span><span class="badge">PASS</span></div>
        <div class="signal"><span>3. RSI (52 - 72 Zone)</span><span class="badge">PASS</span></div>
        <div class="signal"><span>4. Close > Prev High</span><span class="badge">PASS</span></div>
        <div class="signal"><span>5. Time < 15:15 IST</span><span class="badge">PASS</span></div>
      </div>

      <div class="card" style="margin-top:12px">
        <h4 style="margin:0 0 6px">Execution Rules Attached</h4>
        <table>
          <tbody>
            <tr><td>Mode</td><td><b>Notification MIS</b></td></tr>
            <tr><td>Execution Type</td><td><b>Underlying ATM</b></td></tr>
            <tr><td>Trailing Mode</td><td><b>15% Step Trail</b></td></tr>
            <tr><td>End of Day</td><td><b>15:15 Auto Square-off</b></td></tr>
          </tbody>
        </table>
      </div>
    </aside>
  </section>
</main>

<script>
const canvas=document.getElementById('chart'),ctx=canvas.getContext('2d');
function draw(){
  const dpr=window.devicePixelRatio||1,w=canvas.clientWidth,h=canvas.clientHeight;
  canvas.width=w*dpr;canvas.height=h*dpr;ctx.setTransform(dpr,0,0,dpr,0,0);
  ctx.clearRect(0,0,w,h);
  const pad={l:35,r:15,t:15,b:25},cw=w-pad.l-pad.r,ch=h-pad.t-pad.b;
  ctx.strokeStyle='#1b2a3e';ctx.lineWidth=1;
  for(let i=0;i<4;i++){let y=pad.t+i*ch/3;ctx.beginPath();ctx.moveTo(pad.l,y);ctx.lineTo(w-pad.r,y);ctx.stroke()}
  let pts=[25520, 25540, 25530, 25575, 25560, 25590, 25585, 25610, 25620];
  let min=25500,max=25640;
  const y=v=>pad.t+(max-v)/(max-min)*ch,x=i=>pad.l+i*(cw/(pts.length-1));
  ctx.strokeStyle='#239b73';ctx.lineWidth=2;ctx.beginPath();
  pts.forEach((p,i)=>{let xx=x(i),yy=y(p);if(i===0)ctx.moveTo(xx,yy);else ctx.lineTo(xx,yy)});
  ctx.stroke();
  pts.forEach((p,i)=>{let xx=x(i),yy=y(p);ctx.fillStyle=i===pts.length-1?'#6ee7b7':'#239b73';ctx.beginPath();ctx.arc(xx,yy,3.5,0,Math.PI*2);ctx.fill()});
}
window.addEventListener('resize',draw);draw();
</script>
</body>
</html>
"""

components.html(dashboard_html, height=1100, scrolling=True)
