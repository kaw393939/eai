"""
Main CLI application.
"""
import sys
from pathlib import Path

import click

from ei_cli.cli.commands.crop import crop
from ei_cli.cli.commands.image import image
from ei_cli.cli.commands.multi_vision import multi_vision
from ei_cli.cli.commands.remove_bg import remove_bg
from ei_cli.cli.commands.search import search
from ei_cli.cli.commands.setup_youtube import youtube_group
from ei_cli.cli.commands.speak import speak
from ei_cli.cli.commands.speak_elevenlabs import elevenlabs_group
from ei_cli.cli.commands.transcribe import transcribe
from ei_cli.cli.commands.transcribe_video import transcribe_video
from ei_cli.cli.commands.translate_audio import translate_audio
from ei_cli.cli.commands.vision import vision
from ei_cli.config import reload_settings


@click.group()
@click.version_option(version="0.1.0", prog_name="ei")
@click.option(
    "--config",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to YAML/JSON config file",
)
def cli(config: Path | None) -> None:
    """EverydayAI CLI - Personal AI toolkit for regular people."""
    # Load configuration if provided
    if config:
        try:
            reload_settings(config)
        except Exception as e:
            click.echo(
                click.style(f"❌ Configuration Error: {e}", fg="red"),
                err=True,
            )
            sys.exit(1)


# Register commands
cli.add_command(crop)
cli.add_command(elevenlabs_group)
cli.add_command(image)
cli.add_command(multi_vision)
cli.add_command(remove_bg)
cli.add_command(search)
cli.add_command(speak)
cli.add_command(transcribe)
cli.add_command(transcribe_video)
cli.add_command(translate_audio)
cli.add_command(vision)
cli.add_command(youtube_group)


def main() -> None:  # pragma: no cover
    """Entry point for poetry script."""
    cli()


if __name__ == "__main__":  # pragma: no cover
    main()
