"""
Unit tests for core error handling.

Following TDD Red-Green-Refactor:
1. Write failing tests (RED) ✓ We're here
2. Implement minimal code to pass (GREEN)
3. Refactor for quality

Testing the VibeError hierarchy and EAFP error handling patterns.
"""
import json
from datetime import datetime

import pytest
from hypothesis import given
from hypothesis import strategies as st

from ei_cli.core.errors import (
    AIServiceError,
    ConfigFileNotFoundError,
    ConfigurationError,
    DirtyWorkingTreeError,
    GitError,
    InvalidConfigError,
    InvalidResponseError,
    IterationError,
    IterationLogCorruptedError,
    MissingAPIKeyError,
    NotAGitRepoError,
    RateLimitError,
    TemplateError,
    TemplateNotFoundError,
    TemplateSyntaxError,
    TokenLimitError,
    ValidationError,
    VibeError,
    handle_error,
)

# ============================================================================
# TEST: VibeError Base Class
# ============================================================================

def test_vibe_error_has_required_attributes():
    """
    RED: Test that VibeError has structured attributes.

    VibeError should have:
    - message (str): Human-readable error message
    - code (str): Machine-readable error code
    - recoverable (bool): Whether user can fix this
    - context (dict): Additional context
    """


    error = VibeError(
        message="Test error",
        code="TEST_ERROR",
        recoverable=True,
        context={"key": "value"},
    )

    assert error.message == "Test error"
    assert error.code == "TEST_ERROR"
    assert error.recoverable is True
    assert error.context == {"key": "value"}


def test_vibe_error_to_dict_returns_correct_structure():
    """
    RED: Test that VibeError.to_dict() returns JSON-serializable dict.

    Required for AI agent consumption and structured logging.
    """


    error = VibeError(
        message="Test error",
        code="TEST_ERROR",
        recoverable=True,
        context={"file": "test.py", "line": 42},
    )

    result = error.to_dict()

    assert result["message"] == "Test error"
    assert result["code"] == "TEST_ERROR"
    assert result["recoverable"] is True
    assert result["context"]["file"] == "test.py"
    assert result["context"]["line"] == 42
    assert "timestamp" in result  # Should add timestamp


def test_vibe_error_to_json_returns_valid_json():
    """
    RED: Test that VibeError.to_json() returns valid JSON string.

    Required for CLI --json output mode.
    """


    error = VibeError(
        message="Test error",
        code="TEST_ERROR",
        recoverable=True,
    )

    json_str = error.to_json()

    # Should be valid JSON
    parsed = json.loads(json_str)
    assert parsed["message"] == "Test error"
    assert parsed["code"] == "TEST_ERROR"


def test_vibe_error_exit_code_returns_correct_code():
    """
    RED: Test that VibeError.exit_code returns appropriate exit code.

    Exit codes:
    - Recoverable errors: 1 (user can fix)
    - Fatal errors: 2 (system issue)
    """


    recoverable_error = VibeError(
        message="Missing config",
        code="CONFIG_ERROR",
        recoverable=True,
    )

    fatal_error = VibeError(
        message="System error",
        code="SYSTEM_ERROR",
        recoverable=False,
    )

    assert recoverable_error.exit_code == 1
    assert fatal_error.exit_code == 2


def test_vibe_error_str_returns_readable_message():
    """
    RED: Test that str(error) returns human-readable message.

    For terminal output and logging.
    """


    error = VibeError(
        message="Missing API key",
        code="MISSING_API_KEY",
        recoverable=True,
    )

    result = str(error)

    # Should contain message and code
    assert "Missing API key" in result
    assert "MISSING_API_KEY" in result


# ============================================================================
# ConfigurationError Tests
# ============================================================================

def test_configuration_error_inherits_from_vibe_error():
    """RED: ConfigurationError should inherit from VibeError."""


    error = ConfigurationError(message="Bad config")

    assert isinstance(error, VibeError)
    assert error.code.startswith("CONFIG_")


def test_missing_api_key_error_has_correct_attributes():
    """
    RED: MissingAPIKeyError should have specific code and be recoverable.

    User can fix by setting VIBE_API_KEY env var.
    """


    error = MissingAPIKeyError()

    assert error.code == "MISSING_API_KEY"
    assert error.recoverable is True
    assert "API key" in error.message or "VIBE_API_KEY" in error.message


