from app.domain.schemas import AssetGroup, FieldValue, Issue, IssueCode, Severity

# Поля, которые сравниваем между источниками внутри одной группы.
COMPARED_FIELDS = ("status", "location", "responsible_person")

# Обязательные поля, которые не проверяет normalizer.
# Статус, форматы и остальные обязательные поля проверяются при разборе строки,
# чтобы на одно поле не появлялось две ошибки.
REQUIRED_FIELDS = ("location", "responsible_person")


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


def _detect_missing_fields(group: AssetGroup) -> list[Issue]:
    issues: list[Issue] = []
    for r in group.records:
        for field_name in REQUIRED_FIELDS:
            if not getattr(r, field_name):
                issues.append(
                    Issue(
                        code=IssueCode.MISSING_FIELD,
                        severity=Severity.LOW,
                        message=f"Не заполнено обязательное поле '{field_name}'",
                        refs=[r.ref],
                        asset_key=group.asset_key,
                        field=field_name,
                    )
                )
    return issues


def run_detectors(groups: list[AssetGroup]) -> list[Issue]:
    issues: list[Issue] = []
    for group in groups:
        issues.extend(_detect_field_mismatch(group))
        issues.extend(_detect_missing_fields(group))

    return issues
