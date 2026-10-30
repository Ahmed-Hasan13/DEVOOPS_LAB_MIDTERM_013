"""Run the same steps as the pipeline on this computer (no GitHub needed).

    python scripts/local_ci.py            # tests -> report -> send to receiver
Requires the receiver to be running (python receiver/receiver.py).
"""
import os
import subprocess
import sys

PY = sys.executable
env = {**os.environ, "RECEIVER_URL": os.environ.get("RECEIVER_URL", "http://127.0.0.1:5001/report")}

tests = subprocess.run([PY, "-m", "pytest", "-v", "--junitxml=reports/junit.xml"], env=env)
subprocess.run([PY, "scripts/generate_report.py", "--junit", "reports/junit.xml",
                "--out", "reports/test-report.json"], check=True, env=env)
subprocess.run([PY, "scripts/send_report.py", "reports/test-report.json"], check=True, env=env)
sys.exit(tests.returncode)
