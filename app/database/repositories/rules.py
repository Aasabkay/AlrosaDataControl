import re
import tomllib
from collections import defaultdict
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models.dictionaries import AssetType, ColumnAlias, StatusSynonym
from app.domain.schemas import AssetCategory
from app.rules.loader import Rules, build_lookup

FORMATS_TOML = Path(__file__).resolve().parents[2] / "rules" / "formats.toml"


def _load_formats() -> dict[str, re.Pattern]:
    with open(FORMATS_TOML, "rb") as file:
        return {key: re.compile(value) for key, value in tomllib.load(file).items()}


async def load_rules_from_db(session: AsyncSession) -> Rules:
    # статусы: синоним -> канонический (build_lookup сам добавит маппинг канон. на себя)
    status_rows = (await session.execute(select(StatusSynonym))).scalars().all()
    synonyms_by_canonical: dict[str, list[str]] = defaultdict(list)
    for row in status_rows:
        if row.synonym != row.canonical:
            synonyms_by_canonical[row.canonical].append(row.synonym)
    statuses = build_lookup(dict(synonyms_by_canonical))

    # типы: алиас -> (канонический тип, категория)
    type_rows = (await session.execute(
        select(AssetType).options(selectinload(AssetType.aliases))
    )).scalars().all()
    aliases_by_type = {t.name: [a.alias for a in t.aliases] for t in type_rows}
    categories = {t.name: AssetCategory(t.category) for t in type_rows}
    asset_types = {alias: (canonical, categories[canonical])
                   for alias, canonical in build_lookup(aliases_by_type).items()}

    # колонки: алиас шапки -> поле NormalizedRecord
    column_rows = (await session.execute(select(ColumnAlias))).scalars().all()
    aliases_by_field: dict[str, list[str]] = defaultdict(list)
    for row in column_rows:
        aliases_by_field[row.field].append(row.alias)
    columns = build_lookup(dict(aliases_by_field))

    return Rules(columns=columns, statuses=statuses,
                 asset_types=asset_types, formats=_load_formats())
