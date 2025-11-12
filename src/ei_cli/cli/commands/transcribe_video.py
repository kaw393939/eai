"""CLI command for video transcription."""

import contextlib
import json
import tempfile
from pathlib import Path

import click

from ei_cli.cli.utils import require_api_key
from ei_cli.core.error_handler import handle_error
from ei_cli.core.errors import AIServiceError, ConfigurationError
from ei_cli.services.base import ServiceUnavailableError
from ei_cli.services.factory import ServiceFactory
from ei_cli.services.video_downloader import VideoDownloader, VideoDownloadError


@click.command(name="transcribe-video")
@click.argument("url", type=str)
@click.option(
    "--format",
    "-f",
    "response_format",
    type=click.Choice(["text", "json", "srt", "vtt"], case_sensitive=False),
    default="text",
    help="Output format",
)
@click.option(
    "--language",
    "-l",
    help="ISO-639-1 language code (e.g., 'en', 'es', 'fr')",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Save output to file (default: stdout)",
)
@click.option(
    "--keep-audio",
    is_flag=True,
    help="Keep downloaded audio file",
)
@click.option(
    "--audio-format",
    type=click.Choice(["best", "m4a", "mp3", "wav"], case_sensitive=False),
    default="best",
    help="Audio format preference for download",
)
@click.option(
    "--no-preprocess",
    is_flag=True,
    help="Skip audio preprocessing (mono conversion, resampling)",
)
@click.option(
    "--prompt",
    "-p",
    help="Optional text to guide transcription",
)
@click.option(
    "--temperature",
    "-t",
    type=click.FloatRange(0.0, 1.0),
    default=0.0,
    help="Sampling temperature (0.0-1.0, higher = more random)",
)
@click.option(
    "--cookies-from-browser",
    type=click.Choice(["chrome", "firefox", "safari", "edge"], case_sensitive=False),
    help="Extract cookies from browser (helps with restricted videos)",
)
@click.option(
    "--cookies-file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to Netscape format cookies file",
)
@click.option(
    "--parallel",
    is_flag=True,
    help="Use async parallel processing (3-5x faster for large files)",
)
@click.option(
    "--max-concurrent",
    type=int,
    default=4,
    help="Max concurrent chunks when using --parallel (default: 4)",
)
def transcribe_video(
    url: str,
    response_format: str,
    language: str | None,
    output: Path | None,
    keep_audio: bool,
    audio_format: str,
    no_preprocess: bool,
    prompt: str | None,
    temperature: float,
    cookies_from_browser: str | None,
    cookies_file: Path | None,
    parallel: bool,
    max_concurrent: int,
) -> None:
    """
    Download video and transcribe audio using Whisper.

    Supports YouTube, Vimeo, and many other video platforms via yt-dlp.

    Examples:

        \b
        # Transcribe YouTube video
        ei transcribe-video "https://youtube.com/watch?v=..."

        \b
        # Generate subtitles
        ei transcribe-video URL -f srt -o subtitles.srt

        \b
        # Transcribe with language hint
        ei transcribe-video URL -l es --format json

        \b
        # Keep audio file for later use
        ei transcribe-video URL --keep-audio

        \b
        # Use specific audio format
        ei transcribe-video URL --audio-format mp3 --keep-audio
    """
    # Check API key is configured
    require_api_key()

    # Wrap entire command in error handler for user-friendly messages
    try:
        _transcribe_video_impl(
            url=url,
            response_format=response_format,
            language=language,
            output=output,
            keep_audio=keep_audio,
            audio_format=audio_format,
            no_preprocess=no_preprocess,
            prompt=prompt,
            temperature=temperature,
            cookies_from_browser=cookies_from_browser,
            cookies_file=cookies_file,
            parallel=parallel,
            max_concurrent=max_concurrent,
        )
    except Exception as e:
        handle_error(e)


