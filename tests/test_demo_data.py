import json
from pathlib import Path

from app.pipeline.report import ReportMeta, build_report
from app.pipeline.runner import run_pipeline

DEMO_DIR = Path(__file__).parent.parent / "sample_data" / "demo"
FILES = {
    1: DEMO_DIR / "source_1_buh.xlsx",
    2: DEMO_DIR / "source_2_cmdb.csv",
    3: DEMO_DIR / "source_3_act.csv",
}

ALL_TEN_CODES = {
    "BAD_COLUMN_COUNT",
    "DUP_IN_SOURCE",
    "NAME_CONFLICT",
    "INVENTORY_CONFLICT",
    "MISSING_FIELD",
    "INVALID_STATUS",
    "BAD_FORMAT",
    "INVALID_ASSET_TYPE",
    "FIELD_MISMATCH",
    "MISSING_IN_SOURCE",
}


def load_expected() -> dict:
    return json.loads((DEMO_DIR / "expected.json").read_text(encoding="utf-8"))


def test_seeded_errors_match_expected():
    expected = load_expected()

    result = run_pipeline(FILES, expected_source_ids={1, 2, 3})
    report = build_report(result, ReportMeta())

    assert report.summary.model_dump() == expected["summary"]


def test_demo_covers_all_error_codes():
    result = run_pipeline(FILES, expected_source_ids={1, 2, 3})

    codes = {issue.code.value for issue in result.issues}
    assert codes == ALL_TEN_CODES


def test_expected_file_is_fresh():
    expected = load_expected()

    result = run_pipeline(FILES, expected_source_ids={1, 2, 3})
    report = build_report(result, ReportMeta())

    assert report.summary.by_code == expected["by_code"]
    assert report.summary.assets_total == expected["summary"]["assets_total"]
