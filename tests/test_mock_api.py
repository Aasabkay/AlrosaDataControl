import json
import threading
import urllib.error
import urllib.request
from urllib.parse import quote

import pytest

from tools.mock_api import create_server


@pytest.fixture(scope="module")
def base_url():
    server = create_server(("127.0.0.1", 0))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


def get_json(base_url: str, path: str):
    request = urllib.request.Request(base_url + path)
    try:
        with urllib.request.urlopen(request) as response:
            body = json.loads(response.read().decode("utf-8"))
            return response.status, body, dict(response.headers)
    except urllib.error.HTTPError as error:
        body = json.loads(error.read().decode("utf-8"))
        return error.code, body, dict(error.headers)


def test_report_endpoint_serves_demo_data(base_url):
    status, payload, _ = get_json(base_url, "/reconciliations/1")

    assert status == 200
    assert payload["summary"]["assets_total"] == 20
    assert payload["summary"]["issues_total"] == 17
    assert len(payload["recommendations"]) >= 1


def test_issues_filter_by_severity(base_url):
    status, issues, _ = get_json(base_url, "/reconciliations/1/issues?severity=high")

    assert status == 200
    assert issues
    assert all(issue["severity"] == "high" for issue in issues)


def test_issues_filter_by_category(base_url):
    status, issues, _ = get_json(base_url, "/reconciliations/1/issues?category=mismatch")

    assert status == 200
    assert issues
    assert all(issue["category"] == "mismatch" for issue in issues)


def test_assets_list(base_url):
    status, assets, _ = get_json(base_url, "/reconciliations/1/assets")

    assert status == 200
    assert len(assets) == 20


def test_asset_detail_returns_diff(base_url):
    path = f"/assets/{quote('ИНВ-00012')}"
    status, payload, _ = get_json(base_url, path)

    assert status == 200
    assert payload["asset"]["asset_key"] == "ИНВ-00012"
    assert any(issue["code"] == "FIELD_MISMATCH" for issue in payload["issues"])


def test_unknown_asset_returns_404(base_url):
    status, payload, _ = get_json(base_url, f"/assets/{quote('НЕТ-ТАКОГО')}")

    assert status == 404
    assert "не найден" in payload["detail"]


def test_import_log_for_source(base_url):
    status, payload, _ = get_json(base_url, "/imports/2/log")

    assert status == 200
    assert payload["import_id"] == 2
    codes = {issue["code"] for issue in payload["issues"]}
    assert "DUP_IN_SOURCE" in codes


def test_cors_header_allows_frontend(base_url):
    status, _, headers = get_json(base_url, "/sources")

    assert status == 200
    assert headers.get("Access-Control-Allow-Origin") == "*"


def test_openapi_json_is_served(base_url):
    status, spec, _ = get_json(base_url, "/openapi.json")

    assert status == 200
    assert spec["openapi"].startswith("3.")
    assert "/reconciliations/{reconciliation_id}/issues" in spec["paths"]


def test_xlsx_report_is_binary(base_url):
    with urllib.request.urlopen(base_url + "/reconciliations/1/report?format=xlsx") as response:
        assert response.status == 200
        data = response.read()

    assert data[:2] == b"PK"   # сигнатура zip-архива, внутри которого xlsx
