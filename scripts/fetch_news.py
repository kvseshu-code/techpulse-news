"""
TechPulse News Fetcher

Purpose:
    Fetch technology and gaming news from RSS feeds,
    normalize the articles, remove duplicates,
    categorize them and generate news.json.

Architecture:

    RSS feeds
        ↓
    fetch_news.py
        ↓
    normalize
        ↓
    deduplicate
        ↓
    categorize
        ↓
    news.json
        ↓
    GitHub Pages
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import sys
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlparse

import feedparser
import requests
from bs4 import BeautifulSoup


# =========================================================
# CONFIGURATION
# =========================================================

ROOT_DIR = Path(__file__).resolve().parents[1]

OUTPUT_FILE = ROOT_DIR / "news.json"

MAX_ARTICLES = 120

REQUEST_TIMEOUT = 20


# =========================================================
# RSS SOURCES
# =========================================================
#
# These are RSS feed URLs, not copied website content.
#
# The website displays:
#   - headline
#   - short RSS description
#   - date
#   - category
#   - source attribution
#   - link to original article
#
# Always review the terms of each feed before publishing.
#
# =========================================================

FEEDS = [

    # -----------------------------------------------------
    # TECHNOLOGY
    # -----------------------------------------------------

    {
        "name": "Technology News",
        "url": "https://feeds.feedburner.com/TechCrunch/",
        "mainCategory": "Technology",
        "category": "Emerging Technology"
    },

    {
        "name": "Technology News",
        "url": "https://feeds.arstechnica.com/arstechnica/index",
        "mainCategory": "Technology",
        "category": "Technology"
    },

    {
        "name": "Technology News",
        "url": "https://www.wired.com/feed/rss",
        "mainCategory": "Technology",
        "category": "Emerging Technology"
    },

    {
        "name": "Technology News",
        "url": "https://www.zdnet.com/news/rss.xml",
        "mainCategory": "Technology",
        "category": "Software & Applications"
    },


    # -----------------------------------------------------
    # GAMING
    # -----------------------------------------------------

    {
        "name": "Gaming News",
        "url": "https://www.pcgamer.com/rss/",
        "mainCategory": "Gaming",
        "category": "PC Gaming"
    },

    {
        "name": "Gaming News",
        "url": "https://www.gamespot.com/feeds/news/",
        "mainCategory": "Gaming",
        "category": "Gaming Updates"
    },

    {
        "name": "Gaming News",
        "url": "https://www.eurogamer.net/feed",
        "mainCategory": "Gaming",
        "category": "Gaming Updates"
    },

]


# =========================================================
# HTTP SESSION
# =========================================================

SESSION = requests.Session()

SESSION.headers.update(
    {
        "User-Agent":
            "TechPulse-NewsFetcher/1.0 "
            "(RSS aggregation client)",
        "Accept":
            "application/rss+xml, "
            "application/atom+xml, "
            "application/xml, "
            "text/xml, "
            "*/*",
    }
)


# =========================================================
# TEXT HELPERS
# =========================================================

def clean_html(value: str) -> str:
    """
    Convert HTML content to clean plain text.
    """

    if not value:
        return ""

    value = html.unescape(str(value))

    soup = BeautifulSoup(
        value,
        "html.parser"
    )

    text = soup.get_text(
        " ",
        strip=True
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def truncate_text(
    value: str,
    maximum: int = 300
) -> str:
    """
    Keep descriptions reasonably short.
    """

    value = clean_html(value)

    if len(value) <= maximum:
        return value

    truncated = value[:maximum]

    last_space = truncated.rfind(" ")

    if last_space > 100:
        truncated = truncated[:last_space]

    return truncated.rstrip() + "..."


def normalize_title(
    title: str
) -> str:
    """
    Used for duplicate detection.
    """

    title = clean_html(title)

    title = title.lower()

    title = re.sub(
        r"[^a-z0-9\s]",
        " ",
        title
    )

    title = re.sub(
        r"\s+",
        " ",
        title
    )

    return title.strip()


# =========================================================
# DATE HELPERS
# =========================================================

def parse_date(
    entry
) -> str:
    """
    Convert RSS date into ISO UTC.
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

    ]

    for value in candidates:

        if not value:
            continue

        try:

            dt = parsedate_to_datetime(
                value
            )

            if dt.tzinfo is None:

                dt = dt.replace(
                    tzinfo=timezone.utc
                )

            return dt.astimezone(
                timezone.utc
            ).isoformat()

        except Exception:
            pass


    for key in [
        "published_parsed",
        "updated_parsed",
    ]:

        parsed =
            entry.get(key)

        if parsed:

            try:

                dt = datetime.fromtimestamp(
                    time.mktime(parsed),
                    tz=timezone.utc
                )

                return dt.isoformat()

            except Exception:
                pass


    return datetime.now(
        timezone.utc
    ).isoformat()


