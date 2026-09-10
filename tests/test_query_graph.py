"""
Unit tests for the 18-node QueryGraph state machine and subgraphs.
"""
import pytest
from src.graphs.query.graph import (
    load_project,
    resolve_document_mentions,
    query_understanding,
    determine_complexity,
    context_assembly,
    citation_builder,
    QueryGraph,
)
from src.graphs.subgraphs.query_decomposition_subgraph import QueryDecompositionSubgraph
from src.graphs.subgraphs.query_correction_subgraph import QueryCorrectionSubgraph


def test_query_understanding_and_mentions():
    state = {"query": "Compare the performance in @report.pdf with last year"}
    state = resolve_document_mentions(state)
    assert "report.pdf" in state["mentioned_documents"]
    assert "@report.pdf" not in state["query"]

    state = query_understanding(state)
    assert state["intent"] == "comparative"


def test_query_decomposition():
    subgraph = QueryDecompositionSubgraph()
    queries = subgraph.decompose("What are the differences between Transformer and RNN architectures?")
    assert len(queries) >= 1


def test_crag_logic_and_branching():
    corrector = QueryCorrectionSubgraph()
    res = corrector.correct("attn is all u need")
    assert len(res) > 0


def test_context_assembly_and_citations():
    evidence = [
        {"source": "paper.pdf", "page": 3, "content": "The Transformer uses 6 layers.", "rerank_score": 0.95}
    ]
    state = {"reranked_evidence": evidence}
    state = context_assembly(state)
    assert "paper.pdf" in state["context"]
    assert "The Transformer uses 6 layers." in state["context"]

    state = citation_builder(state)
    assert len(state["citations"]) == 1
    assert state["citations"][0]["source"] == "paper.pdf"
    assert state["citations"][0]["page"] == 3
