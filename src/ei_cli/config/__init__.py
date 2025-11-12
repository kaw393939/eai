"""Configuration management for EverydayAI CLI.

This module provides type-safe configuration using Pydantic models with:
- Automatic .env file loading
- YAML/JSON config file support
- Environment variable overrides
- Validation and type checking
- Secret handling

Usage:
    from ei_cli.config import get_settings
    
    settings = get_settings()
    api_key = settings.api.openai_api_key.get_secret_value()
    voice = settings.tts.voice
"""

from ei_cli.config.manager import get_settings, reload_settings, reset_settings
from ei_cli.config.models import (
    APIConfig,
    Settings,
    TranscriptionConfig,
    TTSConfig,
    WorkflowConfig,
    YouTubeConfig,
)

__all__ = [
    "APIConfig",
    "Settings",
    "TTSConfig",
    "TranscriptionConfig",
    "WorkflowConfig",
    "YouTubeConfig",
    "get_settings",
    "reload_settings",
    "reset_settings",
]
