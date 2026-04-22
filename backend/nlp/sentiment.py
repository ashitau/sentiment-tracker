"""
Aspect-Based Sentiment Analysis for financial text.
Uses FinBERT for document-level and PyABSA for entity-level sentiment.
Falls back gracefully if GPU is unavailable.
"""
from dataclasses import dataclass
from typing import Optional
import torch
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
from loguru import logger

FINBERT_MODEL = "ProsusAI/finbert"
MAX_LENGTH = 512

_finbert_pipeline = None


def _get_finbert():
    global _finbert_pipeline
    if _finbert_pipeline is None:
        device = 0 if torch.cuda.is_available() else -1
        logger.info(f"Loading FinBERT on {'GPU' if device == 0 else 'CPU'}")
        _finbert_pipeline = pipeline(
            "text-classification",
            model=FINBERT_MODEL,
            tokenizer=FINBERT_MODEL,
            device=device,
            max_length=MAX_LENGTH,
            truncation=True,
        )
    return _finbert_pipeline


@dataclass
class SentimentResult:
    label: str           # "positive" | "negative" | "neutral"
    score: float         # model confidence 0-1
    magnitude: float     # how strong (score distance from 0.5, scaled to 0-1)
    direction: int       # +1, -1, or 0
    plain_label: str     # human-readable: "Bullish", "Bearish", "Mixed/Neutral"


def analyse_document(text: str) -> Optional[SentimentResult]:
    if not text or len(text.strip()) < 10:
        return None
    try:
        pipe = _get_finbert()
        result = pipe(text[:MAX_LENGTH])[0]
        return _build_result(result["label"].lower(), result["score"])
    except Exception as exc:
        logger.warning(f"FinBERT inference failed: {exc}")
        return None


def analyse_batch(texts: list[str], batch_size: int = 32) -> list[Optional[SentimentResult]]:
    if not texts:
        return []
    try:
        pipe = _get_finbert()
        truncated = [t[:MAX_LENGTH] for t in texts]
        raw_results = pipe(truncated, batch_size=batch_size)
        return [_build_result(r["label"].lower(), r["score"]) for r in raw_results]
    except Exception as exc:
        logger.error(f"Batch sentiment failed: {exc}")
        return [None] * len(texts)


def _build_result(label: str, score: float) -> SentimentResult:
    direction_map = {"positive": 1, "negative": -1, "neutral": 0}
    plain_map = {
        "positive": "Bullish",
        "negative": "Bearish",
        "neutral": "Mixed / Neutral",
    }
    direction = direction_map.get(label, 0)
    # Magnitude = how far from neutral confidence (0.33 baseline for 3-class)
    magnitude = round(abs(score - 0.33) / 0.67, 3)

    return SentimentResult(
        label=label,
        score=round(score, 4),
        magnitude=magnitude,
        direction=direction,
        plain_label=plain_map.get(label, "Mixed / Neutral"),
    )


def aggregate_entity_sentiment(
    sentiments: list[SentimentResult],
    reach_weights: list[float],
) -> dict:
    """
    Weighted aggregate sentiment for one entity across multiple posts.
    reach_weights should be normalised estimated_reach values.
    """
    if not sentiments:
        return {"label": "neutral", "score": 0.5, "magnitude": 0.0, "direction": 0, "plain_label": "Mixed / Neutral", "sample_count": 0}

    total_weight = sum(reach_weights) or 1.0
    weighted_direction = sum(
        s.direction * s.magnitude * w
        for s, w in zip(sentiments, reach_weights)
    ) / total_weight

    if weighted_direction > 0.15:
        label, plain = "positive", "Bullish"
    elif weighted_direction < -0.15:
        label, plain = "negative", "Bearish"
    else:
        label, plain = "neutral", "Mixed / Neutral"

    return {
        "label": label,
        "plain_label": plain,
        "weighted_direction": round(weighted_direction, 4),
        "magnitude": round(abs(weighted_direction), 4),
        "direction": 1 if weighted_direction > 0 else (-1 if weighted_direction < 0 else 0),
        "sample_count": len(sentiments),
    }
