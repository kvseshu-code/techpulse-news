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
        if title and link and u.scheme in ('http','https') and u.netloc:
            published_value = published or datetime.now(timezone.utc).isoformat()

            # Never publish future-dated stories.
            try:
                published_dt = datetime.fromisoformat(published_value.replace('Z', '+00:00'))
                if published_dt > datetime.now(timezone.utc):
                    continue
            except Exception:
                pass

            out.append({
                'title': title[:300],
                'description': desc[:1200],
                'published_at': published_value,
                'url': link,
                'source': src['name'],
                'source_type': src.get('type','secondary'),
                'category': src.get('category','Technology'),
                'source_trust': int(src.get('trust',70))
            })
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


def _tp_normalize(value):
    value = str(value or "").lower()
    value = value.replace("’", "'").replace("–", "-").replace("—", "-")
    return value


def _tp_has(text, term):
    return _term_match(text, term)


def _tp_any(text, terms):
    return any(_tp_has(text, term) for term in terms)


def _tp_matches(text, terms):
    return [term for term in terms if _tp_has(text, term)]


def classify_article_base(x):
    """
    TechPulse Phase 2 classifier.

    The classifier separates:
      - primary category
      - secondary topics
      - content type
      - relevance
      - confidence
      - quality flags

    Company names and source categories are not treated as
    authoritative category signals.
    """

    title = _tp_normalize(x.get("title", ""))
    description = _tp_normalize(
        x.get("description", x.get("summary", "")) or ""
    )
    full = f"{title} {description}"

    quality_flags = []

    # --------------------------------------------------------
    # CONTENT TYPE
    # --------------------------------------------------------

    commerce_terms = [
        "promo code",
        "promo codes",
        "coupon",
        "coupons",
        "discount code",
        "discount codes",
        "deal",
        "deals",
        "sale",
        "sales",
        "save $",
        "save up to",
        "prime day",
        "black friday",
        "cyber monday",
        "best deals",
        "cheapest",
        "best buys",
        "what to buy",
        "best to buy",
        "buying guide",
        "shopping guide",
    ]

    review_terms = [
        "review",
        "tested",
        "hands-on",
        "hands on",
        "pros and cons",
        "benchmark review",
        "performance review",
    ]

    tutorial_terms = [
        "how to",
        "how do you",
        "guide",
        "tutorial",
        "ways to",
        "steps to",
        "what causes",
        "can it be fixed",
    ]

    research_terms = [
        "researchers",
        "research",
        "study finds",
        "study shows",
        "new study",
        "new method",
        "scientists",
        "university",
        "laboratory",
        "lab",
    ]

    analysis_terms = [
        "analysis",
        "opinion",
        "why ",
        "could ",
        "debate",
        "roundtable",
        "explained",
        "what it means",
        "risk",
        "risks",
    ]

    event_terms = [
        "webinar",
        "conference",
        "summit",
        "event",
        "devfest",
        "roundtable",
        "keynote",
        "live event",
    ]

    if _tp_any(title, commerce_terms):
        content_type = "commerce"
        quality_flags.append("PROMOTIONAL_OR_COMMERCE")
    elif _tp_any(title, review_terms):
        content_type = "review"
    elif _tp_any(title, tutorial_terms):
        content_type = "tutorial"
    elif _tp_any(title, research_terms):
        content_type = "research"
    elif _tp_any(title, analysis_terms):
        content_type = "analysis"
    elif _tp_any(title, event_terms):
        content_type = "event"
    else:
        content_type = "news"

    # --------------------------------------------------------
    # NON-TECH / GENERAL INTEREST FILTER
    # --------------------------------------------------------

    nontech_terms = [
        "recipe",
        "recipes",
        "restaurant",
        "restaurants",
        "bird lovers",
        "gift ideas",
        "gifts for",
        "fashion",
        "celebrity",
        "box office",
        "best movies",
        "movie review",
        "movies",
        "anime",
        "comic strip",
        "comics",
        "streaming",
        "tv shows",
        "television shows",
        "travel",
        "vacation",
        "sports scores",
        "football scores",
        "basketball scores",
        "baseball scores",
    ]

    # --------------------------------------------------------
    # CATEGORY SIGNALS
    # --------------------------------------------------------

    rules = {
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
            "breach",
            "exploit",
            "exploited",
            "exploitation",
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
            "hacked",
            "hackers",
            "hacking",
            "zero trust",
            "mfa",
            "oauth",
            "authentication flaw",
            "security flaw",
            "security vulnerability",
            "security update",
            "security patch",
        ],

        "AI": [
            "artificial intelligence",
            "generative ai",
            "ai model",
            "ai models",
            "large language model",
            "language model",
            "foundation model",
            "llm",
            "llms",
            "ai agent",
            "ai agents",
            "agentic ai",
            "machine learning",
            "deep learning",
            "computer vision",
            "chatgpt",
            "openai",
            "anthropic",
            "claude",
            "gemini",
            "deepmind",
            "copilot",
            "hugging face",
            "ai benchmark",
            "ai benchmarking",
            "ai regulation",
            "ai safety",
            "physical ai",
        ],

        "Hardware": [
            "gpu",
            "gpus",
            "cpu",
            "cpus",
            "processor",
            "processors",
            "graphics card",
            "graphics cards",
            "semiconductor",
            "semiconductors",
            "chip",
            "chips",
            "soc",
            "ssd",
            "ssds",
            "nand",
            "dram",
            "memory chip",
            "memory chips",
            "ram",
            "display panel",
            "oled display",
            "monitor",
            "monitors",
            "motherboard",
            "laptop",
            "laptops",
            "desktop pc",
            "gaming pc",
            "smartphone",
            "smartphones",
            "iphone",
            "ipad",
            "macbook",
            "apple watch",
            "galaxy watch",
            "airpods",
            "headphones",
            "keyboard",
            "mouse",
            "printer",
            "3d printer",
            "webcam",
            "router",
            "nvidia",
            "amd",
            "intel",
            "qualcomm",
            "snapdragon",
            "radeon",
            "geforce",
            "apple silicon",
            "nvlink",
            "npu",
            "accelerator",
            "lithography",
        ],

        "Gaming": [
            "video game",
            "video games",
            "gameplay",
            "game studio",
            "game developer",
            "game publisher",
            "gaming",
            "playstation",
            "xbox",
            "nintendo",
            "steam",
            "steam deck",
            "steam frame",
            "fortnite",
            "roblox",
            "grand theft auto",
            "gta",
            "resident evil",
            "final fantasy",
            "world of warcraft",
            "kingdom hearts",
            "pokemon",
            "esports",
            "esports",
            "game release",
            "game launch",
            "game update",
            "gaming console",
            "gaming consoles",
        ],

        "Linux": [
            "linux",
            "linux kernel",
            "ubuntu",
            "rhel",
            "red hat enterprise linux",
            "debian",
            "fedora",
            "arch linux",
            "suse",
            "opensuse",
            "systemd",
            "gnome",
            "kde plasma",
            "io_uring",
            "gnu coreutils",
            "linux distribution",
            "linux desktop",
            "linux server",
        ],

        "Cloud": [
            "aws",
            "amazon web services",
            "google cloud",
            "microsoft azure",
            "azure",
            "oci",
            "oracle cloud",
            "kubernetes",
            "terraform",
            "docker",
            "serverless",
            "cloud infrastructure",
            "cloud computing",
            "cloud platform",
            "cloud service",
            "data center",
            "data centers",
            "ai data center",
            "ai data centers",
            "cloud region",
        ],

        "Enterprise": [
            "salesforce",
            "servicenow",
            "workday",
            "sap",
            "crm",
            "erp",
            "enterprise software",
            "enterprise technology",
            "microsoft 365",
            "office 365",
            "enterprise security",
            "business intelligence",
            "saas",
        ],

        "Robotics": [
            "robot",
            "robots",
            "robotics",
            "humanoid robot",
            "humanoid robots",
            "robotaxi",
            "robotaxis",
            "autonomous vehicle",
            "autonomous vehicles",
            "self-driving",
            "self driving",
            "robotic arm",
            "robotic arms",
            "industrial robot",
            "ros 2",
            "ros2",
            "waymo",
            "zoox",
        ],

        "Quantum": [
            "quantum computer",
            "quantum computing",
            "quantum processor",
            "quantum processors",
            "qubit",
            "qubits",
            "quantum error correction",
            "quantum algorithm",
            "quantum algorithms",
            "quantum network",
            "quantum networking",
            "cuda-q",
            "fault-tolerant quantum",
        ],

        "Space": [
            "nasa",
            "spacex",
            "falcon 9",
            "starship",
            "artemis",
            "international space station",
            "iss",
            "space station",
            "spacecraft",
            "space telescope",
            "rocket launch",
            "rocket launches",
            "satellite launch",
            "satellite launches",
            "lunar mission",
            "mars mission",
            "moon mission",
            "orbital mission",
            "starlink",
            "astronaut",
            "astronauts",
            "hubble",
            "telescope",
        ],

        "Technology": [
            "technology",
            "software",
            "application",
            "applications",
            "app",
            "apps",
            "platform",
            "developer",
            "developers",
            "open source",
            "github",
            "api",
            "webgpu",
            "internet",
            "browser",
            "digital",
            "computing",
            "database",
            "programming",
            "developer tools",
            "smart home",
            "home assistant",
            "raspberry pi",
        ],
    }

    # --------------------------------------------------------
    # SCORE TITLE AND DESCRIPTION SEPARATELY
    # --------------------------------------------------------

    scores = {}

    for name, terms in rules.items():
        title_hits = _tp_matches(title, terms)
        body_hits = _tp_matches(description, terms)

        scores[name] = (
            len(title_hits) * 10
            + len(body_hits) * 2
        )

    # --------------------------------------------------------
    # STRONG PRIMARY-TOPIC SIGNALS
    # --------------------------------------------------------

    cyber_event = _tp_any(title, [
        "ransomware",
        "malware",
        "phishing",
        "data breach",
        "security breach",
        "cyber attack",
        "cyberattack",
        "hacked",
        "hackers",
        "hacking",
        "zero-day",
        "zero day",
        "exploit",
        "exploited",
        "vulnerability",
        "vulnerabilities",
        "credential theft",
        "identity theft",
        "supply-chain attack",
        "supply chain attack",
    ])

    gaming_subject = _tp_any(title, [
        "video game",
        "video games",
        "gameplay",
        "game studio",
        "game developer",
        "game publisher",
        "game release",
        "game launch",
        "game update",
        "gaming console",
        "playstation",
        "xbox",
        "nintendo",
        "steam deck",
        "fortnite",
        "roblox",
        "resident evil",
        "final fantasy",
        "world of warcraft",
        "esports",
    ])

    hardware_subject = _tp_any(title, [
        "gpu",
        "cpu",
        "processor",
        "graphics card",
        "semiconductor",
        "chip",
        "ssd",
        "nand",
        "dram",
        "memory chip",
        "monitor",
        "display panel",
        "oled display",
        "motherboard",
        "laptop",
        "smartphone",
        "iphone",
        "ipad",
        "macbook",
        "apple watch",
        "galaxy watch",
        "airpods",
        "headphones",
        "keyboard",
        "mouse",
        "printer",
        "3d printer",
        "nvidia",
        "amd",
        "intel",
        "qualcomm",
        "snapdragon",
        "radeon",
        "geforce",
        "npu",
        "accelerator",
        "lithography",
    ])

    quantum_subject = _tp_any(title, rules["Quantum"])
    space_subject = _tp_any(title, rules["Space"])
    robotics_subject = _tp_any(title, rules["Robotics"])
    linux_subject = _tp_any(title, rules["Linux"])

    # --------------------------------------------------------
    # NON-TECH CONTENT
    # --------------------------------------------------------

    nontech_hit = _tp_any(title, nontech_terms)

    if content_type == "commerce":
        relevance = "REJECT"
        quality_flags.append("COMMERCE_CONTENT")

    elif nontech_hit and max(scores.values()) == 0:
        relevance = "REJECT"
        quality_flags.append("NON_TECH_GENERAL_INTEREST")

    else:
        relevance = "KEEP"

    # --------------------------------------------------------
    # PRIMARY CATEGORY
    # --------------------------------------------------------

    if cyber_event:
        primary = "Cybersecurity"

    elif quantum_subject:
        primary = "Quantum"

    elif space_subject:
        primary = "Space"

    elif robotics_subject:
        primary = "Robotics"

    elif gaming_subject and not hardware_subject:
        primary = "Gaming"

    elif hardware_subject:
        primary = "Hardware"

    elif linux_subject:
        primary = "Linux"

    else:
        positive = {
            k: v for k, v in scores.items()
            if v > 0
        }

        if positive:
            primary = max(
                positive,
                key=lambda k: (
                    positive[k],
                    {
                        "Cybersecurity": 10,
                        "Gaming": 9,
                        "Quantum": 8,
                        "Space": 7,
                        "Robotics": 6,
                        "Hardware": 5,
                        "Linux": 4,
                        "Cloud": 3,
                        "Enterprise": 2,
                        "AI": 1,
                        "Technology": 0,
                    }.get(k, 0)
                )
            )
        else:
            primary = "Technology"
            quality_flags.append("WEAK_TOPIC_EVIDENCE")
            relevance = "REVIEW"

    # --------------------------------------------------------
    # IMPORTANT OVERRIDES
    # --------------------------------------------------------

    # Security incidents involving AI remain Cybersecurity.
    if cyber_event:
        primary = "Cybersecurity"

    # AI data-center infrastructure is Cloud when infrastructure
    # is the actual subject.
    if (
        primary == "AI"
        and _tp_any(title, [
            "ai data center",
            "ai data centers",
            "data center",
            "data centers",
            "cloud infrastructure",
        ])
    ):
        primary = "Cloud"

    # Dreamforce / enterprise software stories should not become
    # Hardware merely because NVIDIA or another hardware company
    # is mentioned.
    if _tp_any(title, [
        "dreamforce",
        "salesforce",
        "servicenow",
        "workday",
        "microsoft 365",
        "office 365",
        "crm",
        "erp",
        "enterprise software",
    ]):
        if not hardware_subject and not cyber_event:
            primary = "Enterprise"

    # --------------------------------------------------------
    # SECONDARY TOPICS
    # --------------------------------------------------------

    secondary = []

    for name, score in sorted(
        scores.items(),
        key=lambda item: item[1],
        reverse=True
    ):
        if name == primary:
            continue

        if score >= 10:
            secondary.append(name)

    # Do not let broad Technology pollute everything.
    if "Technology" in secondary and len(secondary) > 1:
        secondary.remove("Technology")

    # --------------------------------------------------------
    # CONTENT-SPECIFIC QUALITY
    # --------------------------------------------------------

    if content_type == "commerce":
        relevance = "REJECT"

    if relevance == "REJECT":
        confidence = "High"

    else:
        positive_scores = sorted(
            [v for v in scores.values() if v > 0],
            reverse=True
        )

        if not positive_scores:
            confidence = "Low"
            relevance = "REVIEW"

        elif positive_scores[0] >= 20 and (
            len(positive_scores) == 1
            or positive_scores[0] - positive_scores[1] >= 10
        ):
            confidence = "High"

        elif positive_scores[0] >= 10:
            confidence = "Medium"

        else:
            confidence = "Low"
            relevance = "REVIEW"

    return {
        "category": primary,
        "subcategory": primary,
        "secondary_topics": secondary[:4],
        "content_type": content_type,
        "relevance": relevance,
        "confidence": confidence,
        "quality_flags": quality_flags,
    }



