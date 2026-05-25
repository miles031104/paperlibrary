# paperlibrary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone local web app where users upload PDFs, an LLM analyzes them automatically, and a browser UI displays the organized library.

**Architecture:** FastAPI backend with SQLite (SQLAlchemy ORM) stores paper metadata. Background tasks call an LLM to extract structured metadata (title, authors, topics, summary, citations). A single static HTML/CSS/JS page, served by FastAPI, polls the API and renders paper cards.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy 2.x, PyMuPDF, anthropic SDK, httpx, Pydantic v2, pytest

---

## File Map

```
paperlibrary/               ← repo root
├── paperlibrary/           ← Python package
│   ├── __init__.py
│   ├── __main__.py         ← uvicorn entry point
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py         ← FastAPI app factory + static mount
│   │   ├── deps.py         ← get_db, get_analyzer, get_settings
│   │   └── routers/
│   │       ├── __init__.py
│   │       ├── papers.py   ← upload/list/detail/delete/re-analyze
│   │       └── health.py   ← GET /api/health
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py       ← pydantic-settings, PAPERLIBRARY_* env vars
│   │   ├── database.py     ← SQLAlchemy engine + Base + init_db()
│   │   └── storage.py      ← PDF path helpers
│   ├── models/
│   │   ├── __init__.py
│   │   └── paper.py        ← Paper ORM model (all fields + JSON cols)
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── paper.py        ← PaperResponse, PaperListResponse Pydantic models
│   ├── services/
│   │   ├── __init__.py
│   │   ├── extractor.py    ← PyMuPDF text extraction
│   │   └── analyzer.py     ← LLM call + JSON parse + DB update
│   └── static/
│       ├── index.html
│       ├── style.css
│       └── app.js
├── tests/
│   ├── conftest.py
│   ├── test_extractor.py
│   ├── test_analyzer.py
│   └── test_papers_router.py
├── .env.example
├── .gitignore
├── pyproject.toml
├── requirements.txt
└── README.md
```

---

## Task 1: Project Scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `requirements.txt`
- Create: `requirements-dev.txt`
- Create: `.env.example`
- Create: `.gitignore`
- Create: all `__init__.py` files

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.backends.legacy:build"

[project]
name = "paperlibrary"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115,<1.0",
    "uvicorn[standard]>=0.30,<1.0",
    "sqlalchemy>=2.0,<3.0",
    "pydantic-settings>=2.0,<3.0",
    "pymupdf>=1.24,<2.0",
    "anthropic>=0.40,<1.0",
    "httpx>=0.27,<1.0",
    "python-multipart>=0.0.9,<1.0",
]

[tool.setuptools.packages.find]
where = ["."]
include = ["paperlibrary*"]
```

- [ ] **Step 2: Create `requirements.txt`**

```
fastapi>=0.115,<1.0
uvicorn[standard]>=0.30,<1.0
sqlalchemy>=2.0,<3.0
pydantic-settings>=2.0,<3.0
pymupdf>=1.24,<2.0
anthropic>=0.40,<1.0
httpx>=0.27,<1.0
python-multipart>=0.0.9,<1.0
```

- [ ] **Step 3: Create `requirements-dev.txt`**

```
-r requirements.txt
pytest>=8.0,<9.0
pytest-asyncio>=0.23,<1.0
```

- [ ] **Step 4: Create `.env.example`**

```ini
# LLM provider: "anthropic" or "openai-compatible"
PAPERLIBRARY_LLM_PROVIDER=anthropic

# Your API key
PAPERLIBRARY_LLM_API_KEY=sk-ant-...

# Model to use (lightweight = cheaper)
PAPERLIBRARY_LLM_MODEL=claude-haiku-4-5

# Only needed for openai-compatible provider
# PAPERLIBRARY_LLM_BASE_URL=https://api.openai.com/v1

# Where to store the SQLite DB and uploaded PDFs (default: ./storage)
# PAPERLIBRARY_STORAGE_PATH=./storage

# Server port (default: 8000)
# PAPERLIBRARY_PORT=8000
```

- [ ] **Step 5: Create `.gitignore`**

```
__pycache__/
*.py[cod]
.env
storage/
*.egg-info/
dist/
.pytest_cache/
```

- [ ] **Step 6: Create all package `__init__.py` files**

Create empty files at:
- `paperlibrary/__init__.py`
- `paperlibrary/api/__init__.py`
- `paperlibrary/api/routers/__init__.py`
- `paperlibrary/core/__init__.py`
- `paperlibrary/models/__init__.py`
- `paperlibrary/schemas/__init__.py`
- `paperlibrary/services/__init__.py`
- `tests/__init__.py`

All files are empty (just `# paperlibrary` as a comment is fine).

- [ ] **Step 7: Install dependencies and verify**

```bash
pip install -e ".[dev]"
# or
pip install -r requirements-dev.txt
python -c "import fastapi, sqlalchemy, fitz, anthropic; print('OK')"
```
Expected: `OK`

- [ ] **Step 8: Commit**

```bash
git add .
git commit -m "chore: project scaffold — pyproject, requirements, .env.example"
```

---

## Task 2: Config

**Files:**
- Create: `paperlibrary/core/config.py`

- [ ] **Step 1: Write `paperlibrary/core/config.py`**

```python
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    llm_provider: str = "anthropic"
    llm_api_key: str = ""
    llm_model: str = "claude-haiku-4-5"
    llm_base_url: str | None = None

    storage_path: Path = Path("./storage")
    max_text_chars: int = 6000
    extract_pages: int = 6
    port: int = 8000

    model_config = SettingsConfigDict(
        env_prefix="PAPERLIBRARY_",
        env_file=".env",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 2: Verify config loads**

```bash
python -c "from paperlibrary.core.config import get_settings; s = get_settings(); print(s.storage_path)"
```
Expected: `storage`

- [ ] **Step 3: Commit**

```bash
git add paperlibrary/core/config.py
git commit -m "feat(core): settings from .env via pydantic-settings"
```

---

## Task 3: Database + ORM Model

**Files:**
- Create: `paperlibrary/core/database.py`
- Create: `paperlibrary/models/paper.py`
- Create: `tests/conftest.py`
- Create: `tests/test_extractor.py` (just the fixture for now)

- [ ] **Step 1: Write `paperlibrary/core/database.py`**

```python
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session


class Base(DeclarativeBase):
    pass


