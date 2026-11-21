import argparse
from pathlib import Path

from app.domain.schemas import AssetGroup, Issue, NormalizedRecord, ParseResult, PipelineResult
from app.pipeline.classifier import classify_issues
from app.pipeline.detectors import run_detectors
from app.pipeline.matcher import match_records
from app.pipeline.parser import parse_file
from app.rules.loader import Rules, load_rules


def run_pipeline(
    files: dict[int, Path],
    batch_id: int = 1,
    rules: Rules | None = None,
) -> PipelineResult:
    """Полный прогон: разбор файлов → сопоставление → расхождения → сортировка.

    files: {source_id: путь к файлу}. source_id — номер источника,
    batch_id — номер загрузки (один прогон = одна загрузка).
    """
    if rules is None:
        rules = load_rules()

    records: list[NormalizedRecord] = []
    issues: list[Issue] = []

    # 1. Разбираем каждый файл: строки → записи + ошибки этих строк.
    for source_id, path in files.items():
        parsed: ParseResult = parse_file(path, source_id, batch_id, rules)
        records.extend(parsed.records)
        issues.extend(parsed.issues)

    # 2. Склеиваем записи разных источников в активы.
    groups: list[AssetGroup] = match_records(records)

    # 3. Ищем то, что видно только на уровне группы.
    issues.extend(run_detectors(groups))

    # 4. Выстраиваем ошибки для отчёта: HIGH → MEDIUM → LOW.
    return PipelineResult(
        records=records,
        groups=groups,
        issues=classify_issues(issues),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Сверка ИТ-активов из CSV/XLSX")
    parser.add_argument("files", nargs="+", type=Path, help="файлы источников")
    parser.add_argument("--batch-id", type=int, default=1, help="номер загрузки")
    args = parser.parse_args()

    files = {source_id: path for source_id, path in enumerate(args.files, start=1)}
    result = run_pipeline(files, batch_id=args.batch_id)

    print(f"Записей: {len(result.records)}")
    print(f"Групп:   {len(result.groups)}")
    print(f"Ошибок:  {len(result.issues)}")
    for issue in result.issues:
        print(f"[{issue.severity.value}] {issue.code.value}: {issue.message}")


if __name__ == "__main__":
    main()
