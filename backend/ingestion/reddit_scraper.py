import os
import asyncio
from datetime import datetime, timezone
from typing import Generator
import praw
from loguru import logger

INDIA_FINANCE_SUBREDDITS = [
    "IndianStockMarket",
    "IndiaInvestments",
    "NSEbse",
    "DalalStreetTalks",
    "IndianStreetBets",
    "personalfinanceindia",
    "RichIndia",
    "ValuePickr",
]

QUERY_KEYWORDS = [
    "NIFTY", "SENSEX", "NSE", "BSE", "RBI", "SEBI",
    "Reliance", "HDFC", "Infosys", "TCS", "Wipro",
    "FII", "DII", "FNO", "IPO", "earnings", "results",
    "budget", "inflation", "rate cut", "rate hike",
]


def _build_reddit_client() -> praw.Reddit:
    return praw.Reddit(
        client_id=os.environ["REDDIT_CLIENT_ID"],
        client_secret=os.environ["REDDIT_CLIENT_SECRET"],
        user_agent=os.environ.get("REDDIT_USER_AGENT", "SentimentTracker/1.0"),
    )


def scrape_subreddit(
    subreddit_name: str,
    limit: int = 200,
    time_filter: str = "day",
) -> Generator[dict, None, None]:
    reddit = _build_reddit_client()
    subreddit = reddit.subreddit(subreddit_name)

    for post in subreddit.top(time_filter=time_filter, limit=limit):
        yield _normalise_post(post, subreddit_name)
        for comment in post.comments.list():
            if hasattr(comment, "body") and len(comment.body) > 20:
                yield _normalise_comment(comment, post.id, subreddit_name)


def _normalise_post(post, subreddit: str) -> dict:
    return {
        "source": "reddit",
        "source_type": "post",
        "id": post.id,
        "subreddit": subreddit,
        "text": f"{post.title}\n{post.selftext}".strip(),
        "url": f"https://reddit.com{post.permalink}",
        "author": str(post.author),
        "score": post.score,
        "num_comments": post.num_comments,
        "upvote_ratio": post.upvote_ratio,
        "created_utc": datetime.fromtimestamp(post.created_utc, tz=timezone.utc).isoformat(),
        "ingested_at": datetime.now(tz=timezone.utc).isoformat(),
        "estimated_reach": _estimate_reach(post.score, post.num_comments),
        "flair": post.link_flair_text,
    }


def _normalise_comment(comment, parent_post_id: str, subreddit: str) -> dict:
    return {
        "source": "reddit",
        "source_type": "comment",
        "id": comment.id,
        "parent_post_id": parent_post_id,
        "subreddit": subreddit,
        "text": comment.body,
        "url": f"https://reddit.com{comment.permalink}",
        "author": str(comment.author),
        "score": comment.score,
        "created_utc": datetime.fromtimestamp(comment.created_utc, tz=timezone.utc).isoformat(),
        "ingested_at": datetime.now(tz=timezone.utc).isoformat(),
        "estimated_reach": _estimate_reach(comment.score, 0),
        "flair": None,
    }


def _estimate_reach(score: int, num_comments: int) -> int:
    """Rough proxy: upvotes × 10 + comments × 5 (not unique views but correlated)."""
    return max(score, 0) * 10 + num_comments * 5


async def run_full_ingestion(store_fn) -> dict:
    """Scrape all subreddits and pass documents to store_fn(doc)."""
    totals = {"posts": 0, "comments": 0, "errors": 0}

    for sub in INDIA_FINANCE_SUBREDDITS:
        try:
            logger.info(f"Scraping r/{sub}")
            for doc in scrape_subreddit(sub):
                await store_fn(doc)
                totals["comments" if doc["source_type"] == "comment" else "posts"] += 1
        except Exception as exc:
            logger.error(f"Failed r/{sub}: {exc}")
            totals["errors"] += 1

    logger.info(f"Reddit ingestion complete: {totals}")
    return totals
