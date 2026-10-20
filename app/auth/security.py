""" Authentication + authorization 
user log in with gmail account and get access to the app"""


import hashlib , time 
from dataclasses import dataclass
import jwt
from fastapi import Depends,HTTPException
from fastapi.security import HTTPAuthorizationCredentials , HTTPBearer
from app.config import get_settings

bearer = HTTPBearer(auto_error=False)

@dataclass
class User:
    email:str
    customer_id:str
    role:str #"user" |"admin"


def customer_id_for(email:str)->str:
    return "cus_" + hashlib.sha256(email.lower().encode().hexdigest())[:12]


def create_token(email:str)->str:
    s = get_settings()
    role = "ops" if email.lower() in {e.strip().lower() for e in s.ops_emails.split(",") if e} else "user"
    payload = {
        "sub":email.lower(),"cid":customer_id_for(email),"role":role,
        "exp": int(time.time() + s.jwt_ttl_minutes*60)
    }
    return jwt.encode(payload,s.jwt_secret,algorithm="HS256")

def current_user(cred:HTTPAuthorizationCredentials|None=Depends(bearer))->User:
    if not cred:
        raise HTTPException(status_code=401,detail="Missing token")

    try:
        p = jwt.decode(cred.credentials,get_settings().jwt_secret,algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401,detail="Invalid token or expired token")

    return User(email=p["sub"],customer_id=p["cid"],role=p["role"])

def require_ops(user:User=Depends(current_user))->User:
    if user.role != "ops":
        raise HTTPException(status_code=403,detail="Ops role required")
    return user
