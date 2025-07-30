"""
Utility functions for logging, caching, and other common operations
"""

import os
import time
import logging
from typing import Dict, Any

from ..config.settings import get_settings


def setup_logging(log_level: str = "INFO", log_file: str = "test_generation.log") -> None:
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file)
        ]
    )


def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics"""
    settings = get_settings()
    cache_dir = settings.cache_dir
    
    if not os.path.exists(cache_dir):
        return {"file_count": 0, "total_size": 0, "last_modified": None}
    
    files = os.listdir(cache_dir)
    total_size = 0
    last_modified = 0
    
    for file in files:
        file_path = os.path.join(cache_dir, file)
        if os.path.isfile(file_path):
            total_size += os.path.getsize(file_path)
            last_modified = max(last_modified, os.path.getmtime(file_path))
    
    return {
        "file_count": len(files),
        "total_size": total_size,
        "last_modified": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(last_modified)) if last_modified > 0 else None
    }


def clear_cache(max_age_hours: int = 24) -> int:
    """Clear old cache files and return number of deleted files"""
    settings = get_settings()
    cache_dir = settings.cache_dir
    
    if not os.path.exists(cache_dir):
        return 0
    
    current_time = time.time()
    max_age_seconds = max_age_hours * 3600
    deleted_count = 0
    
    for file in os.listdir(cache_dir):
        file_path = os.path.join(cache_dir, file)
        if os.path.isfile(file_path):
            file_age = current_time - os.path.getmtime(file_path)
            if file_age > max_age_seconds:
                try:
                    os.remove(file_path)
                    deleted_count += 1
                except Exception as e:
                    logging.warning(f"Failed to delete cache file {file_path}: {e}")
    
    return deleted_count


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human readable format"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def validate_api_credentials() -> Dict[str, bool]:
    """Validate API credentials"""
    settings = get_settings()
    
    return {
        "jira_email": bool(settings.email),
        "jira_api_token": bool(settings.jira_api_token),
        "xray_client_id": bool(settings.xray_jira_client_id),
        "xray_client_secret": bool(settings.xray_jira_client_secret)
    }
