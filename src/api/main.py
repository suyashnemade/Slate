from datetime import datetime, timezone
from pathlib import Path
import shutil
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile, Query, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ..config import settings
from ..evaluation.ragas_metrics import RagasEvaluator, EvaluationReport
from ..rag_pipeline import SlatePipeline

app = FastAPI(
    title="Slate API",
    description="Slate — an AI workspace for understanding, exploring, and working with information.",
    version="0.1.0",
)

# Enable CORS for frontend clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pipeline = SlatePipeline()


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str
    chroma_dir: str


class PingResponse(BaseModel):
    status: str
    timestamp: str


class IngestTextRequest(BaseModel):
    text: str
    source_name: Optional[str] = "manual_input"
    metadata: Optional[Dict[str, Any]] = None


class QueryRequest(BaseModel):
    query: str
    top_k: Optional[int] = None
    grade_response: Optional[bool] = True
    chat_id: Optional[str] = None


class QueryResponse(BaseModel):
    project_id: str
    query: str
    answer: str
    citations: List[Dict[str, Any]]
    context: Optional[str] = None
    routing: Optional[Dict[str, Any]] = None
    grade: Optional[Dict[str, Any]] = None
    chat_id: Optional[str] = None


class EvaluationRequest(BaseModel):
    samples: List[Dict[str, Any]]


@app.get("/health", response_model=HealthResponse)
def health_endpoint():
    return {
        "status": "healthy",
        "version": "0.1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "chroma_dir": settings.CHROMA_PERSIST_DIR,
    }


@app.get("/api/ping", response_model=PingResponse)
def ping_endpoint():
    return {
        "status": "pong",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/api/projects/{project_id}/documents/text")
def ingest_text_endpoint(project_id: str, req: IngestTextRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")

    result = pipeline.ingest_text(
        project_id=project_id,
        text=req.text,
        source_name=req.source_name or "manual_input",
        extra_metadata=req.metadata,
    )
    return {"status": "success", "data": result}


@app.post("/api/projects/{project_id}/documents/upload")
async def upload_file_endpoint(
    project_id: str,
    file: UploadFile = File(...),
):
    upload_dir = Path(settings.DATA_DIR) / "uploads" / project_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    temp_path = upload_dir / file.filename

    with temp_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        result = pipeline.ingest_file(
            project_id=project_id,
            file_path=temp_path,
        )
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process file: {str(e)}")


@app.post("/api/projects/{project_id}/query", response_model=QueryResponse)
def query_project_endpoint(project_id: str, req: QueryRequest):
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    res = pipeline.answer_query(
        project_id=project_id,
        query=req.query,
        top_k=req.top_k,
        grade_response=req.grade_response if req.grade_response is not None else True,
        chat_id=req.chat_id,
    )
    return QueryResponse(
        project_id=project_id,
        query=req.query,
        answer=res.get("answer", ""),
        citations=res.get("citations", []),
        context=res.get("context", ""),
        routing=res.get("routing"),
        grade=res.get("grade"),
        chat_id=res.get("chat_id"),
    )


@app.get("/api/projects/{project_id}/documents")
def list_documents_endpoint(project_id: str):
    docs = pipeline.registry.list_documents(project_id)
    return {"project_id": project_id, "documents": docs}


@app.get("/api/projects/{project_id}/chats")
def list_chats_endpoint(project_id: str):
    chats = pipeline.chat_store.list_conversations(project_id)
    return {"project_id": project_id, "chats": chats}


@app.get("/api/projects/{project_id}/chats/{chat_id}/messages")
def get_chat_messages_endpoint(project_id: str, chat_id: str):
    messages = pipeline.chat_store.get_messages(chat_id)
    return {"project_id": project_id, "chat_id": chat_id, "messages": messages}


@app.get("/api/projects/{project_id}/stats")
def get_project_stats(project_id: str):
    count = pipeline.store.count(project_id)
    return {
        "project_id": project_id,
        "total_chunks": count,
    }


class CreateProjectRequest(BaseModel):
    project_id: str


class CreateChatRequest(BaseModel):
    title: Optional[str] = "New Chat"
    chat_id: Optional[str] = None


@app.post("/api/projects")
def create_project_endpoint(req: CreateProjectRequest):
    clean_id = req.project_id.strip()
    if not clean_id:
        raise HTTPException(status_code=400, detail="project_id cannot be empty")
    pipeline.store.get_or_create_collection(clean_id)
    return {"status": "success", "project_id": clean_id}


@app.post("/api/projects/{project_id}/chats")
def create_chat_endpoint(project_id: str, req: Optional[CreateChatRequest] = None):
    title = (req.title if req and req.title else "New Chat")
    custom_cid = req.chat_id if req and req.chat_id else None
    cid = pipeline.chat_store.create_conversation(project_id=project_id, title=title, chat_id=custom_cid)
    return {"status": "success", "chat_id": cid, "project_id": project_id, "title": title}


@app.delete("/api/projects/{project_id}")
def delete_project_endpoint(project_id: str):
    success = pipeline.store.delete_project(project_id)
    return {"status": "success" if success else "not_found", "project_id": project_id}


@app.get("/api/projects")
def list_projects_endpoint():
    projects = pipeline.store.list_projects()
    return {"projects": projects}


@app.post("/api/evaluate", response_model=EvaluationReport)
def evaluate_endpoint(req: EvaluationRequest):
    evaluator = RagasEvaluator()
    report = evaluator.evaluate_dataset(req.samples)
    return report