def test_invalid_config_error_includes_validation_details():
    """
    RED: InvalidConfigError should include what's invalid.

    Helpful error messages for users.
    """


    error = InvalidConfigError(
        message="Invalid config",
        context={
            "field": "ai.max_tokens",
            "value": -1,
            "reason": "Must be positive",
        },
    )

    assert error.code == "INVALID_CONFIG"
    assert error.context["field"] == "ai.max_tokens"
    assert error.context["reason"] == "Must be positive"


# ============================================================================
# AIServiceError Tests
# ============================================================================

def test_ai_service_error_inherits_from_vibe_error():
    """RED: AIServiceError should inherit from VibeError."""


    error = AIServiceError(message="AI failed")

    assert isinstance(error, VibeError)
    assert error.code.startswith("AI_")


def test_rate_limit_error_is_recoverable():
    """
    RED: RateLimitError should be recoverable (user can wait).

    Include retry_after in context.
    """


    error = RateLimitError(context={"retry_after": 60})

    assert error.recoverable is True
    assert error.context["retry_after"] == 60


def test_token_limit_error_includes_usage_info():
    """
    RED: TokenLimitError should show current vs max tokens.

    Helps user adjust --max-tokens.
    """


    error = TokenLimitError(
        context={
            "requested": 5000,
            "max": 4096,
            "model": "gpt-4",
        },
    )

    assert error.context["requested"] == 5000
    assert error.context["max"] == 4096


# ============================================================================
# GitError Tests
# ============================================================================

def test_git_error_inherits_from_vibe_error():
    """RED: GitError should inherit from VibeError."""


    error = GitError(message="Git failed")

    assert isinstance(error, VibeError)
    assert error.code.startswith("GIT_")


def test_dirty_working_tree_error_is_recoverable():
    """
    RED: DirtyWorkingTreeError should be recoverable (user can commit).

    Include list of dirty files in context.
    """


    error = DirtyWorkingTreeError(
        context={
            "files": ["src/main.py", "README.md"],
        },
    )

    assert error.recoverable is True
    assert len(error.context["files"]) == 2


# ============================================================================
# TemplateError Tests
# ============================================================================

def test_template_not_found_error_includes_template_name():
    """
    RED: TemplateNotFoundError should show which template is missing.

    Helps user fix typos or know available templates.
    """


    error = TemplateNotFoundError(
        context={
            "template": "email-writting",  # Typo
            "available": ["email-writing", "lesson-plans"],
        },
    )

    assert error.context["template"] == "email-writting"
    assert "email-writing" in error.context["available"]


# ============================================================================
# TEST: Error Context Enrichment
# ============================================================================

def test_error_adds_timestamp_automatically():
    """
    RED: All errors should automatically add timestamp.

    For debugging and log correlation.
    """


    error = VibeError(message="Test", code="TEST")

    result = error.to_dict()

    assert "timestamp" in result
    # Should be ISO format
    datetime.fromisoformat(result["timestamp"])


def test_error_includes_suggestion_when_provided():
    """
    RED: Errors can include helpful suggestions.

    EAFP principle: fail gracefully with helpful guidance.
    """


    error = MissingAPIKeyError()

    result = error.to_dict()

    assert "suggestion" in result
    assert "export EI_API_KEY" in result["suggestion"] or \
           "set EI_API_KEY" in result["suggestion"]


# ============================================================================
# TEST: Error Chaining
# ============================================================================

def test_error_can_wrap_original_exception():
    """
    RED: VibeError should support exception chaining.

    Preserves original traceback for debugging.
    """


    try:
        # Simulate original error
        msg = "Original error"
        raise ValueError(msg)
    except ValueError as e:
        vibe_error = VibeError(
            message="Wrapped error",
            code="WRAPPED",
            context={"original": str(e)},
        )

        assert vibe_error.context["original"] == "Original error"


# ============================================================================
# TEST: EAFP Pattern Helpers
# ============================================================================

def test_handle_error_decorator_catches_and_converts():
    """
    RED: @handle_error decorator should catch exceptions and convert to VibeError.

    EAFP: Try operation, catch errors gracefully.
    """


    @handle_error(error_code="OPERATION_FAILED")
    def risky_operation():
        msg = "Something went wrong"
        raise ValueError(msg)

    with pytest.raises(VibeError) as exc_info:
        risky_operation()

    assert exc_info.value.code == "OPERATION_FAILED"
    assert "Something went wrong" in str(exc_info.value)


