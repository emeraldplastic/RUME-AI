"""
Skill Gap Analyzer for RUME AI.
Analyzes skill gaps between candidates and job requirements with actionable recommendations.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging
from datetime import datetime
from collections import Counter

logger = logging.getLogger(__name__)

@dataclass
class SkillGap:
    """Represents a skill gap between candidate and requirements."""
    skill: str
    required_level: str
    candidate_level: str
    gap_severity: str  # critical, moderate, minor
    recommended_training: List[str]
    estimated_learning_time: str

@dataclass
class SkillGapAnalysis:
    """Comprehensive skill gap analysis result."""
    candidate_id: str
    job_id: str
    overall_fit_score: float
    skill_gaps: List[SkillGap]
    skill_matches: List[str]
    missing_critical_skills: List[str]
    training_recommendations: List[Dict[str, Any]]
    readiness_level: str  # ready, near_ready, needs_development, not_ready

class SkillGapAnalyzer:
    """Analyzer for skill gaps between candidates and job requirements."""
    
    def __init__(self):
        self.skill_levels = {
            "expert": 5,
            "advanced": 4,
            "intermediate": 3,
            "beginner": 2,
            "familiar": 1,
            "none": 0
        }
        
        self.training_resources = {
            "python": [
                "Python Crash Course (Book)",
                "Real Python (Online Course)",
                "Estimated: 4-6 weeks for intermediate level"
            ],
            "machine learning": [
                "Andrew Ng's ML Course (Coursera)",
                "Fast.ai Practical Deep Learning",
                "Estimated: 8-12 weeks"
            ],
            "sql": [
                "SQLBolt (Interactive Tutorial)",
                "Mode Analytics SQL Tutorial",
                "Estimated: 2-3 weeks"
            ],
            "docker": [
                "Docker Official Documentation",
                "Docker Mastery (Udemy)",
                "Estimated: 3-4 weeks"
            ],
            "aws": [
                "AWS Certified Cloud Practitioner",
                "AWS Training and Certification",
                "Estimated: 6-8 weeks"
            ],
            "react": [
                "React Official Documentation",
                "React Tutorial (reactjs.org)",
                "Estimated: 4-6 weeks"
            ],
            "kubernetes": [
                "Kubernetes Basics (CNCF)",
                "Kubernetes Documentation",
                "Estimated: 8-10 weeks"
            ]
        }
    
    def analyze_skill_gaps(
        self,
        candidate_skills: Dict[str, str],
        required_skills: Dict[str, str],
        preferred_skills: Optional[Dict[str, str]] = None
    ) -> SkillGapAnalysis:
        """
        Analyze skill gaps between candidate and job requirements.
        
        Args:
            candidate_skills: Dictionary of candidate skills and their levels
            required_skills: Dictionary of required skills and their levels
            preferred_skills: Optional dictionary of preferred skills and their levels
        
        Returns:
            SkillGapAnalysis with detailed gap analysis
        """
        skill_gaps = []
        skill_matches = []
        missing_critical = []
        training_recommendations = []
        
        # Analyze required skills
        for skill, required_level in required_skills.items():
            candidate_level = candidate_skills.get(skill, "none")
            
            required_score = self.skill_levels.get(required_level.lower(), 3)
            candidate_score = self.skill_levels.get(candidate_level.lower(), 0)
            
            if candidate_score >= required_score:
                skill_matches.append(skill)
            else:
                gap_score = required_score - candidate_score
                
                # Determine severity
                if gap_score >= 3:
                    severity = "critical"
                    missing_critical.append(skill)
                elif gap_score >= 2:
                    severity = "moderate"
                else:
                    severity = "minor"
                
                # Get training recommendations
                training = self.training_resources.get(skill.lower(), [
                    f"Online courses for {skill}",
                    f"Practice projects with {skill}",
                    "Estimated: 4-8 weeks"
                ])
                
                skill_gap = SkillGap(
                    skill=skill,
                    required_level=required_level,
                    candidate_level=candidate_level,
                    gap_severity=severity,
                    recommended_training=training,
                    estimated_learning_time=training[-1] if training else "Unknown"
                )
                
                skill_gaps.append(skill_gap)
                
                # Add to training recommendations
                training_recommendations.append({
                    'skill': skill,
                    'severity': severity,
                    'resources': training,
                    'priority': 'high' if severity == 'critical' else 'medium'
                })
        
        # Analyze preferred skills
        if preferred_skills:
            for skill, preferred_level in preferred_skills.items():
                candidate_level = candidate_skills.get(skill, "none")
                
                preferred_score = self.skill_levels.get(preferred_level.lower(), 3)
                candidate_score = self.skill_levels.get(candidate_level.lower(), 0)
                
                if candidate_score >= preferred_score:
                    skill_matches.append(skill)
                elif candidate_score > 0:
                    # Partial match - add as moderate gap
                    training = self.training_resources.get(skill.lower(), [
                        f"Advanced {skill} training",
                        "Estimated: 2-4 weeks"
                    ])
                    
                    skill_gap = SkillGap(
                        skill=skill,
                        required_level=preferred_level,
                        candidate_level=candidate_level,
                        gap_severity="minor",
                        recommended_training=training,
                        estimated_learning_time=training[-1] if training else "Unknown"
                    )
                    
                    skill_gaps.append(skill_gap)
        
        # Calculate overall fit score
        total_required = len(required_skills)
        matched_required = len([s for s in required_skills.keys() if s in skill_matches])
        
        base_score = matched_required / total_required if total_required > 0 else 0
        
        # Bonus for preferred skills
        if preferred_skills:
            total_preferred = len(preferred_skills)
            matched_preferred = len([s for s in preferred_skills.keys() if s in skill_matches])
            preferred_bonus = (matched_preferred / total_preferred) * 0.1 if total_preferred > 0 else 0
        else:
            preferred_bonus = 0
        
        overall_fit_score = min(1.0, base_score + preferred_bonus)
        
        # Determine readiness level
        if overall_fit_score >= 0.9:
            readiness = "ready"
        elif overall_fit_score >= 0.7:
            readiness = "near_ready"
        elif overall_fit_score >= 0.5:
            readiness = "needs_development"
        else:
            readiness = "not_ready"
        
        return SkillGapAnalysis(
            candidate_id="",  # To be set by caller
            job_id="",  # To be set by caller
            overall_fit_score=overall_fit_score,
            skill_gaps=skill_gaps,
            skill_matches=skill_matches,
            missing_critical_skills=missing_critical,
            training_recommendations=training_recommendations,
            readiness_level=readiness
        )
    
    def get_team_skill_gaps(
        self,
        team_skills: List[Dict[str, str]],
        required_skills: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Analyze skill gaps across a team.
        
        Args:
            team_skills: List of team member skill dictionaries
            required_skills: Required skills and levels
        
        Returns:
            Dictionary with team-wide skill gap analysis
        """
        team_gaps = {}
        
        for skill, required_level in required_skills.items():
            team_levels = [member.get(skill, "none") for member in team_skills]
            level_scores = [self.skill_levels.get(level.lower(), 0) for level in team_levels]
            
            avg_score = sum(level_scores) / len(level_scores) if level_scores else 0
            required_score = self.skill_levels.get(required_level.lower(), 3)
            
            if avg_score < required_score:
                team_gaps[skill] = {
                    'required_level': required_level,
                    'average_team_level': self._score_to_level(avg_score),
                    'gap_score': required_score - avg_score,
                    'members_with_skill': sum(1 for level in team_levels if level != "none"),
                    'total_members': len(team_skills)
                }
        
        return team_gaps
    
    def _score_to_level(self, score: float) -> str:
        """Convert numeric score to level string."""
        for level, level_score in self.skill_levels.items():
            if abs(score - level_score) < 0.5:
                return level
        return "beginner"
    
    def generate_development_plan(
        self,
        skill_gaps: List[SkillGap],
        time_constraint_weeks: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate a prioritized development plan based on skill gaps.
        
        Args:
            skill_gaps: List of SkillGap objects
            time_constraint_weeks: Optional time constraint in weeks
        
        Returns:
            Prioritized development plan
        """
        # Sort by severity
        critical_gaps = [g for g in skill_gaps if g.gap_severity == "critical"]
        moderate_gaps = [g for g in skill_gaps if g.gap_severity == "moderate"]
        minor_gaps = [g for g in skill_gaps if g.gap_severity == "minor"]
        
        plan = []
        week_counter = 1
        
        # Add critical gaps first
        for gap in critical_gaps:
            plan.append({
                'week': week_counter,
                'skill': gap.skill,
                'priority': 'critical',
                'training': gap.recommended_training,
                'estimated_time': gap.estimated_learning_time
            })
            week_counter += 1
        
        # Add moderate gaps
        for gap in moderate_gaps:
            plan.append({
                'week': week_counter,
                'skill': gap.skill,
                'priority': 'moderate',
                'training': gap.recommended_training,
                'estimated_time': gap.estimated_learning_time
            })
            week_counter += 1
        
        # Add minor gaps if time permits
        if time_constraint_weeks is None or week_counter <= time_constraint_weeks:
            for gap in minor_gaps:
                if time_constraint_weeks and week_counter > time_constraint_weeks:
                    break
                plan.append({
                    'week': week_counter,
                    'skill': gap.skill,
                    'priority': 'minor',
                    'training': gap.recommended_training,
                    'estimated_time': gap.estimated_learning_time
                })
                week_counter += 1
        
        return plan

# Global skill gap analyzer instance
skill_gap_analyzer = SkillGapAnalyzer()

def test_skill_gap_analyzer():
    """Test the skill gap analyzer."""
    analyzer = SkillGapAnalyzer()
    
    # Test candidate analysis
    candidate_skills = {
        'python': 'advanced',
        'sql': 'intermediate',
        'docker': 'beginner',
        'aws': 'none'
    }
    
    required_skills = {
        'python': 'intermediate',
        'sql': 'advanced',
        'docker': 'intermediate',
        'aws': 'beginner'
    }
    
    analysis = analyzer.analyze_skill_gaps(candidate_skills, required_skills)
    
    print(f"Overall Fit Score: {analysis.overall_fit_score:.2%}")
    print(f"Readiness Level: {analysis.readiness_level}")
    print(f"Skill Matches: {analysis.skill_matches}")
    print(f"Critical Gaps: {analysis.missing_critical_skills}")
    
    for gap in analysis.skill_gaps:
        print(f"\nGap: {gap.skill}")
        print(f"  Required: {gap.required_level}, Candidate: {gap.candidate_level}")
        print(f"  Severity: {gap.gap_severity}")
        print(f"  Training: {gap.recommended_training[0]}")

if __name__ == "__main__":
    test_skill_gap_analyzer()
