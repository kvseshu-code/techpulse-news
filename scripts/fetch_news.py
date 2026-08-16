#!/usr/bin/env python3
"""
fetch_news.py — TechPulse news pipeline

    RSS/API sources
        |
        v
    Fetch + parse each feed (feedparser)
        |
        v
    Normalize into a common article shape
        |
        v
    Remove duplicates (by URL, then by normalized title)
        |
        v
    Categorize (by source feed) + auto-tag (by keyword)
        |
        v
    Sort by published date (newest first)
        |
        v
    Compute simple "trending" flags
        |
        v
    Write news.json (with per-source fetch status + last_updated)

Runs standalone (`python scripts/fetch_news.py`) or via the GitHub Actions
workflow in .github/workflows/update-news.yml on a schedule.

Design goals (matches the brief this replaces):
  - No database. news.json IS the database.
  - One broken feed should never break the whole run — every fetch is
    wrapped and failures are skipped + logged into news.json's "sources"
    block, so the frontend can show feed health if it wants to.
  - Sources are declared in one place (SOURCES below) so adding/removing
    a feed is a one-line change, no other code to touch.
"""

import json
import re
import sys
import time
import hashlib
import datetime as dt
from urllib.parse import urlparse

import feedparser

# ---------------------------------------------------------------------------
# STEP 15 (from the original plan): sources live in one config block.
# Add/remove/disable feeds here without touching any other code.
# Each source: name, feed URL, category, and optional weight (higher =
# shown first when scores tie). Verify these periodically — RSS URLs do
# occasionally move.
# ---------------------------------------------------------------------------
SOURCES = [
    # -- Technology --------------------------------------------------------
    {"name": "TechCrunch",   "url": "https://techcrunch.com/feed/",                     "category": "Technology"},
    {"name": "The Verge",    "url": "https://www.theverge.com/rss/index.xml",           "category": "Technology"},
    {"name": "Ars Technica", "url": "https://feeds.arstechnica.com/arstechnica/index",  "category": "Technology"},
    {"name": "Wired",        "url": "https://www.wired.com/feed/rss",                   "category": "Technology"},
    {"name": "ZDNET",        "url": "https://www.zdnet.com/news/rss.xml",               "category": "Technology"},

    # -- Gaming --------------------------------------------------------
    {"name": "IGN",          "url": "https://feeds.ign.com/ign/all",                    "category": "Gaming"},
    {"name": "GameSpot",     "url": "https://www.gamespot.com/feeds/news/",             "category": "Gaming"},
    {"name": "PC Gamer",     "url": "https://www.pcgamer.com/rss/",                     "category": "Gaming"},
    {"name": "Eurogamer",    "url": "https://www.eurogamer.net/feed",                   "category": "Gaming"},
]

# ---------------------------------------------------------------------------
# STEP 12: keyword-based sub-tagging on top of the per-feed category.
# An article can pick up extra tags beyond its main category, e.g. a
# TechCrunch (Technology) article that mentions "OpenAI" also gets "AI".
# Order matters a little (first match found per keyword group wins for
# display purposes) but all matching tags are kept.
# ---------------------------------------------------------------------------
KEYWORD_TAGS = [
    ("AI",            [r"\bai\b", r"artificial intelligence", r"chatgpt", r"openai", r"gemini", r"\bclaude\b", r"llm\b"]),
    ("Cybersecurity", [r"cybersecurity", r"data breach", r"ransomware", r"vulnerabilit", r"exploit", r"malware", r"hack(ed|er|ing)?"]),
    ("Cloud",         [r"\bcloud\b", r"\baws\b", r"azure", r"google cloud"]),
    ("PlayStation",   [r"playstation", r"\bps5\b", r"\bps4\b", r"sony interactive"]),
    ("Xbox",          [r"\bxbox\b", r"microsoft gaming"]),
    ("Nintendo",      [r"nintendo", r"switch"]),
]

MAX_ARTICLES_PER_CATEGORY = 60   # Step 16-style cap, keeps news.json small
FETCH_TIMEOUT_SECONDS = 15
REQUEST_HEADERS = {
    "User-Agent": "TechPulseBot/1.0 (+https://kvseshu-code.github.io/techpulse-news/)"
}


def normalize_title(title: str) -> str:
    """Lowercase, strip punctuation/whitespace so near-duplicate titles
    from different publishers still collide for dedup purposes."""
    t = title.lower()
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def article_id(url: str, title: str) -> str:
    """Stable short ID for an article, used as a dedup key and a DOM id
    on the frontend."""
    basis = (url or "") + "|" + normalize_title(title)
    return hashlib.sha1(basis.encode("utf-8")).hexdigest()[:16]


def best_image(entry) -> str:
    """feedparser entries expose images in several different shapes
    depending on the publisher's feed format. Try the common ones."""
    media = entry.get("media_content") or entry.get("media_thumbnail")
    if media and isinstance(media, list) and media[0].get("url"):
        return media[0]["url"]

    if entry.get("links"):
        for link in entry["links"]:
            if link.get("type", "").startswith("image/") and link.get("href"):
                return link["href"]

    # Some feeds embed an <img> in the summary HTML.
    summary = entry.get("summary", "") or ""
    m = re.search(r'<img[^>]+src="([^"]+)"', summary)
    if m:
        return m.group(1)

    return ""


def clean_summary(entry) -> str:
    raw = entry.get("summary", "") or entry.get("description", "") or ""
    text = re.sub(r"<[^>]+>", " ", raw)      # strip HTML tags
    text = re.sub(r"\s+", " ", text).strip()
    return text[:280]


