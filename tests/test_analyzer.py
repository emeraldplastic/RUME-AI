import unittest

from app.analyzer import ResumeAnalyzer


class ResumeAnalyzerSkillMatchingTest(unittest.TestCase):
    def test_extract_skills_normalizes_common_resume_aliases(self):
        text = (
            "Built NodeJS services with JS/TS, React.js, Postgres, k8s, "
            "GitHub Actions, sklearn pipelines, and C++ modules."
        )

        skills = ResumeAnalyzer.extract_skills(text)

        for expected in (
            "node.js",
            "javascript",
            "typescript",
            "react",
            "postgresql",
            "kubernetes",
            "github actions",
            "scikit-learn",
            "c++",
        ):
            self.assertIn(expected, skills)

    def test_required_skills_accept_mixed_separators_and_aliases(self):
        resume = (
            "Full Stack Engineer with 6 years of experience using Python, React.js, "
            "NodeJS, TypeScript, Postgres, and k8s. Bachelor of Science."
        )
        job = "Build secure Python and React APIs on Kubernetes with PostgreSQL."

        analysis = ResumeAnalyzer.analyze(
            resume,
            job,
            "Python; React / TypeScript\nNodeJS | Postgres, k8s",
            min_exp=4,
            min_edu="bachelor",
        )

        matched = set(analysis["matched_skills"].split(","))
        self.assertEqual(
            matched,
            {"python", "react", "typescript", "node.js", "postgresql", "kubernetes"},
        )
        self.assertEqual(analysis["missing_skills"], "")
        self.assertEqual(analysis["skill_score"], 100.0)


if __name__ == "__main__":
    unittest.main()
