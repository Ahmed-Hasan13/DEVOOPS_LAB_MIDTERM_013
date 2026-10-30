"""Assignment Submission Portal (Flask application factory)."""
import os
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template, request, url_for

from .storage import SubmissionStore
from .validators import FIELDS, validate_submission

BASE_DIR = Path(__file__).resolve().parent.parent


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config["SUBMISSIONS_FILE"] = os.environ.get(
        "SUBMISSIONS_FILE", str(BASE_DIR / "data" / "submissions.json")
    )
    if test_config:
        app.config.update(test_config)

    store = SubmissionStore(app.config["SUBMISSIONS_FILE"])

    def render_page(values=None, errors=None, status=200):
        submissions = list(reversed(store.all()))  # newest first
        return (
            render_template(
                "index.html",
                values=values or {},
                errors=errors or {},
                submissions=submissions,
                submitted=request.args.get("submitted") == "1",
            ),
            status,
        )

    @app.get("/")
    def index():
        return render_page()

    @app.post("/submit")
    def submit():
        clean, errors = validate_submission(request.form)
        if errors:
            return render_page(values=clean, errors=errors, status=400)
        store.add({f: clean[f] for f in FIELDS})
        return redirect(url_for("index", submitted=1) + "#submissions")

    @app.get("/api/submissions")
    def api_submissions():
        return jsonify(store.all())

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    return app
