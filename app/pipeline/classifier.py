from app.domain.schemas import IssueCode, Severity

# Итоговая критичность по коду ошибки.
# HIGH  — ломает сопоставление или ведёт к неверной карточке актива
# MEDIUM — актив опознан, но данные расходятся
# LOW   — пропуски и формат, которые не мешают сверке
ISSUE_SEVERITY: dict[IssueCode, Severity] = {
    IssueCode.PARENT_REJECTED: Severity.HIGH,
    IssueCode.INVENTORY_CONFLICT: Severity.HIGH,
    IssueCode.DUP_CROSS_SOURCE: Severity.HIGH,
    IssueCode.MISSING_IN_SOURCE: Severity.HIGH,

    IssueCode.FIELD_MISMATCH: Severity.MEDIUM,
    IssueCode.INVALID_STATUS: Severity.MEDIUM,
    IssueCode.NAME_CONFLICT: Severity.MEDIUM,
    IssueCode.DUP_IN_SOURCE: Severity.MEDIUM,
    IssueCode.NO_PARENT: Severity.MEDIUM,

    IssueCode.MISSING_FIELD: Severity.LOW,
    IssueCode.BAD_FORMAT: Severity.LOW,
    IssueCode.INVALID_ASSET_TYPE: Severity.LOW,
    IssueCode.BAD_COLUMN_COUNT: Severity.LOW,
}

# Порядок для сортировки отчёта: чем меньше число, тем выше в списке.
SEVERITY_ORDER: dict[Severity, int] = {
    Severity.HIGH: 0,
    Severity.MEDIUM: 1,
    Severity.LOW: 2,
}


def _severity_for(code: IssueCode) -> Severity:
    """Критичность по коду; для нового кода без записи в таблице — MEDIUM."""
    return ISSUE_SEVERITY.get(code, Severity.MEDIUM)
