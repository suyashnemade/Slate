import pytest
from fastapi.testclient import TestClient
from src.api.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health_endpoint(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "0.1.0"


def test_ping_endpoint(client: TestClient):
    response = client.get("/api/ping")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "pong"


def test_ingestion_and_query_flow(client: TestClient):
    proj_id = "test_api_flow"

    # Ingest text
    ingest_resp = client.post(
        f"/api/projects/{proj_id}/documents/text",
        json={
            "text": "DocMind uses ChromaDB as its single collection vector store and all-MiniLM-L6-v2 embeddings.",
            "source_name": "api_spec.txt",
        },
    )
    assert ingest_resp.status_code == 200
    assert ingest_resp.json()["status"] == "success"

    # Query project
    query_resp = client.post(
        f"/api/projects/{proj_id}/query",
        json={"query": "Which vector store does DocMind use?", "top_k": 2},
    )
    assert query_resp.status_code == 200
    q_data = query_resp.json()
    assert q_data["project_id"] == proj_id
    assert len(q_data["citations"]) >= 1
    assert "routing" in q_data
    assert "grade" in q_data

    # Cleanup project
    del_resp = client.delete(f"/api/projects/{proj_id}")
    assert del_resp.status_code == 200
