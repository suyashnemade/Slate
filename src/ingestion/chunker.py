from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from langchain_text_splitters import RecursiveCharacterTextSplitter

from ..config import settings
from .loader import LoadedDocument


class DocumentChunk:
    def __init__(self, content: str, metadata: Dict[str, Any], chunk_id: Optional[str] = None):
        self.content = content
        self.metadata = metadata
        self.chunk_id = chunk_id or f"{metadata.get('source', 'doc')}_{metadata.get('chunk_index', 0)}"

    def __repr__(self) -> str:
        return f"<DocumentChunk id={self.chunk_id} len={len(self.content)}>"


class DocumentChunker:
    """Splits loaded documents using RecursiveCharacterTextSplitter and enriches metadata."""

    def __init__(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        separators: Optional[List[str]] = None,
    ):
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=separators or ["\n\n", "\n", " ", ""],
        )

    def split_documents(
        self,
        documents: List[LoadedDocument],
        project_id: str = "default",
    ) -> List[DocumentChunk]:
        all_chunks: List[DocumentChunk] = []

        for doc in documents:
            texts = self.splitter.split_text(doc.content)
            total = len(texts)
            timestamp = datetime.now(timezone.utc).isoformat()

            for idx, text in enumerate(texts):
                meta = dict(doc.metadata)
                meta.update({
                    "project_id": project_id,
                    "chunk_index": idx,
                    "total_chunks": total,
                    "chunk_created_at": timestamp,
                    "char_count": len(text),
                })
                source_safe = str(meta.get("source", "doc")).replace(" ", "_").replace("/", "_").replace("\\", "_")
                page_suffix = f"_p{meta.get('page')}" if "page" in meta else ""
                chunk_id = f"{project_id}_{source_safe}{page_suffix}_chunk_{idx}"

                all_chunks.append(DocumentChunk(content=text, metadata=meta, chunk_id=chunk_id))

        return all_chunks
