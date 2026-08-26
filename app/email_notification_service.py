"""
Email Notification Service for RUME AI.
Handles sending emails for interview invitations, updates, and candidate communications.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

class EmailTemplate(Enum):
    """Email template types."""
    INTERVIEW_INVITATION = "interview_invitation"
    INTERVIEW_REMINDER = "interview_reminder"
    INTERVIEW_RESCHEDULED = "interview_rescheduled"
    INTERVIEW_CANCELLED = "interview_cancelled"
    CANDIDATE_REJECTED = "candidate_rejected"
    CANDIDATE_HIRED = "candidate_hired"
    APPLICATION_RECEIVED = "application_received"
    FEEDBACK_REQUEST = "feedback_request"

@dataclass
class EmailConfig:
    """Configuration for email service."""
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    from_email: str = "noreply@rumeai.com"
    from_name: str = "RUME AI"
    use_tls: bool = True
    enable_tracking: bool = True

@dataclass
class EmailMessage:
    """Represents an email message."""
    to_email: str
    to_name: str
    subject: str
    html_body: str
    text_body: str
    template: EmailTemplate
    metadata: Dict[str, Any]
    sent: bool = False
    sent_at: Optional[datetime] = None
    error_message: Optional[str] = None

class EmailNotificationService:
    """Service for sending email notifications."""
    
    def __init__(self, config: Optional[EmailConfig] = None):
        self.config = config or EmailConfig()
        self.email_queue: List[EmailMessage] = []
        self.sent_emails: List[EmailMessage] = []
        self.email_templates = self._initialize_templates()
    
    def _initialize_templates(self) -> Dict[EmailTemplate, Dict[str, str]]:
        """Initialize email templates."""
        return {
            EmailTemplate.INTERVIEW_INVITATION: {
                'subject': 'Interview Invitation - {company_name}',
                'html': '''
                    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                        <h2 style="color: #333;">Interview Invitation</h2>
                        <p>Dear {candidate_name},</p>
                        <p>We are pleased to invite you for an interview for the <strong>{job_title}</strong> position at <strong>{company_name}</strong>.</p>
                        <div style="background: #f5f5f5; padding: 20px; margin: 20px 0; border-radius: 5px;">
                            <p><strong>Date:</strong> {interview_date}</p>
                            <p><strong>Time:</strong> {interview_time}</p>
                            <p><strong>Interviewer:</strong> {interviewer_name}</p>
                            <p><strong>Type:</strong> {interview_type}</p>
                        </div>
                        <p>Please confirm your attendance by clicking the link below:</p>
                        <p><a href="{confirmation_link}" style="background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Confirm Attendance</a></p>
                        <p>If you have any questions, please don't hesitate to contact us.</p>
                        <p>Best regards,<br>{company_name} Team</p>
                    </div>
                ''',
                'text': '''
                    Interview Invitation
                    
                    Dear {candidate_name},
                    
                    We are pleased to invite you for an interview for the {job_title} position at {company_name}.
                    
                    Date: {interview_date}
                    Time: {interview_time}
                    Interviewer: {interviewer_name}
                    Type: {interview_type}
                    
                    Please confirm your attendance: {confirmation_link}
                    
                    Best regards,
                    {company_name} Team
                '''
            },
            EmailTemplate.INTERVIEW_REMINDER: {
                'subject': 'Interview Reminder - {company_name}',
                'html': '''
                    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto="">
                        <h2 style="color: #333;">Interview Reminder</h2>
                        <p>Dear {candidate_name},</p>
                        <p>This is a friendly reminder about your upcoming interview for the <strong>{job_title}</strong> position.</p>
                        <div style="background: #f5f5f5; padding: 20px; margin: 20px 0; border-radius: 5px;">
                            <p><strong>Date:</strong> {interview_date}</p>
                            <p><strong>Time:</strong> {interview_time}</p>
                            <p><strong>Interviewer:</strong> {interviewer_name}</p>
                        </div>
                        <p>We look forward to speaking with you!</p>
                        <p>Best regards,<br>{company_name} Team</p>
                    </div>
                ''',
                'text': '''
                    Interview Reminder
                    
                    Dear {candidate_name},
                    
                    This is a friendly reminder about your upcoming interview for the {job_title} position.
                    
                    Date: {interview_date}
                    Time: {interview_time}
                    Interviewer: {interviewer_name}
                    
                    We look forward to speaking with you!
                    
                    Best regards,
                    {company_name} Team
                '''
            },
            EmailTemplate.CANDIDATE_HIRED: {
                'subject': 'Congratulations! - {company_name}',
                'html': '''
                    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                        <h2 style="color: #28a745;">Congratulations!</h2>
                        <p>Dear {candidate_name},</p>
                        <p>We are thrilled to offer you the position of <strong>{job_title}</strong> at <strong>{company_name}</strong>!</p>
                        <p>Your skills and experience impressed us, and we believe you will be a valuable addition to our team.</p>
                        <div style="background: #e8f5e9; padding: 20px; margin: 20px 0; border-radius: 5px;">
                            <p><strong>Position:</strong> {job_title}</p>
                            <p><strong>Start Date:</strong> {start_date}</p>
                            <p><strong>Salary:</strong> {salary}</p>
                        </div>
                        <p>Please review the attached offer letter and let us know if you have any questions.</p>
                        <p>Congratulations again!<br>{company_name} Team</p>
                    </div>
                ''',
                'text': '''
                    Congratulations!
                    
                    Dear {candidate_name},
                    
                    We are thrilled to offer you the position of {job_title} at {company_name}!
                    
                    Your skills and experience impressed us, and we believe you will be a valuable addition to our team.
                    
                    Position: {job_title}
                    Start Date: {start_date}
                    Salary: {salary}
                    
                    Please review the attached offer letter and let us know if you have any questions.
                    
                    Congratulations again!
                    {company_name} Team
                '''
            },
            EmailTemplate.APPLICATION_RECEIVED: {
                'subject': 'Application Received - {company_name}',
                'html': '''
                    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                        <h2 style="color: #333;">Application Received</h2>
                        <p>Dear {candidate_name},</p>
                        <p>Thank you for your interest in the <strong>{job_title}</strong> position at <strong>{company_name}</strong>.</p>
                        <p>We have received your application and our team will review it shortly. We will get back to you within {response_time}.</p>
                        <p>If you have any questions in the meantime, feel free to reach out.</p>
                        <p>Best regards,<br>{company_name} Team</p>
                    </div>
                ''',
                'text': '''
                    Application Received
                    
                    Dear {candidate_name},
                    
                    Thank you for your interest in the {job_title} position at {company_name}.
                    
                    We have received your application and our team will review it shortly. We will get back to you within {response_time}.
                    
                    If you have any questions in the meantime, feel free to reach out.
                    
                    Best regards,
                    {company_name} Team
                '''
            }
        }
    
    def send_email(
        self,
        template: EmailTemplate,
        to_email: str,
        to_name: str,
        template_vars: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> EmailMessage:
        """
        Send an email using a template.
        
        Args:
            template: Email template to use
            to_email: Recipient email address
            to_name: Recipient name
            template_vars: Variables to substitute in template
            metadata: Additional metadata for tracking
        
        Returns:
            EmailMessage object
        """
        if template not in self.email_templates:
            logger.error(f"Template not found: {template}")
            raise ValueError(f"Template not found: {template}")
        
        template_data = self.email_templates[template]
        
        # Substitute variables
        subject = template_data['subject'].format(**template_vars)
        html_body = template_data['html'].format(**template_vars)
        text_body = template_data['text'].format(**template_vars)
        
        # Create email message
        message = EmailMessage(
            to_email=to_email,
            to_name=to_name,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
            template=template,
            metadata=metadata or {}
        )
        
        # In production, this would actually send the email via SMTP
        # For now, we'll simulate sending
        try:
            self._send_via_smtp(message)
            message.sent = True
            message.sent_at = datetime.now()
            self.sent_emails.append(message)
            logger.info(f"Email sent to {to_email} using template {template.value}")
        except Exception as e:
            message.error_message = str(e)
            logger.error(f"Failed to send email to {to_email}: {e}")
        
        return message
    
    def _send_via_smtp(self, message: EmailMessage):
        """
        Send email via SMTP (simulated for now).
        
        Args:
            message: EmailMessage to send
        """
        # In production, this would use smtplib to actually send the email
        # For now, we'll just log it
        logger.info(f"SMTP Send: To={message.to_email}, Subject={message.subject}")
        
        # Example production code (commented out):
        # import smtplib
        # from email.mime.multipart import MIMEMultipart
        # from email.mime.text import MIMEText
        # 
        # msg = MIMEMultipart('alternative')
        # msg['Subject'] = message.subject
        # msg['From'] = f"{self.config.from_name} <{self.config.from_email}>"
        # msg['To'] = f"{message.to_name} <{message.to_email}>"
        # 
        # msg.attach(MIMEText(message.text_body, 'plain'))
        # msg.attach(MIMEText(message.html_body, 'html'))
        # 
        # with smtplib.SMTP(self.config.smtp_server, self.config.smtp_port) as server:
        #     if self.config.use_tls:
        #         server.starttls()
        #     server.login(self.config.smtp_username, self.config.smtp_password)
        #     server.send_message(msg)
    
    def send_bulk_emails(
        self,
        template: EmailTemplate,
        recipients: List[Dict[str, Any]],
        template_vars: Dict[str, Any]
    ) -> List[EmailMessage]:
        """
        Send bulk emails to multiple recipients.
        
        Args:
            template: Email template to use
            recipients: List of recipient dictionaries with 'email' and 'name'
            template_vars: Base template variables
        
        Returns:
            List of EmailMessage objects
        """
        messages = []
        
        for recipient in recipients:
            # Merge base vars with recipient-specific vars
            vars_copy = template_vars.copy()
            vars_copy.update(recipient.get('vars', {}))
            
            message = self.send_email(
                template=template,
                to_email=recipient['email'],
                to_name=recipient['name'],
                template_vars=vars_copy,
                metadata={'bulk_send': True, 'recipient_id': recipient.get('id')}
            )
            
            messages.append(message)
        
        return messages
    
    def get_email_statistics(self) -> Dict[str, Any]:
        """Get email sending statistics."""
        total_sent = len(self.sent_emails)
        total_queued = len(self.email_queue)
        
        # Count by template
        by_template = {}
        for email in self.sent_emails:
            template_name = email.template.value
            by_template[template_name] = by_template.get(template_name, 0) + 1
        
        # Count errors
        errors = sum(1 for email in self.sent_emails if email.error_message)
        
        return {
            'total_sent': total_sent,
            'total_queued': total_queued,
            'by_template': by_template,
            'error_count': errors,
            'success_rate': (total_sent - errors) / total_sent if total_sent > 0 else 0
        }
    
    def add_custom_template(
        self,
        template: EmailTemplate,
        subject: str,
        html_body: str,
        text_body: str
    ):
        """
        Add or update a custom email template.
        
        Args:
            template: Template type
            subject: Email subject
            html_body: HTML body content
            text_body: Plain text body content
        """
        self.email_templates[template] = {
            'subject': subject,
            'html': html_body,
            'text': text_body
        }
        
        logger.info(f"Added custom template: {template.value}")

# Global email notification service instance
email_notification_service = EmailNotificationService()

def test_email_service():
    """Test the email notification service."""
    service = EmailNotificationService()
    
    # Test interview invitation
    template_vars = {
        'candidate_name': 'John Doe',
        'job_title': 'Senior Developer',
        'company_name': 'Tech Corp',
        'interview_date': '2024-02-15',
        'interview_time': '10:00 AM',
        'interviewer_name': 'Jane Smith',
        'interview_type': 'Technical Interview',
        'confirmation_link': 'https://rumeai.com/confirm/123'
    }
    
    message = service.send_email(
        template=EmailTemplate.INTERVIEW_INVITATION,
        to_email='john@example.com',
        to_name='John Doe',
        template_vars=template_vars
    )
    
    print(f"Email sent: {message.sent}")
    print(f"Subject: {message.subject}")
    
    # Get statistics
    stats = service.get_email_statistics()
    print(f"Email statistics: {stats}")

if __name__ == "__main__":
    test_email_service()
