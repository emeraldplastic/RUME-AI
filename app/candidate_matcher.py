"""
Advanced Candidate Matcher for RUME AI.
Provides intelligent candidate matching with ML-based scoring and recommendations.
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import re
import logging
from collections import Counter

logger = logging.getLogger(__name__)

@dataclass
class SkillMatch:
    """Represents a skill match between candidate and job requirements."""
    skill: str
    candidate_has: bool
    required: bool
    proficiency_level: Optional[str] = None
    years_experience: Optional[float] = None
    match_score: float = 0.0

@dataclass
class CandidateScore:
    """Comprehensive candidate scoring result."""
    candidate_id: str
    overall_score: float
    skill_score: float
    experience_score: float
    education_score: float
    culture_fit_score: float
    skill_matches: List[SkillMatch]
    missing_skills: List[str]
    strengths: List[str]
    weaknesses: List[str]
    recommendation: str
    confidence: float

@dataclass
class JobRequirement:
    """Represents job requirements for matching."""
    job_id: str
    title: str
    required_skills: List[str]
    preferred_skills: List[str]
    min_experience_years: float
    required_education: str
    industry: Optional[str] = None
    seniority: Optional[str] = None

@dataclass
class CandidateProfile:
    """Represents a candidate's profile."""
    candidate_id: str
    skills: List[str]
    skill_levels: Dict[str, str]  # skill -> proficiency level
    experience_years: float
    education_level: str
    education_field: str
    current_role: Optional[str] = None
    industry: Optional[str] = None
    previous_companies: List[str] = None
    achievements: List[str] = None

