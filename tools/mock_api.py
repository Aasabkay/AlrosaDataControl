
import argparse
import io
import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from app.pipeline.report import ReportMeta, build_report, write_report_xlsx
from app.pipeline.runner import run_pipeline

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DEMO_DIR = REPO_ROOT / "sample_data" / "demo"
OPENAPI_PATH = REPO_ROOT / "tools" / "openapi.json"

SOURCE_NAMES = {
    1: "Бухгалтерия (XLSX)",
    2: "Выгрузка CMDB (CSV)",
    3: "Акт инвентаризации (CSV)",
}


class MockAPI:

    def __init__(self, demo_dir: Path) -> None:
        files = {
            1: demo_dir / "source_1_buh.xlsx",
            2: demo_dir / "source_2_cmdb.csv",
            3: demo_dir / "source_3_act.csv",
        }
        result = run_pipeline(files, expected_source_ids={1, 2, 3})
        report = build_report(
            result,
            ReportMeta(organization="ООО «Демо»", responsible="Иванов И.И."),
        )

        self.report = json.loads(report.model_dump_json())
        self.issues = self.report["issues"]
        self.assets = self.report["assets"]

        self.ref_to_asset: dict[tuple[int, int, int], str] = {}
        for group in result.groups:
            for record in group.records:
                ref = record.ref
                self.ref_to_asset[(ref.source_id, ref.batch_id, ref.row_number)] = group.asset_key

    @property
    def sources(self) -> list[dict]:
        return [
            {"id": source_id, "name": name}
            for source_id, name in SOURCE_NAMES.items()
        ]

    def filter_issues(self, query: dict[str, list[str]]) -> list[dict]:
        filters = {
            "category": lambda issue, value: issue["category"] == value,
            "severity": lambda issue, value: issue["severity"] == value,
            "code": lambda issue, value: issue["code"] == value,
            "field": lambda issue, value: issue.get("field") == value,
            "asset_key": lambda issue, value: issue.get("asset_key") == value,
        }
        issues = self.issues
        for key, check in filters.items():
            value = query.get(key, [None])[0]
            if value:
                issues = [issue for issue in issues if check(issue, value)]
        return issues

    def import_log(self, import_id: int) -> list[dict]:
        return [
            issue for issue in self.issues
            if any(ref["source_id"] == import_id for ref in issue["refs"])
        ]

    def asset_detail(self, asset_key: str) -> dict | None:
        asset = next(
            (item for item in self.assets if item["asset_key"] == asset_key),
            None,
        )
        if asset is None:
            return None

        issues = [
            issue for issue in self.issues
            if issue.get("asset_key") == asset_key
            or any(
                self.ref_to_asset.get(
                    (ref["source_id"], ref["batch_id"], ref["row_number"])
                ) == asset_key
                for ref in issue["refs"]
            )
        ]
        return {"asset": asset, "issues": issues}

    def report_xlsx(self) -> bytes:
        buffer = io.BytesIO()
        from app.pipeline.report import Report  

        report = Report.model_validate(self.report)
        write_report_xlsx(buffer, report)
        return buffer.getvalue()


class MockHandler(BaseHTTPRequestHandler):
    api: MockAPI

    def log_message(self, *args) -> None:  
        pass

    def _send_json(self, payload, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _send_bytes(self, data: bytes, content_type: str, filename: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self._cors()
        self.end_headers()
        self.wfile.write(data)

    def _cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self) -> None:  
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path == "/sources":
            self._send_json(self.api.sources)
            return

        if path == "/openapi.json" and OPENAPI_PATH.exists():
            self._send_json(json.loads(OPENAPI_PATH.read_text(encoding="utf-8")))
            return

        match = re.fullmatch(r"/reconciliations/(\d+)", path)
        if match:
            self._send_json(self.api.report)
            return

        match = re.fullmatch(r"/reconciliations/(\d+)/issues", path)
        if match:
            self._send_json(self.api.filter_issues(query))
            return

        match = re.fullmatch(r"/reconciliations/(\d+)/assets", path)
        if match:
            self._send_json(self.api.assets)
            return

        match = re.fullmatch(r"/reconciliations/(\d+)/report", path)
        if match:
            fmt = query.get("format", ["json"])[0]
            if fmt == "xlsx":
                self._send_bytes(
                    self.api.report_xlsx(),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    "report.xlsx",
                )
            else:
                self._send_json(self.api.report)
            return

        match = re.fullmatch(r"/imports/(\d+)/log", path)
        if match:
            self._send_json({
                "import_id": int(match.group(1)),
                "issues": self.api.import_log(int(match.group(1))),
            })
            return

        match = re.fullmatch(r"/assets/(.+)", path)
        if match:
            detail = self.api.asset_detail(unquote(match.group(1)))
            if detail is None:
                self._send_json({"detail": "Актив не найден"}, 404)
            else:
                self._send_json(detail)
            return

        self._send_json({"detail": "Эндпоинт не найден"}, 404)

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", 0) or 0)
        if length:
            self.rfile.read(length)   

        if self.path == "/imports":
            self._send_json({"import_id": 1}, 201)
            return
        if self.path == "/reconciliations":
            self._send_json({"reconciliation_id": 1}, 201)
            return

        self._send_json({"detail": "Эндпоинт не найден"}, 404)


def create_server(address: tuple[str, int], demo_dir: Path | None = None) -> ThreadingHTTPServer:
    api = MockAPI(demo_dir or DEFAULT_DEMO_DIR)
    handler = type("BoundHandler", (MockHandler,), {"api": api})
    return ThreadingHTTPServer(address, handler)


def main() -> None:
    parser = argparse.ArgumentParser(description="Мок-API сверки активов")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--demo-dir", type=Path, default=DEFAULT_DEMO_DIR)
    args = parser.parse_args()

    server = create_server((args.host, args.port), args.demo_dir)
    print(f"Мок-API: http://{args.host}:{args.port}")
    print("Эндпоинты: /sources, /openapi.json, /reconciliations/1, "
          "/reconciliations/1/issues, /reconciliations/1/assets, "
          "/reconciliations/1/report?format=xlsx, /imports/1/log, /assets/<ключ>")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()
