"""
Slate Pipeline: Unified interface for Slate multimodal agentic RAG system.
Integrates IngestionGraph and QueryGraph into a cohesive facade.
"""
from pathlib import Path
from typing import Any, Dict, List, Optional
import httpx

from .config import settings
from .graphs.ingestion.graph import IngestionGraph
from .graphs.query.graph import QueryGraph
from .storage.chroma_store import ChromaStore
from .storage.hybrid_store import HybridStore
from .storage.document_registry import DocumentRegistry
from .storage.chat_store import ChatStore


class SlatePipeline:
    """End-to-end Slate RAG pipeline orchestrating IngestionGraph and QueryGraph."""

    def __init__(
        self,
        ingestion_graph: Optional[IngestionGraph] = None,
        query_graph: Optional[QueryGraph] = None,
        store: Optional[ChromaStore] = None,
    ):
        self.ingestion_graph = ingestion_graph or IngestionGraph()
        self.query_graph = query_graph or QueryGraph()
        self.store = store or ChromaStore()
        self.registry = DocumentRegistry()
        self.chat_store = ChatStore()

    def ingest_file(
        self,
        project_id: str,
        file_path: str | Path,
        extra_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Ingests document through the LangGraph IngestionGraph pipeline."""
        return self.ingestion_graph.ingest(
            file_path=str(file_path),
            project_id=project_id,
        )

    def ingest_text(
        self,
        project_id: str,
        text: str,
        source_name: str = "raw_text",
        extra_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Ingests raw text directly into project storage."""
        # Simple text chunking and indexing
        doc_id = self.registry.register_document(
            project_id=project_id,
            filename=source_name,
            file_path=source_name,
            file_type="text/plain",
            file_size=len(text.encode("utf-8")),
        )
        from .ingestion.loader import LoadedDocument
        from .ingestion.chunker import DocumentChunker
        chunker = DocumentChunker()
        doc = LoadedDocument(content=text, metadata={"source": source_name, "project_id": project_id})
        chunks = chunker.split_documents([doc], project_id=project_id)
        count = self.store.add_chunks(project_id, chunks)
        return {
            "status": "success",
            "project_id": project_id,
            "source": source_name,
            "chunks_stored": count,
            "total_chunks_in_project": self.store.count(project_id),
        }

    def answer_query(
        self,
        project_id: str,
        query: str,
        top_k: Optional[int] = None,
        grade_response: bool = True,
        chat_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Executes full query through the 18-node QueryGraph state machine."""
        return self.query_graph.answer_query(
            project_id=project_id,
            query=query,
            top_k=top_k,
            grade_response=grade_response,
            chat_id=chat_id,
        )


# Backward compatibility alias
DocMindPipeline = SlatePipeline
