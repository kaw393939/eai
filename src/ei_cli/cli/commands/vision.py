"""
Vision analysis command for ei CLI.

Provides image analysis using GPT-4 Vision models.
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


def _handle_tool_unavailable(  # pragma: no cover
    console: Console,
    error: str | None,
) -> None:
    """Handle when vision tool is unavailable."""
    console.print(
        f"[red]✗[/red] Vision tool not available: {error}",
    )
    console.print(
        "\n[yellow]Tip:[/yellow] Set your OpenAI API key:",
    )
    console.print("  export API__OPENAI_API_KEY=your-key-here")
    raise Exit(1) from None


def _display_result(
    console: Console,
    result: VisionResult,
    show_metadata: bool,
) -> None:
    """Display vision analysis result."""
    console.print()

    # Display image source
    console.print(Panel(
        f"[cyan]Image:[/cyan] {result.image_source}\n"
        f"[dim]Model:[/dim] {result.model}",
        title="📸 Vision Analysis",
        border_style="cyan",
    ))

    # Display prompt if custom
    if result.prompt != "Describe this image in detail.":
        console.print()
        console.print(Panel(
            result.prompt,
            title="[bold yellow]Question[/bold yellow]",
            border_style="yellow",
        ))

    # Display analysis as markdown
    console.print()
    console.print(Panel(
        Markdown(result.analysis),
        title="[bold green]Analysis[/bold green]",
        border_style="green",
    ))

    if show_metadata:
        console.print()
        console.print("[dim]Tip: Use --json for machine-readable output[/dim]")


def _display_json_output(
    console: Console,
    result: VisionResult,
) -> None:
    """Display result as JSON."""
    output = {
        "analysis": result.analysis,
        "model": result.model,
        "image_source": result.image_source,
        "prompt": result.prompt,
    }
    console.print_json(data=output)


@click.command()
@click.argument("image", required=True)
@click.option(
    "--prompt",
    "-p",
    default="Describe this image in detail.",
    help="Question or instruction about the image",
)
@click.option(
    "--model",
    "-m",
    default="gpt-5",
    type=click.Choice([
        "gpt-5",
    ]),
    help="Model to use for analysis (default: gpt-5)",
)
@click.option(
    "--detail",
    "-d",
    default="auto",
    type=click.Choice(["auto", "low", "high"]),
    help="Image detail level (default: auto, high costs more)",
)
@click.option(
    "--max-tokens",
    "-t",
    default=1000,
    type=int,
    help="Maximum tokens in response (default: 1000)",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output results as JSON",
)
def vision(
    image: str,
    prompt: str,
    model: str,  # noqa: ARG001 - Kept for CLI backward compatibility
    detail: str,
    max_tokens: int,  # noqa: ARG001 - Not supported by AIService
    output_json: bool,
) -> None:
    """
    Analyze images using GPT-5 and GPT-4 Vision.

    IMAGE can be a URL or local file path.

    Examples:

    \b
        # Describe an image
        ei vision image.jpg

        # Ask specific questions
        ei vision photo.png --prompt "What colors are in this image?"

        # Extract text from image (OCR)
        ei vision document.jpg --prompt "Extract all text from this image"

        # Analyze with high detail
        ei vision diagram.png --detail high --max-tokens 2000

        # Analyze from URL
        ei vision https://example.com/image.jpg

        # JSON output
        ei vision image.jpg --json
    """
    # Check API key is configured
    require_api_key()

    console = Console()

    try:
        # Get AI service from factory
        factory = ServiceFactory()
        ai_service = factory.get_ai_service()

        # Check availability
        is_available, error = ai_service.check_available()
        if not is_available:  # pragma: no cover
            _handle_tool_unavailable(console, error)

        # Analyze image
        with console.status(
            "[bold green]Analyzing image...",
            spinner="dots",
        ):
            result = ai_service.analyze_image(
                image_path=image,
                prompt=prompt,
                detail_level=detail,
            )

        # Display result
        if output_json:
            _display_json_output(console, result)
        else:
            _display_result(console, result, show_metadata=True)

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
