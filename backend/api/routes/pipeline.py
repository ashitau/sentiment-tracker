"""
Pipeline orchestration — runs ingestion + NLP + scoring and caches the result.
Called on a schedule and also used by API routes to serve cached snapshots.
"""
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional
import json

from loguru import logger

from backend.db.models import (
    DashboardSnapshot, EntitySignalOut, TopicClusterOut,
    ValidationMetrics, RawDocument, WeakSignalOut, CausalPathOut,
)
from backend.ingestion.reddit_scraper import run_full_ingestion
from backend.ingestion.google_trends import (
    fetch_sector_trends, trends_to_documents,
)
from backend.ingestion.broad_scraper import run_broad_ingestion
from backend.nlp.entity_extractor import extract_entities
from backend.nlp.sentiment import analyse_batch, aggregate_entity_sentiment
from backend.nlp.topic_modeler import fit_topics, extract_topic_clusters
from backend.nlp.scorer import EntitySignal, rank_signals
from backend.nlp.weak_signal_detector import detect_weak_signals, WeakSignal

# In-memory cache — replace with Redis for production
_snapshot_cache: Optional[DashboardSnapshot] = None
_cache_timestamp: Optional[datetime] = None
CACHE_TTL_MINUTES = 30


async def get_latest_snapshot(window_hours: int = 6) -> Optional[DashboardSnapshot]:
    global _snapshot_cache, _cache_timestamp

    if (
        _snapshot_cache is not None
        and _cache_timestamp is not None
        and (datetime.now(tz=timezone.utc) - _cache_timestamp).seconds < CACHE_TTL_MINUTES * 60
    ):
        return _snapshot_cache

    try:
        snapshot = await run_pipeline(window_hours)
        _snapshot_cache = snapshot
        _cache_timestamp = datetime.now(tz=timezone.utc)
        return snapshot
    except Exception as exc:
        logger.error(f"Pipeline run failed: {exc}")
        return _snapshot_cache  # return stale cache rather than nothing


async def run_pipeline(window_hours: int = 6) -> DashboardSnapshot:
    logger.info(f"Pipeline starting — window: {window_hours}h")
    raw_docs: list[dict] = []

    async def store(doc: dict):
        raw_docs.append(doc)

    # Ingest
    await run_full_ingestion(store)

    trends_map = fetch_sector_trends(timeframe=f"now {window_hours}-H")
    trend_docs = trends_to_documents(trends_map)
    raw_docs.extend(trend_docs)

    if not raw_docs:
        raise RuntimeError("No documents ingested")

    logger.info(f"Ingested {len(raw_docs)} documents total")

    # Extract text for NLP
    texts = [d.get("text", "") for d in raw_docs if d.get("text")]
    if len(texts) < 10:
        raise RuntimeError("Insufficient text documents for NLP")

    # Batch sentiment
    sentiments = analyse_batch(texts)

    # Entity extraction
    entity_map: dict[str, dict] = {}
    for doc, sentiment in zip(raw_docs, sentiments):
        text = doc.get("text", "")
        if not text or not sentiment:
            continue
        entities = extract_entities(text)
        reach = doc.get("estimated_reach", 1)
        geo = doc.get("geo", "unknown")

        for ent in entities:
            key = ent.canonical
            if key not in entity_map:
                entity_map[key] = {
                    "canonical_name": key,
                    "sectors": ent.sectors,
                    "mentions": [],
                    "reaches": [],
                    "sentiments": [],
                    "geo_dist": {},
                    "sources": set(),
                    "sample_texts": [],
                    "first_seen": doc.get("created_utc") or doc.get("ingested_at"),
                    "last_seen": doc.get("created_utc") or doc.get("ingested_at"),
                }
            em = entity_map[key]
            em["mentions"].append(doc.get("id", ""))
            em["reaches"].append(reach)
            em["sentiments"].append(sentiment)
            em["geo_dist"][geo] = em["geo_dist"].get(geo, 0) + 1
            em["sources"].add(doc.get("source", "unknown"))
            if len(em["sample_texts"]) < 3 and len(text) > 30:
                em["sample_texts"].append(text[:200])

    # Build EntitySignal objects and score them
    signals: list[EntitySignal] = []
    for key, em in entity_map.items():
        if not em["sentiments"]:
            continue
        agg = aggregate_entity_sentiment(em["sentiments"], em["reaches"])
        sig = EntitySignal(
            canonical_name=em["canonical_name"],
            sectors=em["sectors"],
            mention_count=len(em["mentions"]),
            total_reach=sum(em["reaches"]),
            geo_distribution=em["geo_dist"],
            sentiment_magnitude=agg["magnitude"],
            sentiment_direction=agg["direction"],
            sentiment_label=agg["label"],
            sentiment_plain_label=agg["plain_label"],
            sources=list(em["sources"]),
            sample_texts=em["sample_texts"],
            first_seen=em["first_seen"],
            last_seen=em["last_seen"],
        )
        signals.append(sig)

    ranked = rank_signals(signals, top_n=50)

    # Topic modelling
    topic_model, topic_assignments, _ = fit_topics(texts[:2000])  # cap for speed
    clusters = extract_topic_clusters(topic_model, texts[:2000], topic_assignments)

    # Weak signal pipeline — runs independently on broad (non-financial) ingestion
    broad_topics: list[dict] = []
    try:
        broad_topics = await run_broad_ingestion()
    except Exception as exc:
        logger.warning(f"Broad ingestion failed (non-fatal): {exc}")

    weak_signals_raw = detect_weak_signals(broad_topics) if broad_topics else []
    weak_signals_out = [_weak_signal_to_out(ws) for ws in weak_signals_raw[:20]]

    # Build outputs
    signals_out = [_signal_to_out(s) for s in ranked]
    clusters_out = [_cluster_to_out(c) for c in clusters[:15]]
    validation = _build_validation(raw_docs, signals_out, clusters_out, window_hours)
    sector_heatmap = _build_sector_heatmap(signals_out)
    keywords = _build_keyword_list(ranked)

    return DashboardSnapshot(
        generated_at=datetime.now(tz=timezone.utc).isoformat(),
        top_signals=signals_out,
        topic_clusters=clusters_out,
        validation=validation,
        trending_keywords=keywords,
        sector_heatmap=sector_heatmap,
        weak_signals=weak_signals_out,
    )


