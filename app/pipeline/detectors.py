from app.domain.schemas import (AssetGroup, FieldValue, Issue, IssueCode,
                                NormalizedRecord, Severity)

COMPARED_FIELDS = ("status", "location", "responsible_person")


def _detect_field_mismatch(group: AssetGroup) -> list[Issue]:
    issues: list[Issue] = []
    if len(group.records) < 2:
        return issues

    for field_name in COMPARED_FIELDS:
        unique_values = {
            getattr(r, field_name)
            for r in group.records
            if getattr(r, field_name)
        }
        if len(unique_values) > 1:
            issues.append(
                Issue(
                    code=IssueCode.FIELD_MISMATCH,
                    severity=Severity.MEDIUM,
                    message=f"Расхождение поля '{field_name}' между источниками",
                    refs=[r.ref for r in group.records],
                    asset_key=group.asset_key,
                    field=field_name,
                    values=[
                        FieldValue(ref=r.ref, value=getattr(r, field_name))
                        for r in group.records
                    ],
                )
            )
    return issues


def _detect_cross_source_duplicates(group: AssetGroup) -> list[Issue]:
    by_source: dict[int, list[NormalizedRecord]] = {}
    for record in group.records:
        by_source.setdefault(record.ref.source_id, []).append(record)

    issues: list[Issue] = []
    for source_id, records in by_source.items():
        if len(records) < 2:
            continue

        rows = ", ".join(str(record.ref.row_number) for record in records)
        issues.append(
            Issue(
                code=IssueCode.DUP_CROSS_SOURCE,
                severity=Severity.MEDIUM,
                message=f"Источник {source_id} дал несколько записей одного актива: строки {rows}",
                refs=[record.ref for record in records],
                asset_key=group.asset_key,
            )
        )
    return issues


def _detect_missing_in_source(
    group: AssetGroup,
    expected_source_ids: set[int],
) -> list[Issue]:
    if not group.records:
        return []

    present = {r.ref.source_id for r in group.records}
    missing = sorted(expected_source_ids - present)
    if not missing:
        return []

    source_list = ", ".join(str(source_id) for source_id in missing)
    return [
        Issue(
            code=IssueCode.MISSING_IN_SOURCE,
            severity=Severity.MEDIUM,
            message=f"Актив отсутствует в источниках: {source_list}",
            refs=[r.ref for r in group.records],
            asset_key=group.asset_key,
        )
    ]


def run_detectors(
    groups: list[AssetGroup],
    expected_source_ids: set[int] | None = None,
) -> list[Issue]:
    issues: list[Issue] = []
    for group in groups:
        issues.extend(_detect_field_mismatch(group))
        issues.extend(_detect_cross_source_duplicates(group))
        if expected_source_ids:
            issues.extend(_detect_missing_in_source(group, expected_source_ids))

    return issues
