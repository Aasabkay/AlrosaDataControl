from pathlib import Path

import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload
from sqlalchemy.pool import NullPool

from app.config import DB_URL
from app.database.models import Asset, Issue, Source, SourceRecord
from app.database.repositories.imports import (create_batch, create_source,
                                               save_import)
from app.database.repositories.reconciliations import (create_run,
                                                       issue_from_db,
                                                       load_batches,
                                                       load_run_issues,
                                                       record_from_db, save_run)
from app.database.repositories.rules import load_rules_from_db
from app.pipeline.detectors import run_detectors
from app.pipeline.matcher import match_records
from app.pipeline.parser import parse_file

current_dir = Path(__file__).parent
case_sample_path = current_dir.parent / "sample_data" / "case_sample.csv"


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine(DB_URL, poolclass=NullPool)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with maker() as session:
            transaction = await session.begin()
            try:
                yield session
            finally:
                await transaction.rollback()
    finally:
        await engine.dispose()


async def _prepare_two_batches(session):
    rules = await load_rules_from_db(session)
    batches = []
    for index, source_name in enumerate(("Сверка тест: бухгалтерия", "Сверка тест: CMDB"), start=1):
        source = await create_source(session, Source(name=source_name))
        batch = await create_batch(session, source.id, "case_sample.csv", f"uuid-{index}")
        result = parse_file(case_sample_path, source.id, batch.id, rules)
        await save_import(session, batch.id, case_sample_path, result)
        batches.append(batch)
    return batches


async def test_reconciliation_run_saves_assets_and_issues(session):
    batches = await _prepare_two_batches(session)

    second_record = (await session.execute(
        select(SourceRecord).where(SourceRecord.batch_id == batches[1].id)
    )).scalar_one()
    second_record.location = "Офис 999"

    rules = await load_rules_from_db(session)
    batch_ids = [batch.id for batch in batches]
    loaded = await load_batches(session, batch_ids)

    records = [
        record_from_db(record, batch.source.id)
        for batch in loaded
        for record in batch.records
    ]
    groups = match_records(records)
    issues = run_detectors(groups, expected_source_ids={batch.source.id for batch in loaded})

    record_map = {
        (record.batch_id, record.row_number): record
        for batch in loaded
        for record in batch.records
    }
    run = await create_run(session)
    counts = await save_run(session, run, groups, issues, record_map)

    assert counts == {"assets_total": 1, "issues_total": 1}

    assets = (await session.execute(
        select(Asset).where(Asset.reconciliation_run_id == run.id)
    )).scalars().all()
    assert len(assets) == 1
    assert assets[0].match_status == "matched"
    assert assets[0].match_method == "inventory_number"

    for batch in batches:
        record = (await session.execute(
            select(SourceRecord).where(SourceRecord.batch_id == batch.id)
        )).scalar_one()
        assert record.asset_id == assets[0].id

    run_issues = (await session.execute(
        select(Issue).where(Issue.reconciliation_run_id == run.id)
        .options(selectinload(Issue.refs))
    )).scalars().all()
    assert len(run_issues) == 1
    assert run_issues[0].code == "FIELD_MISMATCH"
    assert run_issues[0].batch_id is None
    assert len(run_issues[0].refs) == 2


async def test_run_issues_are_readable_back(session):
    batches = await _prepare_two_batches(session)
    second_record = (await session.execute(
        select(SourceRecord).where(SourceRecord.batch_id == batches[1].id)
    )).scalar_one()
    second_record.location = "Офис 999"

    rules = await load_rules_from_db(session)
    loaded = await load_batches(session, [batch.id for batch in batches])
    records = [
        record_from_db(record, batch.source.id)
        for batch in loaded
        for record in batch.records
    ]
    groups = match_records(records)
    issues = run_detectors(groups, expected_source_ids={batch.source.id for batch in loaded})

    record_map = {
        (record.batch_id, record.row_number): record
        for batch in loaded
        for record in batch.records
    }
    run = await create_run(session)
    await save_run(session, run, groups, issues, record_map)

    stored = await load_run_issues(session, run.id)
    codes = {issue.code for issue in stored}
    assert "FIELD_MISMATCH" in codes
    assert "BAD_COLUMN_COUNT" in codes
    assert "INVALID_STATUS" in codes

    source_by_batch = {
        record.batch_id: batch.source.id
        for batch in loaded
        for record in batch.records
    }
    converted = [issue_from_db(row, source_by_batch) for row in stored]
    mismatch = next(issue for issue in converted if issue.code.value == "FIELD_MISMATCH")
    assert len(mismatch.refs) == 2
    assert {ref.source_id for ref in mismatch.refs} == {batch.source.id for batch in batches}
