"""Генератор демо-данных: три источника с заранее известными ошибками.

Запуск:
    python -m tools.generate_data

Создаёт в sample_data/demo три файла-источника и expected.json с ожидаемым
результатом сверки. Файлы детерминированы: одинаковый запуск даёт одинаковые
данные. Это «посеяли N ошибок — нашли N» для защиты.
"""

import csv
import json
from pathlib import Path

from openpyxl import Workbook

from app.pipeline.report import ReportMeta, build_report
from app.pipeline.runner import run_pipeline

DEMO_DIR = Path(__file__).resolve().parents[1] / "sample_data" / "demo"

EXPECTED_SOURCE_IDS = {1, 2, 3}

# Канонический порядок полей, как в columns.toml.
FIELDS = (
    "name",
    "asset_type",
    "manufacturer",
    "model",
    "inventory_number",
    "serial_number",
    "specs",
    "status",
    "responsible_person",
    "location",
    "commissioning_date",
)

ASSETS = [
    (1, "ПК-001", "Рабочая станция", "HP", "ProDesk 400"),
    (2, "Сервер-002", "Сервер", "Dell", "PowerEdge R450"),
    (3, "Ноутбук-003", "Ноутбук", "Lenovo", "ThinkPad E16"),
    (4, "Моноблок-004", "Моноблок", "Apple", "iMac 24"),
    (5, "Коммутатор-005", "Коммутатор", "Cisco", "Catalyst 2960"),
    (6, "Маршрутизатор-006", "Маршрутизатор", "MikroTik", "hEX RB750"),
    (7, "Точка-007", "Точка доступа", "TP-Link", "EAP225"),
    (8, "Межсетевой-008", "Межсетевой экран", "ZyXEL", "USG Flex"),
    (9, "ПК-009", "Рабочая станция", "HP", "ProDesk 600"),
    (10, "Сервер-010", "Сервер", "HPE", "ProLiant DL360"),
    (11, "Ноутбук-011", "Ноутбук", "ASUS", "Vivobook 15"),
    (12, "Моноблок-012", "Моноблок", "Lenovo", "IdeaCentre A340"),
    (13, "Коммутатор-013", "Коммутатор", "D-Link", "DES-1024"),
    (14, "Маршрутизатор-014", "Маршрутизатор", "Keenetic", "Giga KN-1010"),
    (15, "Точка-015", "Точка доступа", "Ubiquiti", "UAP AC Lite"),
    (16, "Межсетевой-016", "Межсетевой экран", "Fortinet", "FortiGate 60F"),
    (17, "ПК-017", "Рабочая станция", "Dell", "OptiPlex 7000"),
    (18, "Сервер-018", "Сервер", "Supermicro", "X11SCL"),
    (19, "Ноутбук-019", "Ноутбук", "Huawei", "MateBook D15"),
    (20, "Коммутатор-020", "Коммутатор", "Eltex", "MES2324"),
]

# Правки по источникам: {(source_id, номер актива): {поле: значение}}.
TWEAKS = {
    # источник 1 (бухгалтерия)
    (1, 7): {"location": ""},                     # пропущено местоположение
    (1, 11): {"serial_number": "10.0.0.5"},       # IP вместо серийного номера
    (1, 16): {"commissioning_date": "32.13.2024"},  # битая дата
    (1, 17): {"asset_type": "Сканер 3D"},         # типа нет в справочнике
    # источник 2 (выгрузка CMDB)
    (2, 5): {"status": "Пришло в негодность"},    # статус не из справочника
    (2, 9): {"status": ""},                       # статус пустой
    (2, 10): {"serial_number": "SN00123"},        # серийный номер без дефиса
    (2, 13): {"location": "Офис 999"},            # расхождение местоположения
    # источник 3 (акт инвентаризации)
    (3, 8): {"responsible_person": ""},           # пропущен МОЛ
    (3, 12): {"status": "На складе"},             # расхождение статуса
    (3, 14): {"responsible_person": "Сидоров В.В."},  # расхождение МОЛ
}

SOURCES = [
    {
        "id": 1,
        "file": "source_1_buh.xlsx",
        "kind": "xlsx",
        "header": [
            "Наименование", "Тип оборудования", "Вендор", "Модель",
            "Инвентаризационный номер", "Сер. №", "Характеристики",
            "Состояние", "МОЛ", "Местонахождение", "Дата закупки",
        ],
    },
    {
        "id": 2,
        "file": "source_2_cmdb.csv",
        "kind": "csv",
        "delimiter": ";",
        "encoding": "utf-8",
        "header": [
            "Сетевое имя", "Вид оборудования", "Изготовитель", "Модель",
            "Инв. №", "S/N", "Описание", "Текущее состояние",
            "Ответственный", "Место установки", "Дата установки",
        ],
        "skip_assets": {15},   # актив отсутствует в этом источнике
    },
    {
        "id": 3,
        "file": "source_3_act.csv",
        "kind": "csv",
        "delimiter": ",",
        "encoding": "cp1251",
        "header": [
            "Название", "Тип", "Производитель", "Модель",
            "Инв номер", "S/N", "Технические характеристики",
            "Статус", "МОЛ", "Местоположение", "Дата ввода в эксплуатацию",
        ],
    },
]


