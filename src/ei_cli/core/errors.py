"""
Core error handling for EverydayAI CLI (ei-cli).

Following EAFP (Easier to Ask Forgiveness than Permission) principles:
- Try operations, catch errors gracefully
- Provide structured, JSON-serializable errors for AI consumption
- Include helpful suggestions for users
- Support error chaining for debugging

All errors inherit from VibeError (base error class) and provide:
- Structured attributes (message, code, recoverable, context)
- JSON serialization (to_dict, to_json)
- Appropriate exit codes
- Automatic timestamps

Sprint 4.1 Enhancements:
- Error catalog with solutions and docs URLs
- Retry with exponential backoff
- Structured logging support
- Error reporting system
"""
import functools
import json
import logging
from collections.abc import Callable
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from rich.console import Console

console = Console()

# ============================================================================
# STRUCTURED LOGGING
# ============================================================================

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels for categorization."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

# ============================================================================
# BASE ERROR CLASS
# ============================================================================

class VibeError(Exception):
    """
    Base error class for all Vibe CLI errors.

    Provides structured, JSON-serializable error information for:
    - AI agents (machine-readable JSON)
    - Humans (readable messages with suggestions)
    - Logging (structured context)

    Attributes:
        message: Human-readable error message
        code: Machine-readable error code (e.g., "MISSING_API_KEY")
        recoverable: Whether user can fix this error
        context: Additional structured context (dict)
        suggestion: Optional helpful suggestion for fixing the error
    """

    def __init__(
        self,
        message: str,
        code: str,
        recoverable: bool = True,
        context: dict[str, Any] | None = None,
        suggestion: str | None = None,
    ):
        """Initialize VibeError."""
        super().__init__(message)
        self.message = message
        self.code = code
        self.recoverable = recoverable
        self.context = context or {}
        self.suggestion = suggestion
        self.timestamp = datetime.now(UTC).isoformat()

    def to_dict(self) -> dict[str, Any]:
        """
        Convert error to JSON-serializable dict.

        Returns:
            Dict with error details for AI consumption or logging
        """
        result = {
            "message": self.message,
            "code": self.code,
            "recoverable": self.recoverable,
            "context": self.context,
            "timestamp": self.timestamp,
        }

        if self.suggestion:
            result["suggestion"] = self.suggestion

        return result

    def to_json(self) -> str:
        """
        Convert error to JSON string.

        Returns:
            JSON string for CLI --json output
        """
        return json.dumps(self.to_dict(), indent=2)

    @property
    def exit_code(self) -> int:
        """
        Get appropriate exit code.

        Returns:
            1 for recoverable errors (user can fix)
            2 for fatal errors (system issue)
        """
        return 1 if self.recoverable else 2

    def __str__(self) -> str:
        """
        Human-readable error string.

        Returns:
            Formatted error message with code
        """
        result = f"[{self.code}] {self.message}"

        if self.suggestion:  # pragma: no branch
            result += f"\n\nSuggestion: {self.suggestion}"

        return result


# ============================================================================
# CONFIGURATION ERRORS
# ============================================================================

class ConfigurationError(VibeError):
    """Base class for configuration-related errors."""

    def __init__(
        self,
        message: str,
        code: str | None = None,
        recoverable: bool = True,
        context: dict[str, Any] | None = None,
        suggestion: str | None = None,
    ):
        """Initialize ConfigurationError."""
        if code is None:  # pragma: no branch
            code = "CONFIG_ERROR"
        elif not code.startswith("CONFIG_"):
            code = f"CONFIG_{code}"

        super().__init__(
            message=message,
            code=code,
            recoverable=recoverable,
            context=context,
            suggestion=suggestion,
        )


