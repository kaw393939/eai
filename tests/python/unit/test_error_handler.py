"""Tests for error handler module."""

import pytest

from ei_cli.core import error_handler
from ei_cli.services.exceptions import (
    APIKeyMissingError,
    AudioConversionError,
    InvalidAudioError,
    TranscriptionError,
    TTSError,
    VideoDownloadError,
)


class TestErrorHandlers:
    """Test suite for error handler functions."""

    def test_handle_api_key_error(self, capsys):
        """Test API key error handler."""
        error = APIKeyMissingError("OpenAI API key not found")

        with pytest.raises(SystemExit):
            error_handler.handle_api_key_error(error)

        captured = capsys.readouterr()
        assert "API Key Missing" in captured.out
        assert "API__OPENAI_API_KEY" in captured.out
        assert "config" in captured.out.lower()

    def test_handle_video_download_error_invalid_url(self, capsys):
        """Test video download error with invalid URL."""
        error = VideoDownloadError("Invalid URL format")

        with pytest.raises(SystemExit):
            error_handler.handle_video_download_error(error)

        captured = capsys.readouterr()
        assert "Video Download Failed" in captured.out
        assert "URL format" in captured.out

    def test_handle_video_download_error_private_video(self, capsys):
        """Test video download error with private video."""
        error = VideoDownloadError("Video is private")

        with pytest.raises(SystemExit):
            error_handler.handle_video_download_error(error)

        captured = capsys.readouterr()
        assert "Video Download Failed" in captured.out
        assert "private" in captured.out.lower()

    def test_handle_video_download_error_age_restricted(self, capsys):
        """Test video download error with age-restricted video."""
        error = VideoDownloadError("Age restricted")

        with pytest.raises(SystemExit):
            error_handler.handle_video_download_error(error)

        captured = capsys.readouterr()
        assert "Video Download Failed" in captured.out

    def test_handle_video_download_error_network(self, capsys):
        """Test video download error with network issues."""
        error = VideoDownloadError("Connection timeout")

        with pytest.raises(SystemExit):
            error_handler.handle_video_download_error(error)

        captured = capsys.readouterr()
        assert "Video Download Failed" in captured.out
        assert "connection" in captured.out.lower()

    def test_handle_transcription_error_file_too_large(self, capsys):
        """Test transcription error with file too large."""
        error = TranscriptionError("File size exceeds limit")

        with pytest.raises(SystemExit):
            error_handler.handle_transcription_error(error)

        captured = capsys.readouterr()
        assert "Transcription Failed" in captured.out
        assert "size" in captured.out.lower()

    def test_handle_transcription_error_invalid_format(self, capsys):
        """Test transcription error with invalid format."""
        error = TranscriptionError("Unsupported audio format")

        with pytest.raises(SystemExit):
            error_handler.handle_transcription_error(error)

        captured = capsys.readouterr()
        assert "Transcription Failed" in captured.out
        assert "format" in captured.out.lower()

    def test_handle_transcription_error_api(self, capsys):
        """Test transcription error with API issues."""
        error = TranscriptionError("API rate limit exceeded")

        with pytest.raises(SystemExit):
            error_handler.handle_transcription_error(error)

        captured = capsys.readouterr()
        assert "Transcription Failed" in captured.out

    def test_handle_tts_error_quota_exceeded(self, capsys):
        """Test TTS error with quota exceeded."""
        error = TTSError("Quota exceeded")

        with pytest.raises(SystemExit):
            error_handler.handle_tts_error(error)

        captured = capsys.readouterr()
        assert "Text-to-Speech Failed" in captured.out
        assert "quota" in captured.out.lower()

    def test_handle_tts_error_invalid_voice(self, capsys):
        """Test TTS error with invalid voice."""
        error = TTSError("Invalid voice selection")

        with pytest.raises(SystemExit):
            error_handler.handle_tts_error(error)

        captured = capsys.readouterr()
        assert "Text-to-Speech Failed" in captured.out
        # Just check that voice-related keywords appear
        assert ("voice" in captured.out.lower() or
                "API key" in captured.out)

    def test_handle_tts_error_text_too_long(self, capsys):
        """Test TTS error with text too long."""
        error = TTSError("Text exceeds maximum length")

        with pytest.raises(SystemExit):
            error_handler.handle_tts_error(error)

        captured = capsys.readouterr()
        assert "Text-to-Speech Failed" in captured.out
        assert "length" in captured.out.lower()

    def test_handle_audio_conversion_error_ffmpeg_missing(self, capsys):
        """Test audio conversion error with missing FFmpeg."""
        error = AudioConversionError("FFmpeg not found")

        with pytest.raises(SystemExit):
            error_handler.handle_audio_conversion_error(error)

        captured = capsys.readouterr()
        assert "Audio Conversion Failed" in captured.out
        assert "FFmpeg" in captured.out
        assert "brew install ffmpeg" in captured.out

    def test_handle_audio_conversion_error_invalid_codec(self, capsys):
        """Test audio conversion error with invalid codec."""
        error = AudioConversionError("Unsupported codec")

        with pytest.raises(SystemExit):
            error_handler.handle_audio_conversion_error(error)

        captured = capsys.readouterr()
        assert "Audio Conversion Failed" in captured.out
        assert "codec" in captured.out.lower()

    def test_handle_audio_conversion_error_corrupted(self, capsys):
        """Test audio conversion error with corrupted file."""
        error = AudioConversionError("Corrupted audio stream")

        with pytest.raises(SystemExit):
            error_handler.handle_audio_conversion_error(error)

        captured = capsys.readouterr()
        assert "Audio Conversion Failed" in captured.out
        assert "corrupted" in captured.out.lower()

    def test_handle_invalid_audio_error(self, capsys):
        """Test invalid audio error handler."""
        error = InvalidAudioError("Unsupported format: .xyz")

        with pytest.raises(SystemExit):
            error_handler.handle_invalid_audio_error(error)

        captured = capsys.readouterr()
        assert "Invalid Audio File" in captured.out
        assert "Supported formats" in captured.out
        # Check for common audio formats mentioned
        assert ("MP3" in captured.out or "mp3" in captured.out.lower())

    def test_handle_general_error(self, capsys):
        """Test general error handler."""
        error = Exception("Something went wrong")

        with pytest.raises(SystemExit):
            error_handler.handle_general_error(error)

        captured = capsys.readouterr()
        assert "Error" in captured.out
        assert "Something went wrong" in captured.out
        # Check for help or troubleshooting keywords
        assert ("help" in captured.out.lower() or
                "issues" in captured.out.lower() or
                "troubleshooting" in captured.out.lower())

    def test_handle_error_dispatches_to_api_key_handler(self, capsys):
        """Test handle_error dispatches APIKeyMissingError correctly."""
        error = APIKeyMissingError("Key not found")

        with pytest.raises(SystemExit):
            error_handler.handle_error(error)

        captured = capsys.readouterr()
        assert "API Key Missing" in captured.out

    def test_handle_error_dispatches_to_video_handler(self, capsys):
        """Test handle_error dispatches VideoDownloadError correctly."""
        error = VideoDownloadError("Download failed")

        with pytest.raises(SystemExit):
            error_handler.handle_error(error)

        captured = capsys.readouterr()
        assert "Video Download Failed" in captured.out

    def test_handle_error_dispatches_to_transcription_handler(
        self, capsys,
    ):
        """Test handle_error dispatches TranscriptionError correctly."""
        error = TranscriptionError("Transcription failed")

        with pytest.raises(SystemExit):
            error_handler.handle_error(error)

        captured = capsys.readouterr()
        assert "Transcription Failed" in captured.out

    def test_handle_error_dispatches_to_tts_handler(self, capsys):
        """Test handle_error dispatches TTSError correctly."""
        error = TTSError("TTS failed")

        with pytest.raises(SystemExit):
            error_handler.handle_error(error)

        captured = capsys.readouterr()
        assert "Text-to-Speech Failed" in captured.out

    def test_handle_error_dispatches_to_audio_conversion_handler(
        self, capsys,
    ):
        """Test handle_error dispatches AudioConversionError correctly."""
        error = AudioConversionError("Conversion failed")

        with pytest.raises(SystemExit):
            error_handler.handle_error(error)

        captured = capsys.readouterr()
        assert "Audio Conversion Failed" in captured.out

    def test_handle_error_dispatches_to_invalid_audio_handler(
        self, capsys,
    ):
        """Test handle_error dispatches InvalidAudioError correctly."""
        error = InvalidAudioError("Invalid format")

        with pytest.raises(SystemExit):
            error_handler.handle_error(error)

        captured = capsys.readouterr()
        assert "Invalid Audio File" in captured.out

    def test_handle_error_dispatches_to_general_handler(self, capsys):
        """Test handle_error dispatches generic exceptions correctly."""
        error = RuntimeError("Unknown error")

        with pytest.raises(SystemExit):
            error_handler.handle_error(error)

        captured = capsys.readouterr()
        assert "Error" in captured.out
        assert "Unknown error" in captured.out

    def test_all_error_handlers_show_suggestions(self, capsys):
        """Test that all error handlers provide actionable suggestions."""
        error_test_cases = [
            APIKeyMissingError("test"),
            VideoDownloadError("test"),
            TranscriptionError("test"),
            TTSError("test"),
            AudioConversionError("test"),
            InvalidAudioError("test"),
        ]

        for error in error_test_cases:
            with pytest.raises(SystemExit):
                error_handler.handle_error(error)

            captured = capsys.readouterr()
            # All error handlers should provide meaningful output
            assert len(captured.out) > 50

    def test_error_handlers_exit_with_code_1(self):
        """Test that all error handlers exit with code 1."""
        errors = [
            APIKeyMissingError("test"),
            VideoDownloadError("test"),
            TranscriptionError("test"),
            TTSError("test"),
            AudioConversionError("test"),
            InvalidAudioError("test"),
            Exception("test"),
        ]

        for error in errors:
            with pytest.raises(SystemExit) as excinfo:
                error_handler.handle_error(error)
            assert excinfo.value.code == 1
