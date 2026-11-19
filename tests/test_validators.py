from pathlib import Path

import pytest

from app.domain.schemas import NormalizedRecord, RowRef
from app.pipeline.parser import parse_file
from app.rules.loader import load_rules


@pytest.fixture(scope="module")
def rules():
    return load_rules()

current_dir = Path(__file__).parent
test_full_path = current_dir.parent / "sample_data" / "test_full.xlsx"
test_full_cp1251_path = current_dir.parent / "sample_data" / "test_full_cp1251.csv"
case_sample_csv_path = current_dir.parent / "sample_data" / "case_sample.csv"
test_full_utf8_path = current_dir.parent / "sample_data" / "test_full_utf8.csv"

# dup_records: list[NormalizedRecord] = [
#     NormalizedRecord(ref=RowRef(source_id=1, batch_id=1, row_number=2),
#                      inventory_number=)
# ]