def _signal_to_out(s: EntitySignal) -> EntitySignalOut:
    return EntitySignalOut(
        canonical_name=s.canonical_name,
        sectors=s.sectors,
        mention_count=s.mention_count,
        total_reach=s.total_reach,
        composite_score=s.composite_score,
        frequency_score=s.frequency_score,
        geography_score=s.geography_score,
        sector_score=s.sector_score,
        credibility_score=s.credibility_score,
        sentiment_direction=s.sentiment_direction,
        sentiment_label=s.sentiment_label,
        sentiment_plain_label=s.sentiment_plain_label,
        sentiment_magnitude=s.sentiment_magnitude,
        signal_strength=s.signal_strength,
        confidence_tier=s.confidence_tier,
        plain_summary=s.plain_summary,
        sample_texts=s.sample_texts,
        sources=s.sources,
        first_seen=s.first_seen,
        last_seen=s.last_seen,
    )


def _weak_signal_to_out(ws: WeakSignal) -> WeakSignalOut:
    return WeakSignalOut(
        raw_topic=ws.raw_topic,
        normalised_topic=ws.normalised_topic,
        source=ws.source,
        mention_count=ws.mention_count,
        burst_score=ws.burst_score,
        top_entity=ws.top_entity,
        top_sector=ws.top_sector,
        top_causal_score=ws.top_causal_score,
        causal_chain_plain=ws.causal_chain_plain,
        hop_count=ws.hop_count,
        causal_paths=[
            CausalPathOut(
                hops=p.hops,
                market_entity=p.market_entity,
                affected_sector=p.affected_sector,
                causal_score=p.causal_score,
                relationship_chain=p.relationship_chain,
                plain_explanation=p.plain_explanation,
            )
            for p in ws.causal_paths
        ],
        confidence_tier=ws.confidence_tier,
        analyst_note=ws.analyst_note,
        detected_at=ws.detected_at,
        status=ws.status,
    )


def _cluster_to_out(c) -> TopicClusterOut:
    return TopicClusterOut(
        topic_id=c.topic_id,
        label=c.label,
        plain_label=c.plain_label,
        keywords=c.keywords,
        document_count=c.document_count,
        representative_docs=c.representative_docs,
        sectors=c.sectors,
        trend_velocity=c.trend_velocity,
    )


