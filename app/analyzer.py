import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re

class ResumeAnalyzer:
    TECHNICAL_SKILLS = [
        'python', 'javascript', 'java', 'c++', 'c#', 'php', 'ruby', 'go', 'rust', 'swift', 'kotlin',
        'sql', 'nosql', 'mongodb', 'postgresql', 'mysql', 'redis', 'elasticsearch',
        'react', 'angular', 'vue', 'next.js', 'node.js', 'express', 'flask', 'django', 'fastapi',
        'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'terraform', 'jenkins', 'ansible',
        'git', 'linux', 'ci/cd', 'agile', 'scrum', 'devops', 'microservices', 'rest api', 'graphql',
        'machine learning', 'deep learning', 'nlp', 'pytorch', 'tensorflow', 'pandas', 'numpy', 'scikit-learn',
        'html', 'css', 'sass', 'tailwind', 'typescript', 'webpack', 'unit testing', 'cypress', 'jest'
    ]
    
    SOFT_SKILLS = [
        'leadership', 'communication', 'problem solving', 'teamwork', 'critical thinking',
        'time management', 'adaptability', 'creativity', 'mentoring', 'project management'
    ]

    @staticmethod
    def clean_text(text):
        text = text.lower()
        text = re.sub(r'[^a-z0-9\s]', ' ', text)
        return " ".join(text.split())

    @classmethod
    def extract_skills(cls, text):
        text_lower = text.lower()
        found = []
        for skill in cls.TECHNICAL_SKILLS + cls.SOFT_SKILLS:
            if re.search(rf'\b{re.escape(skill)}\b', text_lower):
                found.append(skill)
        return found

    @classmethod
    def analyze(cls, resume_text, job_description, required_skills_str, min_exp, min_edu):
        # 1. Similarity Score
        vectorizer = TfidfVectorizer(stop_words='english')
        tfidf = vectorizer.fit_transform([cls.clean_text(resume_text), cls.clean_text(job_description)])
        similarity = cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0]
        
        # 2. Skill Score
        req_skills = [s.strip().lower() for s in required_skills_str.split(',') if s.strip()]
        res_skills = cls.extract_skills(resume_text)
        
        matched = [s for s in req_skills if s in res_skills]
        missing = [s for s in req_skills if s not in res_skills]
        
        skill_score = (len(matched) / len(req_skills)) if req_skills else 1.0
        
        # 3. Experience Score
        # Heuristic extraction
        from app.resume_parser import ResumeParser
        exp_years = ResumeParser.extract_experience_years(resume_text)
        exp_score = min(1.0, exp_years / max(1, min_exp))
        
        # 4. Education Score
        edu_level = ResumeParser.detect_education(resume_text)
        edu_hierarchy = {'none': 0, 'high school': 1, 'associate': 2, 'bachelor': 3, 'master': 4, 'phd': 5}
        req_val = edu_hierarchy.get(min_edu.lower(), 3)
        res_val = edu_hierarchy.get(edu_level, 0)
        edu_score = 1.0 if res_val >= req_val else (res_val / req_val if req_val > 0 else 1.0)
        
        # 5. Composite Score
        overall = (skill_score * 0.4) + (exp_score * 0.25) + (similarity * 0.2) + (edu_score * 0.15)
        overall_pct = round(overall * 100, 1)
        
        # Status
        status = 'not_qualified'
        if overall_pct >= 75: status = 'highly_qualified'
        elif overall_pct >= 55: status = 'qualified'
        elif overall_pct >= 35: status = 'partially_qualified'
        
        # Insights
        strengths = []
        if skill_score > 0.8: strengths.append("Strong technical skill alignment")
        if exp_years >= min_exp: strengths.append(f"Exceeds required experience ({exp_years} years)")
        if similarity > 0.4: strengths.append("High context relevance to job description")
        
        weaknesses = []
        if missing: weaknesses.append(f"Missing key skills: {', '.join(missing[:3])}")
        if exp_years < min_exp: weaknesses.append(f"Experience below requirement ({exp_years} vs {min_exp} years)")
        if res_val < req_val: weaknesses.append(f"Education level mismatch")

        return {
            'overall_score': overall_pct,
            'skill_score': round(skill_score * 100, 1),
            'experience_score': round(exp_score * 100, 1),
            'education_score': round(edu_score * 100, 1),
            'similarity_score': round(similarity * 100, 1),
            'status': status,
            'matched_skills': ",".join(matched),
            'missing_skills': ",".join(missing),
            'strengths': "|".join(strengths),
            'weaknesses': "|".join(weaknesses),
            'experience': exp_years,
            'education': edu_level,
            'explanation': f"Candidate scored {overall_pct}% alignment. " + 
                          (f"Matches {len(matched)}/{len(req_skills)} required skills." if req_skills else "")
        }
