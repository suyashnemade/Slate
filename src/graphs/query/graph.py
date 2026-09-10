from datetime import datetime, timezone
import re
from typing import Any, Dict, List, Literal, Optional, TypedDict
import uuid

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph

from .chat_model import get_chat_model
from ...config import settings
from ...storage.chroma_store import ChromaStore
from ...storage.chat_store import ChatStore
from ...storage.reranker import BGEReranker
from ...evaluation.grader import LLMGrader
from ..subgraphs.retrieval_subgraph import build_retrieval_subgraph, SearchResult
from ..subgraphs.citation_subgraph import build_citation_subgraph
from ..subgraphs.reasoning_subgraph import ReasoningSubgraph
from ..subgraphs.query_decomposition_subgraph import QueryDecompositionSubgraph
from ..subgraphs.query_correction_subgraph import QueryCorrectionSubgraph


class QueryState(TypedDict, total=False):
    """State schema for the query pipeline."""
    project_id: str
    query: str
    chat_id: Optional[str]
    top_k: int
    grade_response: bool

    # Query understanding
    intent: str  # factual, comparative, procedural, exploratory
    complexity: str  # simple, complex
    modalities: List[str]
    subqueries: List[str]
    mentioned_documents: List[str]
    conversation_history: List[Dict[str, Any]]

    # Retrieval
    retrieved_evidence: List[Dict[str, Any]]
    reranked_evidence: List[Dict[str, Any]]
    retry_count: int

    # Generation
    context: str
    answer: str
    citations: List[Dict[str, Any]]

    # Verification
    grade: Optional[Dict[str, Any]]
    verified: bool


# ============================================================================
# Node Implementations
# ============================================================================

def load_project(state: QueryState) -> QueryState:
    """Initialize project context and load conversation history."""
    project_id = state.get("project_id", "default")
    chat_id = state.get("chat_id")
    top_k = state.get("top_k") or settings.TOP_K

    conversation_history = []
    if chat_id:
        try:
            chat_store = ChatStore()
            conversation_history = chat_store.get_messages(chat_id)
        except Exception:
            pass

    return {
        **state,
        "project_id": project_id,
        "top_k": top_k,
        "conversation_history": conversation_history,
        "retry_count": 0,
        "retrieved_evidence": [],
        "reranked_evidence": [],
        "citations": [],
        "grade": None,
        "verified": False,
    }


def resolve_document_mentions(state: QueryState) -> QueryState:
    """Parse @document mentions from query."""
    query = state.get("query", "")
    pattern = r"@([\w\-\.]+(?:\.\w+)?)"
    mentions = re.findall(pattern, query)
    clean_query = re.sub(r"@[\w\-\.]+(?:\.\w+)?", "", query).strip()
    return {
        **state,
        "query": clean_query if mentions else query,
        "mentioned_documents": mentions,
    }


def query_understanding(state: QueryState) -> QueryState:
    """Classify query intent and required modalities."""
    query = state.get("query", "").lower()

    # Intent classification via heuristics
    if any(w in query for w in ["compare", "versus", "vs", "difference", "contrast"]):
        intent = "comparative"
    elif any(w in query for w in ["how to", "steps", "procedure", "process"]):
        intent = "procedural"
    elif any(w in query for w in ["explore", "tell me about", "overview", "describe"]):
        intent = "exploratory"
    else:
        intent = "factual"

    # Modality detection
    modalities = ["text"]
    if any(w in query for w in ["table", "row", "column", "data", "number", "statistics"]):
        modalities.append("tables")
    if any(w in query for w in ["image", "figure", "diagram", "photo", "picture", "chart"]):
        modalities.append("images")

    return {**state, "intent": intent, "modalities": modalities}


def determine_complexity(state: QueryState) -> QueryState:
    """Determine if query is simple or complex."""
    query = state.get("query", "")
    intent = state.get("intent", "factual")

    is_complex = (
        intent in ("comparative", "procedural")
        or len(query.split()) > 20
        or any(w in query.lower() for w in ["and also", "additionally", "furthermore", "both"])
    )

    return {**state, "complexity": "complex" if is_complex else "simple"}