# ============================================================================
# PROPERTY TESTS: Error Invariants
# ============================================================================

@pytest.mark.property
def test_vibe_error_invariants_with_random_inputs():
    """
    RED: Property test for VibeError invariants.

    No matter what inputs, certain properties must hold:
    1. to_dict() always returns dict
    2. to_json() always returns valid JSON
    3. exit_code is always 1 or 2
    4. timestamp is always present
    """




    @given(
        message=st.text(min_size=1, max_size=200),
        code=st.text(
            alphabet=st.characters(
                whitelist_categories=("Lu", "Ll", "Nd"),
                whitelist_characters="_",
            ),
            min_size=1,
            max_size=50,
        ),
        recoverable=st.booleans(),
    )
    def test_invariants(message, code, recoverable):
        error = VibeError(message=message, code=code, recoverable=recoverable)

        # Invariant 1: to_dict() returns dict
        result = error.to_dict()
        assert isinstance(result, dict)

        # Invariant 2: to_json() returns valid JSON
        json_str = error.to_json()
        parsed = json.loads(json_str)
        assert isinstance(parsed, dict)

        # Invariant 3: exit_code is 1 or 2
        assert error.exit_code in [1, 2]

        # Invariant 4: timestamp present
        assert "timestamp" in result

    test_invariants()


# ============================================================================
# TEST: Complete Coverage of All Error Classes
# ============================================================================


def test_configuration_error_without_code_prefix():
    """Test ConfigurationError adds CONFIG_ prefix when missing."""


    error = ConfigurationError(message="Test", code="MISSING_PREFIX")

    assert error.code == "CONFIG_MISSING_PREFIX"


def test_configuration_error_with_none_code():
    """Test ConfigurationError uses default code when None."""


    error = ConfigurationError(message="Test", code=None)

    assert error.code == "CONFIG_ERROR"


def test_config_file_not_found_error():
    """Test ConfigFileNotFoundError has correct attributes."""


    error = ConfigFileNotFoundError()

    assert error.code == "CONFIG_NOT_FOUND"
    assert "not found" in error.message.lower()
    assert error.recoverable is True


def test_config_file_not_found_error_with_custom_message():
    """Test ConfigFileNotFoundError with custom message."""


    error = ConfigFileNotFoundError(
        message="Custom not found",
        context={"path": "/test/config.yaml"},
    )

    assert error.message == "Custom not found"
    assert error.context["path"] == "/test/config.yaml"


def test_ai_service_error_without_code_prefix():
    """Test AIServiceError adds AI_ prefix when missing."""


    error = AIServiceError(message="Test", code="MISSING_PREFIX")

    assert error.code == "AI_MISSING_PREFIX"


def test_ai_service_error_with_none_code():
    """Test AIServiceError uses default code when None."""


    error = AIServiceError(message="Test", code=None)

    assert error.code == "AI_ERROR"


def test_rate_limit_error_with_custom_message():
    """Test RateLimitError with custom message."""


    error = RateLimitError(message="Custom rate limit message")

    assert error.message == "Custom rate limit message"


def test_rate_limit_error_with_context_retry_after():
    """Test RateLimitError uses retry_after from context."""


    error = RateLimitError(context={"retry_after": 120})

    assert "120" in error.message


def test_token_limit_error_with_custom_message():
    """Test TokenLimitError with custom message."""


    error = TokenLimitError(message="Custom token limit")

    assert error.message == "Custom token limit"


def test_token_limit_error_without_context():
    """Test TokenLimitError without context."""


    error = TokenLimitError()

    assert "Token limit exceeded" in error.message


def test_invalid_response_error():
    """Test InvalidResponseError."""


    error = InvalidResponseError()

    assert error.code == "AI_INVALID_RESPONSE"
    assert "invalid response" in error.message.lower()


def test_invalid_response_error_with_custom_message():
    """Test InvalidResponseError with custom message."""


    error = InvalidResponseError(message="Bad JSON", context={"response": "{bad}"})

    assert error.message == "Bad JSON"


def test_git_error_without_code_prefix():
    """Test GitError adds GIT_ prefix when missing."""


    error = GitError(message="Test", code="MISSING_PREFIX")

    assert error.code == "GIT_MISSING_PREFIX"


def test_git_error_with_none_code():
    """Test GitError uses default code when None."""


    error = GitError(message="Test", code=None)

    assert error.code == "GIT_ERROR"