def _transcribe_video_impl(
    url: str,
    response_format: str,
    language: str | None,
    output: Path | None,
    keep_audio: bool,
    audio_format: str,
    no_preprocess: bool,
    prompt: str | None,
    temperature: float,
    cookies_from_browser: str | None,
    cookies_file: Path | None,
    parallel: bool,
    max_concurrent: int,
) -> None:
    """Internal implementation of transcribe-video command."""
    audio_file: Path | None = None

    try:
        # Get services
        try:
            service_factory = ServiceFactory()
            ai_service = service_factory.get_ai_service()
        except ConfigurationError as e:
            click.echo(
                click.style("Configuration Error: ", fg="red", bold=True)
                + str(e),
                err=True,
            )
            raise click.exceptions.Exit(1) from e

        # Check if AI service is available
        if not ai_service.check_available():
            raise ServiceUnavailableError(
                service_name="AI Service",
                reason="OpenAI API key not configured",
            )

        # Initialize video downloader
        downloader = VideoDownloader()

        # Get video info
        click.echo(
            click.style("Fetching video information...", fg="cyan", bold=True),
        )

        try:
            info = downloader.get_video_info(url)
            click.echo(f"  Title: {click.style(info['title'], fg='yellow')}")
            if info.get("duration"):
                duration_min = info["duration"] / 60
                click.echo(
                    f"  Duration: {click.style(f'{duration_min:.1f} min', fg='yellow')}",
                )
        except VideoDownloadError as e:
            click.echo(
                click.style("Warning: ", fg="yellow")
                + f"Could not fetch video info: {e.message}",
                err=True,
            )

        # Download audio
        click.echo(
            click.style("\nDownloading audio...", fg="cyan", bold=True),
        )

        if keep_audio and output:
            # Use output path directory for audio file
            audio_dir = output.parent if output.parent != Path() else Path.cwd()
            audio_name = output.stem + f"_audio.{audio_format}"
            audio_file = audio_dir / audio_name
        else:
            # Create temp file in user's temp directory
            # delete=False so it persists for transcription
            temp_file = tempfile.NamedTemporaryFile(
                suffix=f".{audio_format}",
                delete=False,
            )
            audio_file = Path(temp_file.name)
            temp_file.close()

        try:
            audio_file = downloader.download_audio(
                url=url,
                output_path=audio_file,
                format_preference=audio_format,
                show_progress=True,
                cookies_from_browser=cookies_from_browser,
                cookies_file=cookies_file,
            )
        except VideoDownloadError as e:
            click.echo(
                click.style("Download Error: ", fg="red", bold=True)
                + e.message,
                err=True,
            )
            if e.details:
                click.echo(f"  Details: {e.details}", err=True)
            raise click.exceptions.Exit(1) from e

        click.echo(
            click.style("✓ Audio downloaded", fg="green"),
        )

        # Validate format for parallel mode
        if parallel and response_format.lower() in ["srt", "vtt"]:
            click.echo(
                click.style("Warning: ", fg="yellow", bold=True)
                + f"Parallel mode with {response_format.upper()} format may "
                + "produce suboptimal results. Consider using sequential mode "
                + "for subtitle formats.",
                err=True,
            )

        # Transcribe audio
        mode = "parallel" if parallel else "sequential"
        click.echo(
            click.style(
                f"\nTranscribing audio ({mode} mode)...",
                fg="cyan",
                bold=True,
            ),
        )

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

                result = ai_service.transcribe_audio_parallel(
                    audio_path=audio_file,
                    language=language,
                    prompt=prompt,
                    response_format=response_format.lower(),
                    temperature=temperature,
                    max_concurrent=max_concurrent,
                    progress_callback=update_progress,
                )
        else:
            result = ai_service.transcribe_audio(
                audio_path=audio_file,
                language=language,
                prompt=prompt,
                response_format=response_format.lower(),
                temperature=temperature,
                preprocess=not no_preprocess,
            )

        # Format output based on response format
        if response_format.lower() == "json":
            output_text = json.dumps(
                {
                    "text": result.text,
                    "language": result.language,
                    "duration": result.duration,
                    "model": result.model,
                },
                indent=2,
            )
        else:
            output_text = result.text

        # Output result
        if output:
            output.write_text(output_text, encoding="utf-8")
            click.echo(
                click.style("\n✓ Transcription complete!", fg="green", bold=True),
            )
            click.echo(f"  Output: {click.style(str(output), fg='blue')}")
        else:
            click.echo(
                click.style("\n✓ Transcription:", fg="green", bold=True),
            )
            click.echo(output_text)

        # Show metadata for non-json formats
        if response_format.lower() != "json" and not output:
            click.echo(
                click.style("\nMetadata:", fg="cyan"),
            )
            if result.language:
                click.echo(f"  Language: {result.language}")
            if result.duration:
                click.echo(f"  Duration: {result.duration:.2f}s")
            click.echo(f"  Model: {result.model}")

        # Show audio file location if keeping it
        if keep_audio and audio_file:
            click.echo(
                click.style("\nAudio file saved:", fg="cyan"),
            )
            click.echo(f"  {click.style(str(audio_file), fg='blue')}")

    except ServiceUnavailableError as e:
        click.echo(
            click.style("Service Unavailable: ", fg="red", bold=True) + str(e),
            err=True,
        )
        raise click.exceptions.Exit(1) from e

    except AIServiceError as e:
        click.echo(
            click.style("AI Service Error: ", fg="red", bold=True) + e.message,
            err=True,
        )
        if e.code:
            click.echo(f"  Error Code: {e.code}", err=True)
        raise click.exceptions.Exit(1) from e

    except Exception as e:
        click.echo(
            click.style("Error: ", fg="red", bold=True) + str(e),
            err=True,
        )
        raise click.exceptions.Exit(1) from e

    finally:
        # Cleanup temp audio file if not keeping it
        if not keep_audio and audio_file and audio_file.exists():
            with contextlib.suppress(OSError):
                audio_file.unlink()
