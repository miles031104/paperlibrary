# paperlibrary — Design Spec

> Version: v1.0 · 2026-05-25
> Status: Approved for implementation

---

## 1. Overview

paperlibrary is a standalone local application for managing an academic paper library.
Users upload PDFs; an LLM automatically extracts structured metadata in the background.
The browser UI displays an organized library: title, authors, year, venue, topic tags,
one-line summary, key contributions, and citations.

**Non-goals:**
- No user↔model conversation (no chat interface)
- No vector search / RAG retrieval (that stays in papermemory)
- No cloud deployment required

**Installation target:**
```
git clone https://github.com/miles031104/paperlibrary
pip install -r requirements.txt
cp .env.example .env   # fill in LLM API key
python -m paperlibrary
# → open http://localhost:8000
```

---

## 2. Architecture

```
paperlibrary/
├── paperlibrary/
│   ├── __main__.py              ← python -m paperlibrary entry point
│   ├── api/
│   │   ├── main.py              ← FastAPI app, mounts static files
│   │   ├── routers/
│   │   │   ├── papers.py        ← upload, list, detail, delete
│   │   │   └── analysis.py      ← trigger analysis, get status
│   │   └── deps.py              ← dependency injection (DB, LLM client)
│   ├── core/
│   │   ├── config.py            ← .env settings (LLM key, model, storage path)
│   │   ├── database.py          ← SQLite connection + table init (SQLAlchemy)
│   │   └── storage.py           ← PDF file path management
│   ├── models/
│   │   └── paper.py             ← SQLAlchemy ORM model
│   ├── schemas/
│   │   └── paper.py             ← Pydantic request/response models
│   ├── services/
│   │   ├── analyzer.py          ← LLM analysis: extract → prompt → parse → save
│   │   └── extractor.py         ← PyMuPDF text extraction (first N pages)
│   └── static/
│       ├── index.html           ← single-page frontend
│       ├── style.css
│       └── app.js
├── storage/                     ← created at runtime
│   ├── papers.db                ← SQLite database
│   └── pdfs/                    ← uploaded PDF files
├── .env.example
├── requirements.txt
└── README.md
```

**Data flow:**
1. User uploads PDF → `POST /papers/upload`
2. FastAPI saves file to `storage/pdfs/{paper_id}.pdf`, inserts DB row (`analysis_status=pending`), returns immediately
3. `asyncio.create_task` launches `analyzer.analyze(paper_id)` in the background
4. Analyzer: extracts text via PyMuPDF → builds prompt → calls LLM → parses JSON → updates DB row (`analysis_status=done`)
5. Frontend polls `GET /papers/{id}` every 3 seconds until `analysis_status=done`, then refreshes the card

---

## 3. Data Model

Single `papers` table in SQLite, managed via SQLAlchemy ORM.

```sql
CREATE TABLE papers (
    -- identity
    paper_id        TEXT PRIMARY KEY,          -- UUID hex
    filename        TEXT NOT NULL,             -- original upload filename
    file_path       TEXT NOT NULL,             -- absolute path to stored PDF

    -- pipeline status
    analysis_status TEXT NOT NULL DEFAULT 'pending',
    -- values: pending | running | done | failed
    error_message   TEXT,

    -- timestamps
    created_at      TEXT NOT NULL,             -- ISO 8601 UTC
    analyzed_at     TEXT,                      -- ISO 8601 UTC, null until done

    -- LLM-extracted metadata
    title           TEXT,
    authors         TEXT,    -- JSON array: ["Last, First", ...]
    year            INTEGER,
    venue           TEXT,                      -- journal or conference
    abstract        TEXT,                      -- first ~500 chars
    topics          TEXT,    -- JSON array: 3–5 topic tags
    keywords        TEXT,    -- JSON array: author-provided keywords
    one_line_summary TEXT,                     -- ≤50 words
    key_contributions TEXT,  -- JSON array: 2–4 bullet points
    methodology     TEXT,    -- Empirical | Theoretical | Survey | System | Position
    citations       TEXT     -- JSON array: extracted reference strings
);
```

JSON columns (`authors`, `topics`, `keywords`, `key_contributions`, `citations`) are stored
as JSON strings and serialized/deserialized in the schema layer. SQLite has no native array
type; this avoids a junction table while keeping queries simple.

---

## 4. API Endpoints

