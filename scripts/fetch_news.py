#!/usr/bin/env python3

"""
============================================================
TECHPULSE NEWS FETCHER
============================================================

Purpose:
    Fetch current Technology + Gaming news from RSS feeds
    and generate:

        news.json

Architecture:

    RSS feeds
        |
        v
    Fetch articles
        |
        v
    Clean / validate
        |
        v
    Categorize
        |
        v
    Remove duplicates
        |
        v
    Sort by publication time
        |
        v
    Keep latest articles
        |
        v
    news.json

Important:
    - No Google Apps Script
    - No Google Sheets
    - No database
    - No publisher logos
    - No full article copying
    - Only RSS title/excerpt/metadata
    - Original article URL is retained
============================================================
"""

from __future__ import annotations

import hashlib
import html
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlparse

import feedparser
import requests
from bs4 import BeautifulSoup


# ============================================================
# CONFIGURATION
# ============================================================

OUTPUT_FILE = Path("news.json")

MAX_ARTICLES = 120

MAX_CANDIDATES = 500

MAX_AGE_HOURS = 72

REQUEST_TIMEOUT = 20

USER_AGENT = (
    "TechPulseNews/1.0 "
    "(RSS news aggregation; contact via repository)"
)

# Number of attempts per feed
MAX_RETRIES = 2


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger("techpulse")


# ============================================================
# RSS FEEDS
# ============================================================
#
# Feed names are internal only.
#
# They are NOT written to the public website as logos,
# branding elements, or publisher cards.
#
# The website can simply identify the content as:
#
#     TechPulse News
#
# while the article URL still points to the original source.
#
# RSS availability can change over time, therefore the script
# deliberately treats each feed independently.
# ============================================================

FEEDS = [

    # --------------------------------------------------------
    # TECHNOLOGY
    # --------------------------------------------------------

    {
        "name": "Technology Feed 1",
        "url": "https://feeds.arstechnica.com/arstechnica/index",
        "mainCategory": "Technology",
        "defaultCategory": "Emerging Technology",
    },

    {
        "name": "Technology Feed 2",
        "url": "https://www.wired.com/feed/rss",
        "mainCategory": "Technology",
        "defaultCategory": "Emerging Technology",
    },

    {
        "name": "Technology Feed 3",
        "url": "https://www.wired.com/feed/category/artificial-intelligence/latest/rss",
        "mainCategory": "Technology",
        "defaultCategory": "Artificial Intelligence",
    },

    {
        "name": "Technology Feed 4",
        "url": "https://www.wired.com/feed/category/security/latest/rss",
        "mainCategory": "Technology",
        "defaultCategory": "Cybersecurity",
    },

    {
        "name": "Technology Feed 5",
        "url": "https://www.wired.com/feed/category/gear/latest/rss",
        "mainCategory": "Technology",
        "defaultCategory": "Hardware & Devices",
    },

    {
        "name": "Technology Feed 6",
        "url": "https://www.theguardian.com/technology/rss",
        "mainCategory": "Technology",
        "defaultCategory": "Emerging Technology",
    },

    {
        "name": "Technology Feed 7",
        "url": "https://www.bleepingcomputer.com/feed/",
        "mainCategory": "Technology",
        "defaultCategory": "Cybersecurity",
    },

    {
        "name": "Technology Feed 8",
        "url": "https://www.bleepingcomputer.com/feed/tag/linux/",
        "mainCategory": "Technology",
        "defaultCategory": "Cloud & Infrastructure",
    },

    {
        "name": "Technology Feed 9",
        "url": "https://www.bleepingcomputer.com/feed/tag/security/",
        "mainCategory": "Technology",
        "defaultCategory": "Cybersecurity",
    },

    {
        "name": "Technology Feed 10",
        "url": "https://www.itnews.asia/RSS/rss.ashx",
        "mainCategory": "Technology",
        "defaultCategory": "Business & Technology",
    },

    # --------------------------------------------------------
    # GAMING
    # --------------------------------------------------------

    {
        "name": "Gaming Feed 1",
        "url": "https://www.theguardian.com/games/rss",
        "mainCategory": "Gaming",
        "defaultCategory": "Gaming Updates",
    },

    {
        "name": "Gaming Feed 2",
        "url": "https://arstechnica.com/gaming/feed/",
        "mainCategory": "Gaming",
        "defaultCategory": "Gaming Updates",
    },

    {
        "name": "Gaming Feed 3",
        "url": "https://www.pcgamer.com/rss/",
        "mainCategory": "Gaming",
        "defaultCategory": "PC Gaming",
    },

]


