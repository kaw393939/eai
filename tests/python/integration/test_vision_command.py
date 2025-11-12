"""
Integration tests for vision CLI command.

Tests the vision command's argument parsing, error handling, and output formatting.
"""

from unittest.mock import Mock, patch

from click.testing import CliRunner

from ei_cli.cli.commands.vision import vision
from ei_cli.core.errors import MissingAPIKeyError
from ei_cli.services.ai_service import VisionResult
from ei_cli.services.base import ServiceError


class TestVisionCommandBasic:
    """Basic tests for vision command."""

    @patch("ei_cli.cli.commands.vision.ServiceFactory")
    def test_vision_basic_usage(self, mock_factory_class: Mock) -> None:
        """Test basic vision command with image argument."""
        mock_service = Mock()
        mock_service.check_available.return_value = (True, None)
        mock_service.analyze_image.return_value = VisionResult(
            analysis="A beautiful sunset over mountains",
            model="gpt-5",
            image_source="image.jpg",
            prompt="Describe this image in detail.",
        )
        mock_factory = Mock()
        mock_factory.get_ai_service.return_value = mock_service
        mock_factory_class.return_value = mock_factory

        runner = CliRunner()
        result = runner.invoke(vision, ["image.jpg"])

        assert result.exit_code == 0
        assert "Vision Analysis" in result.output
        assert "beautiful sunset" in result.output

    @patch("ei_cli.cli.commands.vision.ServiceFactory")
    def test_vision_with_custom_prompt(self, mock_factory_class: Mock) -> None:
        """Test vision command with custom prompt."""
        mock_service = Mock()
        mock_service.check_available.return_value = (True, None)
        mock_service.analyze_image.return_value = VisionResult(
            analysis="Red, blue, and yellow",
            model="gpt-5",
            image_source="image.jpg",
            prompt="What colors are in this image?",
        )
        mock_factory = Mock()
        mock_factory.get_ai_service.return_value = mock_service
        mock_factory_class.return_value = mock_factory

        runner = CliRunner()
        result = runner.invoke(
            vision,
            ["image.jpg", "--prompt", "What colors are in this image?"],
        )

        assert result.exit_code == 0
        assert "What colors are in this image?" in result.output

    @patch("ei_cli.cli.commands.vision.ServiceFactory")
    def test_vision_with_detail_level(self, mock_factory_class: Mock) -> None:
        """Test vision command with detail level."""
        mock_service = Mock()
        mock_service.check_available.return_value = (True, None)
        mock_service.analyze_image.return_value = VisionResult(
            analysis="Detailed analysis",
            model="gpt-5",
            image_source="image.jpg",
            prompt="Describe this image in detail.",
        )
        mock_factory = Mock()
        mock_factory.get_ai_service.return_value = mock_service
        mock_factory_class.return_value = mock_factory

        runner = CliRunner()
        result = runner.invoke(vision, ["image.jpg", "--detail", "high"])

        assert result.exit_code == 0
        call_kwargs = mock_service.analyze_image.call_args[1]
        assert call_kwargs["detail_level"] == "high"


class TestVisionCommandJsonOutput:
    """Tests for JSON output format."""

    @patch("ei_cli.cli.commands.vision.ServiceFactory")
    def test_vision_json_output(self, mock_factory_class: Mock) -> None:
        """Test vision command with JSON output."""
        mock_service = Mock()
        mock_service.check_available.return_value = (True, None)
        mock_service.analyze_image.return_value = VisionResult(
            analysis="Test analysis",
            model="gpt-5",
            image_source="image.jpg",
            prompt="Describe this image in detail.",
        )
        mock_factory = Mock()
        mock_factory.get_ai_service.return_value = mock_service
        mock_factory_class.return_value = mock_factory

        runner = CliRunner()
        result = runner.invoke(vision, ["image.jpg", "--json"])

        assert result.exit_code == 0
        assert "analysis" in result.output
        assert "model" in result.output
        assert "image_source" in result.output


class TestVisionCommandErrors:
    """Tests for error handling."""

    @patch("ei_cli.cli.commands.vision.ServiceFactory")
    def test_vision_service_unavailable(
        self,
        mock_factory_class: Mock,
    ) -> None:
        """Test handling when vision service is unavailable."""
        mock_service = Mock()
        mock_service.check_available.return_value = (
            False,
            "Missing API key",
        )
        mock_factory = Mock()
        mock_factory.get_ai_service.return_value = mock_service
        mock_factory_class.return_value = mock_factory

        runner = CliRunner()
        result = runner.invoke(vision, ["image.jpg"])

        assert result.exit_code == 1
        assert "not available" in result.output
        assert "API__OPENAI_API_KEY" in result.output

    @patch("ei_cli.cli.commands.vision.ServiceFactory")
    def test_vision_missing_api_key_error(
        self,
        mock_factory_class: Mock,
    ) -> None:
        """Test handling MissingAPIKeyError."""
        mock_service = Mock()
        mock_service.check_available.return_value = (True, None)
        mock_service.analyze_image.side_effect = MissingAPIKeyError(
            message="API key not found",
        )
        mock_factory = Mock()
        mock_factory.get_ai_service.return_value = mock_service
        mock_factory_class.return_value = mock_factory

        runner = CliRunner()
        result = runner.invoke(vision, ["image.jpg"])

        assert result.exit_code == 1
        assert "Missing API key" in result.output

    @patch("ei_cli.cli.commands.vision.ServiceFactory")
    def test_vision_service_error(self, mock_factory_class: Mock) -> None:
        """Test handling ServiceError."""
        mock_service = Mock()
        mock_service.check_available.return_value = (True, None)
        mock_service.analyze_image.side_effect = ServiceError(
            message="API request failed",
            service_name="ai_service",
        )
        mock_factory = Mock()
        mock_factory.get_ai_service.return_value = mock_service
        mock_factory_class.return_value = mock_factory

        runner = CliRunner()
        result = runner.invoke(vision, ["image.jpg"])

        assert result.exit_code == 1
        assert "API request failed" in result.output

    @patch("ei_cli.cli.commands.vision.ServiceFactory")
    def test_vision_unexpected_error(self, mock_factory_class: Mock) -> None:
        """Test handling unexpected errors."""
        mock_service = Mock()
        mock_service.check_available.return_value = (True, None)
        mock_service.analyze_image.side_effect = Exception("Unexpected error")
        mock_factory = Mock()
        mock_factory.get_ai_service.return_value = mock_service
        mock_factory_class.return_value = mock_factory

        runner = CliRunner()
        result = runner.invoke(vision, ["image.jpg"])

        assert result.exit_code == 1
        assert "Unexpected error" in result.output

    def test_vision_missing_image_argument(self) -> None:
        """Test error when image argument is missing."""
        runner = CliRunner()
        result = runner.invoke(vision, [])

        assert result.exit_code != 0
        assert (
            "Missing argument" in result.output or "IMAGE" in result.output
        )


class TestVisionCommandOptions:
    """Tests for command options."""

    def test_vision_help(self) -> None:
        """Test vision command help."""
        runner = CliRunner()
        result = runner.invoke(vision, ["--help"])

        assert result.exit_code == 0
        assert "Analyze images" in result.output
        assert "--prompt" in result.output
        assert "--model" in result.output
        assert "--detail" in result.output
