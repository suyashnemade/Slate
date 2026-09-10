import pytest
from pathlib import Path
from src.ingestion.loader import DocumentLoader
from src.ingestion.chunker import DocumentChunker


def test_load_text_string():
    raw_text = "DocMind is a multimodal document AI system designed for advanced RAG."
    docs = DocumentLoader.load_text(raw_text, source_name="test_text")
    assert len(docs) == 1
    assert docs[0].content == raw_text
    assert docs[0].metadata["source"] == "test_text"
    assert docs[0].metadata["file_type"] == "text"


def test_load_text_file(tmp_path: Path):
    sample_file = tmp_path / "sample.txt"
    sample_file.write_text("This is line one.\nThis is line two.", encoding="utf-8")

    docs = DocumentLoader.load_file(sample_file)
    assert len(docs) == 1
    assert "line one" in docs[0].content
    assert docs[0].metadata["file_type"] == "txt"


def test_load_markdown_file(tmp_path: Path):
    sample_md = tmp_path / "doc.md"
    sample_md.write_text("# Title\n\nContent paragraph here.", encoding="utf-8")

    docs = DocumentLoader.load_file(sample_md)
    assert len(docs) == 1
    assert docs[0].metadata["file_type"] == "md"


def test_chunker_splitting_and_metadata():
    chunker = DocumentChunker(chunk_size=100, chunk_overlap=20)
    docs = DocumentLoader.load_text(
        "A" * 80 + "\n\n" + "B" * 80 + "\n\n" + "C" * 80,
        source_name="long_doc"
    )
    chunks = chunker.split_documents(docs, project_id="test_proj")

    assert len(chunks) >= 3
    for idx, chunk in enumerate(chunks):
        assert chunk.metadata["project_id"] == "test_proj"
        assert chunk.metadata["chunk_index"] == idx
        assert "total_chunks" in chunk.metadata
        assert "chunk_created_at" in chunk.metadata
        assert chunk.chunk_id.startswith("test_proj_long_doc_chunk_")
