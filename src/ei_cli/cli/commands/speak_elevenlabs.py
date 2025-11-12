"""
CLI commands for ElevenLabs text-to-speech.
"""

from pathlib import Path

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from ei_cli.services.elevenlabs_service import ElevenLabsAudioService

console = Console()


@click.group(name="elevenlabs")
def elevenlabs_group() -> None:
    """ElevenLabs TTS commands."""


@elevenlabs_group.command(name="speak")
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
    help="Read text from file",
)
@click.option(
    "--output",
    "-o",
    required=True,
    type=click.Path(path_type=Path),
    help="Output audio file path",
)
@click.option(
    "--voice",
    "-v",
    default="rachel",
    help="Voice name or ID (default: rachel)",
)
@click.option(
    "--model",
    "-m",
    default="eleven_multilingual_v2",
    type=click.Choice([
        "eleven_multilingual_v2",
        "eleven_flash_v2_5",
        "eleven_turbo_v2_5",
    ]),
    help="Model to use",
)
@click.option(
    "--format",
    "-f",
    default="mp3_44100_128",
    help="Audio format (mp3_44100_128, mp3_22050_32, pcm_16000, etc.)",
)
@click.option(
    "--stability",
    default=0.5,
    type=click.FloatRange(0.0, 1.0),
    help="Voice stability 0.0-1.0 (higher = more consistent)",
)
@click.option(
    "--similarity",
    default=0.75,
    type=click.FloatRange(0.0, 1.0),
    help="Voice similarity 0.0-1.0 (higher = closer to original)",
)
@click.option(
    "--style",
    default=0.0,
    type=click.FloatRange(0.0, 1.0),
    help="Style exaggeration 0.0-1.0",
)
@click.option(
    "--speaker-boost/--no-speaker-boost",
    default=True,
    help="Enable speaker boost",
)
@click.option(
    "--stream",
    is_flag=True,
    help="Enable streaming mode",
)
@click.option(
    "--latency",
    type=click.IntRange(0, 4),
    help="Optimize latency 0-4 (higher = faster, lower quality)",
)
@click.option(
    "--play",
    is_flag=True,
    help="Play audio after generation",
)
def speak_elevenlabs(
    text: str | None,
    input_file: Path | None,
    output: Path,
    voice: str,
    model: str,
    format: str,
    stability: float,
    similarity: float,
    style: float,
    speaker_boost: bool,
    stream: bool,
    latency: int | None,
    play: bool,
) -> None:
    """
    Generate speech using ElevenLabs TTS.

    ElevenLabs offers high-quality voices, voice cloning, ultra-low latency.
    100-200x cheaper than OpenAI TTS!

    Examples:

    \b
        # Basic usage
        ei elevenlabs speak "Hello world" -o hello.mp3

        # Use different voice
        ei elevenlabs speak "Welcome!" -o welcome.mp3 -v adam

        # Ultra-fast model for real-time
        ei elevenlabs speak "Quick!" -o fast.mp3 -m eleven_flash_v2_5

        # From file with streaming
        ei elevenlabs speak --input script.txt -o output.mp3 --stream

        # Custom voice settings
        ei elevenlabs speak "Dramatic!" -o drama.mp3 \\
            --stability 0.3 --style 0.8
    """
    try:
        # Get text input
        if text is None and input_file is None:
            raise click.UsageError(
                "Provide text or --input file",
            )

        if text and input_file:
            raise click.UsageError(
                "Provide either text or --input, not both",
            )

        if input_file:
            text = input_file.read_text()

        # Initialize service
        service = ElevenLabsAudioService()

        # Display generation info
        console.print("\n[cyan]Generating speech with ElevenLabs...[/cyan]")
        console.print(f"  Voice: {voice}")
        console.print(f"  Model: {model}")
        console.print(f"  Format: {format}")
        console.print(f"  Stability: {stability}")
        console.print(f"  Similarity: {similarity}")
        if stream:
            console.print("  Mode: Streaming")
        if latency is not None:
            console.print(f"  Latency: {latency} (optimized)")

        # Generate audio
        if stream:
            # Streaming mode
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Generating audio...", total=None)

                audio_chunks = []
                for chunk in service.text_to_speech_stream(
                    text,
                    voice=voice,
                    model=model,
                    output_format=format,
                    stability=stability,
                    similarity_boost=similarity,
                    style=style,
                    use_speaker_boost=speaker_boost,
                    optimize_streaming_latency=latency or 0,
                ):
                    audio_chunks.append(chunk)
                    progress.update(
                        task,
                        description=f"Received {len(audio_chunks)} chunks...",
                    )

                audio_data = b"".join(audio_chunks)
                progress.update(task, description="Complete!")

        else:
            # Non-streaming mode
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Generating audio...", total=None)
                audio_data = service.text_to_speech(
                    text,
                    voice=voice,
                    model=model,
                    output_format=format,
                    stability=stability,
                    similarity_boost=similarity,
                    style=style,
                    use_speaker_boost=speaker_boost,
                    optimize_streaming_latency=latency,
                )
                progress.update(task, description="Complete!")

        # Save audio
        service.save_audio(audio_data, output)
        console.print(f"\n[green]✓ Audio saved to:[/green] {output}")
        console.print(f"  Size: {len(audio_data):,} bytes")

        # Play audio if requested
        if play:
            try:
                from pydub import AudioSegment
                from pydub.playback import play as play_audio

                console.print("\n[cyan]Playing audio...[/cyan]")
                audio = AudioSegment.from_file(output)
                play_audio(audio)
                console.print("[green]✓ Playback complete![/green]")

            except ImportError:
                console.print(
                    "\n[yellow]⚠ Playback unavailable: "
                    "Missing dependencies[/yellow]",
                )
                console.print(
                    "  Install with: pip install pydub simpleaudio",
                )
            except Exception as e:
                console.print(f"\n[yellow]⚠ Playback failed: {e}[/yellow]")

    except Exception as e:
        console.print(f"\n[red]✗ Error: {e}[/red]")
        raise click.Abort()


