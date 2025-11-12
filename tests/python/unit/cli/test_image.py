"""Tests for image CLI command."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from ei_cli.cli.commands.image import image
from ei_cli.core.errors import MissingAPIKeyError
from ei_cli.services.base import ServiceError


class TestImageCommand:
    """Test suite for image generation command."""

    @pytest.fixture
    def runner(self):
        """Create CLI runner."""
        return CliRunner()

    @pytest.fixture
    def mock_service_factory(self):
        """Mock ServiceFactory."""
        with patch("ei_cli.cli.commands.image.ServiceFactory") as mock:
            yield mock

    @pytest.fixture
    def mock_ai_service(self):
        """Create mock AI service with image result."""
        service = MagicMock()
        service.check_available.return_value = (True, None)

        # Mock image generation result
        result = MagicMock()
        result.image_url = "https://example.com/generated-image.png"
        result.local_path = None
        result.model = "gpt-image-1"
        result.revised_prompt = None
        service.generate_image.return_value = result

        return service

    def test_basic_image_generation(
        self, runner, mock_service_factory, mock_ai_service,
    ):
        """Test basic image generation."""
        mock_service_factory.return_value.get_ai_service.return_value = (
            mock_ai_service
        )

        result = runner.invoke(image, ["a beautiful sunset"])

        assert result.exit_code == 0
        assert "Image Generated Successfully" in result.output
        assert "https://example.com/generated-image.png" in result.output
        mock_ai_service.generate_image.assert_called_once()

    def test_image_with_size_option(
        self, runner, mock_service_factory, mock_ai_service,
    ):
        """Test image generation with custom size."""
        mock_service_factory.return_value.get_ai_service.return_value = (
            mock_ai_service
        )

        result = runner.invoke(
            image, ["a landscape", "--size", "1536x1024"],
        )

        assert result.exit_code == 0
        mock_ai_service.generate_image.assert_called_once_with(
            prompt="a landscape",
            size="1536x1024",
            quality="auto",
            output_path=None,
            show_progress=True,
        )

    def test_image_with_hd_quality(
        self, runner, mock_service_factory, mock_ai_service,
    ):
        """Test image generation with high quality."""
        mock_service_factory.return_value.get_ai_service.return_value = (
            mock_ai_service
        )

        result = runner.invoke(image, ["a portrait", "--quality", "high"])

        assert result.exit_code == 0
        assert "high" in result.output.lower()
        mock_ai_service.generate_image.assert_called_once_with(
            prompt="a portrait",
            size="1024x1024",
            quality="high",
            output_path=None,
            show_progress=True,
        )

    def test_image_with_natural_style(
        self, runner, mock_service_factory, mock_ai_service,
    ):
        """Test that style parameter is no longer used (option removed)."""
        mock_service_factory.return_value.get_ai_service.return_value = (
            mock_ai_service
        )

        result = runner.invoke(image, ["abstract art"])

        assert result.exit_code == 0
        mock_ai_service.generate_image.assert_called_once_with(
            prompt="abstract art",
            size="1024x1024",
            quality="auto",
            output_path=None,
            show_progress=True,
        )

    def test_image_with_output_file(
        self, runner, mock_service_factory, mock_ai_service, tmp_path,
    ):
        """Test image generation with output file."""
        output_file = tmp_path / "generated.png"
        mock_service_factory.return_value.get_ai_service.return_value = (
            mock_ai_service
        )
        mock_ai_service.generate_image.return_value.local_path = output_file

        result = runner.invoke(
            image, ["a cat", "--output", str(output_file)],
        )

        assert result.exit_code == 0
        assert "Saved to:" in result.output
        assert "generated.png" in result.output
        mock_ai_service.generate_image.assert_called_once_with(
            prompt="a cat",
            size="1024x1024",
            quality="auto",
            output_path=str(output_file),
            show_progress=True,
        )

    def test_image_with_output_directory(
        self, runner, mock_service_factory, mock_ai_service, tmp_path,
    ):
        """Test image generation with output directory."""
        output_dir = tmp_path / "images"
        output_dir.mkdir()
        mock_service_factory.return_value.get_ai_service.return_value = (
            mock_ai_service
        )
        saved_file = output_dir / "generated.png"
        mock_ai_service.generate_image.return_value.local_path = saved_file

        result = runner.invoke(
            image, ["a dog", "--output", str(output_dir)],
        )

        assert result.exit_code == 0
        assert "Saved to:" in result.output

    def test_image_with_json_output(
        self, runner, mock_service_factory, mock_ai_service,
    ):
        """Test image generation with JSON output."""
        mock_service_factory.return_value.get_ai_service.return_value = (
            mock_ai_service
        )

        result = runner.invoke(image, ["test prompt", "--json"])

        assert result.exit_code == 0
        assert '"url"' in result.output
        assert '"model"' in result.output
        assert '"size"' in result.output
        assert '"quality"' in result.output
        assert "https://example.com/generated-image.png" in result.output
        # In JSON mode, show_progress should be False
        mock_ai_service.generate_image.assert_called_once_with(
            prompt="test prompt",
            size="1024x1024",
            quality="auto",
            output_path=None,
            show_progress=False,
        )

    def test_image_with_all_options(
        self, runner, mock_service_factory, mock_ai_service, tmp_path,
    ):
        """Test image generation with all options combined."""
        output_file = tmp_path / "art.png"
        mock_service_factory.return_value.get_ai_service.return_value = (
            mock_ai_service
        )
        mock_ai_service.generate_image.return_value.local_path = output_file

        result = runner.invoke(
            image,
            [
                "modern art",
                "--size",
                "1024x1536",
                "--quality",
                "high",
                "--output",
                str(output_file),
            ],
        )

        assert result.exit_code == 0
        mock_ai_service.generate_image.assert_called_once_with(
            prompt="modern art",
            size="1024x1536",
            quality="high",
            output_path=str(output_file),
            show_progress=True,
        )

    def test_image_missing_api_key(
        self, runner, mock_service_factory, mock_ai_service,
    ):
        """Test image generation when API key is missing."""
        mock_service_factory.return_value.get_ai_service.return_value = (
            mock_ai_service
        )
        mock_ai_service.generate_image.side_effect = MissingAPIKeyError(
            "EI_API_KEY not set",
        )

        result = runner.invoke(image, ["test prompt"])

        assert result.exit_code == 1
        assert "Missing API key" in result.output
        assert "EI_API_KEY" in result.output

    def test_image_service_error(
        self, runner, mock_service_factory, mock_ai_service,
    ):
        """Test image generation with service error."""
        mock_service_factory.return_value.get_ai_service.return_value = (
            mock_ai_service
        )
        mock_ai_service.generate_image.side_effect = ServiceError(
            "Image generation failed",
        )

        result = runner.invoke(image, ["test prompt"])

        assert result.exit_code == 1
        assert "Image generation failed" in result.output

    def test_image_shows_model_info(
        self, runner, mock_service_factory, mock_ai_service,
    ):
        """Test that model info is displayed."""
        mock_service_factory.return_value.get_ai_service.return_value = (
            mock_ai_service
        )

        result = runner.invoke(image, ["test"])

        assert result.exit_code == 0
        assert "gpt-image-1" in result.output or "Model" in result.output

    def test_image_shows_size_and_quality(
        self, runner, mock_service_factory, mock_ai_service,
    ):
        """Test that size and quality are displayed."""
        mock_service_factory.return_value.get_ai_service.return_value = (
            mock_ai_service
        )

        result = runner.invoke(
            image, ["test", "--size", "1024x1024", "--quality", "high"],
        )

        assert result.exit_code == 0
        assert "1024x1024" in result.output
        assert ("high" in result.output.lower())

    def test_image_json_with_local_path(
        self, runner, mock_service_factory, mock_ai_service, tmp_path,
    ):
        """Test JSON output includes local path when saved."""
        output_file = tmp_path / "test.png"
        mock_service_factory.return_value.get_ai_service.return_value = (
            mock_ai_service
        )
        mock_ai_service.generate_image.return_value.local_path = output_file

        result = runner.invoke(
            image, ["test", "--output", str(output_file), "--json"],
        )

        assert result.exit_code == 0
        assert '"local_path"' in result.output
        assert str(output_file) in result.output

    def test_image_default_values(
        self, runner, mock_service_factory, mock_ai_service,
    ):
        """Test that default values are used when options not specified."""
        mock_service_factory.return_value.get_ai_service.return_value = (
            mock_ai_service
        )

        result = runner.invoke(image, ["simple prompt"])

        assert result.exit_code == 0
        # Check defaults: 1024x1024, auto
        mock_ai_service.generate_image.assert_called_once_with(
            prompt="simple prompt",
            size="1024x1024",
            quality="auto",
            output_path=None,
            show_progress=True,
        )

    def test_image_with_model_option(
        self, runner, mock_service_factory, mock_ai_service,
    ):
        """Test image generation (model option removed, uses gpt-image-1)."""
        mock_service_factory.return_value.get_ai_service.return_value = (
            mock_ai_service
        )

        result = runner.invoke(
            image, ["test"],
        )

        assert result.exit_code == 0
        # Model parameter not passed to generate_image (uses gpt-image-1)
        mock_ai_service.generate_image.assert_called_once()

    def test_image_url_display(
        self, runner, mock_service_factory, mock_ai_service,
    ):
        """Test that image URL is displayed."""
        mock_service_factory.return_value.get_ai_service.return_value = (
            mock_ai_service
        )

        result = runner.invoke(image, ["test"])

        assert result.exit_code == 0
        assert "URL:" in result.output or "url" in result.output
        assert "https://example.com/generated-image.png" in result.output

    def test_image_json_includes_all_fields(
        self, runner, mock_service_factory, mock_ai_service,
    ):
        """Test JSON output includes all expected fields."""
        mock_service_factory.return_value.get_ai_service.return_value = (
            mock_ai_service
        )

        result = runner.invoke(image, ["test", "--json"])

        assert result.exit_code == 0
        assert '"url"' in result.output
        assert '"model"' in result.output
        assert '"size"' in result.output
        assert '"quality"' in result.output
        assert '"local_path"' in result.output
        assert '"revised_prompt"' in result.output
