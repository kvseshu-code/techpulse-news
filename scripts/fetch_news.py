#!/usr/bin/env python3

"""
TechPulse News Fetcher
----------------------

Purpose:
    Fetch technology and gaming news from RSS feeds,
    normalize articles, remove duplicates, categorize
    stories, and generate news.json.

Designed for:
    GitHub Actions + GitHub Pages

No Google Apps Script.
No Google Sheets.
No database.

Output:
    news.json

Important:
    The website displays headlines/excerpts and links
    users to the original article.
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
from typing import Any
from urllib.parse import urlparse

import feedparser
import requests
from bs4 import BeautifulSoup


# =========================================================
# CONFIGURATION
# =========================================================

OUTPUT_FILE = Path("news.json")

MAX_TOTAL_ARTICLES = 180

MAX_ARTICLES_PER_FEED = 25

REQUEST_TIMEOUT = 20

USER_AGENT = (
    "TechPulseNewsBot/1.0 "
    "(RSS reader; automated news aggregation)"
)


# =========================================================
# RSS FEEDS
# =========================================================
#
# These are RSS endpoints only.
#
# The website does NOT copy complete articles.
# It stores headline, short description, date and
# original URL.
#
# You can add/remove feeds later.
# =========================================================

FEEDS = [

    # -----------------------------------------------------
    # TECHNOLOGY
    # -----------------------------------------------------

    {
        "url": "https://feeds.arstechnica.com/arstechnica/index",
        "mainCategory": "Technology",
        "category": "Technology",
    },

    {
        "url": "https://www.wired.com/feed/rss",
        "mainCategory": "Technology",
        "category": "Emerging Technology",
    },

    {
        "url": "https://www.zdnet.com/news/rss.xml",
        "mainCategory": "Technology",
        "category": "Software & Applications",
    },

    {
        "url": "https://www.techradar.com/rss",
        "mainCategory": "Technology",
        "category": "Hardware & Devices",
    },

    # -----------------------------------------------------
    # AI
    # -----------------------------------------------------

    {
        "url": "https://www.artificialintelligence-news.com/feed/",
        "mainCategory": "Technology",
        "category": "Artificial Intelligence",
    },

    {
        "url": "https://machinelearningmastery.com/feed/",
        "mainCategory": "Technology",
        "category": "Artificial Intelligence",
    },

    # -----------------------------------------------------
    # CYBERSECURITY
    # -----------------------------------------------------

    {
        "url": "https://feeds.feedburner.com/TheHackersNews",
        "mainCategory": "Technology",
        "category": "Cybersecurity",
    },

    {
        "url": "https://www.bleepingcomputer.com/feed/",
        "mainCategory": "Technology",
        "category": "Cybersecurity",
    },

    # -----------------------------------------------------
    # LINUX / OPEN SOURCE
    # -----------------------------------------------------

    {
        "url": "https://www.linux.com/feed/",
        "mainCategory": "Technology",
        "category": "Linux & Open Source",
    },

    {
        "url": "https://www.omgubuntu.co.uk/feed",
        "mainCategory": "Technology",
        "category": "Linux & Open Source",
    },

    # -----------------------------------------------------
    # CLOUD / INFRASTRUCTURE
    # -----------------------------------------------------

    {
        "url": "https://aws.amazon.com/blogs/aws/feed/",
        "mainCategory": "Technology",
        "category": "Cloud & Infrastructure",
    },

    # -----------------------------------------------------
    # PROGRAMMING / DEVELOPMENT
    # -----------------------------------------------------

    {
        "url": "https://dev.to/feed",
        "mainCategory": "Technology",
        "category": "Programming & Development",
    },

    # -----------------------------------------------------
    # GAMING
    # -----------------------------------------------------

    {
        "url": "https://www.pcgamer.com/rss/",
        "mainCategory": "Gaming",
        "category": "PC Gaming",
    },

    {
        "url": "https://www.gamespot.com/feeds/news/",
        "mainCategory": "Gaming",
        "category": "Gaming",
    },

    {
        "url": "https://www.eurogamer.net/feed",
        "mainCategory": "Gaming",
        "category": "Gaming",
    },

    {
        "url": "https://www.polygon.com/rss/index.xml",
        "mainCategory": "Gaming",
        "category": "Gaming",
    },

    {
        "url": "https://www.destructoid.com/feed/",
        "mainCategory": "Gaming",
        "category": "Gaming",
    },

]


# =========================================================
# KEYWORDS
# =========================================================

CATEGORY_KEYWORDS = {

    "Artificial Intelligence": [
        "artificial intelligence",
        "artificial-intelligence",
        "machine learning",
        "deep learning",
        "generative ai",
        "genai",
        "large language model",
        "llm",
        "chatbot",
        "neural network",
        "ai model",
        "ai assistant",
        "ai agent",
        "foundation model",
    ],

    "Cybersecurity": [
        "cybersecurity",
        "cyber security",
        "malware",
        "ransomware",
        "phishing",
        "vulnerability",
        "zero-day",
        "zero day",
        "exploit",
        "security breach",
        "data breach",
        "botnet",
        "identity theft",
        "security update",
    ],

    "Cloud & Infrastructure": [
        "cloud computing",
        "cloud infrastructure",
        "kubernetes",
        "docker",
        "container",
        "server",
        "datacenter",
        "data center",
        "virtual machine",
        "infrastructure",
        "devops",
        "cloud security",
    ],

    "Linux & Open Source": [
        "linux",
        "ubuntu",
        "red hat",
        "rhel",
        "debian",
        "fedora",
        "kernel",
        "open source",
        "opensource",
    ],

    "Programming & Development": [
        "programming",
        "developer",
        "developers",
        "software development",
        "python",
        "javascript",
        "typescript",
        "java",
        "golang",
        "rust",
        "api",
        "github",
        "coding",
    ],

    "Smartphones & Mobile": [
        "smartphone",
        "smartphones",
        "android",
        "iphone",
        "mobile phone",
        "mobile device",
        "mobile app",
        "tablet",
        "wearable",
    ],

    "Hardware & Devices": [
        "processor",
        "cpu",
        "gpu",
        "graphics card",
        "laptop",
        "desktop",
        "monitor",
        "keyboard",
        "hardware",
        "chip",
        "semiconductor",
        "memory",
        "ssd",
    ],

    "Internet & Web": [
        "internet",
        "web browser",
        "browser",
        "website",
        "web",
        "search engine",
        "online service",
        "social network",
    ],

    "Emerging Technology": [
        "robotics",
        "robot",
        "quantum computing",
        "quantum",
        "augmented reality",
        "virtual reality",
        "mixed reality",
        "ar technology",
        "vr technology",
        "autonomous",
    ],

    "Science & Innovation": [
        "science",
        "research",
        "innovation",
        "scientists",
        "laboratory",
        "space technology",
        "discovery",
    ],

    "Business & Technology": [
        "startup",
        "startups",
        "technology company",
        "tech industry",
        "funding",
        "investment",
        "acquisition",
        "merger",
    ],

    "PC Gaming": [
        "pc gaming",
        "pc game",
        "steam",
        "gaming pc",
        "pc gamer",
    ],

    "Console Gaming": [
        "console",
        "console gaming",
        "playstation",
        "xbox",
        "nintendo",
        "ps5",
        "ps4",
    ],

    "Mobile Gaming": [
        "mobile gaming",
        "mobile game",
        "android game",
        "ios game",
    ],

    "Game Releases": [
        "game release",
        "released",
        "launches",
        "launch",
        "new game",
        "upcoming game",
        "release date",
    ],

    "Gaming Hardware": [
        "gaming hardware",
        "gaming headset",
        "gaming monitor",
        "gaming keyboard",
        "gaming mouse",
        "graphics card",
        "gaming laptop",
        "gaming console",
    ],

    "Esports": [
        "esports",
        "e-sports",
        "competitive gaming",
        "tournament",
        "gaming championship",
    ],

    "Game Development": [
        "game developer",
        "game development",
        "game engine",
        "unreal engine",
        "unity",
        "developer studio",
    ],

    "Gaming Industry": [
        "gaming industry",
        "game studio",
        "publisher",
        "video game company",
        "game business",
    ],

    "Reviews & Features": [
        "review",
        "hands-on",
        "first impressions",
        "preview",
        "analysis",
        "feature",
    ],
}


# =========================================================
# HTTP SESSION
# =========================================================

SESSION = requests.Session()

SESSION.headers.update(
    {
        "User-Agent": USER_AGENT,
        "Accept": (
            "application/rss+xml, "
            "application/xml, "
            "text/xml, "
            "application/atom+xml, "
            "*/*"
        ),
    }
)


# =========================================================
# HELPERS
# =========================================================

def clean_html(value: Any) -> str:
    """
    Remove HTML and normalize whitespace.
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
    ).strip()

    return text


