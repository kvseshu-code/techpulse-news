"""
============================================================
TECHPULSE — TECHNOLOGY & GAMING NEWS ENGINE
============================================================

GitHub Actions backend

RSS / Atom Sources
        ↓
Python
        ↓
Fetch
        ↓
Parse
        ↓
Clean
        ↓
Categorize
        ↓
Deduplicate
        ↓
Sort
        ↓
news.json
        ↓
GitHub Pages
        ↓
Website

NO TRADITIONAL DATABASE REQUIRED
============================================================
"""

import json
import re
import html
import hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit, urlunsplit

import requests
import feedparser


# ============================================================
# CONFIGURATION
# ============================================================

MAX_ARTICLES = 120

MAX_ARTICLES_PER_SOURCE = 25

MAX_ARTICLE_AGE_HOURS = 72

REQUEST_TIMEOUT = 20

OUTPUT_FILE = (
    Path(__file__).resolve().parent.parent / "news.json"
)


# ============================================================
# NEWS SOURCES
# ============================================================

NEWS_SOURCES = [

    # --------------------------------------------------------
    # TECHNOLOGY
    # --------------------------------------------------------

    {
        "name": "Technology Source 1",
        "category": "Technology",
        "feed": "https://techcrunch.com/feed/",
        "website": "https://techcrunch.com/",
        "active": True
    },

    {
        "name": "Technology Source 2",
        "category": "Technology",
        "feed": "https://www.theverge.com/rss/index.xml",
        "website": "https://www.theverge.com/",
        "active": True
    },

    {
        "name": "Technology Source 3",
        "category": "Technology",
        "feed": "https://feeds.arstechnica.com/arstechnica/index",
        "website": "https://arstechnica.com/",
        "active": True
    },

    {
        "name": "Technology Source 4",
        "category": "Technology",
        "feed": "https://www.wired.com/feed/rss",
        "website": "https://www.wired.com/",
        "active": True
    },

    {
        "name": "Technology Source 5",
        "category": "Technology",
        "feed": "https://www.engadget.com/rss.xml",
        "website": "https://www.engadget.com/",
        "active": True
    },

    {
        "name": "Technology Source 6",
        "category": "Technology",
        "feed": "https://www.cnet.com/rss/news/",
        "website": "https://www.cnet.com/",
        "active": True
    },

    {
        "name": "Technology Source 7",
        "category": "Technology",
        "feed": "https://www.zdnet.com/news/rss.xml",
        "website": "https://www.zdnet.com/",
        "active": True
    },


    # --------------------------------------------------------
    # GAMING
    # --------------------------------------------------------

    {
        "name": "Gaming Source 1",
        "category": "Gaming",
        "feed": "https://feeds.feedburner.com/ign/all",
        "website": "https://www.ign.com/",
        "active": True
    },

    {
        "name": "Gaming Source 2",
        "category": "Gaming",
        "feed": "https://www.pcgamer.com/rss/",
        "website": "https://www.pcgamer.com/",
        "active": True
    },

    {
        "name": "Gaming Source 3",
        "category": "Gaming",
        "feed": "https://www.gamespot.com/feeds/news/",
        "website": "https://www.gamespot.com/",
        "active": True
    },

    {
        "name": "Gaming Source 4",
        "category": "Gaming",
        "feed": "https://www.polygon.com/rss/index.xml",
        "website": "https://www.polygon.com/",
        "active": True
    },

    {
        "name": "Gaming Source 5",
        "category": "Gaming",
        "feed": "https://www.eurogamer.net/feed",
        "website": "https://www.eurogamer.net/",
        "active": True
    },

    {
        "name": "Gaming Source 6",
        "category": "Gaming",
        "feed": "https://www.gamesradar.com/rss/",
        "website": "https://www.gamesradar.com/",
        "active": True
    }

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
        "robotics"
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
        "mobile app"
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
        "privacy"
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
        "devops"
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
        "platform"
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
        "device"
    ],

    "Internet & Web": [
        "internet",
        "website",
        "social media",
        "online",
        "search",
        "browser",
        "streaming",
        "network"
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
        "emerging technology"
    ],

    "Science & Innovation": [
        "science",
        "scientist",
        "research",
        "space",
        "nasa",
        "astronomy",
        "innovation",
        "discovery",
        "laboratory",
        "energy"
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
        "technology industry"
    ],

    "PC Gaming": [
        "pc gaming",
        "pc game",
        "steam",
        "gaming pc",
        "pc gamer"
    ],

    "Console Gaming": [
        "console",
        "playstation",
        "xbox",
        "nintendo",
        "console gaming"
    ],

    "Mobile Gaming": [
        "mobile game",
        "mobile gaming",
        "ios game",
        "android game",
        "smartphone game"
    ],

    "Game Releases": [
        "game release",
        "release date",
        "new game",
        "upcoming game",
        "game launch"
    ],

    "Gaming Hardware": [
        "gaming hardware",
        "gaming headset",
        "gaming mouse",
        "gaming keyboard",
        "gaming monitor",
        "gaming gpu"
    ],

    "Esports": [
        "esports",
        "e-sports",
        "tournament",
        "championship",
        "competitive gaming",
        "pro gamer"
    ],

    "Game Development": [
        "game developer",
        "game development",
        "game engine",
        "developer studio",
        "development studio",
        "game design"
    ],

    "Gaming Industry": [
        "gaming industry",
        "game studio",
        "publisher",
        "gaming business",
        "game sales"
    ],

    "Gaming Updates": [
        "game update",
        "game patch",
        "dlc",
        "expansion",
        "season update"
    ],

    "Reviews & Features": [
        "review",
        "hands-on",
        "preview",
        "feature",
        "analysis",
        "guide"
    ]

}


