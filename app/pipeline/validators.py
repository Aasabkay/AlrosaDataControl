from collections import defaultdict

from app.domain.schemas import NormalizedRecord, Issue, IssueCode, Severity, FieldValue
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
        msg = f"У строк {rows} конфликт имен: они имеют одинаковые инв. номера, но разные имена"

        issues.append(Issue(
            refs=[r.ref for r in group],
            code=IssueCode.INVENTORY_CONFLICT,
            message=msg,
            severity=Severity.HIGH,
            field="name", values=values))

    return excluded, issues


