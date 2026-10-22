"""Traffic-spike protection: cap concurrent in-flight chats per instance, shed the rest fast (503)."""
import asyncio
from contextlib import asynccontextmanager
from fastapi import HTTPException
from app.config import get_settings

_sem = asyncio.Semaphore(get_settings().max_concurrent_requests)


@asynccontextmanager
async def admit():
    if _sem.locked():
        raise HTTPException(503, "Busy, please retry", headers={"Retry-After": "5"})
    async with _sem:
        yield
