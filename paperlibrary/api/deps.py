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