All endpoints are prefixed under `/api`. Frontend is served at `/`.

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/papers/upload` | Upload PDF; returns `paper_id` and `analysis_status=pending` |
| `GET` | `/api/papers` | List all papers; supports `?topic=`, `?year=`, `?methodology=`, `?q=`, `?status=` |
| `GET` | `/api/papers/{id}` | Single paper with full analysis |
| `DELETE` | `/api/papers/{id}` | Delete paper and its PDF file |
| `POST` | `/api/papers/{id}/analyze` | Re-trigger analysis (e.g. after failure) |
| `GET` | `/api/health` | `{"status": "ok", "db": "ok", "llm_configured": true}` |

**`GET /api/papers` query params:**
- `?topic=Transformer` — filter papers whose `topics` array contains this value
- `?year=2024` — exact year match
- `?methodology=Empirical` — methodology filter
- `?status=done` — analysis status filter (`pending|running|done|failed`)
- `?q=attention` — fuzzy search against `title` and `one_line_summary` (SQL `LIKE`)

**`POST /api/papers/upload` response:**
```json
{
  "paper_id": "abc123",
  "filename": "attention.pdf",
  "analysis_status": "pending",
  "created_at": "2026-05-25T10:00:00Z"
}
```

**`GET /api/papers/{id}` response (analysis done):**
```json
{
  "paper_id": "abc123",
  "filename": "attention.pdf",
  "analysis_status": "done",
  "analyzed_at": "2026-05-25T10:00:45Z",
  "title": "Attention Is All You Need",
  "authors": ["Vaswani, A.", "Shazeer, N."],
  "year": 2017,
  "venue": "NeurIPS 2017",
  "abstract": "We propose a novel...",
  "topics": ["Transformer", "Self-Attention", "NLP"],
  "keywords": ["neural machine translation", "attention"],
  "one_line_summary": "首个完全基于注意力机制的序列转换模型。",
  "key_contributions": ["Proposed Multi-Head Attention", "Introduced positional encoding"],
  "methodology": "Empirical",
  "citations": ["Bahdanau et al., 2015. Neural Machine Translation...", "..."]
}
```

---

## 5. Frontend Design

Single `index.html` page. No framework — HTML + CSS + vanilla JS (`fetch` API).
FastAPI serves it via `StaticFiles` mount at `/`.

**Layout:**

```
┌─────────────────────────────────────────────────────────┐
│  📚 paperlibrary          [Upload PDF]  [🔍 Search...]  │
├─────────────────────────────────────────────────────────┤
│  Filters: [All topics ▼] [All years ▼] [All methods ▼]  │
├──────────────────────────────────────────────────────────┤
│  ┌────────────────────┐  ┌────────────────────┐         │
│  │ [DONE] 2017        │  │ [ANALYZING...]     │         │
│  │ Attention Is All   │  │ filename.pdf       │         │
│  │ You Need           │  │                    │         │
│  │ Vaswani et al.     │  │ ⏳ Extracting...   │         │
│  │ NeurIPS 2017       │  └────────────────────┘         │
│  │                    │                                  │
│  │ "首个完全基于注意   │                                  │
│  │  力机制的模型..."   │                                  │
│  │                    │                                  │
│  │ [Transformer][NLP] │                                  │
│  │ [查看详情]  [🗑️]   │                                  │
│  └────────────────────┘                                  │
└─────────────────────────────────────────────────────────┘
```

**Detail modal** (click "查看详情"):
- Full metadata: title, authors, year, venue
- Abstract text
- Key contributions (bullet list)
- Topics + keywords chips
- Citations (collapsible list)
- Re-analyze button (for failed papers)

**Polling logic (app.js):**
- On load: fetch all papers, render cards
- For any paper with `analysis_status=pending|running`: poll that paper's endpoint every 3s
- On `done`/`failed`: stop polling, re-render card

---

## 6. LLM Integration

**Supported providers:**
- `anthropic` — Anthropic SDK (`anthropic` package), models: `claude-haiku-4-5`, `claude-sonnet-4-6`
- `openai-compatible` — `httpx` direct call to any OpenAI-compatible endpoint

**Configuration (`.env`):**
```ini
PAPERLIBRARY_LLM_PROVIDER=anthropic          # anthropic | openai-compatible
PAPERLIBRARY_LLM_API_KEY=sk-ant-...
PAPERLIBRARY_LLM_MODEL=claude-haiku-4-5      # lightweight = cheaper
PAPERLIBRARY_LLM_BASE_URL=                   # only for openai-compatible
PAPERLIBRARY_STORAGE_PATH=./storage          # where to store DB + PDFs
PAPERLIBRARY_MAX_TEXT_CHARS=6000
PAPERLIBRARY_EXTRACT_PAGES=6
```

**Text extraction strategy (`extractor.py`):**
1. Use PyMuPDF to extract text from first `EXTRACT_PAGES` pages
2. Look for "Abstract" keyword; if found, prioritize that section
3. Truncate to `MAX_TEXT_CHARS`
4. If extracted text is empty (scanned PDF): set `analysis_status=failed`, `error_message="Scanned PDF — no extractable text"`

**LLM prompt (system):**
```
You are a precise academic paper metadata extractor.
Given text from the first pages of a research paper, extract structured metadata.
Respond with valid JSON only — no markdown fences, no explanation.
Use null for missing strings/integers, [] for missing arrays.
```

**LLM prompt (user):**
```
Filename: {filename}

