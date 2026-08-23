"""
Advanced Analytics Engine for RUME AI.
Provides comprehensive hiring analytics, trends analysis, and predictive insights.
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import statistics
import logging

logger = logging.getLogger(__name__)

@dataclass
class HiringMetrics:
    """Core hiring metrics."""
    total_applications: int
    total_interviews: int
    total_hires: int
    time_to_hire_days: float
    offer_acceptance_rate: float
    candidate_satisfaction_score: float
    interviewer_satisfaction_score: float

@dataclass
class SkillTrend:
    """Represents skill demand trend over time."""
    skill: str
    demand_count: int
    growth_rate: float
    avg_salary: Optional[float] = None
    time_to_fill: Optional[float] = None

@dataclass
class PipelineAnalytics:
    """Recruitment pipeline analytics."""
    stage_counts: Dict[str, int]
    conversion_rates: Dict[str, float]
    average_time_per_stage: Dict[str, float]
    bottleneck_stages: List[str]
    dropoff_points: List[Tuple[str, float]]

@dataclass
class DiversityMetrics:
    """Diversity and inclusion metrics."""
    gender_distribution: Dict[str, float]
    age_distribution: Dict[str, float]
    education_distribution: Dict[str, float]
    experience_distribution: Dict[str, float]
    industry_diversity: float
    geographic_diversity: float

@dataclass
class PredictiveInsight:
    """Predictive hiring insight."""
    insight_type: str
    confidence: float
    description: str
    actionable_recommendation: str
    impact_potential: str

class AnalyticsEngine:
    """Advanced analytics engine for hiring insights."""
    
    def __init__(self):
        self.historical_data: List[Dict[str, Any]] = []
        self.skill_demand_history: Dict[str, List[int]] = defaultdict(list)
        self.pipeline_stages = ["applied", "screened", "interviewed", "offered", "hired", "rejected"]
    
    def add_historical_data(self, data: Dict[str, Any]):
        """Add historical hiring data for analysis."""
        self.historical_data.append(data)
        
        # Track skill demand
        if "required_skills" in data:
            for skill in data["required_skills"]:
                self.skill_demand_history[skill].append(1)
        
        logger.debug(f"Added historical data point")
    
    def calculate_hiring_metrics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> HiringMetrics:
        """
        Calculate core hiring metrics for a time period.
        
        Args:
            start_date: Start of analysis period
            end_date: End of analysis period
        
        Returns:
            HiringMetrics with calculated values
        """
        filtered_data = self._filter_by_date(self.historical_data, start_date, end_date)
        
        total_applications = len(filtered_data)
        total_interviews = sum(1 for d in filtered_data if d.get("interviewed", False))
        total_hires = sum(1 for d in filtered_data if d.get("hired", False))
        
        # Time to hire calculation
        time_to_hire_values = [
            d["time_to_hire_days"] for d in filtered_data
            if "time_to_hire_days" in d and d["hired"]
        ]
        time_to_hire_days = statistics.mean(time_to_hire_values) if time_to_hire_values else 0
        
        # Offer acceptance rate
        offers_made = sum(1 for d in filtered_data if d.get("offered", False))
        offer_acceptance_rate = total_hires / offers_made if offers_made > 0 else 0
        
        # Satisfaction scores (placeholder - would come from surveys)
        candidate_satisfaction = statistics.mean([
            d.get("candidate_satisfaction", 3.5) for d in filtered_data
            if "candidate_satisfaction" in d
        ]) if filtered_data else 3.5
        
        interviewer_satisfaction = statistics.mean([
            d.get("interviewer_satisfaction", 3.5) for d in filtered_data
            if "interviewer_satisfaction" in d
        ]) if filtered_data else 3.5
        
        return HiringMetrics(
            total_applications=total_applications,
            total_interviews=total_interviews,
            total_hires=total_hires,
            time_to_hire_days=time_to_hire_days,
            offer_acceptance_rate=offer_acceptance_rate,
            candidate_satisfaction_score=candidate_satisfaction,
            interviewer_satisfaction_score=interviewer_satisfaction
        )
    
    def analyze_pipeline_health(self) -> PipelineAnalytics:
        """
        Analyze recruitment pipeline health and identify bottlenecks.
        
        Returns:
            PipelineAnalytics with pipeline insights
        """
        stage_counts = defaultdict(int)
        stage_transitions = defaultdict(int)
        stage_times = defaultdict(list)
        
        for data in self.historical_data:
            current_stage = data.get("stage", "applied")
            stage_counts[current_stage] += 1
            
            # Track transitions
            if "previous_stage" in data:
                transition = f"{data['previous_stage']}->{current_stage}"
                stage_transitions[transition] += 1
            
            # Track time in stage
            if "stage_duration_days" in data:
                stage_times[current_stage].append(data["stage_duration_days"])
        
        # Calculate conversion rates
        conversion_rates = {}
        for i in range(len(self.pipeline_stages) - 1):
            from_stage = self.pipeline_stages[i]
            to_stage = self.pipeline_stages[i + 1]
            transition = f"{from_stage}->{to_stage}"
            
            if stage_counts[from_stage] > 0:
                conversion_rates[transition] = stage_transitions.get(transition, 0) / stage_counts[from_stage]
        
        # Calculate average time per stage
        average_time_per_stage = {}
        for stage, times in stage_times.items():
            average_time_per_stage[stage] = statistics.mean(times) if times else 0
        
        # Identify bottlenecks (stages with low conversion rates)
        bottleneck_stages = []
        for transition, rate in conversion_rates.items():
            if rate < 0.5:  # Less than 50% conversion
                from_stage = transition.split("->")[0]
                bottleneck_stages.append(from_stage)
        
        # Identify dropoff points
        dropoff_points = []
        for transition, rate in conversion_rates.items():
            if rate < 1.0:
                dropoff_points.append((transition, 1.0 - rate))
        
        dropoff_points.sort(key=lambda x: x[1], reverse=True)
        
        return PipelineAnalytics(
            stage_counts=dict(stage_counts),
            conversion_rates=conversion_rates,
            average_time_per_stage=average_time_per_stage,
            bottleneck_stages=list(set(bottleneck_stages)),
            dropoff_points=dropoff_points[:5]  # Top 5 dropoff points
        )
    
    def analyze_skill_trends(
        self,
        lookback_days: int = 90
    ) -> List[SkillTrend]:
        """
        Analyze skill demand trends over time.
        
        Args:
            lookback_days: Number of days to look back for trend analysis
        
        Returns:
            List of SkillTrend objects sorted by growth rate
        """
        cutoff_date = datetime.now() - timedelta(days=lookback_days)
        
        # Calculate current demand
        current_demand = defaultdict(int)
        for data in self.historical_data:
            data_date = data.get("date", datetime.now())
            if data_date >= cutoff_date:
                for skill in data.get("required_skills", []):
                    current_demand[skill] += 1
        
        # Calculate growth rates
        trends = []
        for skill, current_count in current_demand.items():
            historical_counts = self.skill_demand_history.get(skill, [])
            
            if len(historical_counts) >= 2:
                old_count = sum(historical_counts[:-30]) if len(historical_counts) > 30 else sum(historical_counts[:-1])
                growth_rate = (current_count - old_count) / old_count if old_count > 0 else 0
            else:
                growth_rate = 0
            
            trends.append(SkillTrend(
                skill=skill,
                demand_count=current_count,
                growth_rate=growth_rate
            ))
        
        # Sort by growth rate descending
        trends.sort(key=lambda x: x.growth_rate, reverse=True)
        
        return trends
    
    def calculate_diversity_metrics(self) -> DiversityMetrics:
        """
        Calculate diversity and inclusion metrics.
        
        Returns:
            DiversityMetrics with diversity statistics
        """
        gender_data = [d.get("gender", "unknown") for d in self.historical_data]
        age_data = [d.get("age", "unknown") for d in self.historical_data]
        education_data = [d.get("education_level", "unknown") for d in self.historical_data]
        experience_data = [d.get("experience_years", 0) for d in self.historical_data]
        industry_data = [d.get("industry", "unknown") for d in self.historical_data]
        location_data = [d.get("location", "unknown") for d in self.historical_data]
        
        # Calculate distributions
        gender_dist = self._calculate_distribution(gender_data)
        age_dist = self._calculate_age_distribution(age_data)
        education_dist = self._calculate_distribution(education_data)
        experience_dist = self._calculate_experience_distribution(experience_data)
        
        # Calculate diversity indices
        industry_diversity = self._calculate_simpson_diversity_index(industry_data)
        geographic_diversity = self._calculate_simpson_diversity_index(location_data)
        
        return DiversityMetrics(
            gender_distribution=gender_dist,
            age_distribution=age_dist,
            education_distribution=education_dist,
            experience_distribution=experience_dist,
            industry_diversity=industry_diversity,
            geographic_diversity=geographic_diversity
        )
    
    def generate_predictive_insights(self) -> List[PredictiveInsight]:
        """
        Generate predictive insights and recommendations.
        
        Returns:
            List of PredictiveInsight objects
        """
        insights = []
        
        # Analyze hiring velocity
        recent_metrics = self.calculate_hiring_metrics(
            start_date=datetime.now() - timedelta(days=30)
        )
        
        if recent_metrics.time_to_hire_days > 45:
            insights.append(PredictiveInsight(
                insight_type="hiring_velocity",
                confidence=0.8,
                description="Time to hire is above industry average (45+ days)",
                actionable_recommendation="Consider streamlining interview process or increasing interviewer capacity",
                impact_potential="high"
            ))
        
        # Analyze offer acceptance rate
        if recent_metrics.offer_acceptance_rate < 0.7:
            insights.append(PredictiveInsight(
                insight_type="offer_acceptance",
                confidence=0.75,
                description="Offer acceptance rate is below 70%",
                actionable_recommendation="Review compensation packages and improve candidate communication during offer stage",
                impact_potential="medium"
            ))
        
        # Analyze pipeline bottlenecks
        pipeline = self.analyze_pipeline_health()
        if pipeline.bottleneck_stages:
            insights.append(PredictiveInsight(
                insight_type="pipeline_bottleneck",
                confidence=0.85,
                description=f"Bottlenecks detected at stages: {', '.join(pipeline.bottleneck_stages)}",
                actionable_recommendation=f"Focus resources on improving {pipeline.bottleneck_stages[0]} stage processes",
                impact_potential="high"
            ))
        
        # Analyze skill trends
        skill_trends = self.analyze_skill_trends()
        emerging_skills = [t for t in skill_trends if t.growth_rate > 0.5]
        
        if emerging_skills:
            insights.append(PredictiveInsight(
                insight_type="emerging_skills",
                confidence=0.7,
                description=f"Emerging skills detected: {', '.join([s.skill for s in emerging_skills[:3]])}",
                actionable_recommendation="Update job requirements and training programs to include emerging skills",
                impact_potential="medium"
            ))
        
        # Analyze diversity
        diversity = self.calculate_diversity_metrics()
        if diversity.industry_diversity < 0.5:
            insights.append(PredictiveInsight(
                insight_type="diversity_improvement",
                confidence=0.65,
                description="Industry diversity index is below 0.5",
                actionable_recommendation="Expand sourcing channels to include more diverse industries",
                impact_potential="medium"
            ))
        
        return insights
    
    def _filter_by_date(
        self,
        data: List[Dict[str, Any]],
        start_date: Optional[datetime],
        end_date: Optional[datetime]
    ) -> List[Dict[str, Any]]:
        """Filter data by date range."""
        if not start_date and not end_date:
            return data
        
        filtered = []
        for item in data:
            item_date = item.get("date", datetime.now())
            
            if start_date and item_date < start_date:
                continue
            if end_date and item_date > end_date:
                continue
            
            filtered.append(item)
        
        return filtered
    
    def _calculate_distribution(self, data: List[str]) -> Dict[str, float]:
        """Calculate percentage distribution of categorical data."""
        if not data:
            return {}
        
        counts = Counter(data)
        total = len(data)
        
        return {key: count / total for key, count in counts.items()}
    
    def _calculate_age_distribution(self, ages: List[Any]) -> Dict[str, float]:
        """Calculate age group distribution."""
        age_groups = defaultdict(int)
        
        for age in ages:
            if isinstance(age, (int, float)):
                if age < 25:
                    age_groups["18-24"] += 1
                elif age < 35:
                    age_groups["25-34"] += 1
                elif age < 45:
                    age_groups["35-44"] += 1
                elif age < 55:
                    age_groups["45-54"] += 1
                else:
                    age_groups["55+"] += 1
            else:
                age_groups["unknown"] += 1
        
        total = sum(age_groups.values())
        return {key: count / total for key, count in age_groups.items()} if total > 0 else {}
    
    def _calculate_experience_distribution(self, experiences: List[float]) -> Dict[str, float]:
        """Calculate experience level distribution."""
        exp_groups = defaultdict(int)
        
        for exp in experiences:
            if exp < 1:
                exp_groups["0-1 years"] += 1
            elif exp < 3:
                exp_groups["1-3 years"] += 1
            elif exp < 5:
                exp_groups["3-5 years"] += 1
            elif exp < 10:
                exp_groups["5-10 years"] += 1
            else:
                exp_groups["10+ years"] += 1
        
        total = sum(exp_groups.values())
        return {key: count / total for key, count in exp_groups.items()} if total > 0 else {}
    
    def _calculate_simpson_diversity_index(self, data: List[str]) -> float:
        """Calculate Simpson's Diversity Index."""
        if not data:
            return 0.0
        
        counts = Counter(data)
        total = len(data)
        
        if total == 0:
            return 0.0
        
        # Simpson's Index: D = Σ(n_i/N)²
        simpson_index = sum((count / total) ** 2 for count in counts.values())
        
        # Simpson's Diversity Index: 1 - D
        diversity_index = 1 - simpson_index
        
        return diversity_index
    
    def generate_analytics_report(self) -> str:
        """
        Generate comprehensive analytics report.
        
        Returns:
            Formatted report string
        """
        report = []
        report.append("=" * 80)
        report.append("RUME AI - HIRING ANALYTICS REPORT")
        report.append("=" * 80)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Data Points Analyzed: {len(self.historical_data)}")
        report.append("")
        
        # Core Metrics
        report.append("CORE HIRING METRICS")
        report.append("-" * 40)
        metrics = self.calculate_hiring_metrics()
        report.append(f"Total Applications: {metrics.total_applications}")
        report.append(f"Total Interviews: {metrics.total_interviews}")
        report.append(f"Total Hires: {metrics.total_hires}")
        report.append(f"Time to Hire: {metrics.time_to_hire_days:.1f} days")
        report.append(f"Offer Acceptance Rate: {metrics.offer_acceptance_rate:.1%}")
        report.append(f"Candidate Satisfaction: {metrics.candidate_satisfaction_score:.1f}/5.0")
        report.append(f"Interviewer Satisfaction: {metrics.interviewer_satisfaction_score:.1f}/5.0")
        report.append("")
        
        # Pipeline Health
        report.append("PIPELINE HEALTH")
        report.append("-" * 40)
        pipeline = self.analyze_pipeline_health()
        report.append(f"Stage Counts: {pipeline.stage_counts}")
        report.append(f"Bottleneck Stages: {', '.join(pipeline.bottleneck_stages) if pipeline.bottleneck_stages else 'None'}")
        report.append("")
        
        # Skill Trends
        report.append("TOP EMERGING SKILLS")
        report.append("-" * 40)
        trends = self.analyze_skill_trends()[:5]
        for trend in trends:
            report.append(f"{trend.skill}: {trend.growth_rate:.1%} growth ({trend.demand_count} mentions)")
        report.append("")
        
        # Predictive Insights
        report.append("PREDICTIVE INSIGHTS")
        report.append("-" * 40)
        insights = self.generate_predictive_insights()
        for insight in insights:
            report.append(f"[{insight.insight_type.upper()}] {insight.description}")
            report.append(f"Recommendation: {insight.actionable_recommendation}")
            report.append(f"Impact: {insight.impact_potential} (Confidence: {insight.confidence:.0%})")
            report.append("")
        
        report.append("=" * 80)
        report.append("END OF REPORT")
        report.append("=" * 80)
        
        return "\n".join(report)

