from pathlib import Path

import pytest

from app.domain.schemas import NormalizedRecord, RowRef, AssetCategory, IssueCode
from app.pipeline.parser import RowStatus
from app.pipeline.validators import (build_names, find_conflicts,
                                     find_duplicates, resolve_parents)
from app.rules.loader import load_rules, normalize_key


@pytest.fixture(scope="module")
def rules():
    return load_rules()

current_dir = Path(__file__).parent
test_full_path = current_dir.parent / "sample_data" / "test_full.xlsx"
test_full_cp1251_path = current_dir.parent / "sample_data" / "test_full_cp1251.csv"
case_sample_csv_path = current_dir.parent / "sample_data" / "case_sample.csv"
test_full_utf8_path = current_dir.parent / "sample_data" / "test_full_utf8.csv"

def rec(row: int, name="ПК-01", inv="ИНВ-001", asset_type="Рабочая станция",
        category=AssetCategory.ENDPOINT, location=None, **kw) -> NormalizedRecord:
    return NormalizedRecord(
        ref=RowRef(source_id=1, batch_id=1, row_number=row),
        name=name, inventory_number=inv, asset_type=asset_type,
        category=category, location=location, **kw,
    )

@pytest.mark.parametrize("records, excluded, issues, rowref", [
    ([rec(1), rec(2), rec(3)], {2, 3}, 1, {1, 2, 3}),
    ([rec(1, inv=""), rec(2)], set(), 0, set()),
    ([rec(1), rec(2), rec(3), rec(4), rec(5)], {2, 3, 4, 5}, 1, {1, 2, 3, 4, 5}),
    ([rec(1)], set(), 0, set()),
    ([rec(1), rec(2, name="ПК-02", inv="ИНВ-02"), rec(3)], {3}, 1, {1, 3}),
    ([rec(1), rec(2, asset_type="Сервер")], set(), 0, set())
])
def test_find_duplicate(records, excluded, issues, rowref):
    dup_excluded, dup_issues = find_duplicates(records)
    assert dup_excluded == excluded
    assert len(dup_issues) == issues
    for el in dup_issues:
        assert el.code == IssueCode.DUP_IN_SOURCE

    if dup_issues:
        all_refs = {r.row_number for i in dup_issues for r in i.refs}
        assert all_refs == rowref

@pytest.mark.parametrize("records, excluded, issues", [
    ([rec(1), rec(2, inv="ИНВ-002")], {1, 2}, 1),
    ([rec(1, name=""), rec(2, name="")], set(), 0),
    ([rec(1), rec(2, name="ПК-02", inv="ИНВ-002"), rec(3, inv="ИНВ-003"), rec(4, inv="ИНВ-004")], {1, 3, 4}, 1)
])
def test_find_name_conflicts(records, excluded, issues):
    name_conf_excluded, name_conf_issues = find_conflicts(records)
    assert name_conf_excluded == excluded
    assert len(name_conf_issues) == issues
    for el in name_conf_issues:
        assert el.code == IssueCode.NAME_CONFLICT

    if name_conf_issues:
        all_refs = {r.row_number for i in name_conf_issues for r in i.refs}
        assert all_refs == excluded

@pytest.mark.parametrize("records, excluded, issues", [
    ([rec(1), rec(2, name="ПК-02")], {1, 2}, 1),
    ([rec(1, inv=""), rec(2, inv="")], set(), 0),
    ([rec(1), rec(2, name="ПК-02", inv="ИНВ-002"), rec(3, name="ПК-03"), rec(4, name="ПК-04", inv="ИНВ-002")], {1, 2, 3, 4}, 2),
])
def test_find_inv_num_conflicts(records, excluded, issues):
    inv_conf_excluded, inv_conf_issues = find_conflicts(records)
    assert inv_conf_excluded == excluded
    assert len(inv_conf_issues) == issues
    for el in inv_conf_issues:
        assert el.code == IssueCode.INVENTORY_CONFLICT

    if inv_conf_issues:
        all_refs = {r.row_number for i in inv_conf_issues for r in i.refs}
        assert all_refs == excluded

