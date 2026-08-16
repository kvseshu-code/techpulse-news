"""
============================================================
TECHPULSE — TECHNOLOGY & GAMING NEWS ENGINE
============================================================

Purpose:
    Fetch the latest technology and gaming news from RSS/Atom
    feeds and generate news.json.

Architecture:

    RSS / Atom Feeds
            ↓
    GitHub Actions
            ↓
    fetch_news.py
            ↓
    Parse + Clean
            ↓
    Categorize
            ↓
    Deduplicate
            ↓
    Sort by publication date
            ↓
    news.json
            ↓
    app.js
            ↓
    index.html

No traditional database required.
============================================================
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import feedparser
import requests


# ============================================================
# PATH CONFIGURATION
# ============================================================

# fetch_news.py is located inside:
#
#     scripts/fetch_news.py
#
# Therefore the repository root is one level above scripts/.

BASE_DIR = Path(__file__).resolve().parent.parent

NEWS_FILE = BASE_DIR / "news.json"


# ============================================================
# GENERAL CONFIGURATION
# ============================================================

MAX_ARTICLES = 120

MAX_ARTICLES_PER_SOURCE = 25

MAX_ARTICLE_AGE_HOURS = 72

REQUEST_TIMEOUT = 20

USER_AGENT = (
    "TechPulseNewsBot/1.0 "
    "(technology and gaming news aggregation)"
)


# ============================================================
# NEWS SOURCES
# ============================================================

NEWS_SOURCES = [

    # --------------------------------------------------------
    # TECHNOLOGY
    # --------------------------------------------------------

    {
        "name": "TechCrunch",
        "category": "Technology",
        "feed": "https://techcrunch.com/feed/",
        "website": "https://techcrunch.com/",
        "active": True,
    },

    {
        "name": "The Verge",
        "category": "Technology",
        "feed": "https://www.theverge.com/rss/index.xml",
        "website": "https://www.theverge.com/",
        "active": True,
    },

    {
        "name": "Ars Technica",
        "category": "Technology",
        "feed": "https://feeds.arstechnica.com/arstechnica/index",
        "website": "https://arstechnica.com/",
        "active": True,
    },

    {
        "name": "WIRED",
        "category": "Technology",
        "feed": "https://www.wired.com/feed/rss",
        "website": "https://www.wired.com/",
        "active": True,
    },

    {
        "name": "Engadget",
        "category": "Technology",
        "feed": "https://www.engadget.com/rss.xml",
        "website": "https://www.engadget.com/",
        "active": True,
    },

    {
        "name": "CNET",
        "category": "Technology",
        "feed": "https://www.cnet.com/rss/news/",
        "website": "https://www.cnet.com/",
        "active": True,
    },

    {
        "name": "ZDNET",
        "category": "Technology",
        "feed": "https://www.zdnet.com/news/rss.xml",
        "website": "https://www.zdnet.com/",
        "active": True,
    },


    # --------------------------------------------------------
    # GAMING
    # --------------------------------------------------------

    {
        "name": "IGN",
        "category": "Gaming",
        "feed": "https://feeds.feedburner.com/ign/all",
        "website": "https://www.ign.com/",
        "active": True,
    },

    {
        "name": "PC Gamer",
        "category": "Gaming",
        "feed": "https://www.pcgamer.com/rss/",
        "website": "https://www.pcgamer.com/",
        "active": True,
    },

    {
        "name": "GameSpot",
        "category": "Gaming",
        "feed": "https://www.gamespot.com/feeds/news/",
        "website": "https://www.gamespot.com/",
        "active": True,
    },

    {
        "name": "Polygon",
        "category": "Gaming",
        "feed": "https://www.polygon.com/rss/index.xml",
        "website": "https://www.polygon.com/",
        "active": True,
    },

    {
        "name": "Eurogamer",
        "category": "Gaming",
        "feed": "https://www.eurogamer.net/feed",
        "website": "https://www.eurogamer.net/",
        "active": True,
    },

    {
        "name": "GamesRadar+",
        "category": "Gaming",
        "feed": "https://www.gamesradar.com/rss/",
        "website": "https://www.gamesradar.com/",
        "active": True,
    },
]


# ============================================================
# CATEGORY RULES
# ============================================================

CATEGORY_RULES = {

    "Artificial Intelligence": [
        "artificial intelligence",
        "artificial-intelligence",
        "machine learning",
        "deep learning",
        "generative ai",
        "large language model",
        "llm",
        "chatbot",
        "neural network",
        "computer vision",
        "robotics",
    ],

    "Smartphones & Mobile": [
        "smartphone",
        "smartphones",
        "mobile phone",
        "mobile device",
        "android",
        "iphone",
        "ios",
        "tablet",
        "wearable",
        "foldable",
        "mobile app",
    ],

    "Cybersecurity": [
        "cybersecurity",
        "cyber security",
        "malware",
        "ransomware",
        "phishing",
        "zero-day",
        "zero day",
        "vulnerability",
        "exploit",
        "breach",
        "security patch",
        "hacker",
        "data breach",
        "privacy",
    ],

    "Cloud & Infrastructure": [
        "cloud computing",
        "cloud infrastructure",
        "data center",
        "datacenter",
        "server",
        "servers",
        "kubernetes",
        "container",
        "virtual machine",
        "infrastructure",
        "devops",
    ],

    "Software & Applications": [
        "software",
        "application",
        "app update",
        "browser",
        "operating system",
        "open source",
        "developer",
        "programming",
        "api",
        "platform",
    ],

    "Hardware & Devices": [
        "hardware",
        "processor",
        "cpu",
        "gpu",
        "graphics card",
        "memory",
        "ssd",
        "storage",
        "laptop",
        "desktop",
        "monitor",
        "keyboard",
        "device",
    ],

    "Internet & Web": [
        "internet",
        "website",
        "social media",
        "online",
        "search",
        "browser",
        "streaming",
        "network",
        "web service",
    ],

    "Emerging Technology": [
        "quantum",
        "augmented reality",
        "virtual reality",
        "mixed reality",
        "blockchain",
        "autonomous",
        "drone",
        "3d printing",
        "next generation",
        "emerging technology",
    ],

    "Science & Innovation": [
        "science",
        "scientist",
        "research",
        "space",
        "astronomy",
        "innovation",
        "discovery",
        "laboratory",
        "energy",
    ],

    "Business & Technology": [
        "startup",
        "funding",
        "investment",
        "acquisition",
        "merger",
        "enterprise",
        "business",
        "market",
        "revenue",
        "technology industry",
    ],

    # --------------------------------------------------------
    # GAMING
    # --------------------------------------------------------

    "PC Gaming": [
        "pc gaming",
        "pc game",
        "steam",
        "gaming pc",
        "pc gamer",
    ],

    "Console Gaming": [
        "console",
        "playstation",
        "xbox",
        "nintendo",
        "console gaming",
    ],

    "Mobile Gaming": [
        "mobile game",
        "mobile gaming",
        "ios game",
        "android game",
        "smartphone game",
    ],

    "Game Releases": [
        "game release",
        "release date",
        "new game",
        "upcoming game",
        "game launches",
        "game launch",
    ],

    "Gaming Hardware": [
        "gaming hardware",
        "gaming headset",
        "gaming mouse",
        "gaming keyboard",
        "gaming monitor",
        "gaming laptop",
        "gaming gpu",
    ],

    "Esports": [
        "esports",
        "e-sports",
        "tournament",
        "championship",
        "competitive gaming",
        "pro gamer",
    ],

    "Game Development": [
        "game developer",
        "game development",
        "game engine",
        "developer studio",
        "development studio",
        "game design",
    ],

    "Gaming Industry": [
        "gaming industry",
        "game studio",
        "game publisher",
        "gaming business",
        "game sales",
    ],

    "Gaming Updates": [
        "game update",
        "game patch",
        "dlc",
        "expansion",
        "season update",
    ],

    "Reviews & Features": [
        "review",
        "hands-on",
        "preview",
        "feature",
        "analysis",
        "guide",
    ],
}


# ============================================================
# GAMING CATEGORIES
# ============================================================

GAMING_CATEGORIES = {
    "PC Gaming",
    "Console Gaming",
    "Mobile Gaming",
    "Game Releases",
    "Gaming Hardware",
    "Esports",
    "Game Development",
    "Gaming Industry",
    "Gaming Updates",
    "Reviews & Features",
}


# ============================================================
# LOGGING
# ============================================================

def log(message: str) -> None:
    """Print a timestamped message."""

    timestamp = datetime.now(
        timezone.utc
    ).strftime("%Y-%m-%d %H:%M:%S UTC")

    print(
        f"[{timestamp}] {message}",
        flush=True,
    )


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_text(value: Any) -> str:
    """Remove HTML and normalize whitespace."""

    if value is None:
        return ""

    text = str(value)

    text = html.unescape(text)

    text = re.sub(
        r"<script[\s\S]*?</script>",
        " ",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"<style[\s\S]*?</style>",
        " ",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"<[^>]+>",
        " ",
        text,
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


# ============================================================
# EXCERPT
# ============================================================

def create_excerpt(
    value: str,
    maximum: int = 240,
) -> str:
    """Create a clean article excerpt."""

    text = clean_text(value)

    if len(text) <= maximum:
        return text

    shortened = text[:maximum]

    shortened = re.sub(
        r"\s+\S*$",
        "",
        shortened,
    )

    return shortened.rstrip() + "..."


# ============================================================
# NORMALIZE TITLE
# ============================================================

def normalize_title(title: str) -> str:
    """Normalize a title for duplicate detection."""

    text = clean_text(title).lower()

    text = re.sub(
        r"https?://\S+",
        "",
        text,
    )

    text = re.sub(
        r"[^a-z0-9\s]",
        "",
        text,
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


# ============================================================
# NORMALIZE URL
# ============================================================

def normalize_url(url: str) -> str:
    """Normalize URLs for duplicate detection."""

    if not url:
        return ""

    try:

        parts = urlsplit(
            url.strip()
        )

        normalized = urlunsplit(
            (
                parts.scheme.lower(),
                parts.netloc.lower(),
                parts.path.rstrip("/"),
                "",
                "",
            )
        )

        return normalized

    except Exception:

        return url.lower().strip().rstrip("/")


# ============================================================
# ARTICLE ID
# ============================================================

def create_article_id(value: str) -> str:
    """Create a stable article ID."""

    digest = hashlib.sha256(
        value.encode(
            "utf-8",
            errors="ignore",
        )
    ).hexdigest()

    return "news_" + digest[:16]


# ============================================================
# DATE PARSING
# ============================================================

def parse_entry_date(
    entry: Any,
) -> datetime:
    """
    Convert feedparser's published/updated time
    into an aware UTC datetime.
    """

    time_struct = (
        entry.get("published_parsed")
        or entry.get("updated_parsed")
        or entry.get("created_parsed")
    )

    if time_struct:

        try:

            from calendar import timegm

            timestamp = timegm(
                time_struct
            )

            return datetime.fromtimestamp(
                timestamp,
                tz=timezone.utc,
            )

        except Exception:
            pass


    # Fallback to raw date strings.

    raw_date = (
        entry.get("published")
        or entry.get("updated")
        or entry.get("created")
    )

    if raw_date:

        try:

            from email.utils import parsedate_to_datetime

            date = parsedate_to_datetime(
                raw_date
            )

            if date.tzinfo is None:

                date = date.replace(
                    tzinfo=timezone.utc
                )

            return date.astimezone(
                timezone.utc
            )

        except Exception:
            pass


    # If the publisher doesn't provide a valid date,
    # use current UTC time.

    return datetime.now(
        timezone.utc
    )


# ============================================================
# ARTICLE RECENCY
# ============================================================

def is_recent(
    published: datetime,
) -> bool:
    """Check whether an article is within the configured age."""

    now = datetime.now(
        timezone.utc
    )

    age_seconds = (
        now - published
    ).total_seconds()

    maximum_seconds = (
        MAX_ARTICLE_AGE_HOURS
        * 60
        * 60
    )

    return (
        age_seconds >= 0
        and age_seconds <= maximum_seconds
    )


# ============================================================
# CATEGORY DETECTION
# ============================================================

def detect_category(
    main_category: str,
    title: str,
    description: str,
) -> str:
    """
    Determine a useful TechPulse category based on
    article title and description.
    """

    text = (
        f" {title} {description} "
    ).lower()

    # Gaming source gets gaming categories.

    for category, keywords in CATEGORY_RULES.items():

        is_gaming_rule = (
            category in GAMING_CATEGORIES
        )

        if (
            main_category == "Gaming"
            and not is_gaming_rule
        ):
            continue

        if (
            main_category == "Technology"
            and is_gaming_rule
        ):
            continue

        for keyword in keywords:

            keyword = keyword.lower()

            if keyword in text:

                return category


    if main_category == "Gaming":

        return "Gaming Updates"

    return "Emerging Technology"


# ============================================================
# IMAGE EXTRACTION
# ============================================================

def extract_image(
    entry: Any,
) -> str:
    """Extract an article image from common RSS/Atom fields."""

    # --------------------------------------------------------
    # media_content
    # --------------------------------------------------------

    media_content = entry.get(
        "media_content",
        [],
    )

    if isinstance(
        media_content,
        list,
    ):

        for media in media_content:

            if not isinstance(
                media,
                dict,
            ):
                continue

            url = (
                media.get("url")
                or media.get("href")
            )

            if url:

                return str(url)


    # --------------------------------------------------------
    # media_thumbnail
    # --------------------------------------------------------

    media_thumbnail = entry.get(
        "media_thumbnail",
        [],
    )

    if isinstance(
        media_thumbnail,
        list,
    ):

        for media in media_thumbnail:

            if not isinstance(
                media,
                dict,
            ):
                continue

            url = media.get(
                "url"
            )

            if url:

                return str(url)


    # --------------------------------------------------------
    # enclosures
    # --------------------------------------------------------

    enclosures = entry.get(
        "enclosures",
        [],
    )

    if isinstance(
        enclosures,
        list,
    ):

        for enclosure in enclosures:

            if not isinstance(
                enclosure,
                dict,
            ):
                continue

            url = enclosure.get(
                "href"
            ) or enclosure.get(
                "url"
            )

            media_type = str(
                enclosure.get(
                    "type",
                    "",
                )
            ).lower()

            if url:

                if (
                    not media_type
                    or media_type.startswith(
                        "image/"
                    )
                ):

                    return str(url)


    # --------------------------------------------------------
    # HTML image
    # --------------------------------------------------------

    html_content = (
        entry.get(
            "summary",
            "",
        )
        or entry.get(
            "description",
            "",
        )
        or ""
    )

    match = re.search(
        r'<img[^>]+src=["\']([^"\']+)["\']',
        str(html_content),
        flags=re.IGNORECASE,
    )

    if match:

        return html.unescape(
            match.group(1)
        )


    return ""


# ============================================================
# FETCH ONE FEED
# ============================================================

def fetch_feed(
    source: dict,
) -> list[dict]:
    """Fetch and parse one RSS/Atom feed."""

    name = source["name"]

    url = source["feed"]

    log(
        f"Fetching: {name}"
    )

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": (
            "application/rss+xml, "
            "application/atom+xml, "
            "application/xml, "
            "text/xml, "
            "*/*"
        ),
    }

    response = requests.get(
        url,
        headers=headers,
        timeout=REQUEST_TIMEOUT,
    )

    response.raise_for_status()

    parsed = feedparser.parse(
        response.content
    )

    if parsed.bozo:

        log(
            f"Warning: feed parser reported "
            f"an issue for {name}: "
            f"{parsed.bozo_exception}"
        )


    entries = parsed.entries

    log(
        f"{name}: {len(entries)} feed entries found"
    )

    articles = []


    for entry in entries:

        if len(articles) >= MAX_ARTICLES_PER_SOURCE:

            break

        try:

            title = clean_text(
                entry.get(
                    "title",
                    "",
                )
            )

            if not title:

                continue


            link = str(
                entry.get(
                    "link",
                    "",
                )
            ).strip()

            if not link:

                continue


            published = parse_entry_date(
                entry
            )


            if not is_recent(
                published
            ):

                continue


            description = clean_text(
                entry.get(
                    "summary",
                    "",
                )
                or entry.get(
                    "description",
                    "",
                )
                or entry.get(
                    "content",
                    "",
                )
            )


            guid = str(
                entry.get(
                    "id",
                    "",
                )
                or entry.get(
                    "guid",
                    "",
                )
                or link
            )


            category = detect_category(
                source["category"],
                title,
                description,
            )


            image = extract_image(
                entry
            )


            article = {

                "id": create_article_id(
                    guid
                ),

                "title": title,

                "description": create_excerpt(
                    description
                ),

                "url": link,

                "image": image,

                "source": source["name"],

                "sourceWebsite": source[
                    "website"
                ],

                "mainCategory": source[
                    "category"
                ],

                "category": category,

                "published": published.isoformat(),

                "publishedTimestamp": int(
                    published.timestamp()
                    * 1000
                ),
            }


            articles.append(
                article
            )


        except Exception as error:

            log(
                f"Article parsing error "
                f"in {name}: {error}"
            )


    log(
        f"{name}: {len(articles)} recent articles accepted"
    )

    return articles


# ============================================================
# DEDUPLICATION
# ============================================================

def remove_duplicates(
    articles: list[dict],
) -> list[dict]:
    """Remove duplicate articles by URL and title."""

    seen_titles = set()

    seen_urls = set()

    result = []


    for article in articles:

        title_key = normalize_title(
            article.get(
                "title",
                "",
            )
        )

        url_key = normalize_url(
            article.get(
                "url",
                "",
            )
        )


        if not title_key and not url_key:

            continue


        if (
            title_key in seen_titles
            or url_key in seen_urls
        ):

            continue


        seen_titles.add(
            title_key
        )

        seen_urls.add(
            url_key
        )

        result.append(
            article
        )


    return result


# ============================================================
# FETCH ALL NEWS
# ============================================================

def fetch_all_news() -> list[dict]:
    """Fetch articles from all active sources."""

    all_articles = []


    active_sources = [
        source
        for source in NEWS_SOURCES
        if source.get(
            "active",
            False,
        )
    ]


    log(
        f"Active news sources: "
        f"{len(active_sources)}"
    )


    for source in active_sources:

        try:

            articles = fetch_feed(
                source
            )

            all_articles.extend(
                articles
            )

        except requests.RequestException as error:

            log(
                f"Source failed: "
                f"{source['name']} | "
                f"{error}"
            )

        except Exception as error:

            log(
                f"Unexpected source error: "
                f"{source['name']} | "
                f"{error}"
            )


    log(
        f"Total articles before deduplication: "
        f"{len(all_articles)}"
    )


    unique_articles = remove_duplicates(
        all_articles
    )


    log(
        f"Total articles after deduplication: "
        f"{len(unique_articles)}"
    )


    unique_articles.sort(
        key=lambda article: article.get(
            "publishedTimestamp",
            0,
        ),
        reverse=True,
    )


    return unique_articles[
        :MAX_ARTICLES
    ]


# ============================================================
# CREATE OUTPUT
# ============================================================

def create_news_document(
    articles: list[dict],
) -> dict:
    """Create the final news.json structure."""

    now = datetime.now(
        timezone.utc
    ).isoformat()


    return {

        "success": True,

        "updatedAt": now,

        "serverTime": now,

        "total": len(
            articles
        ),

        "articles": articles,

        "metadata": {

            "generator": "TechPulse News Engine",

            "version": "1.0",

            "articleAgeHours":
                MAX_ARTICLE_AGE_HOURS,

            "sourceCount":
                len(
                    [
                        source
                        for source in NEWS_SOURCES
                        if source.get(
                            "active",
                            False,
                        )
                    ]
                ),

        },
    }


# ============================================================
# WRITE JSON
# ============================================================

def write_news_json(
    data: dict,
) -> None:
    """Write news data to repository root."""

    NEWS_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )


    temporary_file = NEWS_FILE.with_suffix(
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


    temporary_file.replace(
        NEWS_FILE
    )


    log(
        f"news.json written successfully: "
        f"{NEWS_FILE}"
    )


# ============================================================
# MAIN
# ============================================================

def main() -> int:

    log(
        "================================================"
    )

    log(
        "TECHPULSE NEWS ENGINE STARTED"
    )

    log(
        "================================================"
    )

    log(
        f"Repository root: {BASE_DIR}"
    )

    log(
        f"Output file: {NEWS_FILE}"
    )


    try:

        articles = fetch_all_news()


        if not articles:

            log(
                "WARNING: No recent articles were found."
            )

            # Do not destroy an existing valid news.json
            # if every feed temporarily fails.

            if NEWS_FILE.exists():

                log(
                    "Existing news.json will be preserved."
                )

                return 0


        data = create_news_document(
            articles
        )


        write_news_json(
            data
        )


        log(
            "================================================"
        )

        log(
            f"SUCCESS: {len(articles)} articles generated."
        )

        log(
            "================================================"
        )


        return 0


    except Exception as error:

        log(
            f"FATAL ERROR: {error}"
        )

        return 1


# ============================================================
# SCRIPT ENTRY POINT
# ============================================================

if __name__ == "__main__":

    sys.exit(
        main()
    )
