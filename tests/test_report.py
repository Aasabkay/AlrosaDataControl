import csv
import json
from pathlib import Path

from openpyxl import load_workbook

from app.domain.schemas import (
    AssetGroup,
    IssueCode,
    MatchMethod,
    MatchStatus,
    NormalizedRecord,
    RowRef,
)
from app.pipeline.report import (
    ReportMeta,
    build_report,
    report_to_json,
    write_report_xlsx,
)
from app.pipeline.runner import PipelineResult, run_pipeline

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
    with open(path, "w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file, delimiter=";")
        writer.writerow(HEADER)
        writer.writerow([
            "ПК-01", "Рабочая станция", "HP", "ProDesk 400",
            "ИНВ-001", "SN-12345", "Intel Core i5",
            status, "Иванов И.И.", location, "15.03.2024",
        ])


def make_record(source_id: int = 1, row: int = 1, name: str = "ПК-01") -> NormalizedRecord:
    return NormalizedRecord(
        ref=RowRef(source_id=source_id, batch_id=1, row_number=row),
        name=name,
    )


def mismatch_report(tmp_path: Path):
    first = tmp_path / "first.csv"
    second = tmp_path / "second.csv"
    write_source(first, status="В эксплуатации", location="Офис 101")
    write_source(second, status="На складе", location="Офис 202")

    result = run_pipeline({1: first, 2: second})
    meta = ReportMeta(organization="ООО «Тест»", responsible="Иванов И.И.")
    return build_report(result, meta)


def test_report_counts_excluded_rows_and_statuses():
    result = run_pipeline({1: SAMPLE_DIR / "case_sample.csv"})
    report = build_report(result, ReportMeta(organization="ООО «Тест»"))

    assert report.summary.assets_total == 1
    assert report.summary.issues_total == 4
    assert report.summary.excluded_rows == 3
    assert report.summary.missing_or_status == 1
    assert report.summary.mismatches == 0
    assert report.summary.ambiguous_assets == 0
    assert report.summary.by_code == {
        "BAD_COLUMN_COUNT": 3,
        "INVALID_STATUS": 1,
    }

    asset = report.assets[0]
    assert asset.name == "ПК-05"
    assert any("не распознан" in note for note in asset.notes)
    assert "есть только в одном источнике" in asset.notes

    assert any("Исключённые строки" in item for item in report.recommendations)


def test_report_collects_mismatch_notes(tmp_path):
    report = mismatch_report(tmp_path)

    assert report.summary.assets_total == 1
    assert report.summary.mismatches == 2

    asset = report.assets[0]
    assert asset.sources == [1, 2]
    assert "расхождение: status" in asset.notes
    assert "расхождение: location" in asset.notes


def test_report_marks_ambiguous_and_single_source_groups():
    ambiguous = AssetGroup(
        asset_key="ПК-01",
        records=[make_record(1, 1)],
        match_status=MatchStatus.AMBIGUOUS,
        match_method=MatchMethod.FUZZY,
    )
    only_in_source = AssetGroup(
        asset_key="SN-1",
        records=[make_record(2, 2, name="ПК-02")],
        match_status=MatchStatus.ONLY_IN_SOURCE,
        match_method=MatchMethod.SERIAL_NUMBER,
    )
    result = PipelineResult(
        records=[*ambiguous.records, *only_in_source.records],
        groups=[ambiguous, only_in_source],
        issues=[],
    )

    report = build_report(result, ReportMeta())

    assert report.summary.ambiguous_assets == 1
    assert "неоднозначное сопоставление" in report.assets[0].notes
    assert "есть только в одном источнике" in report.assets[1].notes


def test_report_without_problems_has_clean_recommendation():
    result = PipelineResult(records=[], groups=[], issues=[])

    report = build_report(result, ReportMeta())

    assert report.recommendations == ["Существенных проблем не найдено."]


def test_report_json_is_serializable(tmp_path):
    report = mismatch_report(tmp_path)
    payload = json.loads(report_to_json(report))

    assert payload["meta"]["organization"] == "ООО «Тест»"
    assert payload["assets"][0]["sources"] == [1, 2]
    assert payload["summary"]["mismatches"] == 2
    assert len(payload["recommendations"]) >= 1
    assert len(payload["issues"]) == 2


def test_report_xlsx_has_three_sheets_and_diff(tmp_path):
    report = mismatch_report(tmp_path)
    path = tmp_path / "report.xlsx"
    write_report_xlsx(path, report)

    workbook = load_workbook(path)
    assert workbook.sheetnames == ["Сводка", "Активы", "Ошибки"]

    assets = workbook["Активы"]
    assert assets["A1"].value == "Наименование"
    assert assets["A2"].value == "ПК-01"
    assert assets["K2"].value == "расхождение: status; расхождение: location"

    issues = workbook["Ошибки"]
    assert issues["F1"].value == "Значения по источникам"
    assert issues["F2"].value == (
        "источник 1, строка 2: В эксплуатации; источник 2, строка 2: На складе"
    )

    summary = workbook["Сводка"]
    labels = [cell.value for cell in summary["A"]]
    assert "Выводы" in labels
    assert "Неоднозначное сопоставление" in labels


def test_report_exports_status_suggestion(tmp_path):
    path = tmp_path / "source.csv"
    write_source(path, status="в эксплуотации", location="Офис 101")

    result = run_pipeline({1: path})
    report = build_report(result, ReportMeta())

    issue = next(
        issue for issue in report.issues
        if issue.code == IssueCode.INVALID_STATUS
    )
    assert issue.suggestion == "В эксплуатации"

    xlsx_path = tmp_path / "report.xlsx"
    write_report_xlsx(xlsx_path, report)
    sheet = load_workbook(xlsx_path)["Ошибки"]
    assert sheet["G1"].value == "Подсказка"
    assert sheet["G2"].value == "В эксплуатации"
