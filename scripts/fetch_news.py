#!/usr/bin/env python3

"""
=========================================================
TECHPULSE NEWS FETCHER
=========================================================

Purpose:
    Fetch fresh technology and gaming news and generate
    the root-level news.json file used by the website.

Architecture:

    Google News RSS
            |
            v
    fetch_news.py
            |
            +--> Parse RSS
            |
            +--> Clean content
            |
            +--> Categorize
            |
            +--> Remove duplicates
            |
            +--> Sort by published date
            |
            v
        news.json
            |
            v
      GitHub Pages website

No Google Apps Script.
No database.
No Google Sheets.
No publisher logos.

=========================================================
"""

import json
import hashlib
import html
import re
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import quote_plus

import feedparser
import requests
from bs4 import BeautifulSoup


# =========================================================
# CONFIGURATION
# =========================================================

OUTPUT_FILE = Path("news.json")

MAX_ARTICLES = 120

ARTICLES_PER_FEED = 20

REQUEST_TIMEOUT = 20

USER_AGENT = (
    "Mozilla/5.0 "
    "(compatible; TechPulseNewsBot/1.0; "
    "+https://github.com/kvseshu-code/techpulse-news)"
)


# =========================================================
# SEARCH TOPICS
# =========================================================
#
# These are topic searches rather than publisher feeds.
#
# This means the website does not need to display or use
# publisher branding/logos.
#
# Google News returns current stories matching these topics.
# =========================================================

TECHNOLOGY_TOPICS = [

    (
        "Artificial Intelligence",
        "artificial intelligence AI technology"
    ),

    (
        "Cloud & Infrastructure",
        "cloud computing infrastructure technology"
    ),

    (
        "Cybersecurity",
        "cybersecurity cyber attack security technology"
    ),

    (
        "Software & Applications",
        "software applications technology"
    ),

    (
        "Smartphones & Mobile",
        "smartphone mobile technology"
    ),

    (
        "Hardware & Devices",
        "computer hardware technology devices"
    ),

    (
        "Internet & Web",
        "internet web technology"
    ),

    (
        "Emerging Technology",
        "emerging technology innovation"
    ),

    (
        "Science & Innovation",
        "technology science innovation"
    ),

    (
        "Business & Technology",
        "technology business industry"
    ),

]


GAMING_TOPICS = [

    (
        "PC Gaming",
        "PC gaming"
    ),

    (
        "Console Gaming",
        "console gaming"
    ),

    (
        "Mobile Gaming",
        "mobile gaming"
    ),

    (
        "Game Releases",
        "new game releases video games"
    ),

    (
        "Gaming Hardware",
        "gaming hardware graphics cards gaming devices"
    ),

    (
        "Esports",
        "esports competitive gaming"
    ),

    (
        "Game Development",
        "video game development game developers"
    ),

    (
        "Gaming Industry",
        "gaming industry video game business"
    ),

    (
        "Gaming Updates",
        "video game updates gaming news"
    ),

    (
        "Reviews & Features",
        "video game reviews gaming features"
    ),

]


# =========================================================
# ALL FEEDS
# =========================================================

FEEDS = []


for category, topic in TECHNOLOGY_TOPICS:

    FEEDS.append(
        {
            "mainCategory": "Technology",
            "category": category,
            "topic": topic,
        }
    )


for category, topic in GAMING_TOPICS:

    FEEDS.append(
        {
            "mainCategory": "Gaming",
            "category": category,
            "topic": topic,
        }
    )


# =========================================================
# SESSION
# =========================================================

session = requests.Session()

session.headers.update(
    {
        "User-Agent": USER_AGENT,
        "Accept": (
            "application/rss+xml,"
            "application/xml,"
            "text/xml,"
            "text/html;q=0.9,"
            "*/*;q=0.8"
        ),
    }
)


# =========================================================
# HELPERS
# =========================================================

def clean_text(value):
    """
    Remove HTML and normalize whitespace.
    """

    if value is None:

        return ""

    value = str(value)

    value = html.unescape(value)

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


# =========================================================
# DESCRIPTION CLEANING
# =========================================================

