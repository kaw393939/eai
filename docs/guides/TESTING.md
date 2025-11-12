# Vibe CLI Testing Strategy

## Overview

This document outlines the comprehensive testing strategy for the Vibe CLI
project, following Test-Driven Development (TDD) principles.

## Testing Philosophy

### 1. TDD Workflow (Red-Green-Refactor)

```
RED: Write failing test first
  ↓
GREEN: Write minimal code to pass
  ↓
REFACTOR: Clean up code
  ↓
REPEAT
```

### 2. Test Pyramid

```
         ┌─────────────┐
         │  E2E (5%)   │  Full CLI scenarios
         └──────┬──────┘
            ┌───▼────────────┐
            │ Integration    │  Service + deps (15%)
            └───┬────────────┘
         ┌──────▼───────────────┐
         │   Unit (80%)         │  Individual functions
         └──────────────────────┘
```

## Test Categories

### Unit Tests (80%)

**Location:** `tests/python/unit/`

**Characteristics:**

- Fast (<1ms per test)
- Isolated (all dependencies mocked)
- High coverage (>95%)
- Test one thing at a time

**Example:**

```python
def test_vibe_error_to_dict():
    """Test VibeError.to_dict() returns correct structure."""
    error = VibeError(
        message="Test error",
        code="TEST_ERROR",
        details={"key": "value"},
        suggestion="Try this",
        recoverable=True
    )

    result = error.to_dict()

    assert result["error"]["type"] == "VibeError"
    assert result["error"]["code"] == "TEST_ERROR"
    assert result["error"]["message"] == "Test error"
    assert result["error"]["details"] == {"key": "value"}
    assert result["error"]["suggestion"] == "Try this"
    assert result["error"]["recoverable"] is True
```

### Integration Tests (15%)

**Location:** `tests/python/integration/`

**Characteristics:**

- Medium speed (<100ms per test)
- Real filesystem, git
- Mocked external APIs (OpenAI)
- Test component interactions

**Example:**

```python
def test_iteration_service_with_git(tmp_path):
    """Test IterationService creates iteration and commits to git."""
    # Setup real git repo
    repo = git.Repo.init(tmp_path)

    # Mock AI service
    mock_ai = Mock()
    mock_ai.generate.return_value = "Generated content"

    # Real git service
    git_service = GitService(logger=get_logger())

    # Create iteration service
    service = IterationService(
        ai_service=mock_ai,
        git_service=git_service,
        logger=get_logger()
    )

    # Execute
    iteration = service.create_iteration(
        prompt="Test prompt",
        working_dir=tmp_path
    )

    # Verify
    assert iteration.id is not None
    assert (tmp_path / ".vibe" / "iterations.log").exists()

    # Verify git commit
    commits = list(repo.iter_commits())
    assert len(commits) == 1
    assert "iteration" in commits[0].message.lower()
```

### E2E Tests (5%)

**Location:** `tests/python/e2e/`

**Characteristics:**

- Slow (>1s per test)
- Full CLI execution
- Real external services
- Critical flows only

**Example:**

```python
def test_full_vibe_init_iterate_workflow(tmp_path, monkeypatch):
    """Test complete workflow: init → iterate → log."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    # Run: vibe init
    result = runner.invoke(cli, ["init", "--template", "email-writing"])
    assert result.exit_code == 0
    assert (tmp_path / ".vibe").exists()

    # Run: vibe iterate
    result = runner.invoke(
        cli,
        ["iterate", "--prompt", "Write a professional email"]
    )
    assert result.exit_code == 0
    assert "iteration" in result.output.lower()

    # Run: vibe log
    result = runner.invoke(cli, ["log"])
    assert result.exit_code == 0
    assert "1 iteration" in result.output.lower()
```

### Property Tests (Hypothesis)

**Location:** `tests/python/property/`

**Characteristics:**

- Generate random inputs
- Find edge cases automatically
- Test invariants

**Example:**

```python
from hypothesis import given, strategies as st

@given(
    message=st.text(min_size=1, max_size=1000),
    code=st.text(min_size=1, max_size=50),
    recoverable=st.booleans()
)
def test_vibe_error_invariants(message, code, recoverable):
    """Test VibeError invariants with random inputs."""
    error = VibeError(
        message=message,
        code=code,
        recoverable=recoverable
    )

    # Invariants
    assert error.message == message
    assert error.code == code
    assert error.recoverable == recoverable
    assert isinstance(error.to_dict(), dict)
    assert "error" in error.to_dict()
    assert error.to_json() is not None
```

