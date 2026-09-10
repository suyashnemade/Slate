from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from pypdf import PdfReader


class LoadedDocument:
    def __init__(self, content: str, metadata: Dict[str, Any]):
        self.content = content
        self.metadata = metadata

    def __repr__(self) -> str:
        return f"<LoadedDocument source={self.metadata.get('source')} chars={len(self.content)}>"


class DocumentLoader:
    """Loads documents from various formats: PDF, TXT, MD."""

    SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf"}

    @classmethod
    def load_file(cls, file_path: str | Path, extra_metadata: Optional[Dict[str, Any]] = None) -> List[LoadedDocument]:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        ext = path.suffix.lower()
        if ext not in cls.SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file format '{ext}'. Supported: {cls.SUPPORTED_EXTENSIONS}")

        metadata_base = {
            "source": str(path.name),
            "file_path": str(path.resolve()),
            "file_type": ext.lstrip("."),
            "file_size": path.stat().st_size,
            "loaded_at": datetime.now(timezone.utc).isoformat(),
        }
        if extra_metadata:
            metadata_base.update(extra_metadata)

        if ext in {".txt", ".md"}:
            return cls._load_text_file(path, metadata_base)
        elif ext == ".pdf":
            return cls._load_pdf_file(path, metadata_base)
        else:
            raise ValueError(f"No handler for extension: {ext}")

    @classmethod
    def load_text(cls, text: str, source_name: str = "raw_text", extra_metadata: Optional[Dict[str, Any]] = None) -> List[LoadedDocument]:
        metadata = {
            "source": source_name,
            "file_type": "text",
            "file_size": len(text.encode("utf-8")),
            "loaded_at": datetime.now(timezone.utc).isoformat(),
        }
        if extra_metadata:
            metadata.update(extra_metadata)
        return [LoadedDocument(content=text, metadata=metadata)]

    @classmethod
    def _load_text_file(cls, path: Path, metadata_base: Dict[str, Any]) -> List[LoadedDocument]:
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = path.read_text(encoding="latin-1")
        return [LoadedDocument(content=content, metadata=metadata_base)]

    @classmethod
    def _load_pdf_file(cls, path: Path, metadata_base: Dict[str, Any]) -> List[LoadedDocument]:
        reader = PdfReader(str(path))
        docs = []
        for page_idx, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            if not text.strip():
                continue
            meta = dict(metadata_base)
            meta["page"] = page_idx + 1
            meta["total_pages"] = len(reader.pages)
            docs.append(LoadedDocument(content=text, metadata=meta))
        return docs
