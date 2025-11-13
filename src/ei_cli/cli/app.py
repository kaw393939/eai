"""
Main CLI application with plugin-based command loading.
"""
import sys
from pathlib import Path

import click

from ei_cli import __version__
from ei_cli.config import reload_settings
from ei_cli.plugins.loader import PluginLoader


@click.group()
@click.version_option(version=__version__, prog_name="eai")
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


# Register commands dynamically from plugins
_plugin_loader = PluginLoader()
_plugin_loader.discover_plugins()
_plugin_loader.register_commands(cli)


def main() -> None:  # pragma: no cover
    """Entry point for poetry script."""
    cli()


if __name__ == "__main__":  # pragma: no cover
    main()