class MissingAPIKeyError(ConfigurationError):
    """Raised when OpenAI API key is not configured."""

    def __init__(
        self,
        message: str | None = None,
        context: dict[str, Any] | None = None,
    ):
        """Initialize MissingAPIKeyError."""
        if message is None:  # pragma: no branch
            message = (
                "OpenAI API key not found. "
                "Set EI_API_KEY environment variable or add to config."
            )

        suggestion = (
            "export EI_API_KEY='your-api-key-here'\n"
            "Or add to .ei/config.yaml:\n"
            "  ai:\n"
            "    api_key: your-api-key-here"
        )

        # Initialize with explicit code, bypassing ConfigurationError's prefix logic
        VibeError.__init__(
            self,
            message=message,
            code="MISSING_API_KEY",
            recoverable=True,
            context=context or {},
            suggestion=suggestion,
        )


class InvalidConfigError(ConfigurationError):
    """Raised when configuration is invalid."""

    def __init__(
        self,
        message: str | None = None,
        context: dict[str, Any] | None = None,
        suggestion: str | None = None,
    ):
        """Initialize InvalidConfigError."""
        if message is None:  # pragma: no branch
            message = "Configuration is invalid"

        # Initialize with explicit code, bypassing ConfigurationError's prefix logic
        VibeError.__init__(
            self,
            message=message,
            code="INVALID_CONFIG",
            recoverable=True,
            context=context or {},
            suggestion=suggestion,
        )


class ConfigFileNotFoundError(ConfigurationError):
    """Raised when config file is not found."""

    def __init__(
        self,
        message: str | None = None,
        context: dict[str, Any] | None = None,
    ):
        """Initialize ConfigFileNotFoundError."""
        if message is None:  # pragma: no branch
            message = "Configuration file not found"

        # Project not initialized
        suggestion = "Run 'ei init' to create a new project with default config"
        
        super().__init__(
            message=message,
            code="CONFIG_NOT_FOUND",
            recoverable=True,
            context=context,
            suggestion=suggestion,
        )


# ============================================================================
# AI SERVICE ERRORS
# ============================================================================

class AIServiceError(VibeError):
    """Base class for AI service errors."""

    def __init__(
        self,
        message: str,
        code: str | None = None,
        recoverable: bool = True,
        context: dict[str, Any] | None = None,
        suggestion: str | None = None,
    ):
        """Initialize AIServiceError."""
        if code is None:  # pragma: no branch
            code = "AI_ERROR"
        elif not code.startswith("AI_"):
            code = f"AI_{code}"

        super().__init__(
            message=message,
            code=code,
            recoverable=recoverable,
            context=context,
            suggestion=suggestion,
        )


class RateLimitError(AIServiceError):
    """Raised when API rate limit is exceeded."""

    def __init__(
        self,
        message: str | None = None,
        context: dict[str, Any] | None = None,
    ):
        """Initialize RateLimitError."""
        if message is None:  # pragma: no branch
            retry_after = context.get("retry_after", 60) if context else 60
            message = f"Rate limit exceeded. Retry after {retry_after} seconds."

        suggestion = "Wait a moment and try again, or upgrade your OpenAI plan"

        super().__init__(
            message=message,
            code="RATE_LIMIT",
            recoverable=True,
            context=context,
            suggestion=suggestion,
        )


class TokenLimitError(AIServiceError):
    """Raised when token limit is exceeded."""

    def __init__(
        self,
        message: str | None = None,
        context: dict[str, Any] | None = None,
    ):
        """Initialize TokenLimitError."""
        if message is None:  # pragma: no branch
            if context:
                requested = context.get("requested", "unknown")
                max_tokens = context.get("max", "unknown")
                message = (
                    f"Token limit exceeded: requested {requested}, "
                    f"max {max_tokens}"
                )
            else:
                message = "Token limit exceeded"

        suggestion = "Reduce prompt length or use --max-tokens flag"

        super().__init__(
            message=message,
            code="TOKEN_LIMIT",
            recoverable=True,
            context=context,
            suggestion=suggestion,
        )


class InvalidResponseError(AIServiceError):
    """Raised when AI service returns invalid response."""

    def __init__(
        self,
        message: str | None = None,
        context: dict[str, Any] | None = None,
    ):
        """Initialize InvalidResponseError."""
        if message is None:  # pragma: no branch
            message = "AI service returned invalid response"

        super().__init__(
            message=message,
            code="INVALID_RESPONSE",
            recoverable=True,
            context=context,
        )


