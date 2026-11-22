import argparse
from pathlib import Path

from pydantic import BaseModel

from app.domain.schemas import AssetGroup, Issue, NormalizedRecord, ParseResult
from app.pipeline.classifier import classify_issues
from app.pipeline.detectors import run_detectors
from app.pipeline.matcher import match_records
from app.pipeline.parser import parse_file
from app.rules.loader import Rules, load_rules


class PipelineResult(BaseModel):
    records: list[NormalizedRecord]   
    groups: list[AssetGroup]          
    issues: list[Issue]               


def run_pipeline(
    files: dict[int, Path],
    batch_id: int = 1,
    rules: Rules | None = None,
    expected_source_ids: set[int] | None = None,
) -> PipelineResult:
    if rules is None:
        rules = load_rules()

    records: list[NormalizedRecord] = []
    issues: list[Issue] = []

    for source_id, path in files.items():
        parsed: ParseResult = parse_file(path, source_id, batch_id, rules)
        records.extend(parsed.records)
        issues.extend(parsed.issues)

    groups: list[AssetGroup] = match_records(records)

    issues.extend(run_detectors(groups, expected_source_ids))

    return PipelineResult(
        records=records,
        groups=groups,
        issues=classify_issues(issues),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Сверка ИТ-активов из CSV/XLSX")
    parser.add_argument("files", nargs="+", type=Path, help="файлы источников")
    parser.add_argument("--batch-id", type=int, default=1, help="номер загрузки")
    parser.add_argument(
        "--expected-source",
        type=int,
        action="append",
        dest="expected_sources",
        help="источник, который обязан содержать все активы (можно указать несколько раз)",
    )
    args = parser.parse_args()

    files = {source_id: path for source_id, path in enumerate(args.files, start=1)}
    expected = set(args.expected_sources) if args.expected_sources else None
    result = run_pipeline(files, batch_id=args.batch_id, expected_source_ids=expected)

    print(f"Записей: {len(result.records)}")
    print(f"Групп:   {len(result.groups)}")
    print(f"Ошибок:  {len(result.issues)}")
    for issue in result.issues:
        print(f"[{issue.severity.value}] {issue.code.value}: {issue.message}")


if __name__ == "__main__":
    main()
