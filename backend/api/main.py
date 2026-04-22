"""
FastAPI application — exposes the processed sentiment signals to the frontend.
"""
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from backend.db.models import DashboardSnapshot, EntitySignalOut, ValidationMetrics


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Sentiment Tracker API starting up")
    yield
    logger.info("Sentiment Tracker API shutting down")


app = FastAPI(
    title="ET Now Sentiment Tracker API",
    version="0.1.0",
    description="Real-time social sentiment signals for Indian equity markets",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now(tz=timezone.utc).isoformat()}


@app.get("/api/dashboard", response_model=DashboardSnapshot)
async def get_dashboard(
    window_hours: int = Query(default=6, ge=1, le=48, description="Look-back window in hours"),
):
    """
    Primary endpoint consumed by the frontend dashboard.
    Returns a full snapshot: top signals, topics, validation metrics, heatmap.
    """
    from backend.api.routes.pipeline import get_latest_snapshot
    snapshot = await get_latest_snapshot(window_hours)
    if snapshot is None:
        raise HTTPException(status_code=503, detail="No processed data available yet. Pipeline may still be warming up.")
    return snapshot


@app.get("/api/signals", response_model=list[EntitySignalOut])
async def get_signals(
    window_hours: int = Query(default=6, ge=1, le=48),
    sector: str = Query(default=None),
    min_score: float = Query(default=0.0, ge=0.0, le=1.0),
    limit: int = Query(default=50, ge=1, le=200),
):
    """Top-ranked entity signals, optionally filtered by sector and minimum composite score."""
    from backend.api.routes.pipeline import get_latest_snapshot
    snapshot = await get_latest_snapshot(window_hours)
    if snapshot is None:
        return []

    signals = snapshot.top_signals
    if sector:
        signals = [s for s in signals if sector in s.sectors]
    signals = [s for s in signals if s.composite_score >= min_score]
    return signals[:limit]


@app.get("/api/validation", response_model=ValidationMetrics)
async def get_validation(window_hours: int = Query(default=6)):
    """
    Validation metrics — includes both technical stats and plain-English
    summaries suitable for non-technical stakeholder review.
    """
    from backend.api.routes.pipeline import get_latest_snapshot
    snapshot = await get_latest_snapshot(window_hours)
    if snapshot is None:
        raise HTTPException(status_code=503, detail="No data available")
    return snapshot.validation


@app.get("/api/sectors")
async def get_sector_heatmap(window_hours: int = Query(default=6)):
    """Sector-level sentiment heatmap data."""
    from backend.api.routes.pipeline import get_latest_snapshot
    snapshot = await get_latest_snapshot(window_hours)
    if snapshot is None:
        return {}
    return snapshot.sector_heatmap


@app.get("/api/keywords")
async def get_keywords(
    window_hours: int = Query(default=6),
    limit: int = Query(default=100),
):
    """Weighted keyword list for constellation map rendering."""
    from backend.api.routes.pipeline import get_latest_snapshot
    snapshot = await get_latest_snapshot(window_hours)
    if snapshot is None:
        return []
    return snapshot.trending_keywords[:limit]