def clean_description(value):
    """
    Keep descriptions short and clean.
    """

    text = clean_text(value)

    if not text:

        return (
            "Read the latest technology and "
            "gaming developments."
        )

    # Remove common RSS boilerplate.

    patterns = [

        r"^\s*read more.*$",

        r"^\s*continue reading.*$",

        r"^\s*click here.*$",

    ]

    for pattern in patterns:

        text = re.sub(
            pattern,
            "",
            text,
            flags=re.IGNORECASE
        ).strip()

    if len(text) > 420:

        text = (
            text[:417].rsplit(" ", 1)[0]
            + "..."
        )

    return text


# =========================================================
# PUBLISHED DATE
# =========================================================

def parse_date(entry):
    """
    Convert RSS dates into UTC ISO format.
    """

    candidates = [

        entry.get("published"),

        entry.get("updated"),

        entry.get("pubDate"),

        entry.get("created"),

    ]

    for value in candidates:

        if not value:

            continue

        try:

            dt = parsedate_to_datetime(
                str(value)
            )

            if dt.tzinfo is None:

                dt = dt.replace(
                    tzinfo=timezone.utc
                )

            dt = dt.astimezone(
                timezone.utc
            )

            return dt.isoformat(
                timespec="seconds"
            ).replace(
                "+00:00",
                "Z"
            )

        except Exception:

            pass

    return datetime.now(
        timezone.utc
    ).isoformat(
        timespec="seconds"
    ).replace(
        "+00:00",
        "Z"
    )


# =========================================================
# ARTICLE URL
# =========================================================

def get_article_url(entry):
    """
    Get original article URL from RSS entry.
    """

    link = entry.get(
        "link",
        ""
    )

    if link:

        return str(link).strip()

    links = entry.get(
        "links",
        []
    )

    for item in links:

        href = item.get(
            "href",
            ""
        )

        if href:

            return str(href).strip()

    return ""


# =========================================================
# ARTICLE IMAGE
# =========================================================

def get_image(entry):
    """
    We intentionally do not use publisher logos.

    If an RSS feed provides a normal article image,
    it may be used by the frontend.

    If no image exists, return empty string.

    The frontend already has a safe placeholder.
    """

    media_content = entry.get(
        "media_content",
        []
    )

    if media_content:

        for media in media_content:

            url = media.get(
                "url",
                ""
            )

            if url and (
                str(url).startswith("http://")
                or
                str(url).startswith("https://")
            ):

                return str(url)

    media_thumbnail = entry.get(
        "media_thumbnail",
        []
    )

    if media_thumbnail:

        for media in media_thumbnail:

            url = media.get(
                "url",
                ""
            )

            if url:

                return str(url)

    enclosures = entry.get(
        "enclosures",
        []
    )

    for enclosure in enclosures:

        url = enclosure.get(
            "href",
            ""
        ) or enclosure.get(
            "url",
            ""
        )

        media_type = str(
            enclosure.get(
                "type",
                ""
            )
        ).lower()

        if (
            url
            and (
                "image" in media_type
                or not media_type
            )
        ):

            return str(url)

    return ""


# =========================================================
# ARTICLE ID
# =========================================================

def create_article_id(
    title,
    url
):
    """
    Stable article identifier.

    URL is preferred because the same article can appear
    in multiple topic feeds.
    """

    base = (
        url.strip().lower()
        if url
        else title.strip().lower()
    )

    digest = hashlib.sha256(
        base.encode(
            "utf-8",
            errors="ignore"
        )
    ).hexdigest()[:20]

    return (
        "techpulse-"
        + digest
    )


# =========================================================
# NORMALIZE TITLE
# =========================================================

def normalize_title(title):
    """
    Used for duplicate detection.
    """

    title = clean_text(
        title
    ).lower()

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
# CREATE TITLE KEY
# =========================================================

def title_key(title):
    """
    Create a compact title comparison key.
    """

    normalized = normalize_title(
        title
    )

    words = normalized.split()

    # Ignore extremely short titles.

    if len(words) > 3:

        words = [
            word
            for word in words
            if len(word) > 2
        ]

    return " ".join(
        words
    )