# ============================================================================
# GIT ERRORS
# ============================================================================

class GitError(VibeError):
    """Base class for Git-related errors."""

    def __init__(
        self,
        message: str,
        code: str | None = None,
        recoverable: bool = True,
        context: dict[str, Any] | None = None,
        suggestion: str | None = None,
    ):
        """Initialize GitError."""
        if code is None:  # pragma: no branch
            code = "GIT_ERROR"
        elif not code.startswith("GIT_"):
            code = f"GIT_{code}"

        super().__init__(
            message=message,
            code=code,
            recoverable=recoverable,
            context=context,
            suggestion=suggestion,
        )


class DirtyWorkingTreeError(GitError):
    """Raised when working tree has uncommitted changes."""

    def __init__(
        self,
        message: str | None = None,
        context: dict[str, Any] | None = None,
    ):
        """Initialize DirtyWorkingTreeError."""
        max_files_to_show = 5  # Constant for clarity
        if message is None:  # pragma: no branch
            if context and "files" in context:
                files = context["files"]
                file_list = "\n  - ".join(files[:max_files_to_show])
                more = (
                    f"\n  ... and {len(files) - max_files_to_show} more"
                    if len(files) > max_files_to_show
                    else ""
                )
                message = (
                    "Working tree has uncommitted changes:"
                    f"\n  - {file_list}{more}"
                )
            else:
                message = "Working tree has uncommitted changes"

        suggestion = "Commit or stash your changes before proceeding"

        super().__init__(
            message=message,
            code="DIRTY_WORKING_TREE",
            recoverable=True,
            context=context,
            suggestion=suggestion,
        )


class NotAGitRepoError(GitError):
    """Raised when directory is not a git repository."""

    def __init__(
        self,
        message: str | None = None,
        context: dict[str, Any] | None = None,
    ):
        """Initialize NotAGitRepoError."""
        if message is None:  # pragma: no branch
            message = "Not a git repository"

        suggestion = "Run 'git init' to initialize a git repository"

        super().__init__(
            message=message,
            code="NOT_GIT_REPO",
            recoverable=True,
            context=context,
            suggestion=suggestion,
        )


# ============================================================================
# TEMPLATE ERRORS
# ============================================================================

class TemplateError(VibeError):
    """Base class for template-related errors."""

    def __init__(
        self,
        message: str,
        code: str | None = None,
        recoverable: bool = True,
        context: dict[str, Any] | None = None,
        suggestion: str | None = None,
    ):
        """Initialize TemplateError."""
        if code is None:  # pragma: no branch
            code = "TEMPLATE_ERROR"
        elif not code.startswith("TEMPLATE_"):
            code = f"TEMPLATE_{code}"

        super().__init__(
            message=message,
            code=code,
            recoverable=recoverable,
            context=context,
            suggestion=suggestion,
        )


class TemplateNotFoundError(TemplateError):
    """Raised when template is not found."""

    def __init__(
        self,
        message: str | None = None,
        context: dict[str, Any] | None = None,
    ):
        """Initialize TemplateNotFoundError."""
        if message is None:  # pragma: no branch
            if context and "template" in context:
                template_name = context["template"]
                message = f"Template not found: {template_name}"
            else:
                message = "Template not found"

        suggestion = None
        if context and "available" in context:
            available = context["available"]
            suggestion = f"Available templates: {', '.join(available)}"

        super().__init__(
            message=message,
            code="NOT_FOUND",
            recoverable=True,
            context=context,
            suggestion=suggestion,
        )


class TemplateSyntaxError(TemplateError):
    """Raised when template has syntax errors."""

    def __init__(
        self,
        message: str | None = None,
        context: dict[str, Any] | None = None,
    ):
        """Initialize TemplateSyntaxError."""
        if message is None:  # pragma: no branch
            message = "Template has syntax errors"

        super().__init__(
            message=message,
            code="SYNTAX_ERROR",
            recoverable=True,
            context=context,
        )


# ============================================================================
# ITERATION ERRORS
# ============================================================================

