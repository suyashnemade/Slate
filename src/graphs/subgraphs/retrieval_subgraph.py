"""
Retrieval Subgraph: LangGraph StateGraph implementing Multi-Modal Hierarchical Retrieval with Reciprocal Rank Fusion (RRF).
"""
from typing import Any, Dict, List, Optional, Union
from typing_extensions import TypedDict
from langgraph.graph import END, StateGraph

from ...storage.chroma_store import ChromaStore, SearchResult
from ...storage.table_store import TableStore
from ...storage.image_store import ImageStore
from ...config import settings

RRF_K = 60


class RetrievalSubgraphState(TypedDict, total=False):
    """State schema for the retrieval subgraph."""
    project_id: str
    query: Union[str, List[str]]
    normalized_queries: List[str]
    modalities: List[str]
    top_k: int
    modality_results: Dict[str, List[Dict[str, Any]]]
    fused_results: List[Dict[str, Any]]


def normalize_input(state: RetrievalSubgraphState) -> Dict[str, Any]:
    """Ensures queries are normalized to a list of strings."""
    raw_query = state.get("query", "")
    if isinstance(raw_query, str):
        normalized = [raw_query.strip()] if raw_query.strip() else []
    elif isinstance(raw_query, list):
        normalized = [str(q).strip() for q in raw_query if str(q).strip()]
    else:
        normalized = []

    modalities = state.get("modalities") or ["text"]
    top_k = state.get("top_k") or settings.TOP_K

    return {
        "normalized_queries": normalized,
        "modalities": modalities,
        "top_k": top_k,
    }


def retrieve_modality_results(state: RetrievalSubgraphState) -> Dict[str, Any]:
    """Retrieves candidates across all active modalities in parallel for each sub-query."""
    project_id = state.get("project_id", "default")
    queries = state.get("normalized_queries", [])
    modalities = state.get("modalities", ["text"])
    top_k = state.get("top_k", settings.TOP_K)

    chroma = ChromaStore()
    table_store = TableStore()
    image_store = ImageStore()

    results_by_modality: Dict[str, List[Dict[str, Any]]] = {m: [] for m in modalities}

    for q in queries:
        if "text" in modalities:
            try:
                docs = chroma.query(project_id=project_id, query_text=q, top_k=top_k)
                for d in docs:
                    results_by_modality["text"].append({
                        "content": d.content,
                        "source": d.metadata.get("source", "unknown"),
                        "page": d.metadata.get("page", 0),
                        "score": d.similarity_score if hasattr(d, "similarity_score") else 0.0,
                        "metadata": d.metadata,
                        "modality": "text",
                    })
            except Exception:
                pass

        if "tables" in modalities:
            try:
                tables = table_store.search(project_id=project_id, query=q, top_k=top_k)
                for t in tables:
                    results_by_modality["tables"].append({
                        "content": t.get("content", ""),
                        "source": t.get("source", "unknown"),
                        "page": t.get("page", 0),
                        "score": t.get("score", 0.0),
                        "metadata": t,
                        "modality": "tables",
                    })
            except Exception:
                pass

        if "images" in modalities:
            try:
                images = image_store.search(project_id=project_id, query=q, top_k=top_k)
                for img in images:
                    results_by_modality["images"].append({
                        "content": img.get("description", ""),
                        "source": img.get("source", "unknown"),
                        "page": img.get("page", 0),
                        "score": img.get("score", 0.0),
                        "metadata": img,
                        "modality": "images",
                    })
            except Exception:
                pass

    return {"modality_results": results_by_modality}


def reciprocal_rank_fusion(lists_of_lists: List[List[Dict[str, Any]]], k: int = RRF_K) -> List[Dict[str, Any]]:
    """Calculates RRF score across multiple ranked retrieval lists."""
    rrf_scores: Dict[str, float] = {}
    doc_map: Dict[str, Dict[str, Any]] = {}

    for doc_list in lists_of_lists:
        for rank, doc in enumerate(doc_list):
            key = f"{doc.get('source', '')}::{doc.get('page', 0)}::{doc.get('content', '')[:100]}"
            if key not in doc_map:
                doc_map[key] = doc
                rrf_scores[key] = 0.0
            rrf_scores[key] += 1.0 / (k + rank + 1)

    sorted_keys = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)
    fused = []
    for key in sorted_keys:
        item = dict(doc_map[key])
        item["rrf_score"] = round(rrf_scores[key], 5)
        fused.append(item)

    return fused


def fuse_modalities(state: RetrievalSubgraphState) -> Dict[str, Any]:
    """Applies Reciprocal Rank Fusion to synthesize text, table, and image candidates."""
    modality_results = state.get("modality_results", {})
    all_lists = [lst for lst in modality_results.values() if lst]
    top_k = state.get("top_k", settings.TOP_K)

    if not all_lists:
        return {"fused_results": []}

    fused = reciprocal_rank_fusion(all_lists)
    return {"fused_results": fused[:top_k * 2]}


def build_retrieval_subgraph() -> StateGraph:
    """Constructs the compiled LangGraph StateGraph for multi-modal retrieval."""
    graph = StateGraph(RetrievalSubgraphState)
    graph.add_node("normalize_input", normalize_input)
    graph.add_node("retrieve_modality_results", retrieve_modality_results)
    graph.add_node("fuse_modalities", fuse_modalities)

    graph.set_entry_point("normalize_input")
    graph.add_edge("normalize_input", "retrieve_modality_results")
    graph.add_edge("retrieve_modality_results", "fuse_modalities")
    graph.add_edge("fuse_modalities", END)
    return graph
