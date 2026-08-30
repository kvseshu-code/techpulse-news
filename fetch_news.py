#!/usr/bin/env python3
"""TechPulse static RSS/Atom builder: normalize, deduplicate, cluster, rank, validate, fail safely."""
from pathlib import Path
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse
from collections import defaultdict
import urllib.request, urllib.error, xml.etree.ElementTree as ET, json, re, html, hashlib, time, os, sys, tempfile

ROOT=Path(__file__).parent; CFG=ROOT/'config'; OUT=ROOT/'news.json'; MAX=100; PER_SOURCE=30; AGE_HOURS=96; TIMEOUT=15
STOP=set('the a an and or of to in on for with from by is are was were this that as at be has have had its into about after before over under new says said how why what when where who their they it we you your our'.split())

def clean(v): return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]*>',' ',v or ''))).strip()
def toks(s): return {x for x in re.findall(r'[a-z0-9][a-z0-9+#.-]{2,}',s.lower()) if x not in STOP}
def sim(a,b):
    x,y=toks(a),toks(b); return len(x&y)/len(x|y) if x and y else 0
def iso(v):
    if not v:return ''
    try:return parsedate_to_datetime(v.strip()).astimezone(timezone.utc).isoformat()
    except:pass
    try:return datetime.fromisoformat(v.strip().replace('Z','+00:00')).astimezone(timezone.utc).isoformat()
    except:return ''
def text(el,names):
    for c in list(el):
        if c.tag.split('}')[-1].lower() in {n.lower() for n in names}:
            if c.text:return c.text
    return ''
def parse(raw,src):
    root=ET.fromstring(raw); entries=[e for e in root.iter() if e.tag.split('}')[-1].lower() in ('item','entry')]; out=[]
    for e in entries[:PER_SOURCE]:
        title=clean(text(e,['title'])); desc=clean(text(e,['description','summary','content'])); published=iso(text(e,['pubDate','published','updated','date'])); link=''
        for c in list(e):
            if c.tag.split('}')[-1].lower()=='link': link=c.attrib.get('href','') or (c.text or '');
            if link:break
        link=link or clean(text(e,['guid']))
        u=urlparse(link)
        if title and link and u.scheme in ('http','https') and u.netloc: out.append({'title':title[:300],'description':desc[:1200],'published_at':published or datetime.now(timezone.utc).isoformat(),'url':link,'source':src['name'],'source_type':src.get('type','secondary'),'category':src.get('category','Technology'),'source_trust':int(src.get('trust',70))})
    return out
def fetch(url):
    r=urllib.request.Request(url,headers={'User-Agent':'TechPulse/1.0','Accept':'application/rss+xml, application/atom+xml, application/xml, text/xml'})
    with urllib.request.urlopen(r,timeout=TIMEOUT) as x:return x.read()
def category(x):
    t=(x['title']+' '+x['description']).lower(); rules={'AI':['ai','artificial intelligence','llm','machine learning','model','openai','anthropic','gemini'],'Cybersecurity':['cyber','security','malware','ransomware','vulnerability','cve','breach','zero-day'],'Gaming':['game','gaming','playstation','xbox','nintendo','steam','esports'],'Cloud':['aws','azure','cloud','kubernetes','container','terraform'],'Hardware':['nvidia','amd','intel','chip','processor','gpu','device'],'Enterprise':['enterprise','saas','software','database','microsoft']}; scores={k:sum(w in t for w in v) for k,v in rules.items()}; return max(scores,key=scores.get) if max(scores.values()) else x['category']
def age(iso_s):
    try:return max(0,round(100-(datetime.now(timezone.utc)-datetime.fromisoformat(iso_s)).total_seconds()/3600*2))
    except:return 30
