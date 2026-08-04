from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from growthos.config import Settings, get_settings
from growthos.database import get_session
from growthos.schemas import HealthRead

router = APIRouter(tags=["health"])


def _readiness(session: Session, settings: Settings) -> HealthRead:
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Serviço temporariamente indisponível",
        ) from exc
    return HealthRead(status="ok", database="ok", provider=settings.ai_provider)


@router.get("/health/live", response_model=dict[str, str])
def liveness() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready", response_model=HealthRead)
def readiness(
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> HealthRead:
    return _readiness(session, settings)


@router.get("/health", response_model=HealthRead)
def health(
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> HealthRead:
    """Compatibilidade: o endpoint histórico mantém semântica de prontidão."""
    return _readiness(session, settings)
