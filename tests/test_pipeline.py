import csv
from pathlib import Path

from app.domain.schemas import IssueCode, MatchStatus, Severity
from app.pipeline.classifier import SEVERITY_ORDER
from app.pipeline.runner import run_pipeline

SAMPLE_DIR = Path(__file__).parent.parent / "sample_data"

HEADER = [
    "Наименование",
    "Тип",
    "Производитель",
    "Модель",
    "Инвентарный номер",
    "Серийный номер",
    "Технические характеристики",
    "Статус",
    "Ответственный",
    "Место установки",
    "Дата ввода в эксплуатацию",
]


def write_source(path: Path, status: str, location: str) -> None:
    """Пишет минимальный валидный CSV одного источника."""
    with open(path, "w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file, delimiter=";")
        writer.writerow(HEADER)
        writer.writerow([
            "ПК-01", "Рабочая станция", "HP", "ProDesk 400",
            "ИНВ-001", "SN-12345", "Intel Core i5",
            status, "Иванов И.И.", location, "15.03.2024",
        ])


def test_pipeline_finds_mismatch_between_sources(tmp_path):
    first = tmp_path / "first.csv"
    second = tmp_path / "second.csv"
    write_source(first, status="В эксплуатации", location="Офис 101")
    write_source(second, status="На складе", location="Офис 202")

    result = run_pipeline({1: first, 2: second})

    assert len(result.records) == 2
    assert len(result.groups) == 1

    group = result.groups[0]
    assert group.match_status == MatchStatus.MATCHED
    assert len(group.records) == 2

    assert len(result.issues) == 2
    assert {issue.code for issue in result.issues} == {IssueCode.FIELD_MISMATCH}
    assert {issue.field for issue in result.issues} == {"status", "location"}
    assert all(issue.severity == Severity.MEDIUM for issue in result.issues)


def test_pipeline_keeps_parse_issues_and_sorts_them():
    result = run_pipeline({1: SAMPLE_DIR / "case_sample.csv"})

    assert len(result.records) == 1
    assert len(result.groups) == 1
    assert result.groups[0].match_status == MatchStatus.ONLY_IN_SOURCE

    assert len(result.issues) == 4
    assert result.issues[-1].code == IssueCode.INVALID_STATUS
    assert all(issue.severity == Severity.HIGH for issue in result.issues[:-1])

    order = [SEVERITY_ORDER[issue.severity] for issue in result.issues]
    assert order == sorted(order)


def test_pipeline_without_files():
    result = run_pipeline({})

    assert result.records == []
    assert result.groups == []
    assert result.issues == []


def test_pipeline_reports_assets_missing_in_expected_source():
    result = run_pipeline(
        {
            1: SAMPLE_DIR / "test_full_utf8.csv",
            2: SAMPLE_DIR / "test_full_cp1251.csv",
        },
        expected_source_ids={1, 2, 3},
    )

    missing = [
        issue for issue in result.issues
        if issue.code == IssueCode.MISSING_IN_SOURCE
    ]
    assert len(result.groups) == 14
    assert len(missing) == 14
    assert all(issue.severity == Severity.MEDIUM for issue in missing)
