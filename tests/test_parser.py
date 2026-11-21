from pathlib import Path

import pytest

from app.pipeline.parser import parse_file
from app.rules.loader import load_rules


@pytest.fixture(scope="module")
def rules():
    return load_rules()

current_dir = Path(__file__).parent
test_full_path = current_dir.parent / "sample_data" / "test_full.xlsx"
test_full_cp1251_path = current_dir.parent / "sample_data" / "test_full_cp1251.csv"
case_sample_csv_path = current_dir.parent / "sample_data" / "case_sample.csv"
test_full_utf8_path = current_dir.parent / "sample_data" / "test_full_utf8.csv"
test_empty_values_path = current_dir.parent / "sample_data" / "test_empty_values.xlsx"

@pytest.mark.parametrize("path, source_id, batch_id, records, issues", [
    (test_full_utf8_path,   1, 1, 14, 16),
    (test_full_path,        2, 1, 14, 16),
    (test_full_cp1251_path, 3, 1, 14, 16),
    (case_sample_csv_path,  4, 1,  1,  4),
    (test_empty_values_path, 5, 1, 13, 21)
])
def test_parser_result(rules, path, source_id, batch_id, records, issues):
    result = parse_file(path, source_id, batch_id, rules)
    assert len(result.records) == records
    assert len(result.issues) == issues


def codes_by_row(result) -> dict[int, list]:
    """Раскладывает коды Issue по номерам строк: {2: [BAD_COLUMN_COUNT], ...}."""
    by_row = {}
    for issue in result.issues:
        for ref in issue.refs:
            by_row.setdefault(ref.row_number, []).append(issue.code)
    return by_row

def test_case_sample_codes(rules):
    """Проверяем не количество, а КОНКРЕТНЫЕ коды на конкретных строках кейса."""
    from app.domain.schemas import IssueCode

    result = parse_file(case_sample_csv_path, 1, 1, rules)
    by_row = codes_by_row(result)

    # строки 2, 4, 5: 8 значений при 9 колонках шапки
    assert by_row[2] == [IssueCode.BAD_COLUMN_COUNT]
    assert by_row[4] == [IssueCode.BAD_COLUMN_COUNT]
    assert by_row[5] == [IssueCode.BAD_COLUMN_COUNT]

    # строка 3 (ПК-05): колонок хватает, но в "Статус" съехало ФИО
    assert by_row[3] == [IssueCode.INVALID_STATUS]

    # прошла только строка 3
    assert len(result.records) == 1
    assert result.records[0].name == "ПК-05"
