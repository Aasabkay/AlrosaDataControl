from enum import StrEnum
from pathlib import Path

from app.domain.schemas import RowRef, Issue, IssueCode, Severity, NormalizedRecord
from app.pipeline.normalizer import normalize_row
from app.pipeline.readers import read_rows
from app.rules.loader import Rules, normalize_key


class RowStatus(StrEnum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"

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


