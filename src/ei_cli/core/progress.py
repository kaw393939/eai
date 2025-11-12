"""Progress indicators for CLI operations."""

from collections.abc import Generator
from contextlib import contextmanager

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn


@contextmanager
def spinner(
    message: str, console: Console | None = None,
) -> Generator[None, None, None]:
    """
    Show a spinner for long-running operations.
    
    Args:
        message: Message to display
        console: Optional Rich console instance
        
    Example:
        with spinner("Processing audio..."):
            # Do work
            pass
    """
    _console = console or Console()

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        TimeElapsedColumn(),
        console=_console,
        transient=True,
    ) as progress:
        progress.add_task(message)
        yield


@contextmanager
def progress_bar(
    total: int,
    message: str = "Processing",
    console: Console | None = None,
) -> Generator[Progress, None, None]:
    """
    Show a progress bar with completion tracking.
    
    Args:
        total: Total number of items to process
        message: Message to display
        console: Optional Rich console instance
        
    Yields:
        Progress instance to update
        
    Example:
        with progress_bar(100, "Processing items") as progress:
            task = progress.add_task("Working...", total=100)
            for i in range(100):
                progress.update(task, advance=1)
    """
    _console = console or Console()

    with Progress(
        TextColumn("[bold blue]{task.description}"),
        SpinnerColumn(),
        *Progress.get_default_columns(),
        console=_console,
    ) as progress:
        yield progress
