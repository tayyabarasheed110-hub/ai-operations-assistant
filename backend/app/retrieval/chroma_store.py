import hashlib
import os
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import get_settings

_embedder: Any | None = None
_client: chromadb.ClientAPI | None = None
_COLLECTION = "policy_chunks"


def _test_embedding(text: str, dim: int = 384) -> list[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    vals = [digest[i % len(digest)] / 255.0 for i in range(dim)]
    norm = sum(v * v for v in vals) ** 0.5 or 1.0
    return [v / norm for v in vals]


def _get_embedder() -> Any:
    global _embedder
    if _embedder is None:
        settings = get_settings()
        if os.getenv("EMBEDDING_MODE") == "test":
            _embedder = "test"
        else:
            from sentence_transformers import SentenceTransformer

            # Token only needed for gated HF models; local model ignores it.
            _embedder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
            _ = settings.huggingfacehub_api_token
    return _embedder


def _get_client() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        path = Path(get_settings().chroma_path)
        path.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(
            path=str(path),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _client


def _collection():
    return _get_client().get_or_create_collection(name=_COLLECTION, metadata={"hnsw:space": "cosine"})


def embed_texts(texts: list[str]) -> list[list[float]]:
    model = _get_embedder()
    if model == "test":
        return [_test_embedding(t) for t in texts]
    return model.encode(texts, normalize_embeddings=True).tolist()


def upsert_chunks(
    *,
    chroma_ids: list[str],
    documents: list[str],
    metadatas: list[dict[str, Any]],
) -> None:
    col = _collection()
    embeddings = embed_texts(documents)
    col.upsert(ids=chroma_ids, documents=documents, embeddings=embeddings, metadatas=metadatas)


def delete_chunks(chroma_ids: list[str]) -> None:
    if not chroma_ids:
        return
    col = _collection()
    col.delete(ids=chroma_ids)


def query_policy(query: str, n_results: int = 5) -> list[dict[str, Any]]:
    col = _collection()
    if col.count() == 0:
        return []
    embedding = embed_texts([query])[0]
    result = col.query(query_embeddings=[embedding], n_results=min(n_results, col.count()))
    out: list[dict[str, Any]] = []
    ids = result.get("ids") or [[]]
    docs = result.get("documents") or [[]]
    metas = result.get("metadatas") or [[]]
    dists = result.get("distances") or [[]]
    for i, doc_id in enumerate(ids[0]):
        out.append(
            {
                "chroma_id": doc_id,
                "content": docs[0][i],
                "metadata": metas[0][i] or {},
                "distance": dists[0][i] if dists else None,
            }
        )
    return out
