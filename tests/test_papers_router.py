import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import fitz
import pytest
from fastapi.testclient import TestClient

from paperlibrary.api.deps import get_analyzer, get_db, get_session_factory, get_settings
from paperlibrary.api.main import create_app
from paperlibrary.models.paper import Paper
from paperlibrary.schemas.paper import PaperResponse
from paperlibrary.services.analyzer import Analyzer


def test_paper_model_roundtrip(db_session):
    paper = Paper(
        paper_id="abc123",
        filename="test.pdf",
        file_path="/tmp/test.pdf",
        analysis_status="pending",
        created_at=datetime.now(UTC).isoformat(),
    )
    db_session.add(paper)
    db_session.commit()

    fetched = db_session.get(Paper, "abc123")
    assert fetched is not None
    assert fetched.filename == "test.pdf"
    assert fetched.analysis_status == "pending"
    assert fetched.title is None


def test_paper_response_parses_json_columns(db_session):
    paper = Paper(
        paper_id="schema1",
        filename="x.pdf",
        file_path="/tmp/x.pdf",
        analysis_status="done",
        created_at=datetime.now(UTC).isoformat(),
        authors=json.dumps(["Smith, J.", "Doe, A."]),
        topics=json.dumps(["NLP", "Transformer"]),
        citations=json.dumps(["Ref 1", "Ref 2"]),
    )
    db_session.add(paper)
    db_session.commit()

    fetched = db_session.get(Paper, "schema1")
    response = PaperResponse.model_validate(fetched)
    assert response.authors == ["Smith, J.", "Doe, A."]
    assert response.topics == ["NLP", "Transformer"]
    assert response.citations == ["Ref 1", "Ref 2"]


# ── API client fixture ──────────────────────────────────────────────────────

@pytest.fixture
def tiny_pdf_bytes() -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 100), "Abstract\n\nTest paper.")
    buf = doc.tobytes()
    doc.close()
    return buf


@pytest.fixture
def api_client(tmp_settings, session_factory):
    app = create_app()

    def override_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_settings] = lambda: tmp_settings
    app.dependency_overrides[get_session_factory] = lambda: session_factory
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_analyzer] = lambda: Analyzer(tmp_settings, session_factory)

    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()


# ── API tests ───────────────────────────────────────────────────────────────

def test_health(api_client):
    resp = api_client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_upload_pdf_returns_pending(api_client, tiny_pdf_bytes):
    with patch("paperlibrary.services.analyzer.Analyzer.analyze", new=AsyncMock()):
        resp = api_client.post(
            "/api/papers/upload",
            files={"file": ("attention.pdf", tiny_pdf_bytes, "application/pdf")},
        )
    assert resp.status_code == 201
    data = resp.json()
    assert data["analysis_status"] == "pending"
    assert data["filename"] == "attention.pdf"
    assert "paper_id" in data


def test_upload_non_pdf_rejected(api_client):
    resp = api_client.post(
        "/api/papers/upload",
        files={"file": ("doc.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 400


def test_list_papers_empty(api_client):
    resp = api_client.get("/api/papers")
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_paper_not_found(api_client):
    resp = api_client.get("/api/papers/doesnotexist")
    assert resp.status_code == 404


def test_upload_then_list(api_client, tiny_pdf_bytes):
    with patch("paperlibrary.services.analyzer.Analyzer.analyze", new=AsyncMock()):
        api_client.post(
            "/api/papers/upload",
            files={"file": ("paper.pdf", tiny_pdf_bytes, "application/pdf")},
        )
    resp = api_client.get("/api/papers")
    assert len(resp.json()) == 1


def test_delete_paper(api_client, tiny_pdf_bytes):
    with patch("paperlibrary.services.analyzer.Analyzer.analyze", new=AsyncMock()):
        upload = api_client.post(
            "/api/papers/upload",
            files={"file": ("paper.pdf", tiny_pdf_bytes, "application/pdf")},
        )
    paper_id = upload.json()["paper_id"]

    assert api_client.delete(f"/api/papers/{paper_id}").status_code == 204
    assert api_client.get(f"/api/papers/{paper_id}").status_code == 404
