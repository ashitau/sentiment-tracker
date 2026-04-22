"""
Magic-link authentication.

Flow:
  1. POST /auth/request  { email }
     → validates email is on the allowlist
     → generates a signed, time-limited token
     → sends an email with a login link
  2. GET  /auth/verify?token=...
     → validates token (signature + expiry)
     → returns a session JWT the frontend stores in localStorage

No passwords. No OAuth setup. Just add emails to ALLOWED_EMAILS in .env.
"""
import os
import hmac
import hashlib
import time
import base64
import json
from typing import Optional
import httpx
from loguru import logger

TOKEN_TTL_SECONDS = 900       # magic link expires after 15 minutes
SESSION_TTL_SECONDS = 8 * 3600  # session JWT valid for 8 hours
SECRET_KEY = os.environ.get("AUTH_SECRET_KEY", "change-me-in-production")


def get_allowed_emails() -> set[str]:
    raw = os.environ.get("ALLOWED_EMAILS", "")
    return {e.strip().lower() for e in raw.split(",") if e.strip()}


def is_allowed(email: str) -> bool:
    return email.strip().lower() in get_allowed_emails()


# ── Token helpers ─────────────────────────────────────────────────────────────

def _sign(payload: str) -> str:
    return hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()


def generate_magic_token(email: str) -> str:
    """Return a URL-safe signed token encoding {email, issued_at}."""
    payload = json.dumps({"email": email, "iat": int(time.time())})
    b64 = base64.urlsafe_b64encode(payload.encode()).decode()
    sig = _sign(b64)
    return f"{b64}.{sig}"


def verify_magic_token(token: str) -> Optional[str]:
    """
    Validate token signature and expiry.
    Returns the email if valid, None otherwise.
    """
    try:
        b64, sig = token.rsplit(".", 1)
    except ValueError:
        return None

    if not hmac.compare_digest(_sign(b64), sig):
        logger.warning("Magic link: invalid signature")
        return None

    try:
        payload = json.loads(base64.urlsafe_b64decode(b64 + "=="))
    except Exception:
        return None

    age = int(time.time()) - payload.get("iat", 0)
    if age > TOKEN_TTL_SECONDS:
        logger.info(f"Magic link expired ({age}s old)")
        return None

    return payload.get("email")


def generate_session_jwt(email: str) -> str:
    """Minimal signed session token (not full JWT — avoids PyJWT dependency)."""
    payload = json.dumps({"email": email, "exp": int(time.time()) + SESSION_TTL_SECONDS})
    b64 = base64.urlsafe_b64encode(payload.encode()).decode()
    sig = _sign(b64)
    return f"{b64}.{sig}"


def verify_session_jwt(token: str) -> Optional[str]:
    """Returns email if session token is valid and not expired, else None."""
    try:
        b64, sig = token.rsplit(".", 1)
    except ValueError:
        return None

    if not hmac.compare_digest(_sign(b64), sig):
        return None

    try:
        payload = json.loads(base64.urlsafe_b64decode(b64 + "=="))
    except Exception:
        return None

    if int(time.time()) > payload.get("exp", 0):
        return None

    return payload.get("email")


# ── Email sending (Brevo SMTP API — free tier, single-sender verification) ────

async def send_magic_link(email: str, token: str, base_url: str) -> bool:
    """
    Send a magic link email via Brevo API.
    Set BREVO_API_KEY and BREVO_FROM_EMAIL in env.
    Falls back to console-logging in dev (no API key set).
    """
    link = f"{base_url}/auth/verify?token={token}"
    api_key = os.environ.get("BREVO_API_KEY")
    from_email = os.environ.get("BREVO_FROM_EMAIL", "")

    if not api_key or not from_email or os.environ.get("APP_ENV") == "development":
        logger.info(f"[DEV] Magic link for {email}: {link}")
        return True

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.brevo.com/v3/smtp/email",
                headers={"api-key": api_key, "Content-Type": "application/json"},
                json={
                    "sender": {"name": "ET Now Sentiment Tracker", "email": from_email},
                    "to": [{"email": email}],
                    "subject": "Your login link — ET Now Sentiment Tracker",
                    "htmlContent": _email_html(link),
                },
                timeout=10,
            )
            if resp.status_code >= 400:
                logger.error(f"Brevo API {resp.status_code}: {resp.text}")
                return False
            logger.info(f"Magic link sent to {email}")
            return True
    except Exception as exc:
        logger.error(f"Failed to send magic link to {email}: {exc}")
        return False


def _email_html(link: str) -> str:
    return f"""
    <div style="font-family:Inter,sans-serif;max-width:480px;margin:0 auto;padding:40px 24px;background:#0a0e1a;color:#f3f4f6;border-radius:12px;">
      <h2 style="color:#3b82f6;margin-bottom:8px;">ET Now Sentiment Tracker</h2>
      <p style="color:#9ca3af;margin-bottom:32px;">Click the button below to log in. This link expires in 15 minutes.</p>
      <a href="{link}" style="display:inline-block;padding:14px 28px;background:#3b82f6;color:white;border-radius:8px;text-decoration:none;font-weight:600;">
        Log in to Tracker
      </a>
      <p style="color:#4b5563;font-size:12px;margin-top:32px;">
        If you didn't request this, ignore this email. The link can only be used once.
      </p>
    </div>
    """
