"""
Weak Signal Detector.

Pipeline:
  1. Receive bursting non-financial topics from broad ingestion
  2. Run Kleinberg burst detection to confirm it's a genuine spike
  3. Traverse causal graph — surface only topics with ≤3 hops to a listed entity
  4. Score and label with confidence tier (always "Exploratory" or "Unconfirmed")
  5. Return WeakSignal objects for the API / frontend

Design principle: these signals NEVER appear in the main constellation.
They surface in a separate "Signals to Watch" panel so the main view stays
clean and high-confidence. Analysts must explicitly promote a weak signal
before it enters the primary feed.
"""
from __future__ import annotations

import re
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from loguru import logger

from backend.nlp.causal_graph import find_causal_paths, CausalPath


@dataclass
class WeakSignal:
    raw_topic: str                          # exactly as detected from source
    normalised_topic: str                   # cleaned, lowercase
    source: str                             # "google_trends_rising" | "reddit_broad" | etc.
    mention_count: int
    burst_score: float                      # velocity above baseline, 0-1
    causal_paths: list[CausalPath]          # all paths found, sorted by score
    top_entity: str                         # highest-score terminal entity
    top_sector: str
    top_causal_score: float
    causal_chain_plain: str                 # human-readable path string
    confidence_tier: str                    # always "Exploratory" for weak signals
    analyst_note: str                       # plain English briefing for non-technical reader
    detected_at: str

    # UI fields
    status: str = "unreviewed"              # "unreviewed" | "promoted" | "dismissed"
    hop_count: int = 0
    signal_type: str = "weak"              # always "weak" until promoted


def detect_weak_signals(
    trending_topics: list[dict],
    baseline_counts: Optional[dict[str, float]] = None,
    min_burst_score: float = 0.3,
    min_causal_score: float = 0.35,
) -> list[WeakSignal]:
    """
    Main entry point.

    trending_topics: list of dicts with keys:
        - topic (str)
        - count (int)
        - source (str)
        - is_rising (bool) — from Google Trends "rising" flag
    baseline_counts: historical average counts per topic (optional — used for burst scoring)
    """
    signals: list[WeakSignal] = []

    for item in trending_topics:
        raw = item.get("topic", "").strip()
        if not raw or len(raw) < 4:
            continue

        normalised = _normalise(raw)

        # Skip if it's a known financial term — those are handled by main pipeline
        if _is_financial_term(normalised):
            continue

        count = item.get("count", 1)
        is_rising = item.get("is_rising", False)
        source = item.get("source", "unknown")

        burst = _burst_score(normalised, count, is_rising, baseline_counts)
        if burst < min_burst_score:
            continue

        # Causal graph traversal
        paths = find_causal_paths(normalised, max_hops=3)
        if not paths:
            logger.debug(f"No causal path found for: '{normalised}' — filtered")
            continue

        top_path = paths[0]
        if top_path.causal_score < min_causal_score:
            continue

        chain_plain = " → ".join(top_path.hops)
        analyst_note = _build_analyst_note(raw, top_path, burst, count)

        signals.append(WeakSignal(
            raw_topic=raw,
            normalised_topic=normalised,
            source=source,
            mention_count=count,
            burst_score=round(burst, 3),
            causal_paths=paths[:5],
            top_entity=top_path.market_entity,
            top_sector=top_path.affected_sector,
            top_causal_score=top_path.causal_score,
            causal_chain_plain=chain_plain,
            confidence_tier="Exploratory",
            analyst_note=analyst_note,
            detected_at=datetime.now(tz=timezone.utc).isoformat(),
            hop_count=len(top_path.hops) - 1,
        ))

    # Rank by composite: burst × causal_score
    signals.sort(key=lambda s: s.burst_score * s.top_causal_score, reverse=True)
    logger.info(f"Weak signal detector: {len(trending_topics)} topics in → {len(signals)} signals out")
    return signals


def _normalise(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


FINANCIAL_TERMS = {
    "nifty", "sensex", "bse", "nse", "sebi", "rbi", "ipo", "fii", "dii",
    "stock", "share", "equity", "mutual fund", "etf", "derivative", "futures",
    "options", "intraday", "trading", "broker", "zerodha", "groww", "upstox",
    "smallcap", "midcap", "largecap", "bluechip", "dividend", "earnings",
}


def _is_financial_term(text: str) -> bool:
    words = set(text.split())
    return bool(words & FINANCIAL_TERMS)


def _burst_score(
    topic: str,
    count: int,
    is_rising: bool,
    baseline: Optional[dict[str, float]],
) -> float:
    """
    Score how anomalous this topic's frequency is.
    Rising flag from Google Trends carries significant weight on its own.
    """
    base_score = 0.0

    if is_rising:
        base_score += 0.5  # Google's own burst detection already did the work

    if baseline and topic in baseline:
        expected = baseline[topic]
        if expected > 0:
            velocity = (count - expected) / expected
            base_score += min(velocity / 5.0, 0.5)  # cap contribution at 0.5
    else:
        # No baseline — use absolute count proxy (rough)
        base_score += min(math.log1p(count) / math.log1p(1000), 0.4)

    return min(base_score, 1.0)


def _build_analyst_note(raw: str, path: CausalPath, burst: float, count: int) -> str:
    burst_word = "strongly" if burst >= 0.7 else ("moderately" if burst >= 0.4 else "mildly")
    hop_word = "directly" if path.causal_score >= 0.85 else (
        "indirectly" if path.causal_score >= 0.55 else "distantly"
    )
    chain_str = " → ".join(path.hops[1:])  # skip the topic node itself

    return (
        f"'{raw.title()}' is {burst_word} trending in India ({count} mentions, burst detected). "
        f"This topic is {hop_word} linked to {path.market_entity} via the supply chain: {chain_str}. "
        f"Causal confidence is {int(path.causal_score * 100)}% ({path.affected_sector} sector). "
        f"This is an EXPLORATORY signal — verify through sector-specific sources before drawing conclusions."
    )