# =========================================================
# IMAGE EXTRACTION
# =========================================================

def extract_image(
    entry
) -> str:
    """
    Try to use an image explicitly supplied
    by the RSS feed.

    We do not scrape arbitrary page images.
    """

    media_content =
        entry.get(
            "media_content",
            []
        )

    if media_content:

        for media in media_content:

            url = media.get(
                "url"
            )

            if (
                url and
                str(url).startswith(
                    "http"
                )
            ):

                return str(url)


    media_thumbnail =
        entry.get(
            "media_thumbnail",
            []
        )

    if media_thumbnail:

        for media in media_thumbnail:

            url = media.get(
                "url"
            )

            if (
                url and
                str(url).startswith(
                    "http"
                )
            ):

                return str(url)


    enclosures =
        entry.get(
            "enclosures",
            []
        )

    for enclosure in enclosures:

        url =
            enclosure.get(
                "href"
            ) or enclosure.get(
                "url"
            )

        mime =
            enclosure.get(
                "type",
                ""
            )

        if (
            url and
            (
                "image" in mime.lower()
                or
                re.search(
                    r"\.(jpg|jpeg|png|webp)(\?|$)",
                    url,
                    re.I
                )
            )
        ):

            return str(url)


    return ""


# =========================================================
# CATEGORY DETECTION
# =========================================================

def detect_category(
    title: str,
    description: str,
    default_category: str,
    main_category: str
) -> str:

    text = (
        title +
        " " +
        description
    ).lower()


    if main_category == "Gaming":

        rules = [

            (
                "PC Gaming",
                [
                    "pc gaming",
                    "steam",
                    "gaming pc",
                    "gpu",
                    "graphics card"
                ]
            ),

            (
                "Mobile Gaming",
                [
                    "mobile game",
                    "mobile gaming",
                    "android game",
                    "ios game"
                ]
            ),

            (
                "Esports",
                [
                    "esports",
                    "e-sports",
                    "tournament"
                ]
            ),

            (
                "Game Releases",
                [
                    "release date",
                    "launches",
                    "new game",
                    "released"
                ]
            ),

            (
                "Gaming Hardware",
                [
                    "gaming hardware",
                    "controller",
                    "console",
                    "gaming headset",
                    "gaming monitor"
                ]
            ),

        ]

    else:

        rules = [

            (
                "Artificial Intelligence",
                [
                    "artificial intelligence",
                    "ai ",
                    "machine learning",
                    "generative ai",
                    "large language model",
                    "llm"
                ]
            ),

            (
                "Cybersecurity",
                [
                    "cybersecurity",
                    "cyber security",
                    "ransomware",
                    "malware",
                    "vulnerability",
                    "data breach",
                    "security"
                ]
            ),

            (
                "Cloud & Infrastructure",
                [
                    "cloud",
                    "kubernetes",
                    "container",
                    "server",
                    "data center",
                    "infrastructure"
                ]
            ),

            (
                "Smartphones & Mobile",
                [
                    "smartphone",
                    "iphone",
                    "android",
                    "mobile phone",
                    "pixel",
                    "galaxy"
                ]
            ),

            (
                "Software & Applications",
                [
                    "software",
                    "application",
                    "app",
                    "browser",
                    "operating system"
                ]
            ),

            (
                "Hardware & Devices",
                [
                    "processor",
                    "cpu",
                    "gpu",
                    "laptop",
                    "computer",
                    "hardware",
                    "device"
                ]
            ),

            (
                "Science & Innovation",
                [
                    "science",
                    "research",
                    "innovation",
                    "quantum",
                    "robotics"
                ]
            ),

        ]


    for category, keywords in rules:

        for keyword in keywords:

            if keyword in text:

                return category


    return default_category


# =========================================================
# ARTICLE ID
# =========================================================

def create_article_id(
    url: str,
    title: str
) -> str:

    raw =
        (
            url.strip() +
            "|" +
            normalize_title(title)
        )

    digest =
        hashlib.sha256(
            raw.encode(
                "utf-8"
            )
        ).hexdigest()[:20]

    return (
        "techpulse-" +
        digest
    )


# =========================================================
# FETCH ONE FEED
# =========================================================