def parse_published(entry) -> str:
    """Return an ISO-8601 UTC timestamp string. Falls back to 'now' if
    the feed doesn't provide a parseable date, so bad dates never crash
    the sort step."""
    for key in ("published_parsed", "updated_parsed"):
        val = entry.get(key)
        if val:
            try:
                return dt.datetime(*val[:6], tzinfo=dt.timezone.utc).isoformat()
            except Exception:
                pass
    return dt.datetime.now(dt.timezone.utc).isoformat()


def tag_article(title: str, summary: str) -> list:
    haystack = (title + " " + summary).lower()
    tags = []
    for tag, patterns in KEYWORD_TAGS:
        if any(re.search(p, haystack) for p in patterns):
            tags.append(tag)
    return tags


def fetch_source(source: dict) -> tuple:
    """Fetch + parse one feed. Returns (articles, status_dict).
    Never raises — a failed source just returns an empty list and a
    status block recording the error, per Step 18/19 (one bad feed
    should never take down the whole site)."""
    status = {
        "name": source["name"],
        "url": source["url"],
        "category": source["category"],
        "ok": False,
        "article_count": 0,
        "error": None,
        "checked_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    articles = []
    try:
        parsed = feedparser.parse(source["url"], request_headers=REQUEST_HEADERS)
        if parsed.bozo and not parsed.entries:
            raise RuntimeError(str(parsed.get("bozo_exception", "unknown parse error")))

        for entry in parsed.entries:
            title = (entry.get("title") or "").strip()
            link = (entry.get("link") or "").strip()
            if not title or not link:
                continue

            summary = clean_summary(entry)
            published = parse_published(entry)
            tags = tag_article(title, summary)

            articles.append({
                "id": article_id(link, title),
                "title": title,
                "description": summary,
                "url": link,
                "image": best_image(entry),
                "source": source["name"],
                "category": source["category"],
                "tags": tags,
                "published": published,
                "domain": urlparse(link).netloc.replace("www.", ""),
            })

        status["ok"] = True
        status["article_count"] = len(articles)
    except Exception as exc:  # noqa: BLE001 - intentionally broad, feeds fail in many ways
        status["error"] = f"{type(exc).__name__}: {exc}"

    return articles, status


def dedupe(articles: list) -> list:
    """STEP 11: collapse duplicate/near-duplicate stories. Two passes -
    exact URL match first (cheapest, catches syndicated copies), then
    normalized-title match (catches the same story covered by multiple
    outlets with slightly different URLs)."""
    seen_urls = set()
    seen_titles = set()
    unique = []
    for art in articles:
        norm_title = normalize_title(art["title"])
        if art["url"] in seen_urls or norm_title in seen_titles:
            continue
        seen_urls.add(art["url"])
        seen_titles.add(norm_title)
        unique.append(art)
    return unique


def compute_trending(articles: list, window_hours: int = 18, min_sources: int = 2) -> set:
    """STEP 14 (simple version, no DB): a normalized title cluster that's
    covered by multiple distinct sources within a recent time window is
    "trending". Returns a set of article ids to flag."""
    now = dt.datetime.now(dt.timezone.utc)
    clusters = {}
    for art in articles:
        try:
            published = dt.datetime.fromisoformat(art["published"])
        except Exception:
            continue
        if (now - published).total_seconds() > window_hours * 3600:
            continue
        key = normalize_title(art["title"])[:60]  # loose clustering key
        clusters.setdefault(key, set()).add(art["source"])

    trending_ids = set()
    for art in articles:
        key = normalize_title(art["title"])[:60]
        if len(clusters.get(key, [])) >= min_sources:
            trending_ids.add(art["id"])
    return trending_ids


def main():
    started = time.time()
    all_articles = []
    source_statuses = []

    for source in SOURCES:
        articles, status = fetch_source(source)
        all_articles.extend(articles)
        source_statuses.append(status)
        flag = "OK " if status["ok"] else "FAIL"
        print(f"[{flag}] {source['name']:<14} {status['article_count']:>3} articles  {status['error'] or ''}")

    all_articles = dedupe(all_articles)
    all_articles.sort(key=lambda a: a["published"], reverse=True)

    trending_ids = compute_trending(all_articles)
    for art in all_articles:
        art["trending"] = art["id"] in trending_ids

    # Cap per category so news.json doesn't grow unbounded over time.
    capped = []
    per_category_count = {}
    for art in all_articles:
        cat = art["category"]
        per_category_count[cat] = per_category_count.get(cat, 0) + 1
        if per_category_count[cat] <= MAX_ARTICLES_PER_CATEGORY:
            capped.append(art)

    output = {
        "success": True,
        "last_updated": dt.datetime.now(dt.timezone.utc).isoformat(),
        "article_count": len(capped),
        "fetch_duration_seconds": round(time.time() - started, 2),
        "sources": source_statuses,
        "articles": capped,
    }

    with open("news.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    ok_count = sum(1 for s in source_statuses if s["ok"])
    print(f"\nWrote news.json — {len(capped)} articles from {ok_count}/{len(SOURCES)} sources "
          f"in {output['fetch_duration_seconds']}s")

    # Non-zero exit only if EVERY source failed - a partial failure should
    # still let the workflow commit whatever news we did get.
    if ok_count == 0:
        print("ERROR: every source failed - not overwriting news.json with an empty result.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