class IterationError(VibeError):
    """Base class for iteration-related errors."""

    def __init__(
        self,
        message: str,
        code: str | None = None,
        recoverable: bool = True,
        context: dict[str, Any] | None = None,
        suggestion: str | None = None,
    ):
        """Initialize IterationError."""
        if code is None:  # pragma: no branch
            code = "ITERATION_ERROR"
        elif not code.startswith("ITERATION_"):
            code = f"ITERATION_{code}"

        super().__init__(
            message=message,
            code=code,
            recoverable=recoverable,
            context=context,
            suggestion=suggestion,
        )


class IterationLogCorruptedError(IterationError):
    """Raised when iteration log is corrupted."""

    def __init__(
        self,
        message: str | None = None,
        context: dict[str, Any] | None = None,
    ):
        """Initialize IterationLogCorruptedError."""
        if message is None:  # pragma: no branch
            message = "Iteration log is corrupted"

        suggestion = "Backup and delete .vibe/iterations.log, then try again"

        super().__init__(
            message=message,
            code="LOG_CORRUPTED",
            recoverable=True,
            context=context,
            suggestion=suggestion,
        )


# ============================================================================
# VALIDATION ERRORS
# ============================================================================

class ValidationError(VibeError):
    """Base class for validation errors."""

    def __init__(
        self,
        message: str,
        code: str | None = None,
        recoverable: bool = True,
        context: dict[str, Any] | None = None,
        suggestion: str | None = None,
    ):
        """Initialize ValidationError."""
        if code is None:  # pragma: no branch
            code = "VALIDATION_ERROR"
        elif not code.startswith("VALIDATION_"):
            code = f"VALIDATION_{code}"

        super().__init__(
            message=message,
            code=code,
            recoverable=recoverable,
            context=context,
            suggestion=suggestion,
        )


# ============================================================================
# EAFP HELPERS
# ============================================================================

