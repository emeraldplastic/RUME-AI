"""
Text Utilities for RUME AI.
Simple text processing utilities for resume and candidate data.
"""

import re
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class TextUtils:
    """Collection of text processing utilities."""
    
    @staticmethod
    def clean_text(text: str) -> str:
        """Clean and normalize text."""
        if not text:
            return ""
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s\.\,\-\@]', '', text)
        
        # Strip leading/trailing whitespace
        text = text.strip()
        
        return text
    
    @staticmethod
    def extract_emails(text: str) -> List[str]:
        """Extract email addresses from text."""
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        return re.findall(email_pattern, text)
    
    @staticmethod
    def extract_phone_numbers(text: str) -> List[str]:
        """Extract phone numbers from text."""
        # Match various phone number formats
        phone_pattern = r'(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}'
        return re.findall(phone_pattern, text)
    
    @staticmethod
    def extract_skills(text: str, skill_keywords: List[str]) -> Dict[str, int]:
        """Extract and count skills from text based on keyword list."""
        text_lower = text.lower()
        skill_counts = {}
        
        for skill in skill_keywords:
            skill_lower = skill.lower()
            count = text_lower.count(skill_lower)
            if count > 0:
                skill_counts[skill] = count
        
        return skill_counts
    
    @staticmethod
    def truncate_text(text: str, max_length: int = 500, suffix: str = "...") -> str:
        """Truncate text to maximum length with suffix."""
        if len(text) <= max_length:
            return text
        
        return text[:max_length - len(suffix)] + suffix
    
    @staticmethod
    def remove_html_tags(text: str) -> str:
        """Remove HTML tags from text."""
        clean = re.compile(r'<[^>]+>')
        return clean.sub('', text)
    
    @staticmethod
    def normalize_whitespace(text: str) -> str:
        """Normalize whitespace in text."""
        return re.sub(r'\s+', ' ', text).strip()
    
    @staticmethod
    def extract_years(text: str) -> List[int]:
        """Extract years (4-digit numbers) from text."""
        year_pattern = r'\b(19|20)\d{2}\b'
        years = re.findall(year_pattern, text)
        return [int(year) for year in years]
    
    @staticmethod
    def calculate_word_count(text: str) -> int:
        """Calculate word count in text."""
        if not text:
            return 0
        
        words = text.split()
        return len(words)
    
    @staticmethod
    def extract_name_from_email(email: str) -> Optional[str]:
        """Extract potential name from email address."""
        if not email or '@' not in email:
            return None
        
        local_part = email.split('@')[0]
        
        # Remove numbers and special characters
        name = re.sub(r'[0-9\.\_]', ' ', local_part)
        
        # Capitalize
        name = ' '.join(word.capitalize() for word in name.split())
        
        return name if name else None

def test_text_utils():
    """Test the text utilities."""
    utils = TextUtils()
    
    # Test clean text
    dirty_text = "  This   is  a  test  with  extra  spaces  "
    clean = utils.clean_text(dirty_text)
    print(f"Cleaned text: '{clean}'")
    
    # Test extract emails
    text_with_emails = "Contact us at test@example.com or support@company.org"
    emails = utils.extract_emails(text_with_emails)
    print(f"Extracted emails: {emails}")
    
    # Test extract skills
    resume_text = "I have experience with Python, Java, and Python development"
    skills = utils.extract_skills(resume_text, ["Python", "Java", "JavaScript", "C++"])
    print(f"Extracted skills: {skills}")
    
    # Test truncate
    long_text = "This is a very long text that should be truncated to a shorter version"
    truncated = utils.truncate_text(long_text, max_length=30)
    print(f"Truncated: '{truncated}'")
    
    # Test word count
    word_count = utils.calculate_word_count("This is a test sentence")
    print(f"Word count: {word_count}")

if __name__ == "__main__":
    test_text_utils()
