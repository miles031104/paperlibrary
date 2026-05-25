import uuid
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from paperlibrary.api.deps import get_analyzer, get_db, get_session_factory, get_settings
from paperlibrary.core.config import Settings
from paperlibrary.core.storage import ensure_storage, pdf_path
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

    background_tasks.add_task(analyzer.analyze, paper_id, file.filename, str(dest))

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


@router.get("/{paper_id}/pdf")
def serve_pdf(paper_id: str, db: Session = Depends(get_db)) -> FileResponse:
    paper = db.get(Paper, paper_id)
    if paper is None:
        raise HTTPException(status_code=404, detail="Paper not found.")
    if not Path(paper.file_path).exists():
        raise HTTPException(status_code=404, detail="PDF file not found on disk.")
    return FileResponse(
        path=paper.file_path,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{paper.filename}"'},
    )


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

    background_tasks.add_task(analyzer.analyze, paper_id, paper.filename, paper.file_path)
    return {"paper_id": paper_id, "analysis_status": "pending"}
