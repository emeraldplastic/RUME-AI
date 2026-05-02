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
from app.models import Resume


class RumeApiSecurityTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app(
            {
                "TESTING": True,
                "RATELIMIT_ENABLED": False,
                "WTF_CSRF_ENABLED": False,
                "MAX_CONTENT_LENGTH": 1024 * 1024,
            }
        )
        self.client = self.app.test_client()
        with self.app.app_context():
            db.drop_all()
            db.create_all()

    def register(self, username="owner"):
        response = self.client.post(
            "/api/auth/register",
            json={
                "username": username,
                "email": f"{username}@example.com",
                "display_name": username.title(),
                "password": "password123",
            },
        )
        self.assertEqual(response.status_code, 201, response.get_data(as_text=True))
        return response.get_json()["token"]

    def create_job(self, token):
        response = self.client.post(
            "/api/jobs",
            headers={"Authorization": f"Bearer {token}"},
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

    def upload_resume(self, token, job_id, filename, text):
        return self.client.post(
            f"/api/jobs/{job_id}/upload",
            headers={"Authorization": f"Bearer {token}"},
            data={"resumes": (BytesIO(text.encode("utf-8")), filename)},
            content_type="multipart/form-data",
        )

    def test_auth_is_required_for_private_endpoints(self):
        response = self.client.get("/api/jobs")
        self.assertEqual(response.status_code, 401)

    def test_resume_text_is_encrypted_and_results_are_sorted(self):
        token = self.register()
        job_id = self.create_job(token)
        strong = (
            "Jane Candidate\njane@example.com\nBachelor of Science\n"
            "5 years experience building python react sql aws platforms."
        )
        weak = (
            "Mark Intern\nmark@example.com\nHigh school\n"
            "1 year experience writing documentation and support notes."
        )

        first = self.upload_resume(token, job_id, "jane.txt", strong)
        second = self.upload_resume(token, job_id, "mark.txt", weak)
        self.assertEqual(first.status_code, 201, first.get_data(as_text=True))
        self.assertEqual(second.status_code, 201, second.get_data(as_text=True))

        with self.app.app_context():
            encrypted = Resume.query.filter_by(job_id=job_id).first()
            self.assertNotIn("Jane Candidate", encrypted.raw_text_encrypted)
            self.assertNotIn("jane@example.com", encrypted.candidate_email_encrypted)

        analysis = self.client.post(f"/api/jobs/{job_id}/analyze", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(analysis.status_code, 200, analysis.get_data(as_text=True))

        results = self.client.get(
            f"/api/jobs/{job_id}/results?sort=score",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(results.status_code, 200, results.get_data(as_text=True))
        candidates = results.get_json()["candidates"]
        self.assertGreaterEqual(candidates[0]["analysis"]["overall_score"], candidates[1]["analysis"]["overall_score"])
        self.assertEqual(candidates[0]["candidate_email_masked"], "j**e@example.com")
        self.assertNotIn("candidate_email", candidates[0])

    def test_jobs_are_scoped_to_the_authenticated_user(self):
        owner_token = self.register("owner")
        intruder_token = self.register("intruder")
        job_id = self.create_job(owner_token)

        response = self.client.get(f"/api/jobs/{job_id}", headers={"Authorization": f"Bearer {intruder_token}"})
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
