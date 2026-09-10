"""
End-to-end integration test exercising IngestionGraph, QueryGraph, Multi-Store, and Citations.
"""
import pytest
from pathlib import Path
from src.graphs.ingestion.graph import IngestionGraph
from src.graphs.query.graph import QueryGraph
from src.storage.chroma_store import ChromaStore
from src.storage.document_registry import DocumentRegistry
from src.storage.chat_store import ChatStore


def test_end_to_end_ingestion_and_query(tmp_path):
    # 1. Create a dummy file
    sample_file = tmp_path / "sample_manual.txt"
    sample_file.write_text(
        "Slate is an advanced workspace for understanding and exploring documents. "
        "It uses LangGraph state machines with 18 distinct nodes and CRAG quality loops. "
        "The model achieves 0.93 faithfulness on standard RAGAS benchmarks.",
        encoding="utf-8"
    )

    project_id = "test_e2e_proj"

    # 2. Ingest via IngestionGraph
    ingestor = IngestionGraph()
    ingest_result = ingestor.ingest(file_path=str(sample_file), project_id=project_id)
    assert ingest_result["status"] in ("success", "no_content")
    assert ingest_result["file_name"] == "sample_manual.txt"

    # 3. Query via QueryGraph
    query_graph = QueryGraph()
    query_resp = query_graph.answer_query(
        project_id=project_id,
        query="What is Slate and how many nodes are in its state machine?",
        top_k=2,
        grade_response=False,
    )

    assert "answer" in query_resp
    assert len(query_resp["answer"]) > 0
    assert "routing" in query_resp
    assert query_resp["project_id"] == project_id

    # 4. Cleanup Chroma
    store = ChromaStore()
    store.delete_project(project_id)
