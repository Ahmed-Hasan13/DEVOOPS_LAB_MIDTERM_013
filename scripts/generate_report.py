"""Build test-report.json from the JUnit XML produced by pytest.

The report contains only data that comes from the executed test run plus the
CI metadata (repository, branch, commit, run id, timestamp).

Usage:
    python scripts/generate_report.py --junit reports/junit.xml --out reports/test-report.json
"""
import argparse
import json
import os
import socket
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

MAX_MESSAGE = 1000


def _clip(text: str | None) -> str:
    text = (text or "").strip()
    return text if len(text) <= MAX_MESSAGE else text[:MAX_MESSAGE] + " ...[truncated]"


def parse_junit(path: Path) -> list[dict]:
    root = ET.parse(path).getroot()
    tests = []
    for case in root.iter("testcase"):
        failure = case.find("failure")
        error = case.find("error")
        skipped = case.find("skipped")
        problem = failure if failure is not None else error
        if problem is not None:
            result = "failed"
            message = _clip(problem.get("message") or problem.text)
        elif skipped is not None:
            result, message = "skipped", _clip(skipped.get("message"))
        else:
            result, message = "passed", None
        tests.append(
            {
                "name": case.get("name", "unknown"),
                "classname": case.get("classname", ""),
                "result": result,
                "failure_message": message if result == "failed" else None,
                "duration_seconds": round(float(case.get("time", 0) or 0), 4),
            }
        )
    return tests


def build_report(tests: list[dict]) -> dict:
    env = os.environ
    server = env.get("GITHUB_SERVER_URL", "https://github.com")
    repo = env.get("GITHUB_REPOSITORY", "local/csc418-submission-portal")
    run_id = env.get("GITHUB_RUN_ID", "local-run")
    passed = sum(t["result"] == "passed" for t in tests)
    failed = sum(t["result"] == "failed" for t in tests)
    skipped = sum(t["result"] == "skipped" for t in tests)
    overall = "PASSED" if tests and failed == 0 else "FAILED"
    return {
        "repository": repo,
        "branch": env.get("GITHUB_REF_NAME", "local"),
        "commit_sha": env.get("GITHUB_SHA", "local"),
        "pipeline_run_id": run_id,
        "pipeline_run_number": env.get("GITHUB_RUN_NUMBER", "local"),
        "pipeline_run_url": f"{server}/{repo}/actions/runs/{run_id}" if run_id != "local-run" else None,
        "workflow": env.get("GITHUB_WORKFLOW", "local"),
        "triggered_by": env.get("GITHUB_ACTOR", "local"),
        "runner": env.get("RUNNER_NAME", socket.gethostname()),
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "summary": {
            "total": len(tests),
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        },
        "overall_status": overall,
        "tests": tests,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--junit", default="reports/junit.xml")
    ap.add_argument("--out", default="reports/test-report.json")
    args = ap.parse_args()

    junit = Path(args.junit)
    if junit.exists():
        tests = parse_junit(junit)
    else:
        # pytest never produced a result file (crash / install failure):
        # still deliver a report so the failed run is visible locally.
        tests = [
            {
                "name": "test-execution",
                "classname": "pipeline",
                "result": "failed",
                "failure_message": f"No JUnit result file found at {junit}. The test run did not complete.",
                "duration_seconds": 0.0,
            }
        ]

    report = build_report(tests)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    s = report["summary"]
    print(f"Report written to {out}: {report['overall_status']} "
          f"(total={s['total']} passed={s['passed']} failed={s['failed']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
