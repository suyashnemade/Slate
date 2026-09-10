import json
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, StateGraph

from ...config import settings
from ...storage.chroma_store import ChromaStore
from ...storage.document_registry import DocumentRegistry
from ...storage.hybrid_store import HybridStore
from ...storage.image_store import ImageStore
from ...storage.table_store import TableStore

try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    RecursiveCharacterTextSplitter = None

# Check Docling availability
DOCLING_AVAILABLE = False
try:
    from docling.document_converter import DocumentConverter
    from docling.datamodel.pipeline_options import PdfPipelineOptions, PdfFormatOption
    DOCLING_AVAILABLE = True
except ImportError:
    pass

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None


class IngestionState(TypedDict, total=False):
    """State schema for the ingestion pipeline."""
    file_path: str
    project_id: str

    # Validation
    is_valid: bool
    error: Optional[str]

    # Registration
    doc_id: str
    file_name: str

    # Parsing
    raw_text: str
    pages: List[Dict[str, Any]]
    tables: List[Dict[str, Any]]
    images: List[Dict[str, Any]]

    # OCR
    needs_ocr: bool
    ocr_text: str

    # Chunking
    chunks: List[Dict[str, Any]]

    # Indexing result
    indexed_count: int
    status: str


# ============================================================================
# Node Implementations
# ============================================================================

def validate_file_node(state: IngestionState) -> IngestionState:
    """Validate that the file exists and is a supported format."""
    file_path = state.get("file_path", "")
    path = Path(file_path)

    if not path.exists():
        return {**state, "is_valid": False, "error": f"File not found: {file_path}"}

    supported = {".pdf", ".txt", ".md", ".docx", ".pptx", ".html", ".csv", ".tsv"}
    if path.suffix.lower() not in supported:
        return {**state, "is_valid": False, "error": f"Unsupported format: {path.suffix}"}

    return {
        **state,
        "is_valid": True,
        "file_name": path.name,
        "error": None,
    }


def register_document_node(state: IngestionState) -> IngestionState:
    """Register the document in the document registry."""
    if not state.get("is_valid"):
        return state

    file_path = state.get("file_path", "")
    project_id = state.get("project_id", "default")
    path = Path(file_path)

    try:
        registry = DocumentRegistry()
        doc_id = registry.register(
            project_id=project_id,
            file_name=path.name,
            file_path=str(path.absolute()),
            file_size=path.stat().st_size,
        )
        return {**state, "doc_id": doc_id}
    except Exception as e:
        doc_id = f"doc_{uuid.uuid4().hex[:8]}"
        return {**state, "doc_id": doc_id}


