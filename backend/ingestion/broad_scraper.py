"""
Broad ingestion — non-financial public sentiment.

Sources:
  1. Google Trends: India-wide trending searches (all categories) + rising queries
  2. Reddit: general Indian subreddits (not finance-specific)

These documents feed the weak signal detector, NOT the main sentiment pipeline.
The goal is to capture consumer behaviour, supply disruptions, and social mood
that could have downstream market effects via supply chain linkages.
"""
import time
from datetime import datetime, timezone
from typing import Generator, Optional
import praw
import pandas as pd
from pytrends.request import TrendReq
from loguru import logger

# General Indian subreddits — broad public sentiment, not finance-specific
BROAD_SUBREDDITS = [
    "india",
    "AskIndia",
    "mumbai",
    "delhi",
    "bangalore",
    "pune",
    "IndiaSpeaks",
    "IndianFood",
    "indianews",
    "technology",     # Indian tech discussions
    "mildlyinfuriating",  # often surfaces product/supply complaints
]

GEO_INDIA = "IN"


# ── Google Trends: Real-time trending ────────────────────────────────────────

def fetch_india_trending_searches() -> list[dict]:
    """
    Fetch today's top trending searches in India across all categories.
    These are real-time breakout topics — highest signal-to-noise for weak signals.
    """
    pytrends = TrendReq(hl="en-IN", tz=330, timeout=(10, 10), retries=2, backoff_factor=0.5)
    results = []
    try:
        df = pytrends.trending_searches(pn="india")
        for term in df[0].tolist():
            results.append({
                "topic": term,
                "source": "google_trends_trending",
                "count": 100,  # trending = high but exact count unavailable
                "is_rising": True,
                "geo": GEO_INDIA,
                "fetched_at": datetime.now(tz=timezone.utc).isoformat(),
            })
        logger.info(f"Google Trends trending: {len(results)} topics")
    except Exception as exc:
        logger.warning(f"Trending searches failed: {exc}")
    return results


def fetch_india_rising_queries(seed_categories: Optional[list[str]] = None) -> list[dict]:
    """
    Fetch 'rising' (breakout) queries from Google Trends for broad category seeds.
    Rising queries are those showing >5000% growth — the purest burst signal.
    """
    pytrends = TrendReq(hl="en-IN", tz=330, timeout=(10, 10), retries=2, backoff_factor=0.5)

    # Seed terms span broad life categories — not finance
    seeds = seed_categories or [
        "shortage india",      # supply disruptions
        "price increase india", # cost pressures
        "strike india",         # labour / logistics disruptions
        "shortage",
        "expensive india",
        "unavailable india",
    ]

    results = []
    for seed in seeds:
        try:
            pytrends.build_payload([seed], timeframe="now 7-d", geo=GEO_INDIA)
            rq = pytrends.related_queries()
            rising = rq.get(seed, {}).get("rising")
            if rising is not None and not rising.empty:
                for _, row in rising.iterrows():
                    results.append({
                        "topic": row["query"],
                        "source": "google_trends_rising",
                        "count": int(row.get("value", 50)),
                        "is_rising": True,
                        "seed_keyword": seed,
                        "geo": GEO_INDIA,
                        "fetched_at": datetime.now(tz=timezone.utc).isoformat(),
                    })
            time.sleep(1.5)
        except Exception as exc:
            logger.warning(f"Rising queries failed for seed '{seed}': {exc}")

    logger.info(f"Google Trends rising queries: {len(results)} topics")
    return results


# ── Reddit: broad subreddit scraping ─────────────────────────────────────────

def scrape_broad_reddit(
    limit: int = 100,
    time_filter: str = "day",
) -> Generator[dict, None, None]:
    """
    Scrape general Indian subreddits for trending discussions.
    Yields normalised documents suitable for the weak signal pipeline.
    """
    import os
    reddit = praw.Reddit(
        client_id=os.environ["REDDIT_CLIENT_ID"],
        client_secret=os.environ["REDDIT_CLIENT_SECRET"],
        user_agent=os.environ.get("REDDIT_USER_AGENT", "SentimentTracker/1.0"),
    )

    for sub_name in BROAD_SUBREDDITS:
        try:
            subreddit = reddit.subreddit(sub_name)
            for post in subreddit.hot(limit=limit):
                if post.score < 50:  # filter low-engagement posts
                    continue
                yield {
                    "source": "reddit_broad",
                    "subreddit": sub_name,
                    "topic": post.title,
                    "text": f"{post.title}\n{post.selftext}".strip(),
                    "count": post.num_comments,
                    "score": post.score,
                    "is_rising": post.score > 500,  # proxy for virality
                    "url": f"https://reddit.com{post.permalink}",
                    "created_utc": datetime.fromtimestamp(post.created_utc, tz=timezone.utc).isoformat(),
                    "fetched_at": datetime.now(tz=timezone.utc).isoformat(),
                    "geo": "IN",  # subreddit is India-specific
                }
        except Exception as exc:
            logger.warning(f"Broad scrape failed for r/{sub_name}: {exc}")


def aggregate_topic_counts(items: list[dict]) -> list[dict]:
    """
    Collapse duplicate/similar topic strings into merged items with summed counts.
    Keeps only items with count >= 2 (appeared in multiple posts/searches).
    """
    from collections import Counter
    counter: Counter = Counter()
    meta: dict[str, dict] = {}

    for item in items:
        topic = item.get("topic", "").strip().lower()
        if not topic:
            continue
        counter[topic] += item.get("count", 1)
        if topic not in meta:
            meta[topic] = {
                "source": item.get("source", "unknown"),
                "is_rising": item.get("is_rising", False),
                "geo": item.get("geo", "IN"),
            }
        elif item.get("is_rising"):
            meta[topic]["is_rising"] = True

    return [
        {
            "topic": topic,
            "count": count,
            **meta[topic],
        }
        for topic, count in counter.most_common(500)
        if count >= 1
    ]


async def run_broad_ingestion() -> list[dict]:
    """
    Orchestrate all broad ingestion sources and return merged topic list.
    """
    all_items: list[dict] = []

    # Google Trends
    all_items.extend(fetch_india_trending_searches())
    all_items.extend(fetch_india_rising_queries())

    # Reddit broad
    try:
        for doc in scrape_broad_reddit():
            all_items.append(doc)
    except Exception as exc:
        logger.error(f"Broad Reddit ingestion failed: {exc}")

    merged = aggregate_topic_counts(all_items)
    logger.info(f"Broad ingestion complete: {len(all_items)} raw items → {len(merged)} merged topics")
    return merged
