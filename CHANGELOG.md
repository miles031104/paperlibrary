# Changelog

## [0.1.0] — 2026-05-25

### Added

- FastAPI backend with SQLite storage via SQLAlchemy ORM
- Single `papers` table storing all metadata and LLM-extracted fields
- PDF upload endpoint: `POST /api/papers/upload` — saves file, triggers background LLM analysis
- Paper list with filters: `GET /api/papers?topic=&year=&methodology=&status=&q=`
- Paper detail: `GET /api/papers/{id}`
- Paper delete: `DELETE /api/papers/{id}` (removes DB record and PDF file)
- Re-trigger analysis: `POST /api/papers/{id}/analyze`
- Health check: `GET /api/health` (reports LLM configuration status)
- LLM support: Anthropic (`claude-haiku-4-5` default) and OpenAI-compatible endpoints
- Text extraction via PyMuPDF — abstract-first ordering, configurable page/char limits
- Graceful failure handling: scanned PDFs and LLM errors set `analysis_status=failed` without crashing
- 16 tests covering extractor, analyzer (with mocked LLM), and all API endpoints
- `python -m paperlibrary` entry point via uvicorn
- Configuration via `.env` with `PAPERLIBRARY_*` prefix
