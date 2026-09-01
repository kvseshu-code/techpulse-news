```python
#!/usr/bin/env python3

"""
TechPulse News Feed Collector
--------------------------------
RSS/Atom feeds -> normalized news.json

Designed for:
    GitHub Pages
    GitHub Actions
    Python 3.10+

Features:
- Multiple legitimate RSS/Atom sources
- Timeout and retry handling
- RSS + Atom support
- Duplicate removal
- Article age filtering
- Per-source limits
- Global article limit
- Preserves previous news.json if collection fails completely
- Source health information
- Stable JSON structure
- No API keys required
"""

import json
import os
import re
import sys
import time
import hashlib
import html
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse

import requests
import xml.etree.ElementTree as ET


# ============================================================
# CONFIGURATION
# ============================================================

OUTPUT_FILE = "news.json"

MAX_ARTICLES = 120
MAX_ARTICLES_PER_SOURCE = 25

# Keep articles published within this period.
MAX_ARTICLE_AGE_HOURS = 72

# Network settings
REQUEST_TIMEOUT = 20
MAX_RETRIES = 2
RETRY_DELAY_SECONDS = 2

USER_AGENT = (
    "TechPulseNews/1.0 "
    "(RSS news aggregator; +https://kvseshu-code.github.io/techpulse-news/)"
)


# ============================================================
# RSS SOURCES
# ============================================================

FEEDS = [
    # --------------------------------------------------------
    # Technology
    # --------------------------------------------------------

    {
        "name": "Ars Technica",
        "url": "https://feeds.arstechnica.com/arstechnica/index",
        "category": "Technology",
    },

    {
        "name": "TechCrunch",
        "url": "https://techcrunch.com/feed/",
        "category": "Technology",
    },

    {
        "name": "The Verge",
        "url": "https://www.theverge.com/rss/index.xml",
        "category": "Technology",
    },

    {
        "name": "WIRED",
        "url": "https://www.wired.com/feed/rss",
        "category": "Technology",
    },

    {
        "name": "MIT Technology Review",
        "url": "https://www.technologyreview.com/feed/",
        "category": "Technology",
    },

    {
        "name": "The Register",
        "url": "https://www.theregister.com/headlines.atom",
        "category": "Technology",
    },

    {
        "name": "Tom's Hardware",
        "url": "https://www.tomshardware.com/feeds/all",
        "category": "Hardware",
    },

    {
        "name": "TechRadar",
        "url": "https://www.techradar.com/rss",
        "category": "Technology",
    },

    {
        "name": "ZDNET",
        "url": "https://www.zdnet.com/news/rss.xml",
        "category": "Technology",
    },

    # --------------------------------------------------------
    # AI / Science
    # --------------------------------------------------------

    {
        "name": "Google AI Blog",
        "url": "https://blog.google/technology/ai/rss/",
        "category": "AI",
    },

    {
        "name": "NASA",
        "url": "https://www.nasa.gov/rss/dyn/breaking_news.rss",
        "category": "Science",
    },

    {
        "name": "IEEE Spectrum",
        "url": "https://spectrum.ieee.org/feeds/feed.rss",
        "category": "Science",
    },

    # --------------------------------------------------------
    # Gaming
    # --------------------------------------------------------

    {
        "name": "VGC",
        "url": "https://www.videogameschronicle.com/feed/",
        "category": "Gaming",
    },

    {
        "name": "GameSpot",
        "url": "https://www.gamespot.com/feeds/mashup/",
        "category": "Gaming",
    },

    {
        "name": "PC Gamer",
        "url": "https://www.pcgamer.com/rss/",
        "category": "Gaming",
    },

    {
        "name": "Eurogamer",
        "url": "https://www.eurogamer.net/feed",
        "category": "Gaming",
    },

    {
        "name": "Polygon",
        "url": "https://www.polygon.com/rss/index.xml",
        "category": "Gaming",
    },
]


# ============================================================
# HELPERS
# ============================================================

def utc_now():
    return datetime.now(timezone.utc)


def iso_now():
    return utc_now().replace(microsecond=0).isoformat().replace("+00:00", "Z")


def clean_text(value):
    """Remove HTML and normalize whitespace."""

    if not value:
        return ""

    value = html.unescape(str(value))

    # Remove scripts/styles
    value = re.sub(
        r"<(script|style).*?>.*?</\1>",
        " ",
        value,
        flags=re.IGNORECASE | re.DOTALL,
    )

    # Remove HTML tags
    value = re.sub(r"<[^>]+>", " ", value)

    # Normalize whitespace
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def strip_html(value):
    return clean_text(value)


def parse_date(value):
    """
    Parse common RSS/Atom date formats.
    Returns timezone-aware datetime.
    """

    if not value:
        return None

    value = value.strip()

    # RFC 2822 / RSS
    try:
        dt = parsedate_to_datetime(value)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt.astimezone(timezone.utc)

    except Exception:
        pass

    # ISO-8601 / Atom
    try:
        normalized = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt.astimezone(timezone.utc)

    except Exception:
        pass

    return None


def make_id(title, url):
    """
    Generate a stable article identifier.
    """

    source = f"{title.strip().lower()}|{url.strip()}"

    return hashlib.sha256(
        source.encode("utf-8")
    ).hexdigest()[:16]


def extract_domain(url):
    try:
        return urlparse(url).netloc.lower()
    except Exception:
        return ""


def first_text(element, names):
    """
    Find the first available child text for a list of tag names.
    """

    for name in names:
        child = element.find(name)

        if child is not None:
            text = "".join(child.itertext()).strip()

            if text:
                return text

    # Handle namespaces
    for child in element:
        local_name = child.tag.split("}")[-1]

        if local_name in names:
            text = "".join(child.itertext()).strip()

            if text:
                return text

    return ""


def find_child_text_by_local_name(element, names):
    """
    Namespace-independent child lookup.
    """

    for child in element:
        local_name = child.tag.split("}")[-1]

        if local_name in names:
            text = "".join(child.itertext()).strip()

            if text:
                return text

    return ""


def find_link(element):
    """
    Extract RSS <link> or Atom <link href="">.
    """

    # RSS
    for child in element:
        local_name = child.tag.split("}")[-1]

        if local_name == "link":

            href = child.attrib.get("href")

            if href:
                return href.strip()

            text = "".join(child.itertext()).strip()

            if text:
                return text

    return ""


def find_image(element):
    """
    Try common RSS/Media/RDF image locations.
    """

    # media:content
    for child in element.iter():

        local_name = child.tag.split("}")[-1]

        if local_name in (
            "content",
            "thumbnail",
            "enclosure",
        ):

            url = (
                child.attrib.get("url")
                or child.attrib.get("href")
            )

            if url:
                media_type = child.attrib.get("type", "")

                if (
                    local_name != "enclosure"
                    or media_type.startswith("image/")
                    or media_type == ""
                ):
                    return url.strip()

    # image element
    for child in element:
        local_name = child.tag.split("}")[-1]

        if local_name == "image":
            text = "".join(child.itertext()).strip()

            if text:
                return text

    return ""


# ============================================================
# NETWORK
# ============================================================

def download_feed(url):
    """
    Download an RSS/Atom feed with retries.
    """

    last_error = None

    for attempt in range(1, MAX_RETRIES + 2):

        try:
            response = requests.get(
                url,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": (
                        "application/rss+xml, "
                        "application/atom+xml, "
                        "application/xml, "
                        "text/xml, "
                        "*/*"
                    ),
                },
                timeout=REQUEST_TIMEOUT,
            )

            response.raise_for_status()

            if not response.content:
                raise RuntimeError("Empty response")

            return response.content, None

        except Exception as exc:

            last_error = str(exc)

            if attempt <= MAX_RETRIES:
                time.sleep(RETRY_DELAY_SECONDS)

    return None, last_error


# ============================================================
# XML PARSER
# ============================================================

def parse_feed(xml_data, source_name, category):
    """
    Parse RSS 2.0, Atom and common namespace variations.
    """

    root = ET.fromstring(xml_data)

    articles = []

    root_name = root.tag.split("}")[-1].lower()

    # --------------------------------------------------------
    # RSS
    # --------------------------------------------------------

    if root_name in ("rss", "rdf"):

        items = []

        for element in root.iter():

            local_name = element.tag.split("}")[-1].lower()

            if local_name == "item":
                items.append(element)

        for item in items:

            title = (
                first_text(
                    item,
                    ["title"]
                )
                or find_child_text_by_local_name(
                    item,
                    ["title"]
                )
            )

            link = find_link(item)

            description = (
                first_text(
                    item,
                    [
                        "description",
                        "summary",
                        "encoded",
                    ],
                )
                or find_child_text_by_local_name(
                    item,
                    [
                        "description",
                        "summary",
                        "encoded",
                    ],
                )
            )

            date_text = (
                first_text(
                    item,
                    [
                        "pubDate",
                        "published",
                        "updated",
                        "date",
                    ],
                )
                or find_child_text_by_local_name(
                    item,
                    [
                        "pubDate",
                        "published",
                        "updated",
                        "date",
                    ],
                )
            )

            image = find_image(item)

            articles.append(
                build_article(
                    title=title,
                    link=link,
                    description=description,
                    date_text=date_text,
                    image=image,
                    source_name=source_name,
                    category=category,
                )
            )

    # --------------------------------------------------------
    # Atom
    # --------------------------------------------------------

    elif root_name == "feed":

        entries = []

        for element in root.iter():

            local_name = element.tag.split("}")[-1].lower()

            if local_name == "entry":
                entries.append(element)

        for entry in entries:

            title = (
                first_text(entry, ["title"])
                or find_child_text_by_local_name(
                    entry,
                    ["title"]
                )
            )

            link = find_link(entry)

            description = (
                first_text(
                    entry,
                    [
                        "summary",
                        "content",
                    ],
                )
                or find_child_text_by_local_name(
                    entry,
                    [
                        "summary",
                        "content",
                    ],
                )
            )

            date_text = (
                first_text(
                    entry,
                    [
                        "published",
                        "updated",
                    ],
                )
                or find_child_text_by_local_name(
                    entry,
                    [
                        "published",
                        "updated",
                    ],
                )
            )

            image = find_image(entry)

            articles.append(
                build_article(
                    title=title,
                    link=link,
                    description=description,
                    date_text=date_text,
                    image=image,
                    source_name=source_name,
                    category=category,
                )
            )

    return [
        article
        for article in articles
        if article is not None
    ]


def build_article(
    title,
    link,
    description,
    date_text,
    image,
    source_name,
    category,
):
    """
    Normalize one article.
    """

    title = clean_text(title)
    description = clean_text(description)

    link = html.unescape(str(link or "")).strip()
    image = html.unescape(str(image or "")).strip()

    if not title or not link:
        return None

    published = parse_date(date_text)

    if published is None:
        published = utc_now()

    # --------------------------------------------------------
    # Age filter
    # --------------------------------------------------------

    age = utc_now() - published

    if age > timedelta(hours=MAX_ARTICLE_AGE_HOURS):
        return None

    if age < timedelta(days=-1):
        # Reject dates more than one day in the future.
        published = utc_now()

    # Short description
    if len(description) > 500:
        description = description[:497].rstrip() + "..."

    article_id = make_id(title, link)

    return {
        "id": article_id,
        "title": title,
        "description": description,
        "url": link,
        "image": image,
        "source": source_name,
        "category": category,
        "published": published.replace(
            microsecond=0
        ).isoformat().replace("+00:00", "Z"),
        "domain": extract_domain(link),
    }


# ============================================================
# DEDUPLICATION
# ============================================================

def deduplicate_articles(articles):
    """
    Remove duplicates using article ID, URL and normalized title.
    """

    result = []

    seen_ids = set()
    seen_urls = set()
    seen_titles = set()

    for article in articles:

        article_id = article.get("id", "")
        url = article.get("url", "").strip().lower()

        title = re.sub(
            r"[^a-z0-9]+",
            " ",
            article.get("title", "").lower(),
        ).strip()

        if article_id in seen_ids:
            continue

        if url and url in seen_urls:
            continue

        if title and title in seen_titles:
            continue

        seen_ids.add(article_id)

        if url:
            seen_urls.add(url)

        if title:
            seen_titles.add(title)

        result.append(article)

    return result


# ============================================================
# LOAD PREVIOUS DATA
# ============================================================

def load_previous_data():
    """
    Load existing news.json.

    Used as a safety mechanism if all feeds fail.
    """

    if not os.path.exists(OUTPUT_FILE):
        return None

    try:

        with open(
            OUTPUT_FILE,
            "r",
            encoding="utf-8",
        ) as file:

            data = json.load(file)

        if isinstance(data, dict):
            return data

    except Exception as exc:
        print(
            f"[WARN] Could not read previous {OUTPUT_FILE}: {exc}"
        )

    return None


# ============================================================
# COLLECTION
# ============================================================

def collect_news():
    """
    Fetch all configured feeds.
    """

    all_articles = []

    source_status = []

    print("=" * 70)
    print("TechPulse News Collector")
    print("=" * 70)
    print(f"Started : {iso_now()}")
    print(f"Sources : {len(FEEDS)}")
    print()

    for feed in FEEDS:

        name = feed["name"]
        url = feed["url"]
        category = feed["category"]

        print(f"[FETCH] {name}")

        xml_data, error = download_feed(url)

        if xml_data is None:

            print(
                f"[FAIL]  {name}: {error}"
            )

            source_status.append(
                {
                    "name": name,
                    "category": category,
                    "status": "failed",
                    "articles": 0,
                    "error": error,
                }
            )

            continue

        try:

            articles = parse_feed(
                xml_data,
                name,
                category,
            )

            # Per-source limit
            articles = sorted(
                articles,
                key=lambda x: x.get(
                    "published",
                    ""
                ),
                reverse=True,
            )[
                :MAX_ARTICLES_PER_SOURCE
            ]

            all_articles.extend(articles)

            source_status.append(
                {
                    "name": name,
                    "category": category,
                    "status": "ok",
                    "articles": len(articles),
                    "error": None,
                }
            )

            print(
                f"[OK]    {name}: {len(articles)} articles"
            )

        except Exception as exc:

            print(
                f"[FAIL]  {name}: XML parse error: {exc}"
            )

            source_status.append(
                {
                    "name": name,
                    "category": category,
                    "status": "failed",
                    "articles": 0,
                    "error": str(exc),
                }
            )

    return all_articles, source_status


# ============================================================
# OUTPUT
# ============================================================

def create_output(articles, source_status):
    """
    Create final news.json structure.
    """

    articles = deduplicate_articles(articles)

    articles.sort(
        key=lambda x: x.get(
            "published",
            ""
        ),
        reverse=True,
    )

    articles = articles[:MAX_ARTICLES]

    successful_sources = sum(
        1
        for item in source_status
        if item["status"] == "ok"
    )

    failed_sources = sum(
        1
        for item in source_status
        if item["status"] == "failed"
    )

    output = {
        "version": "2.0",
        "generated_at": iso_now(),

        "status": {
            "collector": "ok",
            "total_articles": len(articles),
            "total_sources": len(source_status),
            "successful_sources": successful_sources,
            "failed_sources": failed_sources,
            "max_article_age_hours": MAX_ARTICLE_AGE_HOURS,
        },

        "sources": source_status,

        "articles": articles,
    }

    return output


def write_json(data):
    """
    Safely write news.json.
    """

    temporary_file = OUTPUT_FILE + ".tmp"

    with open(
        temporary_file,
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

    os.replace(
        temporary_file,
        OUTPUT_FILE,
    )


# ============================================================
# MAIN
# ============================================================

def main():

    previous_data = load_previous_data()

    articles, source_status = collect_news()

    # --------------------------------------------------------
    # Complete failure protection
    # --------------------------------------------------------

    if not articles:

        print()
        print("=" * 70)
        print("WARNING: No fresh articles were collected.")
        print("=" * 70)

        if previous_data:

            print(
                "Keeping previous news.json instead of "
                "creating an empty feed."
            )

            # Update health information while preserving
            # previously collected articles.

            previous_data["generated_at"] = iso_now()

            previous_data.setdefault(
                "status",
                {}
            )

            previous_data["status"].update(
                {
                    "collector": "degraded",
                    "message": (
                        "All configured feeds failed. "
                        "Previous article data retained."
                    ),
                    "failed_sources": len(
                        source_status
                    ),
                }
            )

            previous_data["sources"] = source_status

            write_json(previous_data)

            print(
                f"Preserved previous dataset: "
                f"{len(previous_data.get('articles', []))} articles"
            )

            return 0

        print(
            "No previous news.json exists. "
            "Creating an empty dataset."
        )

    # --------------------------------------------------------
    # Normal output
    # --------------------------------------------------------

    output = create_output(
        articles,
        source_status,
    )

    write_json(output)

    successful = output["status"][
        "successful_sources"
    ]

    failed = output["status"][
        "failed_sources"
    ]

    total = output["status"][
        "total_articles"
    ]

    print()
    print("=" * 70)
    print("Collection completed")
    print("=" * 70)
    print(f"Articles : {total}")
    print(f"Sources  : {len(source_status)}")
    print(f"Success  : {successful}")
    print(f"Failed   : {failed}")
    print(f"Output   : {OUTPUT_FILE}")
    print(f"Updated  : {output['generated_at']}")
    print("=" * 70)

    # --------------------------------------------------------
    # GitHub Actions summary
    # --------------------------------------------------------

    github_summary = os.environ.get(
        "GITHUB_STEP_SUMMARY"
    )

    if github_summary:

        with open(
            github_summary,
            "a",
            encoding="utf-8",
        ) as summary:

            summary.write(
                "## TechPulse Feed Update\n\n"
            )

            summary.write(
                f"- Articles: **{total}**\n"
            )

            summary.write(
                f"- Sources: **{len(source_status)}**\n"
            )

            summary.write(
                f"- Successful sources: **{successful}**\n"
            )

            summary.write(
                f"- Failed sources: **{failed}**\n\n"
            )

            summary.write(
                "### Source Health\n\n"
            )

            summary.write(
                "| Source | Category | Status | Articles |\n"
            )

            summary.write(
                "|---|---|---|---:|\n"
            )

            for source in source_status:

                status_icon = (
                    "OK"
                    if source["status"] == "ok"
                    else "FAILED"
                )

                summary.write(
                    f"| {source['name']} "
                    f"| {source['category']} "
                    f"| {status_icon} "
                    f"| {source['articles']} |\n"
                )

    # --------------------------------------------------------
    # Fail GitHub Action only if zero feeds worked.
    # --------------------------------------------------------

    if successful == 0:
        print(
            "[ERROR] Every configured feed failed."
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
```
