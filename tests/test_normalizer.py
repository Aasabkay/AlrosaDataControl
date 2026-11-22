from datetime import date

import pytest

from app.domain.schemas import IssueCode, RowRef
from app.pipeline.normalizer import normalize_row
from app.rules.loader import load_rules


@pytest.fixture(scope="module")
def rules():
    return load_rules()

REF = RowRef(source_id=1, batch_id=1, row_number=2)

def base_data() -> dict:
    return {
        "name": "ПК-01",
        "asset_type": "Рабочая станция",
        "inventory_number": "ИНВ-001",
        "serial_number": "SN-123",
        "status": "в эксплуатации",
        "commissioning_date": "15.03.2024",
        "manufacturer": "HP",
        "location": "Офис",
        "responsible_person": "Иванов И.И.",
    }

def norm(rules, **changes) -> tuple:
    data = base_data()
    data.update(changes)
    return normalize_row(data, REF, rules, raw={})

def codes(issues) -> list:
    return [i.code for i in issues]


def test_valid_row_has_no_issues(rules):
    record, issues = norm(rules)
    assert issues == []
    assert record.status == "В эксплуатации"
    assert record.commissioning_date == date(2024, 3, 15)
    assert record.category == "endpoint"

@pytest.mark.parametrize("field", ["name", "asset_type", "inventory_number", "status"])
def test_missing_required_field(rules, field):
    record, issues = norm(rules, **{field: ""})
    assert record is not None
    assert IssueCode.MISSING_FIELD in codes(issues)
    assert any(i.code == IssueCode.MISSING_FIELD and i.field == field for i in issues)

def test_status_synonym(rules):
    record, issues = norm(rules, status="активный")
    assert record.status == "В эксплуатации"
    assert issues == []

def test_invalid_status(rules):
    record, issues = norm(rules, status="активн")
    assert record.status is None
    assert record.status_raw == "активн"
    issue = next(i for i in issues if i.code == IssueCode.INVALID_STATUS)
    assert issue.suggestion is not None

@pytest.mark.parametrize("bad_inv", ["12345", "ИНВ-12", "ИНВ-1234567", "XX-123"])
def test_bad_inventory_number_format(rules, bad_inv):
    _, issues = norm(rules, inventory_number=bad_inv)
    issue = next(i for i in issues if i.code == IssueCode.BAD_FORMAT)
    assert issue.field == "inventory_number"

def test_ip_in_serial_number(rules):
    _, issues = norm(rules, serial_number="145.89.128.10")
    issue = next(i for i in issues if i.code == IssueCode.BAD_FORMAT)
    assert issue.field == "serial_number"

def test_bad_date_format(rules):
    record, issues = norm(rules, commissioning_date="32.13.2024")
    assert record.commissioning_date is None
    issue = next(i for i in issues if i.code == IssueCode.BAD_FORMAT)
    assert issue.field == "commissioning_date"

def test_iso_date_also_parses(rules):
    record, issues = norm(rules, commissioning_date="2024-03-15")
    assert record.commissioning_date == date(2024, 3, 15)
    assert issues == []

def test_unknown_asset_type(rules):
    record, issues = norm(rules, asset_type="Телефон")
    assert record.asset_type == "Телефон"
    assert record.category is None
    assert IssueCode.INVALID_ASSET_TYPE in codes(issues)

def test_whitespace_and_case_normalized(rules):
    record, _ = norm(rules, inventory_number="  инв-001 ")
    assert record.inventory_number == "ИНВ-001"