def test_dirty_working_tree_error_with_custom_message():
    """Test DirtyWorkingTreeError with custom message."""


    error = DirtyWorkingTreeError(message="Custom dirty message")

    assert error.message == "Custom dirty message"


def test_dirty_working_tree_error_without_context():
    """Test DirtyWorkingTreeError without context."""


    error = DirtyWorkingTreeError()

    assert "uncommitted changes" in error.message.lower()


def test_dirty_working_tree_error_with_many_files():
    """Test DirtyWorkingTreeError shows only first 5 files."""


    many_files = [f"file{i}.py" for i in range(10)]
    error = DirtyWorkingTreeError(context={"files": many_files})

    assert "file0.py" in error.message
    assert "file4.py" in error.message
    assert "5 more" in error.message


def test_not_a_git_repo_error():
    """Test NotAGitRepoError."""


    error = NotAGitRepoError()

    assert error.code == "GIT_NOT_GIT_REPO"
    assert "not a git repository" in error.message.lower()


def test_not_a_git_repo_error_with_custom_message():
    """Test NotAGitRepoError with custom message."""

    error = NotAGitRepoError(
        message="No .git folder",
        context={"path": "/home/user/project"},
    )

    assert error.message == "No .git folder"


def test_template_error_without_code_prefix():
    """Test TemplateError adds TEMPLATE_ prefix when missing."""


    error = TemplateError(message="Test", code="MISSING_PREFIX")

    assert error.code == "TEMPLATE_MISSING_PREFIX"


def test_template_error_with_none_code():
    """Test TemplateError uses default code when None."""


    error = TemplateError(message="Test", code=None)

    assert error.code == "TEMPLATE_ERROR"


def test_template_not_found_error_with_custom_message():
    """Test TemplateNotFoundError with custom message."""


    error = TemplateNotFoundError(message="Custom not found")

    assert error.message == "Custom not found"


def test_template_not_found_error_without_context():
    """Test TemplateNotFoundError without context."""


    error = TemplateNotFoundError()

    assert "not found" in error.message.lower()


def test_template_syntax_error():
    """Test TemplateSyntaxError."""


    error = TemplateSyntaxError()

    assert error.code == "TEMPLATE_SYNTAX_ERROR"
    assert "syntax" in error.message.lower()


def test_template_syntax_error_with_custom_message():
    """Test TemplateSyntaxError with custom message."""


    error = TemplateSyntaxError(
        message="Bad template",
        context={"line": 10, "error": "Unclosed tag"},
    )

    assert error.message == "Bad template"


def test_iteration_error_without_code_prefix():
    """Test IterationError adds ITERATION_ prefix when missing."""


    error = IterationError(message="Test", code="MISSING_PREFIX")

    assert error.code == "ITERATION_MISSING_PREFIX"


def test_iteration_error_with_none_code():
    """Test IterationError uses default code when None."""


    error = IterationError(message="Test", code=None)

    assert error.code == "ITERATION_ERROR"


def test_iteration_log_corrupted_error():
    """Test IterationLogCorruptedError."""


    error = IterationLogCorruptedError()

    assert error.code == "ITERATION_LOG_CORRUPTED"
    assert "corrupted" in error.message.lower()


def test_iteration_log_corrupted_error_with_custom_message():
    """Test IterationLogCorruptedError with custom message."""


    error = IterationLogCorruptedError(
        message="Invalid JSON",
        context={"file": ".vibe/iterations.log"},
    )

    assert error.message == "Invalid JSON"


def test_validation_error_without_code_prefix():
    """Test ValidationError adds VALIDATION_ prefix when missing."""


    error = ValidationError(message="Test", code="MISSING_PREFIX")

    assert error.code == "VALIDATION_MISSING_PREFIX"


def test_validation_error_with_none_code():
    """Test ValidationError uses default code when None."""


    error = ValidationError(message="Test", code=None)

    assert error.code == "VALIDATION_ERROR"


def test_vibe_error_str_without_suggestion():
    """Test VibeError __str__ when no suggestion provided."""


    error = VibeError(message="Test error", code="TEST", suggestion=None)

    result = str(error)

    assert "[TEST]" in result
    assert "Test error" in result
    assert "Suggestion:" not in result


def test_vibe_error_to_dict_without_suggestion():
    """Test VibeError to_dict when no suggestion provided."""


    error = VibeError(message="Test", code="TEST", suggestion=None)

    result = error.to_dict()

    assert "suggestion" not in result
