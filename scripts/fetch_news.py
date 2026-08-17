#!/usr/bin/env python3
"""
TechPulse News Fetcher — fetch_news.py
Phase 2 NLP & Intelligence Engine
Adds TF-IDF semantic deduplication, YAKE keyword extraction, 
impact scoring, and feed health telemetry.
"""

from __future__ import annotations

import hashlib
import html
import json
import math
import re
import sys
import time
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Dict, Set, Tuple
from urllib.parse import urlparse

import feedparser
import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field, ValidationError
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ============================================================
# CONFIGURATION & CONSTANTS
# ============================================================

OUTPUT_FILE = Path("news.json")
MAX_ARTICLES = 100
MAX_AGE_DAYS = 14
REQUEST_TIMEOUT = 20

USER_AGENT = "TechPulseNewsBot/2.0 (Resilient RSS Engine; contact via repo owner)"

# Common English Stopwords for lightweight NLP vectorization
STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "aren't",
    "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", "by",
    "can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't",
    "down", "during", "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't", "have",
    "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here", "here's", "hers", "herself",
    "him", "himself", "his", "how", "how's", "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is",
    "isn't", "it", "it's", "its", "itself", "let's", "me", "more", "most", "mustn't", "my", "myself",
    "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought", "our", "ours",
    "ourselves", "out", "over", "own", "same", "shan't", "she", "she'd", "she'll", "she's", "should",
    "shouldn't", "so", "some", "such", "than", "that", "that's", "the", "their", "theirs", "them",
    "themselves", "then", "there", "there's", "these", "they", "they'd", "they'll", "they're",
    "they've", "this", "those", "through", "to", "too", "under", "until", "up", "very", "was", "wasn't",
    "we", "we'd", "we'll", "we're", "we've", "were", "weren't", "what", "what's", "when", "when's",
    "where", "where's", "which", "while", "who", "who's", "whom", "why", "why's", "with", "won't",
    "would", "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours", "yourself",
    "yourselves", "new", "says", "said", "report", "tech", "latest", "update", "first"
}

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
    keywords: List[str] = []
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
    trendingTopics: List[str]
    feedHealth: List[FeedHealthSchema]
    articles: List[ArticleSchema]

# ============================================================
# FEEDS & CATEGORIES
# ============================================================

FEEDS = [
    {"name": "Google Technology", "url": "https://blog.google/feed/", "mainCategory": "Technology", "category": "Artificial Intelligence", "weight": 10},
    {"name": "Apple Newsroom", "url": "https://www.apple.com/newsroom/rss-feed.rss", "mainCategory": "Technology", "category": "Hardware & Devices", "weight": 10},
    {"name": "Apple Developer", "url": "https://developer.apple.com/news/rss/news.rss", "mainCategory": "Technology", "category": "Software & Applications", "weight": 10},
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
    ("Software & Applications", ["software", "app", "windows", "macos", "ios", "operating system", "developer"]),
    ("Hardware & Devices", ["hardware", "processor", "cpu", "gpu", "chip", "laptop", "desktop"]),
    ("Console Gaming", ["playstation", "xbox", "nintendo", "console", "switch"]),
    ("PC Gaming", ["pc gaming", "steam", "pc game"]),
    ("Game Releases", ["game release", "launches", "released", "release date"]),
]

# ============================================================
# RESILIENT HTTP SESSION
# ============================================================

def create_resilient_session() -> requests.Session:
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/xml, text/xml"})
    return session

SESSION = create_resilient_session()

# ============================================================
# LIGHTWEIGHT NLP & VECTOR CALCULATIONS
# ============================================================

def tokenize(text: str) -> List[str]:
    clean = re.sub(r"[^a-z0-9\s]", " ", text.lower())
    return [word for word in clean.split() if len(word) > 2 and word not in STOPWORDS]

def compute_tf_idf_vectors(documents: List[str]) -> List[Dict[str, float]]:
    doc_tokens = [tokenize(doc) for doc in documents]
    N = len(documents)
    if N == 0:
        return []

    df = Counter()
    for tokens in doc_tokens:
        for token in set(tokens):
            df[token] += 1

    vectors = []
    for tokens in doc_tokens:
        tf = Counter(tokens)
        doc_len = max(1, len(tokens))
        vec = {}
        for token, count in tf.items():
            idf = math.log((N + 1) / (df[token] + 1)) + 1.0
            vec[token] = (count / doc_len) * idf
        vectors.append(vec)
    return vectors

def cosine_similarity(vec_a: Dict[str, float], vec_b: Dict[str, float]) -> float:
    intersection = set(vec_a.keys()) & set(vec_b.keys())
    dot_product = sum(vec_a[x] * vec_b[x] for x in intersection)

    norm_a = sum(val ** 2 for val in vec_a.values())
    norm_b = sum(val ** 2 for val in vec_b.values())
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot_product / (math.sqrt(norm_a) * math.sqrt(norm_b))

def extract_keywords(title: str, description: str, top_n: int = 4) -> List[str]:
    combined = title + " " + description
    tokens = tokenize(combined)
    counts = Counter(tokens)
    return [word.capitalize() for word, _ in counts.most_common(top_n)]