--- Paper text (first {N} pages) ---
{text}
---

Return exactly this JSON:
{
  "title": "...",
  "authors": ["Last, First", ...],
  "year": 2024,
  "venue": "Conference or Journal, Year",
  "abstract": "First ~500 chars of abstract",
  "topics": ["Tag1", "Tag2", "Tag3"],
  "keywords": ["kw1", "kw2"],
  "one_line_summary": "One sentence ≤50 words capturing the core idea",
  "key_contributions": ["Contribution 1", "Contribution 2"],
  "methodology": "Empirical | Theoretical | Survey | System | Position",
  "citations": ["Author et al., Year. Title. Venue.", ...]
}
```

**Failure handling:**
- LLM call fails → `analysis_status=failed`, log error
- JSON parse fails → attempt partial extraction, fall back to `failed`
- Empty text → `failed` with clear message
- All failures are non-fatal: the uploaded PDF remains accessible

---

## 7. Integration with papermemory

When papermemory wants to add this feature:

1. Copy `paperlibrary/` package into `apps/paperlibrary/`
2. In `apps/api/app/main.py`: `app.include_router(paperlibrary.api.routers.papers.router, prefix="/library")`
3. papermemory's `IngestionService` calls `analyzer.analyze(paper_id)` after indexing completes
4. papermemory's frontend adds a "Library" tab that calls `/library/papers`

The `storage.py` path configuration accepts an external `StoragePaths` instance,
so papermemory can point paperlibrary's storage at its own `storage/papers/` directory.

---

## 8. Implementation Phases

### Phase 1 — Core backend (target: working analysis pipeline)
- [ ] Project scaffold: `pyproject.toml`, `requirements.txt`, `.env.example`, `README.md`
- [ ] `core/config.py` — settings from `.env`
- [ ] `core/database.py` — SQLite init, `papers` table
- [ ] `core/storage.py` — file path helpers
- [ ] `models/paper.py` — SQLAlchemy model
- [ ] `schemas/paper.py` — Pydantic models
- [ ] `services/extractor.py` — PyMuPDF text extraction
- [ ] `services/analyzer.py` — LLM call + JSON parse + DB update
- [ ] `api/routers/papers.py` — upload, list, detail, delete
- [ ] `api/routers/analysis.py` — trigger, status
- [ ] `api/main.py` — FastAPI app assembly
- [ ] `__main__.py` — uvicorn launch entry

### Phase 2 — Frontend
- [ ] `static/index.html` — layout, upload form, paper grid
- [ ] `static/style.css` — card design, status badges, topic chips
- [ ] `static/app.js` — fetch logic, polling, filter/search, detail modal

### Phase 3 — Polish & integration docs
- [ ] Error states in UI (failed analysis, upload errors)
- [ ] Re-analyze button for failed papers
- [ ] `README.md` — install + config guide
- [ ] `docs/papermemory-integration.md` — how to embed in papermemory

---

## 9. Acceptance Criteria

### Phase 1
- `POST /api/papers/upload` accepts a PDF, returns immediately with `analysis_status=pending`
- Analysis runs in background; `GET /api/papers/{id}` returns `done` with all fields populated
- Scanned PDF (no text) returns `failed` with a clear `error_message`
- LLM failure does not crash the server
- `GET /api/papers` filter params work correctly

### Phase 2
- Upload a PDF from the browser; card appears immediately with "Analyzing" state
- Card updates automatically when analysis finishes (no manual refresh)
- Topic filter narrows visible cards correctly
- Detail modal shows abstract, key contributions, and citations
- Delete removes paper from DB and disk

### Phase 3
- `README.md` covers clone → install → configure → run in under 10 steps
- papermemory integration doc describes exactly which files to copy and which lines to change
