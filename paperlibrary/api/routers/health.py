from fastapi import APIRouter, Depends

from paperlibrary.core.config import Settings, get_settings

router = APIRouter()


@router.get("/health")
def health(settings: Settings = Depends(get_settings)) -> dict:
    return {
        "status": "ok",
        "db": "ok",
        "llm_configured": bool(settings.llm_api_key),
    }
