#!/usr/bin/env python3

"""
TechPulse News Fetcher

Architecture:

RSS feeds
   ↓
Fetch
   ↓
Parse
   ↓
Normalize
   ↓
Categorize
   ↓
Remove duplicates
   ↓
Sort newest first
   ↓
Keep latest articles
   ↓
Write news.json

No Google Apps Script.
No database.
No publisher logos.
No full article reproduction.
"""

from __future__ import annotations

import hashlib
import html
import json
import logging
import os
import re
import sys
import tempfile
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import feedparser
import requests
from bs4 import BeautifulSoup


# ============================================================
# CONFIGURATION
# ============================================================

ROOT_DIR = Path(__file__).resolve().parent.parent

OUTPUT_FILE = ROOT_DIR / "news.json"

MAX_ARTICLES = 200

MAX_ARTICLES_PER_FEED = 40

REQUEST_TIMEOUT = 20

USER_AGENT = (
    "TechPulse-NewsBot/1.0 "
    "(RSS reader; headlines and metadata only)"
)


# ============================================================
# RSS SOURCES
# ============================================================
#
# These are RSS endpoints, not copied website pages.
#
# We do NOT display publisher logos.
#
# The website displays headlines/excerpts and links
# users to the original article.
#
# If a feed becomes unavailable, it is simply skipped.
#
# ============================================================

FEEDS = [

    # -------------------------
    # TECHNOLOGY
    # -------------------------

    {
        "name": "Technology Feed",
        "url": "https://feeds.arstechnica.com/arstechnica/index",
        "mainCategory": "Technology",
        "category": "Technology",
    },

    {
        "name": "AI Feed",
        "url": "https://www.artificialintelligence-news.com/feed/",
        "mainCategory": "Technology",
        "category": "Artificial Intelligence",
    },

    {
        "name": "Cloud Feed",
        "url": "https://www.cloudcomputing-news.net/feed/",
        "mainCategory": "Technology",
        "category": "Cloud & Infrastructure",
    },

    {
        "name": "Cybersecurity Feed",
        "url": "https://feeds.feedburner.com/TheHackersNews",
        "mainCategory": "Technology",
        "category": "Cybersecurity",
    },

    {
        "name": "Developer Feed",
        "url": "https://dev.to/feed",
        "mainCategory": "Technology",
        "category": "Software & Applications",
    },

    # -------------------------
    # GAMING
    # -------------------------

    {
        "name": "Gaming Feed",
        "url": "https://www.pcgamer.com/rss/",
        "mainCategory": "Gaming",
        "category": "PC Gaming",
    },

    {
        "name": "Gaming News Feed",
        "url": "https://www.gamespot.com/feeds/mashup/",
        "mainCategory": "Gaming",
        "category": "Gaming Updates",
    },

    {
        "name": "Gaming Feed",
        "url": "https://www.eurogamer.net/feed",
        "mainCategory": "Gaming",
        "category": "Gaming Updates",
    },

]


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger("techpulse")


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
            "*/*;q=0.8"
        ),
    }
)


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_text(value: Any, max_length: int = 500) -> str:
    """
    Convert HTML/XML content into clean readable text.
    """

    if value is None:
        return ""

    value = str(value)

    if not value.strip():
        return ""

    try:
        soup = BeautifulSoup(value, "html.parser")

        text = soup.get_text(
            " ",
            strip=True,
        )

    except Exception:
        text = value

    text = html.unescape(text)

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    text = text.strip()

    if len(text) > max_length:
        text = text[:max_length].rstrip() + "..."

    return text


# ============================================================
# URL CLEANING
# ============================================================

def clean_url(url: Any) -> str:
    """
    Validate article URLs.
    """

    if not url:
        return ""

    url = str(url).strip()

    if not re.match(
        r"^https?://",
        url,
        re.IGNORECASE,
    ):
        return ""

    return url


# ============================================================
# IMAGE EXTRACTION
# ============================================================

