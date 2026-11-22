from app.domain.schemas import (
    MatchMethod,
    MatchStatus,
    NormalizedRecord,
    RowRef,
)
from app.pipeline.matcher import match_records


def make_rec(
    source_id: int = 1,
    row: int = 1,
    name: str | None = None,
    inv: str | None = None,
    serial: str | None = None,
) -> NormalizedRecord:
    return NormalizedRecord(
        ref=RowRef(source_id=source_id, batch_id=1, row_number=row),
        name=name,
        inventory_number=inv,
        serial_number=serial,
    )


def test_match_by_inventory_number_across_sources():
    groups = match_records([
        make_rec(1, 1, name="ПК-01", inv="ИНВ-001"),
        make_rec(2, 2, name="ПК-01", inv="ИНВ-001"),
    ])

    assert len(groups) == 1
    group = groups[0]
    assert group.asset_key == "ИНВ-001"
    assert group.match_method == MatchMethod.INVENTORY_NUMBER
    assert group.match_status == MatchStatus.MATCHED
    assert len(group.records) == 2


def test_inventory_number_has_priority_over_serial():
    groups = match_records([
        make_rec(1, 1, name="ПК-01", inv="ИНВ-001", serial="SN-AAA"),
        make_rec(2, 2, name="ПК-01", inv="ИНВ-001", serial="SN-BBB"),
    ])

    assert len(groups) == 1
    assert groups[0].match_method == MatchMethod.INVENTORY_NUMBER
    assert {r.serial_number for r in groups[0].records} == {"SN-AAA", "SN-BBB"}


def test_match_by_serial_number_when_no_inventory():
    groups = match_records([
        make_rec(1, 1, name="ПК-01", serial="SN-001"),
        make_rec(2, 2, name="ПК-02", serial="SN-001"),
    ])

    assert len(groups) == 1
    group = groups[0]
    assert group.asset_key == "SN-001"
    assert group.match_method == MatchMethod.SERIAL_NUMBER
    assert group.match_status == MatchStatus.MATCHED


def test_match_by_name_when_no_keys():
    groups = match_records([
        make_rec(1, 1, name="ПК-01"),
        make_rec(2, 2, name="ПК-01"),
    ])

    assert len(groups) == 1
    group = groups[0]
    assert group.asset_key == "ПК-01"
    assert group.match_method == MatchMethod.NAME
    assert group.match_status == MatchStatus.MATCHED


def test_single_record_is_only_in_source():
    groups = match_records([make_rec(1, 1, name="ПК-01", inv="ИНВ-001")])

    assert len(groups) == 1
    assert groups[0].match_status == MatchStatus.ONLY_IN_SOURCE


def test_same_source_duplicates_are_not_matched():
    groups = match_records([
        make_rec(1, 1, name="ПК-01", inv="ИНВ-001"),
        make_rec(1, 2, name="ПК-01", inv="ИНВ-001"),
    ])

    assert len(groups) == 1
    assert groups[0].match_status == MatchStatus.ONLY_IN_SOURCE


def test_record_without_keys_goes_to_unknown_group():
    groups = match_records([make_rec(1, 1)])

    assert len(groups) == 1
    group = groups[0]
    assert group.asset_key == "UNKNOWN"
    assert group.match_status == MatchStatus.ONLY_IN_SOURCE


def test_same_name_with_different_inventory_gives_two_groups():
    groups = match_records([
        make_rec(1, 1, name="ПК-01", inv="ИНВ-001"),
        make_rec(1, 2, name="ПК-01", inv="ИНВ-002"),
    ])

    assert len(groups) == 2
    assert {group.asset_key for group in groups} == {"ИНВ-001", "ИНВ-002"}


def test_fuzzy_merges_similar_names():
    groups = match_records([
        make_rec(1, 1, name="ПК-01"),
        make_rec(2, 2, name="ПК-001"),
    ])

    assert len(groups) == 1
    group = groups[0]
    assert group.match_method == MatchMethod.FUZZY
    assert group.match_status == MatchStatus.MATCHED
    assert group.match_score is not None


def test_fuzzy_flags_ambiguous_match():
    groups = match_records([
        make_rec(1, 1, name="ПК-01"),
        make_rec(2, 2, name="ПК-01A"),
        make_rec(3, 3, name="ПК-01B"),
    ])

    assert any(
        group.match_status == MatchStatus.AMBIGUOUS
        for group in groups
    )


def test_fuzzy_does_not_merge_different_names():
    groups = match_records([
        make_rec(1, 1, name="ПК-01"),
        make_rec(2, 2, name="Сервер-99"),
    ])

    assert len(groups) == 2
    assert all(group.match_status == MatchStatus.ONLY_IN_SOURCE for group in groups)
