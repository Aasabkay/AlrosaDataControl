from app.domain.schemas import Issue, Severity

# Классификация для отчёта: важность ставится там, где ошибку нашли
# (normalizer / validators / detectors), здесь мы только задаём порядок вывода.

# Чем меньше число, тем выше ошибка в списке.
SEVERITY_ORDER: dict[Severity, int] = {
    Severity.HIGH: 0,
    Severity.MEDIUM: 1,
    Severity.LOW: 2,
}


def classify_issues(issues: list[Issue]) -> list[Issue]:
    """Возвращает новый список ошибок, отсортированный HIGH → MEDIUM → LOW.

    sorted() создаёт копию, поэтому входной список не меняется.
    Сортировка стабильная: ошибки одной критичности сохраняют исходный порядок.
    """
    return sorted(issues, key=lambda issue: SEVERITY_ORDER[issue.severity])