def extract_image(entry: Any) -> str:
    """
    Extract an RSS-provided article image when available.

    No publisher logos are generated or copied.
    """

    try:

        media_content = entry.get(
            "media_content",
            [],
        )

        if media_content:

            for item in media_content:

                url = clean_url(
                    item.get("url")
                )

                if url:
                    return url

    except Exception:
        pass

    try:

        media_thumbnail = entry.get(
            "media_thumbnail",
            [],
        )

        if media_thumbnail:

            for item in media_thumbnail:

                url = clean_url(
                    item.get("url")
                )

                if url:
                    return url

    except Exception:
        pass

    try:

        enclosures = entry.get(
            "enclosures",
            [],
        )

        for enclosure in enclosures:

            url = clean_url(
                enclosure.get("href")
                or enclosure.get("url")
            )

            mime_type = str(
                enclosure.get("type", "")
            ).lower()

            if url and (
                mime_type.startswith("image/")
                or re.search(
                    r"\.(jpg|jpeg|png|webp|gif)(\?|$)",
                    url,
                    re.IGNORECASE,
                )
            ):
                return url

    except Exception:
        pass

    return ""


# ============================================================
# DATE PARSING
# ============================================================

def parse_date(entry: Any) -> str:
    """
    Convert RSS publication dates to UTC ISO format.
    """

    candidates = [
        entry.get("published"),
        entry.get("updated"),
        entry.get("created"),
    ]

    for value in candidates:

        if not value:
            continue

        value = str(value).strip()

        try:

            dt = parsedate_to_datetime(
                value
            )

            if dt.tzinfo is None:

                dt = dt.replace(
                    tzinfo=timezone.utc
                )

            dt = dt.astimezone(
                timezone.utc
            )

            return dt.isoformat()

        except Exception:
            pass

    return datetime.now(
        timezone.utc
    ).isoformat()


# ============================================================
# CATEGORY DETECTION
# ============================================================

def detect_category(
    title: str,
    description: str,
    default_category: str,
    main_category: str,
) -> str:

    text = (
        f"{title} "
        f"{description}"
    ).lower()

    if main_category == "Gaming":

        if any(
            word in text
            for word in [
                "playstation",
                "ps5",
                "ps4",
                "sony console",
            ]
        ):
            return "Console Gaming"

        if any(
            word in text
            for word in [
                "xbox",
                "series x",
                "series s",
            ]
        ):
            return "Console Gaming"

        if any(
            word in text
            for word in [
                "nintendo",
                "switch",
                "switch 2",
            ]
        ):
            return "Console Gaming"

        if any(
            word in text
            for word in [
                "esports",
                "e-sports",
                "competitive gaming",
            ]
        ):
            return "Esports"

        if any(
            word in text
            for word in [
                "mobile game",
                "mobile gaming",
                "android game",
                "ios game",
            ]
        ):
            return "Mobile Gaming"

        if any(
            word in text
            for word in [
                "game release",
                "launches",
                "released",
                "release date",
            ]
        ):
            return "Game Releases"

        if any(
            word in text
            for word in [
                "gpu",
                "graphics card",
                "gaming laptop",
                "gaming monitor",
                "gaming pc",
                "gaming hardware",
            ]
        ):
            return "Gaming Hardware"

        if any(
            word in text
            for word in [
                "review",
                "hands-on",
                "preview",
            ]
        ):
            return "Reviews & Features"

        return default_category or "Gaming Updates"

    # -------------------------
    # TECHNOLOGY
    # -------------------------

    if any(
        word in text
        for word in [
            "artificial intelligence",
            "generative ai",
            "machine learning",
            "large language model",
            "chatbot",
            "ai model",
        ]
    ):
        return "Artificial Intelligence"

    if any(
        word in text
        for word in [
            "cybersecurity",
            "cyber security",
            "malware",
            "ransomware",
            "phishing",
            "vulnerability",
            "zero-day",
            "data breach",
        ]
    ):
        return "Cybersecurity"

    if any(
        word in text
        for word in [
            "cloud computing",
            "cloud infrastructure",
            "kubernetes",
            "container",
            "aws",
            "azure",
            "cloud service",
        ]
    ):
        return "Cloud & Infrastructure"

    if any(
        word in text
        for word in [
            "iphone",
            "android",
            "smartphone",
            "mobile phone",
            "pixel phone",
            "mobile device",
        ]
    ):
        return "Smartphones & Mobile"

    if any(
        word in text
        for word in [
            "laptop",
            "processor",
            "cpu",
            "gpu",
            "graphics card",
            "computer hardware",
            "ssd",
            "memory",
        ]
    ):
        return "Hardware & Devices"

    if any(
        word in text
        for word in [
            "linux",
            "windows",
            "macos",
            "software",
            "application",
            "developer",
            "programming",
            "github",
            "python",
            "javascript",
        ]
    ):
        return "Software & Applications"

    if any(
        word in text
        for word in [
            "startup",
            "technology company",
            "enterprise technology",
            "tech industry",
        ]
    ):
        return "Business & Technology"

    if any(
        word in text
        for word in [
            "internet",
            "browser",
            "web",
            "search engine",
            "social media",
        ]
    ):
        return "Internet & Web"

    return default_category or "Technology"


