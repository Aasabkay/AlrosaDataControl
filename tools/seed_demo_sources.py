"""Демо-источники для прототипа: создаёт три источника, если их ещё нет.

Запуск: python -m tools.seed_demo_sources

Идемпотентно: повторный запуск ничего не дублирует (имена уникальны).
Нужно, чтобы на чистой базе (новый VPS) экран «Загрузка» сразу предлагал
источники, а не пустой список.
"""

import asyncio

from sqlalchemy import select

from app.database.models import Source
from app.database.session import SessionLocal

DEMO_SOURCES = [
    ("Бухгалтерия (XLSX)", "Демо-источник 1: выгрузка бухгалтерии"),
    ("Выгрузка CMDB (CSV)", "Демо-источник 2: выгрузка из CMDB"),
    ("Акт инвентаризации (CSV)", "Демо-источник 3: акт инвентаризации"),
]


async def main() -> None:
    async with SessionLocal() as session:
        async with session.begin():
            existing = set((await session.execute(select(Source.name))).scalars())

            for name, description in DEMO_SOURCES:
                if name not in existing:
                    session.add(Source(name=name, description=description))


if __name__ == "__main__":
    asyncio.run(main())
