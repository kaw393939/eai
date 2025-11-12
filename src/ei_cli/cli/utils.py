"""
CLI utility functions.
"""
import sys

import click

from ei_cli.config import get_settings


def require_api_key() -> None:
    """
    Validate that OpenAI API key is configured.

    This should be called at the beginning of commands that require
    the API key. Exits with error message if key is not configured.
    """
    try:
        settings = get_settings()
        api_key = settings.api.openai_api_key.get_secret_value()

        if not api_key or api_key == "":
            click.echo(
                click.style(
                    "❌ Error: OpenAI API key not configured", fg="red",
                ),
                err=True,
            )
            click.echo(
                "\nPlease set your API key in one of these ways:",
                err=True,
            )
            click.echo(
                "  1. Environment variable: export "
                "API__OPENAI_API_KEY=sk-...",
                err=True,
            )
            click.echo(
                "  2. Create .env file with: API__OPENAI_API_KEY=sk-...",
                err=True,
            )
            click.echo(
                "  3. Use --config flag with YAML/JSON config file",
                err=True,
            )
            click.echo(
                "\nGet your API key from: "
                "https://platform.openai.com/api-keys",
                err=True,
            )
            sys.exit(1)

    except Exception as e:
        click.echo(
            click.style(f"❌ Configuration Error: {e}", fg="red"),
            err=True,
        )
        sys.exit(1)
