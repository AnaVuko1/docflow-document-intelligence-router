"""
Configuration settings for DocFlow application.
Uses Pydantic Settings for environment variable management.
"""

from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl, Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    app_name: str = Field(default="DocFlow", description="Application name")
    app_version: str = Field(default="1.0.0", description="Application version")
    app_env: str = Field(default="development", description="Environment: development, staging, production")
    debug: bool = Field(default=False, description="Debug mode")
    
    # Server
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    workers: int = Field(default=4, description="Number of worker processes")
    
    # Database
    database_url: str = Field(
        default="sqlite+aiosqlite:///./docflow.db",
        description="Database connection URL"
    )
    database_echo: bool = Field(default=False, description="SQL echo mode")
    
    # Security
    secret_key: str = Field(
        default="your-secret-key-change-in-production",
        description="Secret key for JWT tokens"
    )
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(default=30, description="Token expiry in minutes")
    
    # File Uploads
    max_upload_size_mb: int = Field(default=10, description="Maximum upload size in MB")
    upload_dir: str = Field(default="./uploads", description="Directory for uploaded files")
    allowed_extensions: str = Field(default="txt,pdf,doc,docx", description="Allowed file extensions")
    
    # CORS
    cors_origins: List[AnyHttpUrl] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="Allowed CORS origins"
    )
    cors_allow_credentials: bool = Field(default=True, description="Allow credentials in CORS")
    
    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="json", description="Log format: json or plain")
    
    # Connectors
    csv_output_dir: str = Field(default="./outputs", description="CSV output directory")
    json_output_dir: str = Field(default="./outputs", description="JSON output directory")
    sqlite_output_db: str = Field(default="./outputs/data.db", description="SQLite output database")
    webhook_timeout_seconds: int = Field(default=30, description="Webhook timeout in seconds")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()