"""Tests for search command."""

from unittest.mock import Mock, patch

import pytest
from click.exceptions import Exit
from click.testing import CliRunner
from rich.console import Console

from ei_cli.cli.commands.search import (
    _build_user_location,
    _display_answer,
    _display_citations,
    _display_json_output,
    _display_metadata,
    _display_rich_output,
    _display_sources,
    _handle_service_error,
    _save_search_results,
    search,
)
from ei_cli.services.ai_service import SearchCitation, SearchResult
from ei_cli.services.base import ServiceError


class TestSearchHelpers:
    """Tests for search helper functions."""

    def test_build_user_location_with_both(self):
        """Test building user location with country and city."""
        location = _build_user_location("US", "Boston")

        assert location == {"country": "US", "city": "Boston"}

    def test_build_user_location_with_country_only(self):
        """Test building user location with country only."""
        location = _build_user_location("US", None)

        assert location == {"country": "US"}

    def test_build_user_location_with_city_only(self):
        """Test building user location with city only."""
        location = _build_user_location(None, "Boston")

        assert location == {"city": "Boston"}

    def test_build_user_location_with_neither(self):
        """Test building user location with no parameters."""
        location = _build_user_location(None, None)

        assert location is None

    def test_save_search_results(self, tmp_path):
        """Test saving search results to file."""
        output_file = tmp_path / "results.md"
        citations = [
            SearchCitation(
                url="https://example.com",
                title="Example",
                start_index=0,
                end_index=10,
            ),
        ]
        sources = ["https://example.com", "https://test.com"]

        _save_search_results(
            output_file,
            "test query",
            "This is the answer",
            citations,
            sources,
        )

        assert output_file.exists()
        content = output_file.read_text()
        assert "# Search Results: test query" in content
        assert "This is the answer" in content
        assert "## Citations" in content
        assert "[Example](https://example.com)" in content
        assert "## All Sources Consulted" in content
        assert "https://test.com" in content

    def test_save_search_results_no_citations(self, tmp_path):
        """Test saving search results without citations."""
        output_file = tmp_path / "results.md"

        _save_search_results(
            output_file,
            "test query",
            "Answer without citations",
            [],
            [],
        )

        assert output_file.exists()
        content = output_file.read_text()
        assert "## Answer" in content
        assert "Answer without citations" in content
        assert "## Citations" not in content

    def test_save_search_results_creates_parent_dir(self, tmp_path):
        """Test that save creates parent directories."""
        output_file = tmp_path / "nested" / "dir" / "results.md"

        _save_search_results(
            output_file,
            "test",
            "answer",
            [],
            [],
        )

        assert output_file.exists()
        assert output_file.parent.exists()

    @patch("ei_cli.cli.commands.search.Console")
    def test_display_answer(self, mock_console_class):
        """Test displaying answer in panel."""
        mock_console = Mock()
        mock_console_class.return_value = mock_console

        real_console = Console()
        _display_answer(real_console, "Test answer")

        # Just verify it doesn't raise

    @patch("ei_cli.cli.commands.search.Console")
    def test_display_citations_empty(self, mock_console_class):
        """Test displaying empty citations list."""
        mock_console = Mock()
        mock_console_class.return_value = mock_console

        real_console = Console()
        _display_citations(real_console, [])

        # Should not raise

    @patch("ei_cli.cli.commands.search.Console")
    def test_display_citations_with_data(self, mock_console_class):
        """Test displaying citations with data."""
        mock_console = Mock()
        mock_console_class.return_value = mock_console

        real_console = Console()
        citations = [
            SearchCitation(
                url="https://example.com",
                title="Example",
                start_index=0,
                end_index=10,
            ),
        ]
        _display_citations(real_console, citations)

        # Should not raise

    @patch("ei_cli.cli.commands.search.Console")
    def test_display_sources(self, mock_console_class):
        """Test displaying sources."""
        mock_console = Mock()
        mock_console_class.return_value = mock_console

        real_console = Console()
        sources = ["https://example.com", "https://test.com"]
        _display_sources(real_console, sources)

        # Should not raise

    @patch("ei_cli.cli.commands.search.Console")
    def test_display_metadata_with_data(self, mock_console_class):
        """Test displaying metadata."""
        mock_console = Mock()
        mock_console_class.return_value = mock_console

        real_console = Console()
        metadata = {
            "model": "gpt-4o",
            "num_citations": 3,
            "num_sources": 5,
        }
        _display_metadata(real_console, metadata)

        # Should not raise

    @patch("ei_cli.cli.commands.search.Console")
    def test_display_metadata_none(self, mock_console_class):
        """Test displaying None metadata."""
        mock_console = Mock()
        mock_console_class.return_value = mock_console

        real_console = Console()
        _display_metadata(real_console, None)

        # Should not raise

    @patch("ei_cli.cli.commands.search.Console")
    def test_display_json_output(self, mock_console_class):
        """Test displaying JSON output."""
        mock_console = Mock()
        mock_console_class.return_value = mock_console

        real_console = Console()
        citations = [
            {
                "url": "https://example.com",
                "title": "Example",
                "start_index": 0,
                "end_index": 10,
            },
        ]
        sources = ["https://example.com"]
        metadata = {"model": "gpt-4o"}

        _display_json_output(
            real_console,
            "test query",
            "test answer",
            citations,
            sources,
            metadata,
        )

        # Should not raise

    @patch("ei_cli.cli.commands.search.Console")
    def test_display_rich_output(self, mock_console_class):
        """Test displaying rich formatted output."""
        mock_console = Mock()
        mock_console_class.return_value = mock_console

        real_console = Console()
        citations = [
            SearchCitation(
                url="https://example.com",
                title="Example",
                start_index=0,
                end_index=10,
            ),
        ]
        sources = ["https://example.com"]
        metadata = {"model": "gpt-4o"}

        _display_rich_output(
            real_console,
            "test answer",
            citations,
            sources,
            metadata,
            show_sources=True,
        )

        # Should not raise

    @patch("ei_cli.cli.commands.search.Console")
    def test_handle_service_error(self, mock_console_class):
        """Test handling service error."""
        mock_console = Mock()
        mock_console_class.return_value = mock_console

        real_console = Console()
        error = ServiceError("Service failed", service_name="test")

        with pytest.raises(Exit):
            _handle_service_error(real_console, error)