def query_decomposition(state: QueryState) -> QueryState:
    """Decompose complex queries into subqueries."""
    query = state.get("query", "")
    complexity = state.get("complexity", "simple")

    if complexity == "simple":
        return {**state, "subqueries": [query]}

    try:
        subgraph = QueryDecompositionSubgraph()
        subqueries = subgraph.decompose(query)
        if subqueries and len(subqueries) > 1:
            return {**state, "subqueries": subqueries}
    except Exception:
        pass

    return {**state, "subqueries": [query]}


def query_router(state: QueryState) -> QueryState:
    """Route query to appropriate retrieval strategy based on modalities."""
    # Already handled by modality detection in query_understanding
    return state


def hierarchical_retrieval(state: QueryState) -> QueryState:
    """Retrieve evidence from ChromaDB using subqueries."""
    project_id = state.get("project_id", "default")
    subqueries = state.get("subqueries", [state.get("query", "")])
    top_k = state.get("top_k", 4)
    mentioned_docs = state.get("mentioned_documents", [])

    all_evidence = []
    chroma = ChromaStore()

    for sq in subqueries:
        try:
            results = chroma.query(project_id=project_id, query_text=sq, top_k=top_k)
            for doc in results:
                evidence = {
                    "content": doc.content,
                    "source": doc.metadata.get("source", "unknown"),
                    "page": doc.metadata.get("page", 0),
                    "score": doc.metadata.get("score", 0.0),
                    "metadata": doc.metadata,
                }
                # Filter by mentioned documents if specified
                if mentioned_docs:
                    src = evidence["source"].lower()
                    if any(m.lower() in src for m in mentioned_docs):
                        all_evidence.append(evidence)
                else:
                    all_evidence.append(evidence)
        except Exception:
            pass

    # Deduplicate by content
    seen = set()
    unique_evidence = []
    for ev in all_evidence:
        key = ev["content"][:200]
        if key not in seen:
            seen.add(key)
            unique_evidence.append(ev)

    return {**state, "retrieved_evidence": unique_evidence}


def reranking(state: QueryState) -> QueryState:
    """Rerank retrieved evidence using BGE cross-encoder."""
    query = state.get("query", "")
    evidence = state.get("retrieved_evidence", [])

    if not evidence:
        return {**state, "reranked_evidence": []}

    try:
        reranker = BGEReranker()
        contents = [e["content"] for e in evidence]
        scores = reranker.rerank(query=query, documents=contents)

        for i, ev in enumerate(evidence):
            if i < len(scores):
                ev["rerank_score"] = scores[i]
            else:
                ev["rerank_score"] = ev.get("score", 0.0)

        reranked = sorted(evidence, key=lambda x: x.get("rerank_score", 0), reverse=True)
        return {**state, "reranked_evidence": reranked}
    except Exception:
        # Fallback: sort by original score
        sorted_ev = sorted(evidence, key=lambda x: x.get("score", 0), reverse=True)
        return {**state, "reranked_evidence": sorted_ev}


def crag(state: QueryState) -> QueryState:
    """Corrective RAG: evaluate evidence quality and decide if re-retrieval is needed."""
    evidence = state.get("reranked_evidence") or state.get("retrieved_evidence", [])
    retry_count = state.get("retry_count", 0)

    # Always increment retry_count to prevent infinite loops
    new_retry = retry_count + 1

    if not evidence:
        return {**state, "retry_count": new_retry}

    # Check average score
    scores = [e.get("rerank_score", e.get("score", 0.0)) for e in evidence[:3]]
    avg_score = sum(scores) / max(1, len(scores))

    if avg_score < 0.3:
        # Try query correction
        try:
            corrector = QueryCorrectionSubgraph()
            corrected = corrector.correct(state.get("query", ""))
            if corrected and corrected != state.get("query"):
                return {**state, "query": corrected, "retry_count": new_retry}
        except Exception:
            pass

    return {**state, "retry_count": new_retry}


def context_assembly(state: QueryState) -> QueryState:
    """Assemble evidence into a formatted context string."""
    evidence = state.get("reranked_evidence") or state.get("retrieved_evidence", [])

    if not evidence:
        return {**state, "context": "No relevant context found in uploaded documents."}

    context_parts = []
    for i, ev in enumerate(evidence[:6], 1):
        source = ev.get("source", "unknown")
        page = ev.get("page", "?")
        content = ev.get("content", "")
        context_parts.append(f"[Source {i}: {source}, p.{page}]\n{content}")

    context = "\n\n".join(context_parts)
    return {**state, "context": context}


