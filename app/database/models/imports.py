from datetime import date, datetime

from sqlalchemy import ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.models.base import Base


class Source(Base):

    __tablename__ = "source"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    batches: Mapped[list["ImportBatch"]] = relationship(back_populates="source")


class ImportBatch(Base):

    __tablename__ = "import_batch"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("source.id"))
    filename: Mapped[str] = mapped_column(String(500))
    uploaded_at: Mapped[datetime] = mapped_column(server_default=func.now())

    source: Mapped[Source] = relationship(back_populates="batches")
    raw_rows: Mapped[list["RawRow"]] = relationship(back_populates="batch")
    records: Mapped[list["SourceRecord"]] = relationship(back_populates="batch")


class RawRow(Base):

    __tablename__ = "raw_row"

    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("import_batch.id"))
    row_number: Mapped[int]
    cells: Mapped[list[str]] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(20))
    reject_reason: Mapped[str | None] = mapped_column(String(30))
    batch: Mapped[ImportBatch] = relationship(back_populates="raw_rows")

    __table_args__ = (Index("ix_raw_row_batch_row", "batch_id", "row_number"),)


class SourceRecord(Base):

    __tablename__ = "source_record"

    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("import_batch.id"))
    row_number: Mapped[int]

    inventory_number: Mapped[str | None] = mapped_column(String(50))
    serial_number: Mapped[str | None] = mapped_column(String(100))
    name: Mapped[str | None] = mapped_column(String(300))
    asset_type: Mapped[str | None] = mapped_column(String(100))
    category: Mapped[str | None] = mapped_column(String(20))
    manufacturer: Mapped[str | None] = mapped_column(String(200))
    model: Mapped[str | None] = mapped_column(String(200))
    specs: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str | None] = mapped_column(String(50))
    status_raw: Mapped[str | None] = mapped_column(String(100))
    responsible_person: Mapped[str | None] = mapped_column(String(200))
    location: Mapped[str | None] = mapped_column(String(500))
    commissioning_date: Mapped[date | None]
    raw: Mapped[dict] = mapped_column(JSONB)

    asset_id: Mapped[int | None] = mapped_column(ForeignKey("asset.id"))

    batch: Mapped[ImportBatch] = relationship(back_populates="records")
    asset: Mapped["Asset"] = relationship(back_populates="records")

    __table_args__ = (Index("ix_source_record_batch_row", "batch_id", "row_number"),)
