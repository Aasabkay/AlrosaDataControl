from app.domain.schemas import (
    AssetGroup,
    IssueCode,
    MatchMethod,
    MatchStatus,
    NormalizedRecord,
    RowRef,
)
from app.pipeline.detectors import run_detectors


def make_rec(
    source_id: int = 1,
    row: int = 1,
    inv: str | None = "ИНВ-001",
    serial: str | None = "SN-12345",
    status: str | None = "В эксплуатации",
    status_raw: str | None = None,
    location: str | None = "Офис 101",
    responsible_person: str | None = "Иванов И.И.",
) -> NormalizedRecord:
    return NormalizedRecord(
        ref=RowRef(source_id=source_id, batch_id=1, row_number=row),
        inventory_number=inv,
        serial_number=serial,
        name="PC-1",
        status=status,
        status_raw=status_raw,
        location=location,
        responsible_person=responsible_person,
    )


def test_clean_group_has_no_issues():
    group = AssetGroup(
        asset_key="ИНВ-001",
        records=[make_rec(source_id=1), make_rec(source_id=2)],
        match_status=MatchStatus.MATCHED,
        match_method=MatchMethod.INVENTORY_NUMBER,
    )
    assert run_detectors([group]) == []


def test_field_mismatch_detected():
    group = AssetGroup(
        asset_key="ИНВ-001",
        records=[
            make_rec(source_id=1, status="В эксплуатации"),
            make_rec(source_id=2, status="На складе"),
        ],
        match_status=MatchStatus.MATCHED,
        match_method=MatchMethod.INVENTORY_NUMBER,
    )
    issues = run_detectors([group])
    assert len(issues) == 1
    assert issues[0].code == IssueCode.FIELD_MISMATCH
    assert issues[0].field == "status"
    assert len(issues[0].values) == 2


def test_empty_value_is_not_a_mismatch():
    """Пустая строка не считается значением: её ловит проверка пропусков."""
    group = AssetGroup(
        asset_key="ИНВ-001",
        records=[
            make_rec(source_id=1, status=""),
            make_rec(source_id=2, status="В эксплуатации"),
        ],
        match_status=MatchStatus.MATCHED,
        match_method=MatchMethod.INVENTORY_NUMBER,
    )
    assert run_detectors([group]) == []


def test_missing_required_fields_detected():
    group = AssetGroup(
        asset_key="ИНВ-004",
        records=[make_rec(location=None, responsible_person=None)],
        match_status=MatchStatus.ONLY_IN_SOURCE,
        match_method=MatchMethod.INVENTORY_NUMBER,
    )
    issues = run_detectors([group])
    assert len(issues) == 2
    assert {i.code for i in issues} == {IssueCode.MISSING_FIELD}
    assert {i.field for i in issues} == {"location", "responsible_person"}


def test_empty_string_counts_as_missing():
    group = AssetGroup(
        asset_key="ИНВ-005",
        records=[make_rec(location="")],
        match_status=MatchStatus.ONLY_IN_SOURCE,
        match_method=MatchMethod.INVENTORY_NUMBER,
    )
    issues = run_detectors([group])
    assert [(i.code, i.field) for i in issues] == [(IssueCode.MISSING_FIELD, "location")]


def test_status_checks_stay_in_normalizer():
    """Невалидный и пустой статус — забота normalizer, детекторы их не дублируют."""
    group = AssetGroup(
        asset_key="ИНВ-006",
        records=[make_rec(status=None, status_raw="Сломался насовсем")],
        match_status=MatchStatus.ONLY_IN_SOURCE,
        match_method=MatchMethod.INVENTORY_NUMBER,
    )
    assert run_detectors([group]) == []
