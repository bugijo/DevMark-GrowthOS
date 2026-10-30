from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from growthos.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class IntegrationToken(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Credencial de máquina (ex.: Hermes) limitada a uma organização e a escopos de leitura.

    Só o hash é persistido; o valor é mostrado uma única vez na emissão.
    """

    __tablename__ = "integration_tokens"

    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    label: Mapped[str] = mapped_column(String(80), nullable=False)
    scopes: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
