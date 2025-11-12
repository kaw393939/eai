"""
Pytest configuration and shared fixtures.

This file is automatically loaded by pytest and provides fixtures
available to all tests.
"""
from datetime import UTC
from pathlib import Path
from unittest.mock import Mock

import pytest

# ============================================================================
# DIRECTORY FIXTURES
# ============================================================================

@pytest.fixture()
def tmp_project(tmp_path: Path) -> Path:
    """
    Create a temporary project directory with vibe structure.

    Structure:
        tmp_project/
            .vibe/
                config.yaml
                iterations.log

    Returns:
        Path to temporary project directory
    """
    project = tmp_path / "project"
    project.mkdir()

    # Create .vibe directory
    vibe_dir = project / ".vibe"
    vibe_dir.mkdir()

    # Create empty config
    (vibe_dir / "config.yaml").write_text("# Vibe config\n")

    # Create empty iteration log
    (vibe_dir / "iterations.log").write_text("[]")

    return project


@pytest.fixture()
def tmp_git_repo(tmp_path: Path) -> Path:
    """
    Create a temporary git repository.

    Returns:
        Path to temporary git repo
    """
    import git

    repo_path = tmp_path / "git_repo"
    repo_path.mkdir()

    repo = git.Repo.init(repo_path)

    # Initial commit
    (repo_path / "README.md").write_text("# Test Repo")
    repo.index.add(["README.md"])
    repo.index.commit("Initial commit")

    return repo_path


# ============================================================================
# MOCK SERVICE FIXTURES
# ============================================================================

@pytest.fixture()
def mock_logger():
    """Mock structured logger."""
    from structlog.testing import CapturingLogger
    return CapturingLogger()


@pytest.fixture()
def mock_ai_service():
    """
    Mock AI service with common responses.

    Default behavior:
        - generate() returns "Generated content"
        - Can be customized per test
    """
    mock = Mock()
    mock.generate.return_value = "Generated content"
    mock.estimate_tokens.return_value = 100
    return mock


@pytest.fixture()
def mock_git_service():
    """
    Mock Git service with common operations.

    Default behavior:
        - commit() returns commit hash
        - is_repo() returns True
        - Can be customized per test
    """
    mock = Mock()
    mock.commit.return_value = "abc123def456"
    mock.is_repo.return_value = True
    mock.is_dirty.return_value = False
    return mock


@pytest.fixture()
def mock_template_service():
    """
    Mock Template service with common operations.

    Default behavior:
        - list_templates() returns test templates
        - load_template() returns template content
        - Can be customized per test
    """
    mock = Mock()
    mock.list_templates.return_value = [
        "email-writing",
        "lesson-plans",
        "simple-website",
    ]
    mock.load_template.return_value = "# Template content"
    return mock


@pytest.fixture()
def mock_iteration_service():
    """
    Mock Iteration service.

    Default behavior:
        - create_iteration() returns iteration object
        - Can be customized per test
    """
    mock = Mock()
    mock.create_iteration.return_value = {
        "id": "iter_abc123",
        "prompt": "Test prompt",
        "result": "Test result",
        "timestamp": "2025-11-07T10:30:00Z",
    }
    return mock


# ============================================================================
# DI CONTAINER FIXTURES
# ============================================================================

@pytest.fixture()
def mock_container(
    mock_logger,
    mock_ai_service,
    mock_git_service,
    mock_template_service,
    mock_iteration_service,
):
    """
    DI container with all services mocked.

    Usage:
        def test_something(mock_container):
            # All services are mocked
            container = mock_container
            service = container.iteration_service()
    """
    from vibe_cli.cli.container import Container

    container = Container()

    # Override with mocks
    container.logger.override(lambda: mock_logger)
    container.ai_service.override(lambda: mock_ai_service)
    container.git_service.override(lambda: mock_git_service)
    container.template_service.override(lambda: mock_template_service)
    container.iteration_service.override(lambda: mock_iteration_service)

    return container


# ============================================================================
# CLI TESTING FIXTURES
# ============================================================================

@pytest.fixture()
def cli_runner():
    """
    Click CLI test runner.

    Usage:
        def test_command(cli_runner):
            result = cli_runner.invoke(cli, ['command', '--arg'])
            assert result.exit_code == 0
    """
    from click.testing import CliRunner
    return CliRunner()


@pytest.fixture()
def isolated_cli_runner():
    """
    Click CLI test runner with isolated filesystem.

    Automatically creates temporary directory and changes to it.

    Usage:
        def test_command(isolated_cli_runner):
            with isolated_cli_runner.isolated_filesystem():
                result = isolated_cli_runner.invoke(cli, ['init'])
                assert Path('.vibe').exists()
    """
    from click.testing import CliRunner
    return CliRunner()


