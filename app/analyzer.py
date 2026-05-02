"""Deterministic resume analysis engine used by RUME AI."""
import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.resume_parser import ResumeParser


class ResumeAnalyzer:
    TECHNICAL_SKILLS = {
        "python", "javascript", "typescript", "java", "c++", "c#", "go", "rust", "php", "ruby",
        "sql", "postgresql", "mysql", "sqlite", "mongodb", "redis", "elasticsearch", "snowflake",
        "react", "angular", "vue", "next.js", "node.js", "express", "flask", "django", "fastapi",
        "html", "css", "tailwind", "sass", "graphql", "rest api", "api design",
        "aws", "azure", "gcp", "docker", "kubernetes", "terraform", "jenkins", "github actions",
        "linux", "bash", "powershell", "ci/cd", "devops", "microservices", "serverless",
        "machine learning", "deep learning", "nlp", "computer vision", "pytorch", "tensorflow",
        "scikit-learn", "pandas", "numpy", "data analysis", "data engineering", "etl",
        "unit testing", "integration testing", "pytest", "jest", "cypress", "selenium",
        "agile", "scrum", "jira", "figma", "salesforce", "sap", "power bi", "tableau",
    }
    SOFT_SKILLS = {
        "leadership", "communication", "problem solving", "teamwork", "critical thinking",
        "time management", "adaptability", "creativity", "mentoring", "project management",
        "stakeholder management", "collaboration", "presentation", "attention to detail",
    }
    EDUCATION_HIERARCHY = {
        "not specified": 0,
        "high school": 1,
        "associate": 2,
        "bachelor": 3,
        "master": 4,
        "phd": 5,
    }
    WEIGHTS = {
        "skill": 0.40,
        "experience": 0.25,
        "education": 0.15,
        "similarity": 0.20,
    }

    @staticmethod
    def clean_text(text: str) -> str:
        text = (text or "").lower()
        text = re.sub(r"[^a-z0-9+#./\s-]", " ", text)
        return " ".join(text.split())

    @classmethod
    def extract_skills(cls, text: str) -> list[str]:
        text_lower = cls.clean_text(text)
        skills = set()
        for skill in cls.TECHNICAL_SKILLS | cls.SOFT_SKILLS:
            if re.search(r"\b" + re.escape(skill) + r"\b", text_lower):
                skills.add(skill)
        return sorted(skills)

    @classmethod
    def _similarity(cls, resume_text: str, job_description: str) -> float:
        clean_resume = cls.clean_text(resume_text)
        clean_job = cls.clean_text(job_description)
        if not clean_resume or not clean_job:
            return 0.0
        try:
            vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=6000)
            tfidf = vectorizer.fit_transform([clean_job, clean_resume])
            return float(cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0])
        except ValueError:
            return 0.0

    @classmethod
    def _required_skills(cls, required_skills_str: str) -> list[str]:
        return sorted({s.strip().lower() for s in (required_skills_str or "").split(",") if s.strip()})

    @classmethod
    def analyze(cls, resume_text, job_description, required_skills_str="", min_exp=0, min_edu="bachelor"):
        resume_skills = set(cls.extract_skills(resume_text))
        required_skills = cls._required_skills(required_skills_str)

        matched = sorted(set(required_skills) & resume_skills)
        missing = sorted(set(required_skills) - resume_skills)
        skill_score = (len(matched) / len(required_skills) * 100) if required_skills else 70.0

        exp_years = ResumeParser.extract_experience_years(resume_text)
        min_exp = max(int(min_exp or 0), 0)
        if min_exp == 0:
            experience_score = 75.0 if exp_years else 60.0
        elif exp_years >= min_exp:
            experience_score = min(100.0, 82.0 + (exp_years - min_exp) * 4)
        else:
            experience_score = max(8.0, (exp_years / min_exp) * 70.0)

        education = ResumeParser.detect_education(resume_text)
        candidate_edu_value = cls.EDUCATION_HIERARCHY.get(education, 0)
        required_edu_value = cls.EDUCATION_HIERARCHY.get((min_edu or "bachelor").lower(), 3)
        if required_edu_value == 0:
            education_score = 70.0
        elif candidate_edu_value >= required_edu_value:
            education_score = min(100.0, 82.0 + (candidate_edu_value - required_edu_value) * 6)
        else:
            education_score = max(15.0, (candidate_edu_value / required_edu_value) * 65.0)

        similarity_score = cls._similarity(resume_text, job_description) * 100

        overall = (
            cls.WEIGHTS["skill"] * skill_score
            + cls.WEIGHTS["experience"] * experience_score
            + cls.WEIGHTS["education"] * education_score
            + cls.WEIGHTS["similarity"] * similarity_score
        )
        overall = round(min(max(overall, 0.0), 100.0), 1)

        if overall >= 75:
            status = "highly_qualified"
        elif overall >= 55:
            status = "qualified"
        elif overall >= 35:
            status = "partially_qualified"
        else:
            status = "not_qualified"

        strengths = []
        if skill_score >= 70:
            strengths.append(f"Matches {len(matched)} required skills")
        if exp_years >= min_exp and min_exp > 0:
            strengths.append(f"Meets the {min_exp}+ year experience requirement")
        if education_score >= 80:
            strengths.append("Education meets or exceeds the role requirement")
        if similarity_score >= 45:
            strengths.append("Resume language is strongly aligned to the job description")
        if not strengths:
            strengths.append("Resume was parsed and scored successfully")

        weaknesses = []
        if missing:
            weaknesses.append(f"Missing skills: {', '.join(missing[:5])}")
        if min_exp and exp_years < min_exp:
            weaknesses.append(f"Experience appears below target: {exp_years:g} vs {min_exp}+ years")
        if candidate_edu_value < required_edu_value:
            weaknesses.append("Education signal is below or not clearly stated for the requirement")
        if similarity_score < 20:
            weaknesses.append("Resume content has limited similarity to the job description")
        if not weaknesses:
            weaknesses.append("No major gaps detected")

        explanation = (
            f"Overall fit is {overall}/100. The candidate matched {len(matched)} of "
            f"{len(required_skills)} required skills, showed {exp_years:g} years of experience, "
            f"and has education classified as {education}."
        )

        return {
            "overall_score": overall,
            "skill_score": round(skill_score, 1),
            "experience_score": round(experience_score, 1),
            "education_score": round(education_score, 1),
            "similarity_score": round(similarity_score, 1),
            "status": status,
            "matched_skills": ",".join(matched),
            "missing_skills": ",".join(missing),
            "strengths": "|".join(strengths),
            "weaknesses": "|".join(weaknesses),
            "experience": exp_years,
            "education": education,
            "all_skills": sorted(resume_skills),
            "explanation": explanation,
        }
