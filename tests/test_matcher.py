from app.domain.schemas import NormalizedRecord, RowRef, MatchStatus
from app.pipeline.matcher import match_records


def rec(source_id, row, inv=None, serial=None, name=None):
    return NormalizedRecord(
        ref=RowRef(source_id=source_id, batch_id=1, row_number=row),
        inventory_number=inv, serial_number=serial, name=name,
    )

def test_single_record_is_only_in_source():
    groups = match_records([rec(1, 1, inv="ИНВ-001")])
    assert len(groups) == 1
    assert groups[0].match_status == MatchStatus.ONLY_IN_SOURCE