import uvicorn

from paperlibrary.core.config import get_settings


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "paperlibrary.api.main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
