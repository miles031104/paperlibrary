import json
from datetime import UTC, datetime

from paperlibrary.models.paper import Paper
from paperlibrary.schemas.paper import PaperResponse


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
