"""
Service factory for dependency injection.

Provides singleton service instances with proper configuration injection.
"""

from typing import Any

from ei_cli.config import Settings, get_settings


class ServiceFactory:
    """
    Factory for creating and managing service instances.

    Implements singleton pattern to reuse service instances within
    a CLI invocation. Services are lazily initialized on first access.

    Example:
        factory = ServiceFactory()
        ai_service = factory.get_ai_service()
        result = ai_service.search("python best practices")
    """

    def __init__(self, config: Settings | None = None):
        """
        Initialize service factory.

        Args:
            config: Optional configuration. If not provided,
                loads from default config sources.
        """
        self._config = config or get_settings()
        self._services: dict[str, Any] = {}

    @property
    def config(self) -> Settings:
        """Get configuration."""
        return self._config

    def reset(self) -> None:
        """
        Reset all cached service instances.

        Useful for testing or when configuration changes.
        """
        self._services.clear()

    def get_ai_service(self) -> "AIService":  # noqa: F821
        """
        Get or create AIService instance.

        Returns:
            AIService configured with OpenAI API key.

        Raises:
            MissingAPIKeyError: If API key is not configured.
        """
        if "ai" not in self._services:
            # Import here to avoid circular dependencies
            from ei_cli.services.ai_service import AIService

            # Get OpenAI API key from unified settings (no legacy env bridging)
            api_key = self._config.api.openai_api_key.get_secret_value()

            self._services["ai"] = AIService(
                api_key=api_key,
                rate_limit=5,  # 5 requests per second
                max_retries=3,  # 3 retry attempts
            )
        return self._services["ai"]

    def get_image_service(self) -> "ImageService":  # noqa: F821
        """
        Get or create ImageService instance.

        Returns:
            ImageService for image processing operations.
        """
        if "image" not in self._services:
            # Import here to avoid circular dependencies
            from ei_cli.services.image_service import ImageService

            self._services["image"] = ImageService()
        return self._services["image"]

    def __repr__(self) -> str:
        """String representation."""
        return f"<ServiceFactory services={list(self._services.keys())}>"
