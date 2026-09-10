"""
Test suite covering DocumentRegistry and ChatStore SQLite persistence.
"""
import pytest
from src.storage.document_registry import DocumentRegistry
from src.storage.chat_store import ChatStore


def test_document_registry_lifecycle(tmp_path):
    db_file = str(tmp_path / "test_registry.db")
    registry = DocumentRegistry(db_path=db_file)

    # Register document
    doc_id = registry.register_document(
        project_id="p1",
        filename="test.pdf",
        file_path="/tmp/test.pdf",
        file_type="application/pdf",
        file_size=1024,
    )
    assert doc_id.startswith("doc_")

    # List documents
    docs = registry.list_documents("p1")
    assert len(docs) == 1
    assert docs[0]["filename"] == "test.pdf"

    # Update status
    registry.update_status(doc_id, status="indexed", chunk_count=10, page_count=2)
    doc = registry.get_document(doc_id)
    assert doc["status"] == "indexed"
    assert doc["chunk_count"] == 10

    # Delete
    registry.delete_document(doc_id)
    assert len(registry.list_documents("p1")) == 0


def test_chat_store_persistence(tmp_path):
    db_file = str(tmp_path / "test_chat.db")
    store = ChatStore(db_path=db_file)

    chat_id = store.create_conversation(project_id="p1", title="Research Session")
    assert chat_id.startswith("chat_")

    store.add_message(chat_id, project_id="p1", role="user", content="Hello, what is in this doc?")
    store.add_message(chat_id, project_id="p1", role="assistant", content="The doc is an AI guide.", citations=[{"source": "guide.pdf", "page": 1}])

    messages = store.get_messages(chat_id)
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"
    assert len(messages[1]["citations"]) == 1

    chats = store.list_conversations("p1")
    assert len(chats) == 1
    assert chats[0]["title"] == "Research Session"
