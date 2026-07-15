from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from growthos.config import Settings, get_settings
from growthos.database import get_session
from growthos.schemas import HealthRead

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthRead)
def health(
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> HealthRead:
    session.execute(text("SELECT 1"))
    return HealthRead(status="ok", database="ok", provider=settings.ai_provider)

