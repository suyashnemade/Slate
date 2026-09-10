"""
Reasoning Subgraph: LangGraph StateGraph performing modality-specific vision and tabular chain-of-thought enhancement.
"""
from typing import Any, Callable, Dict, List, Optional, Set
from typing_extensions import NotRequired, TypedDict
from langgraph.graph import END, StateGraph
from langchain_core.messages import HumanMessage, SystemMessage

from ..query.chat_model import get_chat_model


class ReasoningSubgraphState(TypedDict, total=False):
    """State schema for multimodal context reasoning."""
    query: str
    context: str
    modalities: List[str]
    enhanced_context: str
    table_insights: str
    visual_insights: str


def reason_tables_node(state: ReasoningSubgraphState) -> Dict[str, Any]:
    """Analyzes and summarizes tabular data in context with respect to the user query."""
    modalities = state.get("modalities", [])
    if "tables" not in modalities:
        return {"table_insights": ""}

    context = state.get("context", "")
    query = state.get("query", "")
    llm = get_chat_model()

    prompt = (
        f"Analyze the following document context specifically focusing on tables and quantitative metrics.\n"
        f"Context: {context[:3000]}\n"
        f"Question: {query}\n"
        f"Extract exact numbers, headers, and row comparisons relevant to answering the question concisely."
    )

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        return {"table_insights": response.content.strip()}
    except Exception:
        return {"table_insights": ""}


def reason_images_node(state: ReasoningSubgraphState) -> Dict[str, Any]:
    """Interprets diagram captions, charts, and image context with respect to the query."""
    modalities = state.get("modalities", [])
    if "images" not in modalities:
        return {"visual_insights": ""}

    context = state.get("context", "")
    query = state.get("query", "")
    llm = get_chat_model()

    prompt = (
        f"Analyze the following figure/chart captions and visual annotations in the context.\n"
        f"Context: {context[:3000]}\n"
        f"Question: {query}\n"
        f"Provide the key visual takeaways and structural relations shown."
    )

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        return {"visual_insights": response.content.strip()}
    except Exception:
        return {"visual_insights": ""}


def merge_insights_node(state: ReasoningSubgraphState) -> Dict[str, Any]:
    """Merges modality-specific analysis into the final enriched context."""
    context = state.get("context", "")
    table_insights = state.get("table_insights", "")
    visual_insights = state.get("visual_insights", "")

    additions = []
    if table_insights:
        additions.append(f"\n\n[Structured Table Insights]:\n{table_insights}")
    if visual_insights:
        additions.append(f"\n\n[Visual / Figure Insights]:\n{visual_insights}")

    enhanced = context + "".join(additions) if additions else context
    return {"enhanced_context": enhanced}


def build_reasoning_subgraph() -> StateGraph:
    """Builds the LangGraph StateGraph for multi-modal reasoning."""
    graph = StateGraph(ReasoningSubgraphState)
    graph.add_node("reason_tables", reason_tables_node)
    graph.add_node("reason_images", reason_images_node)
    graph.add_node("merge_insights", merge_insights_node)

    graph.set_entry_point("reason_tables")
    graph.add_edge("reason_tables", "reason_images")
    graph.add_edge("reason_images", "merge_insights")
    graph.add_edge("merge_insights", END)
    return graph


class ReasoningSubgraph:
    """Convenience wrapper around the reasoning StateGraph."""

    def __init__(self):
        self.graph = build_reasoning_subgraph().compile()

    def reason(self, query: str, context: str, modalities: Optional[List[str]] = None) -> str:
        result = self.graph.invoke({
            "query": query,
            "context": context,
            "modalities": modalities or ["text"],
        })
        return result.get("enhanced_context", context)
