"""Human-in-the-loop queue (Redis). Ops staff list pending approvals and approve/reject;
the decision resumes the paused LangGraph thread."""
import json, time, uuid
import redis.asyncio as aioredis
from app.config import get_settings

_r = aioredis.from_url(get_settings().redis_url, decode_responses=True)
KEY = "approvals"


async def enqueue(thread_id: str, customer_id: str, action: dict) -> str:
    aid = uuid.uuid4().hex[:10]
    await _r.hset(KEY, aid, json.dumps({"id": aid, "thread_id": thread_id, "customer_id": customer_id,
                                        "action": action, "created": time.time(), "status": "pending"}))
    return aid


async def list_pending() -> list[dict]:
    items = [json.loads(v) for v in (await _r.hvals(KEY))]
    return [i for i in items if i["status"] == "pending"]


async def pop(aid: str) -> dict | None:
    raw = await _r.hget(KEY, aid)
    if not raw:
        return None
    await _r.hdel(KEY, aid)
    return json.loads(raw)
