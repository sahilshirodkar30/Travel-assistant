"""Per-user and per-IP rate limiting (Redis fixed window; in-memory fallback if Redis is down)."""
import time
from collections import defaultdict
import redis.asyncio as aioredis
from fastapi import Depends, HTTPException, Request
from app.auth.security import User, current_user
from app.config import get_settings

_s = get_settings()
_r = aioredis.from_url(_s.redis_url, decode_responses=True)
_local: dict[str, int] = defaultdict(int)


async def hit(key: str, limit: int, window_s: int = 60) -> bool:
    """Returns True if the call is allowed."""
    bucket = f"rl:{key}:{int(time.time() // window_s)}"
    try:
        n = await _r.incr(bucket)
        if n == 1:
            await _r.expire(bucket, window_s + 5)
    except Exception:  # fault tolerance: never take the API down because Redis is down
        _local[bucket] += 1
        n = _local[bucket]
    return n <= limit


async def rate_limit_user(user: User = Depends(current_user)):
    if not await hit(f"u:{user.customer_id}", _s.rate_limit_per_min):
        raise HTTPException(429, "Too many requests", headers={"Retry-After": "30"})


async def rate_limit_ip(request: Request):
    ip = request.client.host if request.client else "unknown"
    if not await hit(f"ip:{ip}", _s.ip_rate_limit_per_min):
        raise HTTPException(429, "Too many requests", headers={"Retry-After": "30"})
