"""Semantic cache in Pinecone (namespace 'cache'). ONLY for public, non-personal questions
(e.g. 'best beaches in North Goa'). Personal/booking questions are never cached."""
import re, time, uuid
from app.config import get_settings
from app.rag.pinecone_store import get_store

CACHEABLE_INTENTS = {"place_info"}
PERSONAL = re.compile(r"#\d+|\b(my|mine|i booked|our)\b|\[(EMAIL|PHONE|CARD|AADHAAR|PASSPORT)\]", re.I)


def is_cacheable(text: str) -> bool:
    return not PERSONAL.search(text)


async def lookup(query: str) -> str | None:
    s = get_settings()
    try:
        res = await get_store("cache").asimilarity_search_with_score(
            query, k=1, filter={"expires_at": {"$gt": int(time.time())}})
    except Exception:
        return None  # cache failure must never break the request
    if res and res[0][1] >= s.cache_threshold:
        return res[0][0].metadata.get("answer")
    return None


async def store(query: str, answer: str):
    s = get_settings()
    try:
        await get_store("cache").aadd_texts(
            [query], metadatas=[{"answer": answer, "expires_at": int(time.time()) + s.cache_ttl_hours * 3600}],
            ids=[str(uuid.uuid4())])
    except Exception:
        pass
