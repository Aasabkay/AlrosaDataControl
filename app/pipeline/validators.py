from collections import defaultdict

from app.domain.schemas import NormalizedRecord, Issue, IssueCode, Severity, FieldValue, AssetCategory
from app.rules.loader import normalize_key


def group_by(records, key_func):
    groups = defaultdict(list)
    for record in records:
        key = key_func(record)
        if key is not None:
            groups[key].append(record)

    return groups

def find_duplicates(records: list[NormalizedRecord]) -> tuple[set[int], list[Issue]]:
    excluded: set[int] = set()
    issues: list[Issue] = []

    def key_func(rec):
        if not (rec.name and rec.inventory_number and rec.asset_type):
            return None
        return (normalize_key(rec.name), rec.inventory_number, rec.asset_type)

    for group in group_by(records, key_func).values():
        if len(group) < 2:
            continue

        kept, *extra = group

        excluded.update(rec.ref.row_number for rec in extra)
        extra_dup = [str(r.ref.row_number) for r in extra]
        row_dup = f"{kept.ref.row_number}, {', '.join(extra_dup)}"

        issues.append(Issue(
            code=IssueCode.DUP_IN_SOURCE, severity=Severity.MEDIUM,
            message=f"Строки {row_dup} совпали. Была оставлена только {kept.ref.row_number}",
            refs=[r.ref for r in group],
            field=None,
        ))

    return excluded, issues

def find_conflicts(records: list[NormalizedRecord]) -> tuple[set[int], list[Issue]]:
    excluded: set[int] = set()
    issues: list[Issue] = []

    def name_key_func(rec):
        return normalize_key(rec.name) if rec.name else None

    def inventory_key_func(rec):
        return rec.inventory_number if rec.inventory_number else None

    for group in group_by(records, name_key_func).values():
        inv_numbers = {r.inventory_number for r in group if r.inventory_number}
        if len(inv_numbers) < 2:
            continue

        excluded.update(rec.ref.row_number for rec in group)
        values = [FieldValue(ref=r.ref, value=r.inventory_number) for r in group]

        rows = ', '.join([str(r.ref.row_number) for r in group])
        msg = f"У строк {rows} конфликт имен: они имеют одинаковые имена, но разные инв. номера"


        issues.append(Issue(
            refs=[r.ref for r in group],
            code=IssueCode.NAME_CONFLICT,
            message=msg,
            severity=Severity.HIGH,
            field="inventory_number", values=values))

    for group in group_by(records, inventory_key_func).values():
        names = {r.name for r in group if r.name}
        if len(names) < 2:
            continue

        excluded.update(rec.ref.row_number for rec in group)
        values = [FieldValue(ref=r.ref, value=r.name) for r in group]

        rows = ', '.join([str(r.ref.row_number) for r in group])
        msg = f"У строк {rows} конфликт инв.номеров: они имеют одинаковые инв. номера, но разные имена"

        issues.append(Issue(
            refs=[r.ref for r in group],
            code=IssueCode.INVENTORY_CONFLICT,
            message=msg,
            severity=Severity.HIGH,
            field="name", values=values))

    return excluded, issues

def build_names(records: list[NormalizedRecord], excluded: set[int]) -> dict[str, tuple[AssetCategory, bool, int]]:
    names: dict[str, tuple[AssetCategory, bool, int]] = {}

    for r in records:
        if not r.name:
            continue
        is_excluded = True if r.ref.row_number in excluded else False
        key = normalize_key(r.name)
        if key in names and not names[key][1]:
            continue
        names[key] = (r.category, is_excluded, r.ref.row_number)

    return names

def resolve_parents(records, names, rejected_cells, row_status, RowStatus):
    by_row = {r.ref.row_number: r for r in records}
    excluded: set[int] = set()
    issues: list[Issue] = []

    def reject(r, code, message):
        issues.append(Issue(code=code, severity=Severity.HIGH, message=message,
                            refs=[r.ref], field="location"))
        excluded.add(r.ref.row_number)

    children = [r for r in records
                if row_status.get(r.ref.row_number) == RowStatus.ACCEPTED
                and r.category in (AssetCategory.PERIPHERAL, AssetCategory.ADAPTER)]

    for r in children:
        row = r.ref.row_number
        last = normalize_key(r.location.split("\\")[-1]) if r.location else None

        if last in names:
            if names[last][1]:
                reject(r, IssueCode.PARENT_REJECTED,
                       f"Строка {row}: родитель из строки {names[last][2]} исключён")
            continue
        if last in rejected_cells:
            reject(r, IssueCode.PARENT_REJECTED,
                   f"Строка {row}: родитель отброшен при проверке числа колонок")
            continue

        if r.category == AssetCategory.PERIPHERAL:
            continue

        above = row_status.get(row - 1)
        if above == RowStatus.REJECTED:
            reject(r, IssueCode.PARENT_REJECTED, f"Строка {row}: строка выше исключена")
        elif not (above == RowStatus.ACCEPTED
                  and by_row[row - 1].category == AssetCategory.ENDPOINT):
            reject(r, IssueCode.NO_PARENT, f"Строка {row}: не найден родитель")

    return excluded, issues