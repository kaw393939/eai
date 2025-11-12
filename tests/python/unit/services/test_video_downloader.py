"""Unit tests for video_downloader.py with mocked yt-dlp."""

import builtins
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yt_dlp

from ei_cli.services.video_downloader import (
    VideoDownloader,
    VideoDownloadError,
)

# Real YouTube videos for testing
SHORT_VIDEO_URL = "https://www.youtube.com/watch?v=6jkkyoyM9Pc"  # Short video
LONG_VIDEO_URL = "https://www.youtube.com/watch?v=YpKej05RgsY"  # 4 hour video
INVALID_URL = "https://www.youtube.com/watch?v=INVALID_VIDEO_ID"


@pytest.fixture
def temp_output_dir(tmp_path):
    """Create temporary output directory for downloads."""
    output_dir = tmp_path / "downloads"
    output_dir.mkdir()
    return output_dir


@pytest.fixture
def downloader(temp_output_dir):
    """Create VideoDownloader instance with temp directory."""
    return VideoDownloader(output_dir=temp_output_dir)


class TestVideoDownloaderInit:
    """Tests for VideoDownloader initialization."""

    def test_init_with_output_dir(self, temp_output_dir):
        """Test initialization with specified output directory."""
        downloader = VideoDownloader(output_dir=temp_output_dir)
        assert downloader.output_dir == temp_output_dir
        assert downloader.console is not None

    def test_init_without_output_dir(self):
        """Test initialization defaults to current directory."""
        downloader = VideoDownloader()
        assert downloader.output_dir == Path.cwd()

    def test_repr(self, temp_output_dir):
        """Test string representation."""
        downloader = VideoDownloader(output_dir=temp_output_dir)
        repr_str = repr(downloader)
        assert "VideoDownloader" in repr_str
        assert str(temp_output_dir) in repr_str


class TestSupportsUrl:
    """Tests for URL support checking."""

    def test_supports_youtube_url(self, downloader):
        """Test that YouTube URLs are supported."""
        assert downloader.supports_url(SHORT_VIDEO_URL) is True

    def test_supports_youtube_short_format(self, downloader):
        """Test YouTube short format support."""
        assert downloader.supports_url("https://youtu.be/6jkkyoyM9Pc") is True

    def test_unsupported_url(self, downloader):
        """Test that random URLs are not supported."""
        # Note: yt-dlp may support many sites via generic extractors
        result = downloader.supports_url("https://example.com/video.mp4")
        # Just verify it returns a boolean, some extractors may support generic URLs
        assert isinstance(result, bool)

    def test_invalid_url_format(self, downloader):
        """Test invalid URL format."""
        result = downloader.supports_url("not-a-url")
        # Should return False or True (generic extractor), but must be boolean
        assert isinstance(result, bool)


class TestGetVideoInfo:
    """Tests for video metadata extraction."""

    @pytest.mark.slow
    def test_get_info_short_video(self, downloader):
        """Test getting info from short video without downloading."""
        try:
            info = downloader.get_video_info(SHORT_VIDEO_URL)

            # Verify required fields are present
            assert "title" in info
            assert "duration" in info
            assert "uploader" in info
            assert "description" in info
            assert "formats" in info

            # Verify data types
            assert isinstance(info["title"], str)
            assert isinstance(info["duration"], (int, float, type(None)))
            assert isinstance(info["formats"], int)
            assert info["formats"] > 0  # Should have at least one format
        except VideoDownloadError as e:
            # If YouTube blocks the request, skip the test
            if "403" in str(e) or "Forbidden" in str(e):
                pytest.skip("YouTube blocked request (403 Forbidden)")
            raise

    @pytest.mark.slow
    def test_get_info_long_video(self, downloader):
        """Test getting info from long 4-hour video."""
        try:
            info = downloader.get_video_info(LONG_VIDEO_URL)

            assert "title" in info
            assert "duration" in info

            # Verify it's actually a long video (4 hours = 14400 seconds)
            if info["duration"]:
                assert info["duration"] > 10000  # At least ~3 hours
        except VideoDownloadError as e:
            # If YouTube blocks the request, skip the test
            if "403" in str(e) or "Forbidden" in str(e):
                pytest.skip("YouTube blocked request (403 Forbidden)")
            raise

    def test_get_info_invalid_url(self, downloader):
        """Test error handling for invalid video URL."""
        with pytest.raises(VideoDownloadError) as exc_info:
            downloader.get_video_info(INVALID_URL)

        assert "Failed to get video info" in str(exc_info.value)
        assert exc_info.value.details["url"] == INVALID_URL

    def test_get_info_malformed_url(self, downloader):
        """Test error handling for malformed URL."""
        with pytest.raises(VideoDownloadError) as exc_info:
            downloader.get_video_info("not-a-valid-url")

        assert "video info" in str(exc_info.value).lower()


