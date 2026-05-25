from pathlib import Path


def pdfs_dir(storage_path: Path) -> Path:
    return storage_path / "pdfs"


def pdf_path(storage_path: Path, paper_id: str) -> Path:
    return pdfs_dir(storage_path) / f"{paper_id}.pdf"


def ensure_storage(storage_path: Path) -> None:
    pdfs_dir(storage_path).mkdir(parents=True, exist_ok=True)
