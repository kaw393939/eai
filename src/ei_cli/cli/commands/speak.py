"""CLI command for text-to-speech generation using OpenAI TTS."""

from pathlib import Path

import click

from ei_cli.cli.utils import require_api_key
from ei_cli.core.errors import AIServiceError, ConfigurationError
from ei_cli.services.base import ServiceUnavailableError
from ei_cli.services.factory import ServiceFactory


@click.command(name="speak")
@click.argument(
    "text",
    type=str,
    required=False,
)
@click.option(
    "--input",
    "-i",
    "input_file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Read text from a file instead of argument",
)
@click.option(
    "--voice",
    "-v",
    type=click.Choice(
        [
            # Standard voices (all models)
            "alloy", "echo", "fable", "onyx", "nova", "shimmer",
            # tts-1 additional voices
            "ash", "ballad", "coral", "sage", "verse",
        ],
        case_sensitive=False,
    ),
    default="alloy",
    help="Voice to use. Recommended: alloy/nova for most natural speech",
)
@click.option(
    "--speed",
    "-s",
    type=click.FloatRange(0.25, 4.0),
    default=1.0,
    help="Playback speed (0.25 to 4.0)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=False, path_type=Path),
    required=True,
    help="Output audio file path",
)
@click.option(
    "--model",
    "-m",
    type=click.Choice(["tts-1", "tts-1-hd"], case_sensitive=False),
    default="tts-1",
    help="TTS model to use (tts-1 or tts-1-hd for higher quality)",
)
@click.option(
    "--format",
    "-f",
    "audio_format",
    type=click.Choice(["mp3", "opus", "aac", "flac", "wav", "pcm"], case_sensitive=False),
    default="mp3",
    help="Audio format (mp3=default, opus=low latency, aac=compatible, flac/wav=lossless, pcm=raw)",
)
@click.option(
    "--instructions",
    type=str,
    help="Optional guidance for pronunciation, pacing, or speaking style",
)
@click.option(
    "--stream",
    is_flag=True,
    default=False,
    help="Enable streaming mode with progress indicator",
)
@click.option(
    "--play",
    is_flag=True,
    default=False,
    help="Play audio after generation (requires pydub and simpleaudio)",
)
def speak(
    text: str | None,
    input_file: Path | None,
    voice: str,
    speed: float,
    output: Path,
    model: str,
    audio_format: str,
    instructions: str | None,
    stream: bool,
    play: bool,
) -> None:
    """
    Generate speech audio from text using OpenAI TTS.

    Provide text as an argument or use --input to read from a file.

    \b
    Voice Options:
      Standard (all models): alloy, echo, fable, onyx, nova, shimmer
      tts-1 additional: ash, ballad, coral, sage, verse

    Format Options:
      mp3: Default, widely compatible (compressed)
      opus: Low latency streaming, great for real-time (compressed)
      aac: Broad compatibility, good quality (compressed)
      flac: Lossless compression, archival quality
      wav: Uncompressed, highest quality, large files
      pcm: Raw 16-bit PCM audio at 24kHz

    Instructions:
      Optional parameter to guide pronunciation, pacing, or speaking style.
      Useful for: proper names, technical terms, emphasis, emotion, pacing

    Examples:

        \b
        # Generate speech from text
        ei speak "Hello, world!" --output hello.mp3

        \b
        # Use high-quality model
        ei speak "This sounds natural" -v nova -m tts-1-hd -o speech.mp3

        \b
        # Guide pronunciation with instructions
        ei speak "Dr. Nguyen lives on Rue du Chat" -o speech.mp3 \\
          --instructions "Pronounce 'Nguyen' as 'win'"

        \b
        # Control pacing and emotion
        ei speak "Important announcement!" -o urgent.mp3 \\
          --instructions "Speak slowly with urgency"

        \b
        # High-quality lossless audio
        ei speak "Archive quality" -f flac -o speech.flac

        \b
        # Low-latency streaming format
        ei speak "Real-time audio" -f opus -o stream.opus --stream

        \b
        # Read from a file with streaming
        ei speak --input script.txt --output speech.mp3 --stream

        \b
        # Use HD quality with slower speed
        ei speak "Important message" -m tts-1-hd -s 0.8 -o message.mp3

        \b
        # Generate and play immediately
        ei speak "Hello world" -o hello.mp3 --play

        \b
        # Stream with playback (requires pydub and simpleaudio)
        ei speak "Live demo" -o demo.mp3 --stream --play
    """
    # Check API key is configured
    require_api_key()

    try:
        # Validate input
        if not text and not input_file:
            raise click.UsageError(
                "Must provide either text argument or --input file",
            )

        if text and input_file:
            raise click.UsageError(
                "Cannot use both text argument and --input file",
            )

        # Validate voice/model compatibility
        voice_lower = voice.lower()
        model_lower = model.lower()

        # Define model-specific voice sets
        tts1_exclusive = {"ash", "ballad", "coral", "sage", "verse"}

        # Check for invalid combinations
        if voice_lower in tts1_exclusive and model_lower not in ["tts-1", "tts-1-hd"]:
            msg = f"Voice '{voice}' is not available with model '{model}'"
            click.echo(
                click.style("Error: ", fg="red", bold=True) + msg,
                err=True,
            )
            raise click.exceptions.Exit(1)

        # Get text content
        if input_file:
            text_content = input_file.read_text(encoding="utf-8").strip()
            if not text_content:
                click.echo(
                    click.style("Error: ", fg="red", bold=True)
                    + "Input file is empty",
                    err=True,
                )
                raise click.exceptions.Exit(1)
        else:
            text_content = text.strip()  # type: ignore[union-attr]

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
                message="OpenAI API key not configured",
                service_name="AI Service",
            )

        # Show info
        click.echo(
            click.style("Generating speech...", fg="cyan", bold=True),
        )
        click.echo(f"  Voice: {click.style(voice, fg='yellow')}")
        click.echo(f"  Model: {click.style(model, fg='yellow')}")
        click.echo(f"  Format: {click.style(audio_format, fg='yellow')}")
        click.echo(f"  Speed: {click.style(f'{speed}x', fg='yellow')}")
        if instructions:
            # Truncate long instructions for display
            max_display = 50
            display_instr = (
                instructions[:max_display] + "..."
                if len(instructions) > max_display
                else instructions
            )
            click.echo(
                f"  Instructions: {click.style(display_instr, fg='yellow')}",
            )
        if stream:
            click.echo(f"  Mode: {click.style('Streaming', fg='yellow')}")

        # Generate speech with or without streaming
        if stream:
            # Progress tracking for streaming
            bytes_written = [0]  # Use list to allow mutation in closure

            def on_chunk(bytes_received: int, _total: int) -> None:
                """Progress callback for streaming."""
                bytes_written[0] = bytes_received
                kb_received = bytes_received / 1024
                click.echo(
                    f"\r  Progress: {kb_received:.1f} KB received...",
                    nl=False,
                )

            result = ai_service.text_to_speech_stream(
                text=text_content,
                output_path=output,
                voice=voice_lower,
                speed=speed,
                model=model_lower,
                response_format=audio_format.lower(),
                on_chunk=on_chunk,
                instructions=instructions,
            )

            # Clear progress line
            if bytes_written[0] > 0:
                click.echo()  # New line after progress
        else:
            result = ai_service.text_to_speech(
                text=text_content,
                output_path=output,
                voice=voice_lower,
                speed=speed,
                model=model_lower,
                response_format=audio_format.lower(),
                instructions=instructions,
            )

        # Show success
        click.echo(
            click.style("\n✓ Speech generated!", fg="green", bold=True),
        )
        click.echo(
            f"  Output: {click.style(str(result.audio_path), fg='blue')}",
        )

        # Play audio if requested
        if play:
            try:
                from pydub import AudioSegment
                from pydub.playback import play as pydub_play

                click.echo("\nPlaying audio...")
                audio = AudioSegment.from_file(str(result.audio_path))
                pydub_play(audio)
                click.echo(
                    click.style("✓ Playback complete!", fg="green"),
                )

            except ImportError:
                click.echo(
                    click.style(
                        "\n⚠ Playback unavailable: Missing dependencies",
                        fg="yellow",
                    ),
                )
                click.echo(
                    "  Install with: pip install pydub simpleaudio",
                )
            except Exception as e:
                click.echo(
                    click.style(
                        f"\n⚠ Playback failed: {e}",
                        fg="yellow",
                    ),
                )

    except ServiceUnavailableError as e:
        click.echo(
            click.style("Service Unavailable: ", fg="red", bold=True)
            + str(e),
            err=True,
        )
        raise click.exceptions.Exit(1) from e

    except AIServiceError as e:
        click.echo(
            click.style("AI Service Error: ", fg="red", bold=True)
            + e.message,
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
