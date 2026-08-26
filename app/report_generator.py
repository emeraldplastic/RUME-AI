"""
Report Generator for RUME AI.
Generates comprehensive hiring reports in various formats.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging
from datetime import datetime, timedelta
from enum import Enum
import json

logger = logging.getLogger(__name__)

class ReportFormat(Enum):
    """Report output formats."""
    PDF = "pdf"
    HTML = "html"
    CSV = "csv"
    JSON = "json"
    EXCEL = "excel"

class ReportType(Enum):
    """Types of reports."""
    HIRING_SUMMARY = "hiring_summary"
    CANDIDATE_REPORT = "candidate_report"
    PIPELINE_ANALYSIS = "pipeline_analysis"
    DIVERSITY_REPORT = "diversity_report"
    TIME_TO_HIRE = "time_to_hire"
    COST_PER_HIRE = "cost_per_hire"

@dataclass
class ReportConfig:
    """Configuration for report generation."""
    include_charts: bool = True
    include_raw_data: bool = False
    date_range_days: int = 30
    group_by: Optional[str] = None  # department, team, role
    comparison_period: bool = True

@dataclass
class GeneratedReport:
    """Represents a generated report."""
    report_id: str
    report_type: ReportType
    format: ReportFormat
    generated_at: datetime
    data: Dict[str, Any]
    file_path: Optional[str]
    metadata: Dict[str, Any]

class ReportGenerator:
    """Service for generating hiring reports."""
    
    def __init__(self):
        self.report_history: List[GeneratedReport] = []
        self.report_counter = 0
    
    def generate_report(
        self,
        report_type: ReportType,
        data: Dict[str, Any],
        format: ReportFormat = ReportFormat.PDF,
        config: Optional[ReportConfig] = None
    ) -> GeneratedReport:
        """
        Generate a report in the specified format.
        
        Args:
            report_type: Type of report to generate
            data: Report data
            format: Output format
            config: Report configuration
        
        Returns:
            GeneratedReport object
        """
        self.report_counter += 1
        report_id = f"rpt_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{self.report_counter}"
        
        report_config = config or ReportConfig()
        
        # Process data based on report type
        processed_data = self._process_report_data(report_type, data, report_config)
        
        # Generate report content
        report_content = self._generate_report_content(
            report_type, processed_data, format, report_config
        )
        
        # Create report object
        report = GeneratedReport(
            report_id=report_id,
            report_type=report_type,
            format=format,
            generated_at=datetime.now(),
            data=processed_data,
            file_path=None,  # Would be set if saving to file
            metadata={
                'config': {
                    'include_charts': report_config.include_charts,
                    'date_range_days': report_config.date_range_days
                }
            }
        )
        
        self.report_history.append(report)
        logger.info(f"Generated report {report_id} of type {report_type.value}")
        
        return report
    
    def _process_report_data(
        self,
        report_type: ReportType,
        data: Dict[str, Any],
        config: ReportConfig
    ) -> Dict[str, Any]:
        """Process data based on report type."""
        processed = data.copy()
        
        # Add metadata
        processed['generated_at'] = datetime.now().isoformat()
        processed['report_type'] = report_type.value
        
        # Calculate summary statistics
        if 'candidates' in processed:
            processed['summary'] = self._calculate_summary_statistics(
                processed['candidates']
            )
        
        # Add comparison data if enabled
        if config.comparison_period:
            processed['comparison'] = self._calculate_comparison_data(
                data, config.date_range_days
            )
        
        return processed
    
    def _calculate_summary_statistics(
        self,
        candidates: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate summary statistics from candidate data."""
        if not candidates:
            return {}
        
        total = len(candidates)
        hired = sum(1 for c in candidates if c.get('status') == 'hired')
        rejected = sum(1 for c in candidates if c.get('status') == 'rejected')
        interviewed = sum(1 for c in candidates if c.get('interviewed', False))
        
        return {
            'total_candidates': total,
            'hired': hired,
            'rejected': rejected,
            'interviewed': interviewed,
            'hire_rate': hired / total if total > 0 else 0,
            'rejection_rate': rejected / total if total > 0 else 0
        }
    
    def _calculate_comparison_data(
        self,
        data: Dict[str, Any],
        current_period_days: int
    ) -> Dict[str, Any]:
        """Calculate comparison with previous period."""
        # In production, this would query historical data
        # For now, return placeholder
        return {
            'previous_period_days': current_period_days,
            'change_percentage': 0,
            'trend': 'stable'
        }
    
    def _generate_report_content(
        self,
        report_type: ReportType,
        data: Dict[str, Any],
        format: ReportFormat,
        config: ReportConfig
    ) -> str:
        """Generate report content in specified format."""
        if format == ReportFormat.JSON:
            return json.dumps(data, indent=2)
        
        elif format == ReportFormat.HTML:
            return self._generate_html_report(report_type, data, config)
        
        elif format == ReportFormat.CSV:
            return self._generate_csv_report(data)
        
        else:
            # For PDF and Excel, return placeholder
            return f"Report content for {report_type.value} in {format.value}"
    
    def _generate_html_report(
        self,
        report_type: ReportType,
        data: Dict[str, Any],
        config: ReportConfig
    ) -> str:
        """Generate HTML report."""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{report_type.value.replace('_', ' ').title()} Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .header {{ background: #f5f5f5; padding: 20px; border-radius: 5px; }}
                .summary {{ margin: 20px 0; }}
                .stat {{ display: inline-block; margin: 10px; padding: 15px; background: #e9ecef; border-radius: 5px; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background: #007bff; color: white; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{report_type.value.replace('_', ' ').title()}</h1>
                <p>Generated: {data.get('generated_at', 'N/A')}</p>
            </div>
        """
        
        # Add summary statistics if available
        if 'summary' in data:
            summary = data['summary']
            html += """
            <div class="summary">
                <h2>Summary Statistics</h2>
            """
            for key, value in summary.items():
                if isinstance(value, float):
                    value = f"{value:.1%}"
                html += f'<div class="stat"><strong>{key.replace("_", " ").title()}:</strong> {value}</div>'
            html += "</div>"
        
        # Add candidate table if available
        if 'candidates' in data and config.include_raw_data:
            html += """
            <h2>Candidate Details</h2>
            <table>
                <tr>
                    <th>Name</th>
                    <th>Status</th>
                    <th>Score</th>
                    <th>Applied Date</th>
                </tr>
            """
            for candidate in data['candidates'][:20]:  # Limit to 20 for display
                html += f"""
                <tr>
                    <td>{candidate.get('name', 'N/A')}</td>
                    <td>{candidate.get('status', 'N/A')}</td>
                    <td>{candidate.get('score', 'N/A')}</td>
                    <td>{candidate.get('applied_date', 'N/A')}</td>
                </tr>
                """
            html += "</table>"
        
        html += """
        </body>
        </html>
        """
        
        return html
    
    def _generate_csv_report(self, data: Dict[str, Any]) -> str:
        """Generate CSV report."""
        import io
        import csv
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        if 'candidates' in data:
            writer.writerow(['Name', 'Status', 'Score', 'Applied Date'])
            
            for candidate in data['candidates']:
                writer.writerow([
                    candidate.get('name', ''),
                    candidate.get('status', ''),
                    candidate.get('score', ''),
                    candidate.get('applied_date', '')
                ])
        
        return output.getvalue()
    
    def get_report_history(
        self,
        report_type: Optional[ReportType] = None,
        limit: int = 50
    ) -> List[GeneratedReport]:
        """
        Get report generation history.
        
        Args:
            report_type: Filter by report type
            limit: Maximum number of reports to return
        
        Returns:
            List of GeneratedReport objects
        """
        filtered = self.report_history
        
        if report_type:
            filtered = [r for r in filtered if r.report_type == report_type]
        
        # Sort by generation time descending
        filtered.sort(key=lambda x: x.generated_at, reverse=True)
        
        return filtered[:limit]
    
    def schedule_report(
        self,
        report_type: ReportType,
        schedule: str,  # cron-like schedule
        recipients: List[str],
        config: Optional[ReportConfig] = None
    ) -> str:
        """
        Schedule a report to be generated periodically.
        
        Args:
            report_type: Type of report to schedule
            schedule: Schedule string (e.g., "daily", "weekly")
            recipients: Email addresses to send report to
            config: Report configuration
        
        Returns:
            Schedule ID
        """
        schedule_id = f"schd_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # In production, this would integrate with a task scheduler
        logger.info(f"Scheduled report {schedule_id} for {report_type.value} with schedule {schedule}")
        
        return schedule_id

# Global report generator instance
report_generator = ReportGenerator()

def test_report_generator():
    """Test the report generator."""
    generator = ReportGenerator()
    
    # Mock data
    data = {
        'candidates': [
            {'name': 'John Doe', 'status': 'hired', 'score': 85, 'applied_date': '2024-01-15'},
            {'name': 'Jane Smith', 'status': 'rejected', 'score': 45, 'applied_date': '2024-01-16'},
            {'name': 'Bob Johnson', 'status': 'interviewed', 'score': 72, 'applied_date': '2024-01-17'}
        ]
    }
    
    # Generate HTML report
    report = generator.generate_report(
        report_type=ReportType.HIRING_SUMMARY,
        data=data,
        format=ReportFormat.HTML
    )
    
    print(f"Generated report: {report.report_id}")
    print(f"Report type: {report.report_type.value}")
    
    # Get report history
    history = generator.get_report_history()
    print(f"Report history: {len(history)} reports")

if __name__ == "__main__":
    test_report_generator()
