"""
Aspect-Based Sentiment Analysis for financial text.
Uses FinBERT for document-level sentiment.
Falls back to a keyword heuristic when transformers/torch are not installed
(e.g. on Railway where NLP deps are not in requirements.txt).
"""
from dataclasses import dataclass
from typing import Optional
from loguru import logger

try:
    import torch
    from transformers import pipeline as hf_pipeline
    _TRANSFORMERS_AVAILABLE = True
except ImportError:
    _TRANSFORMERS_AVAILABLE = False
    logger.warning("transformers/torch not installed — using keyword-heuristic sentiment fallback")

FINBERT_MODEL = "ProsusAI/finbert"
MAX_LENGTH = 512

_finbert_pipeline = None

# Simple keyword fallback when transformers not installed
_BULLISH_WORDS = {"buy", "bull", "rally", "surge", "beat", "profit", "growth", "positive", "strong", "gain", "up", "rise"}
_BEARISH_WORDS = {"sell", "bear", "fall", "drop", "miss", "loss", "weak", "negative", "crash", "down", "decline", "cut"}


def _get_finbert():
    if not _TRANSFORMERS_AVAILABLE:
        return None
    global _finbert_pipeline
    if _finbert_pipeline is None:
        device = 0 if torch.cuda.is_available() else -1
        logger.info(f"Loading FinBERT on {'GPU' if device == 0 else 'CPU'}")
        _finbert_pipeline = hf_pipeline(
            "text-classification",
            model=FINBERT_MODEL,
            tokenizer=FINBERT_MODEL,
            device=device,
            max_length=MAX_LENGTH,
            truncation=True,
        )
    return _finbert_pipeline


def _keyword_sentiment(text: str) -> "SentimentResult":
    words = set(text.lower().split())
    bull = len(words & _BULLISH_WORDS)
    bear = len(words & _BEARISH_WORDS)
    if bull > bear:
        return _build_result("positive", 0.65)
    if bear > bull:
        return _build_result("negative", 0.65)
    return _build_result("neutral", 0.50)


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
    pipe = _get_finbert()
    if pipe is None:
        return _keyword_sentiment(text)
    try:
        result = pipe(text[:MAX_LENGTH])[0]
        return _build_result(result["label"].lower(), result["score"])
    except Exception as exc:
        logger.warning(f"FinBERT inference failed: {exc}")
        return _keyword_sentiment(text)


def analyse_batch(texts: list[str], batch_size: int = 32) -> list[Optional[SentimentResult]]:
    if not texts:
        return []
    pipe = _get_finbert()
    if pipe is None:
        return [_keyword_sentiment(t) for t in texts]
    try:
        truncated = [t[:MAX_LENGTH] for t in texts]
        raw_results = pipe(truncated, batch_size=batch_size)
        return [_build_result(r["label"].lower(), r["score"]) for r in raw_results]
    except Exception as exc:
        logger.error(f"Batch sentiment failed, falling back to keyword heuristic: {exc}")
        return [_keyword_sentiment(t) for t in texts]


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
