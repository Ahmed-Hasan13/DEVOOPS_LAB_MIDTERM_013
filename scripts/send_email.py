"""Email the test report (bonus). Skips quietly when SMTP settings are absent.

Environment (store as GitHub Actions secrets, never in code):
    SMTP_HOST, SMTP_PORT (587 STARTTLS or 465 SSL), SMTP_USERNAME, SMTP_PASSWORD,
    EMAIL_TO (comma separated allowed), EMAIL_FROM (optional, defaults to SMTP_USERNAME)

Usage:
    python scripts/send_email.py reports/test-report.json
"""
import json
import os
import smtplib
import ssl
import sys
from email.message import EmailMessage
from pathlib import Path


def build_body(r: dict) -> str:
    s = r["summary"]
    lines = [
        f"Overall result : {r['overall_status']}",
        f"Repository     : {r['repository']}",
        f"Branch         : {r['branch']}",
        f"Commit         : {r['commit_sha']}",
        f"Pipeline run   : {r['pipeline_run_id']} (#{r.get('pipeline_run_number')})",
        f"Run URL        : {r.get('pipeline_run_url')}",
        f"Timestamp      : {r['timestamp']}",
        "",
        f"Tests: total={s['total']}  passed={s['passed']}  failed={s['failed']}  skipped={s.get('skipped', 0)}",
        "",
        "Individual results:",
    ]
    for t in r["tests"]:
        lines.append(f"  [{t['result'].upper():7}] {t['name']}")
        if t.get("failure_message"):
            first = t["failure_message"].splitlines()[0][:200]
            lines.append(f"            -> {first}")
    lines += ["", "The full JSON report is attached."]
    return "\n".join(lines)


def main() -> int:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "reports/test-report.json")
    env = os.environ
    host, user, pwd, to = (env.get(k, "").strip() for k in
                           ("SMTP_HOST", "SMTP_USERNAME", "SMTP_PASSWORD", "EMAIL_TO"))
    if not (host and user and pwd and to):
        print("Email settings not configured (SMTP_HOST/SMTP_USERNAME/SMTP_PASSWORD/EMAIL_TO); skipping email.")
        return 0
    if not path.exists():
        print(f"ERROR: report not found: {path}", file=sys.stderr)
        return 1

    report = json.loads(path.read_text(encoding="utf-8"))
    port = int(env.get("SMTP_PORT", "587") or 587)

    msg = EmailMessage()
    msg["Subject"] = (f"[{report['overall_status']}] {report['repository']} "
                      f"{str(report['commit_sha'])[:7]} - {report['summary']['passed']}/"
                      f"{report['summary']['total']} tests passed")
    msg["From"] = env.get("EMAIL_FROM", "").strip() or user
    msg["To"] = to
    msg.set_content(build_body(report))
    msg.add_attachment(path.read_bytes(), maintype="application", subtype="json", filename="test-report.json")

    ctx = ssl.create_default_context()
    if port == 465:
        with smtplib.SMTP_SSL(host, port, context=ctx, timeout=30) as smtp:
            smtp.login(user, pwd)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=30) as smtp:
            smtp.starttls(context=ctx)
            smtp.login(user, pwd)
            smtp.send_message(msg)
    print(f"Email sent to {to}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
