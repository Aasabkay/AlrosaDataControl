from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.models.base import Base


class StatusSynonym(Base):
    """Синоним статуса -> каноническое значение. Каноничный статус маппится сам на себя."""

    __tablename__ = "status_synonym"

    id: Mapped[int] = mapped_column(primary_key=True)
    synonym: Mapped[str] = mapped_column(String(100), unique=True)
    canonical: Mapped[str] = mapped_column(String(100), index=True)


class AssetType(Base):
    """Канонический тип оборудования и его категория (endpoint/network/...)."""

    __tablename__ = "asset_type"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    category: Mapped[str] = mapped_column(String(20))

    aliases: Mapped[list["AssetTypeAlias"]] = relationship(back_populates="asset_type",
                                                           cascade="all, delete-orphan")


class AssetTypeAlias(Base):
    """Альтернативное название типа: "ПК" -> "Рабочая станция"."""

    __tablename__ = "asset_type_alias"

    id: Mapped[int] = mapped_column(primary_key=True)
    alias: Mapped[str] = mapped_column(String(100), unique=True)
    asset_type_id: Mapped[int] = mapped_column(ForeignKey("asset_type.id"))

    asset_type: Mapped[AssetType] = relationship(back_populates="aliases")


class ColumnAlias(Base):
    """Название колонки в файле -> поле NormalizedRecord."""

    __tablename__ = "column_alias"

    id: Mapped[int] = mapped_column(primary_key=True)
    alias: Mapped[str] = mapped_column(String(200), unique=True)
    field: Mapped[str] = mapped_column(String(50), index=True)
