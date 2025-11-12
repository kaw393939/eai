"""
Image cropping command for ei CLI.

Automatically crops images to remove excess whitespace.
"""

from pathlib import Path

import click
from click.exceptions import Exit
from rich.console import Console
from rich.panel import Panel

from ei_cli.services.base import ServiceError
from ei_cli.services.factory import ServiceFactory


def _handle_tool_unavailable(  # pragma: no cover
    console: Console,
    error: str | None,
) -> None:
    """Handle tool unavailability."""
    console.print(
        f"[red]✗[/red] Image crop tool not available: {error}",
    )
    console.print(
        "\n[yellow]Tip:[/yellow] Install required packages:",
    )
    console.print("  poetry add pillow numpy")
    raise Exit(1) from None


def _display_result(
    console: Console,
    input_path: str,
    output_path: str,
    success: bool,
    message: str,
) -> None:
    """Display crop result."""
    console.print()

    if success:
        console.print(Panel(
            f"[green]✓[/green] Successfully cropped image\n"
            f"[cyan]Input:[/cyan] {input_path}\n"
            f"[cyan]Output:[/cyan] {output_path}\n"
            f"[dim]Result:[/dim] {message}",
            title="✂️ Image Crop Result",
            border_style="green",
        ))
    else:
        console.print(Panel(
            f"[red]✗[/red] Failed to crop image\n"
            f"[cyan]Input:[/cyan] {input_path}\n"
            f"[red]Error:[/red] {message}",
            title="✂️ Image Crop Result",
            border_style="red",
        ))


@click.command()
@click.argument("input_path", required=True)
@click.option(
    "--output",
    "-o",
    help="Output file path (default: adds -cropped suffix)",
)
@click.option(
    "--padding",
    "-p",
    default=5,
    type=int,
    help="Pixels of padding to keep around content (default: 5)",
)
@click.option(
    "--tolerance",
    "-t",
    default=20,
    type=int,
    help="Color tolerance for background detection (default: 20)",
)
def crop(
    input_path: str,
    output: str | None,
    padding: int,
    tolerance: int,
) -> None:
    """
    Automatically crop images to remove excess whitespace.

    INPUT_PATH should be the path to the image file to crop.

    Examples:

    \b
        # Crop logo with default settings
        ei crop logo.png

        # Crop with custom output path and padding
        ei crop logo.png --output logo-tight.png --padding 10

        # Crop with higher tolerance for background detection
        ei crop image.jpg --tolerance 30
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

        # Generate output path if not provided
        if not output:
            input_pathobj = Path(input_path)
            stem = input_pathobj.stem
            suffix = input_pathobj.suffix or ".png"
            output = str(input_pathobj.parent / f"{stem}-cropped{suffix}")

        # Crop image
        with console.status(
            "[bold green]Cropping image...",
            spinner="dots",
        ):
            crop_result = image_service.crop(
                input_path=input_path,
                output_path=output,
                tolerance=tolerance,
                padding=padding,
            )

        # Display result
        _display_result(
            console,
            input_path,
            output,
            crop_result.success,
            crop_result.message,
        )

        if not crop_result.success:
            raise Exit(1)

    except ServiceError as e:
        console.print(f"[red]✗[/red] {e}")
        raise Exit(1) from None
    except Exception as e:  # pragma: no cover
        console.print(f"[red]✗[/red] Unexpected error: {e}")
        raise Exit(1) from None