def multimodal_reasoning(state: QueryState) -> QueryState:
    """Apply modality-specific reasoning if tables or images are involved."""
    modalities = state.get("modalities", ["text"])

    if "tables" in modalities or "images" in modalities:
        try:
            reasoner = ReasoningSubgraph()
            enhanced_context = reasoner.reason(
                query=state.get("query", ""),
                context=state.get("context", ""),
                modalities=modalities,
            )
            if enhanced_context:
                return {**state, "context": enhanced_context}
        except Exception:
            pass

    return state


def answer_generation(state: QueryState) -> QueryState:
    """Call LangChain chat model to generate grounded answer."""
    llm = get_chat_model()
    messages: List[Any] = []

    system_prompt = (
        "You are Slate — an AI workspace for understanding, exploring, and working with information. "
        "Answer the user's question using ONLY the provided context. "
        "Every factual claim must cite its source (e.g., [doc.pdf, p.1]). "
        "If the context does not contain enough information to answer, state clearly that "
        "the uploaded documents do not contain the answer."
    )
    messages.append(SystemMessage(content=system_prompt))

    # Add conversation history
    for prev in state.get("conversation_history", []):
        role = prev.get("role", "user")
        content = prev.get("content", "")
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))

    # Add current query with context
    context = state.get("context", "")
    query = state.get("query", "")
    user_msg = f"Context:\n{context}\n\nQuestion: {query}"
    messages.append(HumanMessage(content=user_msg))

    try:
        result = llm.invoke(messages)
        answer = result.content
    except Exception as e:
        answer = f"Error generating answer: {str(e)}"

    return {**state, "answer": answer}


def verification(state: QueryState) -> QueryState:
    """Grade the answer quality using LLM-as-judge."""
    if not state.get("grade_response", True):
        return {**state, "verified": True, "grade": {"score": 1.0, "passed": True, "feedback": "Grading skipped."}}

    try:
        grader = LLMGrader()
        grade_result = grader.grade(
            question=state.get("query", ""),
            context=state.get("context", ""),
            answer=state.get("answer", ""),
        )
        return {
            **state,
            "verified": True,
            "grade": {
                "score": grade_result.score,
                "passed": grade_result.passed,
                "feedback": grade_result.feedback,
                "criteria": grade_result.criteria,
            },
        }
    except Exception:
        return {**state, "verified": True, "grade": {"score": 0.5, "passed": True, "feedback": "Grading unavailable."}}


def citation_builder(state: QueryState) -> QueryState:
    """Extract and structure citations from evidence."""
    evidence = state.get("reranked_evidence") or state.get("retrieved_evidence", [])
    citations = []

    for ev in evidence[:6]:
        citations.append({
            "source": ev.get("source", "unknown"),
            "page": ev.get("page", 0),
            "content": ev.get("content", "")[:500],
            "score": ev.get("rerank_score", ev.get("score", 0.0)),
        })

    return {**state, "citations": citations}


# ============================================================================
# Conditional Edges
# ============================================================================

def should_continue_complexity(state: QueryState) -> Literal["simple", "complex"]:
    return state.get("complexity", "simple")


def should_continue_crag(state: QueryState) -> Literal["sufficient", "insufficient"]:
    evidence = state.get("reranked_evidence") or state.get("retrieved_evidence", [])
    retry_count = state.get("retry_count", 0)

    if retry_count > 1:
        return "sufficient"

    if not evidence:
        return "insufficient"

    scores = [e.get("rerank_score", e.get("score", 0.0)) for e in evidence[:3]]
    avg = sum(scores) / max(1, len(scores))

    if avg < 0.3:
        return "insufficient"

    return "sufficient"


# ============================================================================
# Graph Builder
# ============================================================================