def init_db(db_path: Path) -> sessionmaker[Session]:
    """Create engine, ensure tables exist, return session factory."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)
```

- [ ] **Step 2: Write `paperlibrary/models/paper.py`**

```python
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from paperlibrary.core.database import Base


class Paper(Base):
    __tablename__ = "papers"

    paper_id: Mapped[str] = mapped_column(String, primary_key=True)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    file_path: Mapped[str] = mapped_column(String, nullable=False)

    analysis_status: Mapped[str] = mapped_column(String, default="pending")
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[str] = mapped_column(String, nullable=False)
    analyzed_at: Mapped[str | None] = mapped_column(String, nullable=True)

    # LLM-extracted fields
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    authors: Mapped[str | None] = mapped_column(String, nullable=True)       # JSON
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    venue: Mapped[str | None] = mapped_column(String, nullable=True)
    abstract: Mapped[str | None] = mapped_column(String, nullable=True)
    topics: Mapped[str | None] = mapped_column(String, nullable=True)         # JSON
    keywords: Mapped[str | None] = mapped_column(String, nullable=True)       # JSON
    one_line_summary: Mapped[str | None] = mapped_column(String, nullable=True)
    key_contributions: Mapped[str | None] = mapped_column(String, nullable=True)  # JSON
    methodology: Mapped[str | None] = mapped_column(String, nullable=True)
    citations: Mapped[str | None] = mapped_column(String, nullable=True)      # JSON
```

- [ ] **Step 3: Write failing test in `tests/conftest.py`**

```python
import pytest
from pathlib import Path
from sqlalchemy.orm import Session

from paperlibrary.core.config import Settings
from paperlibrary.core.database import init_db
from paperlibrary.models.paper import Paper


@pytest.fixture
def tmp_settings(tmp_path: Path) -> Settings:
    return Settings(
        llm_provider="anthropic",
        llm_api_key="test-key",
        llm_model="claude-haiku-4-5",
        storage_path=tmp_path,
    )


@pytest.fixture
def session_factory(tmp_settings: Settings):
    return init_db(tmp_settings.storage_path / "papers.db")


@pytest.fixture
def db_session(session_factory) -> Session:
    with session_factory() as s:
        yield s
```

- [ ] **Step 4: Write failing test in `tests/test_papers_router.py`** (DB test only, router comes later)

```python
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
```

- [ ] **Step 5: Run failing test**

```bash
pytest tests/test_papers_router.py::test_paper_model_roundtrip -v
```
Expected: FAIL — `ModuleNotFoundError` or similar until models are importable.

- [ ] **Step 6: Run test after implementation**

```bash
pytest tests/test_papers_router.py::test_paper_model_roundtrip -v
```
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add paperlibrary/core/database.py paperlibrary/models/paper.py tests/
git commit -m "feat(db): SQLite init, Paper ORM model, db_session fixture"
```

---

## Task 4: Storage Helpers

**Files:**
- Create: `paperlibrary/core/storage.py`

- [ ] **Step 1: Write `paperlibrary/core/storage.py`**

```python
from pathlib import Path


def pdfs_dir(storage_path: Path) -> Path:
    return storage_path / "pdfs"


def pdf_path(storage_path: Path, paper_id: str) -> Path:
    return pdfs_dir(storage_path) / f"{paper_id}.pdf"


def ensure_storage(storage_path: Path) -> None:
    pdfs_dir(storage_path).mkdir(parents=True, exist_ok=True)
```

- [ ] **Step 2: Verify**

```bash
python -c "from paperlibrary.core.storage import pdf_path; print(pdf_path('/tmp/s', 'abc'))"
```
Expected: `/tmp/s/pdfs/abc.pdf`

- [ ] **Step 3: Commit**

```bash
git add paperlibrary/core/storage.py
git commit -m "feat(core): storage path helpers"
```

---

## Task 5: Pydantic Schemas

**Files:**
- Create: `paperlibrary/schemas/paper.py`

- [ ] **Step 1: Write `paperlibrary/schemas/paper.py`**

```python
import json
from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator

_JSON_FIELDS = ("authors", "topics", "keywords", "key_contributions", "citations")


class PaperResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    paper_id: str
    filename: str
    analysis_status: str
    error_message: str | None = None
    created_at: str
    analyzed_at: str | None = None

    title: str | None = None
    authors: list[str] = []
    year: int | None = None
    venue: str | None = None
    abstract: str | None = None
    topics: list[str] = []
    keywords: list[str] = []
    one_line_summary: str | None = None
    key_contributions: list[str] = []
    methodology: str | None = None
    citations: list[str] = []

    @model_validator(mode="before")
    @classmethod
    def _parse_json_columns(cls, data: Any) -> Any:
        # SQLAlchemy ORM objects come in as objects, not dicts
        if hasattr(data, "__dict__"):
            data = {k: v for k, v in data.__dict__.items() if not k.startswith("_")}
        for field in _JSON_FIELDS:
            val = data.get(field)
            if isinstance(val, str):
                try:
                    data[field] = json.loads(val)
                except (json.JSONDecodeError, TypeError):
                    data[field] = []
        return data
```

- [ ] **Step 2: Write failing test (add to `tests/test_papers_router.py`)**

```python
from paperlibrary.schemas.paper import PaperResponse
import json


def test_paper_response_parses_json_columns(db_session):
    from paperlibrary.models.paper import Paper
    from datetime import UTC, datetime

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
```

- [ ] **Step 3: Run test**

```bash
pytest tests/test_papers_router.py::test_paper_response_parses_json_columns -v
```
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add paperlibrary/schemas/paper.py tests/test_papers_router.py
git commit -m "feat(schemas): PaperResponse with JSON column deserialization"
```

---

## Task 6: Text Extractor

**Files:**
- Create: `paperlibrary/services/extractor.py`
- Create: `tests/test_extractor.py`

- [ ] **Step 1: Write failing tests in `tests/test_extractor.py`**

```python
import pytest
import fitz  # PyMuPDF
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
    doc.new_page()  # blank page — no text
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
    # Abstract section should appear before Introduction
    assert text.index("Abstract") < text.index("Introduction")


def test_extract_text_empty_pdf_returns_empty(empty_pdf: Path):
    text = extract_text(empty_pdf)
    assert text.strip() == ""


def test_extract_text_respects_max_chars(pdf_with_abstract: Path):
    text = extract_text(pdf_with_abstract, max_chars=10)
    assert len(text) <= 10
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_extractor.py -v
```
Expected: FAIL — `ModuleNotFoundError: paperlibrary.services.extractor`

- [ ] **Step 3: Write `paperlibrary/services/extractor.py`**

```python
from pathlib import Path

import fitz  # PyMuPDF


def extract_text(
    pdf_path: Path,
    max_pages: int = 6,
    max_chars: int = 6000,
) -> str:
    doc = fitz.open(str(pdf_path))
    pages_to_read = min(max_pages, len(doc))

    raw = ""
    for i in range(pages_to_read):
        raw += doc[i].get_text()
    doc.close()

    if not raw.strip():
        return ""

    # Move abstract section to front so LLM gets it first
    lower = raw.lower()
    idx = lower.find("abstract")
    if idx > 0:
        raw = raw[idx:] + "\n" + raw[:idx]

    return raw[:max_chars]
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_extractor.py -v
```
Expected: all 4 PASS

- [ ] **Step 5: Commit**

```bash
git add paperlibrary/services/extractor.py tests/test_extractor.py
git commit -m "feat(services): PyMuPDF text extractor with abstract-first ordering"
```

---

## Task 7: LLM Analyzer

**Files:**
- Create: `paperlibrary/services/analyzer.py`
- Create: `tests/test_analyzer.py`

- [ ] **Step 1: Write failing tests in `tests/test_analyzer.py`**

```python
import json
import pytest
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
def seeded_db(tmp_path: Path, pdf_with_abstract):
    """DB with one pending paper pointing at the test PDF."""
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


# Reuse pdf_with_abstract fixture from test_extractor via conftest
@pytest.fixture
def pdf_with_abstract(tmp_path: Path):
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 100), "Abstract\n\nThis paper proposes a new method.")
    path = tmp_path / "paper.pdf"
    doc.save(str(path))
    doc.close()
    return path


@pytest.mark.asyncio
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


@pytest.mark.asyncio
async def test_analyze_llm_failure_sets_failed(tmp_path, seeded_db):
    settings = Settings(storage_path=tmp_path, llm_api_key="test")
    analyzer = Analyzer(settings, seeded_db)

    with patch.object(analyzer, "call_llm", new=AsyncMock(side_effect=RuntimeError("API error"))):
        await analyzer.analyze("p1", "attention.pdf", str(tmp_path / "paper.pdf"))

    with seeded_db() as s:
        paper = s.get(Paper, "p1")
    assert paper.analysis_status == "failed"
    assert "API error" in paper.error_message


@pytest.mark.asyncio
async def test_analyze_empty_pdf_sets_failed(tmp_path, seeded_db):
    """Scanned / empty PDF should set failed without calling LLM."""
    import fitz
    blank = tmp_path / "blank.pdf"
    doc = fitz.open()
    doc.new_page()
    doc.save(str(blank))
    doc.close()

    # Insert a paper pointing at the blank PDF
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
```

- [ ] **Step 2: Add `asyncio_mode` to `pyproject.toml`**

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

- [ ] **Step 3: Run tests to verify failure**

```bash
pytest tests/test_analyzer.py -v
```
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 4: Write `paperlibrary/services/analyzer.py`**

```python
import asyncio
import json
from datetime import UTC, datetime

from sqlalchemy.orm import sessionmaker, Session

from paperlibrary.core.config import Settings
from paperlibrary.models.paper import Paper
from paperlibrary.services.extractor import extract_text

SYSTEM_PROMPT = (
    "You are a precise academic paper metadata extractor. "
    "Given text from the first pages of a research paper, extract structured metadata. "
    "Respond with valid JSON only — no markdown fences, no explanation. "
    "Use null for missing strings/integers, [] for missing arrays."
)


def _user_prompt(filename: str, text: str) -> str:
    return f"""Filename: {filename}

