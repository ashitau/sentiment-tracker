"""
FastAPI auth dependency — validates session JWT on every protected route.
"""
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from backend.auth.magic_link import verify_session_jwt

bearer = HTTPBearer(auto_error=False)


def require_auth(credentials: HTTPAuthorizationCredentials = Security(bearer)) -> str:
    """Dependency: returns the authenticated email or raises 401."""
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    email = verify_session_jwt(credentials.credentials)
    if not email:
        raise HTTPException(status_code=401, detail="Session expired or invalid — request a new login link")
    return email