# ============================================================
# ARTICLE ID
# ============================================================

def create_article_id(
    title: str,
    url: str,
) -> str:

    normalized_title = re.sub(
        r"\s+",
        " ",
        title.lower().strip(),
    )

    normalized_url = url.lower().strip()

    raw = (
        normalized_title
        + "|"
        + normalized_url
    )

    digest = hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()[:20]

    return "techpulse-" + digest


# ============================================================
# TITLE NORMALIZATION
# ============================================================

def normalize_title(title: str) -> str:

    title = clean_text(
        title,
        300,
    )

    title = title.lower()

    title = re.sub(
        r"[^a-z0-9\s]",
        "",
        title,
    )

    title = re.sub(
        r"\s+",
        " ",
        title,
    )

    return title.strip()


# ============================================================
# DUPLICATE DETECTION
# ============================================================

def are_similar_titles(
    title1: str,
    title2: str,
) -> bool:

    a = set(
        normalize_title(title1).split()
    )

    b = set(
        normalize_title(title2).split()
    )

    if not a or not b:
        return False

    intersection = len(
        a.intersection(b)
    )

    union = len(
        a.union(b)
    )

    similarity = (
        intersection / union
        if union
        else 0
    )

    return similarity >= 0.70


# ============================================================
# FETCH FEED
# ============================================================

def fetch_feed(
    feed_config: dict[str, Any],
) -> list[dict[str, Any]]:

    name = feed_config["name"]

    url = feed_config["url"]

    main_category = (
        feed_config["mainCategory"]
    )

    default_category = (
        feed_config["category"]
    )

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

        if getattr(
            parsed,
            "bozo",
            False,
        ):
            logger.warning(
                "%s returned a feed parsing warning.",
                name,
            )

        entries = getattr(
            parsed,
            "entries",
            [],
        )

        if not entries:

            logger.warning(
                "%s returned no articles.",
                name,
            )

            return []

        articles = []

        for entry in entries[
            :MAX_ARTICLES_PER_FEED
        ]:

            title = clean_text(
                entry.get("title"),
                300,
            )

            article_url = clean_url(
                entry.get("link")
            )

            if not title or not article_url:
                continue

            description = clean_text(
                entry.get("summary")
                or entry.get("description")
                or "",
                600,
            )

            published = parse_date(
                entry
            )

            category = detect_category(
                title,
                description,
                default_category,
                main_category,
            )

            image = extract_image(
                entry
            )

            article = {

                "id": create_article_id(
                    title,
                    article_url,
                ),

                "title": title,

                "description": (
                    description
                    or "Read the latest story from the original publisher."
                ),

                "url": article_url,

                "image": image,

                "category": category,

                "mainCategory": main_category,

                # Generic source label.
                # No publisher branding/logos are used.
                "source": "News Source",

                "published": published,

            }

            articles.append(
                article
            )

        logger.info(
            "%s: %d articles",
            name,
            len(articles),
        )

        return articles

    except requests.RequestException as exc:

        logger.warning(
            "Feed failed: %s | %s",
            name,
            exc,
        )

        return []

    except Exception as exc:

        logger.exception(
            "Unexpected feed error: %s | %s",
            name,
            exc,
        )

        return []


# ============================================================
# DEDUPLICATE ARTICLES
# ============================================================

def deduplicate_articles(
    articles: list[dict[str, Any]],
) -> list[dict[str, Any]]:

    unique = []

    seen_urls = set()

    seen_titles = []

    for article in articles:

        url = article["url"]

        title = article["title"]

        if url in seen_urls:
            continue

        duplicate = False

        for previous_title in seen_titles:

            if are_similar_titles(
                title,
                previous_title,
            ):
                duplicate = True
                break

        if duplicate:
            continue

        seen_urls.add(url)

        seen_titles.append(title)

        unique.append(article)

    return unique


# ============================================================
# SORT ARTICLES
# ============================================================

