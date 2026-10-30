"""POST test-report.json to the local receiver (through a tunnel in CI).

Environment:
    RECEIVER_URL    e.g. https://abcd-12-34.ngrok-free.app/report  (or http://localhost:5001/report)
    RECEIVER_TOKEN  optional shared secret, sent as X-Report-Token

Usage:
    python scripts/send_report.py reports/test-report.json
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


def main() -> int:
    report_path = Path(sys.argv[1] if len(sys.argv) > 1 else "reports/test-report.json")
    url = os.environ.get("RECEIVER_URL", "").strip()
    if not url:
        print("ERROR: RECEIVER_URL is not set. Add it as a repository secret "
              "(Settings > Secrets and variables > Actions).", file=sys.stderr)
        return 1
    if not report_path.exists():
        print(f"ERROR: report file not found: {report_path}", file=sys.stderr)
        return 1

    body = report_path.read_bytes()
    json.loads(body)  # fail early if the file is not valid JSON

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "csc418-report-client/1.0",
        "ngrok-skip-browser-warning": "1",  # harmless elsewhere; skips ngrok's interstitial
    }
    token = os.environ.get("RECEIVER_TOKEN", "").strip()
    if token:
        headers["X-Report-Token"] = token

    last_error = None
    for attempt in range(1, 6):
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                print(f"Receiver answered HTTP {resp.status}: {resp.read().decode('utf-8', 'replace')}")
                return 0
        except urllib.error.HTTPError as exc:
            last_error = f"HTTP {exc.code}: {exc.read().decode('utf-8', 'replace')[:300]}"
            if exc.code in (400, 401, 403, 404):  # retrying will not help
                break
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            last_error = str(exc)
        print(f"Attempt {attempt}/5 failed: {last_error}")
        time.sleep(min(2 * attempt, 8))

    print(f"ERROR: could not deliver the report. Is the receiver and tunnel running? ({last_error})",
          file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
