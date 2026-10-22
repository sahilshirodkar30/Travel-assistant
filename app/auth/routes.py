"""Login endpoints. Two ways to get an API token:
 1) /auth/google    - client sends a Google ID token (verified against Google certs)
 2) /auth/exchange  - trusted Streamlit server (st.login already verified Gmail) + shared secret"""
import hmac
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from google.oauth2 import id_token
from google.auth.transport import requests as g_requests
from app.auth.security import create_token
from app.config import get_settings

router = APIRouter(prefix="/auth", tags=["auth"])


class GoogleIn(BaseModel):
    id_token: str


class ExchangeIn(BaseModel):
    email: str
    email_verified: bool
    internal_key: str


@router.post("/google")
def google_login(body: GoogleIn):
    s = get_settings()
    try:
        claims = id_token.verify_oauth2_token(body.id_token, g_requests.Request(), s.google_client_id)
    except ValueError:
        raise HTTPException(401, "Invalid Google token")
    if not claims.get("email_verified"):
        raise HTTPException(401, "Email not verified")
    return {"access_token": create_token(claims["email"])}


@router.post("/exchange")
def exchange(body: ExchangeIn):
    s = get_settings()
    if not hmac.compare_digest(body.internal_key, s.internal_service_key) or not body.email_verified:
        raise HTTPException(401, "Rejected")
    return {"access_token": create_token(body.email)}
