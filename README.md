# Assignment Submission Portal with Automated Testing (CSC418 DevOps - Lab Midterm)

A small Flask web app where students submit assignment links, protected by a GitHub Actions
pipeline that **tests every push**, **sends the real test results to a receiver on your own
computer** (saved as `test-report.json`), and (bonus) **emails the report** and
**deploys a static demo to GitHub Pages only when all tests pass**.

```
 git push ──► GitHub Actions ──► pytest ──► JUnit XML ──► test-report.json
                                                              │
                          ┌───────────────────────────────────┼──────────────────────┐
                          ▼                                   ▼                      ▼
              HTTP POST via tunnel                     Email (bonus)          Pages deploy (bonus,
              to receiver on localhost:5001                                    only if tests pass)
                          ▼
              receiver/output/test-report.json  (on your computer)
```

## Repository layout

| Path | Purpose |
|---|---|
| `portal/` | Flask app: `validators.py`, `storage.py`, templates, CSS |
| `run.py` | Starts the portal on http://127.0.0.1:5000 |
| `tests/test_submissions.py` | Automated tests (3 required cases + extras) |
| `.github/workflows/ci.yml` | CI pipeline: test -> report -> email -> (deploy Pages) |
| `scripts/generate_report.py` | Converts pytest JUnit XML into `test-report.json` |
| `scripts/send_report.py` | POSTs the report to the receiver URL |
| `scripts/send_email.py` | Emails the report (bonus) |
| `scripts/demo_defect.py` | Switches the deliberate demo defect on/off |
| `scripts/local_ci.py` | Runs the same pipeline steps locally |
| `receiver/receiver.py` | Local HTTP receiver that saves `test-report.json` |
| `docs/` | Static frontend demo published to GitHub Pages |

## 1. Run the application

Requires Python 3.10+.

```bash
python -m venv .venv
# Windows PowerShell:  .venv\Scripts\Activate.ps1      macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

Open http://127.0.0.1:5000. Fill in name, registration number, assignment title and a
submission URL. Valid submissions are stored in `data/submissions.json` and listed on the page.
Missing fields or a bad URL are rejected with a message and nothing is saved.

## 2. Run the tests

```bash
python -m pytest -v
```

| Test | Expected result |
|---|---|
| `test_tc1_valid_submission_is_saved_and_listed` | Saved and shown in the list |
| `test_tc2_missing_registration_number_is_rejected` | HTTP 400 + "Registration number is required." |
| `test_tc3_invalid_submission_url_is_rejected_and_not_saved` | HTTP 400 and storage stays empty |

(Ten more tests cover other missing fields, unsafe URL schemes, HTML escaping, persistence, etc.)

## 3. Start the local receiver

```bash
python receiver/receiver.py
```

It listens on `http://127.0.0.1:5001/report` and writes every report it receives to
`receiver/output/test-report.json` (older ones are archived in `receiver/output/history/`).
Optional settings: `RECEIVER_PORT`, `RECEIVER_TOKEN` (shared secret), `REPORT_DIR`.

Try it without GitHub: with the receiver running, in a second terminal run `python scripts/local_ci.py`.

## 4. Connect GitHub Actions to your computer

A GitHub-hosted runner cannot see your `localhost`, so choose **one** option.

### Option A - tunnel (works with GitHub-hosted runners)

1. Start the receiver (step 3).
2. Start a tunnel in another terminal and keep it running:
   - ngrok: `ngrok http 5001`  (copy the `https://....ngrok-free.app` URL; a free static domain avoids URL changes)
   - or Cloudflare: `cloudflared tunnel --url http://localhost:5001`
3. In GitHub: **Settings > Secrets and variables > Actions > New repository secret**
   - `RECEIVER_URL` = `https://<your-tunnel-host>/report`
   - `RECEIVER_TOKEN` = any long random string (optional but recommended). Start the receiver with the same value:
     `RECEIVER_TOKEN=<value> python receiver/receiver.py` (PowerShell: `$env:RECEIVER_TOKEN="<value>"; python receiver/receiver.py`)

If the tunnel URL changes, update the `RECEIVER_URL` secret.

### Option B - self-hosted runner on your own computer (localhost works directly)

1. **Settings > Actions > Runners > New self-hosted runner**, follow the install steps, start the runner.
2. **Settings > Secrets and variables > Actions > Variables**: add `RUNNER_LABEL` = `self-hosted`.
3. Add secret `RECEIVER_URL` = `http://localhost:5001/report`.

## 5. Demonstration workflow

```bash
# 1. PASS  - push the clean code
git add . && git commit -m "Initial portal with tests" && git push

# 2. FAIL  - introduce the defect (URL validation bypassed) and push
python scripts/demo_defect.py on
git commit -am "Introduce defect: skip URL validation" && git push

# 3. FIX   - remove the defect and push
python scripts/demo_defect.py off
git commit -am "Fix: restore URL validation" && git push
```

After each push, check the **Actions** tab and the receiver's `receiver/output/test-report.json`.

## 6. Bonus tasks

### Conditional deployment to GitHub Pages
- **Settings > Pages > Build and deployment > Source: GitHub Actions** (the repository must be public on free plans).
- The `deploy-pages` job runs only for pushes to `main` and has `needs: test`, so a failing test job skips it and the
  previously published site stays untouched. The footer of the demo shows the deployed commit SHA.
- URL: `https://<your-username>.github.io/<repository-name>/`

### Email report
Add these repository secrets; the step skips itself if they are missing:
`SMTP_HOST` (e.g. `smtp.gmail.com`), `SMTP_PORT` (`587`), `SMTP_USERNAME`, `SMTP_PASSWORD`
(for Gmail use an *App Password*), `EMAIL_TO` (configurable recipient), optional `EMAIL_FROM`.
The email contains the commit SHA, overall result, counts, each test result, and `test-report.json` as an attachment.

## Report format (`test-report.json`)

```json
{
  "repository": "user/csc418-submission-portal",
  "branch": "main",
  "commit_sha": "0123abcd...",
  "pipeline_run_id": "1234567890",
  "timestamp": "2026-10-30T09:15:00+00:00",
  "summary": { "total": 13, "passed": 13, "failed": 0, "skipped": 0 },
  "overall_status": "PASSED",
  "tests": [
    { "name": "test_tc1_valid_submission_is_saved_and_listed", "classname": "tests.test_submissions.SubmissionPortalTests",
      "result": "passed", "failure_message": null, "duration_seconds": 0.01 }
  ]
}
```
