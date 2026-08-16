"""
TechPulse News Fetcher
======================

Architecture:

    RSS Feeds
        ↓
    fetch_news.py
        ↓
    Parse RSS
        ↓
    Clean metadata
        ↓
    Categorize
        ↓
    Remove duplicates
        ↓
    Sort by date
        ↓
    news.json
        ↓
    GitHub Pages

Important:
- No Google Apps Script
- No Google Sheets
- No database
- No company logos
- No full article copying
- Only headline, short excerpt/metadata, source, date and original URL
"""

from __future__ import annotations

import hashlib
import html
import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import urlparse

import feedparser
import requests
from bs4 import BeautifulSoup


# ============================================================
# CONFIGURATION
# ============================================================

OUTPUT_FILE = "news.json"

MAX_ARTICLES = 120

MAX_ARTICLES_PER_FEED = 20

REQUEST_TIMEOUT = 20

USER_AGENT = (
    "TechPulseNewsBot/1.0 "
    "(RSS metadata aggregator; contact site administrator)"
)

# Keep articles from the recent period.
# RSS feeds sometimes contain older entries.
MAX_ARTICLE_AGE_DAYS = 7


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger("TechPulse")


# ============================================================
# RSS SOURCES
# ============================================================
#
# We do not display publisher logos.
#
# "source" is used only as textual attribution.
#
# Feed URLs can be changed later without changing
# the frontend.
#
# Some feeds cover multiple topics. Keyword classification
# below determines the final TechPulse category.
# ============================================================

FEEDS = [

    # --------------------------------------------------------
    # TECHNOLOGY
    # --------------------------------------------------------

    {
        "name": "Ars Technica",
        "url": "https://feeds.arstechnica.com/arstechnica/index",
        "mainCategory": "Technology",
        "defaultCategory": "Emerging Technology",
    },

    {
        "name": "WIRED",
        "url": "https://www.wired.com/feed/rss",
        "mainCategory": "Technology",
        "defaultCategory": "Emerging Technology",
    },

    {
        "name": "TechCrunch",
        "url": "https://techcrunch.com/feed/",
        "mainCategory": "Technology",
        "defaultCategory": "Software & Applications",
    },

    {
        "name": "Engadget",
        "url": "https://www.engadget.com/rss.xml",
        "mainCategory": "Technology",
        "defaultCategory": "Hardware & Devices",
    },

    # --------------------------------------------------------
    # GAMING
    # --------------------------------------------------------

    {
        "name": "Eurogamer",
        "url": "https://www.eurogamer.net/?format=rss",
        "mainCategory": "Gaming",
        "defaultCategory": "Gaming Updates",
    },

    {
        "name": "PC Gamer",
        "url": "https://www.pcgamer.com/rss/",
        "mainCategory": "Gaming",
        "defaultCategory": "PC Gaming",
    },

    # --------------------------------------------------------
    # ADDITIONAL TECHNOLOGY / SCIENCE
    # --------------------------------------------------------

    {
        "name": "New Scientist",
        "url": "https://www.newscientist.com/feed/home/",
        "mainCategory": "Technology",
        "defaultCategory": "Science & Innovation",
    },

]


# ============================================================
# CATEGORY KEYWORDS
# ============================================================