def shorten_text(
    text: str,
    maximum: int = 320
) -> str:

    text = clean_html(text)

    if len(text) <= maximum:
        return text

    shortened = text[:maximum]

    last_space = shortened.rfind(" ")

    if last_space > 100:
        shortened = shortened[:last_space]

    return shortened.rstrip(" .,;:-") + "..."


def normalize_title(
    title: str
) -> str:

    title = clean_html(title).lower()

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


def normalize_url(
    url: str
) -> str:

    if not url:
        return ""

    url = str(url).strip()

    parsed = urlparse(url)

    if parsed.scheme not in (
        "http",
        "https"
    ):
        return ""

    return url


def parse_date(
    entry: Any
) -> datetime:

    possible_values = [

        entry.get("published"),

        entry.get("updated"),

        entry.get("created"),

    ]

    for value in possible_values:

        if not value:
            continue

        try:

            parsed = parsedate_to_datetime(
                str(value)
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


    for key in (
        "published_parsed",
        "updated_parsed",
        "created_parsed",
    ):

        value = entry.get(key)

        if not value:
            continue

        try:

            return datetime(
                value.tm_year,
                value.tm_mon,
                value.tm_mday,
                value.tm_hour,
                value.tm_min,
                value.tm_sec,
                tzinfo=timezone.utc
            )

        except Exception:
            pass


    return datetime.now(
        timezone.utc
    )


def extract_image(
    entry: Any
) -> str:

    # media_content

    media_content = entry.get(
        "media_content",
        []
    )

    if isinstance(
        media_content,
        list
    ):

        for media in media_content:

            if not isinstance(
                media,
                dict
            ):
                continue

            url = normalize_url(
                media.get("url", "")
            )

            if url:
                return url


    # media_thumbnail

    thumbnails = entry.get(
        "media_thumbnail",
        []
    )

    if isinstance(
        thumbnails,
        list
    ):

        for media in thumbnails:

            if not isinstance(
                media,
                dict
            ):
                continue

            url = normalize_url(
                media.get("url", "")
            )

            if url:
                return url


    # enclosure

    enclosures = entry.get(
        "enclosures",
        []
    )

    if isinstance(
        enclosures,
        list
    ):

        for enclosure in enclosures:

            if not isinstance(
                enclosure,
                dict
            ):
                continue

            mime = str(
                enclosure.get(
                    "type",
                    ""
                )
            ).lower()

            url = normalize_url(
                enclosure.get(
                    "href",
                    enclosure.get(
                        "url",
                        ""
                    )
                )
            )

            if (
                url and
                (
                    mime.startswith(
                        "image/"
                    )
                    or
                    not mime
                )
            ):
                return url


    # HTML image inside summary

    for key in (
        "summary",
        "description",
        "content",
    ):

        value = entry.get(
            key
        )

        if isinstance(
            value,
            list
        ):

            value = " ".join(
                str(
                    item.get(
                        "value",
                        ""
                    )
                )
                for item in value
                if isinstance(
                    item,
                    dict
                )
            )

        if not value:
            continue

        match = re.search(
            r'<img[^>]+src=["\']([^"\']+)',
            str(value),
            re.I
        )

        if match:

            url = normalize_url(
                match.group(1)
            )

            if url:
                return url


    return ""


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


    scores = {}


    for category, keywords in (
        CATEGORY_KEYWORDS.items()
    ):

        score = 0

        for keyword in keywords:

            if keyword in text:
                score += 1

        if score:
            scores[category] = score


    if scores:

        best_category = max(
            scores,
            key=scores.get
        )

        if (
            main_category == "Gaming"
            and best_category in (
                "Artificial Intelligence",
                "Cybersecurity",
                "Cloud & Infrastructure",
                "Linux & Open Source",
                "Programming & Development",
                "Smartphones & Mobile",
                "Hardware & Devices",
            )
        ):

            return default_category

        return best_category


    return default_category


def detect_main_category(
    title: str,
    description: str,
    configured_category: str
) -> str:

    text = (
        title +
        " " +
        description +
        " " +
        configured_category
    ).lower()


    gaming_terms = [

        "gaming",
        "game",
        "games",
        "esports",
        "playstation",
        "xbox",
        "nintendo",
        "steam",
        "pc gaming",
        "video game",

    ]


    gaming_score = sum(
        1
        for term in gaming_terms
        if term in text
    )


    if gaming_score >= 1:

        return "Gaming"


    return "Technology"


def create_article_id(
    title: str,
    url: str
) -> str:

    base = (
        normalize_title(title) +
        "|" +
        normalize_url(url)
    )

    digest = hashlib.sha256(
        base.encode(
            "utf-8"
        )
    ).hexdigest()[:20]

    return (
        "techpulse-" +
        digest
    )


def get_source_name(
    feed: dict,
    parsed_feed: Any
) -> str:

    configured_name = (
        feed.get("source")
        or
        feed.get("name")
    )

    if configured_name:
        return str(
            configured_name
        ).strip()


    feed_title = (
        parsed_feed.feed.get(
            "title",
            ""
        )
    )

    feed_title = clean_html(
        feed_title
    )

    if feed_title:
        return feed_title


    return "News Source"


# =========================================================
# FETCH ONE FEED
# =========================================================

def fetch_feed(
    feed_config: dict
) -> list[dict]:

    feed_url = feed_config["url"]

    print(
        f"Fetching: {feed_url}"
    )


    try:

        response = SESSION.get(
            feed_url,
            timeout=REQUEST_TIMEOUT
        )

        response.raise_for_status()


        parsed = feedparser.parse(
            response.content
        )


        if (
            getattr(
                parsed,
                "bozo",
                False
            )
            and
            not parsed.entries
        ):

            raise RuntimeError(
                "Invalid RSS/Atom feed"
            )


        source = get_source_name(
            feed_config,
            parsed
        )


        articles = []


        for entry in parsed.entries[
            :MAX_ARTICLES_PER_FEED
        ]:

            title = clean_html(
                entry.get(
                    "title",
                    ""
                )
            )


            if not title:
                continue


            url = normalize_url(
                entry.get(
                    "link",
                    ""
                )
            )


            if not url:
                continue


            description = ""


            if entry.get(
                "summary"
            ):

                description = (
                    entry.get(
                        "summary"
                    )
                )


            elif entry.get(
                "description"
            ):

                description = (
                    entry.get(
                        "description"
                    )
                )


            elif entry.get(
                "content"
            ):

                content = entry.get(
                    "content"
                )

                if isinstance(
                    content,
                    list
                ):

                    description = " ".join(
                        str(
                            item.get(
                                "value",
                                ""
                            )
                        )
                        for item in content
                        if isinstance(
                            item,
                            dict
                        )
                    )


            description = shorten_text(
                description
            )


            published_date = parse_date(
                entry
            )


            main_category = (
                feed_config.get(
                    "mainCategory",
                    "Technology"
                )
            )


            default_category = (
                feed_config.get(
                    "category",
                    "Technology"
                )
            )


            detected_main = (
                detect_main_category(
                    title,
                    description,
                    main_category
                )
            )


            category = detect_category(
                title,
                description,
                default_category,
                detected_main
            )


            image = extract_image(
                entry
            )


            article = {

                "id": create_article_id(
                    title,
                    url
                ),

                "title": title,

                "description": (
                    description
                    or
                    "Read the latest technology and gaming story."
                ),

                "url": url,

                "image": image,

                "category": category,

                "mainCategory": detected_main,

                "source": source,

                "published": (
                    published_date.isoformat()
                ),

            }


            articles.append(
                article
            )


        print(
            f"  ✓ {len(articles)} articles"
        )


        return articles


    except Exception as error:

        print(
            f"  ✗ Feed failed: {error}"
        )

        return []


# =========================================================
# DUPLICATE REMOVAL
# =========================================================

def remove_duplicates(
    articles: list[dict]
) -> list[dict]:

    unique = []

    seen_urls = set()

    seen_titles = set()


    for article in articles:

        url = (
            normalize_url(
                article.get(
                    "url",
                    ""
                )
            )
        )


        title_key = normalize_title(
            article.get(
                "title",
                ""
            )
        )


        if url in seen_urls:

            continue


        if (
            title_key
            and
            title_key in seen_titles
        ):

            continue


        seen_urls.add(url)

        if title_key:
            seen_titles.add(
                title_key
            )

        unique.append(
            article
        )


    return unique


# =========================================================
# STORY SIMILARITY
# =========================================================

def title_tokens(
    title: str
) -> set[str]:

    words = re.findall(
        r"[a-z0-9]+",
        normalize_title(title)
    )

    stop_words = {

        "the",
        "a",
        "an",
        "and",
        "or",
        "of",
        "to",
        "in",
        "on",
        "for",
        "with",
        "is",
        "are",
        "new",
        "latest",

    }

    return {
        word
        for word in words
        if (
            len(word) > 2
            and
            word not in stop_words
        )
    }


def calculate_similarity(
    title_a: str,
    title_b: str
) -> float:

    a = title_tokens(title_a)

    b = title_tokens(title_b)


    if not a or not b:
        return 0.0


    intersection = len(
        a.intersection(b)
    )

    union = len(
        a.union(b)
    )


    if union == 0:
        return 0.0


    return (
        intersection /
        union
    )


def remove_similar_stories(
    articles: list[dict]
) -> list[dict]:

    result = []


    for article in articles:

        duplicate = False


        for existing in result:

            similarity = (
                calculate_similarity(
                    article["title"],
                    existing["title"]
                )
            )


            if similarity >= 0.82:

                duplicate = True

                break


        if not duplicate:

            result.append(
                article
            )


    return result


# =========================================================
# SORT ARTICLES
# =========================================================

def sort_articles(
    articles: list[dict]
) -> list[dict]:

    return sorted(
        articles,
        key=lambda article: (
            article.get(
                "published",
                ""
            )
        ),
        reverse=True
    )


# =========================================================
# BUILD JSON
# =========================================================

def build_output(
    articles: list[dict]
) -> dict:

    now = datetime.now(
        timezone.utc
    ).isoformat()


    return {

        "success": True,

        "updatedAt": now,

        "total": len(
            articles
        ),

        "articles": articles,

    }


# =========================================================
# VALIDATE OUTPUT
# =========================================================

def validate_output(
    data: dict
) -> None:

    if not isinstance(
        data,
        dict
    ):

        raise ValueError(
            "Output is not an object."
        )


    if data.get(
        "success"
    ) is not True:

        raise ValueError(
            "success must be true."
        )


    articles = data.get(
        "articles"
    )


    if not isinstance(
        articles,
        list
    ):

        raise ValueError(
            "articles must be a list."
        )


    for index, article in enumerate(
        articles
    ):

        required = [

            "id",
            "title",
            "description",
            "url",
            "category",
            "mainCategory",
            "source",
            "published",

        ]


        for field in required:

            if not article.get(
                field
            ):

                raise ValueError(
                    f"Article {index} "
                    f"missing {field}"
                )


        if not re.match(
            r"^https?://",
            article["url"],
            re.I
        ):

            raise ValueError(
                f"Article {index} "
                "has invalid URL."
            )


# =========================================================
# WRITE JSON SAFELY
# =========================================================

def write_json(
    data: dict
) -> None:

    temporary_file = Path(
        str(OUTPUT_FILE) +
        ".tmp"
    )


    with temporary_file.open(
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2
        )

        file.write("\n")


    temporary_file.replace(
        OUTPUT_FILE
    )


# =========================================================
# MAIN
# =========================================================

def main() -> int:

    print()
    print("=" * 60)
    print("TECHPULSE NEWS FETCHER")
    print("=" * 60)
    print()


    all_articles = []


    for feed in FEEDS:

        articles = fetch_feed(
            feed
        )

        all_articles.extend(
            articles
        )


    print()
    print(
        f"Raw articles: {len(all_articles)}"
    )


    if not all_articles:

        print(
            "ERROR: No articles were fetched."
        )

        print(
            "Existing news.json will NOT be overwritten."
        )

        return 1


    # -----------------------------------------------------
    # Remove exact duplicates
    # -----------------------------------------------------

    all_articles = remove_duplicates(
        all_articles
    )


    print(
        f"After URL/title deduplication: "
        f"{len(all_articles)}"
    )


    # -----------------------------------------------------
    # Remove very similar stories
    # -----------------------------------------------------

    all_articles = remove_similar_stories(
        all_articles
    )


    print(
        f"After similarity filtering: "
        f"{len(all_articles)}"
    )


    # -----------------------------------------------------
    # Sort newest first
    # -----------------------------------------------------

    all_articles = sort_articles(
        all_articles
    )


    # -----------------------------------------------------
    # Limit final result
    # -----------------------------------------------------

    all_articles = all_articles[
        :MAX_TOTAL_ARTICLES
    ]


    # -----------------------------------------------------
    # Build output
    # -----------------------------------------------------

    data = build_output(
        all_articles
    )


    # -----------------------------------------------------
    # Validate BEFORE replacing news.json
    # -----------------------------------------------------

    validate_output(
        data
    )


    # -----------------------------------------------------
    # Write
    # -----------------------------------------------------

    write_json(
        data
    )


    print()
    print("=" * 60)
    print("NEWS UPDATE SUCCESSFUL")
    print("=" * 60)
    print(
        f"Articles written: "
        f"{len(all_articles)}"
    )
    print(
        f"Updated at: "
        f"{data['updatedAt']}"
    )
    print(
        f"Output: "
        f"{OUTPUT_FILE}"
    )
    print("=" * 60)
    print()


    return 0


# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":

    try:

        sys.exit(
            main()
        )

    except KeyboardInterrupt:

        print(
            "\nFetch interrupted."
        )

        sys.exit(130)

    except Exception as error:

        print(
            "\nFATAL ERROR:"
        )

        print(
            str(error)
        )

        sys.exit(1)
