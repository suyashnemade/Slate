import pytest
from pathlib import Path
from src.routing.router import QueryRouter, QueryType
from src.routing.multi_hop import MultiHopEngine
from src.storage.chroma_store import ChromaStore
from src.retrieval.retriever import DocumentRetriever
from src.ingestion.loader import DocumentLoader
from src.ingestion.chunker import DocumentChunker


def test_query_router_classification():
    router = QueryRouter()

    # Simple queries
    simple_q = "What is the refund policy?"
    decision_simple = router.route(simple_q)
    assert decision_simple.query_type == QueryType.SIMPLE
    assert decision_simple.confidence >= 0.5
    assert len(decision_simple.subqueries) >= 1

    # Complex / multi-hop queries
    complex_q = "Compare the difference between plan A and plan B"
    decision_complex = router.route(complex_q)
    assert decision_complex.query_type == QueryType.COMPLEX
    assert decision_complex.confidence >= 0.5
    assert len(decision_complex.subqueries) >= 2


def test_multi_hop_engine_process(tmp_path: Path):
    persist_dir = str(tmp_path / "chroma_multihop")
    store = ChromaStore(persist_dir=persist_dir)
    retriever = DocumentRetriever(store=store)
    engine = MultiHopEngine(retriever=retriever, router=QueryRouter())

    project_id = "proj_multihop"
    chunker = DocumentChunker()

    doc1 = DocumentLoader.load_text("Plan A costs $10 monthly and includes basic features.", source_name="plan_a.txt")
    doc2 = DocumentLoader.load_text("Plan B costs $25 monthly and includes advanced analytics.", source_name="plan_b.txt")

    store.add_chunks(project_id, chunker.split_documents(doc1, project_id=project_id))
    store.add_chunks(project_id, chunker.split_documents(doc2, project_id=project_id))

    # Run multi-hop query
    res = engine.process_query(
        project_id=project_id,
        query="Compare the difference between Plan A and Plan B",
        top_k=4,
    )

    assert res["is_multi_hop"] is True
    assert res["routing"]["query_type"] == "complex"
    assert len(res["retrieved_context"].results) >= 2

    store.delete_project(project_id)
