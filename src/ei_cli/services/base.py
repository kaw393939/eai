"""
Base service classes and interfaces.

Provides abstract base class for all services with common functionality.
"""

from abc import ABC, abstractmethod
from typing import Any


class Service(ABC):
    """Base class for all services."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Service name for logging and identification."""

    @abstractmethod
    def check_available(self) -> tuple[bool, str | None]:
        """
        Check if service is available and ready to use.

        Returns:
            Tuple of (is_available, error_message).
            If available, error_message is None.
            If not available, error_message explains why.
        """

    def __repr__(self) -> str:
        """String representation of service."""
        return f"<{self.__class__.__name__} name={self.name!r}>"


class ServiceError(Exception):
    """Base exception for service-level errors."""

    def __init__(
        self,
        message: str,
        *,
        service_name: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        """
        Initialize service error.

        Args:
            message: Human-readable error message
            service_name: Name of service that raised the error
            details: Additional context about the error
        """
        super().__init__(message)
        self.message = message
        self.service_name = service_name
        self.details = details or {}

    def __str__(self) -> str:
        """Format error message."""
        if self.service_name:
            return f"[{self.service_name}] {self.message}"
        return self.message


class ServiceUnavailableError(ServiceError):
    """Raised when a service is not available."""


class RateLimitError(ServiceError):
    """Raised when rate limit is exceeded."""


class RetryExhaustedError(ServiceError):
    """Raised when all retry attempts are exhausted."""
