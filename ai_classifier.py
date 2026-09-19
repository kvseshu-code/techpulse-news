import json
import os
import sys
from pathlib import Path

from openai import OpenAI


ROOT = Path(__file__).resolve().parent
NEWS_FILE = ROOT / "news.json"
CONFIG_FILE = ROOT / "config" / "ai_classifier.json"
OUTPUT_FILE = ROOT / "ai_classification.json"


CATEGORIES = [
    "AI",
    "Cybersecurity",
    "Technology",
    "Hardware",
    "Gaming",
    "Space",
    "Linux",
    "Cloud",
    "Enterprise",
    "Robotics",
    "Quantum",
]


def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def classify(client, model, article):
    title = str(article.get("title", "") or "").strip()
    description = str(article.get("description", "") or "").strip()

    current = {
        "category": article.get("category"),
        "subcategory": article.get("subcategory"),
        "secondary_topics": article.get("secondary_topics", []),
        "content_type": article.get("content_type"),
        "relevance": article.get("relevance"),
        "confidence": article.get("classification_confidence"),
    }

    prompt = f"""
You are the editorial classification engine for TechPulse, a technology
and gaming news publication.

Classify the article based on its ACTUAL SUBJECT, not merely company names,
product names, or incidental technologies.

TechPulse categories:
{", ".join(CATEGORIES)}

Rules:

1. Choose exactly ONE primary category.
2. You may choose zero or more secondary topics.
3. A company name must NOT determine the category.
4. The event/action/topic described by the article should determine the
   primary category.
5. A cybersecurity attack, breach, vulnerability, malware, ransomware,
   phishing, hacking, or security incident should normally be Cybersecurity,
   even when AI, Microsoft, Google, NVIDIA, etc. are involved.
6. A gaming article should be Gaming even when it discusses gaming hardware.
   Hardware may be secondary.
7. A hardware article should be Hardware when physical computing devices,
   components, chips, monitors, storage, memory, GPUs, CPUs, etc. are the
   primary subject.
8. AI should be primary when artificial intelligence itself is the main topic.
9. Quantum should be primary when quantum computing/quantum technology is
   the main topic.
10. Space should be primary for space missions, spacecraft, satellites,
    astronomy, launch systems, or space exploration.
11. General movies, television, celebrity, entertainment, travel, food,
    shopping, coupons, and unrelated lifestyle stories should be REJECT.
12. Product reviews, buying guides, deals, and consumer recommendation
    articles should normally be REVIEW rather than normal news.
13. Research may be KEEP when it is clearly technology/science research
    relevant to TechPulse.
14. Tutorials/how-to articles may be REVIEW unless they are substantial
    technology news or research.
15. If the article is ambiguous, use REVIEW rather than inventing certainty.
16. Do not use the existing classification blindly. It is only a hint.

Return ONLY valid JSON with these fields:

{{
  "category": "...",
  "subcategory": "...",
  "secondary_topics": [],
  "content_type": "news|review|analysis|research|tutorial|event|commerce|entertainment|general_interest",
  "relevance": "KEEP|REVIEW|REJECT",
  "confidence": "High|Medium|Low",
  "reason": "short explanation"
}}

Existing deterministic classification:
{json.dumps(current, ensure_ascii=False)}

ARTICLE TITLE:
{title}

ARTICLE DESCRIPTION:
{description}
"""

    response = client.responses.create(
        model=model,
        input=prompt,
    )

    text = response.output_text.strip()

    try:
        result = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Model returned invalid JSON for article: {title}\n{text}"
        ) from exc

    required = [
        "category",
        "subcategory",
        "secondary_topics",
        "content_type",
        "relevance",
        "confidence",
        "reason",
    ]

    for field in required:
        if field not in result:
            raise RuntimeError(
                f"Missing field '{field}' for article: {title}"
            )

    if result["category"] not in CATEGORIES:
        raise RuntimeError(
            f"Invalid category '{result['category']}' for article: {title}"
        )

    if result["relevance"] not in {"KEEP", "REVIEW", "REJECT"}:
        raise RuntimeError(
            f"Invalid relevance '{result['relevance']}' for article: {title}"
        )

    if result["confidence"] not in {"High", "Medium", "Low"}:
        raise RuntimeError(
            f"Invalid confidence '{result['confidence']}' for article: {title}"
        )

    return result


def main():
    if not NEWS_FILE.exists():
        print("[ERROR] news.json not found.")
        sys.exit(1)

    if not CONFIG_FILE.exists():
        print("[ERROR] config\\ai_classifier.json not found.")
        sys.exit(1)

    api_key = os.environ.get("OPENAI_API_KEY")

    if not api_key:
        print("[ERROR] OPENAI_API_KEY environment variable is not set.")
        print()
        print("Set it in Windows before running the classifier.")
        sys.exit(1)

    config = load_json(CONFIG_FILE)
    news = load_json(NEWS_FILE)

    model = config.get("model", "gpt-5.6-luna")
    max_articles = int(config.get("max_articles", len(news["articles"])))

    articles = news.get("articles", [])[:max_articles]

    client = OpenAI(api_key=api_key)

    results = []

    total = len(articles)

    print("=" * 70)
    print("TECHPULSE AI CLASSIFIER")
    print("=" * 70)
    print(f"Model: {model}")
    print(f"Articles: {total}")
    print(f"Output: {OUTPUT_FILE.name}")
    print()
    print("IMPORTANT: news.json will NOT be modified.")
    print()

    for index, article in enumerate(articles, 1):
        title = str(article.get("title", "") or "").strip()

        print(f"[{index}/{total}] {title[:100]}")

        try:
            classification = classify(client, model, article)

            results.append({
                "id": article.get("id"),
                "title": title,
                "url": article.get("url"),
                "existing": {
                    "category": article.get("category"),
                    "relevance": article.get("relevance"),
                    "content_type": article.get("content_type"),
                    "confidence": article.get("classification_confidence"),
                },
                "ai": classification,
            })

            print(
                f"    -> {classification['category']} | "
                f"{classification['relevance']} | "
                f"{classification['confidence']}"
            )

        except Exception as exc:
            print(f"    [ERROR] {exc}")

            results.append({
                "id": article.get("id"),
                "title": title,
                "url": article.get("url"),
                "error": str(exc),
            })

    output = {
        "schema_version": 1,
        "classifier": "TechPulse AI Classifier",
        "model": model,
        "source": NEWS_FILE.name,
        "article_count": len(results),
        "results": results,
    }

    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print()
    print("=" * 70)
    print(f"[OK] AI classification complete: {OUTPUT_FILE.name}")
    print("[OK] news.json was not modified.")
    print("=" * 70)


if __name__ == "__main__":
    main()