# PHASE3_EDITORIAL_LAYER
def classify_article(x):
    """
    Phase 3 editorial layer.

    Keeps the Phase 2 classifier as the base classifier and applies
    high-confidence editorial corrections for:
      - gaming vs generic technology
      - entertainment/general-interest rejection
      - shopping/buying content
      - cybersecurity event priority
    """

    result = classify_article_base(x)

    title = str(x.get("title", "") or "")
    description = str(x.get("description", "") or "")

    text = f"{title} {description}".lower()
    title_l = title.lower()

    # ------------------------------------------------------------
    # PHASE 4 EDITORIAL QUALITY GATE
    # ------------------------------------------------------------

    # Obvious commerce / affiliate / shopping content.
    commerce_patterns = [
        "promo code", "promo codes",
        "coupon code", "coupon codes",
        "discount code", "discount codes",
        "coupon", "coupons",
        "promo:", "promos:",
        "deals", "deal:",
        "sale:",
        "save up to", "percent off",
        "% off",
        "prime day deals",
        "black friday deals",
        "cyber monday deals",
        "best deals",
        "best buys",
        "what to buy",
        "buying guide",
        "shopping guide",
        "gift guide",
        "amazon prime perks"
    ]

    # General entertainment / lifestyle content.
    entertainment_patterns = [
        "box office",
        "forgotten box-office",
        "comic strip",
        "comic strips",
        "celebrity",
        "tv show",
        "tv series",
        "streaming hit",
        "streaming sleeper",
        "movie review",
        "movie sequel",
        "movie prequel"
    ]

    # General-interest subjects that are outside the TechPulse scope.
    general_interest_patterns = [
        "gifts for bird lovers",
        "brain that put our brain to sleep",
        "cells that put our brain to sleep",
        "iv drips",
        "detoxification",
        "wellness clinic",
        "el niño",
        "summer in parts of the us"
    ]

    # Political / policy subjects without a direct technology angle.
    # This is an editorial scope filter, not a political assessment.
    political_patterns = [
        "senate race",
        "political race",
        "rfk jr",
        "reparations under",
        "epa immediately sued",
        "climate rules"
    ]

    strong_technology_patterns = [
        "artificial intelligence",
        " ai ",
        "machine learning",
        "large language model",
        "language model",
        "generative ai",
        "cybersecurity",
        "cyber attack",
        "cyberattack",
        "malware",
        "ransomware",
        "hacker",
        "data breach",
        "software",
        "hardware",
        "cloud",
        "data center",
        "datacenter",
        "computer",
        "technology",
        "semiconductor",
        "chip",
        "processor",
        "gpu",
        "linux",
        "open source"
    ]

    gaming_patterns = [
        "video game",
        "video games",
        "game update",
        "gameplay",
        "pc gaming",
        "console",
        "playstation",
        "xbox",
        "steam",
        "steam deck",
        "nintendo",
        "game boy",
        "gameboy",
        "indie game",
        "indie games",
        "gaming",
        "gamer",
        "game developer",
        "game developers",
        "game studio",
        "game studios",
        "drm",
        "anti-tamper"
    ]

    def phase4_reject(reason, content_type="general_interest"):
        result["relevance"] = "REJECT"
        result["content_type"] = content_type
        result["confidence"] = "High"
        flags = list(result.get("quality_flags", []) or [])
        if reason not in flags:
            flags.append(reason)
        result["quality_flags"] = flags
        return result

    # Commerce always gets rejected.
    is_commerce_content = any(term in text for term in commerce_patterns)

    if is_commerce_content:
        return phase4_reject("COMMERCE_CONTENT", "commerce")

    # Entertainment is rejected unless it is clearly gaming.
    has_gaming_topic = any(term in text for term in gaming_patterns)

    if any(term in text for term in entertainment_patterns) and not has_gaming_topic:
        return phase4_reject("GENERAL_ENTERTAINMENT", "entertainment")

    # General-interest content.
    if any(term in text for term in general_interest_patterns):
        return phase4_reject("OUTSIDE_TECH_SCOPE", "general_interest")

    # Political/policy content without a strong technology subject.
    if any(term in text for term in political_patterns):
        tech_context = any(term in text for term in strong_technology_patterns)
        if not tech_context:
            return phase4_reject("POLICY_OUTSIDE_TECH_SCOPE", "general_interest")

    # Obvious gaming correction.
    if has_gaming_topic:
        result["category"] = "Gaming"

        secondary = list(result.get("secondary_topics", []) or [])

        if "Gaming" not in secondary:
            secondary.insert(0, "Gaming")

        if any(term in text for term in [
            "game boy",
            "gameboy",
            "handheld",
            "gaming monitor",
            "gaming pc",
            "gaming laptop",
            "steam deck"
        ]):
            if "Hardware" not in secondary:
                secondary.append("Hardware")

        result["secondary_topics"] = list(dict.fromkeys(
            x for x in secondary if x != "Technology"
        ))

    # Commerce is an absolute editorial rejection.
    # Keep this flag available so later Phase 3 rules cannot
    # accidentally turn shopping/deal content back into KEEP/REVIEW.
    if is_commerce_content:
        return phase4_reject("COMMERCE_CONTENT", "commerce")


    # ------------------------------------------------------------
    # Existing Phase 3 logic continues below.
    # ------------------------------------------------------------

    def has_any(terms):
        return any(t in text for t in terms)

    def title_has_any(terms):
        return any(t in title_l for t in terms)

    # ------------------------------------------------------------
    # 1. Strong cybersecurity event priority
    # ------------------------------------------------------------
    cyber_incident = [
        "hacked", "hack", "hacking", "breach", "breached",
        "ransomware", "malware", "phishing", "cyberattack",
        "cyber attack", "data leak", "data breach",
        "stolen data", "credential theft", "exploit",
        "exploited", "vulnerability", "zero-day", "zero day",
        "botnet", "ddos", "distributed denial",
        "cyber espionage", "security flaw", "security incident",
        "infected", "compromised", "attackers", "threat actors"
    ]

    if title_has_any(cyber_incident):
        result["category"] = "Cybersecurity"

        secondary = list(result.get("secondary_topics", []) or [])
        if "Cybersecurity" in secondary:
            secondary.remove("Cybersecurity")

        if has_any([
            "ai ", " ai", "artificial intelligence",
            "machine learning", "gemini", "chatgpt",
            "claude", "copilot", "ai agent"
        ]):
            if "AI" not in secondary:
                secondary.append("AI")

        result["secondary_topics"] = secondary
        result["relevance"] = "KEEP"
        result["confidence"] = "High"
        result["classification_confidence"] = "High"
        result["quality_flags"] = list(
            dict.fromkeys(
                list(result.get("quality_flags", []) or [])
                + ["CYBER_EVENT_PRIORITY"]
            )
        )

        return result

    # ------------------------------------------------------------
    # 2. Strong gaming subject signals
    # ------------------------------------------------------------
    gaming_terms = [
        "video game", "video games", "gaming",
        "game update", "game patch", "game release",
        "gameplay", "playstation", "xbox", "nintendo",
        "steam deck", "steam", "ps5", "ps4",
        "xbox series", "switch 2", "switch",
        "elden ring", "minecraft", "fortnite",
        "call of duty", "grand theft auto", "gta",
        "wolverine game", "rpg", "jrpg",
        "game studio", "game developer", "game developers",
        "game publisher", "esports"
    ]

    gaming_signal = title_has_any(gaming_terms)

    # Entertainment titles should not become Gaming merely because
    # they contain a franchise/character name.
    entertainment_terms = [
        "movie", "movies", "film", "films",
        "live-action movie", "live action movie",
        "tv show", "tv series", "television series",
        "streaming hit", "box office",
        "movie review", "film review",
        "actor", "actress", "producer",
        "hollywood", "celebrity",
        "anime", "comic book", "comics"
    ]

    entertainment_signal = title_has_any(entertainment_terms)

    # If the title clearly describes a game, keep it as Gaming.
    # If it clearly describes a movie/TV/entertainment story,
    # do not allow a broad Technology fallback.
    if gaming_signal and not entertainment_signal:
        result["category"] = "Gaming"
        result["subcategory"] = "Gaming"
        result["relevance"] = "KEEP"
        result["confidence"] = "High"
        result["classification_confidence"] = "High"

        secondary = list(result.get("secondary_topics", []) or [])
        secondary = [v for v in secondary if v != "Technology"]
        result["secondary_topics"] = secondary

        flags = list(result.get("quality_flags", []) or [])
        if "GAMING_SUBJECT_PRIORITY" not in flags:
            flags.append("GAMING_SUBJECT_PRIORITY")
        result["quality_flags"] = flags

        return result

    if entertainment_signal and not gaming_signal:
        result["relevance"] = "REJECT"
        result["content_type"] = "entertainment"
        result["confidence"] = "High"
        result["classification_confidence"] = "High"

        flags = list(result.get("quality_flags", []) or [])
        if "GENERAL_ENTERTAINMENT" not in flags:
            flags.append("GENERAL_ENTERTAINMENT")
        result["quality_flags"] = flags

        return result

    # ------------------------------------------------------------
    # 3. Strong non-tech/general-interest rejection
    # ------------------------------------------------------------
    general_interest = [
        "recipe", "restaurant", "restaurants",
        "fashion", "gift ideas", "gift guide",
        "celebrity", "celebrity news",
        "box office", "movie review",
        "best movies", "movie trailer",
        "travel", "vacation",
        "sports scores", "sports news",
        "real housewives", "reality tv"
    ]

    if title_has_any(general_interest):
        result["relevance"] = "REJECT"
        result["content_type"] = "general_interest"
        result["confidence"] = "High"
        result["classification_confidence"] = "High"

        flags = list(result.get("quality_flags", []) or [])
        if "GENERAL_INTEREST" not in flags:
            flags.append("GENERAL_INTEREST")
        result["quality_flags"] = flags

        return result

    # ------------------------------------------------------------
    # 4. Shopping / buying / deals should not be treated as normal
    #    technology news.
    # ------------------------------------------------------------
    commerce_terms = [
        "promo code", "coupon", "discount code",
        "best deals", "best deal",
        "deal of the day", "deals",
        "best buys", "best buy",
        "what to buy", "buying guide",
        "shopping guide", "best headphones to buy",
        "best laptops to buy", "best monitors to buy",
        "best phones to buy", "best gadgets to buy",
        "save $", "save up to",
        "black friday", "cyber monday",
        "prime day"
    ]

    if title_has_any(commerce_terms):
        result["relevance"] = "REJECT"
        result["content_type"] = "commerce"
        result["confidence"] = "High"
        result["classification_confidence"] = "High"

        flags = list(result.get("quality_flags", []) or [])
        if "COMMERCE_CONTENT" not in flags:
            flags.append("COMMERCE_CONTENT")
        result["quality_flags"] = flags

        return result

    # ------------------------------------------------------------
    # 5. Consumer reviews should remain REVIEW rather than being
    #    promoted to normal news.
    # ------------------------------------------------------------
    review_terms = [
        "review:", "review -", "review —",
        "hands-on review", "first look",
        "pros and cons", "tested",
        "we tested", "our review",
        "performance review"
    ]

    if title_has_any(review_terms):
        result["relevance"] = "REVIEW"
        result["content_type"] = "review"

    # FINAL EDITORIAL COMMERCE OVERRIDE
    # Commerce/shopping content must never reach news.json.
    final_commerce_patterns = [
        "promo code",
        "promo codes",
        "coupon",
        "coupons",
        "discount code",
        "discount codes",
        "prime day deals",
        "black friday deals",
        "cyber monday deals",
        "best deals",
        "best buys",
        "cheapest",
        "buying guide",
        "shopping guide",
        "gift guide",
        "amazon prime perks",
        "percent off",
        "% off",
        "save up to",
    ]

    if any(term in text for term in final_commerce_patterns):
        result["relevance"] = "REJECT"
        result["content_type"] = "commerce"
        result["confidence"] = "High"
        result["classification_confidence"] = "High"
        result["quality_flags"] = list(dict.fromkeys(
            list(result.get("quality_flags", []) or [])
            + ["COMMERCE_CONTENT"]
        ))
        return result

    return result


