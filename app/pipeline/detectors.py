from app.domain.schemas import AssetGroup, FieldValue, Issue, IssueCode, Severity

# Поля, которые сравниваем между источниками внутри одной группы.
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


def _detect_missing_in_source(
    group: AssetGroup,
    expected_source_ids: set[int],
) -> list[Issue]:
    """Актив есть в одних источниках, но отсутствует в других.

    Проверка включается только когда вызывающий явно передал список источников:
    не каждый источник содержит полный перечень активов, поэтому по умолчанию
    такие ошибки не создаются.
    """
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
    """Межгрупповые проверки. Проверки внутри одной строки живут в normalizer.

    expected_source_ids: источники, которые обязаны содержать все активы.
    Если не передать — проверка MISSING_IN_SOURCE пропускается.
    """
    issues: list[Issue] = []
    for group in groups:
        issues.extend(_detect_field_mismatch(group))
        if expected_source_ids:
            issues.extend(_detect_missing_in_source(group, expected_source_ids))

    return issues
