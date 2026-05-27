from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


# Columns added after initial release — applied via ALTER TABLE so existing
# databases are upgraded automatically without requiring a full reset.
_MIGRATIONS = [
    "ALTER TABLE papers ADD COLUMN ai_summary TEXT",
]


def init_db(db_path: Path) -> sessionmaker[Session]:
    """Create engine, ensure tables exist, return session factory."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)

    # Apply additive migrations (silently skip if column already exists)
    with engine.connect() as conn:
        for stmt in _MIGRATIONS:
            try:
                conn.execute(text(stmt))
                conn.commit()
            except OperationalError:
                pass  # column already exists

    return sessionmaker(bind=engine, autoflush=False, autocommit=False)
