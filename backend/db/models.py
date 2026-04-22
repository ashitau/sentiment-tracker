"""
Pydantic models that serve as the contract between the pipeline and the API.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class RawDocument(BaseModel):
    source: str
    source_type: str
    id: str
    text: str
    url: Optional[str] = None
    author: Optional[str] = None
    score: Optional[int] = None
    created_utc: Optional[str] = None
    ingested_at: str
    estimated_reach: int = 0
    geo: Optional[str] = None
    subreddit: Optional[str] = None
    sector: Optional[str] = None


class EntitySignalOut(BaseModel):
    canonical_name: str
    sectors: list[str]
    mention_count: int
    total_reach: int
    composite_score: float
    frequency_score: float
    geography_score: float
    sector_score: float
    credibility_score: float
    sentiment_direction: int
    sentiment_label: str
    sentiment_plain_label: str
    sentiment_magnitude: float
    signal_strength: str
    confidence_tier: str
    plain_summary: str
    sample_texts: list[str] = []
    sources: list[str] = []
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None


class TopicClusterOut(BaseModel):
    topic_id: int
    label: str
    plain_label: str
    keywords: list[tuple[str, float]]
    document_count: int
    representative_docs: list[str]
    sectors: list[str] = []
    trend_velocity: float = 0.0


class ValidationMetrics(BaseModel):
    """
    Dual-layer metrics: technical (for engineers) and plain-English (for stakeholders).
    """
    window_label: str                   # e.g. "Last 6 hours"
    total_documents_processed: int
    total_entities_detected: int
    total_topics_found: int
    data_freshness_minutes: int         # age of most recent document
    source_breakdown: dict[str, int]    # source → doc count
    india_mention_pct: float            # % of docs with India geography signal

    # Stakeholder-facing
    overall_signal_quality: str         # "Strong", "Moderate", "Weak"
    data_coverage_label: str            # "Comprehensive", "Partial", "Limited"
    freshness_label: str                # "Live (< 15 min)", "Recent", "Stale"
    india_coverage_label: str           # "Strongly India-focused", etc.
    reliability_summary: str            # plain English paragraph

    # Track record (populated as historical data accumulates)
    signals_that_preceded_moves: Optional[int] = None
    total_signals_tracked: Optional[int] = None
    historical_accuracy_pct: Optional[float] = None
    accuracy_label: Optional[str] = None    # "Predictive (>70%)", "Indicative", "Exploratory"


class CausalPathOut(BaseModel):
    hops: list[str]
    market_entity: str
    affected_sector: str
    causal_score: float
    relationship_chain: list[str]
    plain_explanation: str


class WeakSignalOut(BaseModel):
    """
    A non-financial trending topic that has a credible supply-chain or macro
    linkage to a listed entity. Always labelled 'Exploratory' — never promoted
    to main feed without analyst review.
    """
    raw_topic: str
    normalised_topic: str
    source: str
    mention_count: int
    burst_score: float
    top_entity: str
    top_sector: str
    top_causal_score: float
    causal_chain_plain: str
    hop_count: int
    causal_paths: list[CausalPathOut]
    confidence_tier: str               # always "Exploratory"
    analyst_note: str
    detected_at: str
    status: str                        # "unreviewed" | "promoted" | "dismissed"


class DashboardSnapshot(BaseModel):
    generated_at: str
    top_signals: list[EntitySignalOut]
    topic_clusters: list[TopicClusterOut]
    validation: ValidationMetrics
    trending_keywords: list[dict]       # [{word, weight, sector, sentiment}]
    sector_heatmap: dict[str, dict]     # sector → {score, direction, mention_count}
    weak_signals: list[WeakSignalOut] = []