# ============================================================
# CATEGORY KEYWORDS
# ============================================================

CATEGORY_KEYWORDS = {

    "Artificial Intelligence": [
        "artificial intelligence",
        "ai ",
        " ai",
        "machine learning",
        "deep learning",
        "generative ai",
        "large language model",
        "llm",
        "neural network",
        "chatbot",
        "robotics",
        "agentic ai",
        "ai model",
    ],

    "Cybersecurity": [
        "cybersecurity",
        "cyber security",
        "ransomware",
        "malware",
        "spyware",
        "phishing",
        "vulnerability",
        "cve-",
        "zero-day",
        "zero day",
        "security flaw",
        "data breach",
        "hack",
        "hacking",
        "infosec",
        "botnet",
        "credential",
    ],

    "Cloud & Infrastructure": [
        "cloud",
        "aws",
        "azure",
        "google cloud",
        "kubernetes",
        "docker",
        "container",
        "server",
        "datacenter",
        "data center",
        "infrastructure",
        "virtualization",
        "vmware",
        "linux",
        "ubuntu",
        "red hat",
        "rhel",
        "oracle linux",
    ],

    "Smartphones & Mobile": [
        "smartphone",
        "iphone",
        "android",
        "pixel phone",
        "galaxy phone",
        "mobile phone",
        "mobile device",
        "tablet",
        "ios",
        "android device",
    ],

    "Software & Applications": [
        "software",
        "application",
        "app update",
        "browser",
        "windows",
        "macos",
        "operating system",
        "office",
        "productivity",
        "open source",
        "developer tool",
    ],

    "Hardware & Devices": [
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
        "motherboard",
        "chip",
        "hardware",
        "device",
        "wearable",
    ],

    "Internet & Web": [
        "internet",
        "web",
        "website",
        "browser",
        "search engine",
        "social media",
        "online",
        "streaming",
        "wifi",
        "5g",
        "6g",
    ],

    "Programming": [
        "programming",
        "developer",
        "development",
        "python",
        "javascript",
        "typescript",
        "java",
        "golang",
        "rust",
        "php",
        "api",
        "github",
        "coding",
        "software development",
    ],

    "Science & Innovation": [
        "science",
        "research",
        "space",
        "nasa",
        "astronomy",
        "quantum",
        "quantum computing",
        "biology",
        "physics",
        "innovation",
        "robot",
        "robotics",
    ],

    "Business & Technology": [
        "startup",
        "funding",
        "investment",
        "enterprise",
        "business",
        "technology company",
        "ceo",
        "acquisition",
        "ipo",
        "layoff",
        "industry",
    ],

    "PC Gaming": [
        "pc gaming",
        "pc game",
        "steam",
        "graphics card",
        "gaming pc",
        "gaming laptop",
        "mod",
        "mods",
    ],

    "Console Gaming": [
        "playstation",
        "xbox",
        "nintendo",
        "console",
        "ps5",
        "ps6",
        "switch",
        "game console",
    ],

    "Mobile Gaming": [
        "mobile game",
        "mobile gaming",
        "android game",
        "ios game",
        "iphone game",
        "tablet game",
    ],

    "Game Releases": [
        "game release",
        "released",
        "launch",
        "launches",
        "release date",
        "coming soon",
        "new game",
        "announced",
    ],

    "Game Reviews": [
        "review",
        "reviewed",
        "hands-on",
        "impressions",
        "rating",
    ],

    "Gaming Hardware": [
        "gaming hardware",
        "gaming monitor",
        "gaming keyboard",
        "gaming mouse",
        "gaming headset",
        "gaming controller",
        "gpu",
        "graphics card",
        "gaming laptop",
    ],

    "Esports": [
        "esports",
        "e-sports",
        "tournament",
        "championship",
        "competitive gaming",
        "pro player",
    ],

    "Game Development": [
        "game developer",
        "game development",
        "game engine",
        "unity",
        "unreal engine",
        "developer studio",
        "indie game",
    ],

    "Gaming Industry": [
        "gaming industry",
        "game studio",
        "publisher",
        "developer studio",
        "game company",
        "gaming business",
    ],

    "Gaming Updates": [
        "gaming",
        "game",
        "games",
        "video game",
        "video games",
    ],

}


