from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # API Settings
    api_title: str = "PAIME API"
    api_version: str = "1.0.0"
    
    # Database
    database_url: str = "postgresql://paime:paime123@db:5432/paime"
    
    # Redis
    redis_url: str = "redis://redis:6379"
    
    # Security
    secret_key: str = "your-secret-key-here"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # CORS
    cors_origins: list = ["*"]
    
    # File Upload
    upload_dir: str = "/app/uploads"
    max_upload_size: int = 104857600  # 100MB
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "/app/logs/backend.log"
    
    class Config:
        env_file = ".env"

settings = Settings()