"""Репозиторий импорта: раскладывает ParseResult по таблицам БД."""

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import (ImportBatch, Issue, IssueRef, RawRow, Source,
                                 SourceRecord)
from app.domain.schemas import IssueCode, ParseResult
from app.pipeline.readers import read_rows

EXCLUDED_CODES = {
    IssueCode.BAD_COLUMN_COUNT, IssueCode.PARENT_REJECTED,
    IssueCode.NAME_CONFLICT, IssueCode.INVENTORY_CONFLICT,
    IssueCode.NO_PARENT, IssueCode.DUP_IN_SOURCE,
}


async def create_source(session: AsyncSession, source: Source) -> Source:
    session.add(source)
    await session.flush()
    return source


async def create_batch(session: AsyncSession, source_id: int,
                       filename: str, file_uuid: str) -> ImportBatch:
    batch = ImportBatch(source_id=source_id, filename=filename, file_uuid=file_uuid)
    session.add(batch)
    await session.flush()
    return batch


async def save_import(session: AsyncSession, batch_id: int, path: Path,
                      result: ParseResult) -> dict:
    """Сохраняет результат парсинга. Возвращает счётчики для ответа API."""

    accepted_rows = {r.ref.row_number for r in result.records}
    rows_total = 0

    reason_by_row: dict[int, IssueCode] = {}
    for issue in result.issues:
        if issue.code not in EXCLUDED_CODES:
            continue
        for ref in issue.refs:
            reason_by_row.setdefault(ref.row_number, issue.code)

    for row_number, cells in read_rows(path):
        if row_number == 1:
            continue
        rows_total += 1
        status = "accepted" if row_number in accepted_rows else "rejected"
        reason = reason_by_row.get(row_number)
        session.add(RawRow(batch_id=batch_id, row_number=row_number,
                           cells=cells, status=status,
                           reject_reason=str(reason) if reason else None))

    for record in result.records:
        session.add(SourceRecord(
            batch_id=batch_id, row_number=record.ref.row_number,
            inventory_number=record.inventory_number,
            serial_number=record.serial_number,
            name=record.name, asset_type=record.asset_type,
            category=str(record.category) if record.category else None,
            manufacturer=record.manufacturer, model=record.model,
            specs=record.specs, status=record.status,
            status_raw=record.status_raw,
            responsible_person=record.responsible_person,
            location=record.location,
            commissioning_date=record.commissioning_date,
            raw=record.raw,
        ))

    for issue in result.issues:
        db_issue = Issue(
            batch_id=batch_id,
            code=str(issue.code), severity=str(issue.severity),
            message=issue.message, field=issue.field,
            suggestion=issue.suggestion,
            values=[v.model_dump(mode="json") for v in issue.values] or None,
        )
        db_issue.refs = [IssueRef(batch_id=ref.batch_id, row_number=ref.row_number)
                         for ref in issue.refs]
        session.add(db_issue)

    return {"rows_total": rows_total,
            "records_accepted": len(result.records),
            "issues_count": len(result.issues)}

async def list_sources(session: AsyncSession) -> list[Source]:
    query = select(Source).order_by(Source.id)
    sources = await session.execute(query)

    return sources.scalars().all()

async def get_batch(session: AsyncSession, batch_id: int) -> ImportBatch | None:
    query = (select(ImportBatch).where(ImportBatch.id == batch_id)
             .options(selectinload(ImportBatch.raw_rows)))

    batch = await session.execute(query)

    return batch.scalar_one_or_none()

async def get_import_log(session: AsyncSession, batch_id: int) -> list[RawRow]:
    query = select(RawRow).where(RawRow.batch_id == batch_id).order_by(RawRow.row_number)

    result = await session.execute(query)

    return result.scalars().all()

async def get_batch_issues(session: AsyncSession, batch_id: int) -> list[Issue]:
    query = (select(Issue).where(Issue.batch_id == batch_id)
             .options(selectinload(Issue.refs)).order_by(Issue.id))

    result = await session.execute(query)

    return result.scalars().all()