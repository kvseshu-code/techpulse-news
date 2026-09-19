#!/usr/bin/env python3
"""TechPulse static RSS/Atom builder: normalize, deduplicate, cluster, rank, validate, fail safely."""
from pathlib import Path
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse
from collections import defaultdict
import urllib.request, urllib.error, xml.etree.ElementTree as ET, json, re, html, hashlib, time, os, sys, tempfile

ROOT=Path(__file__).parent; CFG=ROOT/'config'; OUT=ROOT/'news.json'; MAX=0; PER_SOURCE=100; AGE_HOURS=168; TIMEOUT=15
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
def _term_match(text, term):
    import re

    text = text or ""
    term = term.strip().lower()

    if not term:
        return False

    pattern = r"(?<!\w)" + re.escape(term) + r"(?!\w)"
    return re.search(pattern, text, flags=re.IGNORECASE) is not None


def category(x):
    """
    TechPulse Category Classifier V3

    Classification order:
      1. Explicit entities / unmistakable topics
      2. Strong title signals
      3. Supporting description signals
      4. Source category fallback
      5. Technology fallback

    The headline receives more weight than the description.
    Generic words such as "technology", "software", "game",
    "security", "device", and "space" are intentionally avoided
    as standalone classification signals.
    """

    title = str(x.get("title", "") or "")
    description = str(
        x.get("description", x.get("summary", "")) or ""
    )

    title_l = title.lower()
    description_l = description.lower()
    full_l = f"{title_l} {description_l}"

    # Normalize punctuation.
    for old, new in [
        ("’", "'"),
        ("–", "-"),
        ("—", "-"),
    ]:
        title_l = title_l.replace(old, new)
        description_l = description_l.replace(old, new)
        full_l = full_l.replace(old, new)

    # ------------------------------------------------------------------
    # CYBERSECURITY INCIDENT PRIORITY
    # ------------------------------------------------------------------
    # If the title explicitly describes a security incident,
    # classify it as Cybersecurity even when AI terminology is
    # also present.
    #
    # This is generic classification logic, not an article-specific
    # exception.
    # ------------------------------------------------------------------

    cyber_incident_terms = [
        "ransomware",
        "malware",
        "phishing",
        "zero-day",
        "zero day",
        "cyber attack",
        "cyberattack",
        "cybersecurity",
        "data breach",
        "security breach",
        "breach",
        "exploit",
        "exploited",
        "vulnerability",
        "vulnerabilities",
        "remote code execution",
        "rce",
        "credential theft",
        "identity theft",
        "botnet",
        "spyware",
        "rootkit",
        "supply-chain attack",
        "supply chain attack",
        "clickfix",
        "hacked",
        "hackers",
    ]

    cyber_morphology = {
        "breach": r"breach(?:es|ed|ing)?",
        "attack": r"attack(?:s|ed|ing)?",
        "exploit": r"exploit(?:s|ed|ing)?",
        "hack": r"hack(?:s|ed|ing)?",
        "vulnerability": r"vulnerabilit(?:y|ies)",
    }

    cyber_incident_match = False

    for term in cyber_incident_terms:
        if term in cyber_morphology:
            import re
            pattern = (
                r"(?<!\\w)"
                + cyber_morphology[term]
                + r"(?!\\w)"
            )
            if re.search(pattern, title_l, flags=re.IGNORECASE):
                cyber_incident_match = True
                break
        elif _term_match(title_l, term):
            cyber_incident_match = True
            break

    if cyber_incident_match:
        return "Cybersecurity"

    # 1. ENTITY / UNMISTAKABLE TOPIC OWNERSHIP
    # ------------------------------------------------------------------

    entity_rules = {
        "AI": [
            "openai",
            "anthropic",
            "google deepmind",
            "deepmind",
            "chatgpt",
            "gemini",
            "claude",
            "copilot",
            "hugging face",
            "large language model",
            "language model",
            "foundation model",
            "generative ai",
            "artificial intelligence",
            "machine learning",
            "deep learning",
            "ai agent",
            "ai agents",
            "agentic ai",
            "neural network",
            "computer vision",
            "natural language processing",
        ],

        "Cybersecurity": [
            "ransomware",
            "malware",
            "phishing",
            "zero-day",
            "zero day",
            "cyber attack",
            "cyberattack",
            "cybersecurity",
            "data breach",
            "security breach",
            "remote code execution",
            "credential theft",
            "identity theft",
            "botnet",
            "spyware",
            "rootkit",
            "supply-chain attack",
            "supply chain attack",
            "clickfix",
        ],

        "Gaming": [
            "playstation",
            "xbox",
            "nintendo",
            "steam deck",
            "steam frame",
            "roblox",
            "fortnite",
            "resident evil",
            "grand theft auto",
            "gta 6",
            "gta vi",
            "final fantasy",
            "world of warcraft",
            "kingdom hearts",
            "pokemon",
            "blizzcon",
            "video game",
            "video games",
            "videogame",
            "gameplay",
            "game studio",
            "game developer",
            "game publisher",
            "esports",
            "e-sports",
        ],

        "Cloud": [
            "amazon web services",
            "google cloud",
            "microsoft azure",
            "oracle cloud",
            "aws",
            "azure",
            "oci",
            "kubernetes",
            "terraform",
            "docker",
            "serverless",
            "cloud infrastructure",
            "cloud computing",
            "cloud platform",
            "cloud service",
            "cloud services",
            "container orchestration",
        ],

        "Hardware": [
            "nvidia",
            "amd",
            "intel",
            "qualcomm",
            "mediatek",
            "snapdragon",
            "radeon",
            "geforce",
            "apple silicon",
            "gpu",
            "cpu",
            "processor",
            "processors",
            "semiconductor",
            "semiconductors",
            "graphics card",
            "graphics cards",
            "motherboard",
            "ssd",
            "solid-state drive",
            "solid state drive",
            "oled display",
            "display panel",
            "system-on-chip",
            "system on chip",
        ],

        "Enterprise": [
            "salesforce",
            "servicenow",
            "workday",
            "sap",
            "customer relationship management",
            "enterprise resource planning",
            "crm",
            "erp",
            "saas",
            "software as a service",
            "enterprise software",
            "business intelligence",
            "enterprise technology",
        ],

        "Linux": [
            "ubuntu",
            "red hat enterprise linux",
            "rhel",
            "debian",
            "fedora",
            "arch linux",
            "suse linux",
            "linux kernel",
            "linux distribution",
            "linux distributions",
            "linux server",
            "linux desktop",
            "systemd",
        ],

        "Robotics": [
            "waymo",
            "zoox",
            "robotaxi",
            "humanoid robot",
            "humanoid robots",
            "industrial robot",
            "industrial robots",
            "robotic arm",
            "robotic arms",
            "autonomous robot",
            "autonomous robots",
            "robotics",
            "self-driving",
            "autonomous vehicle",
        ],

        "Quantum": [
            "quantum computer",
            "quantum computing",
            "quantum processor",
            "quantum processors",
            "quantum error correction",
            "quantum algorithm",
            "quantum algorithms",
            "quantum cryptography",
            "quantum network",
            "quantum networking",
            "qubit",
            "qubits",
        ],

        "Space": [
            "nasa",
            "spacex",
            "falcon 9",
            "starship",
            "artemis",
            "international space station",
            "space station",
            "spacecraft",
            "space telescope",
            "rocket launch",
            "satellite launch",
            "lunar mission",
            "mars mission",
            "moon mission",
            "orbital mission",
        ],
    }

    # ------------------------------------------------------------------
    # 2. STRONG TITLE SIGNALS
    # ------------------------------------------------------------------

    title_rules = {
        "AI": [
            "ai",
            "artificial intelligence",
            "machine learning",
            "language model",
            "llm",
            "ai agent",
            "ai agents",
            "agentic",
            "ai safety",
            "ai research",
            "ai model",
            "ai models",
            "ai-powered",
            "ai powered",
        ],

        "Cybersecurity": [
            "cybersecurity",
            "cyber attack",
            "cyberattack",
            "ransomware",
            "malware",
            "phishing",
            "zero-day",
            "zero day",
            "vulnerability",
            "exploit",
            "cve-",
            "data breach",
            "security breach",
            "security flaw",
            "security patch",
            "threat actor",
            "supply-chain attack",
            "supply chain attack",
        ],

        "Gaming": [
            "gaming",
            "gamer",
            "video game",
            "video games",
            "gameplay",
            "game developer",
            "game studio",
            "game publisher",
            "game launch",
            "game release",
            "dlc",
            "rpg",
            "playstation",
            "xbox",
            "nintendo",
            "steam",
            "esports",
        ],

        "Cloud": [
            "cloud computing",
            "cloud infrastructure",
            "cloud platform",
            "cloud service",
            "aws",
            "azure",
            "oci",
            "kubernetes",
            "terraform",
            "docker",
            "serverless",
            "container",
            "containers",
            "data center",
            "datacenter",
        ],

        "Hardware": [
            "gpu",
            "cpu",
            "processor",
            "processors",
            "chip",
            "chips",
            "semiconductor",
            "nvidia",
            "amd",
            "intel",
            "qualcomm",
            "snapdragon",
            "graphics card",
            "ssd",
            "ram",
            "motherboard",
            "oled",
            "display",
            "hardware",
        ],

        "Enterprise": [
            "enterprise",
            "saas",
            "crm",
            "erp",
            "salesforce",
            "servicenow",
            "sap",
            "workday",
            "business software",
            "enterprise software",
        ],

        "Linux": [
            "linux",
            "ubuntu",
            "rhel",
            "red hat",
            "debian",
            "fedora",
            "linux kernel",
            "systemd",
        ],

        "Robotics": [
            "robotaxi",
            "robotics",
            "robot",
            "robots",
            "humanoid",
            "self-driving",
            "autonomous vehicle",
        ],

        "Quantum": [
            "quantum",
            "qubit",
            "qubits",
        ],

        "Space": [
            "nasa",
            "spacex",
            "spacecraft",
            "space station",
            "space telescope",
            "rocket",
            "satellite",
            "lunar",
            "mars",
            "moon",
            "astronaut",
            "orbit",
            "orbital",
        ],
    }

    # ------------------------------------------------------------------
    # 3. DESCRIPTION SUPPORT
    # ------------------------------------------------------------------

    description_rules = {
        "AI": [
            "artificial intelligence",
            "machine learning",
            "large language model",
            "language model",
            "generative ai",
            "ai agent",
            "ai agents",
            "agentic ai",
            "openai",
            "anthropic",
            "gemini",
            "claude",
            "chatgpt",
        ],

        "Cybersecurity": [
            "cybersecurity",
            "ransomware",
            "malware",
            "phishing",
            "vulnerability",
            "exploit",
            "cve-",
            "data breach",
            "security breach",
            "security flaw",
            "threat actor",
        ],

        "Gaming": [
            "video game",
            "video games",
            "gameplay",
            "playstation",
            "xbox",
            "nintendo",
            "gaming",
            "gamer",
            "esports",
        ],

        "Cloud": [
            "cloud computing",
            "cloud infrastructure",
            "cloud platform",
            "amazon web services",
            "google cloud",
            "microsoft azure",
            "kubernetes",
            "terraform",
            "serverless",
            "container orchestration",
        ],

        "Hardware": [
            "graphics processing unit",
            "central processing unit",
            "processor",
            "semiconductor",
            "nvidia",
            "amd",
            "intel",
            "graphics card",
            "ssd",
            "display panel",
            "oled display",
        ],

        "Enterprise": [
            "enterprise software",
            "enterprise technology",
            "saas",
            "customer relationship management",
            "enterprise resource planning",
            "salesforce",
            "servicenow",
            "sap",
        ],

        "Linux": [
            "linux kernel",
            "linux distribution",
            "ubuntu",
            "red hat enterprise linux",
            "rhel",
            "debian",
            "fedora",
            "systemd",
        ],

        "Robotics": [
            "robotaxi",
            "robotics",
            "humanoid robot",
            "autonomous vehicle",
            "self-driving",
            "robotic arm",
        ],

        "Quantum": [
            "quantum computer",
            "quantum computing",
            "quantum processor",
            "quantum error correction",
            "qubit",
        ],

        "Space": [
            "nasa",
            "spacex",
            "spacecraft",
            "space station",
            "rocket launch",
            "satellite launch",
            "lunar mission",
            "mars mission",
            "moon mission",
            "orbital mission",
        ],

        "Technology": [
            "technology",
            "tech company",
            "smartphone",
            "internet",
            "browser",
            "electronics",
            "digital technology",
        ],
    }

    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    # ENTITY CHECK
    # ------------------------------------------------------------------

    entity_hits = {}

    for name, terms in entity_rules.items():
        hits = [term for term in terms if _term_match(title_l, term)]
        if hits:
            entity_hits[name] = hits

    # If a title contains an unmistakable entity/topic, use it.
    # More than one entity is resolved using the number of matching
    # terms and the category-specific priority below.
    if entity_hits:
        entity_priority = [
            "AI",
            "Cybersecurity",
            "Gaming",
            "Cloud",
            "Hardware",
            "Enterprise",
            "Linux",
            "Robotics",
            "Quantum",
            "Space",
        ]

        best_entity = max(
            entity_priority,
            key=lambda name: (
                len(entity_hits.get(name, [])),
                -entity_priority.index(name)
            )
        )

        if entity_hits.get(best_entity):
            return best_entity

    # ------------------------------------------------------------------
    # WEIGHTED TITLE + DESCRIPTION SCORING
    # ------------------------------------------------------------------

    priority = [
        "AI",
        "Cybersecurity",
        "Gaming",
        "Cloud",
        "Hardware",
        "Enterprise",
        "Linux",
        "Robotics",
        "Quantum",
        "Space",
        "Technology",
    ]

    scores = {}

    for name in priority:
        title_hits = sum(
            1 for term in title_rules.get(name, [])
            if _term_match(title_l, term)
        )

        description_hits = sum(
            1 for term in description_rules.get(name, [])
            if _term_match(description_l, term)
        )

        full_hits = sum(
            1 for term in description_rules.get(name, [])
            if _term_match(full_l, term)
        )

        scores[name] = (
            title_hits * 20
            + description_hits * 5
            + full_hits
        )

    best = max(priority, key=lambda name: scores[name])

    if scores[best] > 0:
        return best

    # ------------------------------------------------------------------
    # SOURCE CATEGORY FALLBACK
    # ------------------------------------------------------------------

    source_category = x.get("category")

    if source_category in priority:
        return source_category

    return "Technology"


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
        if target is not None:
            target.append(x)
        else:
            clusters.append([x])
    stories=[]
    for i,c in enumerate(clusters,1):
        c.sort(key=lambda x:(x['source_trust'],age(x['published_at'])),reverse=True); p=c[0]; sources=list(dict.fromkeys(x['source'] for x in c)); fresh=age(p['published_at']); conf=min(99,round(p['source_trust']*.65+min(len(sources),5)*6+(7 if p['source_type']=='primary' else 0))); imp=min(100,round(p['source_trust']*.45+len(c)*9+fresh*.25)); mom=min(100,round(len(c)*16+fresh*.55)); status='VERIFIED' if len(sources)>=2 or p['source_type']=='primary' else 'DEVELOPING'; sid='TP-'+hashlib.sha1('|'.join(sorted(x['url'] for x in c)).encode()).hexdigest()[:12]
        stories.append({'id':sid,'cluster_id':f'CL-{i:04d}','title':p['title'],'summary':p['description'] or 'A technology development has been reported. Open the original source for full context.','why_it_matters':'The development may affect the relevant technology, users, businesses, or industry direction. Review the evidence and original reporting for context.','what_changes':'No additional practical change is asserted beyond the available source evidence.','whats_next':'Watch for official statements, independent confirmation, and subsequent updates.','category':p['category'],'subcategory':p['category'],'published_at':p['published_at'],'source':p['source'],'source_type':p['source_type'],'url':p['url'],'confidence':conf,'importance':imp,'freshness':fresh,'momentum':mom,'verification_status':status,'status':'NEW' if status=='VERIFIED' else 'DEVELOPING','tags':sources[:5],'corroborating_sources':[{'source':x['source'],'title':x['title'],'url':x['url']} for x in c[1:5]]})
    stories.sort(
        key=lambda x: (
            x.get('published_at', ''),
            x.get('importance', 0) + x.get('freshness', 0) + x.get('confidence', 0) + x.get('momentum', 0)
        ),
        reverse=True
    )
    if MAX > 0:
        stories=stories[:MAX]
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
