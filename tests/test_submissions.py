"""Automated tests for the assignment submission portal.

Test cases 1-3 are the ones required by the lab brief. The rest add coverage
for validation edge cases. Written as unittest classes so they run with
`pytest` (used by the CI pipeline) and with `python -m unittest`.
"""
import json
import tempfile
import unittest
from pathlib import Path

from portal import create_app
from portal.validators import is_valid_url

VALID = {
    "student_name": "Ayesha Khan",
    "registration_number": "FA22-BCS-014",
    "assignment_title": "Lab 3 - Docker Basics",
    "submission_url": "https://github.com/ayesha/devops-lab3",
}


class SubmissionPortalTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.data_file = Path(self._tmp.name) / "submissions.json"
        self.app = create_app({"TESTING": True, "SUBMISSIONS_FILE": str(self.data_file)})
        self.client = self.app.test_client()

    def tearDown(self):
        self._tmp.cleanup()

    def saved(self):
        if not self.data_file.exists():
            return []
        return json.loads(self.data_file.read_text(encoding="utf-8"))

    # ---- Required test cases ------------------------------------------------

    def test_tc1_valid_submission_is_saved_and_listed(self):
        """Complete details + valid URL -> saved and shown in the list."""
        resp = self.client.post("/submit", data=VALID, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

        records = self.saved()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["registration_number"], VALID["registration_number"])

        page = resp.get_data(as_text=True)
        self.assertIn("Ayesha Khan", page)
        self.assertIn("FA22-BCS-014", page)
        self.assertIn(VALID["submission_url"], page)
        self.assertIn("Submission saved", page)

    def test_tc2_missing_registration_number_is_rejected(self):
        """Missing registration number -> rejected with a validation message."""
        data = {**VALID, "registration_number": ""}
        resp = self.client.post("/submit", data=data)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Registration number is required.", resp.get_data(as_text=True))
        self.assertEqual(self.saved(), [])

    def test_tc3_invalid_submission_url_is_rejected_and_not_saved(self):
        """Invalid URL -> rejected and nothing is written to storage."""
        data = {**VALID, "submission_url": "not-a-valid-url"}
        resp = self.client.post("/submit", data=data)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("valid submission URL", resp.get_data(as_text=True))
        self.assertEqual(self.saved(), [])
        listing = self.client.get("/api/submissions").get_json()
        self.assertEqual(listing, [])

    # ---- Additional coverage ------------------------------------------------

    def test_missing_student_name_is_rejected(self):
        resp = self.client.post("/submit", data={**VALID, "student_name": "   "})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Student name is required.", resp.get_data(as_text=True))
        self.assertEqual(self.saved(), [])

    def test_missing_assignment_title_is_rejected(self):
        resp = self.client.post("/submit", data={**VALID, "assignment_title": ""})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Assignment title is required.", resp.get_data(as_text=True))

    def test_missing_url_is_rejected(self):
        resp = self.client.post("/submit", data={**VALID, "submission_url": ""})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Submission URL is required.", resp.get_data(as_text=True))

    def test_malformed_and_unsafe_urls_are_rejected(self):
        bad_urls = [
            "ftp://example.com/file",
            "javascript:alert(1)",
            "http://",
            "https://exa mple.com",
            "example",
            "http://-bad-.com",
        ]
        for url in bad_urls:
            resp = self.client.post("/submit", data={**VALID, "submission_url": url})
            self.assertEqual(resp.status_code, 400, msg=f"{url!r} should be rejected")
        self.assertEqual(self.saved(), [])

    def test_valid_url_variants_are_accepted(self):
        for url in [
            "https://github.com/user/repo",
            "http://example.org/path?q=1#frag",
            "https://drive.google.com/file/d/abc123/view",
            "http://localhost:8000/report",
        ]:
            self.assertTrue(is_valid_url(url), msg=url)

    def test_empty_state_message_when_no_submissions(self):
        page = self.client.get("/").get_data(as_text=True)
        self.assertIn("No submissions yet", page)

    def test_multiple_submissions_are_all_listed(self):
        self.client.post("/submit", data=VALID)
        self.client.post("/submit", data={**VALID, "student_name": "Bilal Ahmed",
                                          "registration_number": "FA22-BCS-020"})
        self.assertEqual(len(self.saved()), 2)
        page = self.client.get("/").get_data(as_text=True)
        self.assertIn("Bilal Ahmed", page)
        self.assertIn("Ayesha Khan", page)

    def test_html_in_input_is_escaped(self):
        self.client.post("/submit", data={**VALID, "student_name": "<script>alert(1)</script>"})
        page = self.client.get("/").get_data(as_text=True)
        self.assertNotIn("<script>alert(1)</script>", page)
        self.assertIn("&lt;script&gt;", page)

    def test_submissions_persist_across_app_instances(self):
        self.client.post("/submit", data=VALID)
        other = create_app({"TESTING": True, "SUBMISSIONS_FILE": str(self.data_file)})
        page = other.test_client().get("/").get_data(as_text=True)
        self.assertIn("Ayesha Khan", page)

    def test_health_endpoint(self):
        self.assertEqual(self.client.get("/health").get_json(), {"status": "ok"})


if __name__ == "__main__":
    unittest.main()
