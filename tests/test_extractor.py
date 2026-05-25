import pytest
import fitz
from pathlib import Path

from paperlibrary.services.extractor import extract_text


@pytest.fixture
def pdf_with_abstract(tmp_path: Path) -> Path:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(
        (50, 100),
        "Introduction\n\nSome intro text.\n\nAbstract\n\nThis paper proposes a new method for NLP.",
    )
    path = tmp_path / "paper.pdf"
    doc.save(str(path))
    doc.close()
    return path


@pytest.fixture
def empty_pdf(tmp_path: Path) -> Path:
    doc = fitz.open()
    doc.new_page()
    path = tmp_path / "empty.pdf"
    doc.save(str(path))
    doc.close()
    return path


def test_extract_text_returns_content(pdf_with_abstract: Path):
    text = extract_text(pdf_with_abstract)
    assert "Abstract" in text
    assert len(text) > 10


def test_extract_text_abstract_first(pdf_with_abstract: Path):
    text = extract_text(pdf_with_abstract)
    assert text.index("Abstract") < text.index("Introduction")


def test_extract_text_empty_pdf_returns_empty(empty_pdf: Path):
    text = extract_text(empty_pdf)
    assert text.strip() == ""


def test_extract_text_respects_max_chars(pdf_with_abstract: Path):
    text = extract_text(pdf_with_abstract, max_chars=10)
    assert len(text) <= 10
