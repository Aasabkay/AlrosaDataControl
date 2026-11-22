from app.domain.schemas import Issue, IssueCode, Severity
from app.pipeline.classifier import classify_issues


def make_issue(
    code: IssueCode,
    severity: Severity,
    message: str = "ошибка",
) -> Issue:
    return Issue(code=code, severity=severity, message=message)


def test_sorts_high_medium_low():
    low = make_issue(IssueCode.BAD_FORMAT, Severity.LOW)
    high = make_issue(IssueCode.INVENTORY_CONFLICT, Severity.HIGH)
    medium = make_issue(IssueCode.FIELD_MISMATCH, Severity.MEDIUM)

    result = classify_issues([low, high, medium])

    assert [issue.severity for issue in result] == [
        Severity.HIGH,
        Severity.MEDIUM,
        Severity.LOW,
    ]
    assert result == [high, medium, low]


def test_keeps_order_inside_same_severity():
    first = make_issue(IssueCode.FIELD_MISMATCH, Severity.MEDIUM, "первая")
    second = make_issue(IssueCode.INVALID_STATUS, Severity.MEDIUM, "вторая")

    assert classify_issues([first, second]) == [first, second]


def test_does_not_change_input_list():
    issues = [
        make_issue(IssueCode.BAD_FORMAT, Severity.LOW),
        make_issue(IssueCode.DUP_CROSS_SOURCE, Severity.HIGH),
    ]
    before = list(issues)

    classify_issues(issues)

    assert issues == before
    assert [issue.severity for issue in issues] == [Severity.LOW, Severity.HIGH]
