#!/usr/bin/env python3

import json
import hashlib
import html
import re
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import feedparser
import requests
from bs4 import BeautifulSoup


OUTPUT_FILE = Path("news.json")

MAX_TOTAL_ARTICLES = 150
MAX_PER_FEED = 30
REQUEST_TIMEOUT = 20

USER_AGENT = (
    "TechPulseNewsBot/1.0 "
    "(RSS news aggregation)"
)


FEEDS = [

    {
        "url": "https://feeds.arstechnica.com/arstechnica/index",
        "mainCategory": "Technology",
        "category": "Technology"
    },

    {
        "url": "https://www.wired.com/feed/rss",
        "mainCategory": "Technology",
        "category": "Technology"
    },

    {
        "url": "https://www.zdnet.com/news/rss.xml",
        "mainCategory": "Technology",
        "category": "Technology"
    },

    {
        "url": "https://www.techradar.com/rss",
        "mainCategory": "Technology",
        "category": "Technology"
    },

    {
        "url": "https://www.tomshardware.com/feeds/all",
        "mainCategory": "Technology",
        "category": "Hardware & Devices"
    },

    {
        "url": "https://www.androidauthority.com/feed",
        "mainCategory": "Technology",
        "category": "Smartphones & Mobile"
    },

    {
        "url": "https://www.pcgamer.com/rss/",
        "mainCategory": "Gaming",
        "category": "PC Gaming"
    },

    {
        "url": "https://www.gamespot.com/feeds/news/",
        "mainCategory": "Gaming",
        "category": "Gaming Updates"
    },

    {
        "url": "https://www.eurogamer.net/feed",
        "mainCategory": "Gaming",
        "category": "Gaming Updates"
    },

    {
        "url": "https://www.polygon.com/rss/index.xml",
        "mainCategory": "Gaming",
        "category": "Gaming Updates"
    }

]


session = requests.Session()

session.headers.update({
    "User-Agent": USER_AGENT,
    "Accept": (
        "application/rss+xml, "
        "application/atom+xml, "
        "application/xml, "
        "text/xml, "
        "*/*"
    )
})


def clean_text(value):

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

    return re.sub(
        r"\s+",
        " ",
        text
    ).strip()


def parse_date(entry):

    for value in [
        entry.get("published"),
        entry.get("updated"),
        entry.get("created")
    ]:

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

            return (
                dt.astimezone(
                    timezone.utc
                )
                .isoformat()
                .replace("+00:00", "Z")
            )

        except Exception:
            pass


    for field in [
        "published_parsed",
        "updated_parsed",
        "created_parsed"
    ]:

        parsed = entry.get(field)

        if parsed:

            try:

                timestamp = time.mktime(
                    parsed
                )

                dt = datetime.fromtimestamp(
                    timestamp,
                    tz=timezone.utc
                )

                return (
                    dt.isoformat()
                    .replace("+00:00", "Z")
                )

            except Exception:
                pass


    return (
        datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )


def create_id(url, title):

    raw = (
        str(url).strip()
        + "|"
        + str(title).strip().lower()
    )

    digest = hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()[:20]

    return "techpulse-" + digest


def get_source_name(feed, entry):

    source = ""

    source_data = entry.get(
        "source"
    )

    if isinstance(
        source_data,
        dict
    ):

        source = (
            source_data.get("title")
            or ""
        )

    if not source:

        feed_info = feed.get(
            "feed",
            {}
        )

        source = (
            feed_info.get("title")
            or ""
        )

    return (
        clean_text(source)
        or
        "News Source"
    )


def get_image(entry):

    media_content = entry.get(
        "media_content",
        []
    )

    for media in media_content:

        if isinstance(
            media,
            dict
        ):

            url = media.get("url")

            if url and (
                url.startswith("http://")
                or
                url.startswith("https://")
            ):

                return url


    media_thumbnail = entry.get(
        "media_thumbnail",
        []
    )

    for media in media_thumbnail:

        if isinstance(
            media,
            dict
        ):

            url = media.get("url")

            if url:
                return url


    for enclosure in entry.get(
        "enclosures",
        []
    ):

        if not isinstance(
            enclosure,
            dict
        ):
            continue

        url = (
            enclosure.get("href")
            or
            enclosure.get("url")
        )

        mime = str(
            enclosure.get(
                "type",
                ""
            )
        ).lower()

        if (
            url
            and
            (
                "image" in mime
                or
                re.search(
                    r"\.(jpg|jpeg|png|webp)(\?|$)",
                    url,
                    re.I
                )
            )
        ):

            return url


    return ""


