from enum import StrEnum
from pathlib import Path

from app.domain.schemas import RowRef, Issue, IssueCode, Severity, NormalizedRecord, ParseResult
from app.pipeline.normalizer import normalize_row
from app.pipeline.readers import read_rows
from app.pipeline.validators import find_duplicates, find_conflicts, build_names, resolve_parents
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

        row_status[row_number] = RowStatus.ACCEPTED
        data = {} # data = {"name": "ПК-01", "asset_type": "Рабочая станция", ...}
        for index, value in enumerate(cells):
            field = field_map.get(index)
            if field:
                data[field] = value

        raw = dict(zip(header[:header_len], cells))

        record, row_issues = normalize_row(data, row_ref, rules, raw)
        records.append(record)
        issues.extend(row_issues)

    dup_excluded, dup_issues = find_duplicates(records)
    remaining = [r for r in records if r.ref.row_number not in dup_excluded]
    conflict_excluded, conflict_issues = find_conflicts(remaining)

    excluded = dup_excluded | conflict_excluded
    for row in excluded:
        row_status[row] = RowStatus.REJECTED
    issues.extend(conflict_issues)
    issues.extend(dup_issues)

    names = build_names(records, excluded)

    parent_excluded, parent_issues = resolve_parents(records, names, rejected_cells, row_status, RowStatus)
    issues.extend(parent_issues)
    for row in parent_excluded:
        row_status[row] = RowStatus.REJECTED


    accepted = [r for r in records if row_status[r.ref.row_number] == RowStatus.ACCEPTED]
    return ParseResult(records=accepted, issues=issues)


