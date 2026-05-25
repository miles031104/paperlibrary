import json
import pytest
import fitz
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch

from paperlibrary.core.config import Settings
from paperlibrary.core.database import init_db
from paperlibrary.models.paper import Paper
from paperlibrary.services.analyzer import Analyzer


FAKE_LLM_RESULT = {
    "title": "Attention Is All You Need",
    "authors": ["Vaswani, A."],
    "year": 2017,
    "venue": "NeurIPS 2017",
    "abstract": "We propose a novel architecture.",
    "topics": ["Transformer", "NLP"],
    "keywords": ["attention"],
    "one_line_summary": "Pure attention model for sequence tasks.",
    "key_contributions": ["Multi-Head Attention", "Positional Encoding"],
    "methodology": "Empirical",
    "citations": ["Bahdanau et al., 2015."],
}


@pytest.fixture
def pdf_with_abstract(tmp_path: Path) -> Path:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 100), "Abstract\n\nThis paper proposes a new method.")
    path = tmp_path / "paper.pdf"
    doc.save(str(path))
    doc.close()
    return path


@pytest.fixture
def seeded_db(tmp_path: Path, pdf_with_abstract: Path):
    factory = init_db(tmp_path / "test.db")
    with factory() as s:
        s.add(Paper(
            paper_id="p1",
            filename="attention.pdf",
            file_path=str(pdf_with_abstract),
            analysis_status="pending",
            created_at=datetime.now(UTC).isoformat(),
        ))
        s.commit()
    return factory


async def test_analyze_success(tmp_path, seeded_db):
    settings = Settings(storage_path=tmp_path, llm_api_key="test")
    analyzer = Analyzer(settings, seeded_db)

    with patch.object(analyzer, "call_llm", new=AsyncMock(return_value=FAKE_LLM_RESULT)):
        await analyzer.analyze("p1", "attention.pdf", str(tmp_path / "paper.pdf"))

    with seeded_db() as s:
        paper = s.get(Paper, "p1")
    assert paper.analysis_status == "done"
    assert paper.title == "Attention Is All You Need"
    assert json.loads(paper.authors) == ["Vaswani, A."]
    assert paper.year == 2017
    assert paper.analyzed_at is not None


async def test_analyze_llm_failure_sets_failed(tmp_path, seeded_db):
    settings = Settings(storage_path=tmp_path, llm_api_key="test")
    analyzer = Analyzer(settings, seeded_db)

    with patch.object(analyzer, "call_llm", new=AsyncMock(side_effect=RuntimeError("API error"))):
        await analyzer.analyze("p1", "attention.pdf", str(tmp_path / "paper.pdf"))

    with seeded_db() as s:
        paper = s.get(Paper, "p1")
    assert paper.analysis_status == "failed"
    assert "API error" in paper.error_message


async def test_analyze_empty_pdf_sets_failed(tmp_path, seeded_db):
    blank = tmp_path / "blank.pdf"
    doc = fitz.open()
    doc.new_page()
    doc.save(str(blank))
    doc.close()

    with seeded_db() as s:
        s.add(Paper(
            paper_id="p2",
            filename="blank.pdf",
            file_path=str(blank),
            analysis_status="pending",
            created_at=datetime.now(UTC).isoformat(),
        ))
        s.commit()

    settings = Settings(storage_path=tmp_path, llm_api_key="test")
    analyzer = Analyzer(settings, seeded_db)

    with patch.object(analyzer, "call_llm", new=AsyncMock()) as mock_llm:
        await analyzer.analyze("p2", "blank.pdf", str(blank))
        mock_llm.assert_not_called()

    with seeded_db() as s:
        paper = s.get(Paper, "p2")
    assert paper.analysis_status == "failed"
    assert "Scanned" in paper.error_message