# ============================================================
# USER AGENT
# ============================================================

HEADERS = {

    "User-Agent":
        "TechPulse-NewsBot/1.0 "
        "(RSS aggregation service)"

}


# ============================================================
# FETCH FEED
# ============================================================

def fetch_feed(source):

    response = requests.get(
        source["feed"],
        headers=HEADERS,
        timeout=REQUEST_TIMEOUT
    )

    response.raise_for_status()

    parsed = feedparser.parse(
            response.content
        )

    if parsed.bozo and not parsed.entries:

        raise RuntimeError(
            "Unable to parse RSS/Atom feed"
        )

    return parsed


# ============================================================
# FETCH ALL NEWS
# ============================================================

def fetch_all_news():

    articles = []

    for source in NEWS_SOURCES:

        if not source["active"]:
            continue

        print(
            f"Fetching: {source['name']}"
        )

        try:

            feed =
                fetch_feed(
                    source
                )

            source_articles = 0

            for entry in feed.entries:

                if (
                    source_articles >=
                    MAX_ARTICLES_PER_SOURCE
                ):
                    break

                article =
                    parse_entry(
                        entry,
                        source
                    )

                if not article:
                    continue

                if not is_recent(
                    article["published"]
                ):
                    continue

                articles.append(
                    article
                )

                source_articles += 1

            print(
                f"  Articles accepted: "
                f"{source_articles}"
            )

        except Exception as error:

            print(
                f"  Source failed: "
                f"{error}"
            )

    return articles


# ============================================================
# PARSE FEED ENTRY
# ============================================================

def parse_entry(
    entry,
    source
):

    title =
        clean_text(
            entry.get(
                "title",
                ""
            )
        )

    if not title:
        return None


    url =
        entry.get(
            "link",
            ""
        ).strip()


    if not url:
        return None


    description =
        entry.get(
            "summary",
            ""
        )


    if not description:

        description =
            entry.get(
                "description",
                ""
            )


    content =
        ""


    if entry.get(
        "content"
    ):

        try:

            content =
                entry["content"][0].get(
                    "value",
                    ""
                )

        except Exception:
            content = ""


    description =
        clean_text(
            description or content
        )


    published =
        get_published_date(
            entry
        )


    if not published:
        return None


    image =
        extract_image(
            entry
        )


    category =
        detect_category(
            source["category"],
            title,
            description
        )


    article_id =
        create_article_id(
            entry.get(
                "id",
                ""
            ) or url or title
        )


    return {

        "id": article_id,

        "title": title,

        "description":
            create_excerpt(
                description
            ),

        "url": url,

        "image": image,

        "source":
            source["name"],

        "sourceWebsite":
            source["website"],

        "mainCategory":
            source["category"],

        "category":
            category,

        "published":
            published.isoformat(),

        "publishedTimestamp":
            int(
                published.timestamp()
                * 1000
            )

    }