--- Paper text ---
{text}
---

Return exactly this JSON:
{{
  "title": "Full paper title",
  "authors": ["Last, First"],
  "year": 2024,
  "venue": "Conference or Journal, Year",
  "abstract": "First ~500 chars of abstract",
  "topics": ["Tag1", "Tag2", "Tag3"],
  "keywords": ["kw1", "kw2"],
  "one_line_summary": "One sentence capturing the core idea (<=50 words)",
  "key_contributions": ["Contribution 1", "Contribution 2"],
  "methodology": "Empirical | Theoretical | Survey | System | Position",
  "citations": ["Author et al., Year. Title. Venue."]
}}"""


class Analyzer:
    def __init__(self, settings: Settings, session_factory: sessionmaker):
        self.settings = settings
        self.session_factory = session_factory

    async def call_llm(self, filename: str, text: str) -> dict:
        if self.settings.llm_provider == "anthropic":
            return await self._call_anthropic(filename, text)
        return await self._call_openai_compatible(filename, text)

    async def _call_anthropic(self, filename: str, text: str) -> dict:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=self.settings.llm_api_key)
        msg = await client.messages.create(
            model=self.settings.llm_model,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": _user_prompt(filename, text)}],
        )
        return json.loads(msg.content[0].text)

    async def _call_openai_compatible(self, filename: str, text: str) -> dict:
        import httpx
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self.settings.llm_base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.settings.llm_api_key}"},
                json={
                    "model": self.settings.llm_model,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": _user_prompt(filename, text)},
                    ],
                },
            )
            resp.raise_for_status()
            return json.loads(resp.json()["choices"][0]["message"]["content"])

    async def analyze(self, paper_id: str, filename: str, file_path: str) -> None:
        with self.session_factory() as session:
            await self._run(session, paper_id, filename, file_path)

    async def _run(self, session: Session, paper_id: str, filename: str, file_path: str) -> None:
        paper = session.get(Paper, paper_id)
        if paper is None:
            return

        paper.analysis_status = "running"
        session.commit()

        try:
            text = await asyncio.to_thread(
                extract_text, file_path,
                self.settings.extract_pages,
                self.settings.max_text_chars,
            )

            if not text.strip():
                paper.analysis_status = "failed"
                paper.error_message = "Scanned PDF — no extractable text"
                session.commit()
                return

            result = await self.call_llm(filename, text)

            paper.analysis_status = "done"
            paper.analyzed_at = datetime.now(UTC).isoformat()
            paper.title = result.get("title")
            paper.authors = json.dumps(result.get("authors") or [])
            paper.year = result.get("year")
            paper.venue = result.get("venue")
            paper.abstract = result.get("abstract")
            paper.topics = json.dumps(result.get("topics") or [])
            paper.keywords = json.dumps(result.get("keywords") or [])
            paper.one_line_summary = result.get("one_line_summary")
            paper.key_contributions = json.dumps(result.get("key_contributions") or [])
            paper.methodology = result.get("methodology")
            paper.citations = json.dumps(result.get("citations") or [])
            session.commit()

        except json.JSONDecodeError as exc:
            paper.analysis_status = "failed"
            paper.error_message = f"LLM returned invalid JSON: {exc}"
            session.commit()
        except Exception as exc:
            paper.analysis_status = "failed"
            paper.error_message = str(exc)
            session.commit()
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/test_analyzer.py -v
```
Expected: all 3 PASS

- [ ] **Step 6: Commit**

```bash
git add paperlibrary/services/analyzer.py tests/test_analyzer.py pyproject.toml
git commit -m "feat(services): LLM analyzer — extract, call, parse, persist"
```

---

## Task 8: FastAPI Dependencies

**Files:**
- Create: `paperlibrary/api/deps.py`

- [ ] **Step 1: Write `paperlibrary/api/deps.py`**

```python
from functools import lru_cache

from fastapi import Depends
from sqlalchemy.orm import Session, sessionmaker

from paperlibrary.core.config import Settings, get_settings
from paperlibrary.core.database import init_db
from paperlibrary.core.storage import ensure_storage
from paperlibrary.services.analyzer import Analyzer


@lru_cache(maxsize=4)
def _session_factory(db_path_str: str) -> sessionmaker:
    from pathlib import Path
    return init_db(Path(db_path_str))


def get_session_factory(settings: Settings = Depends(get_settings)) -> sessionmaker:
    ensure_storage(settings.storage_path)
    db_path = settings.storage_path / "papers.db"
    return _session_factory(str(db_path))


def get_db(factory: sessionmaker = Depends(get_session_factory)):
    with factory() as session:
        yield session


def get_analyzer(
    settings: Settings = Depends(get_settings),
    factory: sessionmaker = Depends(get_session_factory),
) -> Analyzer:
    return Analyzer(settings, factory)
```

- [ ] **Step 2: Verify import**

```bash
python -c "from paperlibrary.api.deps import get_db, get_analyzer; print('OK')"
```
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add paperlibrary/api/deps.py
git commit -m "feat(api): dependency injection — db session, analyzer"
```

---

## Task 9: Papers Router + Health Endpoint

**Files:**
- Create: `paperlibrary/api/routers/papers.py`
- Create: `paperlibrary/api/routers/health.py`

- [ ] **Step 1: Write failing API tests in `tests/test_papers_router.py`**

Add these tests (keep the existing model/schema tests at the top):

```python
import io
import pytest
import fitz
from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from paperlibrary.api.main import create_app
from paperlibrary.api.deps import get_settings, get_session_factory, get_db, get_analyzer
from paperlibrary.core.config import Settings
from paperlibrary.core.database import init_db
from paperlibrary.services.analyzer import Analyzer


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

    def override_settings():
        return tmp_settings

    def override_factory():
        return session_factory

    def override_db():
        with session_factory() as s:
            yield s

    def override_analyzer():
        return Analyzer(tmp_settings, session_factory)

    app.dependency_overrides[get_settings] = override_settings
    app.dependency_overrides[get_session_factory] = override_factory
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_analyzer] = override_analyzer

    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


def test_health(api_client):
    resp = api_client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


def test_upload_pdf_returns_pending(api_client, tiny_pdf_bytes):
    with patch("paperlibrary.api.routers.papers.Analyzer.analyze", new=AsyncMock()):
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
    with patch("paperlibrary.api.routers.papers.Analyzer.analyze", new=AsyncMock()):
        api_client.post(
            "/api/papers/upload",
            files={"file": ("paper.pdf", tiny_pdf_bytes, "application/pdf")},
        )
    resp = api_client.get("/api/papers")
    assert len(resp.json()) == 1


def test_delete_paper(api_client, tiny_pdf_bytes):
    with patch("paperlibrary.api.routers.papers.Analyzer.analyze", new=AsyncMock()):
        upload = api_client.post(
            "/api/papers/upload",
            files={"file": ("paper.pdf", tiny_pdf_bytes, "application/pdf")},
        )
    paper_id = upload.json()["paper_id"]

    del_resp = api_client.delete(f"/api/papers/{paper_id}")
    assert del_resp.status_code == 204

    get_resp = api_client.get(f"/api/papers/{paper_id}")
    assert get_resp.status_code == 404
```

- [ ] **Step 2: Run to confirm failure**

```bash
pytest tests/test_papers_router.py -k "test_health or test_upload or test_list or test_delete" -v
```
Expected: FAIL — `ModuleNotFoundError: paperlibrary.api.main`

- [ ] **Step 3: Write `paperlibrary/api/routers/health.py`**

```python
from fastapi import APIRouter, Depends
from paperlibrary.core.config import Settings, get_settings

router = APIRouter()


@router.get("/health")
def health(settings: Settings = Depends(get_settings)) -> dict:
    return {
        "status": "ok",
        "db": "ok",
        "llm_configured": bool(settings.llm_api_key),
    }
```

- [ ] **Step 4: Write `paperlibrary/api/routers/papers.py`**

```python
import uuid
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, File
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from paperlibrary.api.deps import get_db, get_analyzer, get_session_factory, get_settings
from paperlibrary.core.config import Settings
from paperlibrary.core.storage import pdf_path, ensure_storage
from paperlibrary.models.paper import Paper
from paperlibrary.schemas.paper import PaperResponse
from paperlibrary.services.analyzer import Analyzer

router = APIRouter()


@router.post("/upload", status_code=201, response_model=PaperResponse)
async def upload_paper(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
    analyzer: Analyzer = Depends(get_analyzer),
) -> PaperResponse:
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    ensure_storage(settings.storage_path)
    paper_id = uuid.uuid4().hex
    dest = pdf_path(settings.storage_path, paper_id)
    dest.parent.mkdir(parents=True, exist_ok=True)

    content = await file.read()
    dest.write_bytes(content)

    paper = Paper(
        paper_id=paper_id,
        filename=file.filename,
        file_path=str(dest),
        analysis_status="pending",
        created_at=datetime.now(UTC).isoformat(),
    )
    db.add(paper)
    db.commit()
    db.refresh(paper)

    background_tasks.add_task(
        analyzer.analyze, paper_id, file.filename, str(dest)
    )

    return PaperResponse.model_validate(paper)


@router.get("", response_model=list[PaperResponse])
def list_papers(
    topic: str | None = None,
    year: int | None = None,
    methodology: str | None = None,
    status: str | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
) -> list[Paper]:
    stmt = select(Paper)
    if status:
        stmt = stmt.where(Paper.analysis_status == status)
    if year:
        stmt = stmt.where(Paper.year == year)
    if methodology:
        stmt = stmt.where(Paper.methodology == methodology)
    if topic:
        stmt = stmt.where(Paper.topics.like(f'%"{topic}"%'))
    if q:
        pattern = f"%{q.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Paper.title).like(pattern),
                func.lower(Paper.one_line_summary).like(pattern),
            )
        )
    return list(db.execute(stmt).scalars().all())


@router.get("/{paper_id}", response_model=PaperResponse)
def get_paper(paper_id: str, db: Session = Depends(get_db)) -> Paper:
    paper = db.get(Paper, paper_id)
    if paper is None:
        raise HTTPException(status_code=404, detail="Paper not found.")
    return paper


@router.delete("/{paper_id}", status_code=204)
def delete_paper(paper_id: str, db: Session = Depends(get_db)) -> None:
    paper = db.get(Paper, paper_id)
    if paper is None:
        raise HTTPException(status_code=404, detail="Paper not found.")
    Path(paper.file_path).unlink(missing_ok=True)
    db.delete(paper)
    db.commit()


@router.post("/{paper_id}/analyze", status_code=202)
async def retrigger_analysis(
    paper_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    analyzer: Analyzer = Depends(get_analyzer),
) -> dict:
    paper = db.get(Paper, paper_id)
    if paper is None:
        raise HTTPException(status_code=404, detail="Paper not found.")

    paper.analysis_status = "pending"
    paper.error_message = None
    db.commit()

    background_tasks.add_task(
        analyzer.analyze, paper_id, paper.filename, paper.file_path
    )
    return {"paper_id": paper_id, "analysis_status": "pending"}
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/test_papers_router.py -v
```
Expected: FAIL until `create_app` exists (next task). Note the import errors.

- [ ] **Step 6: Commit routers (app wiring in next task)**

```bash
git add paperlibrary/api/routers/papers.py paperlibrary/api/routers/health.py
git commit -m "feat(api): papers router (upload/list/detail/delete/re-analyze) + health endpoint"
```

---

## Task 10: FastAPI App + Entry Point

**Files:**
- Create: `paperlibrary/api/main.py`
- Create: `paperlibrary/__main__.py`

- [ ] **Step 1: Write `paperlibrary/api/main.py`**

```python
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from paperlibrary.api.routers import health, papers

STATIC_DIR = Path(__file__).parent.parent / "static"


def create_app() -> FastAPI:
    app = FastAPI(title="paperlibrary", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router, prefix="/api", tags=["health"])
    app.include_router(papers.router, prefix="/api/papers", tags=["papers"])

    if STATIC_DIR.exists():
        app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")

    return app


app = create_app()
```

- [ ] **Step 2: Write `paperlibrary/__main__.py`**

```python
import uvicorn
from paperlibrary.core.config import get_settings


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "paperlibrary.api.main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Run all tests**

```bash
pytest tests/ -v
```
Expected: all tests PASS

- [ ] **Step 4: Smoke-test the server (no frontend yet)**

```bash
python -m paperlibrary &
sleep 2
curl http://localhost:8000/api/health
# kill %1
```
Expected:
```json
{"status":"ok","db":"ok","llm_configured":false}
```

- [ ] **Step 5: Commit**

```bash
git add paperlibrary/api/main.py paperlibrary/__main__.py
git commit -m "feat(api): FastAPI app factory + uvicorn entry point"
```

**Changelog entry (add to `CHANGELOG.md`):**
```markdown
## [0.1.0] — 2026-05-25

### Added
- FastAPI backend with SQLite storage via SQLAlchemy ORM
- PDF upload endpoint: `POST /api/papers/upload` (background LLM analysis)
- Paper list with filters: `GET /api/papers?topic=&year=&status=&q=`
- Paper detail: `GET /api/papers/{id}`
- Paper delete: `DELETE /api/papers/{id}`
- Re-trigger analysis: `POST /api/papers/{id}/analyze`
- Health check: `GET /api/health`
- LLM support: Anthropic (`claude-haiku-4-5`) and OpenAI-compatible endpoints
- Text extraction via PyMuPDF (abstract-first ordering, configurable page/char limits)
```

- [ ] **Step 6: Commit changelog**

```bash
git add CHANGELOG.md
git commit -m "chore: add CHANGELOG for v0.1.0 backend"
```

---

## Task 11: Frontend HTML + CSS

**Files:**
- Create: `paperlibrary/static/index.html`
- Create: `paperlibrary/static/style.css`

- [ ] **Step 1: Write `paperlibrary/static/index.html`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>paperlibrary</title>
  <link rel="stylesheet" href="/style.css" />
</head>
<body>
  <header class="topbar">
    <span class="brand">📚 paperlibrary</span>
    <div class="topbar-right">
      <label class="upload-btn">
        Upload PDF
        <input type="file" id="file-input" accept=".pdf" hidden />
      </label>
      <input type="search" id="search-input" class="search-box" placeholder="Search title or summary…" />
    </div>
  </header>

  <div class="filter-bar">
    <select id="filter-topic"><option value="">All topics</option></select>
    <select id="filter-year"><option value="">All years</option></select>
    <select id="filter-method"><option value="">All methods</option></select>
    <select id="filter-status">
      <option value="">All status</option>
      <option value="done">Done</option>
      <option value="pending">Pending</option>
      <option value="running">Analyzing</option>
      <option value="failed">Failed</option>
    </select>
  </div>

  <main id="paper-grid" class="paper-grid"></main>

  <!-- Detail modal -->
  <div id="modal-overlay" class="modal-overlay hidden">
    <div class="modal" id="modal">
      <button class="modal-close" id="modal-close">✕</button>
      <div id="modal-content"></div>
    </div>
  </div>

  <script src="/app.js"></script>
</body>
</html>
```

- [ ] **Step 2: Write `paperlibrary/static/style.css`**

```css
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  background: #f5f5f5;
  color: #1a1a1a;
  min-height: 100vh;
}

/* ── Topbar ── */
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1.5rem;
  background: #fff;
  border-bottom: 1px solid #e0e0e0;
  position: sticky;
  top: 0;
  z-index: 10;
}
.brand { font-size: 1.1rem; font-weight: 600; }
.topbar-right { display: flex; gap: 0.75rem; align-items: center; }

.upload-btn {
  background: #2563eb;
  color: #fff;
  padding: 0.4rem 1rem;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.875rem;
  user-select: none;
}
.upload-btn:hover { background: #1d4ed8; }

.search-box {
  padding: 0.4rem 0.75rem;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 0.875rem;
  width: 220px;
  outline: none;
}
.search-box:focus { border-color: #2563eb; }

/* ── Filter bar ── */
.filter-bar {
  display: flex;
  gap: 0.5rem;
  padding: 0.6rem 1.5rem;
  background: #fff;
  border-bottom: 1px solid #e0e0e0;
  flex-wrap: wrap;
}
.filter-bar select {
  padding: 0.3rem 0.6rem;
  border: 1px solid #d1d5db;
  border-radius: 5px;
  font-size: 0.8rem;
  cursor: pointer;
  background: #fff;
}

/* ── Paper grid ── */
.paper-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1rem;
  padding: 1.25rem 1.5rem;
}

/* ── Paper card ── */
.paper-card {
  background: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 10px;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  transition: box-shadow 0.15s;
}
.paper-card:hover { box-shadow: 0 2px 12px rgba(0,0,0,0.08); }

.card-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 0.5rem; }
.card-title { font-size: 0.95rem; font-weight: 600; line-height: 1.3; }
.card-year { font-size: 0.8rem; color: #6b7280; white-space: nowrap; }

.card-authors, .card-venue { font-size: 0.78rem; color: #6b7280; }
.card-summary { font-size: 0.85rem; color: #374151; font-style: italic; line-height: 1.5; }

/* Status badges */
.badge {
  display: inline-block;
  font-size: 0.7rem;
  font-weight: 600;
  padding: 0.15rem 0.5rem;
  border-radius: 999px;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}
.badge--done    { background: #d1fae5; color: #065f46; }
.badge--pending { background: #fef3c7; color: #92400e; }
.badge--running { background: #dbeafe; color: #1e40af; }
.badge--failed  { background: #fee2e2; color: #991b1b; }

/* Topic chips */
.chip-list { display: flex; flex-wrap: wrap; gap: 0.3rem; }
.chip {
  background: #eff6ff;
  color: #1d4ed8;
  font-size: 0.72rem;
  padding: 0.15rem 0.5rem;
  border-radius: 999px;
  cursor: pointer;
}
.chip:hover { background: #dbeafe; }

/* Card actions */
.card-actions { display: flex; gap: 0.4rem; margin-top: auto; padding-top: 0.5rem; }
.btn { padding: 0.3rem 0.75rem; border-radius: 5px; font-size: 0.78rem; cursor: pointer; border: none; }
.btn--primary { background: #2563eb; color: #fff; }
.btn--primary:hover { background: #1d4ed8; }
.btn--danger  { background: #fee2e2; color: #991b1b; }
.btn--danger:hover  { background: #fecaca; }
.btn--subtle  { background: #f3f4f6; color: #374151; }
.btn--subtle:hover  { background: #e5e7eb; }

/* Skeleton / loading */
.skeleton {
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: shimmer 1.4s infinite;
  border-radius: 4px;
  height: 1em;
}
@keyframes shimmer { 0% { background-position: 200% 0 } 100% { background-position: -200% 0 } }

/* ── Modal ── */
.modal-overlay {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.45);
  display: flex; align-items: center; justify-content: center;
  z-index: 100;
}
.modal-overlay.hidden { display: none; }
.modal {
  background: #fff;
  border-radius: 12px;
  padding: 1.5rem;
  max-width: 640px;
  width: 90%;
  max-height: 85vh;
  overflow-y: auto;
  position: relative;
}
.modal-close {
  position: absolute; top: 1rem; right: 1rem;
  background: none; border: none; font-size: 1.1rem; cursor: pointer; color: #6b7280;
}
.modal h2 { font-size: 1.05rem; margin-bottom: 0.5rem; }
.modal .section { margin-top: 1rem; }
.modal .section-title { font-size: 0.75rem; font-weight: 600; text-transform: uppercase; color: #6b7280; margin-bottom: 0.3rem; }
.modal ul { padding-left: 1.2rem; font-size: 0.85rem; line-height: 1.7; }
.modal .abstract-text { font-size: 0.85rem; line-height: 1.7; color: #374151; }

details summary { cursor: pointer; font-size: 0.78rem; color: #2563eb; }
```

- [ ] **Step 3: Verify static files are served**

Start the server and check:

```bash
python -m paperlibrary &
curl -s http://localhost:8000/ | grep "paperlibrary"
# kill %1
```
Expected: HTML response containing `paperlibrary`

- [ ] **Step 4: Commit**

```bash
git add paperlibrary/static/index.html paperlibrary/static/style.css
git commit -m "feat(frontend): HTML layout and CSS — cards, filters, modal, badges"
```

---

## Task 12: Frontend JavaScript

**Files:**
- Create: `paperlibrary/static/app.js`

- [ ] **Step 1: Write `paperlibrary/static/app.js`**

```javascript
const API = "/api/papers";

// ── State ──────────────────────────────────────────────────────────────────
let papers = [];
let activeFilters = { topic: "", year: "", method: "", status: "", q: "" };
const pollingIds = new Map(); // paper_id → intervalId

// ── Bootstrap ──────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  loadPapers();

  document.getElementById("file-input").addEventListener("change", onFileSelect);
  document.getElementById("search-input").addEventListener("input", (e) => {
    activeFilters.q = e.target.value.trim();
    renderGrid();
  });
  document.getElementById("filter-topic").addEventListener("change", (e) => {
    activeFilters.topic = e.target.value;
    renderGrid();
  });
  document.getElementById("filter-year").addEventListener("change", (e) => {
    activeFilters.year = e.target.value;
    renderGrid();
  });
  document.getElementById("filter-method").addEventListener("change", (e) => {
    activeFilters.method = e.target.value;
    renderGrid();
  });
  document.getElementById("filter-status").addEventListener("change", (e) => {
    activeFilters.status = e.target.value;
    renderGrid();
  });
  document.getElementById("modal-close").addEventListener("click", closeModal);
  document.getElementById("modal-overlay").addEventListener("click", (e) => {
    if (e.target === document.getElementById("modal-overlay")) closeModal();
  });
});

// ── Data fetching ──────────────────────────────────────────────────────────
async function loadPapers() {
  const resp = await fetch(API);
  if (!resp.ok) return;
  papers = await resp.json();
  refreshFilters();
  renderGrid();
  papers
    .filter((p) => p.analysis_status === "pending" || p.analysis_status === "running")
    .forEach((p) => startPolling(p.paper_id));
}

async function fetchPaper(id) {
  const resp = await fetch(`${API}/${id}`);
  if (!resp.ok) return null;
  return resp.json();
}

// ── Upload ─────────────────────────────────────────────────────────────────
async function onFileSelect(e) {
  const file = e.target.files[0];
  if (!file) return;
  e.target.value = "";

  const form = new FormData();
  form.append("file", file);
  const resp = await fetch(`${API}/upload`, { method: "POST", body: form });
  if (!resp.ok) {
    alert("Upload failed: " + (await resp.text()));
    return;
  }
  const paper = await resp.json();
  papers.unshift(paper);
  refreshFilters();
  renderGrid();
  startPolling(paper.paper_id);
}

// ── Polling ────────────────────────────────────────────────────────────────
function startPolling(id) {
  if (pollingIds.has(id)) return;
  const intervalId = setInterval(async () => {
    const updated = await fetchPaper(id);
    if (!updated) return;
    const idx = papers.findIndex((p) => p.paper_id === id);
    if (idx !== -1) papers[idx] = updated;
    refreshFilters();
    renderGrid();
    if (updated.analysis_status === "done" || updated.analysis_status === "failed") {
      clearInterval(pollingIds.get(id));
      pollingIds.delete(id);
    }
  }, 3000);
  pollingIds.set(id, intervalId);
}

// ── Filters ────────────────────────────────────────────────────────────────
function refreshFilters() {
  const topics = [...new Set(papers.flatMap((p) => p.topics || []))].sort();
  const years = [...new Set(papers.map((p) => p.year).filter(Boolean))].sort((a, b) => b - a);
  const methods = [...new Set(papers.map((p) => p.methodology).filter(Boolean))].sort();

  populateSelect("filter-topic", topics, activeFilters.topic);
  populateSelect("filter-year", years.map(String), activeFilters.year);
  populateSelect("filter-method", methods, activeFilters.method);
}

function populateSelect(id, options, selected) {
  const el = document.getElementById(id);
  const first = el.options[0];
  el.innerHTML = "";
  el.appendChild(first);
  options.forEach((o) => {
    const opt = document.createElement("option");
    opt.value = o;
    opt.textContent = o;
    if (o === selected) opt.selected = true;
    el.appendChild(opt);
  });
}

function filteredPapers() {
  return papers.filter((p) => {
    if (activeFilters.status && p.analysis_status !== activeFilters.status) return false;
    if (activeFilters.year && String(p.year) !== activeFilters.year) return false;
    if (activeFilters.method && p.methodology !== activeFilters.method) return false;
    if (activeFilters.topic && !(p.topics || []).includes(activeFilters.topic)) return false;
    if (activeFilters.q) {
      const q = activeFilters.q.toLowerCase();
      const inTitle = (p.title || p.filename).toLowerCase().includes(q);
      const inSummary = (p.one_line_summary || "").toLowerCase().includes(q);
      if (!inTitle && !inSummary) return false;
    }
    return true;
  });
}

// ── Rendering ──────────────────────────────────────────────────────────────
function renderGrid() {
  const grid = document.getElementById("paper-grid");
  const visible = filteredPapers();

  if (visible.length === 0) {
    grid.innerHTML = `<p style="color:#6b7280;padding:2rem">No papers match the current filters.</p>`;
    return;
  }

  grid.innerHTML = visible.map(renderCard).join("");

  grid.querySelectorAll("[data-detail]").forEach((btn) => {
    btn.addEventListener("click", () => openModal(btn.dataset.detail));
  });
  grid.querySelectorAll("[data-delete]").forEach((btn) => {
    btn.addEventListener("click", () => deletePaper(btn.dataset.delete));
  });
  grid.querySelectorAll("[data-reanalyze]").forEach((btn) => {
    btn.addEventListener("click", () => reanalyze(btn.dataset.reanalyze));
  });
  grid.querySelectorAll("[data-filter-topic]").forEach((chip) => {
    chip.addEventListener("click", () => {
      activeFilters.topic = chip.dataset.filterTopic;
      document.getElementById("filter-topic").value = chip.dataset.filterTopic;
      renderGrid();
    });
  });
}

function renderCard(p) {
  const status = p.analysis_status;
  const title = p.title || p.filename;
  const authors = (p.authors || []).slice(0, 2).join("; ") + (p.authors?.length > 2 ? " et al." : "");
  const chips = (p.topics || [])
    .map((t) => `<span class="chip" data-filter-topic="${t}">${t}</span>`)
    .join("");

  if (status === "pending" || status === "running") {
    return `
    <div class="paper-card">
      <div class="card-header">
        <span class="badge badge--${status}">${status === "running" ? "Analyzing…" : "Pending"}</span>
      </div>
      <div class="card-title">${esc(p.filename)}</div>
      <div class="skeleton" style="height:0.75em;width:60%"></div>
      <div class="skeleton" style="height:0.75em;width:80%"></div>
    </div>`;
  }

  if (status === "failed") {
    return `
    <div class="paper-card">
      <div class="card-header">
        <span class="badge badge--failed">Failed</span>
      </div>
      <div class="card-title">${esc(p.filename)}</div>
      <div style="font-size:0.78rem;color:#991b1b">${esc(p.error_message || "Analysis failed")}</div>
      <div class="card-actions">
        <button class="btn btn--subtle" data-reanalyze="${p.paper_id}">Retry</button>
        <button class="btn btn--danger"  data-delete="${p.paper_id}">Delete</button>
      </div>
    </div>`;
  }

  return `
  <div class="paper-card">
    <div class="card-header">
      <span class="card-title">${esc(title)}</span>
      <span class="card-year">${p.year || ""}</span>
    </div>
    <div class="badge badge--done">Done</div>
    ${authors ? `<div class="card-authors">${esc(authors)}</div>` : ""}
    ${p.venue ? `<div class="card-venue">${esc(p.venue)}</div>` : ""}
    ${p.one_line_summary ? `<div class="card-summary">"${esc(p.one_line_summary)}"</div>` : ""}
    <div class="chip-list">${chips}</div>
    <div class="card-actions">
      <button class="btn btn--primary" data-detail="${p.paper_id}">Details</button>
      <button class="btn btn--danger"  data-delete="${p.paper_id}">Delete</button>
    </div>
  </div>`;
}

// ── Modal ──────────────────────────────────────────────────────────────────
function openModal(paperId) {
  const p = papers.find((x) => x.paper_id === paperId);
  if (!p) return;

  const contributions = (p.key_contributions || [])
    .map((c) => `<li>${esc(c)}</li>`)
    .join("");
  const citationList = (p.citations || [])
    .map((c) => `<li>${esc(c)}</li>`)
    .join("");

  document.getElementById("modal-content").innerHTML = `
    <h2>${esc(p.title || p.filename)}</h2>
    <div style="font-size:0.82rem;color:#6b7280;margin-bottom:0.5rem">
      ${esc((p.authors || []).join(", "))}
      ${p.year ? `· ${p.year}` : ""}
      ${p.venue ? `· ${esc(p.venue)}` : ""}
      ${p.methodology ? `· ${esc(p.methodology)}` : ""}
    </div>
    <div class="chip-list">${(p.topics || []).map((t) => `<span class="chip">${esc(t)}</span>`).join("")}</div>
    ${p.abstract ? `
    <div class="section">
      <div class="section-title">Abstract</div>
      <p class="abstract-text">${esc(p.abstract)}</p>
    </div>` : ""}
    ${contributions ? `
    <div class="section">
      <div class="section-title">Key Contributions</div>
      <ul>${contributions}</ul>
    </div>` : ""}
    ${citationList ? `
    <div class="section">
      <details>
        <summary>References (${p.citations.length})</summary>
        <ul style="margin-top:0.5rem">${citationList}</ul>
      </details>
    </div>` : ""}
  `;

  document.getElementById("modal-overlay").classList.remove("hidden");
}

function closeModal() {
  document.getElementById("modal-overlay").classList.add("hidden");
}

// ── Actions ────────────────────────────────────────────────────────────────
async function deletePaper(id) {
  if (!confirm("Delete this paper?")) return;
  const resp = await fetch(`${API}/${id}`, { method: "DELETE" });
  if (resp.ok) {
    papers = papers.filter((p) => p.paper_id !== id);
    refreshFilters();
    renderGrid();
  }
}

async function reanalyze(id) {
  await fetch(`${API}/${id}/analyze`, { method: "POST" });
  const updated = await fetchPaper(id);
  if (updated) {
    const idx = papers.findIndex((p) => p.paper_id === id);
    if (idx !== -1) papers[idx] = updated;
    renderGrid();
    startPolling(id);
  }
}

// ── Helpers ────────────────────────────────────────────────────────────────
function esc(str) {
  return String(str ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
```

- [ ] **Step 2: Manual smoke test**

```bash
python -m paperlibrary
```
Open `http://localhost:8000` in a browser.
- Page loads with "Upload PDF" button and empty grid.
- Upload any PDF → card appears with "Pending" badge and skeleton.
- After analysis completes → card shows title, authors, topics, summary.
- Click "Details" → modal opens with abstract, contributions, citations.
- Topic chip click → filter activates.
- Delete button → card removed.

- [ ] **Step 3: Commit**

```bash
git add paperlibrary/static/app.js
git commit -m "feat(frontend): paper grid, upload, polling, filters, detail modal"
```

**Changelog entry (add to `CHANGELOG.md`):**
```markdown
### Added (continued)
- Browser UI served at http://localhost:8000
- Paper cards with title, authors, year, venue, one-line summary, topic chips
- Auto-polling: cards update when background analysis completes (no refresh needed)
- Filter by topic, year, methodology, status; full-text search on title/summary
- Detail modal: abstract, key contributions, collapsible citations list
- Re-analyze button for failed papers
```

- [ ] **Step 4: Commit changelog**

```bash
git add CHANGELOG.md
git commit -m "chore: update CHANGELOG for frontend"
```

---

## Task 13: README

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write `README.md`**

```markdown
# paperlibrary

A local web app that turns a folder of PDFs into a structured, searchable paper library.
Upload PDFs → an LLM extracts title, authors, topics, summary, and citations → browse in your browser.

## Requirements

- Python 3.11+
- An API key for Anthropic or any OpenAI-compatible provider

## Install

```bash
git clone https://github.com/miles031104/paperlibrary
cd paperlibrary
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and set your API key:

```ini
PAPERLIBRARY_LLM_PROVIDER=anthropic
PAPERLIBRARY_LLM_API_KEY=sk-ant-...
PAPERLIBRARY_LLM_MODEL=claude-haiku-4-5
```

## Run

```bash
python -m paperlibrary
```

Open **http://localhost:8000** in your browser.

## Configuration

| Variable | Default | Description |
|---|---|---|
| `PAPERLIBRARY_LLM_PROVIDER` | `anthropic` | `anthropic` or `openai-compatible` |
| `PAPERLIBRARY_LLM_API_KEY` | — | Your API key |
| `PAPERLIBRARY_LLM_MODEL` | `claude-haiku-4-5` | Model name |
| `PAPERLIBRARY_LLM_BASE_URL` | — | Base URL (openai-compatible only) |
| `PAPERLIBRARY_STORAGE_PATH` | `./storage` | Where to store DB and PDFs |
| `PAPERLIBRARY_PORT` | `8000` | Server port |
| `PAPERLIBRARY_EXTRACT_PAGES` | `6` | Pages to extract per PDF |
| `PAPERLIBRARY_MAX_TEXT_CHARS` | `6000` | Max characters fed to LLM |

## Tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

## Integration with papermemory

See `docs/papermemory-integration.md`.
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: README with install, config, and usage instructions"
```

---

## Task 14: Push to GitHub

- [ ] **Step 1: Create the GitHub repo**

Go to https://github.com/new and create `miles031104/paperlibrary` (empty, no README).

- [ ] **Step 2: Push**

```bash
git remote add origin https://github.com/miles031104/paperlibrary.git
git branch -M main
git push -u origin main
```

- [ ] **Step 3: Verify**

Open https://github.com/miles031104/paperlibrary — confirm all files and the CHANGELOG are visible.

---

## Self-Review Checklist

**Spec coverage:**
- ✅ PDF upload → background analysis
- ✅ SQLite with all fields from spec (Section 3)
- ✅ All 6 API endpoints (Section 4)
- ✅ Filters: topic, year, methodology, status, q (Section 4)
- ✅ Frontend layout matching spec wireframe (Section 5)
- ✅ Detail modal: abstract, key contributions, citations (Section 5)
- ✅ Both LLM providers (Section 6)
- ✅ All `.env` config vars (Section 6)
- ✅ Scanned PDF → `failed` with message (Section 6)
- ✅ Re-analyze button for failed papers (Section 5)
- ✅ papermemory integration path mentioned in README (Section 7)
- ✅ 3-phase acceptance criteria covered by tasks 1–13

**No placeholders:** All code blocks are complete.

**Type consistency:** `PaperResponse` used throughout; `Analyzer.analyze(paper_id, filename, file_path)` signature consistent across deps, router, and tests.