# =========================================================
# GOOGLE NEWS RSS URL
# =========================================================

def build_feed_url(topic):
    """
    Build a Google News RSS search URL.

    This avoids hard-coding publisher branding into
    the website data.
    """

    query = quote_plus(
        topic
    )

    return (
        "https://news.google.com/rss/search?"
        "q="
        + query
        + "&hl=en-US"
        "&gl=US"
        "&ceid=US:en"
    )


# =========================================================
# FETCH FEED
# =========================================================

def fetch_feed(
    feed_config
):
    """
    Fetch and parse one RSS feed.
    """

    category = feed_config[
        "category"
    ]

    main_category = feed_config[
        "mainCategory"
    ]

    topic = feed_config[
        "topic"
    ]

    url = build_feed_url(
        topic
    )

    print(
        f"Fetching: "
        f"{main_category} / "
        f"{category}"
    )

    try:

        response = session.get(
            url,
            timeout=REQUEST_TIMEOUT
        )

        response.raise_for_status()

        parsed = feedparser.parse(
            response.content
        )

        if parsed.bozo:

            print(
                "  Feed warning:",
                str(
                    parsed.bozo_exception
                )[:200]
            )

        entries = parsed.entries

        print(
            f"  Entries found: "
            f"{len(entries)}"
        )

        articles = []

        for entry in entries[
            :ARTICLES_PER_FEED
        ]:

            title = clean_text(
                entry.get(
                    "title",
                    ""
                )
            )

            if not title:

                continue

            article_url = (
                get_article_url(
                    entry
                )
            )

            if not article_url:

                continue

            description = (
                clean_description(
                    entry.get(
                        "summary",
                        ""
                    )
                    or
                    entry.get(
                        "description",
                        ""
                    )
                )
            )

            published = parse_date(
                entry
            )

            image = get_image(
                entry
            )

            article = {

                "id":
                    create_article_id(
                        title,
                        article_url
                    ),

                "title":
                    title,

                "description":
                    description,

                "url":
                    article_url,

                "image":
                    image,

                "category":
                    category,

                "mainCategory":
                    main_category,

                # Do not expose publisher
                # branding/source names.

                "source":
                    "TechPulse News",

                "published":
                    published,

            }

            articles.append(
                article
            )

        return articles

    except Exception as error:

        print(
            "  Feed failed:",
            str(error)[:300]
        )

        return []


# =========================================================
# DUPLICATE DETECTION
# =========================================================

def remove_duplicates(
    articles
):
    """
    Remove duplicate articles using:

        1. URL
        2. normalized title
        3. title similarity key
    """

    unique = []

    seen_urls = set()

    seen_titles = set()

    seen_keys = set()

    for article in articles:

        url = (
            article.get(
                "url",
                ""
            )
            .strip()
            .lower()
        )

        title = normalize_title(
            article.get(
                "title",
                ""
            )
        )

        key = title_key(
            article.get(
                "title",
                ""
            )
        )

        if url and url in seen_urls:

            continue

        if title and title in seen_titles:

            continue

        if key and key in seen_keys:

            continue

        if url:

            seen_urls.add(
                url
            )

        if title:

            seen_titles.add(
                title
            )

        if key:

            seen_keys.add(
                key
            )

        unique.append(
            article
        )

    return unique


# =========================================================
# REMOVE INVALID ARTICLES
# =========================================================

def validate_articles(
    articles
):
    """
    Remove obviously invalid records.
    """

    valid = []

    for article in articles:

        title = article.get(
            "title",
            ""
        ).strip()

        url = article.get(
            "url",
            ""
        ).strip()

        if len(title) < 8:

            continue

        if not (
            url.startswith(
                "http://"
            )
            or
            url.startswith(
                "https://"
            )
        ):

            continue

        valid.append(
            article
        )

    return valid


# =========================================================
# SORT ARTICLES
# =========================================================

