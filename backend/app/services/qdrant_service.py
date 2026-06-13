"""
Semantic Codebase Memory
Stores: code chunks, architecture docs, previous PR summaries,
        coding standards, team conventions.
Collections are namespaced so different memory types can be queried separately.
"""
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
    Filter, FieldCondition, MatchValue,
)
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Optional
import uuid
import asyncio
from concurrent.futures import ThreadPoolExecutor
from app.core.config import settings

VECTOR_SIZE = 384      # all-MiniLM-L6-v2
CHUNK_SIZE = 512


class QdrantService:
    """Manages vector embeddings for full semantic codebase memory."""

    def __init__(self):
        self.client = QdrantClient(url=settings.qdrant_url)
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.executor = ThreadPoolExecutor(max_workers=4)
        self._ensure_collection(settings.qdrant_collection)

    def _ensure_collection(self, name: str):
        existing = [c.name for c in self.client.get_collections().collections]
        if name not in existing:
            self.client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
            )

    def _embed(self, text: str) -> List[float]:
        return self.model.encode(text, normalize_embeddings=True).tolist()

    def _chunk_code(self, content: str, file_path: str) -> List[Dict]:
        chunks, current, current_size = [], [], 0
        lines = content.split("\n")
        for i, line in enumerate(lines):
            current.append(line)
            current_size += len(line)
            if current_size >= CHUNK_SIZE:
                chunks.append({
                    "content": "\n".join(current),
                    "file_path": file_path,
                    "start_line": i - len(current) + 1,
                    "end_line": i,
                })
                overlap = max(1, len(current) // 5)
                current = current[-overlap:]
                current_size = sum(len(l) for l in current)
        if current:
            chunks.append({
                "content": "\n".join(current),
                "file_path": file_path,
                "start_line": len(lines) - len(current),
                "end_line": len(lines) - 1,
            })
        return chunks

    # ── Code file indexing ────────────────────────────────────────────────────
    def index_repository(self, repo_id: int, files: List[Dict]) -> int:
        self.client.delete(
            collection_name=settings.qdrant_collection,
            points_selector=Filter(must=[
                FieldCondition(key="repo_id", match=MatchValue(value=repo_id)),
                FieldCondition(key="memory_type", match=MatchValue(value="code")),
            ]),
        )
        points, total = [], 0
        for file_info in files:
            content = file_info.get("content", "")
            file_path = file_info.get("path", "")
            if not content or len(content) < 20:
                continue
            for chunk in self._chunk_code(content, file_path):
                points.append(PointStruct(
                    id=str(uuid.uuid4()),
                    vector=self._embed(chunk["content"]),
                    payload={
                        "repo_id": repo_id,
                        "memory_type": "code",
                        "file_path": chunk["file_path"],
                        "content": chunk["content"],
                        "start_line": chunk["start_line"],
                        "end_line": chunk["end_line"],
                    },
                ))
                total += 1
                if len(points) >= 100:
                    self.client.upsert(collection_name=settings.qdrant_collection, points=points)
                    points = []
        if points:
            self.client.upsert(collection_name=settings.qdrant_collection, points=points)
        return total

    # ── Semantic memory: store architecture docs, standards, conventions ──────
    def store_memory_document(
        self,
        repo_id: int,
        memory_type: str,   # "architecture" | "standards" | "conventions" | "pr_history"
        content: str,
        metadata: Optional[Dict] = None,
    ) -> str:
        """Store a semantic memory document (not code) for richer RAG context."""
        # Delete old entry of same type for this repo
        self.client.delete(
            collection_name=settings.qdrant_collection,
            points_selector=Filter(must=[
                FieldCondition(key="repo_id", match=MatchValue(value=repo_id)),
                FieldCondition(key="memory_type", match=MatchValue(value=memory_type)),
            ]),
        )
        point_id = str(uuid.uuid4())
        self.client.upsert(
            collection_name=settings.qdrant_collection,
            points=[PointStruct(
                id=point_id,
                vector=self._embed(content),
                payload={
                    "repo_id": repo_id,
                    "memory_type": memory_type,
                    "content": content,
                    **(metadata or {}),
                },
            )],
        )
        return point_id

    def store_pr_summary(self, repo_id: int, pr_number: int, summary: str, issues_summary: str):
        """Store a past PR's review summary for future context."""
        content = f"PR #{pr_number} review: {summary}\nIssues found: {issues_summary}"
        self.store_memory_document(
            repo_id=repo_id,
            memory_type=f"pr_history_{pr_number}",
            content=content,
            metadata={"pr_number": pr_number},
        )

    # ── Search ────────────────────────────────────────────────────────────────
    async def search_relevant_context(
        self,
        repo_id: int,
        query: str,
        limit: int = 8,
        memory_types: Optional[List[str]] = None,
    ) -> List[Dict]:
        """
        Semantic search across all memory types for a repo.
        memory_types: filter to specific types (e.g. ["code", "standards"])
                      None = search all
        """
        loop = asyncio.get_event_loop()
        embedding = await loop.run_in_executor(self.executor, self._embed, query)

        filter_conditions = [
            FieldCondition(key="repo_id", match=MatchValue(value=repo_id))
        ]

        results = self.client.search(
            collection_name=settings.qdrant_collection,
            query_vector=embedding,
            query_filter=Filter(must=filter_conditions),
            limit=limit,
            score_threshold=0.35,
        )

        # Sort: architecture/standards first, then code
        priority = {"architecture": 0, "standards": 1, "conventions": 2, "code": 3}
        hits = sorted(
            [
                {
                    "file_path": r.payload.get("file_path") or r.payload.get("memory_type"),
                    "content": r.payload.get("content"),
                    "memory_type": r.payload.get("memory_type", "code"),
                    "score": r.score,
                }
                for r in results
            ],
            key=lambda x: (priority.get(x.get("memory_type", "code"), 9), -x["score"]),
        )
        return hits

    def delete_repo_index(self, repo_id: int):
        self.client.delete(
            collection_name=settings.qdrant_collection,
            points_selector=Filter(must=[
                FieldCondition(key="repo_id", match=MatchValue(value=repo_id))
            ]),
        )

    def get_collection_stats(self) -> Dict:
        info = self.client.get_collection(settings.qdrant_collection)
        return {"total_vectors": info.vectors_count, "status": str(info.status)}
