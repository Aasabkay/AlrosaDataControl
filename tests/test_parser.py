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

@pytest.mark.parametrize("path, source_id, batch_id, records, issues", [
    (test_full_utf8_path,   1, 1, 14, 13),
    (test_full_path,        2, 1, 14, 13),
    (test_full_cp1251_path, 3, 1, 14, 13),
    (case_sample_csv_path,  4, 1,  1,  4),
])
def test_parser_result(rules, path, source_id, batch_id, records, issues):
    result = parse_file(path, source_id, batch_id, rules)
    assert len(result.records) == records
    assert len(result.issues) == issues
