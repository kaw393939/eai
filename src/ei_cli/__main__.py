"""
Main entry point for ei CLI.

Usage:
    python -m ei_cli [command] [options]
"""
import sys


def main() -> None:
    """Main entry point."""
    from ei_cli.cli.app import cli

    try:
        cli()
    except KeyboardInterrupt:
        sys.exit(130)  # Standard Unix signal exit code
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)  # noqa: T201
        sys.exit(2)


if __name__ == "__main__":
    main()