class CandidateMatcher:
    """Advanced candidate matching with ML-inspired scoring."""
    
    def __init__(self):
        self.skill_weights = {
            "required": 1.0,
            "preferred": 0.5,
            "bonus": 0.3
        }
        
        self.proficiency_levels = {
            "expert": 1.0,
            "advanced": 0.8,
            "intermediate": 0.6,
            "beginner": 0.4,
            "familiar": 0.2
        }
        
        self.education_levels = {
            "phd": 1.0,
            "masters": 0.9,
            "bachelors": 0.8,
            "associate": 0.6,
            "certificate": 0.4,
            "high_school": 0.2
        }
    
    def match_candidate(
        self,
        candidate: CandidateProfile,
        job: JobRequirement
    ) -> CandidateScore:
        """
        Match a candidate against job requirements with comprehensive scoring.
        
        Args:
            candidate: CandidateProfile with candidate details
            job: JobRequirement with job details
        
        Returns:
            CandidateScore with detailed matching results
        """
        # Skill matching
        skill_matches, missing_skills = self._match_skills(candidate, job)
        skill_score = self._calculate_skill_score(skill_matches, job)
        
        # Experience scoring
        experience_score = self._calculate_experience_score(candidate, job)
        
        # Education scoring
        education_score = self._calculate_education_score(candidate, job)
        
        # Culture fit scoring (industry and role alignment)
        culture_fit_score = self._calculate_culture_fit(candidate, job)
        
        # Overall score (weighted average)
        overall_score = (
            skill_score * 0.4 +
            experience_score * 0.3 +
            education_score * 0.2 +
            culture_fit_score * 0.1
        )
        
        # Generate insights
        strengths, weaknesses = self._generate_insights(
            candidate, job, skill_matches, missing_skills
        )
        
        # Generate recommendation
        recommendation, confidence = self._generate_recommendation(
            overall_score, skill_score, experience_score
        )
        
        return CandidateScore(
            candidate_id=candidate.candidate_id,
            overall_score=overall_score,
            skill_score=skill_score,
            experience_score=experience_score,
            education_score=education_score,
            culture_fit_score=culture_fit_score,
            skill_matches=skill_matches,
            missing_skills=missing_skills,
            strengths=strengths,
            weaknesses=weaknesses,
            recommendation=recommendation,
            confidence=confidence
        )
    
    def _match_skills(
        self,
        candidate: CandidateProfile,
        job: JobRequirement
    ) -> Tuple[List[SkillMatch], List[str]]:
        """Match candidate skills against job requirements."""
        skill_matches = []
        missing_skills = []
        
        # Check required skills
        for skill in job.required_skills:
            candidate_has = skill.lower() in [s.lower() for s in candidate.skills]
            proficiency = candidate.skill_levels.get(skill, "beginner")
            
            match = SkillMatch(
                skill=skill,
                candidate_has=candidate_has,
                required=True,
                proficiency_level=proficiency if candidate_has else None,
                match_score=self._calculate_skill_match_score(candidate_has, proficiency, True)
            )
            skill_matches.append(match)
            
            if not candidate_has:
                missing_skills.append(skill)
        
        # Check preferred skills
        for skill in job.preferred_skills:
            candidate_has = skill.lower() in [s.lower() for s in candidate.skills]
            proficiency = candidate.skill_levels.get(skill, "beginner")
            
            match = SkillMatch(
                skill=skill,
                candidate_has=candidate_has,
                required=False,
                proficiency_level=proficiency if candidate_has else None,
                match_score=self._calculate_skill_match_score(candidate_has, proficiency, False)
            )
            skill_matches.append(match)
        
        # Check for bonus skills (candidate has skills not in requirements)
        candidate_skill_set = set(s.lower() for s in candidate.skills)
        required_skill_set = set(s.lower() for s in job.required_skills + job.preferred_skills)
        bonus_skills = candidate_skill_set - required_skill_set
        
        for skill in bonus_skills:
            proficiency = candidate.skill_levels.get(skill, "intermediate")
            match = SkillMatch(
                skill=skill,
                candidate_has=True,
                required=False,
                proficiency_level=proficiency,
                match_score=self._calculate_skill_match_score(True, proficiency, False, is_bonus=True)
            )
            skill_matches.append(match)
        
        return skill_matches, missing_skills
    
    def _calculate_skill_match_score(
        self,
        candidate_has: bool,
        proficiency: str,
        required: bool,
        is_bonus: bool = False
    ) -> float:
        """Calculate individual skill match score."""
        if not candidate_has:
            return 0.0 if required else -0.1  # Penalty for missing preferred skills
        
        prof_score = self.proficiency_levels.get(proficiency.lower(), 0.5)
        
        if is_bonus:
            return prof_score * self.skill_weights["bonus"]
        
        weight = self.skill_weights["required"] if required else self.skill_weights["preferred"]
        return prof_score * weight
    
    def _calculate_skill_score(
        self,
        skill_matches: List[SkillMatch],
        job: JobRequirement
    ) -> float:
        """Calculate overall skill score."""
        if not skill_matches:
            return 0.0
        
        total_score = sum(match.match_score for match in skill_matches)
        max_possible = len(job.required_skills) * self.skill_weights["required"] + \
                      len(job.preferred_skills) * self.skill_weights["preferred"]
        
        return min(1.0, max(0.0, total_score / max_possible if max_possible > 0 else 0))
    
    def _calculate_experience_score(
        self,
        candidate: CandidateProfile,
        job: JobRequirement
    ) -> float:
        """Calculate experience match score."""
        if job.min_experience_years == 0:
            return 1.0
        
        if candidate.experience_years >= job.min_experience_years:
            # Bonus for extra experience (up to 2x required)
            excess_ratio = min(2.0, candidate.experience_years / job.min_experience_years)
            return min(1.0, 0.7 + 0.3 * (excess_ratio - 1))
        else:
            # Penalty for insufficient experience
            ratio = candidate.experience_years / job.min_experience_years
            return max(0.0, ratio * 0.7)
    
    def _calculate_education_score(
        self,
        candidate: CandidateProfile,
        job: JobRequirement
    ) -> float:
        """Calculate education match score."""
        candidate_edu_score = self.education_levels.get(
            candidate.education_level.lower(), 0.5
        )
        
        # Check if education field matches
        field_match = 1.0
        if job.industry and candidate.education_field:
            field_match = 0.8 if job.industry.lower() in candidate.education_field.lower() else 0.5
        
        return (candidate_edu_score + field_match) / 2
    
    def _calculate_culture_fit(
        self,
        candidate: CandidateProfile,
        job: JobRequirement
    ) -> float:
        """Calculate culture fit based on industry and role alignment."""
        fit_score = 0.5  # Base score
        
        # Industry match
        if job.industry and candidate.industry:
            if job.industry.lower() == candidate.industry.lower():
                fit_score += 0.3
            elif job.industry.lower() in candidate.industry.lower():
                fit_score += 0.15
        
        # Seniority alignment (heuristic based on experience)
        if job.seniority:
            if job.seniority.lower() == "senior" and candidate.experience_years >= 5:
                fit_score += 0.2
            elif job.seniority.lower() == "mid" and 2 <= candidate.experience_years < 5:
                fit_score += 0.2
            elif job.seniority.lower() == "junior" and candidate.experience_years < 2:
                fit_score += 0.2
        
        return min(1.0, fit_score)
    
    def _generate_insights(
        self,
        candidate: CandidateProfile,
        job: JobRequirement,
        skill_matches: List[SkillMatch],
        missing_skills: List[str]
    ) -> Tuple[List[str], List[str]]:
        """Generate strengths and weaknesses insights."""
        strengths = []
        weaknesses = []
        
        # Skill-based insights
        strong_skills = [
            match.skill for match in skill_matches
            if match.candidate_has and match.match_score > 0.7
        ]
        
        if strong_skills:
            strengths.append(f"Strong in {', '.join(strong_skills[:3])}")
        
        if missing_skills:
            weaknesses.append(f"Missing required skills: {', '.join(missing_skills[:3])}")
        
        # Experience insights
        if candidate.experience_years >= job.min_experience_years * 1.5:
            strengths.append(f"Exceeds experience requirements ({candidate.experience_years} years)")
        elif candidate.experience_years < job.min_experience_years:
            weaknesses.append(f"Below experience requirement ({candidate.experience_years} vs {job.min_experience_years} years)")
        
        # Education insights
        candidate_edu_level = self.education_levels.get(candidate.education_level.lower(), 0)
        if candidate_edu_level >= 0.8:
            strengths.append(f"Strong educational background ({candidate.education_level})")
        
        # Industry insights
        if job.industry and candidate.industry and job.industry.lower() == candidate.industry.lower():
            strengths.append(f"Industry experience in {job.industry}")
        
        return strengths, weaknesses
    
    def _generate_recommendation(
        self,
        overall_score: float,
        skill_score: float,
        experience_score: float
    ) -> Tuple[str, float]:
        """Generate hiring recommendation with confidence."""
        if overall_score >= 0.8:
            return "Strongly Recommend", 0.9
        elif overall_score >= 0.6:
            return "Recommend", 0.75
        elif overall_score >= 0.4:
            return "Consider", 0.6
        elif overall_score >= 0.2:
            return "Low Priority", 0.4
        else:
            return "Not Recommended", 0.3
    
    def rank_candidates(
        self,
        candidates: List[CandidateProfile],
        job: JobRequirement
    ) -> List[CandidateScore]:
        """
        Rank multiple candidates for a job.
        
        Args:
            candidates: List of CandidateProfile objects
            job: JobRequirement for the position
        
        Returns:
            List of CandidateScore objects sorted by overall score
        """
        scores = []
        
        for candidate in candidates:
            score = self.match_candidate(candidate, job)
            scores.append(score)
        
        # Sort by overall score descending
        scores.sort(key=lambda x: x.overall_score, reverse=True)
        
        return scores
    
    def find_similar_candidates(
        self,
        reference_candidate: CandidateProfile,
        candidate_pool: List[CandidateProfile],
        top_n: int = 5
    ) -> List[Tuple[CandidateProfile, float]]:
        """
        Find candidates similar to a reference candidate.
        
        Args:
            reference_candidate: Candidate to compare against
            candidate_pool: List of candidates to search
            top_n: Number of similar candidates to return
        
        Returns:
            List of (candidate, similarity_score) tuples
        """
        similarities = []
        
        for candidate in candidate_pool:
            if candidate.candidate_id == reference_candidate.candidate_id:
                continue
            
            similarity = self._calculate_similarity(reference_candidate, candidate)
            similarities.append((candidate, similarity))
        
        # Sort by similarity score descending
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return similarities[:top_n]
    
    def _calculate_similarity(
        self,
        candidate1: CandidateProfile,
        candidate2: CandidateProfile
    ) -> float:
        """Calculate similarity between two candidates."""
        # Skill overlap
        skills1 = set(s.lower() for s in candidate1.skills)
        skills2 = set(s.lower() for s in candidate2.skills)
        
        if not skills1 or not skills2:
            skill_similarity = 0.0
        else:
            intersection = skills1 & skills2
            union = skills1 | skills2
            skill_similarity = len(intersection) / len(union) if union else 0
        
        # Experience similarity
        exp_diff = abs(candidate1.experience_years - candidate2.experience_years)
        exp_similarity = max(0.0, 1.0 - exp_diff / 10)  # Normalize by 10 years
        
        # Education similarity
        edu1 = self.education_levels.get(candidate1.education_level.lower(), 0.5)
        edu2 = self.education_levels.get(candidate2.education_level.lower(), 0.5)
        edu_similarity = 1.0 - abs(edu1 - edu2)
        
        # Industry similarity
        industry_similarity = 0.0
        if candidate1.industry and candidate2.industry:
            industry_similarity = 1.0 if candidate1.industry.lower() == candidate2.industry.lower() else 0.0
        
        # Weighted average
        overall_similarity = (
            skill_similarity * 0.5 +
            exp_similarity * 0.2 +
            edu_similarity * 0.2 +
            industry_similarity * 0.1
        )
        
        return overall_similarity

