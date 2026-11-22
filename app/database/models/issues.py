from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.models.base import Base


class Issue(Base):

    __tablename__ = "issue"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), index=True)
    severity: Mapped[str] = mapped_column(String(10))
    message: Mapped[str] = mapped_column(Text)
    field: Mapped[str | None] = mapped_column(String(50))
    suggestion: Mapped[str | None] = mapped_column(String(100))

    values: Mapped[list | None] = mapped_column(JSONB)

    batch_id: Mapped[int | None] = mapped_column(ForeignKey("import_batch.id"))
    reconciliation_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("reconciliation_run.id"))

    refs: Mapped[list["IssueRef"]] = relationship(back_populates="issue",
                                                  cascade="all, delete-orphan")


class IssueRef(Base):

    __tablename__ = "issue_ref"

    id: Mapped[int] = mapped_column(primary_key=True)
    issue_id: Mapped[int] = mapped_column(ForeignKey("issue.id"))
    batch_id: Mapped[int] = mapped_column(ForeignKey("import_batch.id"))
    row_number: Mapped[int]

    issue: Mapped[Issue] = relationship(back_populates="refs")
