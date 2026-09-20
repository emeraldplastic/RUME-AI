"""
Date Utilities for RUME AI.
Simple date and time processing utilities.
"""

from datetime import datetime, timedelta
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)

class DateUtils:
    """Collection of date and time utilities."""
    
    @staticmethod
    def format_date(date: datetime, format: str = "%Y-%m-%d") -> str:
        """Format datetime to string."""
        return date.strftime(format)
    
    @staticmethod
    def parse_date(date_str: str, format: str = "%Y-%m-%d") -> Optional[datetime]:
        """Parse string to datetime."""
        try:
            return datetime.strptime(date_str, format)
        except ValueError as e:
            logger.error(f"Error parsing date: {e}")
            return None
    
    @staticmethod
    def days_between(start_date: datetime, end_date: datetime) -> int:
        """Calculate days between two dates."""
        return (end_date - start_date).days
    
    @staticmethod
    def add_days(date: datetime, days: int) -> datetime:
        """Add days to a date."""
        return date + timedelta(days=days)
    
    @staticmethod
    def is_weekend(date: datetime) -> bool:
        """Check if date is a weekend."""
        return date.weekday() >= 5
    
    @staticmethod
    def get_age(birth_date: datetime) -> int:
        """Calculate age from birth date."""
        today = datetime.now()
        age = today.year - birth_date.year
        
        if (today.month, today.day) < (birth_date.month, birth_date.day):
            age -= 1
        
        return age
    
    @staticmethod
    def get_quarter(date: datetime) -> int:
        """Get quarter of the year."""
        return (date.month - 1) // 3 + 1
    
    @staticmethod
    def get_week_number(date: datetime) -> int:
        """Get ISO week number."""
        return date.isocalendar()[1]
    
    @staticmethod
    def is_business_day(date: datetime) -> bool:
        """Check if date is a business day (not weekend)."""
        return not DateUtils.is_weekend(date)
    
    @staticmethod
    def add_business_days(date: datetime, days: int) -> datetime:
        """Add business days to a date."""
        result = date
        added = 0
        
        while added < days:
            result += timedelta(days=1)
            if DateUtils.is_business_day(result):
                added += 1
        
        return result

def test_date_utils():
    """Test the date utilities."""
    utils = DateUtils()
    
    # Test format date
    now = datetime.now()
    formatted = utils.format_date(now)
    print(f"Formatted date: {formatted}")
    
    # Test parse date
    parsed = utils.parse_date("2024-01-15")
    print(f"Parsed date: {parsed}")
    
    # Test days between
    start = datetime(2024, 1, 1)
    end = datetime(2024, 1, 10)
    days = utils.days_between(start, end)
    print(f"Days between: {days}")
    
    # Test is weekend
    weekend = datetime(2024, 1, 6)  # Saturday
    print(f"Is weekend: {utils.is_weekend(weekend)}")
    
    # Test get age
    birth = datetime(1990, 5, 15)
    age = utils.get_age(birth)
    print(f"Age: {age}")

if __name__ == "__main__":
    test_date_utils()
