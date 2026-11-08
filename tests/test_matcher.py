from rapidfuzz import process, fuzz
from app.domain.schemas import NormalizedRecord, AssetGroup, MatchStatus, MatchMethod

def match_records(records: list[NormalizedRecord]) -> list[AssetGroup]:
    groups: list[AssetGroup] = []
    name_to_invs = {}
    for r in records:
        if r.name and r.inventory_number:
            name_to_invs.setdefault(r.name, set()).add(r.inventory_number)

    valid_records = []
    for r in records:
        if r.name and len(name_to_invs.get(r.name, set())) > 1:
            continue
        valid_records.append(r)

    unmatched = valid_records.copy()

    def determine_status(matched_recs: list[NormalizedRecord]) -> MatchStatus:
        unique_sources = {r.ref.source_id for r in matched_recs}
        return MatchStatus.MATCHED if len(unique_sources) > 1 else MatchStatus.ONLY_IN_SOURCE

    leftovers_after_inv = []
    inv_map = {}
    for r in unmatched:
        if r.inventory_number:
            inv_map.setdefault(r.inventory_number, []).append(r)
        else:
            leftovers_after_inv.append(r)
            
    for inv, recs in inv_map.items():
        groups.append(AssetGroup(
            asset_key=inv, records=recs,
            match_status=determine_status(recs), match_method=MatchMethod.INVENTORY_NUMBER
        ))

    unmatched = leftovers_after_inv
    leftovers_after_serial = []
    serial_map = {}
    for r in unmatched:
        if r.serial_number:
            serial_map.setdefault(r.serial_number, []).append(r)
        else:
            leftovers_after_serial.append(r)
            
    for serial, recs in serial_map.items():
        groups.append(AssetGroup(
            asset_key=serial, records=recs,
            match_status=determine_status(recs), match_method=MatchMethod.SERIAL_NUMBER
        ))

    unmatched = leftovers_after_serial
    leftovers_after_name = []
    name_map = {}
    for r in unmatched:
        if r.name:
            name_map.setdefault(r.name, []).append(r)
        else:
            leftovers_after_name.append(r)
            
    for name, recs in name_map.items():
        groups.append(AssetGroup(
            asset_key=name, records=recs,
            match_status=determine_status(recs), match_method=MatchMethod.NAME
        ))

    established_groups = {}
    for g in groups:
        group_name = next((rec.name for rec in g.records if rec.name), None)
        if group_name:
            established_groups[group_name] = g

    established_names = list(established_groups.keys())

    for r in leftovers_after_name:
        if not r.name or not established_names:
            groups.append(AssetGroup(
                asset_key=r.name or "UNKNOWN", records=[r],
                match_status=MatchStatus.ONLY_IN_SOURCE, match_method=MatchMethod.FUZZY
            ))
            continue

        match = process.extractOne(
            r.name, 
            established_names, 
            scorer=fuzz.token_sort_ratio, 
            score_cutoff=85
        )

        if match:
            matched_name = match[0]
            target_group = established_groups[matched_name]
            target_group.records.append(r)
            # Обновляем статус, так как добавили новую запись
            target_group.match_status = determine_status(target_group.records)
        else:
            new_group = AssetGroup(
                asset_key=r.name, records=[r],
                match_status=MatchStatus.ONLY_IN_SOURCE, match_method=MatchMethod.FUZZY
            )
            groups.append(new_group)
            established_groups[r.name] = new_group
            established_names.append(r.name)

    return groups