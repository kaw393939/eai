"""
Unit tests for ImageDownloader utility.

Tests URL detection, base64 decoding, format detection, downloading,
and error handling.
"""

import base64
from unittest.mock import Mock, patch

import pytest

from ei_cli.core.errors import AIServiceError
from ei_cli.services.image_downloader import ImageDownloader


class TestImageDownloader:
    """Test ImageDownloader utility class."""

    def test_init_default_timeout(self):
        """Test ImageDownloader initialization with default timeout."""
        downloader = ImageDownloader()
        assert downloader.timeout == 30

    def test_init_custom_timeout(self):
        """Test ImageDownloader initialization with custom timeout."""
        downloader = ImageDownloader(timeout=60)
        assert downloader.timeout == 60

    def test_is_url_with_http(self):
        """Test URL detection with HTTP URL."""
        downloader = ImageDownloader()
        assert downloader.is_url("http://example.com/image.jpg") is True

    def test_is_url_with_https(self):
        """Test URL detection with HTTPS URL."""
        downloader = ImageDownloader()
        assert downloader.is_url("https://example.com/image.jpg") is True

    def test_is_url_with_file_path(self):
        """Test URL detection with file path returns False."""
        downloader = ImageDownloader()
        assert downloader.is_url("/path/to/image.jpg") is False

    def test_is_url_with_invalid_string(self):
        """Test URL detection with invalid string."""
        downloader = ImageDownloader()
        assert downloader.is_url("not-a-url") is False

    def test_is_base64_with_data_uri(self):
        """Test base64 detection with data URI."""
        downloader = ImageDownloader()
        assert downloader.is_base64("data:image/png;base64,iVBORw0KG...") is True

    def test_is_base64_with_raw_base64(self):
        """Test base64 detection with raw base64 string."""
        downloader = ImageDownloader()
        # Create valid base64 string
        valid_b64 = base64.b64encode(b"x" * 200).decode("utf-8")
        assert downloader.is_base64(valid_b64) is True

    def test_is_base64_with_short_string(self):
        """Test base64 detection with short string returns False."""
        downloader = ImageDownloader()
        assert downloader.is_base64("short") is False

    def test_is_base64_with_invalid_base64(self):
        """Test base64 detection with invalid base64 returns False."""
        downloader = ImageDownloader()
        assert downloader.is_base64("not-base64" * 20) is False

    def test_detect_format_png(self):
        """Test format detection for PNG."""
        downloader = ImageDownloader()
        png_data = b"\x89PNG\r\n\x1a\n" + b"x" * 100
        assert downloader.detect_format(png_data) == ".png"

    def test_detect_format_jpeg(self):
        """Test format detection for JPEG."""
        downloader = ImageDownloader()
        jpeg_data = b"\xff\xd8\xff" + b"x" * 100
        assert downloader.detect_format(jpeg_data) == ".jpg"

    def test_detect_format_webp(self):
        """Test format detection for WebP."""
        downloader = ImageDownloader()
        webp_data = b"RIFF" + b"xxxx" + b"WEBP" + b"x" * 100
        assert downloader.detect_format(webp_data) == ".webp"

    def test_detect_format_gif(self):
        """Test format detection for GIF."""
        downloader = ImageDownloader()
        gif_data = b"GIF89a" + b"x" * 100
        assert downloader.detect_format(gif_data) == ".gif"

    def test_detect_format_unsupported(self):
        """Test format detection with unsupported format raises error."""
        downloader = ImageDownloader()
        with pytest.raises(AIServiceError) as exc_info:
            downloader.detect_format(b"unknown format")
        assert "Unable to detect image format" in str(exc_info.value)

    @patch("ei_cli.services.image_downloader.httpx.Client")
    def test_download_from_url_success(self, mock_client_class, tmp_path):
        """Test successful image download from URL."""
        downloader = ImageDownloader()
        output_path = tmp_path / "test.jpg"

        # Mock response
        mock_response = Mock()
        mock_response.headers = {
            "content-type": "image/jpeg",
            "content-length": "1024",
        }
        mock_response.iter_bytes = Mock(return_value=[b"image data chunk"])
        mock_response.raise_for_status = Mock()

        # Mock client context
        mock_client = Mock()
        mock_client.stream = Mock()
        mock_client.stream.return_value.__enter__ = Mock(return_value=mock_response)
        mock_client.stream.return_value.__exit__ = Mock(return_value=None)
        mock_client_class.return_value.__enter__ = Mock(return_value=mock_client)
        mock_client_class.return_value.__exit__ = Mock(return_value=None)

        result = downloader.download_from_url(
            "https://example.com/image.jpg",
            output_path,
            show_progress=False,
        )

        assert result == output_path
        assert output_path.exists()
        assert output_path.read_bytes() == b"image data chunk"

    @patch("ei_cli.services.image_downloader.httpx.Client")
    def test_download_from_url_http_error(self, mock_client_class, tmp_path):
        """Test download failure with HTTP error."""
        downloader = ImageDownloader()
        output_path = tmp_path / "test.jpg"

        # Mock client to raise error
        mock_client = Mock()
        mock_client.stream = Mock(side_effect=Exception("Connection failed"))
        mock_client_class.return_value.__enter__ = Mock(return_value=mock_client)
        mock_client_class.return_value.__exit__ = Mock(return_value=None)

        with pytest.raises(AIServiceError) as exc_info:
            downloader.download_from_url(
                "https://example.com/image.jpg",
                output_path,
                show_progress=False,
            )
        assert "Unexpected error downloading image" in str(exc_info.value)

    def test_decode_base64_with_data_uri(self, tmp_path):
        """Test decoding base64 data URI."""
        downloader = ImageDownloader()
        output_path = tmp_path / "test.png"

        # Create PNG data URI
        png_data = b"\x89PNG\r\n\x1a\n" + b"test data"
        b64_data = base64.b64encode(png_data).decode("utf-8")
        data_uri = f"data:image/png;base64,{b64_data}"

        result = downloader.decode_base64(data_uri, output_path)

        assert result == output_path
        assert output_path.exists()
        assert output_path.read_bytes() == png_data
        assert output_path.suffix == ".png"

    def test_decode_base64_with_raw_base64(self, tmp_path):
        """Test decoding raw base64 data."""
        downloader = ImageDownloader()
        output_path = tmp_path / "test"

        # Create JPEG data
        jpeg_data = b"\xff\xd8\xff" + b"test data"
        b64_data = base64.b64encode(jpeg_data).decode("utf-8")

        result = downloader.decode_base64(b64_data, output_path)

        assert result.exists()
        assert result.read_bytes() == jpeg_data
        assert result.suffix == ".jpg"

    def test_decode_base64_invalid_data(self, tmp_path):
        """Test decoding invalid base64 raises error."""
        downloader = ImageDownloader()
        output_path = tmp_path / "test.png"

        with pytest.raises(AIServiceError) as exc_info:
            downloader.decode_base64("not-valid-base64!", output_path)
        assert "Failed to decode base64 image" in str(exc_info.value)

    @patch("ei_cli.services.image_downloader.httpx.Client")
    def test_save_image_with_url(self, mock_client_class, tmp_path):
        """Test save_image with URL."""
        downloader = ImageDownloader()
        output_path = tmp_path / "test.jpg"

        # Mock response
        mock_response = Mock()
        mock_response.headers = {
            "content-type": "image/jpeg",
            "content-length": "1024",
        }
        mock_response.iter_bytes = Mock(return_value=[b"image data"])
        mock_response.raise_for_status = Mock()

        mock_client = Mock()
        mock_client.stream = Mock()
        mock_client.stream.return_value.__enter__ = Mock(return_value=mock_response)
        mock_client.stream.return_value.__exit__ = Mock(return_value=None)
        mock_client_class.return_value.__enter__ = Mock(return_value=mock_client)
        mock_client_class.return_value.__exit__ = Mock(return_value=None)

        result = downloader.save_image(
            "https://example.com/image.jpg",
            output_path,
            show_progress=False,
        )

        assert result == output_path
        assert output_path.exists()

    def test_save_image_with_base64(self, tmp_path):
        """Test save_image with base64 data."""
        downloader = ImageDownloader()
        output_path = tmp_path / "test.png"

        # Create base64 data
        png_data = b"\x89PNG\r\n\x1a\n" + b"test"
        b64_data = base64.b64encode(png_data).decode("utf-8")
        data_uri = f"data:image/png;base64,{b64_data}"

        result = downloader.save_image(data_uri, output_path)

        assert result == output_path
        assert output_path.exists()
        assert output_path.read_bytes() == png_data

    def test_save_image_invalid_source(self, tmp_path):
        """Test save_image with invalid source raises error."""
        downloader = ImageDownloader()
        output_path = tmp_path / "test.jpg"

        with pytest.raises(AIServiceError) as exc_info:
            downloader.save_image("invalid-source", output_path)
        assert "neither a valid URL nor base64 data" in str(exc_info.value)

    @patch("ei_cli.services.image_downloader.httpx.Client")
    def test_download_creates_parent_directories(self, mock_client_class, tmp_path):
        """Test download creates parent directories if they don't exist."""
        downloader = ImageDownloader()
        output_path = tmp_path / "nested" / "dir" / "test.jpg"

        # Mock response
        mock_response = Mock()
        mock_response.headers = {
            "content-type": "image/jpeg",
            "content-length": "100",
        }
        mock_response.iter_bytes = Mock(return_value=[b"data"])
        mock_response.raise_for_status = Mock()

        mock_client = Mock()
        mock_client.stream = Mock()
        mock_client.stream.return_value.__enter__ = Mock(return_value=mock_response)
        mock_client.stream.return_value.__exit__ = Mock(return_value=None)
        mock_client_class.return_value.__enter__ = Mock(return_value=mock_client)
        mock_client_class.return_value.__exit__ = Mock(return_value=None)

        result = downloader.download_from_url(
            "https://example.com/image.jpg",
            output_path,
            show_progress=False,
        )

        assert result.parent.exists()
        assert result.exists()

    def test_decode_base64_creates_parent_directories(self, tmp_path):
        """Test decode_base64 creates parent directories if they don't exist."""
        downloader = ImageDownloader()
        output_path = tmp_path / "nested" / "dir" / "test.png"

        png_data = b"\x89PNG\r\n\x1a\n" + b"test"
        b64_data = base64.b64encode(png_data).decode("utf-8")

        result = downloader.decode_base64(b64_data, output_path)

        assert result.parent.exists()
        assert result.exists()
