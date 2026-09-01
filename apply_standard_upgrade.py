from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parent
APP,INDEX,CSS=ROOT/'app.js',ROOT/'index.html',ROOT/'styles.css'
if not all(p.exists() for p in (APP,INDEX,CSS)): raise SystemExit('Run from the root of the existing techpulse-news repository.')
backup=ROOT/'.techpulse-standard-backup'; backup.mkdir(exist_ok=True)
for p in (APP,INDEX,CSS): shutil.copy2(p,backup/p.name)
app=APP.read_text(encoding='utf-8'); index=INDEX.read_text(encoding='utf-8'); css=CSS.read_text(encoding='utf-8')

if 'function tpScore(' not in app:
    inject='function sourceQuality(x){const t=String(x.source_type||"secondary").toLowerCase();return t.includes("official")?98:t.includes("primary")?95:t.includes("wire")?94:t.includes("major")?90:82;}\nfunction tpScore(x){return Math.round(Math.max(0,Math.min(100,(+x.importance||0)*.30+(+x.confidence||0)*.25+(+x.freshness||0)*.20+(+x.momentum||0)*.15+sourceQuality(x)*.10)));}\nfunction scoreBand(v){return v>=85?"HIGH IMPACT":v>=70?"SIGNIFICANT":v>=50?"WATCH":"LOW SIGNAL";}\n'
    app=app.replace('function card(x,i=0){',inject+'function card(x,i=0){',1)

app=app.replace('S.a.sort((a,b)=>(b.importance+b.freshness+b.confidence+b.momentum)-(a.importance+a.freshness+a.confidence+a.momentum));','S.a.sort((a,b)=>tpScore(b)-tpScore(a));',1)
if 'class="tp-score"' not in app:
    app=app.replace('<div class="meta"><span>${esc(x.source)} · ${ago(x.published_at)}</span><span class="confidence">${Math.round(x.confidence)}%</span></div>','<div class="meta"><span>${esc(x.source)} · ${ago(x.published_at)}</span><span class="confidence">${Math.round(x.confidence)}%</span></div><div class="tp-score"><span>TP SCORE</span><strong>${tpScore(x)}</strong><em>${scoreBand(tpScore(x))}</em></div>',1)

needle='<div><b>${tr("confidence")}</b>${Math.round(x.confidence)}%</div><div><b>${tr("ranking")}</b>Impact ${Math.round(x.importance)} · Momentum ${Math.round(x.momentum)} · Freshness ${Math.round(x.freshness)}</div></div>'
replacement='<div><b>${tr("confidence")}</b>${Math.round(x.confidence)}%</div><div><b>${tr("ranking")}</b>Impact ${Math.round(x.importance)} · Momentum ${Math.round(x.momentum)} · Freshness ${Math.round(x.freshness)}</div><div><b>TP SCORE</b>${tpScore(x)} · ${scoreBand(tpScore(x))}</div><div><b>SCORE MODEL</b>Importance 30% · Confidence 25% · Freshness 20% · Momentum 15% · Source Quality 10%</div></div>'
app=app.replace(needle,replacement,1)

start=app.find('function policy(k){'); end=app.find('\ndocument.addEventListener',start)
if start>=0 and end>start:
    policy='async function policy(k){const r=await fetch("config/policies.json",{cache:"no-store"});const d=await r.json(),p=d.policies?.[k];if(!p)throw Error("missing policy");$("#modalBody").innerHTML=`<span class="eyebrow">TECHPULSE POLICY</span><h2>${esc(p.title)}</h2>${p.sections.map(s=>`<section class="policy-section"><h3>${esc(s[0])}</h3><p>${esc(s[1])}</p></section>`).join("")}`;show();}'
    app=app[:start]+policy+app[end:]

if 'id="sourceHealth"' not in index:
    footer=index.find('<footer')
    panel='<section class="two standard-panels"><section class="panel"><span class="eyebrow">SOURCE OPERATIONS</span><h3>Source Health</h3><div id="sourceHealth" class="source-health"></div></section><section class="panel"><span class="eyebrow">METHODOLOGY</span><h3>TP Score Methodology</h3><p class="muted">TP Score is a 0–100 prioritization score. It is a ranking signal, not independent fact verification.</p><div class="weights"><span>Importance <b>30%</b></span><span>Confidence <b>25%</b></span><span>Freshness <b>20%</b></span><span>Momentum <b>15%</b></span><span>Source Quality <b>10%</b></span></div></section></section>'
    if footer>=0: index=index[:footer]+panel+index[footer:]

if 'sourceHealth').innerHTML' not in app:
    health='const sg={};S.a.forEach(x=>{const k=x.source||"Unknown";sg[k]??={name:k,count:0,score:0};sg[k].count++;sg[k].score+=tpScore(x)});$("#sourceHealth").innerHTML=Object.values(sg).sort((a,b)=>b.count-a.count).map(s=>`<div class="source-row"><span><i class="dot good"></i>${esc(s.name)}</span><b>${s.count}</b><small>TP avg ${Math.round(s.score/s.count)}</small></div>`).join("")||"<p>No source telemetry.</p>";\n  '
    app=app.replace('const sv=S.a.filter(x=>S.saved.has(x.id));',health+'const sv=S.a.filter(x=>S.saved.has(x.id));',1)

if '.tp-score{' not in css:
    css+='\n.tp-score{display:flex;align-items:center;gap:8px;margin-top:10px}.tp-score span{font-size:9px;letter-spacing:.13em;color:var(--muted);font-weight:800}.tp-score strong{font-size:21px;line-height:1;color:var(--accent)}.tp-score em{font-size:9px;color:var(--muted);font-style:normal}.muted{color:var(--muted)}.weights{display:flex;flex-wrap:wrap;gap:7px;margin-top:14px}.weights span{border:1px solid var(--line);background:var(--panel-2);border-radius:8px;padding:7px 9px;font-size:11px;color:var(--muted)}.weights b{color:var(--text);margin-left:4px}.source-health{display:grid;gap:5px}.source-row{display:grid;grid-template-columns:1fr 35px 80px;align-items:center;gap:8px;border-bottom:1px solid var(--line);padding:8px 0;font-size:12px}.source-row small{color:var(--muted);text-align:right}.dot{display:inline-block;width:7px;height:7px;border-radius:50%;margin-right:7px}.dot.good{background:var(--success)}.policy-section{border-top:1px solid var(--line);padding:12px 0}.policy-section h3{margin:0 0 5px;font-size:14px}.policy-section p{color:var(--muted);margin:0}\n'

APP.write_text(app,encoding='utf-8'); INDEX.write_text(index,encoding='utf-8'); CSS.write_text(css,encoding='utf-8')
print('TechPulse Standard upgrade applied; original UI files are backed up in .techpulse-standard-backup/.')