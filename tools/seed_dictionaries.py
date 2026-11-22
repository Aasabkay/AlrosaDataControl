"""Разовое наполнение справочников из TOML-файлов в БД.

Запуск: python -m tools.seed_dictionaries
Скрипт идемпотентный: очищает таблицы справочников и вставляет заново.
"""

import asyncio
import tomllib
from pathlib import Path

from sqlalchemy import delete

from app.database.models.dictionaries import (AssetType, AssetTypeAlias,
                                              ColumnAlias, StatusSynonym)
from app.database.session import SessionLocal

RULES_DIR = Path(__file__).resolve().parents[1] / "app" / "rules"


async def main() -> None:
    statuses_toml = tomllib.loads((RULES_DIR / "statuses.toml").read_text(encoding="utf-8"))
    columns_toml = tomllib.loads((RULES_DIR / "columns.toml").read_text(encoding="utf-8"))
    types_toml = tomllib.loads((RULES_DIR / "asset_types.toml").read_text(encoding="utf-8"))

    async with SessionLocal() as session:
        async with session.begin():
            await session.execute(delete(AssetTypeAlias))
            await session.execute(delete(AssetType))
            await session.execute(delete(StatusSynonym))
            await session.execute(delete(ColumnAlias))

            session.add_all(
                StatusSynonym(synonym=s, canonical=canonical)
                for canonical, synonyms in statuses_toml.items()
                for s in [canonical, *synonyms]
            )
            session.add_all(
                ColumnAlias(alias=alias, field=field)
                for field, aliases in columns_toml.items()
                for alias in aliases
            )
            for name, info in types_toml.items():
                asset_type = AssetType(name=name, category=info["category"])
                asset_type.aliases = [AssetTypeAlias(alias=a) for a in info["aliases"]]
                session.add(asset_type)

    print("Справочники наполнены:",
          f"статусы: {sum(len(v) + 1 for v in statuses_toml.values())},",
          f"колонки: {sum(len(v) for v in columns_toml.values())},",
          f"типы: {len(types_toml)}")


if __name__ == "__main__":
    asyncio.run(main())
