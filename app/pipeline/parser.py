import csv
import io
import re
from datetime import datetime, date
from difflib import get_close_matches
from enum import StrEnum
from pathlib import Path
from typing import Iterator

from openpyxl.reader.excel import load_workbook

from app.domain.schemas import RowRef, FieldValue, Issue, IssueCode, Severity, NormalizedRecord
from app.rules.loader import Rules, normalize_key


class RowStatus(StrEnum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"

def decode_bytes(data: bytes) -> str:
    for enc in ("utf-8-sig", "cp1251"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    raise ValueError("Не удалось определить кодировку")

CANDIDATES = [";", ",", "\t", "|"]

def detect_delimiter(text: str) -> str:
    for line in text.splitlines():
        if line.strip():
            header = line
            break
    else:
        return ","

    counts = {d: header.count(d) for d in CANDIDATES}
    best = max(counts, key=counts.get)
    return best if counts[best] > 0 else ","

def read_csv_rows(path: Path):
    text = decode_bytes(path.read_bytes())
    delimiter = detect_delimiter(text)
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter)
    for row in reader:
        row_number = reader.line_num
        cells = [cell.strip() for cell in row]
        if not any(cells):
            continue

        yield row_number, cells

def cell_to_str(cell) -> str:
    if cell is None:
        return ""

    if isinstance(cell, (datetime, date)):
        return cell.strftime("%d.%m.%Y")
    if isinstance(cell, float) and cell.is_integer():
        return str(int(cell))

    return str(cell).strip()

def read_xlsx_rows(path: Path):
    wb = load_workbook(path, read_only=True, data_only=True)
    try:
        ws = wb.active
        width = None
        for row_number, row in enumerate(ws.iter_rows(values_only=True), start=1):
            cells = [cell_to_str(value) for value in row]
            if not any(cells):
                continue
            if width is None:
                width = len(cells)
                while width and not cells[width - 1]:
                    width -= 1
            elif len(cells) < width:
                cells += [""] * (width - len(cells))

            yield row_number, cells
    finally:
        wb.close()

def read_rows(path: Path) -> Iterator[tuple[int, list[str]]]:
    readers = {
        ".csv": read_csv_rows,
        ".xlsx": read_xlsx_rows,
    }
    reader = readers.get(path.suffix.lower())
    if reader is None:
        raise ValueError(f"Неподдерживаемый формат файла: {path.suffix!r}")

    return reader(path)

def clean_key(key: str | None) -> str | None:
    if not key:
        return None
    key = "".join(key.split()).upper()
    return key

def clean_text(value: str | None) -> str | None:
    if not value:
        return None
    value = " ".join(value.split())
    return value

def suggest_status(raw: str, rules: Rules) -> str | None:
    key = normalize_key(raw)
    matches = get_close_matches(key, rules.statuses.keys(), n=1, cutoff=0.6)
    return rules.statuses[matches[0]] if matches else None

def parse_date(value: str) -> date | None:
    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None

def normalize_row(data: dict, ref: RowRef, rules: Rules, raw: dict) -> tuple[NormalizedRecord, list[Issue]]:
    issues: list[Issue] = []

    inventory_number = clean_key(data.get("inventory_number"))
    serial_number = clean_key(data.get("serial_number"))
    name = clean_text(data.get("name"))
    type_raw = clean_text(data.get("asset_type"))

    manufacturer = clean_text(data.get("manufacturer"))
    model = clean_text(data.get("model"))
    specs = clean_text(data.get("specs"))

    responsible_person = clean_text(data.get("responsible_person"))
    location = clean_text(data.get("location"))

    for field, value in (("name", name), ("asset_type", type_raw),
                         ("inventory_number", inventory_number)):
        if not value:
            issues.append(Issue(refs=[ref], code=IssueCode.MISSING_FIELD, severity=Severity.MEDIUM,
                                message=f"Поле {field} пустое", field=field))

    found = rules.asset_type(type_raw) if type_raw else None
    if not found:
        issues.append(Issue(refs=[ref], code=IssueCode.INVALID_ASSET_TYPE,
                            severity=Severity.MEDIUM, message=f"Оборудование типа {type_raw} не найдено в справочнике",
                            field="asset_type"))
    asset_type, category = found if found else (type_raw, None)

    status_raw = clean_text(data.get("status"))
    status = None
    if status_raw is None:
        issues.append(Issue(refs=[ref], code=IssueCode.MISSING_FIELD, severity=Severity.HIGH,
                            message="Поле status пустое", field="status"))
    else:
        status = rules.status(status_raw)
        if status is None:
            suggestion = suggest_status(status_raw, rules)
            message = f"Статус «{status_raw}» не распознан"
            if suggestion:
                message += f". Возможно, имелось в виду: {suggestion}?"
            issues.append(Issue(refs=[ref], code=IssueCode.INVALID_STATUS, severity=Severity.HIGH,
                                message=message,
                                field="status",
                                suggestion=suggestion))

    inv_num_pattern = rules.formats["inventory_number"]
    if inventory_number and not inv_num_pattern.match(inventory_number):
        issues.append(Issue(refs=[ref], code=IssueCode.BAD_FORMAT, severity=Severity.HIGH,
                            message=f"Инв. номер {inventory_number} не подходит по формату. Убедитесь в правильности написания инв. номера",
                            field="inventory_number"))
    serial_num_pattern = rules.formats["serial_number"]
    if serial_number and not serial_num_pattern.match(serial_number):
        issues.append(Issue(refs=[ref], code=IssueCode.BAD_FORMAT, severity=Severity.HIGH,
                            message=f"Серийный номер {serial_number} не подходит по формату. Убедитесь в правильности написания серийного номера",
                            field="serial_number"))


    raw_date = clean_text(data.get("commissioning_date"))
    commissioning_date = parse_date(raw_date) if raw_date else None
    if raw_date and commissioning_date is None:
        issues.append(Issue(refs=[ref], code=IssueCode.BAD_FORMAT, severity=Severity.HIGH,
                            message=f"Дата «{raw_date}» не распознана", field="commissioning_date"))

    record = NormalizedRecord(ref=ref,
                              inventory_number=inventory_number,
                              serial_number=serial_number,
                              name=name,
                              asset_type=asset_type,
                              category=category,
                              manufacturer=manufacturer,
                              model=model,
                              specs=specs,
                              status=status,
                              status_raw=status_raw,
                              responsible_person=responsible_person,
                              location=location,
                              commissioning_date=commissioning_date,
                              raw=raw)

    return record, issues

def parse_file(path: Path, source_id: int, batch_id: int, rules: Rules):
    issues: list[Issue] = []
    records: list[NormalizedRecord] = []
    row_status: dict[int, RowStatus] = {}
    rejected_cells: set[str] = set()

    rows = list(read_rows(path))
    if not rows:
        raise ValueError("Файл пуст")

    _, header = rows[0]

    header_len = len(header)
    while header_len and not header[header_len - 1]:
        header_len -= 1

    field_map: dict[int, str] = {}
    for index, column in enumerate(header[:header_len]):
        field = rules.column_field(column)
        if field:
            field_map[index] = field

    data_rows = rows[1:]

    for row_number, cells in data_rows:
        if len(cells) > header_len and not any(cells[header_len:]):
            cells = cells[:header_len]

        row_ref = RowRef(source_id=source_id,
                         batch_id=batch_id,
                         row_number=row_number)

        if len(cells) != header_len:
            issues.append(Issue(code=IssueCode.BAD_COLUMN_COUNT,
                         severity=Severity.HIGH,
                         message=f"Строка {row_number}: {len(cells)} значений, в шапке {header_len}",
                         refs=[row_ref]))
            row_status[row_number] = RowStatus.REJECTED
            rejected_cells.update(normalize_key(c) for c in cells if c)
            continue

        data = {} # data = {"name": "ПК-01", "asset_type": "Рабочая станция", ...}
        for index, value in enumerate(cells):
            field = field_map.get(index)
            if field:
                data[field] = value

        raw = dict(zip(header[:header_len], cells))

        record, row_issues = normalize_row(data, row_ref, rules, raw)
        records.append(record)
        issues.extend(row_issues)

    return records, issues


