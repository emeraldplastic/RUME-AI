"""
Configuration Loader for RUME AI.
Simple configuration management utility.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class ConfigLoader:
    """Simple configuration loader and manager."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the config loader."""
        self.config_path = config_path or "config.json"
        self.config: Dict[str, Any] = {}
        self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        if not os.path.exists(self.config_path):
            logger.warning(f"Config file not found: {self.config_path}, using defaults")
            self.config = self._get_default_config()
            return self.config
        
        try:
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)
            logger.info(f"Loaded config from {self.config_path}")
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing config file: {e}")
            self.config = self._get_default_config()
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            self.config = self._get_default_config()
        
        return self.config
    
    def save_config(self, config_path: Optional[str] = None) -> bool:
        """Save configuration to file."""
        path = config_path or self.config_path
        
        try:
            with open(path, 'w') as f:
                json.dump(self.config, f, indent=2)
            logger.info(f"Saved config to {path}")
            return True
        except Exception as e:
            logger.error(f"Error saving config: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value."""
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "app": {
                "name": "RUME AI",
                "version": "1.0.0",
                "debug": False
            },
            "database": {
                "url": "sqlite:///rume_ai.db",
                "echo": False
            },
            "security": {
                "secret_key": "change-me-in-production",
                "jwt_expiry_hours": 24
            },
            "upload": {
                "max_file_size_mb": 10,
                "allowed_extensions": [".pdf", ".docx", ".txt"]
            },
            "features": {
                "enable_analytics": True,
                "enable_notifications": True,
                "enable_workflow_automation": True
            }
        }
    
    def reload(self) -> Dict[str, Any]:
        """Reload configuration from file."""
        return self.load_config()
    
    def get_all(self) -> Dict[str, Any]:
        """Get all configuration."""
        return self.config.copy()

def test_config_loader():
    """Test the config loader."""
    import tempfile
    
    # Create a temporary config file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        test_config = {
            "app": {"name": "Test App", "version": "2.0"},
            "test_key": "test_value"
        }
        json.dump(test_config, f)
        temp_path = f.name
    
    # Test loading
    loader = ConfigLoader(temp_path)
    print(f"Loaded config: {loader.get_all()}")
    
    # Test get
    app_name = loader.get("app.name")
    print(f"App name: {app_name}")
    
    # Test set
    loader.set("app.name", "Updated App")
    print(f"Updated app name: {loader.get('app.name')}")
    
    # Test save
    loader.save_config()
    print("Config saved successfully")
    
    # Cleanup
    os.unlink(temp_path)

if __name__ == "__main__":
    test_config_loader()
