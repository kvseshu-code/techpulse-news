#!/usr/bin/env python3
"""
TechPulse News Fetcher — fetch_news.py (Phase 2 Corrected Engine)
Guarantees presence of Phase 2 NLP, impact scoring, feed health, and keywords.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import sys
import time
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Dict, Tuple

import feedparser
import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field, ValidationError
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ============================================================
# CONFIGURATION
# ============================================================

OUTPUT_FILE = Path("news.json")
MAX_ARTICLES = 100
MAX_AGE_DAYS = 14
REQUEST_TIMEOUT = 20

USER_AGENT = "TechPulseNewsBot/2.0 (Resilient RSS Engine)"

STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are",
    "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", "by",
    "can", "did", "do", "does", "doing", "for", "from", "further", "had", "has", "have", "having",
    "he", "her", "here", "him", "his", "how", "if", "in", "into", "is", "it", "its", "me", "more",
    "most", "my", "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", "our",
    "out", "over", "own", "same", "she", "should", "so", "some", "such", "than", "that", "the",
    "their", "them", "then", "there", "these", "they", "this", "those", "through", "to", "too",
    "under", "until", "up", "very", "was", "we", "were", "what", "when", "where", "which", "while",
    "who", "whom", "why", "will", "with", "you", "your", "view", "downloadsview", "release", "notes"
}

# ============================================================
# PYDANTIC SCHEMAS (Strict Phase 2 Enforcer)
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
    keywords: List[str] = Field(default_factory=list)
    impactScore: float = 0.0
    relatedCount: int = 1
    sourceCount: int = 1
    trending: bool = False

class FeedHealthSchema(BaseModel):
    name: str
    status: str
    articlesFetched: int
    error: str = ""

class NewsOutputSchema(BaseModel):
    success: bool = True
    updatedAt: str
    total: int
    featured: List[str]
    technologyCount: int
    gamingCount: int
    trendingTopics: List[str] = Field(default_factory=list)
    feedHealth: List[FeedHealthSchema] = Field(default_factory=list)
    articles: List[ArticleSchema]

# ============================================================
# FEEDS & CATEGORIES
# ============================================================

FEEDS = [
    {"name": "Google Technology", "url": "https://blog.google/feed/", "mainCategory": "Technology", "category": "Artificial Intelligence", "weight": 10},
    {"name": "Apple Software Releases", "url": "https://developer.apple.com/news/releases/rss/releases.rss", "mainCategory": "Technology", "category": "Software & Applications", "weight": 10},
    {"name": "Apple Newsroom", "url": "https://www.apple.com/newsroom/rss-feed.rss", "mainCategory": "Technology", "category": "Hardware & Devices", "weight": 10},
    {"name": "AWS What's New", "url": "https://aws.amazon.com/about-aws/whats-new/recent/feed/", "mainCategory": "Technology", "category": "Cloud & Infrastructure", "weight": 10},
    {"name": "NVIDIA", "url": "https://nvidia.com/en-us/about-nvidia/rss/", "mainCategory": "Technology", "category": "Hardware & Devices", "weight": 9},
    {"name": "Cisco Newsroom", "url": "https://newsroom.cisco.com/c/r/newsroom/en/us/rss-feeds.html", "mainCategory": "Technology", "category": "Enterprise Technology", "weight": 9},
    {"name": "Windows Blog", "url": "https://blogs.windows.com/feed/", "mainCategory": "Technology", "category": "Software & Applications", "weight": 9},
    {"name": "CISA", "url": "https://www.cisa.gov/cybersecurity-advisories/all.xml", "mainCategory": "Technology", "category": "Cybersecurity", "weight": 10},
    {"name": "Nintendo", "url": "https://www.nintendo.com/us/whatsnew/rss/", "mainCategory": "Gaming", "category": "Game Releases", "weight": 10},
    {"name": "Xbox Wire", "url": "https://news.xbox.com/en-us/feed/", "mainCategory": "Gaming", "category": "Console Gaming", "weight": 10},
    {"name": "PlayStation Blog", "url": "https://blog.playstation.com/feed/", "mainCategory": "Gaming", "category": "Console Gaming", "weight": 10},
]

CATEGORY_RULES = [
    ("Cybersecurity", ["cybersecurity", "cyber security", "vulnerability", "cve", "malware", "ransomware", "zero-day", "exploit", "breach"]),
    ("Artificial Intelligence", ["artificial intelligence", "ai", "machine learning", "generative ai", "llm", "gemini", "chatbot", "deep learning"]),
    ("Cloud & Infrastructure", ["cloud", "aws", "azure", "google cloud", "kubernetes", "container", "server", "data center"]),
    ("Smartphones & Mobile", ["smartphone", "iphone", "android", "mobile phone", "tablet", "ipad"]),
    ("Software & Applications", ["software", "app", "windows", "macos", "ios", "operating system", "developer", "beta"]),
    ("Hardware & Devices", ["hardware", "processor", "cpu", "gpu", "chip", "laptop", "desktop"]),
    ("Console Gaming", ["playstation", "xbox", "nintendo", "console", "switch"]),
    ("PC Gaming", ["pc gaming", "steam", "pc game"]),
    ("Game Releases", ["game release", "launches", "released", "release date"]),
]

# ============================================================
# UTILITIES & NLP
# ============================================================

def create_resilient_session() -> requests.Session:
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update({"User-Agent": USER_AGENT})
    return session

SESSION = create_resilient_session()

def tokenize(text: str) -> List[str]:
    clean = re.sub(r"[^a-z0-9\s]", " ", text.lower())
    return [w for w in clean.split() if len(w) > 2 and w not in STOPWORDS]

def extract_keywords(title: str, description: str, top_n: int = 4) -> List[str]:
    combined = title + " " + description
    tokens = tokenize(combined)
    counts = Counter(tokens)
    return [word.capitalize() for word, _ in counts.most_common(top_n)]

# ============================================================
# CORE PIPELINE
# ============================================================

def fetch_feed(config: dict) -> Tuple[list[dict], FeedHealthSchema]:
    name, url = config["name"], config["url"]
    print(f"Fetching: {name}")
    try:
        response = SESSION.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        feed = feedparser.parse(response.content)
        entries = getattr(feed, "entries", [])

        articles = []
        cutoff = datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)

        for entry in entries:
            title = re.sub(r"\s+", " ", BeautifulSoup(entry.get("title", ""), "html.parser").get_text()).strip()
            link = entry.get("link", "").strip()
            if not title or not link:
                continue

            pub_dt = datetime.now(timezone.utc)
            if entry.get("published_parsed"):
                pub_dt = datetime.fromtimestamp(time.mktime(entry["published_parsed"]), tz=timezone.utc)

            if pub_dt < cutoff:
                continue

            desc_raw = BeautifulSoup(entry.get("summary", ""), "html.parser").get_text()
            desc = re.sub(r"\s+", " ", desc_raw).strip()
            if not desc or "View downloadsView release notes" in desc:
                desc = f"Latest release update for {title}."

            cat = config["category"]
            for c_name, kws in CATEGORY_RULES:
                if any(k in (title + " " + desc).lower() for k in kws):
                    cat = c_name
                    break

            raw_id = hashlib.sha256((title.lower() + "|" + link.lower()).encode()).hexdigest()[:20]

            articles.append({
                "id": f"techpulse-{raw_id}",
                "title": title,
                "description": desc[:280],
                "url": link,
                "image": "",
                "category": cat,
                "mainCategory": config["mainCategory"],
                "source": name,
                "published": pub_dt.isoformat(),
                "keywords": extract_keywords(title, desc),
                "_weight": config.get("weight", 5)
            })

        return articles, FeedHealthSchema(name=name, status="Healthy", articlesFetched=len(articles))

    except Exception as exc:
        print(f"  [WARNING] Feed failed: {name} -> {exc}")
        return [], FeedHealthSchema(name=name, status="Degraded", articlesFetched=0, error=str(exc))

def main() -> int:
    print("============================================================")
    print("Running Phase 2 Engine via fetch_news.py")
    print("============================================================")

    all_articles, health_reports = [], []

    for config in FEEDS:
        items, health = fetch_feed(config)
        health_reports.append(health)
        all_articles.extend(items)

    if not all_articles:
        print("[ERROR] No articles fetched.")
        return 1

    # Simple Deduplication & Scoring Enforcer
    unique_articles = {}
    for a in all_articles:
        if a["id"] not in unique_articles:
            unique_articles[a["id"]] = a

    processed = list(unique_articles.values())

    all_keywords = []
    for a in processed:
        pub_dt = datetime.fromisoformat(a["published"])
        age_hours = max(0, (datetime.now(timezone.utc) - pub_dt).total_seconds() / 3600)
        a["impactScore"] = round(max(0, 100 - (age_hours * 2)) + (a["_weight"] * 2), 2)
        a["storyId"] = f"story-{a['id'][10:22]}"
        a["relatedCount"] = 1
        a["sourceCount"] = 1
        a["trending"] = a["impactScore"] > 80.0
        all_keywords.extend(a["keywords"])

    processed.sort(key=lambda x: x["impactScore"], reverse=True)
    top_topics = [kw for kw, _ in Counter(all_keywords).most_common(8)]

    clean_articles = []
    for a in processed[:MAX_ARTICLES]:
        clean_articles.append({
            "id": a["id"],
            "title": a["title"],
            "description": a["description"],
            "url": a["url"],
            "image": a["image"],
            "category": a["category"],
            "mainCategory": a["mainCategory"],
            "source": a["source"],
            "published": a["published"],
            "storyId": a["storyId"],
            "keywords": a["keywords"],
            "impactScore": a["impactScore"],
            "relatedCount": a["relatedCount"],
            "sourceCount": a["sourceCount"],
            "trending": a["trending"]
        })

    payload = {
        "success": True,
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "total": len(clean_articles),
        "featured": [x["id"] for x in clean_articles[:6]],
        "technologyCount": len([x for x in clean_articles if x["mainCategory"] == "Technology"]),
        "gamingCount": len([x for x in clean_articles if x["mainCategory"] == "Gaming"]),
        "trendingTopics": top_topics,
        "feedHealth": [h.model_dump() for h in health_reports],
        "articles": clean_articles
    }

    try:
        validated = NewsOutputSchema(**payload)
    except ValidationError as ve:
        print(f"[FATAL] Validation failed: {ve}")
        return 1

    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(validated.model_dump(), f, ensure_ascii=False, indent=2)

    print("\n[SUCCESS] news.json updated with Phase 2 fields.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