# ============================================================
# DATE EXTRACTION
# ============================================================

def get_published_date(
    entry
):

    date_value = None


    if entry.get(
        "published_parsed"
    ):

        try:

            return datetime.fromtimestamp(
                __import__(
                    "calendar"
                ).timegm(
                    entry[
                        "published_parsed"
                    ]
                ),
                tz=timezone.utc
            )

        except Exception:
            pass


    if entry.get(
        "updated_parsed"
    ):

        try:

            return datetime.fromtimestamp(
                __import__(
                    "calendar"
                ).timegm(
                    entry[
                        "updated_parsed"
                    ]
                ),
                tz=timezone.utc
            )

        except Exception:
            pass


    date_value =
        entry.get(
            "published"
        ) or entry.get(
            "updated"
        )


    if date_value:

        try:

            parsed =
                parsedate_to_datetime(
                    date_value
                )

                if parsed.tzinfo is None:
                    parsed =
                        parsed.replace(
                            tzinfo=timezone.utc
                        )

                return parsed.astimezone(
                    timezone.utc
                )

        except Exception:
            pass


    return None


# ============================================================
# RECENT ARTICLE CHECK
# ============================================================

def is_recent(
    published
):

    now =
        datetime.now(
            timezone.utc
        )


    age =
        now - published


    if age < timedelta(
        seconds=0
    ):
        return False


    return (
        age <=
        timedelta(
            hours=MAX_ARTICLE_AGE_HOURS
        )
    )


# ============================================================
# IMAGE EXTRACTION
# ============================================================

def extract_image(
    entry
):

    # --------------------------------------------------------
    # media_content
    # --------------------------------------------------------

    media_content =
        entry.get(
            "media_content",
            []
        )


    for media in media_content:

        url =
            media.get(
                "url",
                ""
            )

        if url:
            return url


    # --------------------------------------------------------
    # media_thumbnail
    # --------------------------------------------------------

    thumbnails =
        entry.get(
            "media_thumbnail",
            []
        )


    for media in thumbnails:

        url =
            media.get(
                "url",
                ""
            )

        if url:
            return url


    # --------------------------------------------------------
    # enclosures
    # --------------------------------------------------------

    enclosures =
        entry.get(
            "enclosures",
            []
        )


    for enclosure in enclosures:

        media_type =
            enclosure.get(
                "type",
                ""
            ).lower()


        url =
            enclosure.get(
                "href",
                ""
            ) or enclosure.get(
                "url",
                ""
            )


        if (
            url and
            (
                not media_type or
                media_type.startswith(
                    "image/"
                )
            )
        ):

            return url


    # --------------------------------------------------------
    # HTML image
    # --------------------------------------------------------

    html_content =
        (
            entry.get(
                "summary",
                ""
            ) or
            entry.get(
                "description",
                ""
            )
        )


    match =
        re.search(
            r'<img[^>]+src=["\']([^"\']+)["\']',
            html_content,
            re.IGNORECASE
        )


    if match:

        return html.unescape(
            match.group(1)
        )


    return ""


# ============================================================
# CATEGORY DETECTION
# ============================================================

def detect_category(
    main_category,
    title,
    description
):

    text =
        (
            f" {title} "
            f"{description} "
        ).lower()


    gaming_categories = {

        "PC Gaming",
        "Console Gaming",
        "Mobile Gaming",
        "Game Releases",
        "Gaming Hardware",
        "Esports",
        "Game Development",
        "Gaming Industry",
        "Gaming Updates",
        "Reviews & Features"

    }


    for category, keywords in (
        CATEGORY_RULES.items()
    ):

        for keyword in keywords:

            if keyword.lower() in text:

                if (
                    main_category ==
                    "Gaming"
                ):

                    if (
                        category in
                        gaming_categories
                    ):

                        return category


                elif (
                    main_category ==
                    "Technology"
                ):

                    if (
                        category not in
                        gaming_categories
                    ):

                        return category


    if (
        main_category ==
        "Gaming"
    ):

        return "Gaming Updates"


    return "Emerging Technology"


