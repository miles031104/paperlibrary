# paperlibrary

A local web app that turns a folder of PDFs into a structured, searchable paper library.

Upload PDFs → LLM automatically extracts title, authors, year, venue, topics, one-line summary, key contributions, and citations → browse and filter in your browser.

No chat interface, no cloud dependency. Just upload and explore.

---

## Requirements

- Python 3.11+
- An API key for Anthropic or any OpenAI-compatible provider (OpenAI, DeepSeek, etc.)

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

Open **http://localhost:8000** in your browser. That's it — no Node.js, no build step.

---

## Usage

1. Click **Upload PDF** and select a paper
2. A card appears immediately with a "Pending" badge
3. The LLM analyzes the paper in the background (typically 5–15 seconds)
4. The card updates automatically with title, authors, topics, and a one-line summary
5. Click **Details** to see the abstract, key contributions, and citations
6. Use the filter bar to narrow by topic, year, methodology, or status
7. Use the search box to find papers by title or summary text

---

## Configuration

| Variable | Default | Description |
|---|---|---|
| `PAPERLIBRARY_LLM_PROVIDER` | `anthropic` | `anthropic` or `openai-compatible` |
| `PAPERLIBRARY_LLM_API_KEY` | — | Your API key |
| `PAPERLIBRARY_LLM_MODEL` | `claude-haiku-4-5` | Model name |
| `PAPERLIBRARY_LLM_BASE_URL` | — | Base URL (openai-compatible only) |
| `PAPERLIBRARY_STORAGE_PATH` | `./storage` | Where to store DB and PDFs |
| `PAPERLIBRARY_PORT` | `8000` | Server port |
| `PAPERLIBRARY_EXTRACT_PAGES` | `6` | Pages to read per PDF |
| `PAPERLIBRARY_MAX_TEXT_CHARS` | `6000` | Max characters sent to LLM |

### Using OpenAI or other providers

```ini
PAPERLIBRARY_LLM_PROVIDER=openai-compatible
PAPERLIBRARY_LLM_API_KEY=sk-...
PAPERLIBRARY_LLM_MODEL=gpt-4o-mini
PAPERLIBRARY_LLM_BASE_URL=https://api.openai.com/v1
```

---

## API

The browser UI is built on a REST API you can also call directly:

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/papers/upload` | Upload a PDF |
| `GET` | `/api/papers` | List papers (supports `?topic=`, `?year=`, `?status=`, `?q=`) |
| `GET` | `/api/papers/{id}` | Full paper detail |
| `DELETE` | `/api/papers/{id}` | Delete paper and file |
| `POST` | `/api/papers/{id}/analyze` | Re-trigger analysis |
| `GET` | `/api/health` | Health check |

---

## Tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

16 tests covering the extractor, LLM analyzer (mocked), and all API endpoints.

---

## Integration with papermemory

See [`docs/papermemory-integration.md`](docs/papermemory-integration.md) for instructions on embedding paperlibrary inside the papermemory codebase.
