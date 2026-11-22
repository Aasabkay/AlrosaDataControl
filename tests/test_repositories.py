from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import DB_URL
from app.database.models import RawRow, SourceRecord, Issue, Source
from app.database.repositories.imports import create_source, create_batch, save_import, list_batches
from app.database.repositories.rules import load_rules_from_db
from app.pipeline.parser import parse_file

current_dir = Path(__file__).parent
case_sample_csv_path = current_dir.parent / "sample_data" / "case_sample.csv"


@pytest.fixture
async def session():
    # Тест не должен коммитить в общую базу: данные живут внутри транзакции
    # и откатываются. NullPool — чтобы соединение не пережило свой event loop.
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

async def test_save_import(session):
    rules = await load_rules_from_db(session)
    source = await create_source(session, Source(name="Бухгалтерия (тест)"))
    batch = await create_batch(session, source.id, "case_sample.csv", "uuid-test")
    result = parse_file(case_sample_csv_path, source.id, batch.id, rules)
    await save_import(session, batch.id, case_sample_csv_path, result)

    rows = (await session.execute(
        select(RawRow).where(RawRow.batch_id == batch.id)
    )).scalars().all()

    by_number = {r.row_number: r for r in rows}
    assert len(rows) == 4
    assert by_number[2].status == "rejected"
    assert by_number[2].reject_reason == "BAD_COLUMN_COUNT"
    assert by_number[3].status == "accepted"
    assert by_number[3].reject_reason is None

    records = (await session.execute(
        select(SourceRecord).where(SourceRecord.batch_id == batch.id)
    )).scalars().all()
    assert len(records) == 1
    assert records[0].name == "ПК-05"

    codes = {i.code for i in (await session.execute(
        select(Issue).where(Issue.batch_id == batch.id)
    )).scalars()}
    assert codes == {"BAD_COLUMN_COUNT", "INVALID_STATUS"}


async def test_list_batches_newest_first(session):
    source = await create_source(session, Source(name="Журнал импорта (тест)"))
    first = await create_batch(session, source.id, "first.csv", "uuid-first")
    second = await create_batch(session, source.id, "second.csv", "uuid-second")

    batches = await list_batches(session)
    ids = [batch.id for batch in batches]

    assert first.id in ids and second.id in ids
    # Свежие загрузки идут первыми: журнал и «последняя загрузка на источник» зависят от этого.
    assert ids.index(second.id) < ids.index(first.id)