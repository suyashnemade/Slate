import pytest
from pathlib import Path
from src.ingestion.loader import DocumentLoader
from src.ingestion.chunker import DocumentChunker
from src.storage.chroma_store import ChromaStore
from src.retrieval.retriever import DocumentRetriever


def test_chroma_storage_and_retrieval(tmp_path: Path):
    persist_dir = str(tmp_path / "chroma_test")
    store = ChromaStore(persist_dir=persist_dir)
    retriever = DocumentRetriever(store=store)

    project_id = "test_alpha"

    # Ingest two documents
    doc1 = DocumentLoader.load_text(
        "Python is a popular programming language known for data science and AI applications.",
        source_name="python_intro.txt"
    )
    doc2 = DocumentLoader.load_text(
        "DocMind provides multimodal agentic RAG with query routing and corrective verification.",
        source_name="docmind_overview.txt"
    )

    chunker = DocumentChunker(chunk_size=200, chunk_overlap=20)
    chunks1 = chunker.split_documents(doc1, project_id=project_id)
    chunks2 = chunker.split_documents(doc2, project_id=project_id)

    store.add_chunks(project_id, chunks1 + chunks2)
    assert store.count(project_id) == 2

    # Query for docmind
    context = retriever.retrieve(project_id=project_id, query="What is DocMind?", top_k=2)
    assert context.has_matches
    assert len(context.results) >= 1
    top_result = context.results[0]
    assert "DocMind" in top_result.content
    assert top_result.similarity_score > 0.0

    # Test citations and formatting
    citations = context.to_citations()
    assert len(citations) >= 1
    assert "source" in citations[0]

    prompt_context = context.format_context_prompt()
    assert "[Doc 1: docmind_overview.txt" in prompt_context

    # Clean up
    assert store.delete_project(project_id) is True
