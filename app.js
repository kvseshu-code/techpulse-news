(()=>{"use strict";
const S={
 a:[], saved:new Set(JSON.parse(localStorage.tp_saved||"[]")),
 theme:localStorage.tp_theme||"dark", font:+localStorage.tp_font||15,
 reduced:localStorage.tp_motion==="reduced", language:localStorage.tp_lang||"en",
 briefIndex:0, briefItems:[], speaking:false
};
const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
const esc=x=>String(x??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const url=x=>{try{const u=new URL(x,location.href);return["http:","https:"].includes(u.protocol)?u.href:"#"}catch{return"#"}};
const ago=x=>{const t=Date.parse(x);if(!isFinite(t))return"—";const m=Math.max(0,Math.floor((Date.now()-t)/6e4));return m<60?m+"m ago":m<1440?Math.floor(m/60)+"h ago":Math.floor(m/1440)+"d ago"};
const n=(x,i)=>({id:String(x.id||x.story_id||"TP-"+i),title:x.title||"Untitled",summary:x.summary||x.description||"",
why:x.why_it_matters||x.why||"Review the available evidence and original reporting.",changes:x.what_changes||x.changes||"No additional confirmed change is supplied.",
next:x.whats_next||x.next||"Watch for verified follow-up developments.",category:String(x.category||"Technology"),
published_at:x.published_at||x.timestamp||"",source:x.source||x.publisher||"Source",source_type:x.source_type||"secondary",
url:url(x.url||x.source_url||"#"),confidence:+x.confidence||70,importance:+x.importance||60,freshness:+x.freshness||60,momentum:+x.momentum||50,
verification_status:String(x.verification_status||x.verification||"DEVELOPING").toUpperCase(),status:String(x.status||"NEW").toUpperCase(),
tags:Array.isArray(x.tags)?x.tags:[],corroborating_sources:Array.isArray(x.corroborating_sources)?x.corroborating_sources:[]});

const T={
en:{skip:"Skip to content",brandSubtitle:"INTELLIGENCE CONSOLE",language:"Language",navOverview:"Overview",navTechnology:"Technology",navGaming:"Gaming",navCybersecurity:"Cybersecurity",navAI:"AI",navTrending:"Trending",navSaved:"Saved",navBrief:"Daily Brief",
liveIntelligence:"LIVE INTELLIGENCE",heroTitle:"Discover.<br>Rank.<br>Understand.",heroText:"An original technology intelligence layer that organizes, ranks and explains developments while directing you to the original reporting.",
startBrief:"Start Intelligence Brief",stories:"stories",sources:"sources",updated:"updated",priority:"PRIORITY INTELLIGENCE",top10:"Top 10",searchPlaceholder:"Search intelligence…",radar:"Technology Radar",developing:"Developing Stories",
technologyIntelligence:"Technology Intelligence",gamingIntelligence:"Gaming Intelligence",cybersecurityIntelligence:"Cybersecurity Intelligence",aiIntelligence:"AI Intelligence",trendingNow:"Trending Now",savedIntelligence:"Saved Intelligence",dailyTitle:"TechPulse Daily",playBrief:"Play briefing",
footerText:"Original summaries · source transparency · no account required",listen:"Listen",save:"Save",saved:"Saved",intelligence:"Intelligence",noStories:"No stories available.",noSaved:"No saved intelligence.",noSavedText:"Save a story to build your personal queue.",noMatch:"No matching intelligence.",noBrief:"No briefing available.",
loading:"Loading",feedsOperational:"Feeds operational",dataset:"Dataset",datasetUnavailable:"Dataset unavailable",publishDataset:"Publish a valid news.json",briefing:"DAILY BRIEFING",briefingCount:"stories in this briefing",playing:"Playing",paused:"Paused",stopped:"Stopped",finished:"Briefing complete",
whatHappened:"WHAT HAPPENED?",whyMatters:"WHY IT MATTERS",whatChanges:"WHAT CHANGES?",whatsNext:"WHAT'S NEXT?",confidence:"CONFIDENCE",ranking:"RANKING",evidence:"Evidence & provenance",publisher:"Publisher",sourceType:"Source type",published:"Published",
readOriginal:"Read original ↗",playSummary:"▶ Play summary",saveStory:"Save story",removeSaved:"Remove saved",noCorroborating:"No corroborating sources supplied.",askTitle:"Ask TechPulse",askPrompt:"Ask about the stories currently in TechPulse.",askExample:"Try: What are the most important AI developments today?",askNote:"This static edition answers using the loaded news dataset; it does not invent information.",askButton:"Search stories",
about:"About",editorial:"Editorial",copyright:"Copyright",source:"Sources",privacy:"Privacy",terms:"Terms",corrections:"Corrections",contact:"Contact"},
hi:{navOverview:"अवलोकन",navTechnology:"टेक्नोलॉजी",navGaming:"गेमिंग",navCybersecurity:"साइबर सुरक्षा",navAI:"एआई",navTrending:"ट्रेंडिंग",navSaved:"सेव्ड",navBrief:"दैनिक ब्रीफ",liveIntelligence:"लाइव इंटेलिजेंस",top10:"टॉप 10",radar:"टेक्नोलॉजी रडार",developing:"विकसित हो रही खबरें",trendingNow:"अभी ट्रेंडिंग",savedIntelligence:"सेव्ड इंटेलिजेंस",dailyTitle:"टेकपल्स डेली",playBrief:"ब्रीफिंग चलाएं",stories:"खबरें",sources:"स्रोत",updated:"अपडेटेड",technologyIntelligence:"टेक्नोलॉजी इंटेलिजेंस",gamingIntelligence:"गेमिंग इंटेलिजेंस",cybersecurityIntelligence:"साइबर सुरक्षा इंटेलिजेंस",aiIntelligence:"एआई इंटेलिजेंस",footerText:"मूल सारांश · स्रोत पारदर्शिता · अकाउंट आवश्यक नहीं"},
te:{navOverview:"అవలోకనం",navTechnology:"టెక్నాలజీ",navGaming:"గేమింగ్",navCybersecurity:"సైబర్ సెక్యూరిటీ",navAI:"AI",navTrending:"ట్రెండింగ్",navSaved:"సేవ్ చేసినవి",navBrief:"డైలీ బ్రీఫ్",liveIntelligence:"లైవ్ ఇంటెలిజెన్స్",top10:"టాప్ 10",radar:"టెక్నాలజీ రాడార్",developing:"అభివృద్ధి చెందుతున్న వార్తలు",trendingNow:"ఇప్పుడు ట్రెండింగ్",savedIntelligence:"సేవ్ చేసిన ఇంటెలిజెన్స్",dailyTitle:"టెక్‌పల్స్ డైలీ",playBrief:"బ్రీఫింగ్ ప్లే చేయండి",stories:"వార్తలు",sources:"మూలాలు",updated:"అప్‌డేట్",technologyIntelligence:"టెక్నాలజీ ఇంటెలిజెన్స్",gamingIntelligence:"గేమింగ్ ఇంటెలిజెన్స్",cybersecurityIntelligence:"సైబర్ సెక్యూరిటీ ఇంటెలిజెన్స్",aiIntelligence:"AI ఇంటెలిజెన్స్",footerText:"ఒరిజినల్ సారాంశాలు · మూల పారదర్శకత · అకౌంట్ అవసరం లేదు"},
ta:{navOverview:"மேலோட்டம்",navTechnology:"தொழில்நுட்பம்",navGaming:"கேமிங்",navCybersecurity:"சைபர் பாதுகாப்பு",navAI:"AI",navTrending:"டிரெண்டிங்",navSaved:"சேமித்தவை",navBrief:"தினசரி சுருக்கம்",liveIntelligence:"நேரடி நுண்ணறிவு",top10:"முதல் 10",radar:"தொழில்நுட்ப ரேடார்",developing:"வளரும் செய்திகள்",trendingNow:"இப்போது டிரெண்டிங்",savedIntelligence:"சேமித்த நுண்ணறிவு",dailyTitle:"டெக்பல்ஸ் டெய்லி",playBrief:"சுருக்கத்தை இயக்கவும்",stories:"செய்திகள்",sources:"மூலங்கள்",updated:"புதுப்பிப்பு",technologyIntelligence:"தொழில்நுட்ப நுண்ணறிவு",gamingIntelligence:"கேமிங் நுண்ணறிவு",cybersecurityIntelligence:"சைபர் பாதுகாப்பு நுண்ணறிவு",aiIntelligence:"AI நுண்ணறிவு"},
kn:{navOverview:"ಅವಲೋಕನ",navTechnology:"ತಂತ್ರಜ್ಞಾನ",navGaming:"ಗೇಮಿಂಗ್",navCybersecurity:"ಸೈಬರ್ ಭದ್ರತೆ",navAI:"AI",navTrending:"ಟ್ರೆಂಡಿಂಗ್",navSaved:"ಉಳಿಸಿದವು",navBrief:"ದೈನಂದಿನ ಬ್ರೀಫ್",liveIntelligence:"ಲೈವ್ ಇಂಟೆಲಿಜೆನ್ಸ್",top10:"ಟಾಪ್ 10",radar:"ತಂತ್ರಜ್ಞಾನ ರಾಡಾರ್",developing:"ಅಭಿವೃದ್ಧಿಯಲ್ಲಿರುವ ಸುದ್ದಿಗಳು",trendingNow:"ಈಗ ಟ್ರೆಂಡಿಂಗ್",savedIntelligence:"ಉಳಿಸಿದ ಇಂಟೆಲಿಜೆನ್ಸ್",dailyTitle:"ಟೆಕ್‌ಪಲ್ಸ್ ಡೈಲಿ",playBrief:"ಬ್ರೀಫ್ ಪ್ಲೇ ಮಾಡಿ",stories:"ಸುದ್ದಿಗಳು",sources:"ಮೂಲಗಳು",updated:"ಅಪ್‌ಡೇಟ್",technologyIntelligence:"ತಂತ್ರಜ್ಞಾನ ಇಂಟೆಲಿಜೆನ್ಸ್",gamingIntelligence:"ಗೇಮಿಂಗ್ ಇಂಟೆಲಿಜೆನ್ಸ್",cybersecurityIntelligence:"ಸೈಬರ್ ಭದ್ರತಾ ಇಂಟೆಲಿಜೆನ್ಸ್",aiIntelligence:"AI ಇಂಟೆಲಿಜೆನ್ಸ್"},
mr:{navOverview:"आढावा",navTechnology:"तंत्रज्ञान",navGaming:"गेमिंग",navCybersecurity:"सायबर सुरक्षा",navAI:"AI",navTrending:"ट्रेंडिंग",navSaved:"जतन केलेले",navBrief:"दैनिक ब्रीफ",liveIntelligence:"लाईव्ह इंटेलिजन्स",top10:"टॉप 10",radar:"तंत्रज्ञान रडार",developing:"विकसनशील बातम्या",trendingNow:"आत्ता ट्रेंडिंग",savedIntelligence:"जतन केलेले इंटेलिजन्स",dailyTitle:"टेकपल्स डेली",playBrief:"ब्रीफिंग प्ले करा",stories:"बातम्या",sources:"स्रोत",updated:"अपडेट",technologyIntelligence:"तंत्रज्ञान इंटेलिजन्स",gamingIntelligence:"गेमिंग इंटेलिजन्स",cybersecurityIntelligence:"सायबर सुरक्षा इंटेलिजन्स",aiIntelligence:"AI इंटेलिजन्स"}
};

function tr(k){return (T[S.language]&&T[S.language][k])||T.en[k]||k}
function applyI18n(){
 document.documentElement.lang=S.language;
 $$("[data-i18n]").forEach(e=>e.textContent=tr(e.dataset.i18n));
 $$("[data-i18n-html]").forEach(e=>e.innerHTML=tr(e.dataset.i18nHtml));
 $$("[data-i18n-placeholder]").forEach(e=>e.placeholder=tr(e.dataset.i18nPlaceholder));
 $("#language").value=S.language;
}

function card(x,i=0){
 const sv=S.saved.has(x.id);
 return `<article class="card">
 <div class="cardtop"><span class="rank">${i<10?"#"+(i+1):"SIGNAL"}</span><span class="tag">${esc(x.category)}</span></div>
 <h3>${esc(x.title)}</h3><p>${esc(x.summary)}</p>
 <div class="meta"><span>${esc(x.source)} · ${ago(x.published_at)}</span><span class="confidence">${Math.round(x.confidence)}%</span></div>
 <div class="buttons"><button data-open="${esc(x.id)}">${esc(tr("intelligence"))}</button>
 <button class="${sv?"saved":""}" data-save="${esc(x.id)}">${sv?esc(tr("saved")):esc(tr("save"))}</button>
 <button data-speak="${esc(x.id)}">${esc(tr("listen"))}</button></div></article>`;
}

function cat(id,key){
 const a=S.a.filter(x=>(x.category+" "+x.tags.join(" ")).toLowerCase().includes(key));
 $(id).innerHTML=a.length?a.map(card).join(""):`<div class="panel">${esc("No "+key+" intelligence in the current dataset.")}</div>`;
}

function buildBrief(){
 S.briefItems=S.a.slice(0,Math.min(15,S.a.length));
 S.briefIndex=Math.min(S.briefIndex,Math.max(0,S.briefItems.length-1));
 $("#briefing").innerHTML=S.briefItems.length
 ? `<div class="brief-head"><span class="eyebrow">${tr("briefing")}</span><strong>${S.briefItems.length} ${tr("briefingCount")}</strong></div>`+
 S.briefItems.map((x,i)=>`<div class="brief ${i===S.briefIndex?"current":""}" data-brief="${i}">
 <b>${String(i+1).padStart(2,"0")} · ${esc(x.category)}</b><h4>${esc(x.title)}</h4><p>${esc(x.summary)}</p>
 <div class="brief-meta">${esc(x.source)} · ${ago(x.published_at)} · ${Math.round(x.importance)} impact</div></div>`).join("")
 : `<p>${tr("noBrief")}</p>`;
 updateBriefProgress();
}

function updateBriefProgress(){
 const total=S.briefItems.length||1, pct=((S.briefIndex+1)/total)*100;
 $("#briefProgress i").style.setProperty("--w",pct+"%");
 $$(".brief").forEach((e,i)=>e.classList.toggle("current",i===S.briefIndex));
}

function render(){
 const top=S.a.slice(0,10);
 $("#top").innerHTML=top.length?top.map(card).join(""):`<div class="panel">${tr("noStories")}</div>`;
 const dev=S.a.filter(x=>["DEVELOPING","NEW"].includes(x.status)).slice(0,8);
 $("#developing").innerHTML=dev.map(x=>`<div class="compact" data-open="${esc(x.id)}"><strong>${Math.round(x.importance)}</strong><span>${esc(x.title)}</span></div>`).join("")||"<p>No developing stories.</p>";
 const tx=S.a.slice(0,15).map(x=>`<span class="tick"><b>${esc(x.category)}</b> · ${esc(x.title)}</span>`).join("");
 $("#ticker").innerHTML=tx+tx;
 cat("#technology","technology");cat("#gaming","gaming");cat("#cybersecurity","cyber");cat("#ai","ai");
 const cats=["AI","Cybersecurity","Cloud","Hardware","Gaming","Robotics","Quantum","Space","Linux","Enterprise"];
 $("#radar").innerHTML=cats.map(c=>{const a=S.a.filter(x=>(x.category+" "+x.tags.join(" ")).toLowerCase().includes(c.toLowerCase()));
 const m=a.length?Math.round(a.reduce((z,x)=>z+x.momentum,0)/a.length):0;
 return `<div class="signal"><b>${c} <span class="${m>60?"up":m&&m<40?"down":""}">${m>60?"↑↑":m>40?"↑":m?"↓":"—"}</span></b><span>${m||"No"} momentum signal</span></div>`}).join("");
 let g={};S.a.forEach(x=>(g[x.category]??={n:x.category,s:0,c:0},g[x.category].s+=x.momentum,g[x.category].c++));
 $("#trending").innerHTML=Object.values(g).map(x=>({...x,v:Math.round(x.s/x.c)})).sort((a,b)=>b.v-a.v)
 .map((x,i)=>`<div class="trendrow"><b>#${i+1}</b><div><b>${esc(x.n)}</b><div class="bar"><i style="--w:${Math.max(0,Math.min(100,x.v))}%"></i></div></div><span>${x.v}</span></div>`).join("")||"<div class='panel'>No trend data.</div>";
 const sv=S.a.filter(x=>S.saved.has(x.id));
 $("#saved").innerHTML=sv.length?sv.map(card).join(""):`<div class="panel"><b>${tr("noSaved")}</b><p>${tr("noSavedText")}</p></div>`;
 buildBrief();
 applyI18n();
}

async function load(){
 try{
  const r=await fetch("news.json?ts="+Date.now(),{cache:"no-store"});
  if(!r.ok)throw Error(r.status);
  const d=await r.json();
  S.a=(Array.isArray(d)?d:d.articles||[]).map(n).filter(x=>x.url!=="#");
  S.a.sort((a,b)=>(b.importance+b.freshness+b.confidence+b.momentum)-(a.importance+a.freshness+a.confidence+a.momentum));
  $("#feedStatus").textContent=tr("feedsOperational");
  $("#feedMeta").textContent=d.generated_at?tr("dataset")+" "+new Date(d.generated_at).toLocaleString(S.language):tr("dataset");
  $("#count").textContent=S.a.length;
  $("#sources").textContent=new Set(S.a.map(x=>x.source)).size;
  $("#updated").textContent=d.generated_at?new Date(d.generated_at).toLocaleTimeString(S.language,{hour:"2-digit",minute:"2-digit"}):"—";
  render();
 }catch(e){
  $("#feedStatus").textContent=tr("datasetUnavailable");$("#feedMeta").textContent=tr("publishDataset");console.error(e);
 }
}

function openStory(id){
 const x=S.a.find(a=>a.id===id);if(!x)return;
 const cs=x.corroborating_sources;
 $("#modalBody").innerHTML=`<span class="eyebrow">${esc(x.category)} · ${esc(x.verification_status)}</span>
 <h2>${esc(x.title)}</h2><p>${esc(x.summary)}</p><div class="intel">
 <div><b>${tr("whatHappened")}</b>${esc(x.summary)}</div><div><b>${tr("whyMatters")}</b>${esc(x.why)}</div>
 <div><b>${tr("whatChanges")}</b>${esc(x.changes)}</div><div><b>${tr("whatsNext")}</b>${esc(x.next)}</div>
 <div><b>${tr("confidence")}</b>${Math.round(x.confidence)}%</div><div><b>${tr("ranking")}</b>Impact ${Math.round(x.importance)} · Momentum ${Math.round(x.momentum)} · Freshness ${Math.round(x.freshness)}</div></div>
 <div class="buttons"><button data-speak="${esc(x.id)}">${tr("playSummary")}</button><button data-save="${esc(x.id)}">${S.saved.has(x.id)?tr("removeSaved"):tr("saveStory")}</button>
 <a href="${x.url}" target="_blank" rel="noopener noreferrer">${tr("readOriginal")}</a></div>
 <h3>${tr("evidence")}</h3><p>${tr("publisher")}: ${esc(x.source)} · ${tr("sourceType")}: ${esc(x.source_type)} · ${tr("published")}: ${esc(x.published_at||"unknown")}</p>
 <div class="sources">${cs.length?cs.map(s=>{const u=typeof s==="string"?s:s.url;return `<a href="${url(u)}" target="_blank" rel="noopener noreferrer"><span>${esc(typeof s==="string"?s:s.title||s.source||"Corroborating source")}</span><small>↗</small></a>`}).join(""):`<p>${tr("noCorroborating")}</p>`}</div>`;
 show();
}
function show(){$("#modal").hidden=false;document.body.style.overflow="hidden"}
function close(){$("#modal").hidden=true;document.body.style.overflow="";window.speechSynthesis?.cancel();S.speaking=false}
function speak(id){
 const x=S.a.find(a=>a.id===id);if(!x)return;
 if(!("speechSynthesis"in window))return alert("Browser narration is unavailable.");
 speechSynthesis.cancel();
 const u=new SpeechSynthesisUtterance(`${x.title}. ${x.summary} Why it matters: ${x.why}. What changes: ${x.changes}. What's next: ${x.next}.`);
 u.rate=1;u.onstart=()=>S.speaking=true;u.onend=()=>S.speaking=false;speechSynthesis.speak(u);
}
function speakBrief(index=S.briefIndex){
 if(!S.briefItems.length)return;
 S.briefIndex=Math.max(0,Math.min(index,S.briefItems.length-1));
 const x=S.briefItems[S.briefIndex];speechSynthesis.cancel();
 const u=new SpeechSynthesisUtterance(`Story ${S.briefIndex+1}. ${x.title}. ${x.summary} Why it matters: ${x.why}.`);
 u.rate=.96;u.onstart=()=>{S.speaking=true;updateBriefProgress()};u.onend=()=>{S.speaking=false;if(S.briefIndex<S.briefItems.length-1){S.briefIndex++;updateBriefProgress();setTimeout(()=>speakBrief(S.briefIndex),250)}else{updateBriefProgress();}};
 speechSynthesis.speak(u);updateBriefProgress();
}
function stopBrief(){speechSynthesis.cancel();S.speaking=false;updateBriefProgress()}
function save(id){S.saved.has(id)?S.saved.delete(id):S.saved.add(id);localStorage.tp_saved=JSON.stringify([...S.saved]);render()}
function view(v){$$(".nav").forEach(b=>b.classList.toggle("active",b.dataset.view===v));$$(".view").forEach(x=>x.classList.toggle("active",x.id==="view-"+v));scrollTo({top:0,behavior:S.reduced?"auto":"smooth"})}
function settings(){document.documentElement.dataset.theme=S.theme;document.documentElement.style.setProperty("--font",S.font+"px");document.documentElement.classList.toggle("reduce-motion",S.reduced)}
function askTechPulse(){
 const q=prompt(tr("askPrompt")+" "+tr("askExample"));if(!q)return;
 const terms=q.toLowerCase().split(/\W+/).filter(w=>w.length>2);
 const hits=S.a.map(x=>({x,score:terms.reduce((n,t)=>n+((x.title+" "+x.summary+" "+x.category+" "+x.tags.join(" ")).toLowerCase().includes(t)?1:0),0)})).filter(o=>o.score).sort((a,b)=>b.score-a.score).slice(0,8);
 $("#modalBody").innerHTML=`<span class="eyebrow">${tr("askTitle")}</span><h2>${esc(q)}</h2><p>${tr("askNote")}</p>${hits.length?`<div class="ask-results">${hits.map((h,i)=>`<div class="ask-result"><b>#${i+1}</b><button data-open="${esc(h.x.id)}">${esc(h.x.title)}</button><small>${esc(h.x.category)} · ${esc(h.x.source)}</small></div>`).join("")}</div>`:`<p>${tr("noMatch")}</p>`}`;show();
}
function policy(k){
 const d={about:["About TechPulse","TechPulse is an original technology intelligence layer for discovering, organizing, explaining and navigating technology and gaming developments."],editorial:["Editorial Policy","Prioritize factual accuracy, source transparency, attribution and separation of fact, analysis, forecast and unconfirmed information."],copyright:["Content & Copyright","TechPulse does not intentionally reproduce complete third-party articles. Summaries are independently worded and readers are directed to the original source."],source:["Source Policy","Sources are evaluated for reliability, freshness, expertise, duplicate rate, feed health and reporting quality. Primary sources receive appropriate weight."],privacy:["Privacy Policy","Core preferences and saved stories are stored locally in the browser. No account is required for the core static experience."],terms:["Terms of Use","TechPulse is an information and navigation layer. External content and source availability remain under their respective publishers."],corrections:["Corrections Policy","Incorrect intelligence should be reviewed, corrected or suppressed and marked appropriately; known errors should not knowingly remain presented as confirmed."],contact:["Contact / Content Concern","Replace this production placeholder with the official TechPulse contact channel for corrections, licensing questions and security reports."]};
 $("#modalBody").innerHTML=`<span class="eyebrow">TECHPULSE POLICY</span><h2>${esc(d[k][0])}</h2><p>${esc(d[k][1])}</p>`;show();
}

document.addEventListener("click",e=>{
 let b=e.target.closest("[data-view]");if(b)return view(b.dataset.view);
 let o=e.target.closest("[data-open]");if(o)return openStory(o.dataset.open);
 let s=e.target.closest("[data-save]");if(s)return save(s.dataset.save);
 let p=e.target.closest("[data-speak]");if(p)return speak(p.dataset.speak);
 if(e.target.closest("[data-close]"))return close();
 let pol=e.target.closest("[data-policy]");if(pol)return policy(pol.dataset.policy);
});
$("#search").oninput=e=>{const q=e.target.value.toLowerCase();const a=S.a.filter(x=>(x.title+" "+x.summary+" "+x.category+" "+x.source+" "+x.tags.join(" ")).toLowerCase().includes(q));$("#top").innerHTML=(q?a:S.a.slice(0,10)).map(card).join("")||`<div class="panel">${tr("noMatch")}</div>`};
$("#language").onchange=e=>{S.language=e.target.value;localStorage.tp_lang=S.language;render()};
$("#theme").onclick=()=>{S.theme=S.theme==="dark"?"light":S.theme==="light"?"glass":"dark";localStorage.tp_theme=S.theme;settings()};
$("#fontPlus").onclick=()=>{S.font=Math.min(19,S.font+1);localStorage.tp_font=S.font;settings()};
$("#fontMinus").onclick=()=>{S.font=Math.max(13,S.font-1);localStorage.tp_font=S.font;settings()};
$("#motion").onclick=()=>{S.reduced=!S.reduced;localStorage.tp_motion=S.reduced?"reduced":"normal";settings()};
$("#startBrief").onclick=()=>{view("briefing");S.briefIndex=0;speakBrief(0)};
$("#playBrief").onclick=()=>{if(S.speaking){speechSynthesis.pause();S.speaking=false;$("#playBrief").firstElementChild?.replaceWith?.(document.createTextNode("▶ "));}else if(speechSynthesis.paused){speechSynthesis.resume();S.speaking=true}else speakBrief(S.briefIndex)};
$("#briefStop").onclick=stopBrief;
$("#briefNext").onclick=()=>{speechSynthesis.cancel();S.briefIndex=Math.min(S.briefIndex+1,S.briefItems.length-1);updateBriefProgress();speakBrief(S.briefIndex)};
$("#briefPrev").onclick=()=>{speechSynthesis.cancel();S.briefIndex=Math.max(S.briefIndex-1,0);updateBriefProgress();speakBrief(S.briefIndex)};
$("#ask").onclick=askTechPulse;
document.addEventListener("keydown",e=>{if(e.key==="Escape")close()});
applyI18n();settings();load();
})();