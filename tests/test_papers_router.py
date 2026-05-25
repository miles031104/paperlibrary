from datetime import UTC, datetime

from paperlibrary.models.paper import Paper


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
