from app.domain.schemas import NormalizedRecord, AssetGroup, MatchStatus, MatchMethod


def match_records(records: list[NormalizedRecord]) -> list[AssetGroup]:
    boxes = {}
    result = []
    for record in records:
        inv = record.inventory_number
        if inv is None: continue
        if inv not in boxes:
            boxes[inv] = []
        boxes[inv].append(record)
    for inv, recs in boxes.items():
        group = AssetGroup(asset_key=inv , records=recs, match_status=MatchStatus.ONLY_IN_SOURCE, match_method=MatchMethod.INVENTORY_NUMBER)
        result.append(group)
    return result