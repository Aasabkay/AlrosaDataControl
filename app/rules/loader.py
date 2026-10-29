import tomllib
from pathlib import Path
import re
from app.domain.schemas import AssetCategory

from pydantic import BaseModel

def normalize_key(value: str) -> str:
    value = value.casefold()
    value = value.replace("_", " ").replace("ё", "е")
    value = value.replace("№", "").replace(".", "")
    value = " ".join(value.split())
    return value

def build_lookup(mapping: dict[str, list[str]]) -> dict[str, str]:
    lookup = {}
    for key, values in mapping.items():
        for name in [key, *values]:
            k = normalize_key(name)
            if k in lookup and lookup[k] != key:
                raise ValueError(f"'{name}' относится и к '{lookup[k]}', и к '{key}'")
            lookup[k] = key

    return lookup

class Rules(BaseModel):
    columns: dict[str, str]
    statuses: dict[str, str]
    asset_types: dict[str, tuple[str, AssetCategory]]
    formats: dict[str, re.Pattern]

    def column_field(self, header: str) -> str | None:
        return self.columns.get(normalize_key(header))

    def status(self, value: str) -> str | None:
        return self.statuses.get(normalize_key(value))

    def asset_type(self, value: str) -> tuple[str, AssetCategory] | None:
        return self.asset_types.get(normalize_key(value))


def load_rules(rules_dir: Path = Path(__file__).resolve().parent) -> Rules:
    with open(rules_dir / "columns.toml", 'rb') as file:
        columns = tomllib.load(file)
        parsed_columns = build_lookup(columns)

    with open(rules_dir / "statuses.toml", 'rb') as file:
        statuses = tomllib.load(file)
        parsed_statuses = build_lookup(statuses)

    with open(rules_dir / "asset_types.toml", 'rb') as file:
        parsed_asset_types: dict[str, tuple[str, AssetCategory]] = {}
        assets = tomllib.load(file)
        for key, info in assets.items():
            try:
                category = AssetCategory(info["category"])
            except ValueError:
                raise ValueError(f"This type of category doesn't exist: {info["category"]}")

            aliases: list = info["aliases"]
            asset_types_aliases = build_lookup({key: aliases})
            for k, v in asset_types_aliases.items():
                parsed_asset_types[k] = v, category

    with open(rules_dir / "formats.toml", 'rb') as file:
        formats = tomllib.load(file)
        parsed_formats = {}

        for key, value in formats.items():
            try:
                re.compile(value)
            except re.error:
                raise ValueError(f"This format doesn't exist: {value}")

            parsed_formats[key] = re.compile(value)

    return Rules(columns=parsed_columns, statuses=parsed_statuses,
                 asset_types=parsed_asset_types, formats=parsed_formats)


