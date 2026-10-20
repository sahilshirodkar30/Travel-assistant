
import argparse,collections,datetime , time
from app.rag.loaders import iter_chunks

TTL_DAYS = {"transport": 14, "events": 14, "stay": 30, "faq": 60, "activities": 60, "food": 90,
            "places": 120, "guides": 120, "safety": 180, "policy": 180, "general": 30}
BATCH = 100

def run (root:str="data/knowledge",verified_on:str|None=None,dry_run:bool=False):
    day = datetime.date.fromisoformat(verified_on) if verified_on else datetime.date.today()
    update_at = int(time.mktime(day.timetuple()))
    chunks = list(iter_chunks(root))

    for c in chunks:
        ttl = TTL_DAYS.get(c["metadata"]["category"],30)
        c["metadata"].updated(update_at=update_at,valid_until=update_at+ttl*86400)

    stats = collections.Counter((c["metadata"]["category"],c["metadata"]["format"]) for c in chunks)
    for (cat,fmt),n in sorted(stats.items()):
        print(f"{cat:<11}{fmt:6}{n:>5} chunks")

    print(f"total {len(chunks)} chunks (verified {day})")

    if dry_run:
        return chunks

    from app.rag.pinecone_store import ensure_index,get_store
    ensure_index()
    store = get_store("Knowlegde")
    for i in range(0,len(chunks),BATCH):
        b = chunks[i:i+BATCH]
        store.add_texts([c["text"] for c in b],metadatas=[c["metadata"] for c in b],ids=[c["id"] for c in b])
        print(f"upserted {i+len(b)}/{len(chunks)}")

    return chunks

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root",default="data/knowledge")
    ap.add_argument("--verified_on")
    ap.add_argument("--dry_run",action="store_true",help="parse + count only, no Pinecone calls")
    a = ap.parse_args()
    run(a.root,a.verified_on,a.dry_run)