def base_row(asset: tuple) -> dict:
    num, name, asset_type, manufacturer, model = asset
    return {
        "name": name,
        "asset_type": asset_type,
        "manufacturer": manufacturer,
        "model": model,
        "inventory_number": f"ИНВ-{num:05d}",
        "serial_number": f"SN-{num:05d}",
        "specs": "Intel Core i5 / 8 ГБ ОЗУ / SSD 256",
        "status": "В эксплуатации",
        "responsible_person": "Иванов И.И.",
        "location": f"Офис {100 + num}",
        "commissioning_date": "15.03.2024",
    }


def apply_tweaks(source_id: int, row: dict, asset_num: int) -> None:
    for field, value in TWEAKS.get((source_id, asset_num), {}).items():
        row[field] = value


def special_rows(source_id: int) -> list[list[str]]:
    """Строки, созданные специально ради ошибки: мусор, дубли, конфликты."""
    rows: list[list[str]] = []

    if source_id == 1:
        # Число колонок не совпадает с шапкой (11), в конце есть данные.
        for junk_num in (1, 2):
            row = {field: "" for field in FIELDS}
            row["name"] = f"Мусор-{junk_num:03d}"
            row["asset_type"] = "Рабочая станция"
            row["inventory_number"] = f"ИНВ-9{junk_num:04d}"
            values = [row[field] for field in FIELDS]
            values.extend(["лишнее-1", "лишнее-2"])   # 13 значений вместо 11
            rows.append(values)

    if source_id == 2:
        # Точная копия строки актива 6: дубликат внутри источника.
        asset = ASSETS[5]
        row = base_row(asset)
        rows.append([row[field] for field in FIELDS])

    if source_id == 3:
        base = base_row(ASSETS[-1])
        # Конфликт имён: одинаковое название, разные инв. номера.
        for inv in ("ИНВ-00021", "ИНВ-00210"):
            row = dict(base)
            row["name"] = "ПК-021"
            row["inventory_number"] = inv
            rows.append([row[field] for field in FIELDS])
        # Конфликт инв. номеров: одинаковый номер, разные названия.
        for name in ("ПК-022", "Сервер-022"):
            row = dict(base)
            row["name"] = name
            row["inventory_number"] = "ИНВ-00022"
            rows.append([row[field] for field in FIELDS])

    return rows


def build_rows(source: dict) -> list[list[str]]:
    rows: list[list[str]] = []
    skip = source.get("skip_assets", set())

    for asset in ASSETS:
        if asset[0] in skip:
            continue

        row = base_row(asset)
        apply_tweaks(source["id"], row, asset[0])
        rows.append([row[field] for field in FIELDS])

    rows.extend(special_rows(source["id"]))
    return rows


def write_xlsx(path: Path, header: list[str], rows: list[list[str]]) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(header)
    for row in rows:
        sheet.append(row)
    workbook.save(path)


def write_csv(
    path: Path,
    header: list[str],
    rows: list[list[str]],
    delimiter: str,
    encoding: str,
) -> None:
    with open(path, "w", encoding=encoding, newline="") as file:
        writer = csv.writer(file, delimiter=delimiter)
        writer.writerow(header)
        writer.writerows(rows)


def write_expected() -> None:
    files = {
        source["id"]: DEMO_DIR / source["file"]
        for source in SOURCES
    }
    result = run_pipeline(files, expected_source_ids=EXPECTED_SOURCE_IDS)
    report = build_report(result, ReportMeta())

    seeded_codes = {
        "BAD_COLUMN_COUNT", "DUP_IN_SOURCE", "NAME_CONFLICT",
        "INVENTORY_CONFLICT", "MISSING_FIELD", "INVALID_STATUS",
        "BAD_FORMAT", "INVALID_ASSET_TYPE", "FIELD_MISMATCH",
        "MISSING_IN_SOURCE",
    }
    missing = seeded_codes - set(report.summary.by_code)
    if missing:
        raise RuntimeError(f"Посеянные ошибки не найдены в прогоне: {sorted(missing)}")

    payload = {
        "summary": report.summary.model_dump(),
        "by_code": report.summary.by_code,
    }
    (DEMO_DIR / "expected.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("Ошибок всего:", report.summary.issues_total)
    for code, count in report.summary.by_code.items():
        print(f"  {code}: {count}")


def main() -> None:
    DEMO_DIR.mkdir(parents=True, exist_ok=True)

    for source in SOURCES:
        path = DEMO_DIR / source["file"]
        rows = build_rows(source)
        if source["kind"] == "xlsx":
            write_xlsx(path, source["header"], rows)
        else:
            write_csv(path, source["header"], rows,
                      source["delimiter"], source["encoding"])
        print(f"Записан {path.name}: строк с данными {len(rows)}")

    write_expected()
    print(f"Ожидаемый результат: {DEMO_DIR / 'expected.json'}")


if __name__ == "__main__":
    main()
