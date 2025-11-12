"""YouTube authentication setup commands."""

import subprocess
from datetime import datetime, timedelta
from pathlib import Path

import click
from rich.console import Console
from rich.prompt import Confirm

console = Console()


@click.group(name="youtube")
def youtube_group() -> None:
    """Manage YouTube authentication and cookies."""


@youtube_group.command(name="setup")
@click.option(
    "--browser",
    "-b",
    type=click.Choice(["chrome", "firefox", "safari", "edge"], case_sensitive=False),
    default="chrome",
    help="Browser to extract cookies from",
)
@click.option(
    "--refresh",
    is_flag=True,
    help="Refresh existing cookies even if they're fresh",
)
def setup_youtube(browser: str, refresh: bool) -> None:
    """
    Setup YouTube authentication for downloading videos.

    Extracts cookies from your browser to enable downloading of
    age-restricted, members-only, or private videos that you have
    access to.

    Examples:

        \b
        # Setup using Chrome cookies
        ei-cli youtube setup

        \b
        # Setup using Safari cookies
        ei-cli youtube setup --browser safari

        \b
        # Force refresh cookies
        ei-cli youtube setup --refresh
    """
    cookie_file = Path.home() / ".ei_cli" / "youtube_cookies.txt"
    cookie_file.parent.mkdir(parents=True, exist_ok=True)

    # Check existing cookies
    if cookie_file.exists() and not refresh:
        age = datetime.now() - datetime.fromtimestamp(cookie_file.stat().st_mtime)

        console.print("[green]✓ Cookies found[/green]")
        console.print(f"  Location: {cookie_file}")
        console.print(f"  Age: {age.days} days old")

        if age.days > 7:
            console.print("\n[yellow]⚠️  Cookies are over 7 days old[/yellow]")
            console.print(
                "[dim]YouTube cookies typically expire after 14 days[/dim]",
            )
            if not Confirm.ask("Refresh cookies?", default=True):
                return
        else:
            console.print("[dim]Cookies are fresh, no action needed[/dim]")
            console.print(
                "\n[cyan]💡 Use --refresh to force update cookies[/cyan]",
            )
            return

    # Extract cookies
    console.print(f"\n[cyan]🍪 Extracting cookies from {browser}...[/cyan]")
    console.print("[dim]Make sure you're logged into YouTube in your browser[/dim]")

    try:
        # Use yt-dlp to extract cookies
        cmd = [
            "yt-dlp",
            "--cookies-from-browser",
            browser,
            "--cookies",
            str(cookie_file),
            "--skip-download",
            "--no-warnings",
            "--quiet",
            "https://www.youtube.com",
        ]

        result = subprocess.run(
            cmd,
            check=False, capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            console.print("\n[green bold]✓ Cookies saved successfully![/green bold]")
            console.print(f"  Location: {cookie_file}")
            console.print(
                "\n[dim]Cookies will be automatically used for YouTube downloads[/dim]",
            )
            console.print(
                "[dim]Run 'ei-cli youtube check' to verify cookie status[/dim]",
            )
        else:
            error_msg = result.stderr or result.stdout or "Unknown error"
            raise RuntimeError(error_msg)

    except FileNotFoundError:
        console.print("\n[red]✗ yt-dlp not found[/red]")
        console.print(
            "\n[yellow]Please install yt-dlp:[/yellow]",
        )
        console.print("  pip install yt-dlp")
        raise click.exceptions.Exit(1)

    except subprocess.TimeoutExpired:
        console.print("\n[red]✗ Cookie extraction timed out[/red]")
        console.print("\n[yellow]This might happen if:[/yellow]")
        console.print(f"  • {browser.title()} is not installed")
        console.print("  • Browser profile is locked")
        console.print("  • Browser needs to be updated")
        raise click.exceptions.Exit(1)

    except Exception as e:
        console.print("\n[red]✗ Failed to extract cookies[/red]")
        console.print(f"  Error: {e}")

        console.print("\n[yellow]📝 Manual setup instructions:[/yellow]")
        console.print("1. Login to YouTube in your browser")
        console.print("2. Install a browser extension for cookie export:")
        console.print("   • Chrome: 'Get cookies.txt LOCALLY'")
        console.print("   • Firefox: 'cookies.txt'")
        console.print("3. Export cookies in Netscape format")
        console.print(f"4. Save to: {cookie_file}")

        console.print("\n[yellow]Alternative: Use --cookies-from-browser flag:[/yellow]")
        console.print(
            f"  ei-cli transcribe-video <url> --cookies-from-browser {browser}",
        )

        raise click.exceptions.Exit(1)


@youtube_group.command(name="check")
def check_youtube() -> None:
    """
    Check YouTube authentication status.

    Shows the status of saved cookies including age and
    estimated expiry time.

    Example:

        \b
        ei-cli youtube check
    """
    cookie_file = Path.home() / ".ei_cli" / "youtube_cookies.txt"

    if not cookie_file.exists():
        console.print("[yellow]✗ No cookies configured[/yellow]")
        console.print(
            "\n[cyan]💡 Run 'ei-cli youtube setup' to configure YouTube authentication[/cyan]",
        )
        console.print(
            "[dim]This is only needed for age-restricted, members-only, or private videos[/dim]",
        )
        raise click.exceptions.Exit(1)

    age = datetime.now() - datetime.fromtimestamp(cookie_file.stat().st_mtime)

    # YouTube cookies typically last 14 days
    estimated_expiry_days = 14
    expires_in = timedelta(days=estimated_expiry_days) - age

    console.print("[green]✓ Cookies configured[/green]")
    console.print(f"  Location: {cookie_file}")
    console.print(f"  Size: {cookie_file.stat().st_size:,} bytes")
    console.print(f"  Age: {age.days} days")

    if expires_in.days > 0:
        console.print(f"  Estimated expiry: in {expires_in.days} days")

        if age.days > 10:
            console.print(
                "\n[yellow]⚠️  Cookies are getting old, consider refreshing soon[/yellow]",
            )
            console.print("  Run: [cyan]ei-cli youtube setup --refresh[/cyan]")
        else:
            console.print("\n[green]✓ Cookies are fresh[/green]")
    else:
        console.print("  Status: [red]Likely expired[/red]")
        console.print(
            "\n[yellow]⚠️  Cookies have likely expired, refresh recommended[/yellow]",
        )
        console.print("  Run: [cyan]ei-cli youtube setup --refresh[/cyan]")

    console.print("\n[dim]Note: YouTube cookies typically expire after 14 days of inactivity[/dim]")


@youtube_group.command(name="clear")
def clear_youtube() -> None:
    """
    Clear saved YouTube cookies.

    Removes the saved cookie file. You'll need to run 'setup'
    again if you want to download restricted videos.

    Example:

        \b
        ei-cli youtube clear
    """
    cookie_file = Path.home() / ".ei_cli" / "youtube_cookies.txt"

    if not cookie_file.exists():
        console.print("[yellow]No cookies to clear[/yellow]")
        return

    if Confirm.ask(
        "Are you sure you want to clear YouTube cookies?", default=False,
    ):
        cookie_file.unlink()
        console.print("[green]✓ Cookies cleared[/green]")
        console.print(
            "\n[dim]Run 'ei-cli youtube setup' to configure again[/dim]",
        )
    else:
        console.print("[dim]Cancelled[/dim]")
