"""
Query Correction Subgraph: LangGraph StateGraph that reformulates queries when CRAG detects low evidence quality.
"""
from typing import Any, Dict, List, Optional
from typing_extensions import TypedDict
from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph

from ..query.chat_model import get_chat_model


class QueryCorrectionState(TypedDict, total=False):
    """State schema for CRAG query correction."""
    query: str
    corrected_query: str


def correct_query_node(state: QueryCorrectionState) -> Dict[str, Any]:
    """Uses LLM to rewrite ambiguous or failing search queries with more targeted terminology."""
    query = state.get("query", "")
    llm = get_chat_model()

    system_prompt = (
        "You are an expert search query optimization assistant in a Corrective RAG (CRAG) system. "
        "The previous query failed to retrieve sufficient high-quality evidence from the knowledge base.\n"
        "Your task:\n"
        "- Reformulate the query into a more specific, keyword-dense search query.\n"
        "- Use domain-appropriate terminology and synonyms.\n"
        "- Return ONLY the reformulated query text, nothing else."
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Original Query: {query}"),
    ]

    try:
        response = llm.invoke(messages)
        corrected = response.content.strip().strip('"\'')
        if corrected and len(corrected) > 5:
            return {"corrected_query": corrected}
    except Exception:
        pass

    return {"corrected_query": query}


def build_query_correction_subgraph() -> StateGraph:
    """Builds the LangGraph StateGraph for query reformulation."""
    graph = StateGraph(QueryCorrectionState)
    graph.add_node("correct_query", correct_query_node)
    graph.set_entry_point("correct_query")
    graph.add_edge("correct_query", END)
    return graph


class QueryCorrectionSubgraph:
    """Convenience wrapper around the correction StateGraph."""

    def __init__(self, llm: Optional[BaseLanguageModel] = None):
        self.graph = build_query_correction_subgraph().compile()

    def correct(self, query: str) -> str:
        result = self.graph.invoke({"query": query})
        return result.get("corrected_query", query)
