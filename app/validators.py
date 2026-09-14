"""
Data Validators for RUME AI.
Simple validation utilities for resume and candidate data.
"""

import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class ValidationResult:
    """Result of a validation check."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]

class DataValidators:
    """Collection of data validation utilities."""
    
    @staticmethod
    def validate_email(email: str) -> ValidationResult:
        """Validate email address format."""
        errors = []
        warnings = []
        
        if not email:
            errors.append("Email is required")
            return ValidationResult(False, errors, warnings)
        
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not re.match(email_pattern, email):
            errors.append("Invalid email format")
        
        return ValidationResult(len(errors) == 0, errors, warnings)
    
    @staticmethod
    def validate_phone(phone: str) -> ValidationResult:
        """Validate phone number format."""
        errors = []
        warnings = []
        
        if not phone:
            warnings.append("Phone number not provided")
            return ValidationResult(True, errors, warnings)
        
        # Remove common separators
        clean_phone = re.sub(r'[\s\-\(\)\.]', '', phone)
        
        if not clean_phone.isdigit() or len(clean_phone) < 10:
            errors.append("Invalid phone number format")
        
        return ValidationResult(len(errors) == 0, errors, warnings)
    
    @staticmethod
    def validate_url(url: str) -> ValidationResult:
        """Validate URL format."""
        errors = []
        warnings = []
        
        if not url:
            return ValidationResult(True, errors, warnings)
        
        url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        
        if not re.match(url_pattern, url):
            errors.append("Invalid URL format")
        
        return ValidationResult(len(errors) == 0, errors, warnings)
    
    @staticmethod
    def validate_years_experience(years: Any) -> ValidationResult:
        """Validate years of experience."""
        errors = []
        warnings = []
        
        try:
            exp = float(years)
            
            if exp < 0:
                errors.append("Years of experience cannot be negative")
            
            if exp > 50:
                warnings.append("Years of experience seems unusually high")
            
        except (ValueError, TypeError):
            errors.append("Years of experience must be a number")
        
        return ValidationResult(len(errors) == 0, errors, warnings)
    
    @staticmethod
    def validate_candidate_data(candidate: Dict[str, Any]) -> ValidationResult:
        """Validate complete candidate data."""
        errors = []
        warnings = []
        
        # Required fields
        if not candidate.get('name'):
            errors.append("Candidate name is required")
        
        if not candidate.get('email'):
            errors.append("Candidate email is required")
        else:
            email_result = DataValidators.validate_email(candidate['email'])
            errors.extend(email_result.errors)
            warnings.extend(email_result.warnings)
        
        # Optional validations
        if candidate.get('phone'):
            phone_result = DataValidators.validate_phone(candidate['phone'])
            errors.extend(phone_result.errors)
            warnings.extend(phone_result.warnings)
        
        if candidate.get('linkedin'):
            linkedin_result = DataValidators.validate_url(candidate['linkedin'])
            errors.extend(linkedin_result.errors)
            warnings.extend(linkin_result.warnings)
        
        if candidate.get('experience_years'):
            exp_result = DataValidators.validate_years_experience(candidate['experience_years'])
            errors.extend(exp_result.errors)
            warnings.extend(exp_result.warnings)
        
        return ValidationResult(len(errors) == 0, errors, warnings)
    
    @staticmethod
    def validate_resume_text(text: str) -> ValidationResult:
        """Validate resume text content."""
        errors = []
        warnings = []
        
        if not text or len(text.strip()) < 50:
            errors.append("Resume text is too short")
        
        if len(text) > 100000:
            warnings.append("Resume text is very long, consider summarizing")
        
        # Check for common sections
        common_sections = ['experience', 'education', 'skills', 'summary']
        text_lower = text.lower()
        
        found_sections = [section for section in common_sections if section in text_lower]
        
        if len(found_sections) < 2:
            warnings.append("Resume may be missing common sections")
        
        return ValidationResult(len(errors) == 0, errors, warnings)

def test_validators():
    """Test the validators."""
    validators = DataValidators()
    
    # Test email validation
    email_result = validators.validate_email("test@example.com")
    print(f"Email validation: {email_result.is_valid}")
    
    # Test phone validation
    phone_result = validators.validate_phone("+1-555-123-4567")
    print(f"Phone validation: {phone_result.is_valid}")
    
    # Test candidate data validation
    candidate = {
        'name': 'John Doe',
        'email': 'john@example.com',
        'phone': '555-123-4567',
        'experience_years': 5
    }
    
    candidate_result = validators.validate_candidate_data(candidate)
    print(f"Candidate validation: {candidate_result.is_valid}")
    print(f"Errors: {candidate_result.errors}")
    print(f"Warnings: {candidate_result.warnings}")

if __name__ == "__main__":
    test_validators()
