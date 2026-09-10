"""
Test suite covering multi-modal TableStore and ImageStore components.
"""
import pytest
from src.storage.table_store import TableStore
from src.storage.image_store import ImageStore


def test_table_store_crud(tmp_path):
    db_file = str(tmp_path / "test_tables.db")
    store = TableStore(db_path=db_file)

    # Add table using project_id, table_name, rows format
    rows = [
        {"Year": "2024", "Revenue": "$10M"},
        {"Year": "2025", "Revenue": "$15M"}
    ]
    table_id = store.add_table(
        project_id="p1",
        table_name="financial_report",
        rows=rows,
        extra_metadata={"source": "report.pdf", "page": 3},
    )
    assert table_id is not None

    # Search table by cell value
    results = store.query_tables_by_content(project_id="p1", search_term="$10M")
    assert len(results) >= 1


def test_image_store_clip_search(tmp_path):
    base_dir = str(tmp_path / "test_images")
    store = ImageStore(base_path=base_dir)

    # Add image using project_id, image_data, metadata
    dummy_bytes = b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
    image_id = store.add_image(
        project_id="p1",
        image_data=dummy_bytes,
        metadata={"filename": "diagram.png", "source": "diagram.png", "page": 1, "description": "Architecture flowchart showing Encoder and Decoder layers in Transformer"},
    )
    assert image_id is not None

    # Search image
    results = store.search_by_text(project_id="p1", query="Transformer architecture diagram")
    assert isinstance(results, list)
