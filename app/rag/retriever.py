
import time
from datetime import datetime
from app.rag.pinecone_store import get_store

async def retriever(query:str,k=4) -> list[str]:
    store = get_store("Knowleage")
    docs = await store.asimilarity_search(query=query,k=k,filter={"valid_until": {"$gt": int(time.time())}})
    out = []
    for d in docs:
        ts = datetime.fromtimestamp(d.metadata.get("updated_at",0)).strftime("%d %b %Y")
        out.append(f"{d.page_content} (soure: {d.metadata.get('source')}, last verified {ts})")

    return out