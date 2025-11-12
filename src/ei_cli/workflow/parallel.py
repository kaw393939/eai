"""Parallel execution for independent tasks."""

import asyncio
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TaskID, TextColumn, TimeElapsedColumn

console = Console()


class ParallelExecutor:
    """Execute independent tasks in parallel with progress tracking."""

    def __init__(self, max_workers: int = 3) -> None:
        """
        Initialize parallel executor.

        Args:
            max_workers: Maximum number of parallel workers (default: 3)
        """
        self.max_workers = max_workers

    async def run_parallel_async(
        self,
        tasks: list[Callable],
        descriptions: list[str],
    ) -> list[Any]:
        """
        Run multiple async tasks in parallel with progress.

        Args:
            tasks: List of async callable functions
            descriptions: List of descriptions for each task

        Returns:
            List of results (or exceptions if tasks failed)
        """
        if len(tasks) != len(descriptions):
            raise ValueError("Number of tasks must match number of descriptions")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            # Create progress tasks
            task_ids = [
                progress.add_task(desc, total=None) for desc in descriptions
            ]

            # Run tasks in parallel
            results = await asyncio.gather(
                *[
                    self._run_async_task(task, progress, task_id)
                    for task, task_id in zip(tasks, task_ids, strict=False)
                ],
                return_exceptions=True,
            )

            # Update final status
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    progress.update(
                        task_ids[i],
                        description=f"[red]✗ {descriptions[i]}[/red]",
                    )
                else:
                    progress.update(
                        task_ids[i],
                        description=f"[green]✓ {descriptions[i]}[/green]",
                    )

            return results

    async def _run_async_task(
        self,
        task: Callable,
        progress: Progress,
        task_id: TaskID,
    ) -> Any:
        """
        Run single async task with progress update.

        Args:
            task: Async callable to execute
            progress: Progress instance
            task_id: Task ID for progress updates

        Returns:
            Task result or raises exception
        """
        try:
            result = await task()
            return result
        except Exception as e:
            # Return exception instead of raising so other tasks continue
            return e

    def run_parallel_sync(
        self,
        tasks: list[Callable],
        descriptions: list[str],
    ) -> list[Any]:
        """
        Run multiple sync tasks in parallel using threads.

        Args:
            tasks: List of callable functions
            descriptions: List of descriptions for each task

        Returns:
            List of results (or exceptions if tasks failed)
        """
        if len(tasks) != len(descriptions):
            raise ValueError("Number of tasks must match number of descriptions")

        results = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            # Create progress tasks
            task_ids = [
                progress.add_task(desc, total=None) for desc in descriptions
            ]

            # Run tasks in thread pool
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = [
                    executor.submit(self._run_sync_task, task, progress, task_id)
                    for task, task_id in zip(tasks, task_ids, strict=False)
                ]

                # Collect results
                for i, future in enumerate(futures):
                    try:
                        result = future.result()
                        results.append(result)
                        progress.update(
                            task_ids[i],
                            description=f"[green]✓ {descriptions[i]}[/green]",
                        )
                    except Exception as e:
                        results.append(e)
                        progress.update(
                            task_ids[i],
                            description=f"[red]✗ {descriptions[i]}[/red]",
                        )

        return results

    def _run_sync_task(
        self,
        task: Callable,
        progress: Progress,
        task_id: TaskID,
    ) -> Any:
        """
        Run single sync task.

        Args:
            task: Callable to execute
            progress: Progress instance
            task_id: Task ID for progress updates

        Returns:
            Task result or raises exception
        """
        return task()

    def filter_results(
        self,
        results: list[Any],
        raise_errors: bool = False,
    ) -> list[Any]:
        """
        Filter out exceptions from results.

        Args:
            results: List of results from parallel execution
            raise_errors: If True, raise first exception found

        Returns:
            List of successful results only
        """
        if raise_errors:
            for result in results:
                if isinstance(result, Exception):
                    raise result

        return [r for r in results if not isinstance(r, Exception)]

    def get_errors(self, results: list[Any]) -> list[Exception]:
        """
        Extract exceptions from results.

        Args:
            results: List of results from parallel execution

        Returns:
            List of exceptions that occurred
        """
        return [r for r in results if isinstance(r, Exception)]

    def print_summary(
        self,
        results: list[Any],
        descriptions: list[str],
    ) -> None:
        """
        Print summary of parallel execution.

        Args:
            results: List of results from parallel execution
            descriptions: Original task descriptions
        """
        successful = len(self.filter_results(results))
        failed = len(self.get_errors(results))

        console.print("\n[bold]Parallel Execution Summary:[/bold]")
        console.print(f"  [green]Successful: {successful}[/green]")
        if failed > 0:
            console.print(f"  [red]Failed: {failed}[/red]")

            # Show which tasks failed
            console.print("\n[yellow]Failed tasks:[/yellow]")
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    console.print(f"  • {descriptions[i]}: {result}")

    def __repr__(self) -> str:
        """Return string representation."""
        return f"ParallelExecutor(max_workers={self.max_workers})"


# Convenience functions for common use cases

def run_parallel(*tasks_and_descriptions: tuple[Callable, str]) -> list[Any]:
    """
    Convenient way to run parallel tasks.

    Args:
        *tasks_and_descriptions: Tuples of (task, description)

    Returns:
        List of results

    Example:
        results = run_parallel(
            (lambda: fetch_url("https://example.com"), "Fetch example.com"),
            (lambda: fetch_url("https://example.org"), "Fetch example.org"),
        )
    """
    executor = ParallelExecutor()
    tasks = [t[0] for t in tasks_and_descriptions]
    descriptions = [t[1] for t in tasks_and_descriptions]

    return executor.run_parallel_sync(tasks, descriptions)


async def run_parallel_async(*tasks_and_descriptions: tuple[Callable, str]) -> list[Any]:
    """
    Convenient way to run parallel async tasks.

    Args:
        *tasks_and_descriptions: Tuples of (async_task, description)

    Returns:
        List of results

    Example:
        results = await run_parallel_async(
            (async_fetch("https://example.com"), "Fetch example.com"),
            (async_fetch("https://example.org"), "Fetch example.org"),
        )
    """
    executor = ParallelExecutor()
    tasks = [t[0] for t in tasks_and_descriptions]
    descriptions = [t[1] for t in tasks_and_descriptions]

    return await executor.run_parallel_async(tasks, descriptions)
