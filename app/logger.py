"""
Logger Configuration for RUME AI.
Simple logging setup utility.
"""

import logging
import os
from datetime import datetime
from typing import Optional

class LoggerSetup:
    """Simple logger configuration utility."""
    
    @staticmethod
    def setup_logger(
        name: str,
        log_file: Optional[str] = None,
        level: int = logging.INFO,
        format_string: Optional[str] = None
    ) -> logging.Logger:
        """
        Setup a logger with file and console handlers.
        
        Args:
            name: Logger name
            log_file: Optional log file path
            level: Logging level
            format_string: Optional custom format string
        
        Returns:
            Configured logger
        """
        logger = logging.getLogger(name)
        logger.setLevel(level)
        
        # Clear existing handlers
        logger.handlers.clear()
        
        # Default format
        if format_string is None:
            format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        formatter = logging.Formatter(format_string)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # File handler if specified
        if log_file:
            # Ensure directory exists
            log_dir = os.path.dirname(log_file)
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)
            
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        
        return logger
    
    @staticmethod
    def get_log_filename(base_name: str = "app") -> str:
        """Generate a log filename with timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d")
        return f"{base_name}_{timestamp}.log"

def test_logger():
    """Test the logger setup."""
    # Setup logger
    logger = LoggerSetup.setup_logger(
        name="test_logger",
        log_file="logs/test.log",
        level=logging.DEBUG
    )
    
    # Test logging
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
    
    print("Logger test completed. Check logs/test.log for output.")

if __name__ == "__main__":
    test_logger()
