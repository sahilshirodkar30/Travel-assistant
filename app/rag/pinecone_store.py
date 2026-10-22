

from functools import lru_cache
from pinecone import Pinecone,ServerlessSpec
from langchain_pinecone import PineconeEmbeddings,PineconeSparseVectorStore
from app.config import get_settings

@lru_cache
def _pc() -> Pinecone:
    return Pinecone(api_key=get_settings().pinecone_api_key)


def ensure_index():
    s = get_settings()
    pc = _pc()
    if s.pinecone_index not in pc.list_indexes().names():
        pc.create_index(s.pinecone_index,dimension=1024,metric="cosine",spec=ServerlessSpec(cloud="aws",region="us-east-1"))


@lru_cache
def get_store(namespace:str)->PineconeSparseVectorStore:
    s = get_settings()
    emb = PineconeEmbeddings(model = s.embedding_model_name,pinecone_api_key=s.pinecone_api_key)
    return PineconeSparseVectorStore(index=_pc().Index(s.pinecone_index),embedding=emb,namespace=namespace)