def sort_articles(
    articles
):
    """
    Newest articles first.
    """

    def sort_key(article):

        value = article.get(
            "published",
            ""
        )

        try:

            return datetime.fromisoformat(
                value.replace(
                    "Z",
                    "+00:00"
                )
            )

        except Exception:

            return datetime.min.replace(
                tzinfo=timezone.utc
            )

    return sorted(
        articles,
        key=sort_key,
        reverse=True
    )


# =========================================================
# LIMIT PER CATEGORY
# =========================================================

def balance_articles(
    articles
):
    """
    Prevent one category from consuming the
    entire news feed.

    Maximum 15 articles per category.
    """

    category_counts = {}

    balanced = []

    for article in articles:

        category = article.get(
            "category",
            "General"
        )

        count = category_counts.get(
            category,
            0
        )

        if count >= 15:

            continue

        category_counts[
            category
        ] = count + 1

        balanced.append(
            article
        )

    return balanced


# =========================================================
# MAIN FETCH
# =========================================================

def fetch_all_news():
    """
    Fetch all configured feeds.
    """

    all_articles = []

    print("")
    print("=" * 60)
    print("TECHPULSE NEWS FETCH")
    print("=" * 60)
    print(
        "Feeds configured:",
        len(FEEDS)
    )
    print(
        "Maximum articles:",
        MAX_ARTICLES
    )
    print("=" * 60)
    print("")

    for index, feed_config in enumerate(
        FEEDS,
        start=1
    ):

        print(
            f"[{index}/{len(FEEDS)}] "
            f"{feed_config['category']}"
        )

        articles = fetch_feed(
            feed_config
        )

        all_articles.extend(
            articles
        )

        print(
            f"  Added: "
            f"{len(articles)}"
        )

        print("")

        # Small delay to avoid
        # unnecessary rapid requests.

        time.sleep(
            0.15
        )

    print("=" * 60)

    print(
        "Raw articles:",
        len(all_articles)
    )

    all_articles = validate_articles(
        all_articles
    )

    print(
        "Valid articles:",
        len(all_articles)
    )

    all_articles = remove_duplicates(
        all_articles
    )

    print(
        "After duplicates:",
        len(all_articles)
    )

    all_articles = sort_articles(
        all_articles
    )

    all_articles = balance_articles(
        all_articles
    )

    all_articles = sort_articles(
        all_articles
    )

    if len(all_articles) > MAX_ARTICLES:

        all_articles = (
            all_articles[
                :MAX_ARTICLES
            ]
        )

    print(
        "Final articles:",
        len(all_articles)
    )

    print("=" * 60)

    return all_articles


# =========================================================
# WRITE NEWS.JSON
# =========================================================

def write_news_json(
    articles
):
    """
    Write the final news.json safely.
    """

    updated_at = (
        datetime.now(
            timezone.utc
        )
        .isoformat(
            timespec="seconds"
        )
        .replace(
            "+00:00",
            "Z"
        )
    )

    data = {

        "success":
            True,

        "updatedAt":
            updated_at,

        "total":
            len(articles),

        "articles":
            articles,

    }

    temporary_file = Path(
        "news.json.tmp"
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

        file.write(
            "\n"
        )

    # Atomic replacement.

    temporary_file.replace(
        OUTPUT_FILE
    )

    print("")
    print(
        "news.json successfully written."
    )

    print(
        "Updated:",
        updated_at
    )

    print(
        "Articles:",
        len(articles)
    )


# =========================================================
# MAIN
# =========================================================

def main():

    try:

        articles = fetch_all_news()

        if not articles:

            print("")
            print(
                "ERROR: No valid articles were fetched."
            )

            print(
                "Existing news.json will NOT be overwritten."
            )

            raise SystemExit(
                1
            )

        write_news_json(
            articles
        )

        print("")
        print(
            "TECHPULSE UPDATE COMPLETED SUCCESSFULLY"
        )

    except KeyboardInterrupt:

        print(
            "\nProcess interrupted."
        )

        raise SystemExit(
            130
        )

    except Exception as error:

        print("")
        print(
            "FATAL ERROR:"
        )

        print(
            str(error)
        )

        raise SystemExit(
            1
        )


# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":

    main()