def fetch_feed(
    feed_config: dict
) -> list[dict]:

    feed_url =
        feed_config["url"]


    print(
        f"Fetching: {feed_url}"
    )


    try:

        response =
            SESSION.get(
                feed_url,
                timeout=REQUEST_TIMEOUT
            )


        response.raise_for_status()


        parsed =
            feedparser.parse(
                response.content
            )


        if parsed.bozo:

            print(
                "Warning: feed parser reported "
                "a feed issue."
            )


        articles = []


        for entry in parsed.entries:

            title =
                clean_html(
                    entry.get(
                        "title",
                        ""
                    )
                )


            link =
                entry.get(
                    "link",
                    ""
                )


            if not title or not link:

                continue


            description =
                truncate_text(
                    entry.get(
                        "summary",
                        ""
                    ),
                    350
                )


            published =
                parse_date(
                    entry
                )


            category =
                detect_category(
                    title,
                    description,
                    feed_config[
                        "category"
                    ],
                    feed_config[
                        "mainCategory"
                    ]
                )


            image =
                extract_image(
                    entry
                )


            article = {

                "id":
                    create_article_id(
                        link,
                        title
                    ),

                "title":
                    title,

                "description":
                    description,

                "url":
                    link,

                "image":
                    image,

                "category":
                    category,

                "mainCategory":
                    feed_config[
                        "mainCategory"
                    ],

                "source":
                    feed_config[
                        "name"
                    ],

                "published":
                    published

            }


            articles.append(
                article
            )


        print(
            f"  Found {len(articles)} articles"
        )


        return articles


    except Exception as error:

        print(
            f"  ERROR: {error}"
        )

        return []


# =========================================================
# DEDUPLICATION
# =========================================================

def deduplicate_articles(
    articles: list[dict]
) -> list[dict]:

    seen_urls = set()

    seen_titles = set()

    result = []


    for article in articles:

        url =
            article["url"].strip()


        title_key =
            normalize_title(
                article["title"]
            )


        url_key =
            url.lower().rstrip("/")


        if url_key in seen_urls:

            continue


        if title_key in seen_titles:

            continue


        seen_urls.add(
            url_key
        )

        seen_titles.add(
            title_key
        )

        result.append(
            article
        )


    return result


# =========================================================
# SORT
# =========================================================

def sort_articles(
    articles: list[dict]
) -> list[dict]:

    def timestamp(article):

        try:

            return datetime.fromisoformat(
                article[
                    "published"
                ].replace(
                    "Z",
                    "+00:00"
                )
            ).timestamp()

        except Exception:

            return 0


    return sorted(
        articles,
        key=timestamp,
        reverse=True
    )


# =========================================================
# WRITE JSON
# =========================================================

def write_news_json(
    articles: list[dict]
) -> None:

    updated_at =
        datetime.now(
            timezone.utc
        ).isoformat()


    output = {

        "success":
            True,

        "updatedAt":
            updated_at,

        "total":
            len(articles),

        "articles":
            articles

    }


    temporary_file =
        OUTPUT_FILE.with_suffix(
            ".tmp"
        )


    with open(
        temporary_file,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            output,
            file,
            ensure_ascii=False,
            indent=2
        )


    temporary_file.replace(
        OUTPUT_FILE
    )


    print(
        f"Created {OUTPUT_FILE}"
    )

    print(
        f"Articles: {len(articles)}"
    )


# =========================================================
# MAIN
# =========================================================

def main():

    print(
        "=========================================="
    )

    print(
        "TechPulse News Fetcher"
    )

    print(
        "=========================================="
    )


    all_articles = []


    for feed in FEEDS:

        articles =
            fetch_feed(
                feed
            )

        all_articles.extend(
            articles
        )


    print(
        f"Total fetched: "
        f"{len(all_articles)}"
    )


    all_articles =
        deduplicate_articles(
            all_articles
        )


    print(
        f"After deduplication: "
        f"{len(all_articles)}"
    )


    all_articles =
        sort_articles(
            all_articles
        )


    all_articles =
        all_articles[
            :MAX_ARTICLES
        ]


    /*
     * Safety mechanism:
     *
     * Never overwrite an existing
     * working news.json with an empty
     * result when all feeds fail.
     */

    if not all_articles:

        if OUTPUT_FILE.exists():

            print(
                "ERROR: No articles were fetched."
            )

            print(
                "Existing news.json will "
                "NOT be replaced."
            )

            sys.exit(1)

        else:

            print(
                "ERROR: No articles were fetched "
                "and news.json does not exist."
            )

            sys.exit(1)


    write_news_json(
        all_articles
    )


    print(
        "News update completed successfully."
    )


if __name__ == "__main__":

    main()