def detect_category(
    title,
    description,
    default_category,
    main_category
):

    text = (
        f"{title} "
        f"{description}"
    ).lower()


    if main_category == "Gaming":

        if any(
            x in text
            for x in [
                "pc gaming",
                "steam",
                "gaming pc",
                "graphics card",
                "gpu"
            ]
        ):
            return "PC Gaming"


        if any(
            x in text
            for x in [
                "mobile game",
                "mobile gaming",
                "android game",
                "ios game"
            ]
        ):
            return "Mobile Gaming"


        if any(
            x in text
            for x in [
                "esports",
                "esport",
                "tournament"
            ]
        ):
            return "Esports"


        if any(
            x in text
            for x in [
                "release",
                "launch",
                "released"
            ]
        ):
            return "Game Releases"


        if any(
            x in text
            for x in [
                "hardware",
                "controller",
                "headset",
                "console"
            ]
        ):
            return "Gaming Hardware"


        return default_category or "Gaming Updates"


    if any(
        x in text
        for x in [
            "artificial intelligence",
            "machine learning",
            "generative ai",
            "chatbot",
            "large language model"
        ]
    ):
        return "Artificial Intelligence"


    if any(
        x in text
        for x in [
            "cybersecurity",
            "cyber security",
            "malware",
            "ransomware",
            "vulnerability",
            "security flaw",
            "zero-day"
        ]
    ):
        return "Cybersecurity"


    if any(
        x in text
        for x in [
            "cloud computing",
            "cloud infrastructure",
            "kubernetes",
            "container",
            "serverless",
            "data center"
        ]
    ):
        return "Cloud & Infrastructure"


    if any(
        x in text
        for x in [
            "iphone",
            "android",
            "smartphone",
            "mobile phone"
        ]
    ):
        return "Smartphones & Mobile"


    if any(
        x in text
        for x in [
            "laptop",
            "processor",
            "cpu",
            "gpu",
            "graphics card",
            "hardware",
            "monitor",
            "ssd"
        ]
    ):
        return "Hardware & Devices"


    if any(
        x in text
        for x in [
            "software",
            "application",
            "app",
            "browser",
            "operating system"
        ]
    ):
        return "Software & Applications"


    return default_category or "Technology"


def fetch_feed(config):

    url = config["url"]

    print(f"Fetching: {url}")

    try:

        response = session.get(
            url,
            timeout=REQUEST_TIMEOUT
        )

        response.raise_for_status()

        feed = feedparser.parse(
            response.content
        )

        articles = []

        for entry in feed.entries[
            :MAX_PER_FEED
        ]:

            title = clean_text(
                entry.get(
                    "title",
                    ""
                )
            )

            if not title:
                continue


            article_url = str(
                entry.get(
                    "link",
                    ""
                )
            ).strip()


            if not (
                article_url.startswith(
                    "http://"
                )
                or
                article_url.startswith(
                    "https://"
                )
            ):
                continue


            description = clean_text(
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


            if len(description) > 350:

                description = (
                    description[:347]
                    + "..."
                )


            article = {

                "id": create_id(
                    article_url,
                    title
                ),

                "title": title,

                "description": description,

                "url": article_url,

                "image": get_image(
                    entry
                ),

                "category": detect_category(
                    title,
                    description,
                    config.get(
                        "category",
                        "Technology"
                    ),
                    config[
                        "mainCategory"
                    ]
                ),

                "mainCategory": config[
                    "mainCategory"
                ],

                "source": get_source_name(
                    feed,
                    entry
                ),

                "published": parse_date(
                    entry
                )

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
            f"  Feed failed: {error}"
        )

        return []


def deduplicate(articles):

    seen_urls = set()

    seen_titles = set()

    result = []


    for article in articles:

        url_key = (
            article["url"]
            .strip()
            .lower()
        )


        title_key = re.sub(
            r"\s+",
            " ",
            re.sub(
                r"[^a-z0-9]+",
                " ",
                article["title"].lower()
            )
        ).strip()


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


def main():

    print("")
    print(
        "=========================================="
    )
    print(
        "       TECHPULSE NEWS FETCHER"
    )
    print(
        "=========================================="
    )
    print("")


    all_articles = []


    for config in FEEDS:

        articles = fetch_feed(
            config
        )

        all_articles.extend(
            articles
        )


    print("")

    print(
        "Before deduplication:",
        len(all_articles)
    )


    all_articles = deduplicate(
        all_articles
    )


    print(
        "After deduplication:",
        len(all_articles)
    )


    all_articles.sort(
        key=lambda article:
            article.get(
                "published",
                ""
            ),
        reverse=True
    )


    all_articles = all_articles[
        :MAX_TOTAL_ARTICLES
    ]


    updated_at = (
        datetime.now(
            timezone.utc
        )
        .isoformat()
        .replace(
            "+00:00",
            "Z"
        )
    )


    output = {

        "success": True,

        "updatedAt": updated_at,

        "total": len(
            all_articles
        ),

        "articles": all_articles

    }


    OUTPUT_FILE.write_text(
        json.dumps(
            output,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


    print("")
    print(
        "news.json created successfully."
    )
    print(
        "Total articles:",
        len(all_articles)
    )
    print(
        "Updated:",
        updated_at
    )
    print("")


if __name__ == "__main__":
    main()
