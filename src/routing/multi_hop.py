from typing import Dict, List, Optional
from ..config import settings
from ..retrieval.retriever import DocumentRetriever, RetrievedContext
from ..storage.chroma_store import SearchResult
from .router import QueryRouter, RoutingDecision, QueryType


class MultiHopEngine:
    """Executes query routing, subquery decomposition, and result synthesis."""

    def __init__(
        self,
        retriever: Optional[DocumentRetriever] = None,
        router: Optional[QueryRouter] = None,
    ):
        self.retriever = retriever or DocumentRetriever()
        self.router = router or QueryRouter()

    def process_query(
        self,
        project_id: str,
        query: str,
        top_k: Optional[int] = None,
    ) -> Dict[str, object]:
        k = top_k or settings.TOP_K
        decision = self.router.route(query)

        if decision.query_type == QueryType.SIMPLE or not decision.subqueries:
            context = self.retriever.retrieve(
                project_id=project_id,
                query=query,
                top_k=k,
            )
            return {
                "query": query,
                "routing": decision.model_dump(),
                "retrieved_context": context,
                "is_multi_hop": False,
                "subquery_results": {},
            }

        # Multi-hop execution: retrieve per subquery and combine
        seen_chunks: Dict[str, SearchResult] = {}
        subquery_logs: Dict[str, List[Dict[str, object]]] = {}

        # Slices per subquery
        per_subquery_k = max(2, k // len(decision.subqueries) + 1)

        for sub_q in decision.subqueries:
            sub_context = self.retriever.retrieve(
                project_id=project_id,
                query=sub_q,
                top_k=per_subquery_k,
                min_similarity=0.0,
            )
            subquery_logs[sub_q] = [r.to_dict() for r in sub_context.results]

            for res in sub_context.results:
                if res.chunk_id in seen_chunks:
                    # Boost score if chunk matches multiple subqueries
                    existing = seen_chunks[res.chunk_id]
                    boosted_score = min(1.0, max(existing.similarity_score, res.similarity_score) + 0.05)
                    existing.similarity_score = boosted_score
                else:
                    seen_chunks[res.chunk_id] = res

        # Sort combined results by similarity score descending
        combined_results = sorted(seen_chunks.values(), key=lambda x: x.similarity_score, reverse=True)[:k]
        combined_context = RetrievedContext(
            query=query,
            results=combined_results,
            project_id=project_id,
        )

        return {
            "query": query,
            "routing": decision.model_dump(),
            "retrieved_context": combined_context,
            "is_multi_hop": True,
            "subquery_results": subquery_logs,
        }
