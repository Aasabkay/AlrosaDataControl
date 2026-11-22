from collections import Counter
from datetime import date
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter
from pydantic import BaseModel, Field

from app.domain.schemas import (
    AssetGroup,
    Issue,
    IssueCategory,
    IssueCode,
    MatchStatus,
    NormalizedRecord,
)
from app.pipeline.runner import PipelineResult


class ReportMeta(BaseModel):
    organization: str = ""
    responsible: str = ""
    generated_at: date = Field(default_factory=date.today)
    period_start: date | None = None
    period_end: date | None = None
    commission: list[str] = Field(default_factory=list)


class ReportSummary(BaseModel):
    assets_total: int
    assets_with_issues: int
    ambiguous_assets: int
    issues_total: int
    excluded_rows: int
    duplicates: int
    missing_or_status: int
    mismatches: int
    by_code: dict[str, int]


class AssetRow(BaseModel):
    asset_key: str
    name: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    inventory_number: str | None = None
    serial_number: str | None = None
    asset_type: str | None = None
    location: str | None = None
    status: str | None = None
    responsible_person: str | None = None
    sources: list[int] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class Report(BaseModel):
    meta: ReportMeta
    summary: ReportSummary
    assets: list[AssetRow]
    issues: list[Issue]
    recommendations: list[str] = Field(default_factory=list)


def _first_value(records: list[NormalizedRecord], field_name: str):
    for record in records:
        value = getattr(record, field_name)
        if value:
            return value
    return None


def _issue_note(issue: Issue) -> str:
    if issue.code == IssueCode.FIELD_MISMATCH:
        return f"расхождение: {issue.field}" if issue.field else "расхождение"
    if issue.code == IssueCode.MISSING_FIELD:
        return f"не заполнено: {issue.field}"
    if issue.code == IssueCode.BAD_FORMAT:
        return f"неверный формат: {issue.field}"
    if issue.code == IssueCode.INVALID_ASSET_TYPE:
        return "тип не найден в справочнике"
    return issue.message


def _ref_key(ref) -> tuple[int, int, int]:
    return ref.source_id, ref.batch_id, ref.row_number


def _unique_refs(issues: list[Issue]) -> set[tuple[int, int, int]]:
    return {_ref_key(ref) for issue in issues for ref in issue.refs}


def _build_assets(groups: list[AssetGroup]) -> tuple[list[AssetRow], dict]:
    assets: list[AssetRow] = []
    ref_to_asset: dict[tuple[int, int, int], int] = {}
    key_to_asset: dict[str, int] = {}

    for index, group in enumerate(groups):
        key_to_asset.setdefault(group.asset_key, index)
        for record in group.records:
            ref_to_asset[_ref_key(record.ref)] = index

        assets.append(
            AssetRow(
                asset_key=group.asset_key,
                name=_first_value(group.records, "name"),
                manufacturer=_first_value(group.records, "manufacturer"),
                model=_first_value(group.records, "model"),
                inventory_number=_first_value(group.records, "inventory_number"),
                serial_number=_first_value(group.records, "serial_number"),
                asset_type=_first_value(group.records, "asset_type"),
                location=_first_value(group.records, "location"),
                status=_first_value(group.records, "status"),
                responsible_person=_first_value(group.records, "responsible_person"),
                sources=sorted({r.ref.source_id for r in group.records}),
            )
        )

    return assets, (ref_to_asset, key_to_asset)


def _fill_notes(
    assets: list[AssetRow],
    issues: list[Issue],
    ref_to_asset: dict[tuple[int, int, int], int],
    key_to_asset: dict[str, int],
) -> None:
    for issue in issues:
        note = _issue_note(issue)
        target_indexes: set[int] = set()

        if issue.asset_key is not None and issue.asset_key in key_to_asset:
            target_indexes.add(key_to_asset[issue.asset_key])

        for ref in issue.refs:
            index = ref_to_asset.get(_ref_key(ref))
            if index is not None:
                target_indexes.add(index)

        for index in target_indexes:
            if note not in assets[index].notes:
                assets[index].notes.append(note)


def _add_match_notes(assets: list[AssetRow], groups: list[AssetGroup]) -> None:
    for asset, group in zip(assets, groups):
        if group.match_status == MatchStatus.AMBIGUOUS:
            note = "неоднозначное сопоставление"
        elif group.match_status == MatchStatus.ONLY_IN_SOURCE:
            note = "есть только в одном источнике"
        else:
            continue

        if note not in asset.notes:
            asset.notes.append(note)


def _build_summary(result: PipelineResult, assets: list[AssetRow]) -> ReportSummary:
    by_category = Counter(issue.category for issue in result.issues)
    by_code = Counter(issue.code.value for issue in result.issues)

    excluded = [
        issue for issue in result.issues
        if issue.category == IssueCategory.EXCLUDED
    ]
    duplicates = [
        issue for issue in result.issues
        if issue.category == IssueCategory.DUPLICATE
    ]

    return ReportSummary(
        assets_total=len(assets),
        assets_with_issues=sum(1 for asset in assets if asset.notes),
        ambiguous_assets=sum(
            1 for group in result.groups
            if group.match_status == MatchStatus.AMBIGUOUS
        ),
        issues_total=len(result.issues),
        excluded_rows=len(_unique_refs(excluded)),
        duplicates=len(duplicates),
        missing_or_status=by_category[IssueCategory.MISSING_OR_STATUS],
        mismatches=by_category[IssueCategory.MISMATCH],
        by_code=dict(sorted(by_code.items())),
    )