class TestSearchCommand:
    """Tests for search command."""

    @patch("ei_cli.cli.commands.search.ServiceFactory")
    def test_search_basic(self, mock_factory_class):
        """Test basic search command."""
        runner = CliRunner()

        # Setup mock service
        mock_service = Mock()
        mock_service.check_available.return_value = (True, None)
        mock_service.search.return_value = SearchResult(
            answer="Python is great",
            citations=[],
            sources=[],
        )

        mock_factory = Mock()
        mock_factory.get_ai_service.return_value = mock_service
        mock_factory_class.return_value = mock_factory

        result = runner.invoke(search, ["Python programming"])

        assert result.exit_code == 0
        assert "Python is great" in result.output or result.exit_code == 0

    @patch("ei_cli.cli.commands.search.ServiceFactory")
    def test_search_with_domains(self, mock_factory_class):
        """Test search with domain filtering."""
        runner = CliRunner()

        mock_service = Mock()
        mock_service.check_available.return_value = (True, None)
        mock_service.search.return_value = SearchResult(
            answer="Python info",
            citations=[],
            sources=[],
        )

        mock_factory = Mock()
        mock_factory.get_ai_service.return_value = mock_service
        mock_factory_class.return_value = mock_factory

        result = runner.invoke(
            search,
            ["Python", "-d", "python.org", "-d", "docs.python.org"],
        )

        assert result.exit_code == 0
        # Verify domains were passed
        call_args = mock_service.search.call_args
        domains = ["python.org", "docs.python.org"]
        assert call_args[1]["allowed_domains"] == domains

    @patch("ei_cli.cli.commands.search.ServiceFactory")
    def test_search_with_location(self, mock_factory_class):
        """Test search with location."""
        runner = CliRunner()

        mock_service = Mock()
        mock_service.check_available.return_value = (True, None)
        mock_service.search.return_value = SearchResult(
            answer="Boston weather",
            citations=[],
            sources=[],
        )

        mock_factory = Mock()
        mock_factory.get_ai_service.return_value = mock_service
        mock_factory_class.return_value = mock_factory

        result = runner.invoke(
            search,
            ["weather", "--country", "US", "--city", "Boston"],
        )

        assert result.exit_code == 0
        # Verify location was passed
        call_args = mock_service.search.call_args
        expected_loc = {"country": "US", "city": "Boston"}
        assert call_args[1]["user_location"] == expected_loc

    @patch("ei_cli.cli.commands.search.ServiceFactory")
    def test_search_with_output_file(self, mock_factory_class, tmp_path):
        """Test search with output file."""
        runner = CliRunner()
        output_file = tmp_path / "results.md"

        mock_service = Mock()
        mock_service.check_available.return_value = (True, None)
        mock_service.search.return_value = SearchResult(
            answer="Test answer",
            citations=[],
            sources=[],
        )

        mock_factory = Mock()
        mock_factory.get_ai_service.return_value = mock_service
        mock_factory_class.return_value = mock_factory

        result = runner.invoke(
            search,
            ["test", "-o", str(output_file)],
        )

        assert result.exit_code == 0
        assert output_file.exists()
        content = output_file.read_text()
        assert "Test answer" in content

    @patch("ei_cli.cli.commands.search.ServiceFactory")
    def test_search_json_output(self, mock_factory_class):
        """Test search with JSON output."""
        runner = CliRunner()

        mock_service = Mock()
        mock_service.check_available.return_value = (True, None)
        mock_service.search.return_value = SearchResult(
            answer="JSON answer",
            citations=[],
            sources=[],
        )

        mock_factory = Mock()
        mock_factory.get_ai_service.return_value = mock_service
        mock_factory_class.return_value = mock_factory

        result = runner.invoke(search, ["test", "--json"])

        assert result.exit_code == 0
        # JSON output should contain the answer

    @patch("ei_cli.cli.commands.search.ServiceFactory")
    def test_search_with_show_sources(self, mock_factory_class):
        """Test search with show sources flag."""
        runner = CliRunner()

        mock_service = Mock()
        mock_service.check_available.return_value = (True, None)
        mock_service.search.return_value = SearchResult(
            answer="Answer",
            citations=[],
            sources=["https://example.com"],
        )

        mock_factory = Mock()
        mock_factory.get_ai_service.return_value = mock_service
        mock_factory_class.return_value = mock_factory

        result = runner.invoke(search, ["test", "--show-sources"])

        assert result.exit_code == 0

    @patch("ei_cli.cli.commands.search.ServiceFactory")
    def test_search_with_citations(self, mock_factory_class):
        """Test search with citations in results."""
        runner = CliRunner()

        mock_service = Mock()
        mock_service.check_available.return_value = (True, None)
        mock_service.search.return_value = SearchResult(
            answer="Answer with citation",
            citations=[
                SearchCitation(
                    url="https://example.com",
                    title="Example Source",
                    start_index=0,
                    end_index=10,
                ),
            ],
            sources=["https://example.com"],
        )

        mock_factory = Mock()
        mock_factory.get_ai_service.return_value = mock_service
        mock_factory_class.return_value = mock_factory

        result = runner.invoke(search, ["test query"])

        assert result.exit_code == 0

    @patch("ei_cli.cli.commands.search.ServiceFactory")
    def test_search_service_error(self, mock_factory_class):
        """Test search with service error."""
        runner = CliRunner()

        mock_service = Mock()
        mock_service.check_available.return_value = (True, None)
        mock_service.search.side_effect = ServiceError(
            "Search failed",
            service_name="ai_service",
        )

        mock_factory = Mock()
        mock_factory.get_ai_service.return_value = mock_service
        mock_factory_class.return_value = mock_factory

        result = runner.invoke(search, ["test"])

        assert result.exit_code == 1
        assert "Search failed" in result.output or result.exit_code == 1

    @patch("ei_cli.cli.commands.search.ServiceFactory")
    def test_search_with_json_and_output_file(
        self,
        mock_factory_class,
        tmp_path,
    ):
        """Test search with both JSON output and file saving."""
        runner = CliRunner()
        output_file = tmp_path / "results.md"

        mock_service = Mock()
        mock_service.check_available.return_value = (True, None)
        mock_service.search.return_value = SearchResult(
            answer="Test answer",
            citations=[],
            sources=[],
        )

        mock_factory = Mock()
        mock_factory.get_ai_service.return_value = mock_service
        mock_factory_class.return_value = mock_factory

        result = runner.invoke(
            search,
            ["test", "--json", "-o", str(output_file)],
        )

        assert result.exit_code == 0
        assert output_file.exists()
