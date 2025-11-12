"""Centralized AI model configuration.

This module provides a single source of truth for all AI model names used
throughout the application. This ensures consistency and makes it easy to
update model versions.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelConfig:
    """Centralized configuration for AI models.

    This class defines all model names used in the application.
    All services and commands should reference these constants
    instead of hardcoding model names.

    Attributes:
        vision: Model for image analysis (GPT-5)
        search: Model for web search (GPT-4o)
        image: Model for image generation (gpt-image-1)
        transcription: Model for audio transcription (whisper-1)
        tts: Model for text-to-speech (tts-1)
    """

    # Vision Analysis - Use GPT-5 for all image analysis
    vision: str = "gpt-5"

    # Web Search - Use GPT-4o for search queries
    search: str = "gpt-4o"

    # Image Generation - Use gpt-image-1 for all image generation
    image: str = "gpt-image-1"

    # Audio Transcription - Use whisper-1
    transcription: str = "whisper-1"

    # Text-to-Speech - Use tts-1
    tts: str = "tts-1"


# Global model configuration instance
MODELS = ModelConfig()


__all__ = ["MODELS", "ModelConfig"]
