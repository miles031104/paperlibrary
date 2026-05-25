import asyncio
import json
import re
from datetime import UTC, datetime

from sqlalchemy.orm import Session, sessionmaker

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


def _clean_json(raw: str) -> str:
    """Strip model-added wrappers before JSON parsing.

    Handles:
    - Markdown code fences (```json ... ```)
    - Reasoning model <think>...</think> blocks (e.g. MiniMax-M2.7, DeepSeek-R1)
    """
    raw = raw.strip()
    # Remove <think>...</think> reasoning blocks (reasoning models emit these)
    raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
    # Remove markdown code fences
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    # Advance to first { in case there is any remaining preamble text
    brace = raw.find("{")
    if brace > 0:
        raw = raw[brace:]
    return raw.strip()


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
        return json.loads(_clean_json(msg.content[0].text))

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
            return json.loads(_clean_json(resp.json()["choices"][0]["message"]["content"]))

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
                extract_text,
                file_path,
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