@pytest.mark.parametrize("records, excluded, expected", [
    ([rec(1), rec(2, name="пк-02")], {1, 2},
     {"пк-01":(AssetCategory.ENDPOINT, True, 1), "пк-02":(AssetCategory.ENDPOINT, True, 2)}
     ),
    ([rec(1), rec(2, name="пк-02", inv="инв-002")], set(),
     {"пк-01":(AssetCategory.ENDPOINT, False, 1), "пк-02":(AssetCategory.ENDPOINT, False, 2)}
     ),
    ([rec(1), rec(2)], {1}, {"пк-01":(AssetCategory.ENDPOINT, False, 2)}),
    ([rec(1), rec(2)], {2},{"пк-01":(AssetCategory.ENDPOINT, False, 1)})
])
def test_build_names(records, excluded, expected):
    names = build_names(records, excluded)

    assert names == expected


PER = AssetCategory.PERIPHERAL
ADA = AssetCategory.ADAPTER

def resolve(records, excluded_rows=(), rejected_cells=frozenset()):
    row_status = {
        r.ref.row_number: (RowStatus.REJECTED if r.ref.row_number in set(excluded_rows)
                           else RowStatus.ACCEPTED)
        for r in records
    }
    return resolve_parents(records, set(excluded_rows), set(rejected_cells), row_status, RowStatus)

def test_peripheral_with_accepted_parent():
    excluded, issues = resolve([rec(1), rec(2, name="Принтер-1", category=PER, location="Офис\\ПК-01")])
    assert excluded == set()
    assert issues == []

def test_peripheral_with_excluded_parent():
    excluded, issues = resolve([rec(1), rec(2, name="Принтер-1", category=PER, location="Офис\\ПК-01")],
                               excluded_rows=(1,))
    assert excluded == {2}
    assert [i.code for i in issues] == [IssueCode.PARENT_REJECTED]

def test_peripheral_parent_in_rejected_cells():
    excluded, issues = resolve([rec(2, name="Принтер-1", category=PER, location="Офис\\ПК-01")],
                               rejected_cells={normalize_key("ПК-01")})
    assert excluded == {2}
    assert [i.code for i in issues] == [IssueCode.PARENT_REJECTED]

def test_peripheral_unknown_location_is_room():
    excluded, issues = resolve([rec(2, name="Принтер-1", category=PER, location="Офис\\Комната 5")])
    assert excluded == set()
    assert issues == []

def test_adapter_with_accepted_parent_by_location():
    excluded, issues = resolve([rec(1), rec(2, name="Сетевуха", category=ADA,
                                          location="Офис\\ПК-01")])
    assert excluded == set()
    assert issues == []

def test_adapter_row_above_accepted_endpoint():
    excluded, issues = resolve([rec(1), rec(2, name="Сетевуха", category=ADA)])
    assert excluded == set()
    assert issues == []

def test_adapter_row_above_rejected():
    excluded, issues = resolve([rec(1), rec(2, name="Сетевуха", category=ADA)],
                               excluded_rows=(1,))
    assert excluded == {2}
    assert [i.code for i in issues] == [IssueCode.PARENT_REJECTED]

def test_adapter_row_above_not_endpoint():
    excluded, issues = resolve([rec(1, name="Монитор-1", category=PER, location="Комната 5"),
                                rec(2, name="Сетевуха", category=ADA)])
    assert excluded == {2}
    assert [i.code for i in issues] == [IssueCode.NO_PARENT]

def test_cascade_child_of_rejected_child():
    records = [rec(2, name="Принтер-1", category=PER, location="Офис\\ПК-99"),
               rec(3, name="Сетевуха", category=ADA)]
    excluded, issues = resolve(records, rejected_cells={normalize_key("ПК-99")})
    assert excluded == {2, 3}
    assert [i.code for i in issues] == [IssueCode.PARENT_REJECTED] * 2
