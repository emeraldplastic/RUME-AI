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
        self.assertNotIn("token", response.get_json())
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

    def upload_resume(self, job_id, filename, text, client=None, content_type="text/plain"):
        client = client or self.client
        return client.post(
            f"/api/jobs/{job_id}/upload",
            headers=self.csrf_headers(client),
            data={"resumes": (BytesIO(text.encode("utf-8")), filename, content_type)},
            content_type="multipart/form-data",
        )

    def test_auth_is_required_for_private_endpoints(self):
        response = self.client.get("/api/jobs")
        self.assertEqual(response.status_code, 401)

    def test_auth_cookie_is_httponly_and_token_is_not_exposed_to_js(self):
        response = self.register()
        cookies = response.headers.getlist("Set-Cookie")
        auth_cookie = next(cookie for cookie in cookies if cookie.startswith("auth_token="))
        csrf_cookie = next(cookie for cookie in cookies if cookie.startswith("csrf_token="))

        self.assertIn("HttpOnly", auth_cookie)
        self.assertNotIn("HttpOnly", csrf_cookie)
        self.assertIn("SameSite=Strict", auth_cookie)
        self.assertIn("SameSite=Strict", csrf_cookie)

    def test_cookie_mutations_require_csrf_header(self):
        self.register()
        blocked = self.client.post(
            "/api/jobs",
            json={
                "title": "Blocked",
                "description": "This should not save without the CSRF header.",
                "required_skills": "python",
                "min_experience": 1,
                "min_education": "bachelor",
            },
        )
        self.assertEqual(blocked.status_code, 403)

        allowed_job_id = self.create_job()
        self.assertIsInstance(allowed_job_id, int)

    def test_resume_text_is_encrypted_and_results_are_sorted(self):
        self.register()
        job_id = self.create_job()
        strong = (
            "Jane Candidate\njane@example.com\nBachelor of Science\n"
            "5 years experience building python react sql aws platforms."
        )
        weak = (
            "Mark Intern\nmark@example.com\nHigh school\n"
            "1 year experience writing documentation and support notes."
        )

        first = self.upload_resume(job_id, "jane.txt", strong)
        second = self.upload_resume(job_id, "mark.txt", weak)
        self.assertEqual(first.status_code, 201, first.get_data(as_text=True))
        self.assertEqual(second.status_code, 201, second.get_data(as_text=True))

        with self.app.app_context():
            encrypted = Resume.query.filter_by(job_id=job_id).first()
            self.assertNotIn("Jane Candidate", encrypted.raw_text_encrypted)
            self.assertNotIn("jane@example.com", encrypted.candidate_email_encrypted)

        analysis = self.client.post(f"/api/jobs/{job_id}/analyze", headers=self.csrf_headers())
        self.assertEqual(analysis.status_code, 200, analysis.get_data(as_text=True))

        results = self.client.get(
            f"/api/jobs/{job_id}/results?sort=score",
        )
        self.assertEqual(results.status_code, 200, results.get_data(as_text=True))
        candidates = results.get_json()["candidates"]
        self.assertGreaterEqual(candidates[0]["analysis"]["overall_score"], candidates[1]["analysis"]["overall_score"])
        self.assertEqual(candidates[0]["candidate_email_masked"], "j**e@example.com")
        self.assertNotIn("candidate_email", candidates[0])

    def test_upload_rejects_mime_extension_mismatch(self):
        self.register()
        job_id = self.create_job()
        response = self.upload_resume(
            job_id,
            "not-a-pdf.pdf",
            "Jane Candidate\njane@example.com\nBachelor\n5 years python sql",
            content_type="text/plain",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["uploaded"], 0)
        self.assertIn("file type does not match", response.get_json()["errors"][0])

    def test_jobs_are_scoped_to_the_authenticated_user(self):
        self.register("owner")
        job_id = self.create_job()
        intruder = self.app.test_client()
        self.register("intruder", client=intruder)

        response = intruder.get(f"/api/jobs/{job_id}")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
