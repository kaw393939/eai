"""
Tests for multi-image vision analysis command.
"""

from unittest.mock import Mock, patch

from click.testing import CliRunner

from ei_cli.cli.commands.multi_vision import multi_vision
from ei_cli.core.errors import MissingAPIKeyError
from ei_cli.services.ai_service import VisionResult
from ei_cli.services.base import ServiceError


class TestMultiVisionCommand:
    """Test multi-image vision analysis command."""

    @patch("ei_cli.cli.commands.multi_vision.ServiceFactory")
    def test_basic_multi_vision_analysis(self, mock_factory, tmp_path):
        """Test basic multi-image analysis."""
        # Create test images
        image1 = tmp_path / "test1.jpg"
        image1.write_bytes(b"fake image 1")
        image2 = tmp_path / "test2.jpg"
        image2.write_bytes(b"fake image 2")

        # Mock service
        mock_service = Mock()
        mock_service.check_available.return_value = (True, None)
        mock_service.analyze_multiple_images.return_value = VisionResult(
            analysis=(
                "These images show similar themes with different "
                "compositions."
            ),
            model="gpt-5",
            image_source="Multiple images: test1.jpg, test2.jpg",
            prompt="Compare and analyze these images.",
        )
        mock_factory.return_value.get_ai_service.return_value = mock_service

        runner = CliRunner()
        result = runner.invoke(multi_vision, [str(image1), str(image2)])

        assert result.exit_code == 0
        assert "Multi-Image Analysis" in result.output
        assert "similar themes" in result.output
        mock_service.analyze_multiple_images.assert_called_once()

    @patch("ei_cli.cli.commands.multi_vision.ServiceFactory")
    def test_multi_vision_with_custom_prompt(self, mock_factory, tmp_path):
        """Test multi-image analysis with custom prompt."""
        # Create test images
        image1 = tmp_path / "test1.jpg"
        image1.write_bytes(b"fake image 1")
        image2 = tmp_path / "test2.jpg"
        image2.write_bytes(b"fake image 2")

        # Mock service
        mock_service = Mock()
        mock_service.check_available.return_value = (True, None)
        mock_service.analyze_multiple_images.return_value = VisionResult(
            analysis="Both images contain red objects.",
            model="gpt-5",
            image_source="Multiple images: test1.jpg, test2.jpg",
            prompt="What colors are common?",
        )
        mock_factory.return_value.get_ai_service.return_value = mock_service

        runner = CliRunner()
        result = runner.invoke(multi_vision, [
            str(image1),
            str(image2),
            "--prompt",
            "What colors are common?",
        ])

        assert result.exit_code == 0
        assert "red objects" in result.output

        # Verify the service was called with correct parameters
        call_args = mock_service.analyze_multiple_images.call_args
        assert call_args.kwargs["prompt"] == "What colors are common?"

    @patch("ei_cli.cli.commands.multi_vision.ServiceFactory")
    def test_multi_vision_with_compare_mode(self, mock_factory, tmp_path):
        """Test multi-image analysis with comparison mode."""
        # Create test images
        image1 = tmp_path / "test1.jpg"
        image1.write_bytes(b"fake image 1")
        image2 = tmp_path / "test2.jpg"
        image2.write_bytes(b"fake image 2")

        # Mock service
        mock_service = Mock()
        mock_service.check_available.return_value = (True, None)
        mock_service.analyze_multiple_images.return_value = VisionResult(
            analysis="Comparison analysis with detailed differences.",
            model="gpt-5",
            image_source="Multiple images: test1.jpg, test2.jpg",
            prompt="Compare and analyze these images.",
        )
        mock_factory.return_value.get_ai_service.return_value = mock_service

        runner = CliRunner()
        result = runner.invoke(multi_vision, [
            str(image1),
            str(image2),
            "--compare",
        ])

        assert result.exit_code == 0
        assert "Comparison analysis" in result.output

        # Verify compare mode was enabled
        call_args = mock_service.analyze_multiple_images.call_args
        assert call_args.kwargs["compare_mode"] is True

    @patch("ei_cli.cli.commands.multi_vision.ServiceFactory")
    def test_multi_vision_with_detail_level(self, mock_factory, tmp_path):
        """Test multi-image analysis with detail level."""
        # Create test images
        image1 = tmp_path / "test1.jpg"
        image1.write_bytes(b"fake image 1")
        image2 = tmp_path / "test2.jpg"
        image2.write_bytes(b"fake image 2")

        # Mock service
        mock_service = Mock()
        mock_service.check_available.return_value = (True, None)
        mock_service.analyze_multiple_images.return_value = VisionResult(
            analysis="High detail analysis of multiple images.",
            model="gpt-5",
            image_source="Multiple images: test1.jpg, test2.jpg",
            prompt="Compare and analyze these images.",
        )
        mock_factory.return_value.get_ai_service.return_value = mock_service

        runner = CliRunner()
        result = runner.invoke(multi_vision, [
            str(image1),
            str(image2),
            "--detail",
            "high",
        ])

        assert result.exit_code == 0

        # Verify detail level was passed
        call_args = mock_service.analyze_multiple_images.call_args
        assert call_args.kwargs["detail_level"] == "high"

    @patch("ei_cli.cli.commands.multi_vision.ServiceFactory")
    def test_multi_vision_json_output(self, mock_factory, tmp_path):
        """Test multi-image analysis with JSON output."""
        # Create test images
        image1 = tmp_path / "test1.jpg"
        image1.write_bytes(b"fake image 1")
        image2 = tmp_path / "test2.jpg"
        image2.write_bytes(b"fake image 2")

        # Mock service
        mock_service = Mock()
        mock_service.check_available.return_value = (True, None)
        mock_service.analyze_multiple_images.return_value = VisionResult(
            analysis="JSON analysis result.",
            model="gpt-5",
            image_source="Multiple images: test1.jpg, test2.jpg",
            prompt="Compare and analyze these images.",
        )
        mock_factory.return_value.get_ai_service.return_value = mock_service

        runner = CliRunner()
        result = runner.invoke(multi_vision, [
            str(image1),
            str(image2),
            "--json",
        ])

        assert result.exit_code == 0
        assert '"analysis": "JSON analysis result."' in result.output
        assert '"image_count": 2' in result.output

    def test_multi_vision_too_few_images(self):
        """Test multi-vision with too few images."""
        runner = CliRunner()
        result = runner.invoke(multi_vision, ["single_image.jpg"])

        assert result.exit_code == 1
        assert "At least 2 images are required" in result.output

    def test_multi_vision_too_many_images(self):
        """Test multi-vision with too many images."""
        runner = CliRunner()
        result = runner.invoke(multi_vision, [
            "img1.jpg",
            "img2.jpg",
            "img3.jpg",
            "img4.jpg",
            "img5.jpg",
        ])

        assert result.exit_code == 1
        assert "Maximum 3 images allowed" in result.output

    @patch("ei_cli.cli.commands.multi_vision.ServiceFactory")
    def test_multi_vision_missing_api_key(self, mock_factory, tmp_path):
        """Test multi-vision with missing API key."""
        # Create test images
        image1 = tmp_path / "test1.jpg"
        image1.write_bytes(b"fake image 1")
        image2 = tmp_path / "test2.jpg"
        image2.write_bytes(b"fake image 2")

        # Mock service to raise MissingAPIKeyError
        mock_service = Mock()
        mock_service.check_available.return_value = (True, None)
        mock_service.analyze_multiple_images.side_effect = (
            MissingAPIKeyError("Missing API key")
        )
        mock_factory.return_value.get_ai_service.return_value = mock_service

        runner = CliRunner()
        result = runner.invoke(multi_vision, [str(image1), str(image2)])

        assert result.exit_code == 1
        assert "Missing API key" in result.output

    @patch("ei_cli.cli.commands.multi_vision.ServiceFactory")
    def test_multi_vision_service_error(self, mock_factory, tmp_path):
        """Test multi-vision with service error."""
        # Create test images
        image1 = tmp_path / "test1.jpg"
        image1.write_bytes(b"fake image 1")
        image2 = tmp_path / "test2.jpg"
        image2.write_bytes(b"fake image 2")

        # Mock service to raise ServiceError
        mock_service = Mock()
        mock_service.check_available.return_value = (True, None)
        mock_service.analyze_multiple_images.side_effect = (
            ServiceError("Service error")
        )
        mock_factory.return_value.get_ai_service.return_value = mock_service

        runner = CliRunner()
        result = runner.invoke(multi_vision, [str(image1), str(image2)])

        assert result.exit_code == 1
        assert "Service error" in result.output

    @patch("ei_cli.cli.commands.multi_vision.ServiceFactory")
    def test_multi_vision_service_unavailable(self, mock_factory, tmp_path):
        """Test multi-vision when service is unavailable."""
        # Create test images
        image1 = tmp_path / "test1.jpg"
        image1.write_bytes(b"fake image 1")
        image2 = tmp_path / "test2.jpg"
        image2.write_bytes(b"fake image 2")

        # Mock service as unavailable
        mock_service = Mock()
        mock_service.check_available.return_value = (
            False,
            "Service unavailable",
        )
        mock_factory.return_value.get_ai_service.return_value = mock_service

        runner = CliRunner()
        result = runner.invoke(multi_vision, [str(image1), str(image2)])

        assert result.exit_code == 1
        assert "Multi-image analysis tool not available" in result.output

    @patch("ei_cli.cli.commands.multi_vision.ServiceFactory")
    def test_multi_vision_combined_options(self, mock_factory, tmp_path):
        """Test multi-vision with all options combined."""
        # Create test images
        image1 = tmp_path / "test1.jpg"
        image1.write_bytes(b"fake image 1")
        image2 = tmp_path / "test2.jpg"
        image2.write_bytes(b"fake image 2")
        image3 = tmp_path / "test3.jpg"
        image3.write_bytes(b"fake image 3")

        # Mock service
        mock_service = Mock()
        mock_service.check_available.return_value = (True, None)
        mock_service.analyze_multiple_images.return_value = VisionResult(
            analysis="Comprehensive analysis of all images.",
            model="gpt-5",
            image_source="Multiple images: test1.jpg, test2.jpg, test3.jpg",
            prompt="What patterns do you see?",
        )
        mock_factory.return_value.get_ai_service.return_value = mock_service

        runner = CliRunner()
        result = runner.invoke(multi_vision, [
            str(image1),
            str(image2),
            str(image3),
            "--prompt",
            "What patterns do you see?",
            "--compare",
            "--detail",
            "low",
        ])

        assert result.exit_code == 0

        # Verify all parameters were passed correctly
        call_args = mock_service.analyze_multiple_images.call_args
        assert call_args.kwargs["prompt"] == "What patterns do you see?"
        assert call_args.kwargs["compare_mode"] is True
        assert call_args.kwargs["detail_level"] == "low"
        assert len(call_args.kwargs["image_paths"]) == 3  # image_paths list