CATEGORY_KEYWORDS = {

    "Artificial Intelligence": [
        "artificial intelligence",
        "machine learning",
        "deep learning",
        "generative ai",
        "generative artificial intelligence",
        "large language model",
        "language model",
        "llm",
        "chatbot",
        "ai model",
        "ai agent",
        "ai assistant",
        "neural network",
        "computer vision",
        "openai",
        "chatgpt",
        "gemini",
        "claude",
        "copilot",
    ],

    "Smartphones & Mobile": [
        "smartphone",
        "smartphones",
        "iphone",
        "android phone",
        "mobile phone",
        "mobile device",
        "pixel phone",
        "galaxy phone",
        "foldable phone",
        "folding phone",
        "mobile processor",
        "mobile chipset",
        "5g",
        "6g",
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
        "vulnerabilities",
        "exploit",
        "data breach",
        "security breach",
        "credential theft",
        "identity theft",
        "botnet",
        "spyware",
        "infostealer",
        "security patch",
    ],

    "Cloud & Infrastructure": [
        "cloud computing",
        "cloud infrastructure",
        "cloud service",
        "cloud services",
        "kubernetes",
        "container",
        "containers",
        "docker",
        "server",
        "servers",
        "datacenter",
        "data center",
        "virtualization",
        "linux",
        "ubuntu",
        "red hat",
        "oracle linux",
        "infrastructure",
        "devops",
        "terraform",
        "ansible",
    ],

    "Software & Applications": [
        "software",
        "application",
        "applications",
        "app",
        "apps",
        "operating system",
        "windows",
        "macos",
        "browser",
        "web browser",
        "productivity",
        "database",
        "developer tools",
    ],

    "Hardware & Devices": [
        "hardware",
        "processor",
        "cpu",
        "gpu",
        "graphics card",
        "motherboard",
        "laptop",
        "desktop",
        "monitor",
        "memory",
        "ssd",
        "storage",
        "chip",
        "semiconductor",
        "device",
        "devices",
        "wearable",
        "smartwatch",
    ],

    "Internet & Web": [
        "internet",
        "web",
        "website",
        "online",
        "social media",
        "search engine",
        "streaming",
        "browser",
        "internet service",
        "broadband",
        "wifi",
        "wi-fi",
    ],

    "Emerging Technology": [
        "robotics",
        "robot",
        "quantum computing",
        "quantum computer",
        "autonomous",
        "self-driving",
        "augmented reality",
        "virtual reality",
        "mixed reality",
        "ar glasses",
        "vr headset",
        "3d printing",
        "automation",
    ],

    "Science & Innovation": [
        "science",
        "scientist",
        "research",
        "space",
        "nasa",
        "astronomy",
        "physics",
        "biology",
        "genetics",
        "medical technology",
        "biotechnology",
        "biotech",
        "climate technology",
        "energy technology",
    ],

    "Business & Technology": [
        "startup",
        "startups",
        "venture capital",
        "funding",
        "investment",
        "acquisition",
        "merger",
        "technology company",
        "tech company",
        "enterprise",
        "business technology",
    ],

    # --------------------------------------------------------
    # GAMING
    # --------------------------------------------------------

    "PC Gaming": [
        "pc gaming",
        "pc game",
        "pc games",
        "steam",
        "gaming pc",
        "graphics card",
        "gpu",
        "windows gaming",
    ],

    "Console Gaming": [
        "console gaming",
        "console game",
        "console games",
        "playstation",
        "xbox",
        "nintendo",
        "console",
    ],

    "Mobile Gaming": [
        "mobile gaming",
        "mobile game",
        "mobile games",
        "ios game",
        "android game",
        "mobile gamer",
    ],

    "Game Releases": [
        "game release",
        "game releases",
        "launches",
        "launched",
        "release date",
        "new game",
        "new games",
        "coming soon",
    ],

    "Gaming Hardware": [
        "gaming hardware",
        "gaming headset",
        "gaming monitor",
        "gaming keyboard",
        "gaming mouse",
        "gaming laptop",
        "gaming pc",
        "graphics card",
        "gpu",
        "controller",
    ],

    "Esports": [
        "esports",
        "e-sports",
        "competitive gaming",
        "tournament",
        "gaming tournament",
    ],

    "Game Development": [
        "game development",
        "game developer",
        "game engine",
        "unity",
        "unreal engine",
        "developer studio",
        "development studio",
    ],

    "Gaming Industry": [
        "gaming industry",
        "game studio",
        "publisher",
        "game publisher",
        "gaming company",
        "video game industry",
    ],

    "Gaming Updates": [
        "gaming update",
        "game update",
        "patch",
        "dlc",
        "expansion",
        "season update",
        "player update",
    ],

    "Reviews & Features": [
        "game review",
        "gaming review",
        "review:",
        "hands-on",
        "preview",
        "gaming feature",
    ],

}


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
            "text/html;q=0.9, "
            "*/*;q=0.8"
        ),
    }
)


# ============================================================
# HELPERS
# ============================================================

def clean_text(value: Any) -> str:
    """
    Convert HTML/RSS content to clean readable text.
    """

    if value is None:
        return ""

    value = str(value)

    if not value.strip():
        return ""

    value = html.unescape(value)

    soup = BeautifulSoup(value, "html.parser")

    text = soup.get_text(" ", strip=True)

    text = re.sub(r"\s+", " ", text)

    return text.strip()


def truncate_text(text: str, limit: int = 360) -> str:
    """
    Keep descriptions short.
    """

    text = clean_text(text)

    if len(text) <= limit:
        return text

    shortened = text[:limit].rsplit(" ", 1)[0]

    return shortened.rstrip(".,;:") + "…"


