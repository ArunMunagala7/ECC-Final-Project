"""
Configuration management
"""

import os
import yaml
from typing import Any, Dict


class Config:
    """Configuration loader and manager"""
    
    def __init__(self, config_path: str = None):
        if config_path is None:
            # Default to config/config.yaml relative to project root
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            config_path = os.path.join(project_root, 'config', 'config.yaml')
        
        self.config_path = config_path
        self.config = self._load_config()
        self._setup_directories()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def _setup_directories(self):
        """Create necessary directories if they don't exist"""
        storage = self.config.get('storage', {})
        base_path = storage.get('base_path', './storage')
        
        dirs = [
            base_path,
            os.path.join(base_path, storage.get('input_dir', 'input')),
            os.path.join(base_path, storage.get('chunks_dir', 'chunks')),
            os.path.join(base_path, storage.get('output_dir', 'output')),
            os.path.join(base_path, storage.get('temp_dir', 'temp')),
            self.config.get('logging', {}).get('log_dir', 'logs'),
            self.config.get('evaluation', {}).get('metrics_dir', 'metrics'),
        ]
        
        for directory in dirs:
            os.makedirs(directory, exist_ok=True)
    
    def get(self, *keys, default=None):
        """Get nested configuration value"""
        value = self.config
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return default
            if value is None:
                return default
        return value
    
    def get_storage_path(self, *paths) -> str:
        """Get full path for storage location"""
        base_path = self.get('storage', 'base_path', default='./storage')
        return os.path.join(base_path, *paths)
    
    def __getitem__(self, key):
        """Allow dict-like access"""
        return self.config[key]
    
    def __contains__(self, key):
        """Allow 'in' operator"""
        return key in self.config