## Test Organization

### File Naming

- **Unit tests:** `test_<module>.py`
- **Integration tests:** `test_<feature>_integration.py`
- **E2E tests:** `test_<scenario>_e2e.py`
- **Property tests:** `test_<property>_properties.py`

### Test Function Naming

```python
def test_<function>_<scenario>_<expected_result>():
    """Descriptive docstring explaining test purpose."""
    # Arrange
    # Act
    # Assert
```

Examples:

- `test_vibe_error_to_dict_returns_correct_structure()`
- `test_ai_service_generate_raises_error_on_invalid_api_key()`
- `test_iterate_command_handles_rate_limit_with_retry()`

## Fixtures (`conftest.py`)

### Common Fixtures

```python
import pytest
from pathlib import Path
from unittest.mock import Mock
from vibe_cli.cli.container import Container
from vibe_cli.core.logger import get_logger

@pytest.fixture
def mock_logger():
    """Mock logger for testing."""
    return Mock(spec=get_logger())

@pytest.fixture
def tmp_project(tmp_path):
    """Create temporary project structure."""
    project = tmp_path / "project"
    project.mkdir()
    (project / ".vibe").mkdir()
    (project / ".vibe" / "iterations.log").write_text("[]")
    return project

@pytest.fixture
def mock_ai_service():
    """Mock AI service."""
    mock = Mock()
    mock.generate.return_value = "Generated content"
    return mock

@pytest.fixture
def mock_git_service():
    """Mock Git service."""
    mock = Mock()
    mock.commit.return_value = "abc123"
    return mock

@pytest.fixture
def container_with_mocks(mock_ai_service, mock_git_service, mock_logger):
    """DI container with mocked services."""
    container = Container()
    container.ai_service.override(mock_ai_service)
    container.git_service.override(mock_git_service)
    container.logger.override(mock_logger)
    return container

@pytest.fixture
def cli_runner():
    """Click CLI test runner."""
    from click.testing import CliRunner
    return CliRunner()
```

## Running Tests

### All Tests

```bash
poetry run pytest
```

### By Category

```bash
# Unit tests only (fast)
poetry run pytest tests/python/unit/ -v

# Integration tests
poetry run pytest tests/python/integration/ -v

# E2E tests (slow)
poetry run pytest tests/python/e2e/ -v

# Property tests
poetry run pytest tests/python/property/ -v
```

### By Marker

```bash
# Fast tests only
poetry run pytest -m "not slow"

# Tests requiring AI
poetry run pytest -m ai

# Tests requiring git
poetry run pytest -m git
```

### With Coverage

```bash
# Full coverage report
poetry run pytest --cov=src/vibe_cli --cov-report=html

# Open HTML report
open htmlcov/index.html
```

### Parallel Execution

```bash
# Run tests in parallel (faster)
poetry run pytest -n auto
```

## Coverage Requirements

### Thresholds

| Component | Minimum Coverage |
| --------- | ---------------- |
| Overall   | 90%              |
| Core      | 95%              |
| Services  | 90%              |
| Commands  | 85%              |
| Utils     | 95%              |

### Exclusions

Lines excluded from coverage:

- `pragma: no cover`
- `def __repr__`
- `if TYPE_CHECKING:`
- `raise AssertionError`
- `raise NotImplementedError`
- `if __name__ == .__main__.:`
- `@abstractmethod`

## Mocking Strategy

### What to Mock

✅ **Always Mock:**

- External APIs (OpenAI, GitHub)
- Network calls
- System time
- Random number generation
- Environment variables (sometimes)

✅ **Sometimes Mock:**

- Filesystem (unit tests)
- Git operations (unit tests)
- Logger (when testing log messages)

❌ **Never Mock:**

- Pure functions
- Data classes
- The system under test itself

### Mocking Patterns

**1. Mock with return value:**

```python
mock_service.method.return_value = "expected result"
```

**2. Mock with side effect:**

```python
mock_service.method.side_effect = ValueError("Error")
```