# Global analytics engine instance
analytics_engine = AnalyticsEngine()

def test_analytics_engine():
    """Test the analytics engine functionality."""
    engine = AnalyticsEngine()
    
    # Add some test data
    test_data = [
        {
            "date": datetime.now() - timedelta(days=10),
            "stage": "hired",
            "interviewed": True,
            "hired": True,
            "offered": True,
            "time_to_hire_days": 35,
            "candidate_satisfaction": 4.2,
            "interviewer_satisfaction": 4.5,
            "required_skills": ["Python", "Django", "SQL"],
            "gender": "female",
            "age": 28,
            "education_level": "masters",
            "experience_years": 5,
            "industry": "Technology",
            "location": "San Francisco"
        },
        {
            "date": datetime.now() - timedelta(days=5),
            "stage": "interviewed",
            "interviewed": True,
            "hired": False,
            "offered": False,
            "required_skills": ["Python", "React", "AWS"],
            "gender": "male",
            "age": 32,
            "education_level": "bachelors",
            "experience_years": 7,
            "industry": "Technology",
            "location": "New York"
        }
    ]
    
    for data in test_data:
        engine.add_historical_data(data)
    
    # Generate report
    report = engine.generate_analytics_report()
    print(report)

if __name__ == "__main__":
    test_analytics_engine()
