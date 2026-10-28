// web_dashboard.h -- the live soil-moisture page served by the ESP32's own
// Wi-Fi access point (http://192.168.4.1). Self-contained: phones on the
// ESP32's network have no internet, so no external fonts or scripts.
// Read-only: the page cannot water, switch relays or change settings.
#pragma once
#include <pgmspace.h>

static const char DASHBOARD_HTML[] PROGMEM = R"HTML(<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AgriSentry Live</title>
<style>
:root{--bg:#f4f5f2;--card:#fff;--ink:#1d2b2e;--ink2:#5d6870;--line:#dfe2df;
--low:#cc7722;--opt:#109e92;--high:#3d5bd9;--ok:#2e9e5b;--warn:#c9821c;--bad:#c94a3a;--hl:#ffe9a8}
@media (prefers-color-scheme:dark){:root{--bg:#121617;--card:#1c2224;--ink:#e8ecea;--ink2:#9aa5a8;
--line:#2c3437;--hl:#5a4a12}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.4 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
header{padding:16px 16px 8px}
h1{font-size:20px;margin:0 0 2px}
.sub{color:var(--ink2);font-size:13px}
.chips{display:flex;flex-wrap:wrap;gap:6px;padding:0 16px 10px}
.chip{background:var(--card);border:1px solid var(--line);border-radius:999px;padding:4px 10px;font-size:13px;white-space:nowrap}
.dot{display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--bad);margin-right:6px;vertical-align:1px}
.dot.on{background:var(--ok)}
.bar{display:flex;gap:8px;padding:0 16px 10px;flex-wrap:wrap}
button{font:inherit;font-size:13px;background:var(--card);color:var(--ink);border:1px solid var(--line);border-radius:8px;padding:6px 10px}
button.on{border-color:var(--ink)}
.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;padding:0 16px}
.tile{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:10px;position:relative;transition:background .3s}
.tile.hl{background:var(--hl);border-color:var(--warn)}
.tile .id{font-weight:700;font-size:15px}
.tile .grp{font-size:11px;color:var(--ink2)}
.tile .pct{font-size:28px;font-weight:700;font-variant-numeric:tabular-nums;margin:2px 0}
.tile .pct small{font-size:14px;font-weight:600}
.meter{position:relative;height:8px;border-radius:4px;background:var(--line);overflow:hidden}
.meter .band{position:absolute;top:0;bottom:0;opacity:.35}
.meter .val{position:absolute;top:-2px;width:3px;height:12px;background:var(--ink)}
.st{font-size:12px;margin-top:4px}
.st.in{color:var(--ok)}.st.lo{color:var(--warn)}.st.hi{color:var(--high)}.st.bad{color:var(--bad)}
.meta{font-size:11px;color:var(--ink2);margin-top:4px;font-variant-numeric:tabular-nums}
svg.spark{display:block;width:100%;height:26px;margin-top:4px}
.flag{position:absolute;top:8px;right:8px;font-size:11px;font-weight:700;color:var(--warn)}
.help{margin:12px 16px;padding:10px 12px;background:var(--card);border:1px solid var(--line);border-radius:10px;font-size:13px;color:var(--ink2)}
.help b{color:var(--ink)}
footer{padding:4px 16px 24px;font-size:12px;color:var(--ink2)}
@media (max-width:420px){.tile{padding:8px}.tile .pct{font-size:22px}.grid{gap:6px}}
</style></head><body>
<header><h1>AgriSentry · live soil moisture</h1>
<div class="sub">Fresh probe readings every 2 s, straight from the ESP32</div></header>
<div class="chips">
<span class="chip"><span class="dot" id="dot"></span><span id="conn">connecting…</span></span>
<span class="chip" id="mode">mode –</span>
<span class="chip" id="temp">enclosure –</span>
<span class="chip" id="clock">clock –</span>
</div>
<div class="bar">
<button id="lay" class="on">Camera view</button>
<button id="rot">Rotate 180°</button>
<button id="raw">Show raw ADC</button>
</div>
<div class="grid" id="grid"></div>
<div class="help"><b>Finding a probe:</b> pull one probe into the air (or squeeze the soil around it). The tile whose reading jumps lights up yellow — that is the pot number the ESP32 thinks that probe belongs to. Push it back in the same spot afterwards.</div>
<footer><span id="foot"></span><br>Moisture %: 0 = oven-dried soil, 100 = saturated (two-point scale). The 15-min value is what the watering logic uses.</footer>
<script>
const CAM=[3,2,1,6,5,4,9,8,7], NUM=[1,2,3,4,5,6,7,8,9];
const COL={A_Low:'var(--low)',B_Optimal:'var(--opt)',C_High:'var(--high)'};
const NAME={A_Low:'Low',B_Optimal:'Optimal',C_High:'High'};
let st={cam:true,rot:false,raw:false}; try{Object.assign(st,JSON.parse(localStorage.getItem('as_view')||'{}'))}catch(e){}
const hist={}; let last=null, fails=0;
function save(){try{localStorage.setItem('as_view',JSON.stringify(st))}catch(e){}}
function order(){let o=st.cam?CAM.slice():NUM.slice(); if(st.rot)o.reverse(); return o}
function btns(){lay.className=st.cam?'on':''; lay.textContent=st.cam?'Camera view':'Number order';
 rot.className=st.rot?'on':''; raw.className=st.raw?'on':''}
lay.onclick=()=>{st.cam=!st.cam;save();btns();draw()}; rot.onclick=()=>{st.rot=!st.rot;save();btns();draw()};
raw.onclick=()=>{st.raw=!st.raw;save();btns();draw()};
function spark(a){ if(a.length<2)return''; const w=100,h=26,mn=Math.min(...a)-1,mx=Math.max(...a)+1;
 const p=a.map((v,i)=>(i*w/(a.length-1)).toFixed(1)+','+(h-(v-mn)/(mx-mn)*h).toFixed(1)).join(' ');
 return `<svg class="spark" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none"><polyline points="${p}" fill="none" stroke="currentColor" stroke-width="1.5" vector-effect="non-scaling-stroke"/></svg>`}
function draw(){ if(!last)return; const now=Date.now();
 let best=null,bestD=0;
 last.pots.forEach(p=>{const h=hist[p.id]||[]; const old=h.find(x=>now-x.t<=8000); if(old){const d=Math.abs(p.raw-old.raw); if(d>bestD){bestD=d;best=p.id}}});
 if(bestD<80)best=null;
 grid.innerHTML=order().map(n=>{const p=last.pots[n-1]; const c=COL[p.grp]||'var(--ink2)';
  const bad=p.pct<0, v=bad?0:p.pct; let cls='in',txt='in band';
  if(p.q){cls='bad';txt='quarantined (sensor fault)'} else if(bad){cls='bad';txt='sensor out of range'}
  else if(v<p.lo){cls='lo';txt='below band → will water'} else if(v>p.hi){cls='hi';txt='above band'}
  const h=(hist[p.id]||[]).map(x=>st.raw?x.raw:x.pct);
  const big=st.raw?`${p.raw}<small> ADC</small>`:(bad?'—':`${v.toFixed(1)}<small>%</small>`);
  return `<div class="tile${best===p.id?' hl':''}">${best===p.id?'<span class="flag">changing</span>':''}
  <div class="id" style="color:${c}">${p.id}</div><div class="grp">${last.germ?'Germination':NAME[p.grp]} · band ${p.lo}–${p.hi}%</div>
  <div class="pct">${big}</div>
  <div class="meter"><div class="band" style="left:${p.lo}%;width:${p.hi-p.lo}%;background:${c}"></div><div class="val" style="left:calc(${v}% - 1px)"></div></div>
  <div class="st ${cls}">${txt}</div>
  <div style="color:${c}">${spark(h)}</div>
  <div class="meta">raw ${p.raw} · ch ${p.ch} · 15-min ${p.logged<0?'—':p.logged.toFixed(1)+'%'}<br>watered ${p.n}×</div></div>`}).join('');
}
async function tick(){
 try{ const r=await fetch('/api',{cache:'no-store'}); const j=await r.json(); last=j; fails=0; const now=Date.now();
  j.pots.forEach(p=>{const h=hist[p.id]=hist[p.id]||[]; h.push({t:now,pct:p.pct<0?0:p.pct,raw:p.raw}); while(h.length&&now-h[0].t>120000)h.shift()});
  dot.className='dot on'; conn.textContent='live · '+(j.age_ms/1000).toFixed(1)+' s old';
  mode.textContent=j.irrigating?'WATERING NOW':(j.germ?'Germination mode (all pots 50–60%)':'Treatment bands');
  temp.textContent=j.bmp?('enclosure '+j.temp.toFixed(1)+' °C'):'enclosure sensor offline';
  clock.textContent=j.synced?new Date(j.t*1000).toLocaleTimeString():'clock not synced';
  foot.textContent='ESP32 up '+Math.floor(j.up/3600)+' h '+Math.floor(j.up%3600/60)+' min';
  draw();
 }catch(e){ if(++fails>2){dot.className='dot';conn.textContent='no connection — are you on the AgriSentry Wi-Fi?'} }
 setTimeout(tick,2000);
}
btns(); tick();
</script></body></html>)HTML";