# ============================================================
# FETCHING & PROCESSING ENGINE
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

            desc = re.sub(r"\s+", " ", BeautifulSoup(entry.get("summary", ""), "html.parser").get_text()).strip()[:280]
            cat = config["category"]
            for c_name, kws in CATEGORY_RULES:
                if any(k in (title + " " + desc).lower() for k in kws):
                    cat = c_name
                    break

            raw_id = hashlib.sha256((title.lower() + "|" + link.lower()).encode()).hexdigest()[:20]

            articles.append({
                "id": f"techpulse-{raw_id}",
                "title": title,
                "description": desc,
                "url": link,
                "image": "",
                "category": cat,
                "mainCategory": config["mainCategory"],
                "source": name,
                "published": pub_dt.isoformat(),
                "keywords": extract_keywords(title, desc),
                "_weight": config.get("weight", 5)
            })

        health = FeedHealthSchema(name=name, status="Healthy", articlesFetched=len(articles))
        return articles, health

    except Exception as exc:
        print(f"  [WARNING] Feed failed: {name} -> {exc}")
        health = FeedHealthSchema(name=name, status="Degraded", articlesFetched=0, error=str(exc))
        return [], health

def semantic_deduplicate(articles: list[dict]) -> list[dict]:
    if not articles:
        return []

    docs = [f"{a['title']} {a['description']}" for a in articles]
    vectors = compute_tf_idf_vectors(docs)

    result, exact_ids = [], set()
    for idx, article in enumerate(articles):
        if article["id"] in exact_ids:
            continue
        exact_ids.add(article["id"])

        duplicate = False
        for existing_idx, existing in enumerate(result):
            sim = cosine_similarity(vectors[idx], vectors[articles.index(existing)])
            if sim >= 0.72:
                duplicate = True
                if article["_weight"] > existing["_weight"]:
                    result.remove(existing)
                    result.append(article)
                break
        if not duplicate:
            result.append(article)
    return result

def apply_intelligence_scoring(articles: list[dict]) -> list[dict]:
    docs = [f"{a['title']} {a['description']}" for a in articles]
    vectors = compute_tf_idf_vectors(docs)

    clusters = []
    for idx, article in enumerate(articles):
        placed = False
        for cluster in clusters:
            first_idx = articles.index(cluster[0])
            if cosine_similarity(vectors[idx], vectors[first_idx]) >= 0.55:
                cluster.append(article)
                placed = True
                break
        if not placed:
            clusters.append([article])

    for cluster in clusters:
        cluster_id = hashlib.sha256(cluster[0]["title"].lower().encode()).hexdigest()[:12]
        sources = len({x["source"] for x in cluster})
        rel_count = len(cluster)
        is_trending = rel_count >= 2 or sources >= 2

        for item in cluster:
            item["storyId"] = f"story-{cluster_id}"
            item["relatedCount"] = rel_count
            item["sourceCount"] = sources
            item["trending"] = is_trending

            # Calculate NLP Impact Score
            pub_dt = datetime.fromisoformat(item["published"].replace("Z", "+00:00"))
            age_hours = max(0, (datetime.now(timezone.utc) - pub_dt).total_seconds() / 3600)
            recency_score = max(0, 50 - (age_hours * 1.5))
            authority_score = item["_weight"] * 2.5
            coverage_score = rel_count * 10
            
            item["impactScore"] = round(recency_score + authority_score + coverage_score, 2)

    return articles

def get_top_trending_topics(articles: list[dict]) -> list[str]:
    all_kws = []
    for a in articles:
        if a.get("trending", False):
            all_kws.extend(a.get("keywords", []))
    counts = Counter(all_kws)
    return [word for word, _ in counts.most_common(8)]

# ============================================================
# MAIN EXECUTION
# ============================================================

def main() -> int:
    print("============================================================")
    print("TechPulse Ingestion Engine — fetch_news.py (Phase 2)")
    print("============================================================")

    all_articles = []
    health_reports = []

    for config in FEEDS:
        items, health = fetch_feed(config)
        health_reports.append(health)
        all_articles.extend(items)

    if not all_articles:
        print("[ERROR] No valid articles fetched across all feeds.")
        return 1 if not OUTPUT_FILE.exists() else 0

    deduped = semantic_deduplicate(all_articles)
    enriched = apply_intelligence_scoring(deduped)
    enriched.sort(key=lambda x: x["impactScore"], reverse=True)

    trending_topics = get_top_trending_topics(enriched)

    clean_articles = []
    for a in enriched[:MAX_ARTICLES]:
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
            "trending": a["trending"],
        })

    payload = {
        "success": True,
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "total": len(clean_articles),
        "featured": [x["id"] for x in clean_articles[:6]],
        "technologyCount": len([x for x in clean_articles if x["mainCategory"] == "Technology"]),
        "gamingCount": len([x for x in clean_articles if x["mainCategory"] == "Gaming"]),
        "trendingTopics": trending_topics,
        "feedHealth": [h.model_dump() for h in health_reports],
        "articles": clean_articles,
    }

    try:
        validated = NewsOutputSchema(**payload)
    except ValidationError as ve:
        print(f"[FATAL] Output payload failed schema validation: {ve}")
        return 1

    temp_file = OUTPUT_FILE.with_suffix(".tmp")
    with temp_file.open("w", encoding="utf-8") as f:
        json.dump(validated.model_dump(), f, ensure_ascii=False, indent=2)
        f.write("\n")

    temp_file.replace(OUTPUT_FILE)
    print("\nPhase 2 news.json successfully written via fetch_news.py.")
    print("============================================================")
    return 0

if __name__ == "__main__":
    sys.exit(main())