@elevenlabs_group.command(name="list-voices")
def list_voices() -> None:
    """List available default voices."""
    try:
        service = ElevenLabsAudioService()
        voices = service.list_available_voices()

        console.print("\n[cyan]Available ElevenLabs Voices:[/cyan]\n")

        for name, voice_id in sorted(voices.items()):
            console.print(f"  • {name:<15} {voice_id}")

        console.print(f"\n[dim]Total: {len(voices)} voices[/dim]")
        console.print(
            '\n[dim]Use with: ei elevenlabs speak "text" '
            "-o output.mp3 -v <voice_name>[/dim]",
        )

    except Exception as e:
        console.print(f"\n[red]✗ Error: {e}[/red]")
        raise click.Abort()


@elevenlabs_group.command(name="list-models")
def list_models() -> None:
    """List available models."""
    try:
        service = ElevenLabsAudioService()
        models = service.get_available_models()

        console.print("\n[cyan]Available ElevenLabs Models:[/cyan]\n")

        model_info = {
            "eleven_multilingual_v2": (
                "Highest quality, 29 languages, stable"
            ),
            "eleven_flash_v2_5": (
                "Ultra-low latency, 32 languages, 50% cheaper"
            ),
            "eleven_turbo_v2_5": (
                "Balanced speed/quality, 32 languages"
            ),
        }

        for m in models:
            info = model_info.get(m, "")
            console.print(f"  • {m}")
            console.print(f"    {info}")
            console.print()

        console.print(
            '[dim]Use with: ei elevenlabs speak "text" '
            "-o output.mp3 -m <model>[/dim]",
        )

    except Exception as e:
        console.print(f"\n[red]✗ Error: {e}[/red]")
        raise click.Abort()

