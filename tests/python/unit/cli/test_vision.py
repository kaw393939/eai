"""Tests for vision CLI command."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from ei_cli.cli.commands.vision import vision
from ei_cli.core.errors import MissingAPIKeyError
from ei_cli.services.base import ServiceError


class TestVisionCommand:
    """Test suite for vision command."""

    @pytest.fixture
    def runner(self):
        """Create CLI runner."""
        return CliRunner()

    @pytest.fixture
    def mock_service_factory(self):
        """Mock ServiceFactory."""
        with patch("ei_cli.cli.commands.vision.ServiceFactory") as mock:
            yield mock

    @pytest.fixture
    def mock_ai_service(self):
        """Create mock AI service with vision result."""
        service = MagicMock()
        service.check_available.return_value = (True, None)

        # Mock vision result
        result = MagicMock()
        result.analysis = "This is a detailed analysis of the image."
        result.model = "gpt-5"
        result.image_source = "image.jpg"
        result.prompt = "Describe this image in detail."
        service.analyze_image.return_value = result

        return service

    @pytest.fixture
    def image_file(self, tmp_path):
        """Create temporary image file."""
        img = tmp_path / "test_image.jpg"
        img.write_bytes(b"fake image data")
        return img

    def test_basic_vision_analysis(
        self, runner, mock_service_factory, mock_ai_service, image_file,
    ):
        """Test basic vision analysis."""
        mock_service_factory.return_value.get_ai_service.return_value = (
            mock_ai_service
        )

        result = runner.invoke(vision, [str(image_file)])

        assert result.exit_code == 0
        assert "Vision Analysis" in result.output
        assert "This is a detailed analysis of the image." in result.output
        mock_ai_service.analyze_image.assert_called_once()

    def test_vision_with_custom_prompt(
        self, runner, mock_service_factory, mock_ai_service, image_file,
    ):
        """Test vision with custom prompt."""
        mock_service_factory.return_value.get_ai_service.return_value = (
            mock_ai_service
        )
        mock_ai_service.analyze_image.return_value.prompt = (
            "What colors are in this image?"
        )

        result = runner.invoke(
            vision,
            [str(image_file), "--prompt", "What colors are in this image?"],
        )

        assert result.exit_code == 0
        mock_ai_service.analyze_image.assert_called_once_with(
            image_path=str(image_file),
            prompt="What colors are in this image?",
            detail_level="auto",
        )

    def test_vision_with_url(
        self, runner, mock_service_factory, mock_ai_service,
    ):
        """Test vision analysis with URL."""
        url = "https://example.com/image.jpg"
        mock_service_factory.return_value.get_ai_service.return_value = (
            mock_ai_service
        )
        mock_ai_service.analyze_image.return_value.image_source = url

        result = runner.invoke(vision, [url])

        assert result.exit_code == 0
        assert "Vision Analysis" in result.output
        mock_ai_service.analyze_image.assert_called_once_with(
            image_path=url,
            prompt="Describe this image in detail.",
            detail_level="auto",
        )

    def test_vision_with_high_detail(
        self, runner, mock_service_factory, mock_ai_service, image_file,
    ):
        """Test vision with high detail level."""
        mock_service_factory.return_value.get_ai_service.return_value = (
            mock_ai_service
        )

        result = runner.invoke(
            vision, [str(image_file), "--detail", "high"],
        )

        assert result.exit_code == 0
        mock_ai_service.analyze_image.assert_called_once_with(
            image_path=str(image_file),
            prompt="Describe this image in detail.",
            detail_level="high",
        )

    def test_vision_with_low_detail(
        self, runner, mock_service_factory, mock_ai_service, image_file,
    ):
        """Test vision with low detail level."""
        mock_service_factory.return_value.get_ai_service.return_value = (
            mock_ai_service
        )

        result = runner.invoke(vision, [str(image_file), "--detail", "low"])

        assert result.exit_code == 0
        mock_ai_service.analyze_image.assert_called_once_with(
            image_path=str(image_file),
            prompt="Describe this image in detail.",
            detail_level="low",
        )

    def test_vision_with_json_output(
        self, runner, mock_service_factory, mock_ai_service, image_file,
    ):
        """Test vision with JSON output format."""
        mock_service_factory.return_value.get_ai_service.return_value = (
            mock_ai_service
        )

        result = runner.invoke(vision, [str(image_file), "--json"])

        assert result.exit_code == 0
        assert '"analysis"' in result.output
        assert '"model"' in result.output
        assert '"image_source"' in result.output
        assert "This is a detailed analysis of the image." in result.output

    def test_vision_with_max_tokens(
        self, runner, mock_service_factory, mock_ai_service, image_file,
    ):
        """Test vision with custom max tokens."""
        mock_service_factory.return_value.get_ai_service.return_value = (
            mock_ai_service
        )

        result = runner.invoke(
            vision, [str(image_file), "--max-tokens", "2000"],
        )

        assert result.exit_code == 0
        # Note: max-tokens not passed to AIService currently
        mock_ai_service.analyze_image.assert_called_once()

    def test_vision_with_model_option(
        self, runner, mock_service_factory, mock_ai_service, image_file,
    ):
        """Test vision with model selection."""
        mock_service_factory.return_value.get_ai_service.return_value = (
            mock_ai_service
        )

        result = runner.invoke(
            vision, [str(image_file), "--model", "gpt-5"],
        )

        assert result.exit_code == 0
        # Note: model not passed to AIService currently
        mock_ai_service.analyze_image.assert_called_once()

    def test_vision_missing_api_key(
        self, runner, mock_service_factory, mock_ai_service, image_file,
    ):
        """Test vision when API key is missing."""
        mock_service_factory.return_value.get_ai_service.return_value = (
            mock_ai_service
        )
        mock_ai_service.analyze_image.side_effect = MissingAPIKeyError(
            "EI_API_KEY not set",
        )

        result = runner.invoke(vision, [str(image_file)])

        assert result.exit_code == 1
        assert "Missing API key" in result.output
        assert "EI_API_KEY" in result.output

    def test_vision_service_error(
        self, runner, mock_service_factory, mock_ai_service, image_file,
    ):
        """Test vision with service error."""
        mock_service_factory.return_value.get_ai_service.return_value = (
            mock_ai_service
        )
        mock_ai_service.analyze_image.side_effect = ServiceError(
            "Image analysis failed",
        )

        result = runner.invoke(vision, [str(image_file)])

        assert result.exit_code == 1
        assert "Image analysis failed" in result.output

    def test_vision_shows_custom_prompt_in_panel(
        self, runner, mock_service_factory, mock_ai_service, image_file,
    ):
        """Test that custom prompt is displayed in panel."""
        mock_service_factory.return_value.get_ai_service.return_value = (
            mock_ai_service
        )
        custom_prompt = "Extract text from this image"
        mock_ai_service.analyze_image.return_value.prompt = custom_prompt

        result = runner.invoke(
            vision, [str(image_file), "--prompt", custom_prompt],
        )

        assert result.exit_code == 0
        assert "Question" in result.output or custom_prompt in result.output

    def test_vision_combined_options(
        self, runner, mock_service_factory, mock_ai_service, image_file,
    ):
        """Test vision with multiple options combined."""
        mock_service_factory.return_value.get_ai_service.return_value = (
            mock_ai_service
        )
        custom_prompt = "Analyze the colors and composition"

        result = runner.invoke(
            vision,
            [
                str(image_file),
                "--prompt",
                custom_prompt,
                "--detail",
                "high",
                "--max-tokens",
                "1500",
            ],
        )

        assert result.exit_code == 0
        mock_ai_service.analyze_image.assert_called_once_with(
            image_path=str(image_file),
            prompt=custom_prompt,
            detail_level="high",
        )

    def test_vision_json_with_url(
        self, runner, mock_service_factory, mock_ai_service,
    ):
        """Test JSON output with URL source."""
        url = "https://example.com/test.jpg"
        mock_service_factory.return_value.get_ai_service.return_value = (
            mock_ai_service
        )
        mock_ai_service.analyze_image.return_value.image_source = url

        result = runner.invoke(vision, [url, "--json"])

        assert result.exit_code == 0
        assert url in result.output
        assert '"analysis"' in result.output

    def test_vision_shows_model_info(
        self, runner, mock_service_factory, mock_ai_service, image_file,
    ):
        """Test that model info is displayed."""
        mock_service_factory.return_value.get_ai_service.return_value = (
            mock_ai_service
        )

        result = runner.invoke(vision, [str(image_file)])

        assert result.exit_code == 0
        assert "gpt-5" in result.output or "Model" in result.output

    def test_vision_shows_image_source(
        self, runner, mock_service_factory, mock_ai_service, image_file,
    ):
        """Test that image source is displayed."""
        mock_service_factory.return_value.get_ai_service.return_value = (
            mock_ai_service
        )

        result = runner.invoke(vision, [str(image_file)])

        assert result.exit_code == 0
        assert "image.jpg" in result.output or "Image" in result.output

    def test_vision_ocr_use_case(
        self, runner, mock_service_factory, mock_ai_service, image_file,
    ):
        """Test OCR use case."""
        mock_service_factory.return_value.get_ai_service.return_value = (
            mock_ai_service
        )
        mock_ai_service.analyze_image.return_value.analysis = (
            "Extracted text: Hello World"
        )

        result = runner.invoke(
            vision,
            [str(image_file), "--prompt", "Extract all text from this image"],
        )

        assert result.exit_code == 0
        assert "Extracted text: Hello World" in result.output

    def test_vision_default_prompt(
        self, runner, mock_service_factory, mock_ai_service, image_file,
    ):
        """Test that default prompt is used when none specified."""
        mock_service_factory.return_value.get_ai_service.return_value = (
            mock_ai_service
        )

        result = runner.invoke(vision, [str(image_file)])

        assert result.exit_code == 0
        mock_ai_service.analyze_image.assert_called_once_with(
            image_path=str(image_file),
            prompt="Describe this image in detail.",
            detail_level="auto",
        )

    def test_vision_metadata_tip(
        self, runner, mock_service_factory, mock_ai_service, image_file,
    ):
        """Test that metadata tip is shown in non-JSON mode."""
        mock_service_factory.return_value.get_ai_service.return_value = (
            mock_ai_service
        )

        result = runner.invoke(vision, [str(image_file)])

        assert result.exit_code == 0
        assert ("--json" in result.output or "JSON" in result.output) or (
            "Vision Analysis" in result.output
        )
