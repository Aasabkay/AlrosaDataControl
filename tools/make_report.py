import argparse
from datetime import date
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
    parser.add_argument("--period-start", type=date.fromisoformat, help="начало периода, ГГГГ-ММ-ДД")
    parser.add_argument("--period-end", type=date.fromisoformat, help="конец периода, ГГГГ-ММ-ДД")
    parser.add_argument(
        "--commission",
        action="append",
        default=[],
        help="член комиссии (можно указать несколько раз)",
    )
    parser.add_argument(
        "--expected-source",
        type=int,
        action="append",
        dest="expected_sources",
        help="источник, который обязан содержать все активы (можно указать несколько раз)",
    )
    parser.add_argument("--batch-id", type=int, default=1, help="номер загрузки")
    parser.add_argument("--json", type=Path, dest="json_path", help="куда сохранить JSON")
    parser.add_argument("--xlsx", type=Path, dest="xlsx_path", help="куда сохранить Excel")
    args = parser.parse_args()

    files = {source_id: path for source_id, path in enumerate(args.files, start=1)}
    expected = set(args.expected_sources) if args.expected_sources else None
    result = run_pipeline(
        files,
        batch_id=args.batch_id,
        expected_source_ids=expected,
    )
    report = build_report(
        result,
        ReportMeta(
            organization=args.organization,
            responsible=args.responsible,
            period_start=args.period_start,
            period_end=args.period_end,
            commission=args.commission,
        ),
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
