import os
import unittest
from io import BytesIO

from cryptography.fernet import Fernet

os.environ["TESTING"] = "1"
os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["JWT_SECRET"] = "test-jwt-secret-with-more-than-32-bytes"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.main import create_app, db


class RumeTrustLayerTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app(
            {
                "TESTING": True,
                "RATELIMIT_ENABLED": False,
                "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
                "SECRET_KEY": os.environ["SECRET_KEY"],
                "JWT_SECRET": os.environ["JWT_SECRET"],
                "ENCRYPTION_KEY": os.environ["ENCRYPTION_KEY"],
                "LOG_LEVEL": "ERROR",
            }
        )
        self.client = self.app.test_client()
        with self.app.app_context():
            db.drop_all()
            db.create_all()

    def csrf_headers(self):
        csrf_cookie = self.client.get_cookie("csrf_token")
        self.assertIsNotNone(csrf_cookie)
        return {"X-CSRF-Token": csrf_cookie.value}

    def register(self):
        response = self.client.post(
            "/api/auth/register",
            json={
                "username": "trustowner",
                "email": "trustowner@example.com",
                "display_name": "Trust Owner",
                "password": "password123",
            },
        )
        self.assertEqual(response.status_code, 201, response.get_data(as_text=True))

    def create_job(self):
        response = self.client.post(
            "/api/jobs",
            headers=self.csrf_headers(),
            json={
                "title": "Platform Engineer",
                "description": "Own Python, React, PostgreSQL, Kubernetes, and secure platform operations.",
                "required_skills": "Python; React | Postgres, k8s",
                "min_experience": 4,
                "min_education": "bachelor",
            },
        )
        self.assertEqual(response.status_code, 201, response.get_data(as_text=True))
        return response.get_json()["id"]

    def upload_resume(self, job_id):
        text = (
            "Priya Builder\npriya@example.com\nBachelor of Science\n"
            "6 years of experience building Python APIs, React dashboards, "
            "Postgres reporting systems, and k8s deployment workflows."
        )
        response = self.client.post(
            f"/api/jobs/{job_id}/upload",
            headers=self.csrf_headers(),
            data={"resumes": (BytesIO(text.encode("utf-8")), "priya.txt", "text/plain")},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 201, response.get_data(as_text=True))
        return response.get_json()["results"][0]["id"]

    def test_analysis_records_evidence_calibration_blind_review_decisions_and_audit_pack(self):
        self.register()
        job_id = self.create_job()
        resume_id = self.upload_resume(job_id)

        analysis = self.client.post(f"/api/jobs/{job_id}/analyze", headers=self.csrf_headers())
        self.assertEqual(analysis.status_code, 200, analysis.get_data(as_text=True))
        self.assertEqual(analysis.get_json()["calibration_version"]["version"], 1)

        results = self.client.get(f"/api/jobs/{job_id}/results")
        self.assertEqual(results.status_code, 200, results.get_data(as_text=True))
        candidate = results.get_json()["candidates"][0]
        evidence = candidate["analysis"]["evidence"]
        self.assertIn("python", evidence["matched_skills"])
        self.assertTrue(evidence["matched_skills"]["python"][0]["snippet"])
        self.assertEqual(candidate["analysis"]["calibration_version_id"], 1)

        blind = self.client.get(f"/api/jobs/{job_id}/results?blind=1")
        blind_candidate = blind.get_json()["candidates"][0]
        self.assertEqual(blind_candidate["candidate_name"], f"Candidate {resume_id}")
        self.assertEqual(blind_candidate["candidate_email_masked"], "")
        self.assertTrue(blind_candidate["blind_review"])

        decision = self.client.post(
            f"/api/jobs/{job_id}/candidates/{resume_id}/decision",
            headers=self.csrf_headers(),
            json={"decision": "advance", "note": "Evidence supports a phone screen."},
        )
        self.assertEqual(decision.status_code, 201, decision.get_data(as_text=True))
        self.assertEqual(decision.get_json()["decision"], "advance")
        self.assertEqual(decision.get_json()["note"], "Evidence supports a phone screen.")

        pack = self.client.get(f"/api/jobs/{job_id}/audit-pack")
        self.assertEqual(pack.status_code, 200, pack.get_data(as_text=True))
        pack_json = pack.get_json()
        self.assertEqual(pack_json["calibration_versions"][0]["version"], 1)
        self.assertEqual(pack_json["decision_journal"][0]["decision"], "advance")
        self.assertIn("privacy_note", pack_json)
        self.assertNotIn("raw_text", str(pack_json).lower())

    def test_logs_endpoint_returns_queryable_structured_request_logs(self):
        self.register()
        response = self.client.get("/api/logs?event=request.completed&limit=10")

        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        logs = response.get_json()["logs"]
        self.assertTrue(logs)
        self.assertEqual(logs[0]["event"], "request.completed")
        self.assertIn("request_id", logs[0])
        self.assertIn("payload", logs[0])


if __name__ == "__main__":
    unittest.main()