def sort_articles(
    articles: list[dict[str, Any]],
) -> list[dict[str, Any]]:

    def sort_key(article):

        try:

            return datetime.fromisoformat(
                article["published"]
                .replace(
                    "Z",
                    "+00:00",
                )
            )

        except Exception:

            return datetime.min.replace(
                tzinfo=timezone.utc
            )

    return sorted(
        articles,
        key=sort_key,
        reverse=True,
    )


# ============================================================
# BUILD NEWS DATA
# ============================================================

def build_news() -> dict[str, Any]:

    logger.info(
        "Starting TechPulse news collection."
    )

    all_articles = []

    successful_feeds = 0

    failed_feeds = 0

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
        "Feeds successful: %d | failed: %d",
        successful_feeds,
        failed_feeds,
    )

    if not all_articles:

        raise RuntimeError(
            "All RSS feeds failed or returned no articles."
        )

    logger.info(
        "Articles before deduplication: %d",
        len(all_articles),
    )

    unique_articles = (
        deduplicate_articles(
            all_articles
        )
    )

    logger.info(
        "Articles after deduplication: %d",
        len(unique_articles),
    )

    sorted_articles = sort_articles(
        unique_articles
    )

    final_articles = sorted_articles[
        :MAX_ARTICLES
    ]

    updated_at = datetime.now(
        timezone.utc
    ).isoformat()

    data = {

        "success": True,

        "updatedAt": updated_at,

        "total": len(
            final_articles
        ),

        "feedsConfigured": len(
            FEEDS
        ),

        "feedsSuccessful": (
            successful_feeds
        ),

        "feedsFailed": (
            failed_feeds
        ),

        "articles": final_articles,

    }

    return data


# ============================================================
# VALIDATE DATA
# ============================================================

def validate_news(
    data: dict[str, Any],
) -> None:

    if not isinstance(
        data,
        dict,
    ):
        raise ValueError(
            "news.json root must be an object."
        )

    if data.get("success") is not True:
        raise ValueError(
            "success must be true."
        )

    articles = data.get(
        "articles"
    )

    if not isinstance(
        articles,
        list,
    ):
        raise ValueError(
            "articles must be a list."
        )

    if not articles:
        raise ValueError(
            "articles list is empty."
        )

    required_fields = [
        "id",
        "title",
        "description",
        "url",
        "image",
        "category",
        "mainCategory",
        "source",
        "published",
    ]

    for index, article in enumerate(
        articles
    ):

        if not isinstance(
            article,
            dict,
        ):
            raise ValueError(
                f"Article {index} is not an object."
            )

        for field in required_fields:

            if field not in article:

                raise ValueError(
                    f"Article {index} missing field: {field}"
                )

        if not article["title"]:
            raise ValueError(
                f"Article {index} has empty title."
            )

        if not re.match(
            r"^https?://",
            article["url"],
            re.IGNORECASE,
        ):
            raise ValueError(
                f"Article {index} has invalid URL."
            )


# ============================================================
# WRITE JSON SAFELY
# ============================================================

def write_json(
    data: dict[str, Any],
) -> None:

    validate_news(
        data
    )

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fd, temp_path = tempfile.mkstemp(
        prefix="news-",
        suffix=".json",
        dir=OUTPUT_FILE.parent,
        text=True,
    )

    try:

        with os.fdopen(
            fd,
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

            file.flush()

            os.fsync(
                file.fileno()
            )

        os.replace(
            temp_path,
            OUTPUT_FILE,
        )

    finally:

        if os.path.exists(
            temp_path
        ):

            os.remove(
                temp_path
            )


# ============================================================
# MAIN
# ============================================================

def main() -> int:

    start = time.time()

    try:

        data = build_news()

        write_json(
            data
        )

        elapsed = (
            time.time() - start
        )

        logger.info(
            "============================================"
        )

        logger.info(
            "TechPulse update successful."
        )

        logger.info(
            "Articles: %d",
            data["total"],
        )

        logger.info(
            "Updated: %s",
            data["updatedAt"],
        )

        logger.info(
            "Execution time: %.2f seconds",
            elapsed,
        )

        logger.info(
            "Output: %s",
            OUTPUT_FILE,
        )

        logger.info(
            "============================================"
        )

        return 0

    except Exception as exc:

        logger.exception(
            "TechPulse update failed: %s",
            exc,
        )

        return 1


if __name__ == "__main__":

    sys.exit(
        main()
    )