def normalize_url(url: str) -> str:
    """
    Remove common tracking parameters while preserving
    the original article destination.
    """

    if not url:
        return ""

    url = html.unescape(str(url)).strip()

    return url


def canonical_key(url: str) -> str:
    """
    Generate a normalized URL key for duplicate detection.
    """

    if not url:
        return ""

    parsed = urlparse(url)

    host = parsed.netloc.lower()

    path = parsed.path.rstrip("/")

    key = host + path

    return key


def normalize_title(title: str) -> str:
    """
    Normalize title for duplicate detection.
    """

    title = clean_text(title).lower()

    title = re.sub(
        r"[^a-z0-9\s]",
        " ",
        title,
    )

    title = re.sub(
        r"\s+",
        " ",
        title,
    )

    return title.strip()


def create_article_id(
    title: str,
    url: str,
) -> str:
    """
    Create stable article ID.
    """

    raw = (
        normalize_title(title)
        + "|"
        + normalize_url(url)
    )

    digest = hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()[:16]

    return "techpulse-" + digest


def parse_date(value: Any) -> datetime | None:
    """
    Convert RSS dates to timezone-aware UTC datetime.
    """

    if not value:
        return None

    # feedparser parsed time tuple
    if isinstance(value, tuple):

        try:

            timestamp = time.mktime(value)

            return datetime.fromtimestamp(
                timestamp,
                tz=timezone.utc,
            )

        except Exception:
            pass

    value = str(value).strip()

    if not value:
        return None

    # ISO format
    try:

        parsed = datetime.fromisoformat(
            value.replace(
                "Z",
                "+00:00",
            )
        )

        if parsed.tzinfo is None:

            parsed = parsed.replace(
                tzinfo=timezone.utc
            )

        return parsed.astimezone(
            timezone.utc
        )

    except Exception:
        pass

    # RFC date
    try:

        parsed = parsedate_to_datetime(
            value
        )

        if parsed.tzinfo is None:

            parsed = parsed.replace(
                tzinfo=timezone.utc
            )

        return parsed.astimezone(
            timezone.utc
        )

    except Exception:
        pass

    return None


def get_entry_date(
    entry: Any,
) -> datetime:

    candidates = [

        entry.get("published"),

        entry.get("updated"),

        entry.get("created"),

        entry.get("pubDate"),

        entry.get("published_parsed"),

        entry.get("updated_parsed"),

        entry.get("created_parsed"),

    ]

    for candidate in candidates:

        parsed = parse_date(candidate)

        if parsed:

            return parsed

    return datetime.now(
        timezone.utc
    )


# ============================================================
# IMAGE EXTRACTION
# ============================================================

def extract_image(entry: Any) -> str:
    """
    Extract image URL from RSS metadata only.

    No logos are generated or displayed.
    """

    # media:content / media_thumbnail
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

            url = media.get("url")

            if url:
                return str(url)

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

            url = media.get("url")

            if url:
                return str(url)

    # enclosure
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

            media_type = str(
                enclosure.get(
                    "type",
                    "",
                )
            ).lower()

            url = enclosure.get(
                "href"
            ) or enclosure.get(
                "url"
            )

            if (
                url
                and (
                    media_type.startswith(
                        "image/"
                    )
                    or not media_type
                )
            ):

                return str(url)

    # RSS image element
    image = entry.get("image")

    if isinstance(
        image,
        dict,
    ):

        url = image.get("href")

        if url:
            return str(url)

        url = image.get("url")

        if url:
            return str(url)

    return ""


# ============================================================
# CATEGORY CLASSIFICATION
# ============================================================

def classify_article(
    title: str,
    description: str,
    feed: dict[str, Any],
) -> tuple[str, str]:

    text = (
        clean_text(title)
        + " "
        + clean_text(description)
    ).lower()

    scores: dict[str, int] = {}

    for category, keywords in CATEGORY_KEYWORDS.items():

        score = 0

        for keyword in keywords:

            keyword = keyword.lower()

            if keyword in text:

                # Give title-related keywords slightly
                # more importance.
                if keyword in title.lower():

                    score += 3

                else:

                    score += 1

        if score > 0:

            scores[category] = score

    if scores:

        best_category = max(
            scores,
            key=scores.get,
        )

        return (
            feed["mainCategory"],
            best_category,
        )

    return (
        feed["mainCategory"],
        feed["defaultCategory"],
    )