def build_query_graph() -> StateGraph:
    """Build the 18-node QueryGraph state machine."""
    graph = StateGraph(QueryState)

    # Add nodes
    graph.add_node("load_project", load_project)
    graph.add_node("resolve_document_mentions", resolve_document_mentions)
    graph.add_node("query_understanding", query_understanding)
    graph.add_node("determine_complexity", determine_complexity)
    graph.add_node("query_decomposition", query_decomposition)
    graph.add_node("query_router", query_router)
    graph.add_node("hierarchical_retrieval", hierarchical_retrieval)
    graph.add_node("reranking", reranking)
    graph.add_node("crag", crag)
    graph.add_node("context_assembly", context_assembly)
    graph.add_node("multimodal_reasoning", multimodal_reasoning)
    graph.add_node("answer_generation", answer_generation)
    graph.add_node("verification", verification)
    graph.add_node("citation_builder", citation_builder)

    # Set entry point
    graph.set_entry_point("load_project")

    # Linear edges
    graph.add_edge("load_project", "resolve_document_mentions")
    graph.add_edge("resolve_document_mentions", "query_understanding")
    graph.add_edge("query_understanding", "determine_complexity")

    # Conditional: complexity routing
    graph.add_conditional_edges(
        "determine_complexity",
        should_continue_complexity,
        {
            "simple": "query_router",
            "complex": "query_decomposition",
        },
    )

    graph.add_edge("query_decomposition", "query_router")
    graph.add_edge("query_router", "hierarchical_retrieval")
    graph.add_edge("hierarchical_retrieval", "reranking")
    graph.add_edge("reranking", "crag")

    # Conditional: CRAG quality check
    graph.add_conditional_edges(
        "crag",
        should_continue_crag,
        {
            "sufficient": "context_assembly",
            "insufficient": "hierarchical_retrieval",
        },
    )

    graph.add_edge("context_assembly", "multimodal_reasoning")
    graph.add_edge("multimodal_reasoning", "answer_generation")
    graph.add_edge("answer_generation", "verification")
    graph.add_edge("verification", "citation_builder")
    graph.add_edge("citation_builder", END)

    return graph


# ============================================================================
# QueryGraph Class
# ============================================================================

class QueryGraph:
    """High-level interface for executing the query graph."""

    def __init__(self):
        self.graph = build_query_graph()
        self.runnable = self.graph.compile()

    def answer_query(
        self,
        project_id: str,
        query: str,
        top_k: Optional[int] = None,
        grade_response: bool = True,
        chat_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        cid = chat_id or f"chat_{uuid.uuid4().hex[:8]}"

        initial_state: QueryState = {
            "project_id": project_id,
            "query": query,
            "chat_id": cid,
            "top_k": top_k or settings.TOP_K,
            "grade_response": grade_response,
        }

        final_state = self.runnable.invoke(initial_state)

        answer = final_state.get("answer", "No answer generated.")
        citations = final_state.get("citations", [])
        grade_dict = final_state.get("grade")

        # Persist conversation
        if cid:
            try:
                chat_store = ChatStore()
                chat_store.add_message(cid, project_id, "user", query)
                chat_store.add_message(cid, project_id, "assistant", answer, citations=citations, grade=grade_dict)
            except Exception:
                pass

        # Grade with LLM grader if requested
        if grade_response and not grade_dict:
            try:
                grader = LLMGrader()
                gr = grader.grade(
                    question=query,
                    context=final_state.get("context", ""),
                    answer=answer,
                )
                grade_dict = {
                    "score": gr.score,
                    "passed": gr.passed,
                    "feedback": gr.feedback,
                    "criteria": gr.criteria,
                }
            except Exception:
                grade_dict = {"score": 0.5, "passed": True, "feedback": "Grading unavailable."}

        ev_list = final_state.get("reranked_evidence") or final_state.get("retrieved_evidence", [])
        return {
            "project_id": project_id,
            "chat_id": cid,
            "answer": answer,
            "citations": citations,
            "context": final_state.get("context", ""),
            "retrieved_evidence": [e.get("content", "") for e in ev_list if e.get("content")],
            "routing": {
                "intent": final_state.get("intent", "factual"),
                "modalities": final_state.get("modalities", ["text"]),
                "complexity": final_state.get("complexity", "simple"),
                "subqueries": final_state.get("subqueries", [query]),
            },
            "grade": grade_dict,
        }