# ============================================================================
# DATA FACTORIES
# ============================================================================

@pytest.fixture()
def error_factory():
    """
    Factory for creating test errors.

    Usage:
        def test_error(error_factory):
            error = error_factory(code="TEST_ERROR")
            assert error.code == "TEST_ERROR"
    """
    from vibe_cli.core.errors import VibeError

    def _create_error(**kwargs):
        defaults = {
            "message": "Test error",
            "code": "TEST_ERROR",
            "recoverable": True,
        }
        defaults.update(kwargs)
        return VibeError(**defaults)

    return _create_error


@pytest.fixture()
def iteration_factory():
    """
    Factory for creating test iterations.

    Usage:
        def test_iteration(iteration_factory):
            iteration = iteration_factory(prompt="Custom prompt")
            assert iteration["prompt"] == "Custom prompt"
    """
    import uuid
    from datetime import datetime

    def _create_iteration(**kwargs):
        defaults = {
            "id": f"iter_{uuid.uuid4().hex[:12]}",
            "prompt": "Test prompt",
            "result": "Test result",
            "timestamp": datetime.now(UTC).isoformat(),
            "tokens": 100,
            "model": "gpt-4",
        }
        defaults.update(kwargs)
        return defaults

    return _create_iteration


# ============================================================================
# ENVIRONMENT FIXTURES
# ============================================================================

@pytest.fixture()
def clean_env(monkeypatch):
    """
    Clean environment (no VIBE_ variables).

    Usage:
        def test_with_clean_env(clean_env):
            # No VIBE_* env vars set
            pass
    """
    # Remove all VIBE_ environment variables
    import os
    for key in list(os.environ.keys()):
        if key.startswith("VIBE_"):
            monkeypatch.delenv(key, raising=False)

    return monkeypatch


@pytest.fixture()
def mock_env(monkeypatch):
    """
    Mock environment with common VIBE_ variables.

    Usage:
        def test_with_mock_env(mock_env):
            # VIBE_API_KEY is set
            assert os.environ["VIBE_API_KEY"] == "test-key"
    """
    monkeypatch.setenv("VIBE_API_KEY", "test-api-key-12345")
    monkeypatch.setenv("VIBE_MODEL", "gpt-4")
    monkeypatch.setenv("VIBE_DEBUG", "false")

    return monkeypatch


# ============================================================================
# HYPOTHESIS STRATEGIES
# ============================================================================

@pytest.fixture()
def hypothesis_strategies():
    """
    Common Hypothesis strategies for property testing.

    Usage:
        def test_property(hypothesis_strategies):
            st = hypothesis_strategies
            @given(st.error_codes)
            def test(code):
                assert len(code) > 0
    """
    from hypothesis import strategies as st

    return {
        "error_codes": st.text(
            alphabet=st.characters(blacklist_categories=("Cs",)),
            min_size=1,
            max_size=50,
        ),
        "prompts": st.text(min_size=1, max_size=1000),
        "file_paths": st.text(
            alphabet="abcdefghijklmnopqrstuvwxyz0123456789-_./",
            min_size=1,
            max_size=100,
        ),
    }


# ============================================================================
# MARKERS
# ============================================================================

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "unit: Unit tests (fast, isolated)",
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests (slower, external deps)",
    )
    config.addinivalue_line(
        "markers", "e2e: End-to-end tests (slow, full scenarios)",
    )
    config.addinivalue_line(
        "markers", "property: Property-based tests (hypothesis)",
    )
    config.addinivalue_line(
        "markers", "slow: Slow tests (>1s)",
    )
    config.addinivalue_line(
        "markers", "ai: Tests requiring AI API (OpenAI)",
    )
    config.addinivalue_line(
        "markers", "git: Tests requiring git",
    )


# ============================================================================
# HOOKS
# ============================================================================

def pytest_collection_modifyitems(config, items):
    """
    Automatically add markers based on test location.

    - tests/python/unit/ → @pytest.mark.unit
    - tests/python/integration/ → @pytest.mark.integration
    - tests/python/e2e/ → @pytest.mark.e2e
    - tests/python/property/ → @pytest.mark.property
    """
    for item in items:
        test_path = str(item.fspath)

        if "/unit/" in test_path:
            item.add_marker(pytest.mark.unit)
        elif "/integration/" in test_path:
            item.add_marker(pytest.mark.integration)
        elif "/e2e/" in test_path:
            item.add_marker(pytest.mark.e2e)
        elif "/property/" in test_path:
            item.add_marker(pytest.mark.property)
