from datetime import datetime

from sqlalchemy import Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.models.base import Base


class Asset(Base):

    __tablename__ = "asset"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_key: Mapped[str] = mapped_column(String(100), index=True)
    match_status: Mapped[str] = mapped_column(String(20))
    match_method: Mapped[str | None] = mapped_column(String(20))
    match_score: Mapped[float | None] = mapped_column(Float)

    reconciliation_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("reconciliation_run.id"))

    records: Mapped[list["SourceRecord"]] = relationship(back_populates="asset")
    reconciliation_run: Mapped["ReconciliationRun"] = relationship(back_populates="assets")


class ReconciliationRun(Base):

    __tablename__ = "reconciliation_run"

    id: Mapped[int] = mapped_column(primary_key=True)
    started_at: Mapped[datetime] = mapped_column(server_default=func.now())
    status: Mapped[str] = mapped_column(String(20), default="running")

    assets: Mapped[list[Asset]] = relationship(back_populates="reconciliation_run")