def build():
    cfg=json.loads((CFG/'sources.json').read_text()); candidates=[]; health=[]
    for s in cfg.get('sources',[]):
        if not s.get('enabled',True):continue
        try:a=parse(fetch(s['url']),s); candidates+=a; health.append({'source':s['name'],'status':'HEALTHY','articles':len(a)})
        except Exception as e:health.append({'source':s['name'],'status':'WARNING','error':str(e)[:180]})
    cutoff=time.time()-AGE_HOURS*3600; clean_items=[]; seen=set()
    for x in candidates:
        if x['url'] in seen:continue
        seen.add(x['url'])
        try:
            if datetime.fromisoformat(x['published_at']).timestamp()<cutoff:continue
        except:pass
        x['category']=category(x);clean_items.append(x)
    clusters=[]
    for x in clean_items:
        target=next((c for c in clusters if max(sim(x['title'],z['title']) for z in c)>=.58),None)
        (target if target is not None else clusters.append([x]) or clusters[-1]).append(x) if target is not None else None
    stories=[]
    for i,c in enumerate(clusters,1):
        c.sort(key=lambda x:(x['source_trust'],age(x['published_at'])),reverse=True); p=c[0]; sources=list(dict.fromkeys(x['source'] for x in c)); fresh=age(p['published_at']); conf=min(99,round(p['source_trust']*.65+min(len(sources),5)*6+(7 if p['source_type']=='primary' else 0))); imp=min(100,round(p['source_trust']*.45+len(c)*9+fresh*.25)); mom=min(100,round(len(c)*16+fresh*.55)); status='VERIFIED' if len(sources)>=2 or p['source_type']=='primary' else 'DEVELOPING'; sid='TP-'+hashlib.sha1('|'.join(sorted(x['url'] for x in c)).encode()).hexdigest()[:12]
        stories.append({'id':sid,'cluster_id':f'CL-{i:04d}','title':p['title'],'summary':p['description'] or 'A technology development has been reported. Open the original source for full context.','why_it_matters':'The development may affect the relevant technology, users, businesses, or industry direction. Review the evidence and original reporting for context.','what_changes':'No additional practical change is asserted beyond the available source evidence.','whats_next':'Watch for official statements, independent confirmation, and subsequent updates.','category':p['category'],'subcategory':p['category'],'published_at':p['published_at'],'source':p['source'],'source_type':p['source_type'],'url':p['url'],'confidence':conf,'importance':imp,'freshness':fresh,'momentum':mom,'verification_status':status,'status':'NEW' if status=='VERIFIED' else 'DEVELOPING','tags':sources[:5],'corroborating_sources':[{'source':x['source'],'title':x['title'],'url':x['url']} for x in c[1:5]]})
    stories.sort(key=lambda x:x['importance']+x['freshness']+x['confidence']+x['momentum'],reverse=True); stories=stories[:MAX]
    if not stories:raise RuntimeError('No valid stories produced; last-known-good news.json preserved.')
    for i,x in enumerate(stories,1):x['rank']=i
    data={'schema_version':1,'product':'TechPulse','generated_at':datetime.now(timezone.utc).isoformat(),'article_count':len(stories),'source_count':len(set(x['source'] for x in stories)),'source_health':health,'articles':stories}; validate(data); atomic(data)
def validate(d):
    if d.get('schema_version')!=1 or not isinstance(d.get('articles'),list) or not d['articles']:raise ValueError('Invalid dataset')
    req={'id','title','summary','category','published_at','source','url','confidence','importance'};ids=set();urls=set()
    for x in d['articles']:
        if req-set(x):raise ValueError('Missing story fields')
        if x['id'] in ids or x['url'] in urls:raise ValueError('Duplicate story')
        ids.add(x['id']);urls.add(x['url']);u=urlparse(x['url'])
        if u.scheme not in ('http','https') or not u.netloc:raise ValueError('Unsafe URL')
def atomic(d):
    fd,tmp=tempfile.mkstemp(prefix='news.',suffix='.json',dir=ROOT);os.close(fd);p=Path(tmp)
    try:p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8');os.replace(p,OUT)
    finally:
        if p.exists():p.unlink()
if __name__=='__main__':
    try:build();print('[OK] news.json updated')
    except Exception as e:print('[SAFE-FAIL]',e,file=sys.stderr);print('[SAFE-FAIL] Existing news.json preserved.',file=sys.stderr);sys.exit(1)
