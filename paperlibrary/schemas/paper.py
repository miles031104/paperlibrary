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
        if hasattr(data, "__dict__"):
            data = {k: v for k, v in data.__dict__.items() if not k.startswith("_")}
        for field in _JSON_FIELDS:
            val = data.get(field)
            if val is None:
                data[field] = []
            elif isinstance(val, str):
                try:
                    data[field] = json.loads(val)
                except (json.JSONDecodeError, TypeError):
                    data[field] = []
        return data
