"""Local HTTP receiver for CI test reports.

Listens for POST /report, validates the JSON and saves it as test-report.json
on this computer. Each report is also archived under output/history/.

Run:   python receiver/receiver.py
Env:   RECEIVER_HOST (default 127.0.0.1)   RECEIVER_PORT (default 5001)
       RECEIVER_TOKEN (optional shared secret; clients send X-Report-Token)
       REPORT_DIR (default receiver/output)
"""
import hmac
import json
import os
import re
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HOST = os.environ.get("RECEIVER_HOST", "127.0.0.1")
PORT = int(os.environ.get("RECEIVER_PORT", "5001"))
TOKEN = os.environ.get("RECEIVER_TOKEN", "").strip()
OUTPUT_DIR = Path(os.environ.get("REPORT_DIR", Path(__file__).resolve().parent / "output"))
MAX_BYTES = 1_000_000
REQUIRED_KEYS = {"repository", "branch", "commit_sha", "pipeline_run_id",
                 "timestamp", "summary", "overall_status", "tests"}


def validate(report) -> str | None:
    if not isinstance(report, dict):
        return "report must be a JSON object"
    missing = REQUIRED_KEYS - report.keys()
    if missing:
        return f"missing keys: {', '.join(sorted(missing))}"
    if not isinstance(report["tests"], list) or not isinstance(report["summary"], dict):
        return "'tests' must be a list and 'summary' an object"
    return None


def save(report: dict) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    text = json.dumps(report, indent=2)

    target = OUTPUT_DIR / "test-report.json"
    tmp = target.with_suffix(".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, target)  # atomic: readers never see a half-written file

    history = OUTPUT_DIR / "history"
    history.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    sha = re.sub(r"[^A-Za-z0-9]", "", str(report["commit_sha"]))[:7]
    status = re.sub(r"[^A-Za-z]", "", str(report["overall_status"])).lower()
    (history / f"{stamp}_{sha}_{status}.json").write_text(text, encoding="utf-8")
    return target


class Handler(BaseHTTPRequestHandler):
    server_version = "ReportReceiver/1.0"

    def _send(self, code: int, payload: dict):
        data = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/health":
            self._send(200, {"status": "ok"})
        elif self.path == "/":
            latest = OUTPUT_DIR / "test-report.json"
            self._send(200, {"service": "CSC418 test report receiver",
                             "post_reports_to": "/report",
                             "latest_report_saved": latest.exists()})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/report":
            return self._send(404, {"error": "POST to /report"})
        if TOKEN and not hmac.compare_digest(self.headers.get("X-Report-Token", ""), TOKEN):
            print("[receiver] rejected request: bad token")
            return self._send(401, {"error": "invalid token"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return self._send(400, {"error": "bad Content-Length"})
        if length <= 0 or length > MAX_BYTES:
            return self._send(400, {"error": "body missing or too large"})
        try:
            report = json.loads(self.rfile.read(length))
        except json.JSONDecodeError as exc:
            return self._send(400, {"error": f"invalid JSON: {exc}"})
        problem = validate(report)
        if problem:
            print(f"[receiver] rejected report: {problem}")
            return self._send(400, {"error": problem})

        path = save(report)
        s = report["summary"]
        print(f"[receiver] saved {path.name}: {report['overall_status']} "
              f"commit={str(report['commit_sha'])[:7]} run={report['pipeline_run_id']} "
              f"total={s.get('total')} passed={s.get('passed')} failed={s.get('failed')}")
        self._send(200, {"status": "saved", "file": str(path), "overall_status": report["overall_status"]})

    def log_message(self, fmt, *args):  # quieter default access log
        print(f"[receiver] {self.address_string()} {fmt % args}")


def main():
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"[receiver] listening on http://{HOST}:{PORT}/report")
    print(f"[receiver] saving reports to {OUTPUT_DIR / 'test-report.json'}")
    if TOKEN:
        print("[receiver] token check enabled")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[receiver] stopped")


if __name__ == "__main__":
    main()
