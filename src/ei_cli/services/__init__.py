"""
Services package for business logic layer.

Services handle business logic and orchestrate tool operations.
Use ServiceFactory to create service instances with proper DI.
"""

from ei_cli.services.ai_service import AIService
from ei_cli.services.base import (
    RateLimitError,
    RetryExhaustedError,
    Service,
    ServiceError,
    ServiceUnavailableError,
)
from ei_cli.services.factory import ServiceFactory
from ei_cli.services.image_service import (
    CropResult,
    ImageService,
    OptimizeResult,
    RemoveBgResult,
)

__all__ = [
    "AIService",
    "CropResult",
    "ImageService",
    "OptimizeResult",
    "RateLimitError",
    "RemoveBgResult",
    "RetryExhaustedError",
    "Service",
    "ServiceError",
    "ServiceFactory",
    "ServiceUnavailableError",
]
