from typing import Any, Dict, List, Optional
from ..config import settings
from ..storage.chroma_store import ChromaStore, SearchResult


class RetrievedContext:
    def __init__(self, query: str, results: List[SearchResult], project_id: str):
        self.query = query
        self.results = results
        self.project_id = project_id

    @property
    def has_matches(self) -> bool:
        return len(self.results) > 0

    def format_context_prompt(self) -> str:
        if not self.results:
            return "No relevant documents found."

        parts = []
        for i, res in enumerate(self.results, 1):
            src = res.metadata.get("source", "unknown")
            page = res.metadata.get("page")
            page_info = f", Page {page}" if page else ""
            header = f"[Doc {i}: {src}{page_info} | Relevance: {res.similarity_score:.2f}]"
            parts.append(f"{header}\n{res.content.strip()}")
        return "\n\n".join(parts)

    def to_citations(self) -> List[Dict[str, Any]]:
        citations = []
        for res in self.results:
            citations.append({
                "chunk_id": res.chunk_id,
                "source": res.metadata.get("source"),
                "page": res.metadata.get("page"),
                "similarity_score": res.similarity_score,
                "preview": res.content[:150] + ("..." if len(res.content) > 150 else ""),
            })
        return citations


class DocumentRetriever:
    """Semantic retriever for querying project vector stores."""

    def __init__(self, store: Optional[ChromaStore] = None):
        self.store = store or ChromaStore()

    def retrieve(
        self,
        project_id: str,
        query: str,
        top_k: Optional[int] = None,
        min_similarity: Optional[float] = None,
        where: Optional[Dict[str, Any]] = None,
    ) -> RetrievedContext:
        k = top_k or settings.TOP_K
        threshold = min_similarity if min_similarity is not None else settings.SIMILARITY_THRESHOLD

        raw_results = self.store.query(
            project_id=project_id,
            query_text=query,
            top_k=k,
            where=where,
        )

        filtered = [res for res in raw_results if res.similarity_score >= threshold]
        # If threshold filtered everything out, keep the top match if available to avoid complete dropout
        if not filtered and raw_results:
            filtered = [raw_results[0]]

        return RetrievedContext(query=query, results=filtered, project_id=project_id)
