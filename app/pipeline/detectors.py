from app.domain.schemas import AssetGroup, FieldValue, Issue, IssueCode, Severity
from app.rules.loader import Rules, load_rules

COMPARED_FIELDS = ("status", "location", "responsible_person")
REQUIRED_FIELDS = ("location", "responsible_person")


def _detect_field_mismatch(group: AssetGroup) -> list[Issue]:
    issues: list[Issue] = []
    if len(group.records) < 2:
        return issues

    for field_name in COMPARED_FIELDS:
        unique_values = {
            getattr(r, field_name)
            for r in group.records
            if getattr(r, field_name) is not None
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


def _detect_invalid_status(group: AssetGroup) -> list[Issue]:
    issues: list[Issue] = []
    for r in group.records:
        if r.status is None and r.status_raw:
            issues.append(
                Issue(
                    code=IssueCode.INVALID_STATUS,
                    severity=Severity.MEDIUM,
                    message=f"Неизвестный статус: '{r.status_raw}'",
                    refs=[r.ref],
                    asset_key=group.asset_key,
                    field="status",
                    values=[FieldValue(ref=r.ref, value=r.status_raw)],
                )
            )
    return issues


def _detect_bad_format(group: AssetGroup, rules: Rules) -> list[Issue]:
    issues: list[Issue] = []
    ip_pattern = rules.formats["ip_address"]
    serial_pattern = rules.formats["serial_number"]
    inv_pattern = rules.formats["inventory_number"]

    for r in group.records:
        if r.serial_number:
            if ip_pattern.match(r.serial_number):
                issues.append(
                    Issue(
                        code=IssueCode.BAD_FORMAT,
                        severity=Severity.MEDIUM,
                        message=f"В поле серийного номера указан IP-адрес: '{r.serial_number}'",
                        refs=[r.ref],
                        asset_key=group.asset_key,
                        field="serial_number",
                        values=[FieldValue(ref=r.ref, value=r.serial_number)],
                    )
                )
            elif not serial_pattern.match(r.serial_number):
                issues.append(
                    Issue(
                        code=IssueCode.BAD_FORMAT,
                        severity=Severity.LOW,
                        message=f"Неверный формат серийного номера: '{r.serial_number}'",
                        refs=[r.ref],
                        asset_key=group.asset_key,
                        field="serial_number",
                        values=[FieldValue(ref=r.ref, value=r.serial_number)],
                    )
                )

        if r.inventory_number and not inv_pattern.match(r.inventory_number):
            issues.append(
                Issue(
                    code=IssueCode.BAD_FORMAT,
                    severity=Severity.LOW,
                    message=f"Неверный формат инвентарного номера: '{r.inventory_number}'",
                    refs=[r.ref],
                    asset_key=group.asset_key,
                    field="inventory_number",
                    values=[FieldValue(ref=r.ref, value=r.inventory_number)],
                )
            )

    return issues


def _detect_missing_fields(group: AssetGroup) -> list[Issue]:
    issues: list[Issue] = []
    for r in group.records:
        if r.status is None and not r.status_raw:
            issues.append(
                Issue(
                    code=IssueCode.MISSING_FIELD,
                    severity=Severity.LOW,
                    message="Не заполнено обязательное поле 'status'",
                    refs=[r.ref],
                    asset_key=group.asset_key,
                    field="status",
                )
            )

        for field_name in REQUIRED_FIELDS:
            if getattr(r, field_name) is None:
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


def run_detectors(groups: list[AssetGroup], rules: Rules | None = None) -> list[Issue]:
    if rules is None:
        rules = load_rules()

    issues: list[Issue] = []
    for group in groups:
        issues.extend(_detect_field_mismatch(group))
        issues.extend(_detect_invalid_status(group))
        issues.extend(_detect_bad_format(group, rules))
        issues.extend(_detect_missing_fields(group))

    return issues