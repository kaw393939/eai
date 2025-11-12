"""CLI command for audio translation using OpenAI Whisper."""

import json
from pathlib import Path

import click

from ei_cli.cli.utils import require_api_key
from ei_cli.core.errors import AIServiceError, ConfigurationError
from ei_cli.services.base import ServiceUnavailableError
from ei_cli.services.factory import ServiceFactory


@click.command(name="translate-audio")
@click.argument(
    "audio_file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option(
    "--format",
    "-f",
    "response_format",
    type=click.Choice(["text", "json", "srt", "vtt"], case_sensitive=False),
    default="text",
    help="Output format",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Save output to file (default: stdout)",
)
@click.option(
    "--no-preprocess",
    is_flag=True,
    help="Skip audio preprocessing (mono conversion, resampling)",
)
@click.option(
    "--prompt",
    "-p",
    help="Optional text to guide translation style",
)
@click.option(
    "--temperature",
    "-t",
    type=click.FloatRange(0.0, 1.0),
    default=0.0,
    help="Sampling temperature (0.0-1.0, higher = more random)",
)
def translate_audio(
    audio_file: Path,
    response_format: str,
    output: Path | None,
    no_preprocess: bool,
    prompt: str | None,
    temperature: float,
) -> None:
    """
    Translate audio from any language to English using Whisper.

    NOTE: OpenAI Whisper translation ONLY supports translating TO English.
    It cannot translate FROM English to other languages or between non-English
    languages. For text translation, use ChatGPT API instead.

    Supports various audio formats (mp3, wav, m4a, etc.) and automatically
    converts them to the optimal format for translation.

    Examples:

        \b
        # Translate audio to English (text output)
        ei translate-audio spanish.mp3

        \b
        # Get JSON with metadata
        ei translate-audio audio.wav --format json

        \b
        # Generate English subtitles
        ei translate-audio video.mp4 -f srt -o english.srt

        \b
        # Translate to file
        ei translate-audio recording.m4a -o translation.txt

        \b
        # Skip preprocessing for pre-optimized audio
        ei translate-audio optimized.wav --no-preprocess
    """
    # Check API key is configured
    require_api_key()

    try:
        # Get AI service
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

        # Check if service is available
        if not ai_service.check_available():
            raise ServiceUnavailableError(
                service_name="AI Service",
                reason="OpenAI API key not configured",
            )

        # Show info
        click.echo(
            click.style("Translating audio to English...", fg="cyan", bold=True),
        )
        click.echo(f"  File: {click.style(str(audio_file), fg='yellow')}")
        click.echo(f"  Format: {click.style(response_format, fg='yellow')}")

        # Translate audio
        result = ai_service.translate_audio(
            audio_path=audio_file,
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
                click.style("\n✓ Translation complete!", fg="green", bold=True),
            )
            click.echo(f"  Output: {click.style(str(output), fg='blue')}")
        else:
            click.echo(
                click.style("\n✓ Translation:", fg="green", bold=True),
            )
            click.echo(output_text)

        # Show metadata for non-json formats
        if response_format.lower() != "json" and not output:
            click.echo(
                click.style("\nMetadata:", fg="cyan"),
            )
            click.echo(f"  Language: {result.language} (translated to English)")
            if result.duration:
                click.echo(f"  Duration: {result.duration:.2f}s")
            click.echo(f"  Model: {result.model}")

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
