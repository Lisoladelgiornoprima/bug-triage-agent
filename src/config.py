"""Configuration management for Bug Triage Agent."""
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field


# Load environment variables
load_dotenv()


class Config(BaseModel):
    """Application configuration."""

    # API Keys
    anthropic_api_key: str = Field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    github_token: str = Field(default_factory=lambda: os.getenv("GITHUB_TOKEN", ""))

    # Model Configuration
    default_model: str = Field(default="claude-sonnet-4-20250514")

    # Logging
    log_level: str = Field(default="INFO")

    # Paths
    project_root: Path = Field(default_factory=lambda: Path(__file__).parent.parent)

    def validate_keys(self) -> None:
        """Validate that required API keys are present."""
        if not self.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment")
        if not self.github_token:
            raise ValueError("GITHUB_TOKEN not found in environment")


# Global config instance
config = Config()