def handle_error(
    error_code: str,
    message: str | None = None,
    recoverable: bool = True,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator to catch exceptions and convert to VibeError.

    EAFP principle: Try operation, catch errors gracefully.

    Usage:
        @handle_error(error_code="OPERATION_FAILED")
        def risky_operation():
            raise ValueError("Something went wrong")

    Args:
        error_code: Error code for the VibeError
        message: Optional custom message (uses original if not provided)
        recoverable: Whether error is recoverable

    Returns:
        Decorated function that raises VibeError instead of original exception
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except VibeError:
                # Already a VibeError, re-raise as-is
                raise
            # Intentionally broad Exception catch for EAFP pattern
            except Exception as e:  # pragma: no cover - EAFP catch-all
                # Convert to VibeError
                error_message = message or str(e)
                raise VibeError(
                    message=error_message,
                    code=error_code,
                    recoverable=recoverable,
                    context={"original": str(e), "type": type(e).__name__},
                ) from e
        return wrapper
    return decorator


# ============================================================================
# SPRINT 4.1: RETRY WITH EXPONENTIAL BACKOFF
# ============================================================================

def retry_with_backoff(
    func: Callable[..., Any],
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    retry_on: tuple[type[Exception], ...] | None = None,
    silent: bool = False,
) -> Any:
    """
    Retry function with exponential backoff.

    Args:
        func: Function to retry (no arguments)
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        backoff_factor: Multiplier for delay after each retry
        retry_on: Tuple of exception types to retry on (None = all)
        silent: If True, don't show retry messages

    Returns:
        Function result

    Raises:
        Last exception if all retries exhausted

    Example:
        result = retry_with_backoff(
            lambda: api_call(),
            max_retries=3,
            retry_on=(RateLimitError, NetworkError)
        )
    """
    import time

    delay = initial_delay
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            return func()
        except Exception as e:
            last_error = e

            # Log error
            logger.warning(
                "Attempt %d/%d failed: %s",
                attempt + 1,
                max_retries + 1,
                str(e),
            )

            # Check if we should retry this exception
            if retry_on and not isinstance(e, retry_on):
                logger.error("Exception not in retry list, raising")
                raise

            # Don't retry on last attempt
            if attempt == max_retries:
                logger.error("Max retries exhausted")
                break

            # Show retry message
            if not silent:
                console.print(
                    f"[yellow]Attempt {attempt + 1}/{max_retries + 1} failed. "
                    f"Retrying in {delay:.1f}s...[/yellow]",
                )

            # Wait before retry
            time.sleep(delay)

            # Increase delay
            delay *= backoff_factor

    # All retries exhausted
    if last_error:
        raise last_error

    # Should not reach here
    msg = "No result and no error after retries"
    raise RuntimeError(msg)


# ============================================================================
# SPRINT 4.1: ERROR REPORTING
# ============================================================================

class ErrorReporter:
    """Collect and report errors for debugging and analytics."""

    def __init__(self) -> None:
        """Initialize error reporter."""
        self.errors: list[dict[str, Any]] = []

    def report(
        self,
        error: Exception,
        context: dict[str, Any] | None = None,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
    ) -> None:
        """
        Report an error for tracking.

        Args:
            error: The exception that occurred
            context: Additional context about the error
            severity: Error severity level
        """
        error_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "type": type(error).__name__,
            "message": str(error),
            "severity": severity.value,
            "context": context or {},
        }

        # Add structured info if VibeError
        if isinstance(error, VibeError):
            error_entry["code"] = error.code
            error_entry["recoverable"] = error.recoverable
            error_entry["vibe_context"] = error.context

        self.errors.append(error_entry)

        # Log error
        log_method = getattr(logger, severity.value)
        log_method(
            "Error reported: %s - %s",
            error_entry["type"],
            error_entry["message"],
            extra={"error_entry": error_entry},
        )

    def get_errors(
        self,
        severity: ErrorSeverity | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get reported errors, optionally filtered by severity.

        Args:
            severity: Filter by severity level (None = all)

        Returns:
            List of error entries
        """
        if severity is None:
            return self.errors.copy()

        return [
            err
            for err in self.errors
            if err["severity"] == severity.value
        ]

    def clear(self) -> None:
        """Clear all reported errors."""
        self.errors.clear()
        logger.info("Error reporter cleared")

    def to_json(self) -> str:
        """
        Export errors as JSON.

        Returns:
            JSON string with all errors
        """
        return json.dumps(
            {"errors": self.errors, "count": len(self.errors)},
            indent=2,
        )

    def summary(self) -> dict[str, int]:
        """
        Get error summary by severity.

        Returns:
            Dict with counts by severity level
        """
        summary_dict = {
            "info": 0,
            "warning": 0,
            "error": 0,
            "critical": 0,
            "total": len(self.errors),
        }

        for error in self.errors:
            severity = error.get("severity", "error")
            if severity in summary_dict:
                summary_dict[severity] += 1

        return summary_dict

    def print_summary(self) -> None:
        """Print error summary to console."""
        summary_dict = self.summary()

        if summary_dict["total"] == 0:
            console.print("[green]No errors reported[/green]")
            return

        console.print("\n[bold]Error Summary:[/bold]")
        console.print(f"  Total: {summary_dict['total']}")

        if summary_dict["critical"] > 0:
            console.print(f"  [red bold]Critical: {summary_dict['critical']}[/red bold]")

        if summary_dict["error"] > 0:
            console.print(f"  [red]Errors: {summary_dict['error']}[/red]")

        if summary_dict["warning"] > 0:
            console.print(f"  [yellow]Warnings: {summary_dict['warning']}[/yellow]")

        if summary_dict["info"] > 0:
            console.print(f"  [blue]Info: {summary_dict['info']}[/blue]")


# Global error reporter instance
_error_reporter = ErrorReporter()


def get_error_reporter() -> ErrorReporter:
    """
    Get global error reporter instance.

    Returns:
        Global ErrorReporter instance
    """
    return _error_reporter


def report_error(
    error: Exception,
    context: dict[str, Any] | None = None,
    severity: ErrorSeverity = ErrorSeverity.ERROR,
) -> None:
    """
    Report error to global error reporter.

    Args:
        error: The exception to report
        context: Additional context
        severity: Error severity level
    """
    _error_reporter.report(error, context, severity)

