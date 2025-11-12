"""
Background removal command for ei CLI.

Provides background removal functionality for images.
"""

import click
from click.exceptions import Exit
from rich.console import Console
from rich.panel import Panel

from ei_cli.services.base import ServiceError
from ei_cli.services.factory import ServiceFactory
from ei_cli.services.image_service import RemoveBgResult


def _handle_tool_unavailable(  # pragma: no cover
    console: Console,
    error: str | None,
) -> None:
    """Handle when background removal tool is unavailable."""
    console.print(
        f"[red]✗[/red] Background removal tool not available: {error}",
    )
    console.print(
        "\n[yellow]Tip:[/yellow] Install required dependencies:",
    )
    console.print("  pip install pillow numpy")
    raise Exit(1) from None


def _display_result(
    console: Console,
    result: RemoveBgResult,
) -> None:
    """Display background removal result."""
    console.print()

    display_text = (
        f"[bold cyan]Background Removed Successfully![/bold cyan]\n\n"
        f"[green]Input:[/green] {result.input_path}\n"
        f"[green]Output:[/green] {result.output_path}\n"
        f"[dim]Method:[/dim] {result.method_used}\n"
        f"[dim]Message:[/dim] {result.message}"
    )

    console.print(Panel(
        display_text,
        title="✨ Background Removal Result",
        border_style="green",
    ))


def _display_json_output(
    console: Console,
    result: RemoveBgResult,
) -> None:
    """Display result as JSON."""
    output = {
        "input_path": result.input_path,
        "output_path": result.output_path,
        "method_used": result.method_used,
        "success": result.success,
        "message": result.message,
    }
    console.print_json(data=output)


@click.command()
@click.argument("input_path", required=True, type=click.Path(exists=True))
@click.option(
    "--output",
    "-o",
    "output_path",
    type=click.Path(),
    help="Output path for processed image (default: <input>_no_bg.png)",
)
@click.option(
    "--tolerance",
    "-t",
    default=30,
    type=click.IntRange(0, 255),
    help="Color tolerance for background detection (0-255, default: 30)",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output results as JSON",
)
def remove_bg(
    input_path: str,
    output_path: str | None,
    tolerance: int,
    output_json: bool,
) -> None:
    """
    Remove background from images and create transparent PNGs.

    INPUT_PATH is the path to the input image file.

    Examples:

    \b
        ei remove-bg logo.png
        ei remove-bg logo.png --output logo_transparent.png
        ei remove-bg logo.png --tolerance 50
        ei remove-bg logo.png --json
    """
    console = Console()

    try:
        # Use ImageService via factory
        factory = ServiceFactory()
        image_service = factory.get_image_service()

        # Check availability
        is_available, error = image_service.check_available()
        if not is_available:  # pragma: no cover
            _handle_tool_unavailable(console, error)

        # Process image
        with console.status(
            "[bold green]Removing background...",
            spinner="dots",
        ):
            result = image_service.remove_background(
                input_path=input_path,
                output_path=output_path,
                tolerance=tolerance,
            )

        # Display result
        if output_json:
            _display_json_output(console, result)
        else:
            _display_result(console, result)

    except ServiceError as e:
        console.print(f"[red]✗[/red] {e}")
        raise Exit(1) from None
    except Exception as e:  # pragma: no cover
        console.print(f"[red]✗[/red] Unexpected error: {e}")
        raise Exit(1) from None