# Global candidate matcher instance
candidate_matcher = CandidateMatcher()

def test_candidate_matcher():
    """Test the candidate matcher functionality."""
    matcher = CandidateMatcher()
    
    # Create test job
    job = JobRequirement(
        job_id="job1",
        title="Senior Python Developer",
        required_skills=["Python", "Django", "SQL"],
        preferred_skills=["Docker", "AWS", "Redis"],
        min_experience_years=5.0,
        required_education="bachelors",
        industry="Technology",
        seniority="senior"
    )
    
    # Create test candidates
    candidate1 = CandidateProfile(
        candidate_id="cand1",
        skills=["Python", "Django", "SQL", "Docker", "AWS"],
        skill_levels={"Python": "expert", "Django": "advanced", "SQL": "advanced", "Docker": "intermediate", "AWS": "intermediate"},
        experience_years=6.0,
        education_level="masters",
        education_field="Computer Science",
        current_role="Senior Developer",
        industry="Technology"
    )
    
    candidate2 = CandidateProfile(
        candidate_id="cand2",
        skills=["Python", "Flask", "PostgreSQL"],
        skill_levels={"Python": "intermediate", "Flask": "intermediate", "PostgreSQL": "intermediate"},
        experience_years=3.0,
        education_level="bachelors",
        education_field="Software Engineering",
        current_role="Developer",
        industry="Technology"
    )
    
    # Match candidates
    score1 = matcher.match_candidate(candidate1, job)
    score2 = matcher.match_candidate(candidate2, job)
    
    print(f"Candidate 1 Score: {score1.overall_score:.2f} - {score1.recommendation}")
    print(f"Candidate 2 Score: {score2.overall_score:.2f} - {score2.recommendation}")
    
    # Rank candidates
    rankings = matcher.rank_candidates([candidate1, candidate2], job)
    print(f"\nRankings:")
    for i, score in enumerate(rankings, 1):
        print(f"{i}. Candidate {score.candidate_id}: {score.overall_score:.2f}")

if __name__ == "__main__":
    test_candidate_matcher()
