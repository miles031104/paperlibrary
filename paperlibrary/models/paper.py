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
    authors: Mapped[str | None] = mapped_column(String, nullable=True)        # JSON array
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    venue: Mapped[str | None] = mapped_column(String, nullable=True)
    abstract: Mapped[str | None] = mapped_column(String, nullable=True)
    topics: Mapped[str | None] = mapped_column(String, nullable=True)          # JSON array
    keywords: Mapped[str | None] = mapped_column(String, nullable=True)        # JSON array
    one_line_summary: Mapped[str | None] = mapped_column(String, nullable=True)
    key_contributions: Mapped[str | None] = mapped_column(String, nullable=True)  # JSON array
    methodology: Mapped[str | None] = mapped_column(String, nullable=True)
    citations: Mapped[str | None] = mapped_column(String, nullable=True)       # JSON array