# ============================================================
# CLEAN TEXT
# ============================================================

def clean_text(
    value
):

    if not value:
        return ""


    text =
        html.unescape(
            str(value)
        )


    text =
        re.sub(
            r"<script[\s\S]*?</script>",
            " ",
            text,
            flags=re.IGNORECASE
        )


    text =
        re.sub(
            r"<style[\s\S]*?</style>",
            " ",
            text,
            flags=re.IGNORECASE
        )


    text =
        re.sub(
            r"<[^>]+>",
            " ",
            text
        )


    text =
        re.sub(
            r"\s+",
            " ",
            text
        )


    return text.strip()


# ============================================================
# CREATE EXCERPT
# ============================================================

def create_excerpt(
    text
):

    text =
        clean_text(
            text
        )


    if len(text) <= 240:

        return text


    shortened =
        text[:240]


    shortened =
        re.sub(
            r"\s+\S*$",
            "",
            shortened
        )


    return shortened + "..."


# ============================================================
# NORMALIZE TITLE
# ============================================================

def normalize_title(
    title
):

    value =
        str(
            title or ""
        ).lower()


    value =
        re.sub(
            r"https?://\S+",
            "",
            value
        )


    value =
        re.sub(
            r"[^a-z0-9\s]",
            "",
            value
        )


    value =
        re.sub(
            r"\s+",
            " ",
            value
        )


    return value.strip()


# ============================================================
# NORMALIZE URL
# ============================================================

def normalize_url(
    url
):

    try:

        parts =
            urlsplit(
                str(
                    url or ""
                ).lower()
            )


        return urlunsplit(
            (
                parts.scheme,
                parts.netloc,
                parts.path.rstrip("/"),
                "",
                ""
            )
        )

    except Exception:

        return str(
            url or ""
        ).lower().strip()


# ============================================================
# REMOVE DUPLICATES
# ============================================================

def remove_duplicates(
    articles
):

    seen_titles = set()

    seen_urls = set()

    result = []


    for article in articles:

        title_key =
            normalize_title(
                article["title"]
            )


        url_key =
            normalize_url(
                article["url"]
            )


        if (
            not title_key and
            not url_key
        ):

            continue


        if (
            title_key in seen_titles or
            url_key in seen_urls
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
# ARTICLE ID
# ============================================================

def create_article_id(
    value
):

    digest =
        hashlib.sha256(
            str(
                value
            ).encode(
                "utf-8"
            )
        ).hexdigest()


    return (
        "news_" +
        digest[:16]
    )


# ============================================================
# WRITE NEWS.JSON
# ============================================================

def write_news(
    articles
):

    now =
        datetime.now(
            timezone.utc
        )


    articles =
        sorted(
            articles,
            key=lambda article:
                article.get(
                    "publishedTimestamp",
                    0
                ),
            reverse=True
        )


    articles =
        articles[
            :MAX_ARTICLES
        ]


    response = {

        "success": True,

        "updatedAt":
            now.isoformat(),

        "serverTime":
            now.isoformat(),

        "total":
            len(articles),

        "articles":
            articles

    }


    OUTPUT_FILE.write_text(
        json.dumps(
            response,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


    print()
    print(
        "================================================"
    )
    print(
        f"News file updated: {OUTPUT_FILE}"
    )
    print(
        f"Total articles: {len(articles)}"
    )
    print(
        f"Updated at: {now.isoformat()}"
    )
    print(
        "================================================"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print(
        "==============================================="
    )
    print(
        "TECHPULSE NEWS ENGINE"
    )
    print(
        "==============================================="
    )
    print()


    articles =
        fetch_all_news()


    print()
    print(
        f"Total fetched: {len(articles)}"
    )


    articles =
        remove_duplicates(
            articles
        )


    print(
        f"After deduplication: "
        f"{len(articles)}"
    )


    write_news(
        articles
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()
