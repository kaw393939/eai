"""
Transcribe command for audio transcription.

Converts audio files to text using OpenAI Whisper API with optional
preprocessing for improved accuracy.
"""

import json
import logging
from pathlib import Path

import click

from ei_cli.cli.utils import require_api_key
from ei_cli.services.factory import ServiceFactory

logger = logging.getLogger(__name__)


@click.command()
@click.argument(
    "audio_file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["text", "json", "srt", "vtt"], case_sensitive=False),
    default="text",
    help="Output format (default: text)",
)
@click.option(
    "--language",
    "-l",
    help="ISO-639-1 language code (e.g., 'en', 'es', 'fr')",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output file path (default: stdout)",
)
@click.option(
    "--no-preprocess",
    is_flag=True,
    help="Skip audio preprocessing",
)
@click.option(
    "--prompt",
    help="Optional prompt to guide transcription style",
)
@click.option(
    "--temperature",
    type=click.FloatRange(0.0, 1.0),
    default=0.0,
    help="Sampling temperature (0.0-1.0, default: 0.0)",
)
@click.option(
    "--parallel",
    is_flag=True,
    help="Use async parallel processing for faster transcription (3-5× speedup)",
)
@click.option(
    "--max-concurrent",
    type=int,
    default=3,
    help="Max concurrent chunk transcriptions when using --parallel (default: 3)",
)
def transcribe(
    audio_file: Path,
    output_format: str,
    language: str | None,
    output: Path | None,
    no_preprocess: bool,
    prompt: str | None,
    temperature: float,
    parallel: bool,
    max_concurrent: int,
) -> None:
    """
    Transcribe audio file to text using OpenAI Whisper.

    AUDIO_FILE is the path to the audio file to transcribe.

    Examples:

    \b
    # Basic transcription to stdout
    ei transcribe audio.mp3

    \b
    # Transcribe to JSON format with output file
    ei transcribe audio.mp3 -f json -o transcript.json

    \b
    # Transcribe with language hint
    ei transcribe audio.mp3 -l es -o transcript.txt

    \b
    # Generate SRT subtitles
    ei transcribe audio.mp3 -f srt -o subtitles.srt

    \b
    # Skip preprocessing for already optimized audio
    ei transcribe audio.wav --no-preprocess
    """
    # Check API key is configured
    require_api_key()

    _transcribe_impl(
        audio_file=audio_file,
        output_format=output_format,
        language=language,
        output=output,
        no_preprocess=no_preprocess,
        prompt=prompt,
        temperature=temperature,
        parallel=parallel,
        max_concurrent=max_concurrent,
    )


def _transcribe_impl(
    audio_file: Path,
    output_format: str,
    language: str | None,
    output: Path | None,
    no_preprocess: bool,
    prompt: str | None,
    temperature: float,
    parallel: bool,
    max_concurrent: int,
) -> None:
    """Internal implementation of transcribe command."""
    try:
        # Get AI service from factory
        factory = ServiceFactory()
        service = factory.get_ai_service()

        # Check availability
        is_available, error = service.check_available()
        if not is_available:
            click.echo(
                click.style(f"❌ Error: {error}", fg="red"),
                err=True,
            )
            click.echo("Set your OpenAI API key:", err=True)
            click.echo("  export API__OPENAI_API_KEY=sk-...", err=True)
            raise SystemExit(1)
    except Exception as e:
        click.echo(
            click.style(f"❌ Configuration Error: {e}", fg="red"),
            err=True,
        )
        click.echo("Set your OpenAI API key:", err=True)
        click.echo("  export API__OPENAI_API_KEY=sk-...", err=True)
        raise SystemExit(1) from e

    # Show processing message
    mode = "parallel" if parallel else "sequential"
    click.echo(
        click.style(
            f"Transcribing {audio_file.name} ({mode} mode)...",
            fg="cyan",
        ),
        err=True,
    )

    # Transcribe audio (use parallel or sequential method)
    if parallel:
        # Create progress bar for parallel mode
        from rich.console import Console
        from rich.progress import (
            BarColumn,
            MofNCompleteColumn,
            Progress,
            SpinnerColumn,
            TextColumn,
            TimeElapsedColumn,
            TimeRemainingColumn,
        )

        console = Console()
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(complete_style="green"),
            MofNCompleteColumn(),
            TextColumn("•"),
            TimeElapsedColumn(),
            TextColumn("•"),
            TimeRemainingColumn(),
            console=console,
        )

        with progress:
            task = progress.add_task(
                "Transcribing chunks",
                total=None,
            )

            def update_progress(completed: int, total: int) -> None:
                """Update progress bar."""
                if progress.tasks[task].total is None:
                    progress.update(task, total=total)
                progress.update(task, completed=completed)

            result = service.transcribe_audio_parallel(
                audio_file,
                language=language,
                prompt=prompt,
                temperature=temperature,
                max_concurrent=max_concurrent,
                progress_callback=update_progress,
            )
    else:
        result = service.transcribe_audio(
            audio_file,
            language=language,
            prompt=prompt,
            response_format=output_format,
            temperature=temperature,
            preprocess=not no_preprocess,
        )

    # Format output
    output_text = result.text

    # Add metadata for JSON format
    if output_format == "json" and result.language:
        metadata = {
            "text": result.text,
            "language": result.language,
            "duration": result.duration,
            "model": result.model,
        }
        output_text = json.dumps(metadata, indent=2)

    # Write to output file or stdout
    if output:
        output.write_text(output_text)
        click.echo(
            click.style(
                f"✓ Transcription saved to {output}",
                fg="green",
            ),
            err=True,
        )

        # Show metadata
        if result.language:
            click.echo(
                click.style(
                    f"  Language: {result.language}",
                    fg="blue",
                ),
                err=True,
            )
        if result.duration:
            duration_min = result.duration / 60
            click.echo(
                click.style(
                    f"  Duration: {duration_min:.2f} minutes",
                    fg="blue",
                ),
                err=True,
            )
    else:
        # Output to stdout
        click.echo(output_text)
