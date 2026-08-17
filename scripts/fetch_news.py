#!/usr/bin/env python3
"""
TechPulse News Fetcher — Phase 1 Resilience Upgrade
Preserves all original features while adding HTTP retries, 
Pydantic validation, and atomic JSON persistence.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse
from difflib import SequenceMatcher

import feedparser
import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, HttpUrl, Field, ValidationError
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ============================================================
# CONFIGURATION & CONSTANTS
# ============================================================

OUTPUT_FILE = Path("news.json")
MAX_ARTICLES = 100
MIN_ARTICLES = 30
MAX_AGE_DAYS = 14
REQUEST_TIMEOUT = 20

USER_AGENT = "TechPulseNewsBot/1.0 (RSS news discovery; contact via repository owner)"

# ============================================================
# PYDANTIC SCHEMAS
# ============================================================

class ArticleSchema(BaseModel):
    id: str
    title: str
    description: str
    url: str
    image: str = ""
    category: str
    mainCategory: str
    source: str
    published: str
    storyId: str
    relatedCount: int = 1
    sourceCount: int = 1
    trending: bool = False

class NewsOutputSchema(BaseModel):
    success: bool = True
    updatedAt: str
    total: int
    featured: List[str]
    technologyCount: int
    gamingCount: int
    articles: List[ArticleSchema]

# ============================================================
# AUTHORITATIVE & FALLBACK FEEDS
# ============================================================

FEEDS = [
    {"name": "Google Technology", "url": "https://blog.google/feed/", "mainCategory": "Technology", "category": "Artificial Intelligence", "weight": 10},
    {"name": "Apple Newsroom", "url": "https://www.apple.com/newsroom/rss-feed.rss", "mainCategory": "Technology", "category": "Hardware & Devices", "weight": 10},
    {"name": "Apple Developer", "url": "https://developer.apple.com/news/rss/news.rss", "mainCategory": "Technology", "category": "Software & Applications", "weight": 10},
    {"name": "Apple Software Releases", "url": "https://developer.apple.com/news/releases/rss/releases.rss", "mainCategory": "Technology", "category": "Software & Applications", "weight": 10},
    {"name": "AWS What's New", "url": "https://aws.amazon.com/about-aws/whats-new/recent/feed/", "mainCategory": "Technology", "category": "Cloud & Infrastructure", "weight": 10},
    {"name": "NVIDIA", "url": "https://nvidia.com/en-us/about-nvidia/rss/", "mainCategory": "Technology", "category": "Hardware & Devices", "weight": 9},
    {"name": "Cisco Newsroom", "url": "https://newsroom.cisco.com/c/r/newsroom/en/us/rss-feeds.html", "mainCategory": "Technology", "category": "Enterprise Technology", "weight": 9},
    {"name": "Windows Blog", "url": "https://blogs.windows.com/feed/", "mainCategory": "Technology", "category": "Software & Applications", "weight": 9},
    {"name": "Cisco Security", "url": "https://newsroom.cisco.com/c/services/i/servlets/newsroom/rssfeed.json?feed=security", "mainCategory": "Technology", "category": "Cybersecurity", "weight": 9},
    {"name": "CISA", "url": "https://www.cisa.gov/cybersecurity-advisories/all.xml", "mainCategory": "Technology", "category": "Cybersecurity", "weight": 10},
    {"name": "NASA", "url": "https://www.nasa.gov/rss/dyn/breaking_news.rss", "mainCategory": "Technology", "category": "Science & Innovation", "weight": 9},
    {"name": "European Space Agency", "url": "https://www.esa.int/rssfeed/TopNews", "mainCategory": "Technology", "category": "Science & Innovation", "weight": 9},
    {"name": "Nintendo", "url": "https://www.nintendo.com/us/whatsnew/rss/", "mainCategory": "Gaming", "category": "Game Releases", "weight": 10},
    {"name": "Xbox Wire", "url": "https://news.xbox.com/en-us/feed/", "mainCategory": "Gaming", "category": "Console Gaming", "weight": 10},
    {"name": "PlayStation Blog", "url": "https://blog.playstation.com/feed/", "mainCategory": "Gaming", "category": "Console Gaming", "weight": 10},
]

FALLBACK_FEEDS = [
    {"name": "BBC Technology", "url": "https://feeds.bbci.co.uk/news/technology/rss.xml", "mainCategory": "Technology", "category": "Emerging Technology", "weight": 7},
    {"name": "Ars Technica Technology", "url": "https://feeds.arstechnica.com/arstechnica/technology-lab", "mainCategory": "Technology", "category": "Emerging Technology", "weight": 7},
]

ALL_FEEDS = FEEDS + FALLBACK_FEEDS

CATEGORY_RULES = [
    ("Cybersecurity", ["cybersecurity", "cyber security", "security", "vulnerability", "cve", "malware", "ransomware", "phishing", "zero-day", "zero day", "exploit", "breach"]),
    ("Artificial Intelligence", ["artificial intelligence", "ai", "machine learning", "generative ai", "large language model", "llm", "gemini", "chatbot", "deep learning", "neural network"]),
    ("Cloud & Infrastructure", ["cloud", "aws", "azure", "google cloud", "kubernetes", "container", "server", "infrastructure", "data center", "datacenter"]),
    ("Smartphones & Mobile", ["smartphone", "iphone", "android", "mobile phone", "mobile", "tablet", "ipad"]),
    ("Software & Applications", ["software", "application", "app", "windows", "macos", "ios", "developer", "release", "update", "operating system"]),
    ("Hardware & Devices", ["hardware", "processor", "cpu", "gpu", "chip", "device", "laptop", "desktop", "memory", "storage"]),
    ("PC Gaming", ["pc gaming", "steam", "pc game", "pc games"]),
    ("Console Gaming", ["playstation", "xbox", "nintendo", "console", "switch"]),
    ("Mobile Gaming", ["mobile gaming", "mobile game", "android game", "ios game"]),
    ("Game Releases", ["game release", "launches", "released", "release date", "coming to", "available now"]),
    ("Gaming Hardware", ["gaming hardware", "gaming monitor", "gaming laptop", "gaming pc", "controller", "headset", "graphics card"]),
    ("Esports", ["esports", "e-sports", "tournament", "championship"]),
]

# ============================================================
# HTTP SESSION WITH AUTOMATIC RETRIES
# ============================================================

def create_resilient_session() -> requests.Session:
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        raise_on_status=False
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, text/html;q=0.8, */*;q=0.5",
    })
    return session

SESSION = create_resilient_session()

# ============================================================
# HELPER UTILITIES
# ============================================================

def now_utc() -> datetime:
    return datetime.now(timezone.utc)

def clean_html(value: str) -> str:
    if not value:
        return ""
    value = html.unescape(str(value))
    soup = BeautifulSoup(value, "html.parser")
    text = soup.get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()

def shorten_text(value: str, maximum: int = 280) -> str:
    text = clean_html(value)
    if not text or len(text) <= maximum:
        return text
    shortened = text[:maximum]
    if " " in shortened:
        shortened = shortened.rsplit(" ", 1)[0]
    return shortened.rstrip(" .,;:") + "…"

def normalize_title(title: str) -> str:
    value = title.lower()
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    return re.sub(r"\s+", " ", value).strip()

def canonical_url(url: str) -> str:
    if not url:
        return ""
    try:
        parsed = urlparse(url)
        if parsed.scheme in ("http", "https") and parsed.netloc:
            return url.strip()
    except Exception:
        pass
    return ""

def parse_date(entry) -> datetime:
    candidates = [entry.get("published_parsed"), entry.get("updated_parsed"), entry.get("created_parsed")]
    for val in candidates:
        if val:
            try:
                return datetime.fromtimestamp(time.mktime(val), tz=timezone.utc)
            except Exception:
                pass
    for key in ("published", "updated", "created", "date"):
        raw = entry.get(key)
        if raw:
            try:
                parsed = feedparser._parse_date(raw)
                if parsed:
                    return datetime.fromtimestamp(time.mktime(parsed), tz=timezone.utc)
            except Exception:
                pass
    return now_utc()

def detect_category(title: str, description: str, default_category: str) -> str:
    text = (title + " " + description).lower()
    for category, keywords in CATEGORY_RULES:
        for keyword in keywords:
            if keyword in text:
                return category
    return default_category

def make_id(title: str, url: str) -> str:
    raw = normalize_title(title) + "|" + url.lower()
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]
    return "techpulse-" + digest

def similarity(title_a: str, title_b: str) -> float:
    a, b = normalize_title(title_a), normalize_title(title_b)
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()

def extract_description(entry) -> str:
    values = [entry.get("summary", ""), entry.get("description", "")]
    content = entry.get("content")
    if content and isinstance(content, list):
        for item in content:
            if isinstance(item, dict):
                values.append(item.get("value", ""))
    for value in values:
        text = shorten_text(value, 280)
        if text:
            return text
    return "Latest technology and gaming news from an authoritative source."

def extract_url(entry) -> str:
    link = entry.get("link", "")
    if link:
        return canonical_url(link)
    links = entry.get("links", [])
    if isinstance(links, list):
        for item in links:
            if isinstance(item, dict):
                url = canonical_url(item.get("href", ""))
                if url:
                    return url
    return ""

# ============================================================
# FETCHING & PROCESSING ENGINE
# ============================================================

def fetch_feed(config: dict) -> list[dict]:
    name, url = config["name"], config["url"]
    print(f"Fetching: {name}")
    try:
        response = SESSION.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        feed = feedparser.parse(response.content)
        entries = getattr(feed, "entries", [])
        print(f"  Entries fetched: {len(entries)}")

        articles = []
        cutoff = now_utc() - timedelta(days=MAX_AGE_DAYS)

        for entry in entries:
            title = clean_html(entry.get("title", ""))
            url_val = extract_url(entry)
            if not title or not url_val:
                continue

            pub_dt = parse_date(entry)
            if pub_dt < cutoff:
                continue

            desc = extract_description(entry)
            category = detect_category(title, desc, config["category"])

            articles.append({
                "id": make_id(title, url_val),
                "title": title,
                "description": desc,
                "url": url_val,
                "image": "",
                "category": category,
                "mainCategory": config["mainCategory"],
                "source": name,
                "published": pub_dt.isoformat(),
                "_weight": config.get("weight", 5),
            })
        return articles
    except Exception as exc:
        print(f"  [WARNING] Feed failed: {name} -> {exc}")
        return []

def deduplicate(articles: list[dict]) -> list[dict]:
    result, exact_ids = [], set()
    for article in sorted(articles, key=lambda x: x["published"], reverse=True):
        if article["id"] in exact_ids:
            continue
        exact_ids.add(article["id"])

        duplicate = False
        for existing in result:
            if article["mainCategory"] != existing["mainCategory"]:
                continue
            if similarity(article["title"], existing["title"]) >= 0.88:
                duplicate = True
                if article["_weight"] > existing["_weight"]:
                    result.remove(existing)
                    result.append(article)
                break
        if not duplicate:
            result.append(article)
    return result

def apply_story_metadata(articles: list[dict]) -> list[dict]:
    clusters = []
    for article in articles:
        placed = False
        for cluster in clusters:
            if similarity(article["title"], cluster[0]["title"]) >= 0.68:
                cluster.append(article)
                placed = True
                break
        if not placed:
            clusters.append([article])

    cluster_lookup = {}
    for cluster in clusters:
        cluster_id = hashlib.sha256(normalize_title(cluster[0]["title"]).encode("utf-8")).hexdigest()[:12]
        sources = len({item["source"] for item in cluster})
        for item in cluster:
            cluster_lookup[item["id"]] = {
                "storyId": f"story-{cluster_id}",
                "relatedCount": len(cluster),
                "sourceCount": sources,
                "trending": len(cluster) >= 2 or sources >= 2,
            }

    for article in articles:
        meta = cluster_lookup.get(article["id"], {})
        article["storyId"] = meta.get("storyId", f"story-{article['id']}")
        article["relatedCount"] = meta.get("relatedCount", 1)
        article["sourceCount"] = meta.get("sourceCount", 1)
        article["trending"] = meta.get("trending", False)

    return articles

def rank_score(article: dict) -> float:
    try:
        published = datetime.fromisoformat(article["published"].replace("Z", "+00:00"))
    except Exception:
        published = now_utc()
    age_hours = max(0, (now_utc() - published).total_seconds() / 3600)
    
    recency = max(0, 48 - age_hours)
    authority = article.get("_weight", 5) * 3
    related = article.get("relatedCount", 1) * 8
    trending = 20 if article.get("trending", False) else 0
    return recency + authority + related + trending

def build_output(articles: list[dict]) -> dict:
    articles = apply_story_metadata(articles)
    articles.sort(key=rank_score, reverse=True)

    clean_articles = []
    for article in articles[:MAX_ARTICLES]:
        clean_articles.append({
            "id": article["id"],
            "title": article["title"],
            "description": article["description"],
            "url": article["url"],
            "image": article["image"],
            "category": article["category"],
            "mainCategory": article["mainCategory"],
            "source": article["source"],
            "published": article["published"],
            "storyId": article["storyId"],
            "relatedCount": article["relatedCount"],
            "sourceCount": article["sourceCount"],
            "trending": article["trending"],
        })

    tech_count = len([x for x in clean_articles if x["mainCategory"] == "Technology"])
    gaming_count = len([x for x in clean_articles if x["mainCategory"] == "Gaming"])
    featured = [x["id"] for x in clean_articles[:6]]

    raw_data = {
        "success": True,
        "updatedAt": now_utc().isoformat(),
        "total": len(clean_articles),
        "featured": featured,
        "technologyCount": tech_count,
        "gamingCount": gaming_count,
        "articles": clean_articles,
    }

    # Validate schema using Pydantic
    validated = NewsOutputSchema(**raw_data)
    return validated.model_dump()

# ============================================================
# MAIN EXECUTION
# ============================================================

def main() -> int:
    print("============================================================")
    print("TechPulse Resilient Fetcher (Phase 1 Engine)")
    print("============================================================")

    all_articles = []
    successful_feeds = 0

    for config in ALL_FEEDS:
        items = fetch_feed(config)
        if items:
            successful_feeds += 1
            all_articles.extend(items)

    print(f"\nRaw articles fetched: {len(all_articles)}")
    print(f"Successful feeds: {successful_feeds}/{len(ALL_FEEDS)}")

    if not all_articles:
        print("[ERROR] No valid articles fetched.")
        if OUTPUT_FILE.exists():
            print("Existing news.json preserved.")
            return 0
        return 1

    deduped = deduplicate(all_articles)
    print(f"After deduplication: {len(deduped)}")

    try:
        final_payload = build_output(deduped)
    except ValidationError as ve:
        print(f"[FATAL] Schema validation failed: {ve}")
        return 1

    temp_file = OUTPUT_FILE.with_suffix(".tmp")
    with temp_file.open("w", encoding="utf-8") as f:
        json.dump(final_payload, f, ensure_ascii=False, indent=2)
        f.write("\n")

    # Atomic write replacement
    temp_file.replace(OUTPUT_FILE)

    print("\nnews.json successfully validated and written.")
    print(f"Total: {final_payload['total']} | Tech: {final_payload['technologyCount']} | Gaming: {final_payload['gamingCount']}")
    print("============================================================")
    return 0

if __name__ == "__main__":
    sys.exit(main())
