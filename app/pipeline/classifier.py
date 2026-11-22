from app.domain.schemas import Issue, Severity


SEVERITY_ORDER: dict[Severity, int] = {
    Severity.HIGH: 0,
    Severity.MEDIUM: 1,
    Severity.LOW: 2,
}


def classify_issues(issues: list[Issue]) -> list[Issue]:
    return sorted(issues, key=lambda issue: SEVERITY_ORDER[issue.severity])