def category(x):
    """
    Backward-compatible category wrapper.

    Existing TechPulse code expects category(x) to return a string.
    The richer classification is available through classify_article().
    """
    return classify_article(x)["category"]

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
        classification = classify_article(x)

        if classification["relevance"] == "REJECT":
            continue

        x["category"] = classification["category"]
        x["subcategory"] = classification["subcategory"]
        x["secondary_topics"] = classification["secondary_topics"]
        x["content_type"] = classification["content_type"]
        x["relevance"] = classification["relevance"]
        x["classification_confidence"] = classification["confidence"]
        x["quality_flags"] = classification["quality_flags"]

        clean_items.append(x)
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
        stories.append({'id':sid,'cluster_id':f'CL-{i:04d}','title':p['title'],'summary':p['description'] or 'A technology development has been reported. Open the original source for full context.','why_it_matters':'The development may affect the relevant technology, users, businesses, or industry direction. Review the evidence and original reporting for context.','what_changes':'No additional practical change is asserted beyond the available source evidence.','whats_next':'Watch for official statements, independent confirmation, and subsequent updates.','category':p['category'],
        'subcategory':p.get('subcategory',p['category']),
        'secondary_topics':p.get('secondary_topics',[]),
        'content_type':p.get('content_type','news'),
        'relevance':p.get('relevance','KEEP'),
        'classification_confidence':p.get('classification_confidence','Medium'),
        'quality_flags':p.get('quality_flags',[]),
        'published_at':p['published_at'],'source':p['source'],'source_type':p['source_type'],'url':p['url'],'confidence':conf,'importance':imp,'freshness':fresh,'momentum':mom,'verification_status':status,'status':'NEW' if status=='VERIFIED' else 'DEVELOPING','tags':sources[:5],'corroborating_sources':[{'source':x['source'],'title':x['title'],'url':x['url']} for x in c[1:5]]})
    # Recent stories first; existing score is only a tie-breaker.
    stories.sort(
        key=lambda x: (
            x.get('published_at', ''),
            x.get('importance', 0) + x.get('freshness', 0) + x.get('confidence', 0) + x.get('momentum', 0)
        ),
        reverse=True
    )
    if MAX > 0:
        stories=stories[:MAX]

    # Apply editorial moderation decisions from admin/moderation.json.
    # KEEP   -> publish normally
    # REVIEW -> publish and mark for editorial review
    # HIDE   -> exclude from public news.json
    moderation_file = ROOT / 'admin' / 'moderation.json'
    moderation = {}

    if moderation_file.exists():
        try:
            moderation_data = json.loads(
                moderation_file.read_text(encoding='utf-8')
            )
            moderation = moderation_data.get('decisions', {})
            if not isinstance(moderation, dict):
                moderation = {}
        except Exception as e:
            print(
                f'[WARN] Unable to read moderation.json: {e}',
                file=sys.stderr
            )
            moderation = {}

    moderated_stories = []

    for x in stories:
        decision = moderation.get(x.get('id'))

        if not isinstance(decision, dict):
            moderated_stories.append(x)
            continue

        action = str(
            decision.get('action', '')
        ).strip().lower()

        reason = str(
            decision.get('reason', '')
        ).strip()

        if action == 'hide':
            print(
                f'[MODERATION] HIDDEN: {x.get("id")} '
                f'| {x.get("title", "")}'
            )
            continue

        if action == 'review':
            x['editorial_status'] = 'REVIEW'
            if reason:
                x['editorial_reason'] = reason

        elif action == 'keep':
            x['editorial_status'] = 'KEEP'
            if reason:
                x['editorial_reason'] = reason

        moderated_stories.append(x)

    stories = moderated_stories

    if not stories:
        raise RuntimeError(
            'No valid stories remain after moderation; '
            'last-known-good news.json preserved.'
        )

    for i,x in enumerate(stories,1):
        x['rank']=i

    data={
        'schema_version':1,
        'product':'TechPulse',
        'generated_at':datetime.now(timezone.utc).isoformat(),
        'article_count':len(stories),
        'source_count':len(set(x['source'] for x in stories)),
        'source_health':health,
        'articles':stories
    }

    validate(data)
    atomic(data)
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
