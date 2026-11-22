
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import (Asset, ImportBatch, Issue as DbIssue,
                                 IssueRef, ReconciliationRun, SourceRecord)
from app.domain.schemas import (AssetCategory, AssetGroup, FieldValue, Issue,
                                IssueCode, MatchMethod, MatchStatus,
                                NormalizedRecord, RowRef, Severity)


async def load_batches(session: AsyncSession, batch_ids: list[int]) -> list[ImportBatch]:
    query = (select(ImportBatch)
             .where(ImportBatch.id.in_(batch_ids))
             .options(selectinload(ImportBatch.records),
                      selectinload(ImportBatch.source)))

    result = await session.execute(query)
    return list(result.scalars().all())


def record_from_db(record: SourceRecord, source_id: int) -> NormalizedRecord:
    category = None
    if record.category:
        try:
            category = AssetCategory(record.category)
        except ValueError:
            category = None

    return NormalizedRecord(
        ref=RowRef(source_id=source_id,
                   batch_id=record.batch_id,
                   row_number=record.row_number),
        inventory_number=record.inventory_number,
        serial_number=record.serial_number,
        name=record.name,
        asset_type=record.asset_type,
        category=category,
        manufacturer=record.manufacturer,
        model=record.model,
        specs=record.specs,
        status=record.status,
        status_raw=record.status_raw,
        responsible_person=record.responsible_person,
        location=record.location,
        commissioning_date=record.commissioning_date,
        raw=record.raw or {},
    )


async def create_run(session: AsyncSession) -> ReconciliationRun:
    run = ReconciliationRun(status="done")
    session.add(run)
    await session.flush()
    return run


async def save_run(session: AsyncSession, run: ReconciliationRun,
                   groups: list[AssetGroup], issues: list[Issue],
                   record_map: dict[tuple[int, int], SourceRecord]) -> dict:
    assets_total = 0
    for group in groups:
        asset = Asset(
            asset_key=group.asset_key,
            match_status=str(group.match_status),
            match_method=str(group.match_method) if group.match_method else None,
            match_score=group.match_score,
            reconciliation_run_id=run.id,
        )
        session.add(asset)
        await session.flush()
        assets_total += 1

        for record in group.records:
            db_record = record_map.get((record.ref.batch_id, record.ref.row_number))
            if db_record is not None:
                db_record.asset_id = asset.id

    issues_total = 0
    for issue in issues:
        db_issue = DbIssue(
            code=str(issue.code),
            severity=str(issue.severity),
            message=issue.message,
            field=issue.field,
            suggestion=issue.suggestion,
            values=[v.model_dump(mode="json") for v in issue.values] or None,
            reconciliation_run_id=run.id,
        )
        db_issue.refs = [
            IssueRef(batch_id=ref.batch_id, row_number=ref.row_number)
            for ref in issue.refs
        ]
        session.add(db_issue)
        issues_total += 1

    return {"assets_total": assets_total, "issues_total": issues_total}


async def get_run(session: AsyncSession, run_id: int) -> ReconciliationRun | None:
    return await session.get(ReconciliationRun, run_id)


async def load_run_assets(session: AsyncSession, run_id: int) -> list[Asset]:
    query = (select(Asset)
             .where(Asset.reconciliation_run_id == run_id)
             .options(selectinload(Asset.records)
                      .selectinload(SourceRecord.batch)
                      .selectinload(ImportBatch.source)))

    result = await session.execute(query)
    return list(result.scalars().all())


async def load_run_issues(session: AsyncSession, run_id: int) -> list[Issue]:
    assets = await load_run_assets(session, run_id)
    batch_ids = {record.batch_id for asset in assets for record in asset.records}

    query = (select(DbIssue)
             .where((DbIssue.reconciliation_run_id == run_id)
                    | (DbIssue.batch_id.in_(batch_ids)))
             .options(selectinload(DbIssue.refs)))

    result = await session.execute(query)
    return list(result.scalars().all())


def issue_from_db(row: Issue, source_by_batch: dict[int, int]) -> Issue:
    return Issue(
        code=IssueCode(row.code),
        severity=Severity(row.severity),
        message=row.message,
        field=row.field,
        suggestion=row.suggestion,
        refs=[RowRef(source_id=source_by_batch[ref.batch_id],
                     batch_id=ref.batch_id,
                     row_number=ref.row_number)
              for ref in row.refs],
        values=[FieldValue.model_validate(value) for value in (row.values or [])],
    )


def group_from_db(asset: Asset) -> AssetGroup:
    records = [
        record_from_db(record, record.batch.source_id)
        for record in asset.records
    ]
    return AssetGroup(
        asset_key=asset.asset_key,
        records=records,
        match_status=MatchStatus(asset.match_status),
        match_method=MatchMethod(asset.match_method) if asset.match_method else None,
        match_score=asset.match_score,
    )
