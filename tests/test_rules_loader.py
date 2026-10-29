import pytest

from app.rules.loader import normalize_key, load_rules, build_lookup
from app.domain.schemas import AssetCategory


@pytest.fixture(scope="module")
def rules():
    return load_rules()


values = ["Рабочая станция", "Вид оборудования", "Сер. №", "S/N", "Материально ответственное лицо"]
exp = ["рабочая станция", "вид оборудования", "сер", "s/n", "материально ответственное лицо"]
@pytest.mark.parametrize("value, expected", list(zip(values, exp)))
def test_normalize_key(value: str, expected: str):
    normalized_value = normalize_key(value)
    assert normalized_value == expected

CASE_HEADER = {
    "Наименование": "name",
    "Тип": "asset_type",
    "Производитель": "manufacturer",
    "Модель": "model",
    "Инвентарный_номер": "inventory_number",
    "Серийный_номер": "serial_number",
    "Место_установки": "location",
    "Ответственный": "responsible_person",
    "Статус": "status",
}

@pytest.mark.parametrize("header, field", CASE_HEADER.items())
def test_case_csv_header_is_recognized(rules, header: str, field: str):
    assert rules.column_field(header) == field

def test_unknown_column_returns_none(rules):
    assert rules.column_field("Цвет корпуса") is None

@pytest.mark.parametrize("raw, expected", [
    ("активный", "В эксплуатации"),
    ("В ЭКСПЛУАТАЦИИ", "В эксплуатации"),   # канон в другом регистре
    ("на_складе", "На складе"),
    ("Петров А.С.", None),                  # случай ПК-05 из кейса
])
def test_status(rules, raw: str, expected: str):
    assert rules.status(raw) == expected

@pytest.mark.parametrize("raw, expected", [
    ("Рабочая_станция", ("Рабочая станция", AssetCategory.ENDPOINT)),
    ("ОЗУ", ("Модуль оперативной памяти", AssetCategory.ADAPTER)),
    ("Switch", ("Коммутатор", AssetCategory.NETWORK)),
    ("Холодильник", None),
])
def test_asset_type(rules, raw, expected):
    assert rules.asset_type(raw) == expected

@pytest.mark.parametrize("value, is_valid", [
    ("ИНВ-0045", True),
    ("IN-009134", True),
    ("PR-007", True),
    ("SN-007821", False),   # префикс серийника
    ("ИНВ-45", False),      # слишком мало цифр
])
def test_inventory_number_format(rules, value, is_valid):
    assert bool(rules.formats["inventory_number"].match(value)) == is_valid

def test_ip_in_serial_is_detected(rules):
    assert rules.formats["ip_address"].match("145.89.128.10")
    assert not rules.formats["ip_address"].match("SN-001122")

def test_build_lookup_collision_raises():
    with pytest.raises(ValueError):
        build_lookup({"specs": ["Описание"], "name": ["описание"]})

def test_build_lookup_same_synonym_twice_is_not_collision():
    assert build_lookup({"a": ["x", "X"]}) == {"a": "a", "x": "a"}

def test_load_rules_from_custom_dir(tmp_path):
    (tmp_path / "columns.toml").write_text('name = ["Имя"]', encoding="utf-8")
    (tmp_path / "statuses.toml").write_text('"Списано" = ["списан"]', encoding="utf-8")
    (tmp_path / "asset_types.toml").write_text('["ПК"]\ncategory = "endpoint"\naliases = []', encoding="utf-8")
    (tmp_path / "formats.toml").write_text("inventory_number = '^\\d+$'", encoding="utf-8")

    rules = load_rules(tmp_path)

    assert rules.column_field("ИМЯ") == "name"
    assert rules.status("СПИСАН") == "Списано"