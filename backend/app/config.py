"""Application configuration for different environments."""
import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = "sqlite:///./data/dse_investor.db"

    # App settings
    app_name: str = "DSE Value Investor"
    debug: bool = False

    # CORS - Frontend URL
    frontend_url: str = "http://localhost:5173"

    # API settings
    api_prefix: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