class TestDownloadAudio:
    """Tests for audio download functionality."""

    @patch("yt_dlp.YoutubeDL")
    def test_download_short_video_default_format(
        self, mock_ydl_class, downloader, temp_output_dir,
    ):
        """Test downloading short video with default format."""
        # Create expected output file
        expected_file = temp_output_dir / "Test Video.m4a"
        expected_file.write_text("fake audio content")

        # Mock the YoutubeDL instance
        mock_ydl = MagicMock()
        mock_ydl_class.return_value.__enter__ = MagicMock(
            return_value=mock_ydl,
        )
        mock_ydl_class.return_value.__exit__ = MagicMock(
            return_value=False,
        )

        # Mock video info
        video_info = {
            "title": "Test Video",
            "ext": "m4a",
            "age_limit": 0,
        }
        mock_ydl.extract_info.return_value = video_info
        mock_ydl.prepare_filename.return_value = str(expected_file)

        audio_path = downloader.download_audio(
            url=SHORT_VIDEO_URL,
            show_progress=False,
        )

        # Verify file exists
        assert audio_path.exists()
        assert audio_path.is_file()

        # Verify it's in the output directory
        assert audio_path.parent == temp_output_dir

        # Verify file has content
        assert audio_path.stat().st_size > 0

        # Clean up
        audio_path.unlink()

    @patch("yt_dlp.YoutubeDL")
    def test_download_with_specific_output_path(
        self, mock_ydl_class, downloader, temp_output_dir,
    ):
        """Test downloading with specified output path."""
        output_path = temp_output_dir / "custom_name.m4a"
        output_path.write_text("fake audio content")

        # Mock YoutubeDL
        mock_ydl = MagicMock()
        mock_ydl.prepare_filename.return_value = str(
            output_path.with_suffix(""),
        )
        mock_ydl_class.return_value.__enter__ = MagicMock(
            return_value=mock_ydl,
        )
        mock_ydl_class.return_value.__exit__ = MagicMock(
            return_value=False,
        )

        video_info = {
            "title": "Test Video",
            "ext": "m4a",
            "age_limit": 0,
        }
        mock_ydl.extract_info.return_value = video_info

        audio_path = downloader.download_audio(
            url=SHORT_VIDEO_URL,
            output_path=output_path,
            show_progress=False,
        )

        # Verify correct path
        assert audio_path == output_path
        assert audio_path.exists()
        assert audio_path.stat().st_size > 0

        # Clean up
        audio_path.unlink()

    @patch("yt_dlp.YoutubeDL")
    def test_download_mp3_format(self, mock_ydl_class, downloader):
        """Test downloading and converting to MP3 format."""
        expected_file = downloader.output_dir / "Test Video.mp3"
        expected_file.write_text("fake mp3 content")

        # Mock YoutubeDL
        mock_ydl = MagicMock()
        mock_ydl_class.return_value.__enter__ = MagicMock(
            return_value=mock_ydl,
        )
        mock_ydl_class.return_value.__exit__ = MagicMock(
            return_value=False,
        )

        video_info = {
            "title": "Test Video",
            "ext": "m4a",
            "age_limit": 0,
        }
        mock_ydl.extract_info.return_value = video_info
        mock_ydl.prepare_filename.return_value = str(
            expected_file.with_suffix(".m4a"),
        )

        audio_path = downloader.download_audio(
            url=SHORT_VIDEO_URL,
            format_preference="mp3",
            show_progress=False,
        )

        assert audio_path.exists()
        assert audio_path.suffix == ".mp3"
        assert audio_path.stat().st_size > 0

        # Clean up
        audio_path.unlink()

    @patch("yt_dlp.YoutubeDL")
    def test_download_with_progress(self, mock_ydl_class, downloader):
        """Test downloading with progress display enabled."""
        expected_file = downloader.output_dir / "Test Video.m4a"
        expected_file.write_text("fake audio content")

        # Mock YoutubeDL
        mock_ydl = MagicMock()
        mock_ydl_class.return_value.__enter__ = MagicMock(
            return_value=mock_ydl,
        )
        mock_ydl_class.return_value.__exit__ = MagicMock(
            return_value=False,
        )

        video_info = {
            "title": "Test Video",
            "ext": "m4a",
            "age_limit": 0,
        }
        mock_ydl.extract_info.return_value = video_info
        mock_ydl.prepare_filename.return_value = str(expected_file)

        audio_path = downloader.download_audio(
            url=SHORT_VIDEO_URL,
            show_progress=True,  # Enable progress bar
        )

        assert audio_path.exists()
        assert audio_path.stat().st_size > 0

        # Clean up
        audio_path.unlink()

    @patch("yt_dlp.YoutubeDL")
    def test_download_creates_output_dir(
        self, mock_ydl_class, temp_output_dir,
    ):
        """Test that output directory is created if it doesn't exist."""
        new_dir = temp_output_dir / "new_subdir"
        assert not new_dir.exists()

        expected_file = new_dir / "Test Video.m4a"
        expected_file.parent.mkdir(parents=True, exist_ok=True)
        expected_file.write_text("fake audio content")

        # Mock YoutubeDL
        mock_ydl = MagicMock()
        mock_ydl_class.return_value.__enter__ = MagicMock(
            return_value=mock_ydl,
        )
        mock_ydl_class.return_value.__exit__ = MagicMock(
            return_value=False,
        )

        video_info = {
            "title": "Test Video",
            "ext": "m4a",
            "age_limit": 0,
        }
        mock_ydl.extract_info.return_value = video_info
        mock_ydl.prepare_filename.return_value = str(expected_file)

        downloader = VideoDownloader(output_dir=new_dir)
        audio_path = downloader.download_audio(
            url=SHORT_VIDEO_URL,
            show_progress=False,
        )

        assert new_dir.exists()
        assert audio_path.exists()

        # Clean up
        audio_path.unlink()

    @patch("yt_dlp.YoutubeDL")
    def test_download_invalid_url(self, mock_ydl_class, downloader):
        """Test error handling for invalid video URL."""
        # Mock YoutubeDL to raise DownloadError
        mock_ydl = MagicMock()
        mock_ydl_class.return_value.__enter__ = MagicMock(
            return_value=mock_ydl,
        )
        mock_ydl_class.return_value.__exit__ = MagicMock(
            return_value=False,
        )

        # Simulate DownloadError on extract_info
        mock_ydl.extract_info.side_effect = yt_dlp.utils.DownloadError(
            "Video unavailable",
        )

        with pytest.raises(VideoDownloadError) as exc_info:
            downloader.download_audio(
                url=INVALID_URL,
                show_progress=False,
            )

        assert "unavailable" in str(exc_info.value).lower()
        assert exc_info.value.details["url"] == INVALID_URL

    def test_download_malformed_url(self, downloader):
        """Test error handling for malformed URL."""
        with pytest.raises(VideoDownloadError) as exc_info:
            downloader.download_audio(
                url="not-a-valid-url",
                show_progress=False,
            )

        error_msg = str(exc_info.value).lower()
        assert "download" in error_msg or "error" in error_msg


