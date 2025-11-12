"""Tests for workflow parallel execution."""

import asyncio
from unittest.mock import patch

import pytest

from ei_cli.workflow.parallel import ParallelExecutor, run_parallel, run_parallel_async


class TestParallelExecutor:
    """Tests for ParallelExecutor class."""

    def test_init_default(self):
        """Test default initialization."""
        executor = ParallelExecutor()
        assert executor.max_workers == 3

    def test_init_custom(self):
        """Test custom initialization."""
        executor = ParallelExecutor(max_workers=5)
        assert executor.max_workers == 5

    @pytest.mark.asyncio
    async def test_run_parallel_async_success(self):
        """Test async parallel execution with all successful tasks."""
        async def task1():
            await asyncio.sleep(0.01)
            return "result1"

        async def task2():
            await asyncio.sleep(0.01)
            return "result2"

        async def task3():
            await asyncio.sleep(0.01)
            return "result3"

        executor = ParallelExecutor()
        results = await executor.run_parallel_async(
            tasks=[task1, task2, task3],
            descriptions=["Task 1", "Task 2", "Task 3"],
        )

        assert len(results) == 3
        assert "result1" in results
        assert "result2" in results
        assert "result3" in results

    @pytest.mark.asyncio
    async def test_run_parallel_async_with_errors(self):
        """Test async execution with some tasks failing."""
        async def task1():
            await asyncio.sleep(0.01)
            return "result1"

        async def task2():
            await asyncio.sleep(0.01)
            msg = "Task 2 failed"
            raise ValueError(msg)

        async def task3():
            await asyncio.sleep(0.01)
            return "result3"

        executor = ParallelExecutor()
        results = await executor.run_parallel_async(
            tasks=[task1, task2, task3],
            descriptions=["Task 1", "Task 2", "Task 3"],
        )

        # Should have 3 results (2 successes, 1 exception)
        assert len(results) == 3

        # Check successful results
        assert "result1" in results
        assert "result3" in results

        # Check error is captured
        assert any(isinstance(r, ValueError) for r in results)

    def test_run_parallel_sync_success(self):
        """Test sync parallel execution with all successful tasks."""
        def task1():
            return "result1"

        def task2():
            return "result2"

        def task3():
            return "result3"

        executor = ParallelExecutor(max_workers=3)
        results = executor.run_parallel_sync(
            tasks=[task1, task2, task3],
            descriptions=["Task 1", "Task 2", "Task 3"],
        )

        assert len(results) == 3
        assert "result1" in results
        assert "result2" in results
        assert "result3" in results

    def test_run_parallel_sync_with_errors(self):
        """Test sync execution with some tasks failing."""
        def task1():
            return "result1"

        def task2():
            msg = "Task 2 failed"
            raise ValueError(msg)

        def task3():
            return "result3"

        executor = ParallelExecutor()
        results = executor.run_parallel_sync(
            tasks=[task1, task2, task3],
            descriptions=["Task 1", "Task 2", "Task 3"],
        )

        # Should have 3 results
        assert len(results) == 3

        # Check successful results
        assert "result1" in results
        assert "result3" in results

        # Check error is captured
        assert any(isinstance(r, ValueError) for r in results)

    def test_filter_results_success_only(self):
        """Test filtering to get only successful results."""
        results = ["result1", ValueError("error"), "result3"]

        executor = ParallelExecutor()
        filtered = executor.filter_results(results, raise_errors=False)

        assert len(filtered) == 2
        assert "result1" in filtered
        assert "result3" in filtered

    def test_filter_results_with_raise(self):
        """Test filtering with raise_errors=True."""
        results = ["result1", ValueError("error"), "result3"]

        executor = ParallelExecutor()

        with pytest.raises(ValueError, match="error"):
            executor.filter_results(results, raise_errors=True)

    def test_get_errors(self):
        """Test extracting errors from results."""
        results = ["result1", ValueError("error1"), "result3", RuntimeError("error2")]

        executor = ParallelExecutor()
        errors = executor.get_errors(results)

        assert len(errors) == 2
        assert any(isinstance(e, ValueError) for e in errors)
        assert any(isinstance(e, RuntimeError) for e in errors)

    @patch("ei_cli.workflow.parallel.console")
    def test_print_summary(self, mock_console):
        """Test printing execution summary."""
        results = ["result1", ValueError("error"), "result3"]
        descriptions = ["Task 1", "Task 2", "Task 3"]

        executor = ParallelExecutor()
        executor.print_summary(results, descriptions)

        # Should print success and failure counts
        assert mock_console.print.call_count >= 2

    def test_convenience_function_sync(self):
        """Test run_parallel convenience function."""
        def task1():
            return "result1"

        def task2():
            return "result2"

        results = run_parallel(
            (task1, "Task 1"),
            (task2, "Task 2"),
        )

        assert len(results) == 2
        assert "result1" in results
        assert "result2" in results

    @pytest.mark.asyncio
    async def test_convenience_function_async(self):
        """Test run_parallel_async convenience function."""
        async def task1():
            return "result1"

        async def task2():
            return "result2"

        results = await run_parallel_async(
            (task1, "Task 1"),
            (task2, "Task 2"),
        )

        assert len(results) == 2
        assert "result1" in results
        assert "result2" in results

    def test_empty_tasks(self):
        """Test with empty task list."""
        executor = ParallelExecutor()
        results = executor.run_parallel_sync(tasks=[], descriptions=[])

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_empty_tasks_async(self):
        """Test async execution with empty task list."""
        executor = ParallelExecutor()
        results = await executor.run_parallel_async(
            tasks=[],
            descriptions=[],
        )

        assert len(results) == 0