# ============================================================
# EXCLUDED CONTENT
# ============================================================

EXCLUDED_KEYWORDS = [

    "horoscope",
    "astrology",
    "celebrity",
    "fashion",
    "recipe",
    "cooking",
    "real estate",
    "politics",
    "election",
    "sports",
    "football",
    "soccer",
    "cricket",
    "baseball",
    "basketball",

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
            "text/html;q=0.9, "
            "*/*;q=0.8"
        ),
    }
)


# ============================================================
# HELPERS
# ============================================================

def clean_text(value: str | None) -> str:
    """
    Remove HTML and normalize whitespace.
    """

    if not value:
        return ""

    value = html.unescape(str(value))

    soup = BeautifulSoup(
        value,
        "html.parser",
    )

    text = soup.get_text(
        " ",
        strip=True,
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def strip_tracking_parameters(url: str) -> str:
    """
    Remove common tracking parameters.
    """

    if not url:
        return ""

    url = url.strip()

    url = re.sub(
        r"[?&](utm_[^&]+|"
        r"ref_[^&]+|"
        r"ocid[^&]*|"
        r"cmpid[^&]*)",
        "",
        url,
        flags=re.IGNORECASE,
    )

    url = url.rstrip("?&")

    return url


def normalize_title(title: str) -> str:
    """
    Normalize a title for duplicate detection.
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


def make_id(title: str, url: str) -> str:
    """
    Stable article ID.
    """

    raw = (
        normalize_title(title)
        + "|"
        + strip_tracking_parameters(url)
    )

    digest = hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()[:20]

    return "tp-" + digest


def parse_date(value) -> datetime | None:
    """
    Convert RSS date values to UTC datetime.
    """

    if not value:
        return None

    try:

        if isinstance(
            value,
            datetime,
        ):

            dt = value

        else:

            text = str(value).strip()

            dt = parsedate_to_datetime(
                text
            )

    except Exception:

        try:

            from dateutil import parser

            dt = parser.parse(
                str(value)
            )

        except Exception:

            return None

    if dt.tzinfo is None:

        dt = dt.replace(
            tzinfo=timezone.utc
        )

    return dt.astimezone(
        timezone.utc
    )


def get_entry_date(entry):
    """
    Try all common RSS/Atom date fields.
    """

    candidates = [

        entry.get(
            "published"
        ),

        entry.get(
            "updated"
        ),

        entry.get(
            "created"
        ),

        entry.get(
            "pubDate"
        ),

    ]

    for value in candidates:

        dt = parse_date(value)

        if dt:

            return dt

    return None


def extract_image(entry) -> str:
    """
    Try to find an article image from RSS metadata.

    We only use the image URL as metadata.
    The frontend does not display publisher logos.
    """

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

            if url and is_http_url(url):

                return url


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

            if url and is_http_url(url):

                return url


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

            if (
                url
                and is_http_url(url)
                and (
                    media_type.startswith(
                        "image/"
                    )
                    or not media_type
                )
            ):

                return url


    # --------------------------------------------------------
    # HTML description
    # --------------------------------------------------------

    html_fields = [

        entry.get(
            "summary",
            "",
        ),

        entry.get(
            "description",
            "",
        ),

        entry.get(
            "content",
            "",
        ),

    ]

    for field in html_fields:

        if isinstance(
            field,
            list,
        ):

            for item in field:

                if isinstance(
                    item,
                    dict,
                ):

                    field_value = item.get(
                        "value",
                        "",
                    )

                else:

                    field_value = str(
                        item
                    )

                image = extract_image_from_html(
                    field_value
                )

                if image:

                    return image

        else:

            image = extract_image_from_html(
                str(field)
            )

            if image:

                return image


    return ""


def extract_image_from_html(
    value: str,
) -> str:

    if not value:

        return ""

    soup = BeautifulSoup(
        value,
        "html.parser",
    )

    image = soup.find(
        "img"
    )

    if not image:

        return ""

    src = (
        image.get("src")
        or image.get("data-src")
        or image.get("data-original")
    )

    if src and is_http_url(src):

        return src

    return ""


def is_http_url(
    value: str,
) -> bool:

    if not value:

        return False

    return bool(
        re.match(
            r"^https?://",
            str(value).strip(),
            re.IGNORECASE,
        )
    )


def get_description(entry) -> str:
    """
    Extract a short RSS excerpt.

    We deliberately do NOT download and reproduce
    the full article.
    """

    values = [

        entry.get(
            "summary",
            "",
        ),

        entry.get(
            "description",
            "",
        ),

    ]

    content = entry.get(
        "content",
        [],
    )

    if isinstance(
        content,
        list,
    ):

        for item in content:

            if isinstance(
                item,
                dict,
            ):

                values.append(
                    item.get(
                        "value",
                        "",
                    )
                )


    for value in values:

        cleaned = clean_text(
            value
        )

        if cleaned:

            # Remove extremely long excerpts.
            if len(cleaned) > 500:

                cleaned = (
                    cleaned[:497]
                    + "..."
                )

            return cleaned

    return (
        "Read the latest technology "
        "and gaming story from the "
        "original publisher."
    )


def is_excluded(
    title: str,
    description: str,
) -> bool:

    text = (
        title
        + " "
        + description
    ).lower()

    for keyword in EXCLUDED_KEYWORDS:

        if keyword in text:

            return True

    return False


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
        title
        + " "
        + description
    ).lower()


    # --------------------------------------------------------
    # Gaming categories first
    # --------------------------------------------------------

    if main_category == "Gaming":

        priority = [

            "PC Gaming",
            "Console Gaming",
            "Mobile Gaming",
            "Game Reviews",
            "Game Releases",
            "Gaming Hardware",
            "Esports",
            "Game Development",
            "Gaming Industry",
            "Gaming Updates",

        ]

        for category in priority:

            keywords = CATEGORY_KEYWORDS.get(
                category,
                [],
            )

            for keyword in keywords:

                if keyword.lower() in text:

                    return category

        return default_category


    # --------------------------------------------------------
    # Technology categories
    # --------------------------------------------------------

    priority = [

        "Cybersecurity",
        "Artificial Intelligence",
        "Cloud & Infrastructure",
        "Smartphones & Mobile",
        "Programming",
        "Software & Applications",
        "Hardware & Devices",
        "Internet & Web",
        "Science & Innovation",
        "Business & Technology",

    ]

    for category in priority:

        keywords = CATEGORY_KEYWORDS.get(
            category,
            [],
        )

        for keyword in keywords:

            if keyword.lower() in text:

                return category

    return default_category


def detect_main_category(
    title: str,
    description: str,
    feed_category: str,
) -> str:

    if feed_category in (
        "Gaming",
        "Technology",
    ):

        return feed_category


    text = (
        title
        + " "
        + description
    ).lower()


    gaming_words = [

        "gaming",
        "video game",
        "video games",
        "playstation",
        "xbox",
        "nintendo",
        "steam",
        "esports",
        "game release",
        "game developer",

    ]

    for word in gaming_words:

        if word in text:

            return "Gaming"


    return "Technology"


# ============================================================
# FETCH FEED
# ============================================================

def fetch_feed(
    feed_config: dict,
) -> list[dict]:

    feed_url = feed_config[
        "url"
    ]

    feed_name = feed_config[
        "name"
    ]

    logger.info(
        "Fetching: %s",
        feed_name,
    )

    for attempt in range(
        1,
        MAX_RETRIES + 1,
    ):

        try:

            response = SESSION.get(
                feed_url,
                timeout=REQUEST_TIMEOUT,
            )

            response.raise_for_status()


            parsed = feedparser.parse(
                response.content
            )


            if getattr(
                parsed,
                "bozo",
                False,
            ):

                logger.warning(
                    "%s returned a feed warning: %s",
                    feed_name,
                    getattr(
                        parsed,
                        "bozo_exception",
                        "unknown",
                    ),
                )


            entries = getattr(
                parsed,
                "entries",
                [],
            )


            logger.info(
                "%s -> %d entries",
                feed_name,
                len(entries),
            )


            articles = []


            for entry in entries:

                article = process_entry(
                    entry,
                    feed_config,
                )

                if article:

                    articles.append(
                        article
                    )


            return articles


        except Exception as exc:

            logger.warning(
                "%s failed "
                "(attempt %d/%d): %s",
                feed_name,
                attempt,
                MAX_RETRIES,
                exc,
            )

            if attempt < MAX_RETRIES:

                time.sleep(2)


    logger.error(
        "%s failed completely.",
        feed_name,
    )

    return []


# ============================================================
# PROCESS ENTRY
# ============================================================

def process_entry(
    entry,
    feed_config: dict,
) -> dict | None:

    title = clean_text(
        entry.get(
            "title",
            "",
        )
    )

    url = (
        entry.get(
            "link",
            "",
        )
        or entry.get(
            "id",
            "",
        )
    )

    url = strip_tracking_parameters(
        str(url)
    )


    if not title:

        return None


    if not is_http_url(url):

        return None


    description = get_description(
        entry
    )


    if is_excluded(
        title,
        description,
    ):

        return None


    published_dt = get_entry_date(
        entry
    )


    if not published_dt:

        return None


    # --------------------------------------------------------
    # Reject very old articles
    # --------------------------------------------------------

    now = datetime.now(
        timezone.utc
    )

    cutoff = (
        now
        - timedelta(
            hours=MAX_AGE_HOURS
        )
    )


    if published_dt < cutoff:

        return None


    main_category = (
        feed_config[
            "mainCategory"
        ]
    )


    category = detect_category(
        title,
        description,
        feed_config[
            "defaultCategory"
        ],
        main_category,
    )


    # --------------------------------------------------------
    # Re-evaluate main category
    # --------------------------------------------------------

    main_category = detect_main_category(
        title,
        description,
        main_category,
    )


    image = extract_image(
        entry
    )


    article_id = make_id(
        title,
        url,
    )


    return {

        "id": article_id,

        "title": title,

        "description": description,

        "url": url,

        "image": image,

        "category": category,

        "mainCategory": main_category,

        # Deliberately generic public label.
        # No publisher logo/name is displayed.
        "source": "TechPulse News",

        "published": published_dt.isoformat(),

    }


# ============================================================
# DEDUPLICATION
# ============================================================

def deduplicate_articles(
    articles: list[dict],
) -> list[dict]:

    seen_ids = set()

    seen_urls = set()

    seen_titles = set()

    result = []


    for article in articles:

        article_id = article[
            "id"
        ]

        url = strip_tracking_parameters(
            article[
                "url"
            ]
        ).lower()

        title_key = normalize_title(
            article[
                "title"
            ]
        )


        if article_id in seen_ids:

            continue


        if url in seen_urls:

            continue


        if title_key in seen_titles:

            continue


        seen_ids.add(
            article_id
        )

        seen_urls.add(
            url
        )

        seen_titles.add(
            title_key
        )

        result.append(
            article
        )


    return result


# ============================================================
# SORT
# ============================================================

def sort_articles(
    articles: list[dict],
) -> list[dict]:

    return sorted(
        articles,
        key=lambda item: item.get(
            "published",
            "",
        ),
        reverse=True,
    )


# ============================================================
# WRITE JSON
# ============================================================

def write_news_json(
    articles: list[dict],
    feed_count: int,
) -> None:

    now = datetime.now(
        timezone.utc
    )


    payload = {

        "success": True,

        "updatedAt":
            now.isoformat(),

        "total":
            len(articles),

        "articles":
            articles,

        "meta": {

            "version":
                "2.0",

            "generatedAt":
                now.isoformat(),

            "feedsConfigured":
                feed_count,

            "articlesReturned":
                len(articles),

            "maxArticles":
                MAX_ARTICLES,

            "maxAgeHours":
                MAX_AGE_HOURS,

        },

    }


    temporary_file = (
        OUTPUT_FILE.with_suffix(
            ".tmp"
        )
    )


    with open(
        temporary_file,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            payload,
            file,
            ensure_ascii=False,
            indent=2,
        )


    temporary_file.replace(
        OUTPUT_FILE
    )


    logger.info(
        "news.json written successfully: %d articles",
        len(articles),
    )


# ============================================================
# VALIDATE EXISTING NEWS
# ============================================================

def load_existing_news() -> dict | None:

    if not OUTPUT_FILE.exists():

        return None


    try:

        with open(
            OUTPUT_FILE,
            "r",
            encoding="utf-8",
        ) as file:

            data = json.load(
                file
            )


        if not isinstance(
            data,
            dict,
        ):

            return None


        if not isinstance(
            data.get(
                "articles"
            ),
            list,
        ):

            return None


        return data


    except Exception:

        return None


# ============================================================
# MAIN
# ============================================================

def main() -> int:

    logger.info(
        "=================================================="
    )

    logger.info(
        "TechPulse News Fetcher starting"
    )

    logger.info(
        "=================================================="
    )

    logger.info(
        "Feeds configured: %d",
        len(FEEDS),
    )

    logger.info(
        "Maximum articles: %d",
        MAX_ARTICLES,
    )

    logger.info(
        "Maximum article age: %d hours",
        MAX_AGE_HOURS,
    )


    all_articles = []


    # --------------------------------------------------------
    # Fetch every feed independently
    # --------------------------------------------------------

    for feed_config in FEEDS:

        articles = fetch_feed(
            feed_config
        )

        all_articles.extend(
            articles
        )


    logger.info(
        "Total raw valid articles: %d",
        len(all_articles),
    )


    # --------------------------------------------------------
    # Deduplicate
    # --------------------------------------------------------

    all_articles = deduplicate_articles(
        all_articles
    )


    logger.info(
        "After duplicate removal: %d",
        len(all_articles),
    )


    # --------------------------------------------------------
    # Sort
    # --------------------------------------------------------

    all_articles = sort_articles(
        all_articles
    )


    # --------------------------------------------------------
    # Limit
    # --------------------------------------------------------

    final_articles = all_articles[
        :MAX_ARTICLES
    ]


    # --------------------------------------------------------
    # Safety mechanism
    #
    # If ALL feeds fail, do not overwrite a previously
    # working news.json with an empty file.
    # --------------------------------------------------------

    if not final_articles:

        existing = load_existing_news()


        if existing:

            logger.warning(
                "No new articles were fetched."
            )

            logger.warning(
                "Keeping existing news.json."
            )

            return 0


        logger.error(
            "No articles available and no existing news.json."
        )

        return 1


    # --------------------------------------------------------
    # Write result
    # --------------------------------------------------------

    write_news_json(
        final_articles,
        len(FEEDS),
    )


    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    technology_count = sum(
        1
        for article in final_articles
        if article.get(
            "mainCategory"
        ) == "Technology"
    )


    gaming_count = sum(
        1
        for article in final_articles
        if article.get(
            "mainCategory"
        ) == "Gaming"
    )


    logger.info(
        "--------------------------------------------------"
    )

    logger.info(
        "FINAL RESULT"
    )

    logger.info(
        "--------------------------------------------------"
    )

    logger.info(
        "Total articles : %d",
        len(final_articles),
    )

    logger.info(
        "Technology     : %d",
        technology_count,
    )

    logger.info(
        "Gaming         : %d",
        gaming_count,
    )

    logger.info(
        "Output         : %s",
        OUTPUT_FILE,
    )

    logger.info(
        "--------------------------------------------------"
    )


    # --------------------------------------------------------
    # Print first 10 headlines for GitHub Actions logs
    # --------------------------------------------------------

    logger.info(
        "Latest articles:"
    )


    for index, article in enumerate(
        final_articles[:10],
        start=1,
    ):

        logger.info(
            "%02d. [%s] %s",
            index,
            article.get(
                "category"
            ),
            article.get(
                "title"
            ),
        )


    logger.info(
        "=================================================="
    )

    logger.info(
        "TechPulse News Fetcher completed successfully."
    )

    logger.info(
        "=================================================="
    )


    return 0


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    sys.exit(
        main()
    )