def parse_with_docling_node(state: IngestionState) -> IngestionState:
    """Parse document using Docling for advanced layout understanding."""
    if not state.get("is_valid"):
        return state

    file_path = state.get("file_path", "")
    path = Path(file_path)
    pages = []
    tables = []
    images = []
    raw_text = ""

    if DOCLING_AVAILABLE:
        try:
            converter = DocumentConverter()
            result = converter.convert(str(path))
            doc = result.document

            # Extract text
            raw_text = doc.export_to_markdown()

            # Extract tables
            if hasattr(doc, "tables"):
                for i, table in enumerate(doc.tables):
                    table_data = {
                        "index": i,
                        "content": str(table),
                        "page": getattr(table, "prov", [{}])[0].get("page_no", 0) if hasattr(table, "prov") and table.prov else 0,
                    }
                    tables.append(table_data)

            # Extract images/figures
            if hasattr(doc, "pictures"):
                for i, pic in enumerate(doc.pictures):
                    img_data = {
                        "index": i,
                        "description": getattr(pic, "caption", "") or f"Figure {i+1}",
                        "page": getattr(pic, "prov", [{}])[0].get("page_no", 0) if hasattr(pic, "prov") and pic.prov else 0,
                    }
                    images.append(img_data)

            # Approximate pages
            lines = raw_text.split("\n")
            chunk_size = max(1, len(lines) // max(1, len(raw_text) // 3000))
            page_num = 1
            for i in range(0, len(lines), max(1, chunk_size)):
                page_text = "\n".join(lines[i:i+chunk_size])
                pages.append({"page_num": page_num, "text": page_text})
                page_num += 1

        except Exception as e:
            traceback.print_exc()
            # Fallback to pypdf
            if PdfReader and path.suffix.lower() == ".pdf":
                try:
                    reader = PdfReader(str(path))
                    for i, page in enumerate(reader.pages):
                        text = page.extract_text() or ""
                        pages.append({"page_num": i + 1, "text": text})
                        raw_text += text + "\n"
                except Exception:
                    pass
            elif path.suffix.lower() in (".txt", ".md"):
                raw_text = path.read_text(encoding="utf-8", errors="replace")
                pages.append({"page_num": 1, "text": raw_text})
    else:
        # No Docling: fallback
        if PdfReader and path.suffix.lower() == ".pdf":
            try:
                reader = PdfReader(str(path))
                for i, page in enumerate(reader.pages):
                    text = page.extract_text() or ""
                    pages.append({"page_num": i + 1, "text": text})
                    raw_text += text + "\n"
            except Exception:
                pass
        elif path.suffix.lower() in (".txt", ".md", ".csv", ".tsv", ".html"):
            raw_text = path.read_text(encoding="utf-8", errors="replace")
            pages.append({"page_num": 1, "text": raw_text})

    return {
        **state,
        "raw_text": raw_text,
        "pages": pages,
        "tables": tables,
        "images": images,
    }


def ocr_decision_node(state: IngestionState) -> IngestionState:
    """Decide if OCR is needed based on extracted text quality."""
    raw_text = state.get("raw_text", "")
    pages = state.get("pages", [])

    # OCR needed if extracted text is too short relative to expected content
    text_length = len(raw_text.strip())
    needs_ocr = text_length < 100 and len(pages) == 0

    return {**state, "needs_ocr": needs_ocr}


def paddle_ocr_node(state: IngestionState) -> IngestionState:
    """Apply PaddleOCR as fallback for scanned/image-based documents."""
    if not state.get("needs_ocr"):
        return state

    file_path = state.get("file_path", "")

    try:
        from paddleocr import PaddleOCR
        ocr = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
        result = ocr.ocr(file_path, cls=True)

        ocr_text_parts = []
        if result:
            for page_result in result:
                if page_result:
                    for line in page_result:
                        if line and len(line) >= 2:
                            text = line[1][0] if isinstance(line[1], (list, tuple)) else str(line[1])
                            ocr_text_parts.append(text)

        ocr_text = "\n".join(ocr_text_parts)

        if ocr_text.strip():
            pages = state.get("pages", [])
            if not pages:
                pages = [{"page_num": 1, "text": ocr_text}]
            return {
                **state,
                "ocr_text": ocr_text,
                "raw_text": state.get("raw_text", "") + "\n" + ocr_text,
                "pages": pages,
            }
    except Exception:
        traceback.print_exc()

    return state


def classify_and_chunk_node(state: IngestionState) -> IngestionState:
    """Chunk extracted text with RecursiveCharacterTextSplitter."""
    if not state.get("is_valid"):
        return state

    pages = state.get("pages", [])
    file_name = state.get("file_name", "unknown")
    doc_id = state.get("doc_id", "unknown")
    project_id = state.get("project_id", "default")

    chunks = []

    if RecursiveCharacterTextSplitter:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            length_function=len,
        )
    else:
        splitter = None

    for page_data in pages:
        page_num = page_data.get("page_num", 1)
        text = page_data.get("text", "")

        if not text.strip():
            continue

        if splitter:
            splits = splitter.split_text(text)
        else:
            # Manual chunking fallback
            words = text.split()
            splits = []
            for i in range(0, len(words), settings.CHUNK_SIZE // 5):
                chunk_words = words[i:i + settings.CHUNK_SIZE // 5]
                splits.append(" ".join(chunk_words))

        for i, chunk_text in enumerate(splits):
            chunk_id = f"{doc_id}_p{page_num}_c{i}"
            chunks.append({
                "chunk_id": chunk_id,
                "content": chunk_text,
                "metadata": {
                    "source": file_name,
                    "page": page_num,
                    "chunk_index": i,
                    "doc_id": doc_id,
                    "project_id": project_id,
                },
            })

    return {**state, "chunks": chunks}


def index_node(state: IngestionState) -> IngestionState:
    """Index chunks into ChromaDB, tables into TableStore, images into ImageStore."""
    if not state.get("is_valid"):
        return {**state, "indexed_count": 0, "status": "failed"}

    chunks = state.get("chunks", [])
    tables = state.get("tables", [])
    images = state.get("images", [])
    project_id = state.get("project_id", "default")
    doc_id = state.get("doc_id", "unknown")
    file_name = state.get("file_name", "unknown")

    indexed = 0

    # Index text chunks into ChromaDB
    if chunks:
        try:
            chroma = ChromaStore()
            documents = [c["content"] for c in chunks]
            metadatas = [c["metadata"] for c in chunks]
            ids = [c["chunk_id"] for c in chunks]
            chroma.add_documents(
                project_id=project_id,
                documents=documents,
                metadatas=metadatas,
                ids=ids,
            )
            indexed += len(chunks)
        except Exception as e:
            traceback.print_exc()

    # Index tables into TableStore
    if tables:
        try:
            table_store = TableStore()
            for table in tables:
                table_store.add_table(
                    project_id=project_id,
                    doc_id=doc_id,
                    source=file_name,
                    page=table.get("page", 0),
                    content=table.get("content", ""),
                )
                indexed += 1
        except Exception:
            pass

    # Index images into ImageStore
    if images:
        try:
            image_store = ImageStore()
            for img in images:
                image_store.add_image(
                    project_id=project_id,
                    doc_id=doc_id,
                    source=file_name,
                    page=img.get("page", 0),
                    description=img.get("description", ""),
                )
                indexed += 1
        except Exception:
            pass

    status = "success" if indexed > 0 else "no_content"
    return {**state, "indexed_count": indexed, "status": status}


# ============================================================================
# Graph Builder
# ============================================================================

def build_ingestion_graph() -> StateGraph:
    """Build the ingestion pipeline graph."""
    graph = StateGraph(IngestionState)

    graph.add_node("validate_file", validate_file_node)
    graph.add_node("register_document", register_document_node)
    graph.add_node("parse_with_docling", parse_with_docling_node)
    graph.add_node("ocr_decision", ocr_decision_node)
    graph.add_node("paddle_ocr", paddle_ocr_node)
    graph.add_node("classify_and_chunk", classify_and_chunk_node)
    graph.add_node("index", index_node)

    graph.set_entry_point("validate_file")

    graph.add_edge("validate_file", "register_document")
    graph.add_edge("register_document", "parse_with_docling")
    graph.add_edge("parse_with_docling", "ocr_decision")
    graph.add_edge("ocr_decision", "paddle_ocr")
    graph.add_edge("paddle_ocr", "classify_and_chunk")
    graph.add_edge("classify_and_chunk", "index")
    graph.add_edge("index", END)

    return graph


# ============================================================================
# IngestionGraph Class
# ============================================================================

class IngestionGraph:
    """High-level interface for executing the ingestion pipeline."""

    def __init__(self):
        self.graph = build_ingestion_graph()
        self.runnable = self.graph.compile()

    def ingest(self, file_path: str, project_id: str = "default") -> Dict[str, Any]:
        initial_state: IngestionState = {
            "file_path": file_path,
            "project_id": project_id,
        }
        final_state = self.runnable.invoke(initial_state)

        return {
            "project_id": project_id,
            "doc_id": final_state.get("doc_id", ""),
            "file_name": final_state.get("file_name", ""),
            "status": final_state.get("status", "unknown"),
            "indexed_count": final_state.get("indexed_count", 0),
            "tables_found": len(final_state.get("tables", [])),
            "images_found": len(final_state.get("images", [])),
            "needs_ocr": final_state.get("needs_ocr", False),
            "error": final_state.get("error"),
        }
