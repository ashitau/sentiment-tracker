"""
FastAPI application — exposes the processed sentiment signals to the frontend.
"""
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Query, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from loguru import logger

from backend.db.models import DashboardSnapshot, EntitySignalOut, ValidationMetrics, WeakSignalOut
from backend.auth.magic_link import (
    is_allowed, generate_magic_token, verify_magic_token,
    generate_session_jwt, send_magic_link,
)
from backend.auth.middleware import require_auth

ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
    os.environ.get("FRONTEND_URL", "https://sentiment-tracker.vercel.app"),
]


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
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Auth routes (public — no token required) ──────────────────────────────────

class MagicLinkRequest(BaseModel):
    email: str  # validated against ALLOWED_EMAILS allowlist, not pydantic EmailStr


@app.post("/auth/request")
async def request_magic_link(body: MagicLinkRequest, request: Request):
    email = body.email.strip().lower()
    if not is_allowed(email):
        # Return 200 regardless — don't leak which emails are allowed
        return {"message": "If that address is registered, you'll receive a login link shortly."}

    token = generate_magic_token(email)
    base_url = os.environ.get("FRONTEND_URL", str(request.base_url).rstrip("/"))
    await send_magic_link(email, token, base_url)
    return {"message": "If that address is registered, you'll receive a login link shortly."}


@app.get("/auth/verify")
async def verify_magic_link(token: str = Query(...)):
    email = verify_magic_token(token)
    if not email:
        raise HTTPException(status_code=401, detail="This login link is invalid or has expired. Please request a new one.")
    if not is_allowed(email):
        raise HTTPException(status_code=403, detail="This email is not authorised to access the tracker.")

    session = generate_session_jwt(email)
    return {"session_token": session, "email": email}


@app.get("/auth/me")
async def get_me(email: str = Depends(require_auth)):
    return {"email": email, "authenticated": True}


# ── Public ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now(tz=timezone.utc).isoformat()}


# ── Protected data routes ─────────────────────────────────────────────────────

@app.get("/api/dashboard", response_model=DashboardSnapshot)
async def get_dashboard(
    window_hours: int = Query(default=6, ge=1, le=48),
    _email: str = Depends(require_auth),
):
    from backend.api.routes.pipeline import get_latest_snapshot
    snapshot = await get_latest_snapshot(window_hours)
    if snapshot is None:
        raise HTTPException(status_code=503, detail="Pipeline warming up — check back in 2 minutes.")
    return snapshot


@app.get("/api/signals", response_model=list[EntitySignalOut])
async def get_signals(
    window_hours: int = Query(default=6, ge=1, le=48),
    sector: str = Query(default=None),
    min_score: float = Query(default=0.0, ge=0.0, le=1.0),
    limit: int = Query(default=50, ge=1, le=200),
    _email: str = Depends(require_auth),
):
    from backend.api.routes.pipeline import get_latest_snapshot
    snapshot = await get_latest_snapshot(window_hours)
    if snapshot is None:
        return []
    signals = snapshot.top_signals
    if sector:
        signals = [s for s in signals if sector in s.sectors]
    return [s for s in signals if s.composite_score >= min_score][:limit]


@app.get("/api/validation", response_model=ValidationMetrics)
async def get_validation(
    window_hours: int = Query(default=6),
    _email: str = Depends(require_auth),
):
    from backend.api.routes.pipeline import get_latest_snapshot
    snapshot = await get_latest_snapshot(window_hours)
    if snapshot is None:
        raise HTTPException(status_code=503, detail="No data available")
    return snapshot.validation


@app.get("/api/sectors")
async def get_sector_heatmap(
    window_hours: int = Query(default=6),
    _email: str = Depends(require_auth),
):
    from backend.api.routes.pipeline import get_latest_snapshot
    snapshot = await get_latest_snapshot(window_hours)
    return snapshot.sector_heatmap if snapshot else {}


@app.get("/api/weak-signals", response_model=list[WeakSignalOut])
async def get_weak_signals(
    window_hours: int = Query(default=6),
    min_causal_score: float = Query(default=0.35),
    sector: str = Query(default=None),
    _email: str = Depends(require_auth),
):
    from backend.api.routes.pipeline import get_latest_snapshot
    snapshot = await get_latest_snapshot(window_hours)
    if snapshot is None:
        return []
    signals = snapshot.weak_signals
    if sector:
        signals = [s for s in signals if s.top_sector == sector]
    return [s for s in signals if s.top_causal_score >= min_causal_score]


@app.get("/api/keywords")
async def get_keywords(
    window_hours: int = Query(default=6),
    limit: int = Query(default=100),
    _email: str = Depends(require_auth),
):
    from backend.api.routes.pipeline import get_latest_snapshot
    snapshot = await get_latest_snapshot(window_hours)
    return snapshot.trending_keywords[:limit] if snapshot else []
