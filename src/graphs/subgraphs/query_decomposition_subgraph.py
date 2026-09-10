"""
Query Decomposition Subgraph: LangGraph StateGraph that breaks complex multi-hop queries into atomic sub-questions.
"""
from typing import Any, Dict, List, Optional
from typing_extensions import TypedDict
from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph

from ..query.chat_model import get_chat_model


class QueryDecompositionState(TypedDict, total=False):
    """State schema for query decomposition."""
    query: str
    subqueries: List[str]


def decompose_query_node(state: QueryDecompositionState) -> Dict[str, Any]:
    """Uses the chat model to break complex queries into targeted search steps."""
    query = state.get("query", "")
    llm = get_chat_model()

    system_prompt = (
        "You are an expert query decomposition assistant for an advanced RAG system. "
        "Your job is to break complex, multi-hop, or comparative questions into 2 to 4 simple, "
        "self-contained sub-queries that can be retrieved independently.\n"
        "Guidelines:\n"
        "- Return ONLY the sub-queries, one per line.\n"
        "- Do not number the lines, do not use bullet points.\n"
        "- If the query is already simple, return only the original query."
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Query: {query}"),
    ]

    try:
        response = llm.invoke(messages)
        lines = [line.strip().lstrip("-*0123456789. ") for line in response.content.split("\n") if line.strip()]
        subqueries = [l for l in lines if len(l) > 8]
        if subqueries:
            return {"subqueries": subqueries[:4]}
    except Exception:
        pass

    return {"subqueries": [query]}


def build_query_decomposition_subgraph() -> StateGraph:
    """Builds the LangGraph StateGraph for query decomposition."""
    graph = StateGraph(QueryDecompositionState)
    graph.add_node("decompose_query", decompose_query_node)
    graph.set_entry_point("decompose_query")
    graph.add_edge("decompose_query", END)
    return graph


class QueryDecompositionSubgraph:
    """Convenience wrapper around the decomposition StateGraph."""

    def __init__(self, llm: Optional[BaseLanguageModel] = None):
        self.graph = build_query_decomposition_subgraph().compile()

    def decompose(self, query: str) -> List[str]:
        result = self.graph.invoke({"query": query})
        return result.get("subqueries", [query])
