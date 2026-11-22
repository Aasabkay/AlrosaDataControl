import pytest

from app.pipeline.parser import parse_file
from app.pipeline.readers import read_rows
from app.rules.loader import load_rules
from app.domain.schemas import IssueCode


@pytest.fixture(scope="module")
def rules():
    return load_rules()

HEADER = "Наименование;Тип;Инвентарный номер"
ROW = "ПК-01;Рабочая станция;ИНВ-001"


def write_csv(tmp_path, text: str, encoding="utf-8"):
    path = tmp_path / "test.csv"
    path.write_bytes(text.encode(encoding))
    return path


def test_semicolon_delimiter(tmp_path):
    path = write_csv(tmp_path, HEADER + "\n" + ROW)
    rows = list(read_rows(path))
    assert rows[0] == (1, ["Наименование", "Тип", "Инвентарный номер"])
    assert rows[1] == (2, ["ПК-01", "Рабочая станция", "ИНВ-001"])

def test_cp1251_encoding(tmp_path):
    path = write_csv(tmp_path, HEADER + "\n" + ROW, encoding="cp1251")
    rows = list(read_rows(path))
    assert rows[1] == (2, ["ПК-01", "Рабочая станция", "ИНВ-001"])

def test_empty_rows_skipped_but_numbers_kept(tmp_path):
    path = write_csv(tmp_path, HEADER + "\n\n\n" + ROW)
    rows = list(read_rows(path))
    assert len(rows) == 2
    assert rows[1][0] == 4

def test_unknown_column_ignored(tmp_path, rules):
    text = HEADER + ";Комментарий\n" + ROW + ";привет"
    result = parse_file(write_csv(tmp_path, text), 1, 1, rules)
    assert len(result.records) == 1
    assert result.records[0].name == "ПК-01"
    assert result.records[0].serial_number is None

def test_bad_column_count(tmp_path, rules):
    text = HEADER + "\nПК-01;Рабочая станция"
    result = parse_file(write_csv(tmp_path, text), 1, 1, rules)
    assert result.records == []
    assert [i.code for i in result.issues] == [IssueCode.BAD_COLUMN_COUNT]

def test_unsupported_extension(tmp_path):
    path = tmp_path / "test.txt"
    path.write_text(HEADER)
    with pytest.raises(ValueError):
        read_rows(path)
