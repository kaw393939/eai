"""
Smoke tests for the main CLI application.
"""
from click.testing import CliRunner

from ei_cli.cli.app import cli, main


class TestCLIApp:
    """Test main CLI application."""

    def test_cli_help(self):
        """Test CLI shows help message."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "EverydayAI CLI" in result.output
        assert "Personal AI toolkit for regular people" in result.output

    def test_cli_version(self):
        """Test CLI shows version."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "ei, version 0.1.0" in result.output

    def test_cli_has_crop_command(self):
        """Test crop command is registered."""
        runner = CliRunner()
        result = runner.invoke(cli, ["crop", "--help"])
        assert result.exit_code == 0
        assert "crop" in result.output.lower()

    def test_cli_has_image_command(self):
        """Test image command is registered."""
        runner = CliRunner()
        result = runner.invoke(cli, ["image", "--help"])
        assert result.exit_code == 0
        assert "image" in result.output.lower()

    def test_cli_has_remove_bg_command(self):
        """Test remove-bg command is registered."""
        runner = CliRunner()
        result = runner.invoke(cli, ["remove-bg", "--help"])
        assert result.exit_code == 0
        output = result.output.lower()
        assert "remove" in output or "background" in output

    def test_cli_has_search_command(self):
        """Test search command is registered."""
        runner = CliRunner()
        result = runner.invoke(cli, ["search", "--help"])
        assert result.exit_code == 0
        assert "search" in result.output.lower()

    def test_cli_has_vision_command(self):
        """Test vision command is registered."""
        runner = CliRunner()
        result = runner.invoke(cli, ["vision", "--help"])
        assert result.exit_code == 0
        assert "vision" in result.output.lower()

    def test_cli_invalid_command(self):
        """Test CLI handles invalid command."""
        runner = CliRunner()
        result = runner.invoke(cli, ["invalid-command"])
        assert result.exit_code != 0
        assert "Error" in result.output or "No such command" in result.output

    def test_main_entry_point(self):
        """Test main entry point function."""
        # Just verify it's callable - actual execution would need mocking
        assert callable(main)
        assert main.__name__ == "main"
