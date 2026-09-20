"""
File Utilities for RUME AI.
Simple file processing utilities.
"""

import os
from pathlib import Path
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

class FileUtils:
    """Collection of file processing utilities."""
    
    @staticmethod
    def get_file_extension(filename: str) -> str:
        """Get file extension from filename."""
        return Path(filename).suffix.lower()
    
    @staticmethod
    def is_allowed_extension(filename: str, allowed: List[str]) -> bool:
        """Check if file extension is in allowed list."""
        ext = FileUtils.get_file_extension(filename)
        return ext in allowed
    
    @staticmethod
    def get_file_size(filepath: str) -> int:
        """Get file size in bytes."""
        return os.path.getsize(filepath)
    
    @staticmethod
    def get_file_size_mb(filepath: str) -> float:
        """Get file size in megabytes."""
        size_bytes = FileUtils.get_file_size(filepath)
        return size_bytes / (1024 * 1024)
    
    @staticmethod
    def ensure_directory(directory: str) -> bool:
        """Ensure directory exists, create if not."""
        try:
            Path(directory).mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            logger.error(f"Error creating directory: {e}")
            return False
    
    @staticmethod
    def read_file(filepath: str) -> Optional[str]:
        """Read file content as string."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading file: {e}")
            return None
    
    @staticmethod
    def write_file(filepath: str, content: str) -> bool:
        """Write content to file."""
        try:
            FileUtils.ensure_directory(os.path.dirname(filepath))
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            logger.error(f"Error writing file: {e}")
            return False
    
    @staticmethod
    def delete_file(filepath: str) -> bool:
        """Delete file if it exists."""
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
            return True
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            return False
    
    @staticmethod
    def list_files(directory: str, extension: Optional[str] = None) -> List[str]:
        """List files in directory, optionally filtered by extension."""
        try:
            path = Path(directory)
            if extension:
                return [str(f) for f in path.glob(f"*{extension}") if f.is_file()]
            return [str(f) for f in path.iterdir() if f.is_file()]
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            return []

def test_file_utils():
    """Test the file utilities."""
    utils = FileUtils()
    
    # Test get file extension
    ext = utils.get_file_extension("document.pdf")
    print(f"File extension: {ext}")
    
    # Test is allowed extension
    allowed = [".pdf", ".docx", ".txt"]
    is_allowed = utils.is_allowed_extension("document.pdf", allowed)
    print(f"Is allowed: {is_allowed}")
    
    # Test ensure directory
    import tempfile
    temp_dir = tempfile.mkdtemp()
    test_dir = os.path.join(temp_dir, "test_subdir")
    utils.ensure_directory(test_dir)
    print(f"Directory created: {os.path.exists(test_dir)}")
    
    # Test write and read file
    test_file = os.path.join(test_dir, "test.txt")
    utils.write_file(test_file, "Hello, World!")
    content = utils.read_file(test_file)
    print(f"File content: {content}")
    
    # Cleanup
    import shutil
    shutil.rmtree(temp_dir)

if __name__ == "__main__":
    test_file_utils()
