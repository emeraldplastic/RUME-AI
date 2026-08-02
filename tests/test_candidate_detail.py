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


class CandidateDetailTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app(
            {
                "TESTING": True,
                "RATELIMIT_ENABLED": False,
                "MAX_CONTENT_LENGTH": 1024 * 1024,
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

    def register(self, username="owner", client=None):
        client = client or self.client
        response = client.post(
            "/api/auth/register",
            json={
                "username": username,
                "email": f"{username}@example.com",
                "display_name": username.title(),
                "password": "password123",
            },
        )
        self.assertEqual(response.status_code, 201, response.get_data(as_text=True))
        return response

    def csrf_headers(self, client=None):
        client = client or self.client
        csrf_cookie = client.get_cookie("csrf_token")
        self.assertIsNotNone(csrf_cookie)
        return {"X-CSRF-Token": csrf_cookie.value}

    def create_job(self, client=None):
        client = client or self.client
        response = client.post(
            "/api/jobs",
            headers=self.csrf_headers(client),
            json={
                "title": "Full Stack Engineer",
                "description": "Build Flask React SQL systems on AWS with secure APIs.",
                "required_skills": "python, react, sql, aws",
                "min_experience": 3,
                "min_education": "bachelor",
            },
        )
        self.assertEqual(response.status_code, 201, response.get_data(as_text=True))
        return response.get_json()["id"]

    def upload_resume(self, job_id, filename, text, client=None):
        client = client or self.client
        return client.post(
            f"/api/jobs/{job_id}/upload",
            headers=self.csrf_headers(client),
            data={"resumes": (BytesIO(text.encode("utf-8")), filename, "text/plain")},
            content_type="multipart/form-data",
        )

    def seed_candidate(self):
        self.register()
        job_id = self.create_job()
        text = (
            "Jane Candidate\njane@example.com\nBachelor of Science\n"
            "5 years experience building python react sql aws platforms."
        )
        response = self.upload_resume(job_id, "jane.txt", text)
        self.assertEqual(response.status_code, 201, response.get_data(as_text=True))
        analysis = self.client.post(f"/api/jobs/{job_id}/analyze", headers=self.csrf_headers())
        self.assertEqual(analysis.status_code, 200, analysis.get_data(as_text=True))
        resume_id = self.client.get(f"/api/jobs/{job_id}/results").get_json()["candidates"][0]["id"]
        return job_id, resume_id

    def test_candidate_detail_requires_auth(self):
        job_id, resume_id = self.seed_candidate()
        anonymous = self.app.test_client()
        response = anonymous.get(f"/api/jobs/{job_id}/candidates/{resume_id}")
        self.assertEqual(response.status_code, 401)

    def test_candidate_detail_not_found(self):
        self.register()
        job_id = self.create_job()
        response = self.client.get(f"/api/jobs/{job_id}/candidates/9999")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json()["error"], "Candidate not found")

    def test_candidate_detail_returns_full_payload(self):
        job_id, resume_id = self.seed_candidate()
        headers = self.csrf_headers()
        comment = self.client.post(
            f"/api/jobs/{job_id}/candidates/{resume_id}/comments",
            headers=headers,
            json={"comment": "Strong technical candidate"},
        )
        self.assertEqual(comment.status_code, 201, comment.get_data(as_text=True))
        tag = self.client.post(
            f"/api/jobs/{job_id}/candidates/{resume_id}/tags",
            headers=headers,
            json={"tag": "promote", "color": "#22c55e"},
        )
        self.assertEqual(tag.status_code, 201, tag.get_data(as_text=True))
        decision = self.client.post(
            f"/api/jobs/{job_id}/candidates/{resume_id}/decision",
            headers=headers,
            json={"decision": "advance", "note": "Schedule first round"},
        )
        self.assertEqual(decision.status_code, 201, decision.get_data(as_text=True))

        response = self.client.get(f"/api/jobs/{job_id}/candidates/{resume_id}")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["candidate"]["id"], resume_id)
        self.assertIn("analysis", data["candidate"])
        self.assertEqual(len(data["comments"]), 1)
        self.assertEqual(data["comments"][0]["comment"], "Strong technical candidate")
        self.assertEqual(len(data["tags"]), 1)
        self.assertEqual(data["tags"][0]["tag"], "promote")
        self.assertEqual(len(data["decisions"]), 1)
        self.assertEqual(data["decisions"][0]["decision"], "advance")

    def test_candidate_detail_is_scoped_to_owner(self):
        self.register("owner")
        job_id = self.create_job()
        text = "Jane Candidate\njane@example.com\nBachelor\n5 years python sql"
        self.upload_resume(job_id, "jane.txt", text)
        resume_id = self.client.get(f"/api/jobs/{job_id}/results").get_json()["candidates"][0]["id"]

        intruder = self.app.test_client()
        self.register("intruder", client=intruder)
        response = intruder.get(f"/api/jobs/{job_id}/candidates/{resume_id}")
        self.assertEqual(response.status_code, 404)

    def test_candidate_detail_blind_mode_masks_identity(self):
        job_id, resume_id = self.seed_candidate()
        response = self.client.get(f"/api/jobs/{job_id}/candidates/{resume_id}?blind=1")
        self.assertEqual(response.status_code, 200)
        candidate = response.get_json()["candidate"]
        self.assertTrue(candidate["blind_review"])
        self.assertEqual(candidate["candidate_name"], f"Candidate {resume_id}")
        self.assertEqual(candidate["candidate_email_masked"], "")


if __name__ == "__main__":
    unittest.main()
