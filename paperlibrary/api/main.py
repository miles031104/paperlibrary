from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from paperlibrary.api.routers import health, papers

STATIC_DIR = Path(__file__).parent.parent / "static"


def create_app() -> FastAPI:
    app = FastAPI(title="paperlibrary", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router, prefix="/api", tags=["health"])
    app.include_router(papers.router, prefix="/api/papers", tags=["papers"])

    if STATIC_DIR.exists():
        app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")

    return app


app = create_app()
