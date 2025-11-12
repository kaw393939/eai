"""
Search command for ei CLI.

Provides web search with citations and sources.
"""

from datetime import datetime
from pathlib import Path
from typing import Any

import click
from click.exceptions import Exit
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from ei_cli.cli.utils import require_api_key
from ei_cli.core.errors import MissingAPIKeyError
from ei_cli.services.ai_service import SearchCitation
from ei_cli.services.base import ServiceError
from ei_cli.services.factory import ServiceFactory


def _save_search_results(
    output_path: Path,
    query: str,
    answer: str,
    citations: list[SearchCitation],
    sources: list[str],
) -> None:
    """
    Save search results to Markdown file.
    
    Args:
        output_path: Path to save file
        query: Search query
        answer: Search answer
        citations: List of citations
        sources: List of sources
    """
    # Create parent directory if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Build Markdown content
    content = [
        f"# Search Results: {query}",
        "",
        f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Answer",
        "",
        answer,
        "",
    ]

    # Add citations if available
    if citations:
        content.extend([
            "## Citations",
            "",
        ])
        for i, citation in enumerate(citations, 1):
            content.append(f"{i}. [{citation.title}]({citation.url})")
        content.append("")

    # Add sources if available
    if sources:
        content.extend([
            "## All Sources Consulted",
            "",
        ])
        for i, source in enumerate(sources, 1):
            content.append(f"{i}. {source}")
        content.append("")

    # Write to file
    output_path.write_text("\n".join(content), encoding="utf-8")


def _build_user_location(
    country: str | None,
    city: str | None,
) -> dict[str, str] | None:
    """Build user location dictionary from country and city."""
    if not country and not city:
        return None

    location = {}
    if country:
        location["country"] = country
    if city:
        location["city"] = city
    return location


def _create_location_dict(
    country: str | None,
    city: str | None,
) -> dict[str, str]:  # pragma: no cover
    """Create location dictionary from country and city."""
    location = {}
    if country:
        location["country"] = country
    if city:
        location["city"] = city
    return location


def _handle_tool_unavailable(  # pragma: no cover
    console: Console,
    error: str | None,
) -> None:
    """Handle when search tool is unavailable."""
    console.print(
        f"[red]✗[/red] Search tool not available: {error}",
    )
    console.print(
        "\n[yellow]Tip:[/yellow] Set your OpenAI API key:",
    )
    console.print("  export API__OPENAI_API_KEY=your-key-here")
    raise Exit(1) from None


def _display_json_output(
    console: Console,
    query: str,
    answer: str,
    citations: list[dict[str, Any]],
    sources: list[str],
    metadata: dict[str, Any] | None,
) -> None:
    """Display search results as JSON."""
    output = {
        "query": query,
        "answer": answer,
        "citations": citations,
        "sources": sources,
        "metadata": metadata,
    }
    console.print_json(data=output)


def _display_answer(console: Console, answer: str) -> None:
    """Display the answer in a panel."""
    console.print()
    md = Markdown(answer)
    console.print(Panel(
        md,
        title="🔎 Answer",
        border_style="cyan",
        padding=(1, 2),
    ))


def _display_citations(
    console: Console,
    citations: list[SearchCitation],
) -> None:
    """Display citations in a table."""
    if not citations:
        return

    console.print("\n[bold cyan]📚 Citations:[/bold cyan]\n")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Source", style="cyan")
    table.add_column("Title", style="green")

    for citation in citations:
        table.add_row(
            citation.url,
            citation.title,
        )

    console.print(table)


def _display_sources(
    console: Console,
    sources: list[str],
) -> None:  # pragma: no cover
    """Display all sources consulted in a table."""
    if not sources:
        return

    console.print()
    sources_table = Table(
        title="🔍 All Sources Consulted",
        show_header=True,
        header_style="bold green",
    )
    sources_table.add_column("#", style="dim", width=3)
    sources_table.add_column("URL", style="blue")

    for idx, source in enumerate(sources, 1):
        sources_table.add_row(str(idx), source)

    console.print(sources_table)


def _display_metadata(
    console: Console,
    metadata: dict[str, Any] | None,
) -> None:
    """Display metadata about the search."""
    if not metadata:
        return

    console.print()
    console.print(
        f"[dim]Model: {metadata.get('model')} | "
        f"Citations: {metadata.get('num_citations')} | "
        f"Sources: {metadata.get('num_sources')}[/dim]",
    )


def _display_rich_output(
    console: Console,
    answer: str,
    citations: list[SearchCitation],
    sources: list[str],
    metadata: dict[str, Any] | None,
    show_sources: bool,
) -> None:
    """Display search results with rich formatting."""
    _display_answer(console, answer)
    _display_citations(console, citations)

    if show_sources:
        _display_sources(console, sources)

    _display_metadata(console, metadata)