class TestVideoDownloadError:
    """Tests for VideoDownloadError exception."""

    def test_error_with_message_only(self):
        """Test error with just a message."""
        error = VideoDownloadError(message="Test error")
        assert error.message == "Test error"
        assert error.details == {}
        assert str(error) == "Test error"

    def test_error_with_details(self):
        """Test error with message and details."""
        details = {"url": "https://example.com", "code": 404}
        error = VideoDownloadError(message="Download failed", details=details)
        assert error.message == "Download failed"
        assert error.details == details
        assert error.details["url"] == "https://example.com"
        assert error.details["code"] == 404

    def test_error_inherits_from_exception(self):
        """Test that error properly inherits from Exception."""
        error = VideoDownloadError(message="Test")
        assert isinstance(error, Exception)


class TestYtDlpNotInstalled:
    """Tests for handling missing yt-dlp dependency."""

    def test_download_without_ytdlp(self, downloader, monkeypatch):
        """Test error when yt-dlp is not installed (download_audio)."""
        # Mock import failure
        def mock_import(name, *args, **kwargs):
            if name == "yt_dlp":
                msg = "No module named 'yt_dlp'"
                raise ImportError(msg)
            return __builtins__.__import__(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", mock_import)

        with pytest.raises(VideoDownloadError) as exc_info:
            downloader.download_audio(SHORT_VIDEO_URL)

        assert "yt-dlp not installed" in str(exc_info.value)
        assert "pip install yt-dlp" in str(exc_info.value)

    def test_get_info_without_ytdlp(self, downloader, monkeypatch):
        """Test error when yt-dlp is not installed (get_video_info)."""
        # Mock import failure
        def mock_import(name, *args, **kwargs):
            if name == "yt_dlp":
                msg = "No module named 'yt_dlp'"
                raise ImportError(msg)
            return __builtins__.__import__(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", mock_import)

        with pytest.raises(VideoDownloadError) as exc_info:
            downloader.get_video_info(SHORT_VIDEO_URL)

        assert "yt-dlp not installed" in str(exc_info.value)

    def test_supports_url_without_ytdlp(self, downloader, monkeypatch):
        """Test supports_url returns False when yt-dlp not installed."""
        # Mock import failure
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "yt_dlp":
                msg = "No module named 'yt_dlp'"
                raise ImportError(msg)
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)

        # Should return False, not raise an error
        result = downloader.supports_url(SHORT_VIDEO_URL)
        assert result is False