def _build_validation(
    raw_docs: list[dict],
    signals: list[EntitySignalOut],
    clusters: list[TopicClusterOut],
    window_hours: int,
) -> ValidationMetrics:
    now = datetime.now(tz=timezone.utc)
    source_breakdown: dict[str, int] = {}
    india_count = 0
    freshness_minutes = 9999

    for doc in raw_docs:
        src = doc.get("source", "unknown")
        source_breakdown[src] = source_breakdown.get(src, 0) + 1
        if doc.get("geo", "").startswith("IN"):
            india_count += 1
        ingested = doc.get("ingested_at")
        if ingested:
            try:
                dt = datetime.fromisoformat(ingested.replace("Z", "+00:00"))
                age = int((now - dt).total_seconds() / 60)
                freshness_minutes = min(freshness_minutes, age)
            except Exception:
                pass

    india_pct = round(india_count / max(len(raw_docs), 1) * 100, 1)
    total_docs = len(raw_docs)

    # Quality labels
    if total_docs >= 500 and len(set(source_breakdown)) >= 2:
        coverage = "Comprehensive"
        quality = "Strong"
    elif total_docs >= 150:
        coverage = "Partial"
        quality = "Moderate"
    else:
        coverage = "Limited"
        quality = "Weak"

    if freshness_minutes < 15:
        freshness = "Live (< 15 min old)"
    elif freshness_minutes < 60:
        freshness = f"Recent ({freshness_minutes} min old)"
    else:
        freshness = f"Stale ({freshness_minutes // 60}h old) — consider re-running pipeline"

    if india_pct >= 60:
        india_label = "Strongly India-focused (ideal for ET Now use)"
    elif india_pct >= 30:
        india_label = f"Partially India-focused ({india_pct}% India-origin signals)"
    else:
        india_label = f"Low India coverage ({india_pct}%) — geographic filters recommended"

    reliability = (
        f"This snapshot analysed {total_docs:,} posts and comments collected over the last {window_hours} hours. "
        f"{len(signals)} distinct market entities were detected with measurable sentiment, "
        f"grouped into {len(clusters)} narrative themes. "
        f"Data is {freshness_minutes} minutes old. "
        f"Overall signal quality is rated {quality.upper()} — "
        f"{'sufficient for directional inference' if quality != 'Weak' else 'treat as exploratory only'}. "
        f"India-origin signals account for {india_pct}% of the dataset."
    )

    return ValidationMetrics(
        window_label=f"Last {window_hours} hours",
        total_documents_processed=total_docs,
        total_entities_detected=len(signals),
        total_topics_found=len(clusters),
        data_freshness_minutes=freshness_minutes if freshness_minutes < 9999 else 0,
        source_breakdown=source_breakdown,
        india_mention_pct=india_pct,
        overall_signal_quality=quality,
        data_coverage_label=coverage,
        freshness_label=freshness,
        india_coverage_label=india_label,
        reliability_summary=reliability,
    )


def _build_sector_heatmap(signals: list[EntitySignalOut]) -> dict[str, dict]:
    heatmap: dict[str, dict] = {}
    for sig in signals:
        for sector in sig.sectors:
            if sector not in heatmap:
                heatmap[sector] = {"score": 0.0, "direction": 0, "mention_count": 0, "plain_label": ""}
            heatmap[sector]["score"] = max(heatmap[sector]["score"], sig.composite_score)
            heatmap[sector]["mention_count"] += sig.mention_count
            heatmap[sector]["direction"] += sig.sentiment_direction

    for sector, data in heatmap.items():
        d = data["direction"]
        data["plain_label"] = "Net Bullish" if d > 0 else ("Net Bearish" if d < 0 else "Mixed")

    return heatmap


def _build_keyword_list(signals: list[EntitySignal]) -> list[dict]:
    return [
        {
            "word": s.canonical_name,
            "weight": s.composite_score,
            "mention_count": s.mention_count,
            "sector": s.sectors[0] if s.sectors else "General",
            "sentiment": s.sentiment_plain_label,
            "direction": s.sentiment_direction,
            "signal_strength": s.signal_strength,
        }
        for s in signals
    ]
