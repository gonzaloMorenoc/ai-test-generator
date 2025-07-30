"""
Configuration settings for AI Test Generator
"""

import os
from typing import Optional
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class Settings:
    """Main configuration settings"""
    
    # API URLs
    jira_url: str = field(default_factory=lambda: os.getenv("JIRA_URL", "https://your-company.atlassian.net"))
    xray_url_auth: str = field(default_factory=lambda: os.getenv("XRAY_URL_AUTH", "https://xray.cloud.getxray.app/api/v2/authenticate"))
    xray_base_url: str = field(default_factory=lambda: os.getenv("XRAY_BASE_URL", "https://xray.cloud.getxray.app/api/v2"))
    
    # Credentials
    email: str = field(default_factory=lambda: os.getenv("JIRA_EMAIL", ""))
    jira_api_token: str = field(default_factory=lambda: os.getenv("JIRA_API_TOKEN", ""))
    xray_jira_client_id: str = field(default_factory=lambda: os.getenv("XRAY_JIRA_CLIENT_ID", ""))
    xray_jira_client_secret: str = field(default_factory=lambda: os.getenv("XRAY_JIRA_CLIENT_SECRET", ""))
    
    # JQL Query
    jql_query: str = field(default_factory=lambda: os.getenv("JQL_QUERY", 'project = "DEMO" AND Sprint in openSprints() AND labels = "automation-ready"'))
    
    # File paths
    gherkin_examples_file: str = field(default_factory=lambda: os.getenv("GHERKIN_EXAMPLES_FILE", "resources/examples/gherkin_examples.txt"))
    openapi_user_service_file: str = field(default_factory=lambda: os.getenv("OPENAPI_USER_SERVICE_FILE", "resources/examples/openapi_user_service.yaml"))
    openapi_order_service_file: str = field(default_factory=lambda: os.getenv("OPENAPI_ORDER_SERVICE_FILE", "resources/examples/openapi_order_service.yaml"))
    
    # Cache configuration
    cache_dir: str = field(default_factory=lambda: os.getenv("CACHE_DIR", ".test_generation_cache"))
    
    # AI Model configuration
    ai_model: str = field(default_factory=lambda: os.getenv("AI_MODEL", "deepseek-r1:14b"))
    
    # Execution parameters
    max_worker_threads: int = field(default_factory=lambda: int(os.getenv("MAX_WORKER_THREADS", "3")))
    batch_size: int = field(default_factory=lambda: int(os.getenv("BATCH_SIZE", "3")))
    request_timeout: int = field(default_factory=lambda: int(os.getenv("REQUEST_TIMEOUT", "30")))
    
    # Project configuration
    jira_project_key: str = field(default_factory=lambda: os.getenv("JIRA_PROJECT_KEY", "DEMO"))
    
    def validate(self) -> None:
        """Validate required configuration"""
        required_fields = [
            ("email", self.email),
            ("jira_api_token", self.jira_api_token),
            ("xray_jira_client_id", self.xray_jira_client_id),
            ("xray_jira_client_secret", self.xray_jira_client_secret),
        ]
        
        missing_fields = [field_name for field_name, field_value in required_fields if not field_value]
        
        if missing_fields:
            raise ValueError(f"Missing required configuration: {', '.join(missing_fields)}")


@dataclass
class DemoSettings(Settings):
    """Demo configuration with sample values"""
    
    # Override with demo values
    jql_query: str = 'project = "DEMO" AND Sprint in openSprints() AND labels = "automation-ready"'
    ai_model: str = "qwen2.5:7b"  # Smaller model for demo
    max_worker_threads: int = 2
    batch_size: int = 2


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get the global settings instance"""
    return settings


def set_demo_mode(enable: bool = True) -> None:
    """Enable or disable demo mode"""
    global settings
    if enable:
        settings = DemoSettings()
    else:
        settings = Settings()
