"""
Composite scoring engine.
Combines frequency, geography, sector relevance, source credibility,
and sentiment magnitude into a single ranked signal per entity.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Optional
import math


# ── Weight configuration (sums to 1.0) ──────────────────────────────────────
WEIGHTS = {
    "frequency":    0.35,
    "geography":    0.25,
    "sector":       0.15,
    "credibility":  0.10,
    "sentiment":    0.15,
}

SOURCE_CREDIBILITY: dict[str, float] = {
    "news_rss":       1.0,
    "google_trends":  0.9,
    "reddit":         0.7,
    "telegram":       0.5,
    "twitter":        0.6,
}

GEO_WEIGHTS: dict[str, float] = {
    "IN":    1.0,   # India — maximum weight
    "IN-DL": 0.95,
    "IN-MH": 0.95,
    "IN-KA": 0.85,
    "IN-TN": 0.80,
    "IN-GJ": 0.80,
    "US":    0.40,
    "GB":    0.35,
    "SG":    0.50,
    "unknown": 0.20,
}

HIGH_PRIORITY_SECTORS = {"Banking & Finance", "Information Technology", "Macro / Policy"}


@dataclass
class EntitySignal:
    canonical_name: str
    sectors: list[str]
    mention_count: int
    total_reach: int
    geo_distribution: dict[str, int]        # geo_code → mention count
    sentiment_magnitude: float              # 0-1
    sentiment_direction: int                # +1, -1, 0
    sentiment_label: str
    sentiment_plain_label: str
    sources: list[str]
    sample_texts: list[str] = field(default_factory=list)
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None

    # Computed scores (populated by score())
    composite_score: float = 0.0
    frequency_score: float = 0.0
    geography_score: float = 0.0
    sector_score: float = 0.0
    credibility_score: float = 0.0
    trend_velocity: float = 0.0             # burst acceleration

    # Stakeholder-facing fields
    signal_strength: str = ""              # "Strong", "Moderate", "Emerging"
    confidence_tier: str = ""             # "High", "Medium", "Low"
    plain_summary: str = ""


def score(signal: EntitySignal, baseline_mention_count: float = 5.0) -> EntitySignal:
    """Compute all sub-scores and populate composite_score + stakeholder fields."""

    # 1. Frequency score — log-scaled burst above baseline
    signal.frequency_score = min(
        math.log1p(max(signal.mention_count - baseline_mention_count, 0)) / math.log1p(500),
        1.0,
    )

    # 2. Geography score — weighted geo coverage
    total_geo_mentions = sum(signal.geo_distribution.values()) or 1
    weighted_geo = sum(
        GEO_WEIGHTS.get(geo, 0.2) * count
        for geo, count in signal.geo_distribution.items()
    )
    signal.geography_score = min(weighted_geo / total_geo_mentions, 1.0)

    # 3. Sector relevance score
    matched_priority = any(s in HIGH_PRIORITY_SECTORS for s in signal.sectors)
    signal.sector_score = 1.0 if matched_priority else 0.6

    # 4. Source credibility
    cred_scores = [SOURCE_CREDIBILITY.get(s, 0.5) for s in signal.sources]
    signal.credibility_score = sum(cred_scores) / len(cred_scores) if cred_scores else 0.5

    # 5. Composite
    signal.composite_score = round(
        WEIGHTS["frequency"]   * signal.frequency_score
        + WEIGHTS["geography"] * signal.geography_score
        + WEIGHTS["sector"]    * signal.sector_score
        + WEIGHTS["credibility"] * signal.credibility_score
        + WEIGHTS["sentiment"] * signal.sentiment_magnitude,
        4,
    )

    # 6. Stakeholder-facing labels
    signal.signal_strength = _signal_strength(signal.composite_score)
    signal.confidence_tier = _confidence_tier(signal.mention_count, len(set(signal.sources)))
    signal.plain_summary = _build_plain_summary(signal)

    return signal


def _signal_strength(score: float) -> str:
    if score >= 0.65:
        return "Strong"
    if score >= 0.40:
        return "Moderate"
    return "Emerging"


def _confidence_tier(mention_count: int, source_diversity: int) -> str:
    if mention_count >= 50 and source_diversity >= 2:
        return "High"
    if mention_count >= 15 or source_diversity >= 2:
        return "Medium"
    return "Low"


def _build_plain_summary(s: EntitySignal) -> str:
    sectors_str = ", ".join(s.sectors[:2]) if s.sectors else "General Market"
    direction_word = {1: "positive", -1: "negative", 0: "neutral"}.get(s.sentiment_direction, "neutral")

    return (
        f"{s.canonical_name} is seeing {s.signal_strength.lower()} social signal activity "
        f"({s.mention_count} mentions, {s.confidence_tier.lower()} confidence). "
        f"Sentiment is predominantly {s.sentiment_plain_label} across {sectors_str}. "
        f"This signal is sourced from {', '.join(set(s.sources))}."
    )


def rank_signals(signals: list[EntitySignal], top_n: int = 50) -> list[EntitySignal]:
    scored = [score(s) for s in signals]
    return sorted(scored, key=lambda x: x.composite_score, reverse=True)[:top_n]
