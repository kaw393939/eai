"""
Multi-image vision analysis command for ei CLI.

Provides batch image analysis and comparison using GPT-5 Vision models.
"""

import click
from click.exceptions import Exit
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from ei_cli.cli.utils import require_api_key
from ei_cli.core.errors import MissingAPIKeyError
from ei_cli.services.ai_service import VisionResult
from ei_cli.services.base import ServiceError
from ei_cli.services.factory import ServiceFactory


def _handle_tool_unavailable(
    console: Console,
    error: str | None,
) -> None:
    """Handle when multi-vision tool is unavailable."""
    console.print(
        f"[red]✗[/red] Multi-image analysis tool not available: {error}",
    )
    console.print(
        "\n[yellow]Tip:[/yellow] Set your OpenAI API key:",
    )
    console.print("  export EI_API_KEY=your-key-here")
    raise Exit(1) from None


def _display_result(
    console: Console,
    result: VisionResult,
    show_metadata: bool,
    image_count: int,
) -> None:
    """Display multi-image analysis result."""
    console.print()

    # Display image sources
    console.print(Panel(
        f"[cyan]Images:[/cyan] {result.image_source}\n"
        f"[dim]Model:[/dim] {result.model}\n"
        f"[dim]Count:[/dim] {image_count} images",
        title="📸 Multi-Image Analysis",
        border_style="cyan",
    ))

    # Display prompt if custom
    if result.prompt != "Compare and analyze these images.":
        console.print()
        console.print(Panel(
            result.prompt,
            title="[bold yellow]Analysis Prompt[/bold yellow]",
            border_style="yellow",
        ))

    # Display analysis as markdown
    console.print()
    console.print(Panel(
        Markdown(result.analysis),
        title="[bold green]Multi-Image Analysis[/bold green]",
        border_style="green",
    ))

    if show_metadata:
        console.print()
        console.print("[dim]Tip: Use --json for machine-readable output[/dim]")


def _display_json_output(
    console: Console,
    result: VisionResult,
    image_paths: list[str],
) -> None:
    """Display result as JSON."""
    output = {
        "analysis": result.analysis,
        "model": result.model,
        "image_sources": image_paths,
        "image_count": len(image_paths),
        "prompt": result.prompt,
    }
    console.print_json(data=output)


@click.command()
@click.argument("images", nargs=-1, required=True)
@click.option(
    "--prompt",
    "-p",
    default="Compare and analyze these images.",
    help="Analysis prompt for all images",
)
@click.option(
    "--compare",
    "-c",
    is_flag=True,
    help="Enable comparison mode for detailed comparisons",
)
@click.option(
    "--detail",
    "-d",
    default="auto",
    type=click.Choice(["auto", "low", "high"]),
    help="Image detail level (default: auto, high costs more)",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output results as JSON",
)
def multi_vision(
    images: tuple[str, ...],
    prompt: str,
    compare: bool,
    detail: str,
    output_json: bool,
) -> None:
    """
    Analyze multiple images simultaneously using GPT-5 Vision.

    IMAGES should be 2-3 image paths or URLs.

    Examples:

    \b
        # Compare two images
        ei multi-vision image1.jpg image2.jpg

        # Analyze multiple images with custom prompt  
        ei multi-vision *.jpg --prompt "What's common in these images?"

        # Detailed comparison mode
        ei multi-vision photo1.png photo2.png --compare

        # High detail analysis
        ei multi-vision img1.jpg img2.jpg img3.jpg --detail high

        # Mix local files and URLs
        ei multi-vision local.jpg https://example.com/image.jpg

        # JSON output for automation
        ei multi-vision image1.jpg image2.jpg --json
    """
    # Check API key is configured
    require_api_key()

    console = Console()

    # Validate number of images
    if len(images) < 2:
        console.print("[red]✗[/red] At least 2 images are required")
        console.print("\n[yellow]Example:[/yellow] ei multi-vision image1.jpg image2.jpg")
        raise Exit(1)

    if len(images) > 3:
        console.print("[red]✗[/red] Maximum 3 images allowed")
        console.print(f"\n[yellow]You provided {len(images)} images.[/yellow] Please select 2-3 images.")
        console.print("\n[dim]Note:[/dim] OpenAI Vision API currently supports up to 3 images in multi-vision analysis.")
        raise Exit(1)

    try:
        # Get AI service from factory
        factory = ServiceFactory()
        ai_service = factory.get_ai_service()

        # Check availability
        is_available, error = ai_service.check_available()
        if not is_available:  # pragma: no cover
            _handle_tool_unavailable(console, error)

        # Analyze multiple images
        with console.status(
            f"[bold green]Analyzing {len(images)} images...",
            spinner="dots",
        ):
            result = ai_service.analyze_multiple_images(
                image_paths=list(images),
                prompt=prompt,
                detail_level=detail,
                compare_mode=compare,
            )

        # Display result
        if output_json:
            _display_json_output(console, result, list(images))
        else:
            _display_result(console, result, show_metadata=True, image_count=len(images))

    except MissingAPIKeyError:
        console.print("[red]✗[/red] Missing API key: EI_API_KEY not set")
        console.print(
            "\n[yellow]Set your OpenAI API key:[/yellow]",
        )
        console.print("  export EI_API_KEY=your-key-here")
        raise Exit(1) from None
    except ServiceError as e:
        console.print(f"[red]✗[/red] {e}")
        raise Exit(1) from None
    except Exception as e:  # pragma: no cover
        console.print(f"[red]✗[/red] Unexpected error: {e}")
        raise Exit(1) from None