**3. Mock with multiple calls:**

```python
mock_service.method.side_effect = ["first", "second", "third"]
```

**4. Verify calls:**

```python
mock_service.method.assert_called_once_with(arg1, arg2)
mock_service.method.assert_called_with(arg1, arg2)
mock_service.method.assert_not_called()
```

## Test Data

### Fixtures vs Factories

**Fixtures:** For simple, reusable test data

```python
@pytest.fixture
def sample_error():
    return VibeError(message="Test", code="TEST")
```

**Factories:** For complex, customizable test data

```python
from faker import Faker

fake = Faker()

def create_iteration(**kwargs):
    """Factory for creating test iterations."""
    defaults = {
        "id": fake.uuid4(),
        "prompt": fake.sentence(),
        "result": fake.text(),
        "timestamp": fake.date_time(),
    }
    defaults.update(kwargs)
    return Iteration(**defaults)
```

## Parameterized Tests

```python
@pytest.mark.parametrize(
    "input,expected",
    [
        ("test", "TEST"),
        ("hello", "HELLO"),
        ("", ""),
        ("123", "123"),
    ]
)
def test_uppercase(input, expected):
    """Test uppercase function with various inputs."""
    assert uppercase(input) == expected
```

## Async Tests

```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    """Test async function."""
    result = await async_function()
    assert result == "expected"
```

## Snapshot Testing (Optional)

For testing complex output structures:

```python
def test_error_output(snapshot):
    """Test error output matches snapshot."""
    error = VibeError(message="Test", code="TEST")
    snapshot.assert_match(error.to_dict())
```

## Test Isolation

### Rules

1. **No shared state between tests**
2. **Each test creates its own data**
3. **Clean up after tests** (fixtures with yield)
4. **Use tmp_path for filesystem tests**
5. **Mock external services**

### Example

```python
@pytest.fixture
def temp_project(tmp_path):
    """Create and cleanup temporary project."""
    project = tmp_path / "project"
    project.mkdir()

    yield project

    # Cleanup (pytest handles tmp_path cleanup)
```

## TDD Checklist

For each feature:

- [ ] Write architecture doc section
- [ ] Define error cases
- [ ] Write failing tests (RED)
- [ ] Implement minimal code (GREEN)
- [ ] Refactor for quality (REFACTOR)
- [ ] Verify coverage >90%
- [ ] Run quality gates (ruff, mypy, bandit)
- [ ] Update documentation
- [ ] Create PR

## CI/CD Integration

Tests run automatically on:

- Every push
- Every pull request
- Before merge to main
- Before release

Pipeline stages:

1. Linting (ruff)
2. Type checking (mypy)
3. Security (bandit, safety)
4. Unit tests
5. Integration tests
6. E2E tests (optional, slow)
7. Coverage check (>90%)

## Performance Benchmarks

### Target Times

| Test Type   | Target | Max  |
| ----------- | ------ | ---- |
| Unit        | <1ms   | 10ms |
| Integration | <100ms | 1s   |
| E2E         | <5s    | 30s  |
| Full Suite  | <30s   | 5min |

### Monitoring

Use pytest-benchmark for tracking:

```bash
poetry run pytest --benchmark-only
```

## Debugging Tests

### Failed Tests

```bash
# Show print statements
poetry run pytest -s

# Stop on first failure
poetry run pytest -x

# Drop into debugger on failure
poetry run pytest --pdb
```

### Slow Tests

```bash
# Show slowest 10 tests
poetry run pytest --durations=10

# Show tests slower than 1s
poetry run pytest --durations-min=1.0
```

## Documentation

Each test should have:

1. **Descriptive name**
2. **Docstring** explaining purpose
3. **Clear AAA structure** (Arrange, Act, Assert)
4. **Meaningful assertions**

Example:

```python
def test_error_includes_suggestion_when_provided():
    """Test that VibeError includes suggestion in dict when provided.

    This ensures AI agents receive helpful recovery suggestions.
    """
    # Arrange
    error = VibeError(
        message="Test error",
        code="TEST",
        suggestion="Try this fix"
    )

    # Act
    result = error.to_dict()

    # Assert
    assert result["error"]["suggestion"] == "Try this fix"
```

---

**Last Updated:** 2025-11-07  
**Next Review:** 2025-11-14