def _build_recommendations(summary: ReportSummary) -> list[str]:
    items: list[str] = []

    if summary.mismatches:
        items.append(
            f"Расхождения между источниками: {summary.mismatches} — проверить вручную."
        )
    if summary.excluded_rows:
        items.append(
            f"Исключённые строки: {summary.excluded_rows} — разобрать причины."
        )
    if summary.duplicates:
        items.append(f"Дубли: {summary.duplicates} — устранить.")
    if summary.missing_or_status:
        items.append(
            f"Пропуски и некорректные статусы: {summary.missing_or_status} — заполнить или исправить."
        )
    if summary.ambiguous_assets:
        items.append(
            f"Неоднозначное сопоставление: {summary.ambiguous_assets} — подтвердить вручную."
        )

    if not items:
        items.append("Существенных проблем не найдено.")

    return items


def build_report(result: PipelineResult, meta: ReportMeta) -> Report:
    assets, maps = _build_assets(result.groups)
    _fill_notes(assets, result.issues, *maps)
    _add_match_notes(assets, result.groups)

    summary = _build_summary(result, assets)

    return Report(
        meta=meta,
        summary=summary,
        assets=assets,
        issues=list(result.issues),
        recommendations=_build_recommendations(summary),
    )


def report_to_json(report: Report) -> str:
    return report.model_dump_json(indent=2)


def write_report_json(path: Path, report: Report) -> None:
    path.write_text(report_to_json(report), encoding="utf-8")


def _format_date(value: date | None) -> str:
    return value.strftime("%d.%m.%Y") if value else "—"


def _append_section(sheet, title: str, rows: list[tuple]) -> None:
    sheet.append((title, ""))
    sheet.cell(row=sheet.max_row, column=1).font = Font(bold=True)
    for row in rows:
        sheet.append(row)


def _write_summary_sheet(sheet, report: Report) -> None:
    meta = report.meta
    summary = report.summary

    _append_section(sheet, "Шапка", [
        ("Организация", meta.organization),
        ("Ответственный", meta.responsible),
        ("Дата составления", _format_date(meta.generated_at)),
        (
            "Период инвентаризации",
            f"{_format_date(meta.period_start)} — {_format_date(meta.period_end)}",
        ),
        ("Комиссия", ", ".join(meta.commission) or "—"),
    ])
    sheet.append(("", ""))

    _append_section(sheet, "Классификация ошибок", [
        ("Всего активов", summary.assets_total),
        ("Активов с замечаниями", summary.assets_with_issues),
        ("Неоднозначное сопоставление", summary.ambiguous_assets),
        ("Всего ошибок", summary.issues_total),
        ("Исключено строк", summary.excluded_rows),
        ("Дублей", summary.duplicates),
        ("Пропуски и статусы", summary.missing_or_status),
        ("Расхождения", summary.mismatches),
    ])
    sheet.append(("", ""))

    _append_section(sheet, "По кодам ошибок", list(summary.by_code.items()))
    sheet.append(("", ""))

    _append_section(
        sheet,
        "Выводы",
        [(text, "") for text in report.recommendations],
    )
    first_recommendation = sheet.max_row - len(report.recommendations) + 1
    for row in range(first_recommendation, sheet.max_row + 1):
        sheet.merge_cells(start_row=row, start_column=1, end_row=row, end_column=2)
        sheet.cell(row=row, column=1).alignment = Alignment(wrap_text=True, vertical="top")

    sheet.column_dimensions["A"].width = 32
    sheet.column_dimensions["B"].width = 60


def _write_assets_sheet(sheet, report: Report) -> None:
    headers = [
        "Наименование", "Производитель", "Модель", "Инв. номер",
        "Серийный номер", "Тип", "Местоположение", "Состояние",
        "Ответственный", "Источники", "Примечания",
    ]
    sheet.append(headers)

    for asset in report.assets:
        sheet.append([
            asset.name,
            asset.manufacturer,
            asset.model,
            asset.inventory_number,
            asset.serial_number,
            asset.asset_type,
            asset.location,
            asset.status,
            asset.responsible_person,
            ", ".join(str(source) for source in asset.sources),
            "; ".join(asset.notes),
        ])

    for cell in sheet[1]:
        cell.font = Font(bold=True)
    sheet.freeze_panes = "A2"
    _set_widths(sheet, [30, 18, 22, 16, 18, 20, 30, 18, 24, 12, 45])


def _format_values(issue: Issue) -> str:
    return "; ".join(
        f"источник {value.ref.source_id}, строка {value.ref.row_number}: {value.value}"
        for value in issue.values
    )


def _write_issues_sheet(sheet, report: Report) -> None:
    headers = [
        "Категория", "Код", "Критичность", "Поле", "Сообщение",
        "Значения по источникам", "Подсказка", "Строки", "Актив",
    ]
    sheet.append(headers)

    for issue in report.issues:
        refs = "; ".join(
            f"источник {ref.source_id}, строка {ref.row_number}"
            for ref in issue.refs
        )
        sheet.append([
            issue.category.value,
            issue.code.value,
            issue.severity.value,
            issue.field,
            issue.message,
            _format_values(issue),
            issue.suggestion,
            refs,
            issue.asset_key,
        ])

    for cell in sheet[1]:
        cell.font = Font(bold=True)
    sheet.freeze_panes = "A2"
    _set_widths(sheet, [18, 22, 12, 18, 55, 45, 30, 35, 20])


def _set_widths(sheet, widths: list[int]) -> None:
    for index, width in enumerate(widths, start=1):
        sheet.column_dimensions[get_column_letter(index)].width = width


def write_report_xlsx(path: Path, report: Report) -> None:
    workbook = Workbook()

    summary_sheet = workbook.active
    summary_sheet.title = "Сводка"
    _write_summary_sheet(summary_sheet, report)

    _write_assets_sheet(workbook.create_sheet("Активы"), report)
    _write_issues_sheet(workbook.create_sheet("Ошибки"), report)

    workbook.save(path)
