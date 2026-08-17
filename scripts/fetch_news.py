#!/usr/bin/env python3

"""
TechPulse News Fetcher
----------------------

Purpose:
- Fetch legitimate RSS/Atom sources.
- Prefer authoritative / primary sources.
- Never scrape full copyrighted articles.
- Store only headline, short summary/excerpt, metadata and original URL.
- Remove duplicates.
- Cluster similar stories.
- Rank important recent stories.
- Categorize automatically.
- Keep the JSON stable if some feeds fail.
- Produce 50-100 articles when the configured sources provide enough data.

Output:
    news.json

No Google Apps Script.
No database.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import sys
import time
from datetime import datetime, timezone, timedelta
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import urlparse

import feedparser
import requests
from bs4 import BeautifulSoup


# ============================================================
# CONFIGURATION
# ============================================================

OUTPUT_FILE = Path("news.json")

MAX_ARTICLES = 100
MIN_ARTICLES = 30

# Keep a reasonable amount of recent history in the generated file.
MAX_AGE_DAYS = 14

REQUEST_TIMEOUT = 20

USER_AGENT = (
    "TechPulseNewsBot/1.0 "
    "(RSS news discovery; contact via repository owner)"
)


# ============================================================
# AUTHORITATIVE SOURCES
# ============================================================

FEEDS = [

    # --------------------------------------------------------
    # TECHNOLOGY / AI
    # --------------------------------------------------------

    {
        "name": "Google Technology",
        "url": "https://blog.google/feed/",
        "mainCategory": "Technology",
        "category": "Artificial Intelligence",
        "weight": 10,
    },

    {
        "name": "Apple Newsroom",
        "url": "https://www.apple.com/newsroom/rss-feed.rss",
        "mainCategory": "Technology",
        "category": "Hardware & Devices",
        "weight": 10,
    },

    {
        "name": "Apple Developer",
        "url": "https://developer.apple.com/news/rss/news.rss",
        "mainCategory": "Technology",
        "category": "Software & Applications",
        "weight": 10,
    },

    {
        "name": "Apple Software Releases",
        "url": "https://developer.apple.com/news/releases/rss/releases.rss",
        "mainCategory": "Technology",
        "category": "Software & Applications",
        "weight": 10,
    },

    {
        "name": "AWS What's New",
        "url": "https://aws.amazon.com/about-aws/whats-new/recent/feed/",
        "mainCategory": "Technology",
        "category": "Cloud & Infrastructure",
        "weight": 10,
    },

    {
        "name": "NVIDIA",
        "url": "https://nvidia.com/en-us/about-nvidia/rss/",
        "mainCategory": "Technology",
        "category": "Hardware & Devices",
        "weight": 9,
    },

    {
        "name": "Cisco Newsroom",
        "url": "https://newsroom.cisco.com/c/r/newsroom/en/us/rss-feeds.html",
        "mainCategory": "Technology",
        "category": "Enterprise Technology",
        "weight": 9,
    },

    {
        "name": "Windows Blog",
        "url": "https://blogs.windows.com/feed/",
        "mainCategory": "Technology",
        "category": "Software & Applications",
        "weight": 9,
    },

    # --------------------------------------------------------
    # SECURITY
    # --------------------------------------------------------

    {
        "name": "Cisco Security",
        "url": "https://newsroom.cisco.com/c/services/i/servlets/newsroom/rssfeed.json?feed=security",
        "mainCategory": "Technology",
        "category": "Cybersecurity",
        "weight": 9,
    },

    {
        "name": "CISA",
        "url": "https://www.cisa.gov/cybersecurity-advisories/all.xml",
        "mainCategory": "Technology",
        "category": "Cybersecurity",
        "weight": 10,
    },

    # --------------------------------------------------------
    # SCIENCE / SPACE
    # --------------------------------------------------------

    {
        "name": "NASA",
        "url": "https://www.nasa.gov/rss/dyn/breaking_news.rss",
        "mainCategory": "Technology",
        "category": "Science & Innovation",
        "weight": 9,
    },

    {
        "name": "European Space Agency",
        "url": "https://www.esa.int/rssfeed/TopNews",
        "mainCategory": "Technology",
        "category": "Science & Innovation",
        "weight": 9,
    },

    # --------------------------------------------------------
    # GAMING - OFFICIAL
    # --------------------------------------------------------

    {
        "name": "Nintendo",
        "url": "https://www.nintendo.com/us/whatsnew/rss/",
        "mainCategory": "Gaming",
        "category": "Game Releases",
        "weight": 10,
    },

    {
        "name": "Xbox Wire",
        "url": "https://news.xbox.com/en-us/feed/",
        "mainCategory": "Gaming",
        "category": "Console Gaming",
        "weight": 10,
    },

    {
        "name": "PlayStation Blog",
        "url": "https://blog.playstation.com/feed/",
        "mainCategory": "Gaming",
        "category": "Console Gaming",
        "weight": 10,
    },

]


# ============================================================
# FALLBACK RECOGNIZED NEWS SOURCES
# ============================================================

# These are used to increase coverage when primary sources
# don't provide enough current material.
#
# We still store only short metadata/excerpts and direct links.

FALLBACK_FEEDS = [

    {
        "name": "BBC Technology",
        "url": "https://feeds.bbci.co.uk/news/technology/rss.xml",
        "mainCategory": "Technology",
        "category": "Emerging Technology",
        "weight": 7,
    },

    {
        "name": "Ars Technica Technology",
        "url": "https://feeds.arstechnica.com/arstechnica/technology-lab",
        "mainCategory": "Technology",
        "category": "Emerging Technology",
        "weight": 7,
    },

]


ALL_FEEDS = FEEDS + FALLBACK_FEEDS


# ============================================================
# CATEGORY KEYWORDS
# ============================================================

CATEGORY_RULES = [

    (
        "Cybersecurity",
        [
            "cybersecurity",
            "cyber security",
            "security",
            "vulnerability",
            "cve",
            "malware",
            "ransomware",
            "phishing",
            "zero-day",
            "zero day",
            "exploit",
            "breach",
        ],
    ),

    (
        "Artificial Intelligence",
        [
            "artificial intelligence",
            "ai",
            "machine learning",
            "generative ai",
            "large language model",
            "llm",
            "gemini",
            "chatbot",
            "deep learning",
            "neural network",
        ],
    ),

    (
        "Cloud & Infrastructure",
        [
            "cloud",
            "aws",
            "azure",
            "google cloud",
            "kubernetes",
            "container",
            "server",
            "infrastructure",
            "data center",
            "datacenter",
        ],
    ),

    (
        "Smartphones & Mobile",
        [
            "smartphone",
            "iphone",
            "android",
            "mobile phone",
            "mobile",
            "tablet",
            "ipad",
        ],
    ),

    (
        "Software & Applications",
        [
            "software",
            "application",
            "app",
            "windows",
            "macos",
            "ios",
            "developer",
            "release",
            "update",
            "operating system",
        ],
    ),

    (
        "Hardware & Devices",
        [
            "hardware",
            "processor",
            "cpu",
            "gpu",
            "chip",
            "device",
            "laptop",
            "desktop",
            "memory",
            "storage",
        ],
    ),

    (
        "PC Gaming",
        [
            "pc gaming",
            "steam",
            "pc game",
            "pc games",
        ],
    ),

    (
        "Console Gaming",
        [
            "playstation",
            "xbox",
            "nintendo",
            "console",
            "switch",
        ],
    ),

    (
        "Mobile Gaming",
        [
            "mobile gaming",
            "mobile game",
            "android game",
            "ios game",
        ],
    ),

    (
        "Game Releases",
        [
            "game release",
            "launches",
            "released",
            "release date",
            "coming to",
            "available now",
        ],
    ),

    (
        "Gaming Hardware",
        [
            "gaming hardware",
            "gaming monitor",
            "gaming laptop",
            "gaming pc",
            "controller",
            "headset",
            "graphics card",
        ],
    ),

    (
        "Esports",
        [
            "esports",
            "e-sports",
            "tournament",
            "championship",
        ],
    ),

]


# ============================================================
# HTTP SESSION
# ============================================================

SESSION = requests.Session()

SESSION.headers.update(
    {
        "User-Agent": USER_AGENT,
        "Accept": (
            "application/rss+xml, "
            "application/atom+xml, "
            "application/xml, "
            "text/xml, "
            "text/html;q=0.8, "
            "*/*;q=0.5"
        ),
    }
)


# ============================================================
# HELPERS
# ============================================================

def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def clean_html(value: str) -> str:

    if not value:
        return ""

    value = html.unescape(str(value))

    soup = BeautifulSoup(value, "html.parser")

    text = soup.get_text(" ", strip=True)

    text = re.sub(r"\s+", " ", text)

    return text.strip()


def shorten_text(value: str, maximum: int = 280) -> str:

    text = clean_html(value)

    if not text:
        return ""

    if len(text) <= maximum:
        return text

    shortened = text[:maximum]

    if " " in shortened:
        shortened = shortened.rsplit(" ", 1)[0]

    return shortened.rstrip(" .,;:") + "…"


def normalize_title(title: str) -> str:

    value = title.lower()

    value = re.sub(
        r"[^a-z0-9\s]",
        " ",
        value,
    )

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value.strip()


def canonical_url(url: str) -> str:

    if not url:
        return ""

    try:

        parsed = urlparse(url)

        if parsed.scheme not in ("http", "https"):
            return ""

        if not parsed.netloc:
            return ""

        return url.strip()

    except Exception:
        return ""


def parse_date(entry) -> datetime:

    candidates = [
        entry.get("published_parsed"),
        entry.get("updated_parsed"),
        entry.get("created_parsed"),
    ]

    for value in candidates:

        if value:

            try:

                return datetime.fromtimestamp(
                    time.mktime(value),
                    tz=timezone.utc,
                )

            except Exception:
                pass

    for key in (
        "published",
        "updated",
        "created",
        "date",
    ):

        raw = entry.get(key)

        if raw:

            try:

                parsed = feedparser._parse_date(raw)

                if parsed:

                    return datetime.fromtimestamp(
                        time.mktime(parsed),
                        tz=timezone.utc,
                    )

            except Exception:
                pass

    return now_utc()


def detect_category(
    title: str,
    description: str,
    default_category: str,
) -> str:

    text = (
        title + " " + description
    ).lower()

    for category, keywords in CATEGORY_RULES:

        for keyword in keywords:

            if keyword in text:

                return category

    return default_category


def make_id(
    title: str,
    url: str,
) -> str:

    raw = (
        normalize_title(title)
        + "|"
        + url.lower()
    )

    digest = hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()[:20]

    return "techpulse-" + digest


def similarity(
    title_a: str,
    title_b: str,
) -> float:

    a = normalize_title(title_a)
    b = normalize_title(title_b)

    if not a or not b:
        return 0.0

    return SequenceMatcher(
        None,
        a,
        b,
    ).ratio()


def extract_description(entry) -> str:

    values = [

        entry.get("summary", ""),

        entry.get("description", ""),

    ]

    # Some Atom feeds expose content.
    content = entry.get("content")

    if content and isinstance(content, list):

        for item in content:

            if isinstance(item, dict):

                values.append(
                    item.get("value", "")
                )

    for value in values:

        text = shorten_text(
            value,
            280,
        )

        if text:
            return text

    return (
        "Latest technology and gaming "
        "news from an authoritative source."
    )


def extract_url(entry) -> str:

    link = entry.get("link", "")

    if link:
        return canonical_url(link)

    links = entry.get("links", [])

    if isinstance(links, list):

        for item in links:

            if not isinstance(item, dict):
                continue

            href = item.get("href", "")

            url = canonical_url(href)

            if url:
                return url

    return ""


# ============================================================
# FEED FETCHING
# ============================================================

def fetch_feed(config: dict) -> list[dict]:

    name = config["name"]

    url = config["url"]

    print(f"Fetching: {name}")

    try:

        response = SESSION.get(
            url,
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()

        feed = feedparser.parse(
            response.content
        )

        if feed.bozo:

            print(
                f"  Warning: malformed feed: {name}"
            )

        entries = getattr(
            feed,
            "entries",
            [],
        )

        print(
            f"  Entries: {len(entries)}"
        )

        articles = []

        cutoff = (
            now_utc()
            - timedelta(
                days=MAX_AGE_DAYS
            )
        )

        for entry in entries:

            title = clean_html(
                entry.get(
                    "title",
                    "",
                )
            )

            if not title:
                continue

            url_value = extract_url(entry)

            if not url_value:
                continue

            published_dt = parse_date(entry)

            if published_dt < cutoff:

                continue

            description = extract_description(
                entry
            )

            category = detect_category(
                title,
                description,
                config["category"],
            )

            article = {

                "id": make_id(
                    title,
                    url_value,
                ),

                "title": title,

                "description": description,

                "url": url_value,

                # Intentionally no remote image.
                # This avoids unnecessary image/logo
                # copyright and branding issues.
                "image": "",

                "category": category,

                "mainCategory":
                    config["mainCategory"],

                "source":
                    name,

                "published":
                    published_dt.isoformat(),

                "_weight":
                    config.get(
                        "weight",
                        5,
                    ),

            }

            articles.append(article)

        return articles

    except Exception as exc:

        print(
            f"  FAILED: {name}: {exc}"
        )

        return []


# ============================================================
# DEDUPLICATION
# ============================================================

def deduplicate(
    articles: list[dict],
) -> list[dict]:

    result = []

    exact_ids = set()

    for article in sorted(
        articles,
        key=lambda x: x["published"],
        reverse=True,
    ):

        article_id = article["id"]

        if article_id in exact_ids:
            continue

        exact_ids.add(article_id)

        duplicate = False

        for existing in result:

            if (
                article["mainCategory"]
                != existing["mainCategory"]
            ):
                continue

            score = similarity(
                article["title"],
                existing["title"],
            )

            if score >= 0.88:

                duplicate = True

                # Keep the more authoritative source.
                if (
                    article["_weight"]
                    > existing["_weight"]
                ):

                    result.remove(existing)

                    result.append(article)

                break

        if not duplicate:

            result.append(article)

    return result


# ============================================================
# TRENDING / STORY CLUSTERING
# ============================================================

def build_clusters(
    articles: list[dict],
) -> list[dict]:

    clusters = []

    for article in articles:

        placed = False

        for cluster in clusters:

            representative = cluster[0]

            if similarity(
                article["title"],
                representative["title"],
            ) >= 0.68:

                cluster.append(article)

                placed = True

                break

        if not placed:

            clusters.append(
                [article]
            )

    return clusters


def apply_story_metadata(
    articles: list[dict],
) -> list[dict]:

    clusters = build_clusters(
        articles
    )

    cluster_lookup = {}

    for cluster in clusters:

        cluster_id = hashlib.sha256(
            normalize_title(
                cluster[0]["title"]
            ).encode("utf-8")
        ).hexdigest()[:12]

        source_count = len(
            {
                item["source"]
                for item in cluster
            }
        )

        for item in cluster:

            cluster_lookup[
                item["id"]
            ] = {
                "storyId":
                    "story-" + cluster_id,

                "relatedCount":
                    len(cluster),

                "sourceCount":
                    source_count,

                "trending":
                    (
                        len(cluster) >= 2
                        or source_count >= 2
                    ),
            }

    for article in articles:

        metadata = cluster_lookup.get(
            article["id"],
            {},
        )

        article["storyId"] = metadata.get(
            "storyId",
            "story-" + article["id"],
        )

        article["relatedCount"] = metadata.get(
            "relatedCount",
            1,
        )

        article["sourceCount"] = metadata.get(
            "sourceCount",
            1,
        )

        article["trending"] = metadata.get(
            "trending",
            False,
        )

    return articles


# ============================================================
# RANKING
# ============================================================

def rank_score(
    article: dict,
) -> float:

    try:

        published = datetime.fromisoformat(
            article["published"]
            .replace(
                "Z",
                "+00:00",
            )
        )

    except Exception:

        published = now_utc()

    age_hours = max(
        0,
        (
            now_utc()
            - published
        ).total_seconds()
        / 3600,
    )

    recency_score = max(
        0,
        48 - age_hours,
    )

    authority_score = (
        article.get(
            "_weight",
            5,
        )
        * 3
    )

    related_score = (
        article.get(
            "relatedCount",
            1,
        )
        * 8
    )

    trending_score = (
        20
        if article.get(
            "trending",
            False,
        )
        else 0
    )

    return (
        recency_score
        + authority_score
        + related_score
        + trending_score
    )


# ============================================================
# BUILD JSON
# ============================================================

def build_output(
    articles: list[dict],
) -> dict:

    articles = apply_story_metadata(
        articles
    )

    articles.sort(
        key=rank_score,
        reverse=True,
    )

    # Remove internal fields.
    clean_articles = []

    for article in articles[:MAX_ARTICLES]:

        item = {
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
        }

        clean_articles.append(item)

    # Featured articles are selected by ranking.
    technology = [
        item
        for item in clean_articles
        if item["mainCategory"]
        == "Technology"
    ]

    gaming = [
        item
        for item in clean_articles
        if item["mainCategory"]
        == "Gaming"
    ]

    featured = clean_articles[:6]

    return {

        "success": True,

        "updatedAt":
            now_utc().isoformat(),

        "total":
            len(clean_articles),

        "featured":
            [
                item["id"]
                for item in featured
            ],

        "technologyCount":
            len(technology),

        "gamingCount":
            len(gaming),

        "articles":
            clean_articles,

    }


# ============================================================
# MAIN
# ============================================================

def main() -> int:

    print("=" * 60)

    print(
        "TechPulse News Fetcher"
    )

    print("=" * 60)

    all_articles = []

    successful_feeds = 0

    for feed_config in ALL_FEEDS:

        articles = fetch_feed(
            feed_config
        )

        if articles:

            successful_feeds += 1

            all_articles.extend(
                articles
            )

    print()

    print(
        "Raw articles:",
        len(all_articles),
    )

    print(
        "Successful feeds:",
        successful_feeds,
        "/",
        len(ALL_FEEDS),
    )

    if not all_articles:

        print(
            "ERROR: No valid articles were fetched."
        )

        # Preserve an existing valid news.json
        # rather than destroying good content.
        if OUTPUT_FILE.exists():

            print(
                "Existing news.json preserved."
            )

            return 0

        return 1

    articles = deduplicate(
        all_articles
    )

    print(
        "After deduplication:",
        len(articles),
    )

    if len(articles) < MIN_ARTICLES:

        print(
            f"WARNING: Only {len(articles)} "
            f"articles available."
        )

        print(
            "The system will publish the valid "
            "articles instead of generating fake stories."
        )

    data = build_output(
        articles
    )

    temporary_file = OUTPUT_FILE.with_suffix(
        ".tmp"
    )

    with temporary_file.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
        )

        file.write("\n")

    # Validate before replacing production JSON.
    with temporary_file.open(
        "r",
        encoding="utf-8",
    ) as file:

        json.load(file)

    temporary_file.replace(
        OUTPUT_FILE
    )

    print()

    print(
        "news.json successfully updated."
    )

    print(
        "Articles:",
        data["total"],
    )

    print(
        "Technology:",
        data["technologyCount"],
    )

    print(
        "Gaming:",
        data["gamingCount"],
    )

    print(
        "Updated:",
        data["updatedAt"],
    )

    print("=" * 60)

    return 0


if __name__ == "__main__":

    sys.exit(main())