# ============================================================
# FETCH FEED
# ============================================================

def fetch_feed(
    feed: dict[str, Any],
) -> list[dict[str, Any]]:

    name = feed["name"]

    url = feed["url"]

    logger.info(
        "Fetching: %s",
        name,
    )

    try:

        response = SESSION.get(
            url,
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()

        content = response.content

        parsed = feedparser.parse(
            content
        )

    except Exception as exc:

        logger.warning(
            "Feed failed: %s | %s",
            name,
            exc,
        )

        return []

    if getattr(
        parsed,
        "bozo",
        False,
    ):

        logger.warning(
            "Feed parser warning: %s",
            name,
        )

    entries = getattr(
        parsed,
        "entries",
        [],
    )

    logger.info(
        "%s entries received from %s",
        len(entries),
        name,
    )

    articles = []

    for entry in entries[
        :MAX_ARTICLES_PER_FEED
    ]:

        title = clean_text(
            entry.get(
                "title",
                "",
            )
        )

        if not title:
            continue

        url_value = (
            entry.get("link")
            or entry.get("id")
            or ""
        )

        article_url = normalize_url(
            url_value
        )

        if not article_url:

            continue

        description = clean_text(
            entry.get(
                "summary",
                "",
            )
        )

        if not description:

            description = clean_text(
                entry.get(
                    "description",
                    "",
                )
            )

        # Avoid publishing huge RSS descriptions.
        description = truncate_text(
            description,
            360,
        )

        published = get_entry_date(
            entry
        )

        image = extract_image(
            entry
        )

        main_category, category = (
            classify_article(
                title,
                description,
                feed,
            )
        )

        article_id = create_article_id(
            title,
            article_url,
        )

        article = {

            "id": article_id,

            "title": title,

            "description": (
                description
                or "Read the latest story from the original publisher."
            ),

            "url": article_url,

            "image": image,

            "category": category,

            "mainCategory": main_category,

            "source": name,

            "published": (
                published
                .astimezone(
                    timezone.utc
                )
                .isoformat()
                .replace(
                    "+00:00",
                    "Z",
                )
            ),

        }

        articles.append(
            article
        )

    return articles


# ============================================================
# DUPLICATE DETECTION
# ============================================================

def remove_duplicates(
    articles: list[dict[str, Any]],
) -> list[dict[str, Any]]:

    unique = []

    seen_ids = set()

    seen_urls = set()

    seen_titles = set()

    for article in articles:

        article_id = article["id"]

        url_key = canonical_key(
            article["url"]
        )

        title_key = normalize_title(
            article["title"]
        )

        if article_id in seen_ids:

            continue

        if url_key and url_key in seen_urls:

            continue

        if title_key and title_key in seen_titles:

            continue

        seen_ids.add(
            article_id
        )

        if url_key:
            seen_urls.add(
                url_key
            )

        if title_key:
            seen_titles.add(
                title_key
            )

        unique.append(
            article
        )

    logger.info(
        "Duplicate filtering: %d unique articles",
        len(unique),
    )

    return unique


# ============================================================
# FILTER OLD ARTICLES
# ============================================================

def filter_recent_articles(
    articles: list[dict[str, Any]],
) -> list[dict[str, Any]]:

    now = datetime.now(
        timezone.utc
    )

    cutoff = (
        now.timestamp()
        - (
            MAX_ARTICLE_AGE_DAYS
            * 24
            * 60
            * 60
        )
    )

    recent = []

    for article in articles:

        published = parse_date(
            article["published"]
        )

        if not published:

            recent.append(
                article
            )

            continue

        if published.timestamp() >= cutoff:

            recent.append(
                article
            )

    return recent


# ============================================================
# SORT ARTICLES
# ============================================================

def sort_articles(
    articles: list[dict[str, Any]],
) -> list[dict[str, Any]]:

    return sorted(
        articles,
        key=lambda article: (
            parse_date(
                article["published"]
            )
            or datetime.min.replace(
                tzinfo=timezone.utc
            )
        ),
        reverse=True,
    )


# ============================================================
# VALIDATE ARTICLE
# ============================================================

def validate_article(
    article: dict[str, Any],
) -> bool:

    required_fields = [

        "id",
        "title",
        "description",
        "url",
        "category",
        "mainCategory",
        "source",
        "published",

    ]

    for field in required_fields:

        if not article.get(field):

            return False

    if not article["url"].startswith(
        (
            "http://",
            "https://",
        )
    ):

        return False

    if article["mainCategory"] not in (
        "Technology",
        "Gaming",
    ):

        return False

    return True


# ============================================================
# WRITE NEWS.JSON
# ============================================================

def write_news_json(
    articles: list[dict[str, Any]],
) -> None:

    now = datetime.now(
        timezone.utc
    )

    output = {

        "success": True,

        "updatedAt": (
            now.isoformat()
            .replace(
                "+00:00",
                "Z",
            )
        ),

        "total": len(
            articles
        ),

        "articles": articles,

    }

    output_directory = os.path.dirname(
        OUTPUT_FILE
    )

    if output_directory:

        os.makedirs(
            output_directory,
            exist_ok=True,
        )

    temporary_file = (
        OUTPUT_FILE +
        ".tmp"
    )

    with open(
        temporary_file,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            output,
            file,
            ensure_ascii=False,
            indent=2,
        )

        file.write("\n")

    os.replace(
        temporary_file,
        OUTPUT_FILE,
    )

    logger.info(
        "Wrote %d articles to %s",
        len(articles),
        OUTPUT_FILE,
    )


# ============================================================
# MAIN
# ============================================================

def main() -> None:

    logger.info(
        "============================================"
    )

    logger.info(
        "TechPulse News Fetcher Starting"
    )

    logger.info(
        "============================================"
    )

    all_articles: list[
        dict[str, Any]
    ] = []

    successful_feeds = 0

    failed_feeds = 0

    # --------------------------------------------------------
    # FETCH ALL RSS SOURCES
    # --------------------------------------------------------

    for feed in FEEDS:

        articles = fetch_feed(
            feed
        )

        if articles:

            successful_feeds += 1

            all_articles.extend(
                articles
            )

        else:

            failed_feeds += 1

    logger.info(
        "Feeds successful: %d",
        successful_feeds,
    )

    logger.info(
        "Feeds failed: %d",
        failed_feeds,
    )

    logger.info(
        "Total raw articles: %d",
        len(all_articles),
    )

    # --------------------------------------------------------
    # REMOVE OLD STORIES
    # --------------------------------------------------------

    all_articles = (
        filter_recent_articles(
            all_articles
        )
    )

    logger.info(
        "After date filtering: %d",
        len(all_articles),
    )

    # --------------------------------------------------------
    # REMOVE DUPLICATES
    # --------------------------------------------------------

    all_articles = (
        remove_duplicates(
            all_articles
        )
    )

    # --------------------------------------------------------
    # VALIDATE
    # --------------------------------------------------------

    valid_articles = []

    for article in all_articles:

        if validate_article(
            article
        ):

            valid_articles.append(
                article
            )

    all_articles = valid_articles

    logger.info(
        "After validation: %d",
        len(all_articles),
    )

    # --------------------------------------------------------
    # SORT NEWEST FIRST
    # --------------------------------------------------------

    all_articles = sort_articles(
        all_articles
    )

    # --------------------------------------------------------
    # LIMIT TOTAL
    # --------------------------------------------------------

    all_articles = all_articles[
        :MAX_ARTICLES
    ]

    # --------------------------------------------------------
    # SAFETY CHECK
    # --------------------------------------------------------
    #
    # IMPORTANT:
    #
    # If every feed fails, do NOT replace an existing
    # working news.json with an empty file.
    #
    # This prevents a temporary RSS outage from making
    # the website completely empty.
    #

    if not all_articles:

        logger.error(
            "No valid articles were collected."
        )

        if os.path.exists(
            OUTPUT_FILE
        ):

            logger.warning(
                "Keeping existing news.json."
            )

            return

        logger.error(
            "No existing news.json found."
        )

        raise SystemExit(
            1
        )

    # --------------------------------------------------------
    # WRITE OUTPUT
    # --------------------------------------------------------

    write_news_json(
        all_articles
    )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    technology_count = sum(
        1
        for article in all_articles
        if article["mainCategory"]
        == "Technology"
    )

    gaming_count = sum(
        1
        for article in all_articles
        if article["mainCategory"]
        == "Gaming"
    )

    logger.info(
        "Technology articles: %d",
        technology_count,
    )

    logger.info(
        "Gaming articles: %d",
        gaming_count,
    )

    logger.info(
        "============================================"
    )

    logger.info(
        "TechPulse News Fetcher Completed"
    )

    logger.info(
        "============================================"
    )


if __name__ == "__main__":

    main()