def _display_citations_and_sources(
    console: Console,
    citations: list[SearchCitation],
    sources: list[str],
    show_sources: bool,
) -> None:
    """Display only citations and sources (for streaming mode)."""
    _display_citations(console, citations)

    if show_sources:
        _display_sources(console, sources)


def _handle_missing_api_key(console: Console) -> None:  # pragma: no cover
    """Handle missing API key error."""
    console.print("[red]✗[/red] Missing API key: API__OPENAI_API_KEY not set")
    console.print(
        "\n[yellow]Set your OpenAI API key:[/yellow]",
    )
    console.print("  export API__OPENAI_API_KEY=your-key-here")
    raise Exit(1) from None


def _handle_service_error(
    console: Console,
    error: ServiceError,
) -> None:
    """Handle service error."""
    console.print(f"[red]✗[/red] {error}")
    raise Exit(1) from None


def _handle_unexpected_error(  # pragma: no cover
    console: Console,
    error: Exception,
) -> None:
    """Handle unexpected error."""
    console.print(f"[red]✗[/red] Unexpected error: {error}")
    raise Exit(1) from None


@click.command()
@click.argument("query", required=True)
@click.option(
    "--domains",
    "-d",
    multiple=True,
    help="Restrict search to specific domains (can be used multiple times)",
)
@click.option(
    "--model",
    "-m",
    default="gpt-4o-mini",
    help="Model to use (currently uses configured model from config)",
)
@click.option(
    "--country",
    "-c",
    help="Country code for location-based search (e.g., US, GB)",
)
@click.option(
    "--city",
    help="City for location-based search",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output results as JSON",
)
@click.option(
    "--show-sources",
    is_flag=True,
    help="Show all sources consulted (not just citations)",
)
@click.option(
    "--output",
    "-o",
    "output_file",
    type=click.Path(),
    help="Save results to Markdown file",
)
@click.option(
    "--stream",
    is_flag=True,
    help="Stream the response in real-time",
)
def search(
    query: str,
    domains: tuple[str, ...],
    model: str,  # noqa: ARG001 - Kept for CLI backward compatibility
    country: str | None,
    city: str | None,
    output_json: bool,
    show_sources: bool,
    output_file: str | None,
    stream: bool,
) -> None:
    """
    Search the web for current information.

    Examples:

    \b
        ei search "best AI productivity tools 2025"
        ei search "Python async" --domains python.org
        ei search "restaurants near me" --country US --city "New York"
        ei search "AI news" --output results.md
        ei search "breaking news" --stream
    """
    # Check API key is configured
    require_api_key()

    console = Console()
    user_location = _build_user_location(country, city)

    try:
        # Get AI service from factory
        factory = ServiceFactory()
        ai_service = factory.get_ai_service()

        # Check if service is available
        is_available, _ = ai_service.check_available()
        if not is_available:  # pragma: no cover
            _handle_missing_api_key(console)

        # Execute search
        if stream:
            # Streaming search
            console.print(f"\n[bold cyan]🔎 Searching:[/bold cyan] {query}")
            console.print()

            answer_parts = []
            citations = []
            sources = []

            for event in ai_service.search_stream(
                query=query,
                allowed_domains=list(domains) if domains else None,
                user_location=user_location,
            ):
                if event["type"] == "text_delta":
                    # Print streaming text
                    console.print(event["content"], end="")
                    answer_parts.append(event["content"])
                elif event["type"] == "search_complete":
                    # Store final metadata
                    citations = event["citations"]
                    sources = event["sources"]

            # Combine streamed parts for saving
            search_result = type("SearchResult", (), {
                "answer": "".join(answer_parts),
                "citations": citations,
                "sources": sources,
            })()

            console.print("\n")
        else:
            # Non-streaming search
            with console.status("[bold green]Searching...", spinner="dots"):
                search_result = ai_service.search(
                    query=query,
                    allowed_domains=list(domains) if domains else None,
                    user_location=user_location,
                )

        # Save to file if requested
        if output_file:
            output_path = Path(output_file)
            _save_search_results(
                output_path,
                query,
                search_result.answer,
                search_result.citations,
                search_result.sources,
            )
            if not output_json:
                console.print(f"\n[green]✓[/green] Results saved to {output_path}")

        # Display results
        if output_json:
            _display_json_output(
                console,
                query,
                search_result.answer,
                search_result.citations,
                search_result.sources,
                {},  # No metadata from service
            )
        elif not stream:
            # For non-streaming, display the full rich output
            _display_rich_output(
                console,
                search_result.answer,
                search_result.citations,
                search_result.sources,
                {},  # No metadata from service
                show_sources,
            )
        else:
            # For streaming, only display citations/sources (answer already streamed)
            _display_citations_and_sources(
                console,
                search_result.citations,
                search_result.sources,
                show_sources,
            )

    except MissingAPIKeyError:
        _handle_missing_api_key(console)
    except ServiceError as e:
        _handle_service_error(console, e)
    except Exception as e:
        _handle_unexpected_error(console, e)
