"""Auth: users sign in with Google, then the app issues its own short-lived JWT."""
import hashlib, time
from dataclasses import dataclass
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests
from app.config import get_settings

bearer = HTTPBearer(auto_error=False)


@dataclass
class User:
    email: str
    customer_id: str
    role: str  # "user" or "ops"


def customer_id_for(email: str) -> str:
    digest = hashlib.sha256(email.strip().lower().encode()).hexdigest()
    return f"cus_{digest[:12]}"


def verify_google_login(google_token: str) -> str:
    """Check the Google ID token and return the verified email."""
    try:
        info = google_id_token.verify_oauth2_token(
            google_token, google_requests.Request(), get_settings().google_client_id)
    except ValueError:
        raise HTTPException(status_code=401, detail="Google sign-in failed")
    if not info.get("email_verified"):
        raise HTTPException(status_code=401, detail="Email not verified")
    return info["email"]


def create_token(email: str) -> str:
    s = get_settings()
    email = email.strip().lower()
    ops = {e.strip().lower() for e in s.ops_emails.split(",") if e.strip()}
    payload = {
        "sub": email,
        "cid": customer_id_for(email),
        "role": "ops" if email in ops else "user",
        "exp": int(time.time()) + s.jwt_ttl_minutes * 60,
    }
    return jwt.encode(payload, s.jwt_secret, algorithm="HS256")


def current_user(cred: HTTPAuthorizationCredentials | None = Depends(bearer)) -> User:
    if not cred:
        raise HTTPException(status_code=401, detail="Missing token")
    try:
        p = jwt.decode(cred.credentials, get_settings().jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return User(email=p["sub"], customer_id=p["cid"], role=p["role"])


def require_ops(user: User = Depends(current_user)) -> User:
    if user.role != "ops":
        raise HTTPException(status_code=403, detail="Ops role required")
    return user