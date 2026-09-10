"""
Citation Subgraph: LangGraph StateGraph that aligns generated answers with retrieved evidence via Jaccard similarity.
"""
import re
from typing import Any, Dict, List, Set, Tuple
from typing_extensions import TypedDict
from langgraph.graph import END, StateGraph


class CitationSubgraphState(TypedDict, total=False):
    """State schema for citation attribution and verification."""
    answer: str
    evidence: List[Dict[str, Any]]
    sentences: List[str]
    citations: List[Dict[str, Any]]


def preprocess_text(text: str) -> Set[str]:
    """Tokenize and clean text for n-gram / term overlap."""
    words = re.findall(r"\b\w{3,}\b", text.lower())
    return set(words)


def jaccard_similarity(set_a: Set[str], set_b: Set[str]) -> float:
    """Computes Jaccard similarity coefficient between two token sets."""
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a.intersection(set_b))
    union = len(set_a.union(set_b))
    return intersection / union if union > 0 else 0.0


def extract_sentences(state: CitationSubgraphState) -> Dict[str, Any]:
    """Splits answer into individual proposition sentences."""
    answer = state.get("answer", "")
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", answer) if len(s.strip()) > 15]
    return {"sentences": sentences}


def align_citations(state: CitationSubgraphState) -> Dict[str, Any]:
    """Maps each answer sentence to the most relevant evidence chunk using Jaccard alignment."""
    sentences = state.get("sentences", [])
    evidence = state.get("evidence", [])
    citations: List[Dict[str, Any]] = []

    # Also detect explicit inline brackets like [Source: paper.pdf, p.3]
    inline_pattern = r"\[([^,\]]+),\s*p\.?\s*(\d+)\]"
    answer = state.get("answer", "")
    explicit_matches = re.findall(inline_pattern, answer)

    seen_citations = set()

    for doc_name, page_no in explicit_matches:
        key = f"{doc_name.strip()}::{page_no}"
        if key not in seen_citations:
            seen_citations.add(key)
            citations.append({
                "source": doc_name.strip(),
                "page": int(page_no),
                "type": "explicit",
                "confidence": 1.0,
            })

    # For each sentence, find best matching context chunk
    for sent in sentences:
        sent_tokens = preprocess_text(sent)
        best_score = 0.0
        best_doc = None

        for ev in evidence:
            ev_content = ev.get("content", "")
            ev_tokens = preprocess_text(ev_content)
            score = jaccard_similarity(sent_tokens, ev_tokens)
            if score > best_score:
                best_score = score
                best_doc = ev

        if best_doc and best_score >= 0.15:
            key = f"{best_doc.get('source')}::{best_doc.get('page')}"
            if key not in seen_citations:
                seen_citations.add(key)
                citations.append({
                    "source": best_doc.get("source", "unknown"),
                    "page": best_doc.get("page", 0),
                    "type": "aligned",
                    "sentence": sent,
                    "confidence": round(best_score, 3),
                    "snippet": best_doc.get("content", "")[:180],
                })

    return {"citations": citations}


def build_citation_subgraph() -> StateGraph:
    """Constructs the compiled LangGraph StateGraph for citation alignment."""
    graph = StateGraph(CitationSubgraphState)
    graph.add_node("extract_sentences", extract_sentences)
    graph.add_node("align_citations", align_citations)

    graph.set_entry_point("extract_sentences")
    graph.add_edge("extract_sentences", "align_citations")
    graph.add_edge("align_citations", END)
    return graph
