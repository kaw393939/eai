"""Tests for service base classes and factory."""

from ei_cli.config import Settings
from ei_cli.services.base import (
    RateLimitError,
    RetryExhaustedError,
    Service,
    ServiceError,
    ServiceUnavailableError,
)
from ei_cli.services.factory import ServiceFactory


class MockService(Service):
    """Mock service for testing."""

    def __init__(self, available: bool = True):
        self._available = available

    @property
    def name(self) -> str:
        return "mock_service"

    def check_available(self) -> tuple[bool, str | None]:
        if self._available:
            return (True, None)
        return (False, "Service not available")


class TestService:
    """Tests for Service base class."""

    def test_service_name(self):
        """Test service name property."""
        service = MockService()
        assert service.name == "mock_service"

    def test_service_available(self):
        """Test available service."""
        service = MockService(available=True)
        is_available, error = service.check_available()

        assert is_available is True
        assert error is None

    def test_service_unavailable(self):
        """Test unavailable service."""
        service = MockService(available=False)
        is_available, error = service.check_available()

        assert is_available is False
        assert error == "Service not available"

    def test_service_repr(self):
        """Test service string representation."""
        service = MockService()
        repr_str = repr(service)

        assert "MockService" in repr_str
        assert "mock_service" in repr_str


class TestServiceError:
    """Tests for ServiceError exceptions."""

    def test_service_error_basic(self):
        """Test basic service error."""
        error = ServiceError("Something went wrong")

        assert str(error) == "Something went wrong"
        assert error.message == "Something went wrong"
        assert error.service_name is None
        assert error.details == {}

    def test_service_error_with_service_name(self):
        """Test service error with service name."""
        error = ServiceError(
            "API call failed",
            service_name="ai_service",
        )

        assert str(error) == "[ai_service] API call failed"
        assert error.service_name == "ai_service"

    def test_service_error_with_details(self):
        """Test service error with details."""
        error = ServiceError(
            "Request failed",
            service_name="api",
            details={"status_code": 500, "retry_count": 3},
        )

        assert error.details["status_code"] == 500
        assert error.details["retry_count"] == 3

    def test_service_unavailable_error(self):
        """Test ServiceUnavailableError."""
        error = ServiceUnavailableError(
            "API key missing",
            service_name="openai",
        )

        assert isinstance(error, ServiceError)
        assert "API key missing" in str(error)

    def test_rate_limit_error(self):
        """Test RateLimitError."""
        error = RateLimitError(
            "Rate limit exceeded",
            service_name="ai_service",
            details={"limit": 5, "window": "1s"},
        )

        assert isinstance(error, ServiceError)
        assert error.details["limit"] == 5

    def test_retry_exhausted_error(self):
        """Test RetryExhaustedError."""
        error = RetryExhaustedError(
            "Max retries reached",
            service_name="ai_service",
            details={"attempts": 3},
        )

        assert isinstance(error, ServiceError)
        assert error.details["attempts"] == 3


class TestServiceFactory:
    """Tests for ServiceFactory."""

    def test_factory_initialization(self, monkeypatch):
        """Test factory initialization."""
        monkeypatch.setenv("API__OPENAI_API_KEY", "test-key")
        factory = ServiceFactory()

        assert factory.config is not None
        assert isinstance(factory.config, Settings)

    def test_factory_with_custom_config(self, monkeypatch):
        """Test factory with custom config."""
        monkeypatch.setenv("API__OPENAI_API_KEY", "test-key")
        config = Settings()
        factory = ServiceFactory(config=config)

        assert factory.config is config

    def test_factory_reset(self, monkeypatch):
        """Test factory reset clears cached services."""
        monkeypatch.setenv("EI_API_KEY", "test-key")
        factory = ServiceFactory()

        # Manually add a service to cache
        factory._services["test"] = "cached_service"
        assert "test" in factory._services

        # Reset should clear cache
        factory.reset()
        assert "test" not in factory._services
        assert len(factory._services) == 0

    def test_factory_repr(self, monkeypatch):
        """Test factory string representation."""
        monkeypatch.setenv("EI_API_KEY", "test-key")
        factory = ServiceFactory()
        repr_str = repr(factory)

        assert "ServiceFactory" in repr_str
        assert "services" in repr_str

    def test_factory_lazy_initialization(self, monkeypatch):
        """Test services are lazily initialized."""
        monkeypatch.setenv("EI_API_KEY", "test-key")
        factory = ServiceFactory()

        # Initially no services should be created
        assert len(factory._services) == 0

    def test_factory_singleton_pattern(self, monkeypatch):
        """Test factory returns same instance on multiple calls."""
        monkeypatch.setenv("EI_API_KEY", "test-key")
        factory = ServiceFactory()

        # Get service twice
        service1 = factory.get_ai_service()
        service2 = factory.get_ai_service()

        # Should be the same instance
        assert service1 is service2
        assert len(factory._services) == 1

    def test_factory_multiple_services(self, monkeypatch):
        """Test factory can create multiple service types."""
        # Set API key for AIService
        monkeypatch.setenv("EI_API_KEY", "test-key")

        factory = ServiceFactory()

        # Get both services
        ai = factory.get_ai_service()
        image = factory.get_image_service()

        # Verify both are created
        assert ai is not None
        assert image is not None

        # Verify singletons
        assert factory.get_ai_service() is ai
        assert factory.get_image_service() is image
