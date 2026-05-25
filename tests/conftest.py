import pytest
from pathlib import Path
from sqlalchemy.orm import Session

from paperlibrary.core.config import Settings
from paperlibrary.core.database import init_db


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
