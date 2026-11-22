"""Демо-запуск: сверка файлов и выгрузка отчёта в JSON/XLSX.

Пример:
    python -m tools.make_report sample_data/case_sample.csv \
        --organization "ООО «Тест»" --responsible "Иванов И.И." \
        --json report.json --xlsx report.xlsx
"""
import argparse
from pathlib import Path

from app.pipeline.report import (
    ReportMeta,
    build_report,
    write_report_json,
    write_report_xlsx,
)
from app.pipeline.runner import run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Сверка активов и выгрузка отчёта")
    parser.add_argument("files", nargs="+", type=Path, help="файлы источников")
    parser.add_argument("--organization", default="", help="название организации")
    parser.add_argument("--responsible", default="", help="ответственный за сверку")
    parser.add_argument("--batch-id", type=int, default=1, help="номер загрузки")
    parser.add_argument("--json", type=Path, dest="json_path", help="куда сохранить JSON")
    parser.add_argument("--xlsx", type=Path, dest="xlsx_path", help="куда сохранить Excel")
    args = parser.parse_args()

    files = {source_id: path for source_id, path in enumerate(args.files, start=1)}
    result = run_pipeline(files, batch_id=args.batch_id)
    report = build_report(
        result,
        ReportMeta(organization=args.organization, responsible=args.responsible),
    )

    if args.json_path:
        write_report_json(args.json_path, report)
        print(f"JSON сохранён: {args.json_path}")
    if args.xlsx_path:
        write_report_xlsx(args.xlsx_path, report)
        print(f"Excel сохранён: {args.xlsx_path}")

    summary = report.summary
    print(f"Активов: {summary.assets_total}, с замечаниями: {summary.assets_with_issues}")
    print(
        f"Ошибок: {summary.issues_total}; исключено строк: {summary.excluded_rows}; "
        f"дублей: {summary.duplicates}; пропусков и статусов: {summary.missing_or_status}; "
        f"расхождений: {summary.mismatches}"
    )


if __name__ == "__main__":
    main()
