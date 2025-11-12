"""Tests for audio_processor module."""
import json
import subprocess
from unittest.mock import Mock, patch

import pytest

from ei_cli.services.audio_processor import (
    AudioProcessingError,
    AudioProcessor,
)


@pytest.fixture
def audio_processor():
    """Create an AudioProcessor instance."""
    with patch("shutil.which", return_value="/usr/bin/ffmpeg"):
        return AudioProcessor()


@pytest.fixture
def mock_subprocess_success():
    """Mock successful subprocess.run calls."""
    mock = Mock()
    mock.returncode = 0
    mock.stdout = ""
    mock.stderr = ""
    return mock


class TestAudioProcessor:
    """Tests for AudioProcessor class."""

    def test_init_with_ffmpeg(self):
        """Test AudioProcessor initialization with FFmpeg available."""
        with patch("shutil.which", return_value="/usr/bin/ffmpeg"):
            processor = AudioProcessor()
            assert processor is not None

    def test_init_without_ffmpeg(self):
        """Test AudioProcessor initialization without FFmpeg."""
        with patch("shutil.which", return_value=None):
            with pytest.raises(AudioProcessingError) as exc_info:
                AudioProcessor()
            assert "FFmpeg not found" in str(exc_info.value)
            assert "install_url" in exc_info.value.details

    def test_preprocess_basic(
        self,
        audio_processor,
        tmp_path,
        mock_subprocess_success,
    ):
        """Test basic audio preprocessing."""
        input_file = tmp_path / "input.mp3"
        input_file.write_text("fake audio")
        output_file = tmp_path / "output.wav"

        with patch("subprocess.run", return_value=mock_subprocess_success):
            result = audio_processor.preprocess(input_file, output_file)

        assert result == output_file

    def test_preprocess_auto_output_path(
        self,
        audio_processor,
        tmp_path,
        mock_subprocess_success,
    ):
        """Test preprocessing with auto-generated output path."""
        input_file = tmp_path / "input.mp3"
        input_file.write_text("fake audio")

        with patch("subprocess.run", return_value=mock_subprocess_success):
            result = audio_processor.preprocess(input_file)

        assert result == tmp_path / "input_preprocessed.wav"

    def test_preprocess_with_filters(
        self,
        audio_processor,
        tmp_path,
        mock_subprocess_success,
    ):
        """Test preprocessing with audio filters enabled."""
        input_file = tmp_path / "input.mp3"
        input_file.write_text("fake audio")

        mock_run = Mock(return_value=mock_subprocess_success)
        with patch("subprocess.run", mock_run):
            audio_processor.preprocess(input_file, apply_filters=True)

            # Verify FFmpeg command includes filters
            call_args = mock_run.call_args[0][0]
            assert "-af" in call_args
            filter_idx = call_args.index("-af")
            filters = call_args[filter_idx + 1]
            assert "highpass=f=40" in filters
            assert "lowpass=f=7000" in filters

    def test_preprocess_without_filters(
        self,
        audio_processor,
        tmp_path,
        mock_subprocess_success,
    ):
        """Test preprocessing without audio filters."""
        input_file = tmp_path / "input.mp3"
        input_file.write_text("fake audio")

        mock_run = Mock(return_value=mock_subprocess_success)
        with patch("subprocess.run", mock_run):
            audio_processor.preprocess(input_file, apply_filters=False)

            # Verify no filters in command
            call_args = mock_run.call_args[0][0]
            assert "-af" not in call_args

    def test_preprocess_custom_sample_rate(
        self,
        audio_processor,
        tmp_path,
        mock_subprocess_success,
    ):
        """Test preprocessing with custom sample rate."""
        input_file = tmp_path / "input.mp3"
        input_file.write_text("fake audio")

        mock_run = Mock(return_value=mock_subprocess_success)
        with patch("subprocess.run", mock_run):
            audio_processor.preprocess(input_file, sample_rate=44100)

            # Verify sample rate in command
            call_args = mock_run.call_args[0][0]
            assert "-ar" in call_args
            rate_idx = call_args.index("-ar")
            assert call_args[rate_idx + 1] == "44100"

    def test_preprocess_custom_channels(
        self,
        audio_processor,
        tmp_path,
        mock_subprocess_success,
    ):
        """Test preprocessing with custom channel count."""
        input_file = tmp_path / "input.mp3"
        input_file.write_text("fake audio")

        mock_run = Mock(return_value=mock_subprocess_success)
        with patch("subprocess.run", mock_run):
            audio_processor.preprocess(input_file, channels=2)

            # Verify channels in command
            call_args = mock_run.call_args[0][0]
            assert "-ac" in call_args
            channels_idx = call_args.index("-ac")
            assert call_args[channels_idx + 1] == "2"

    def test_preprocess_input_not_found(self, audio_processor, tmp_path):
        """Test preprocessing with missing input file."""
        input_file = tmp_path / "nonexistent.mp3"

        with pytest.raises(FileNotFoundError) as exc_info:
            audio_processor.preprocess(input_file)
        assert "Input file not found" in str(exc_info.value)

    def test_preprocess_ffmpeg_error(self, audio_processor, tmp_path):
        """Test preprocessing with FFmpeg error."""
        input_file = tmp_path / "input.mp3"
        input_file.write_text("fake audio")

        mock_error = subprocess.CalledProcessError(
            returncode=1,
            cmd=["ffmpeg"],
            stderr="Invalid codec",
        )

        with (
            patch("subprocess.run", side_effect=mock_error),
            pytest.raises(AudioProcessingError) as exc_info,
        ):
            audio_processor.preprocess(input_file)

        assert "FFmpeg failed" in str(exc_info.value)
        assert "Invalid codec" in str(exc_info.value)
        assert exc_info.value.details["returncode"] == 1

    def test_preprocess_ffmpeg_not_found_error(
        self,
        audio_processor,
        tmp_path,
    ):
        """Test preprocessing when FFmpeg executable not found during run."""
        input_file = tmp_path / "input.mp3"
        input_file.write_text("fake audio")

        with (
            patch("subprocess.run", side_effect=FileNotFoundError),
            pytest.raises(AudioProcessingError) as exc_info,
        ):
            audio_processor.preprocess(input_file)

        assert "FFmpeg executable not found" in str(exc_info.value)

    def test_convert_format_basic(
        self,
        audio_processor,
        tmp_path,
        mock_subprocess_success,
    ):
        """Test basic format conversion."""
        input_file = tmp_path / "input.wav"
        input_file.write_text("fake audio")
        output_file = tmp_path / "output.mp3"

        with patch("subprocess.run", return_value=mock_subprocess_success):
            result = audio_processor.convert_format(input_file, output_file)

        assert result == output_file

    def test_convert_format_with_codec(
        self,
        audio_processor,
        tmp_path,
        mock_subprocess_success,
    ):
        """Test format conversion with specific codec."""
        input_file = tmp_path / "input.wav"
        input_file.write_text("fake audio")
        output_file = tmp_path / "output.mp3"

        mock_run = Mock(return_value=mock_subprocess_success)
        with patch("subprocess.run", mock_run):
            audio_processor.convert_format(
                input_file,
                output_file,
                codec="libmp3lame",
            )

            # Verify codec in command
            call_args = mock_run.call_args[0][0]
            assert "-acodec" in call_args
            codec_idx = call_args.index("-acodec")
            assert call_args[codec_idx + 1] == "libmp3lame"

    def test_convert_format_with_bitrate(
        self,
        audio_processor,
        tmp_path,
        mock_subprocess_success,
    ):
        """Test format conversion with specific bitrate."""
        input_file = tmp_path / "input.wav"
        input_file.write_text("fake audio")
        output_file = tmp_path / "output.mp3"

        mock_run = Mock(return_value=mock_subprocess_success)
        with patch("subprocess.run", mock_run):
            audio_processor.convert_format(
                input_file,
                output_file,
                bitrate="192k",
            )

            # Verify bitrate in command
            call_args = mock_run.call_args[0][0]
            assert "-b:a" in call_args
            bitrate_idx = call_args.index("-b:a")
            assert call_args[bitrate_idx + 1] == "192k"

    def test_convert_format_with_format(
        self,
        audio_processor,
        tmp_path,
        mock_subprocess_success,
    ):
        """Test format conversion with explicit format."""
        input_file = tmp_path / "input.wav"
        input_file.write_text("fake audio")
        output_file = tmp_path / "output.audio"

        mock_run = Mock(return_value=mock_subprocess_success)
        with patch("subprocess.run", mock_run):
            audio_processor.convert_format(
                input_file,
                output_file,
                output_format="mp3",
            )

            # Verify format in command
            call_args = mock_run.call_args[0][0]
            assert "-f" in call_args
            format_idx = call_args.index("-f")
            assert call_args[format_idx + 1] == "mp3"

    def test_convert_format_input_not_found(self, audio_processor, tmp_path):
        """Test format conversion with missing input file."""
        input_file = tmp_path / "nonexistent.wav"
        output_file = tmp_path / "output.mp3"

        with pytest.raises(FileNotFoundError) as exc_info:
            audio_processor.convert_format(input_file, output_file)
        assert "Input file not found" in str(exc_info.value)

    def test_convert_format_ffmpeg_error(self, audio_processor, tmp_path):
        """Test format conversion with FFmpeg error."""
        input_file = tmp_path / "input.wav"
        input_file.write_text("fake audio")
        output_file = tmp_path / "output.mp3"

        mock_error = subprocess.CalledProcessError(
            returncode=1,
            cmd=["ffmpeg"],
            stderr="Conversion failed",
        )

        with (
            patch("subprocess.run", side_effect=mock_error),
            pytest.raises(AudioProcessingError) as exc_info,
        ):
            audio_processor.convert_format(input_file, output_file)

        assert "FFmpeg failed" in str(exc_info.value)
        assert "Conversion failed" in str(exc_info.value)

    def test_get_audio_info_success(self, audio_processor, tmp_path):
        """Test getting audio file information."""
        audio_file = tmp_path / "audio.mp3"
        audio_file.write_text("fake audio")

        mock_output = {
            "format": {
                "duration": "123.45",
                "size": "1234567",
                "bit_rate": "128000",
                "format_name": "mp3",
            },
            "streams": [
                {
                    "codec_type": "audio",
                    "sample_rate": "44100",
                    "channels": 2,
                    "codec_name": "mp3",
                },
            ],
        }

        mock_result = Mock()
        mock_result.stdout = json.dumps(mock_output)
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result):
            info = audio_processor.get_audio_info(audio_file)

        assert info["duration"] == 123.45
        assert info["size"] == 1234567
        assert info["bit_rate"] == 128000
        assert info["sample_rate"] == 44100
        assert info["channels"] == 2
        assert info["codec"] == "mp3"
        assert info["format"] == "mp3"

    def test_get_audio_info_file_not_found(self, audio_processor, tmp_path):
        """Test getting info for missing audio file."""
        audio_file = tmp_path / "nonexistent.mp3"

        with pytest.raises(FileNotFoundError) as exc_info:
            audio_processor.get_audio_info(audio_file)
        assert "Audio file not found" in str(exc_info.value)

    def test_get_audio_info_ffprobe_error(self, audio_processor, tmp_path):
        """Test getting info with ffprobe error."""
        audio_file = tmp_path / "audio.mp3"
        audio_file.write_text("fake audio")

        mock_error = subprocess.CalledProcessError(
            returncode=1,
            cmd=["ffprobe"],
            stderr="Invalid file",
        )

        with (
            patch("subprocess.run", side_effect=mock_error),
            pytest.raises(AudioProcessingError) as exc_info,
        ):
            audio_processor.get_audio_info(audio_file)

        assert "Failed to get audio info" in str(exc_info.value)
        assert "Invalid file" in str(exc_info.value)

    def test_get_audio_info_parse_error(self, audio_processor, tmp_path):
        """Test getting info with JSON parse error."""
        audio_file = tmp_path / "audio.mp3"
        audio_file.write_text("fake audio")

        mock_result = Mock()
        mock_result.stdout = "invalid json"
        mock_result.returncode = 0

        with (
            patch("subprocess.run", return_value=mock_result),
            pytest.raises(AudioProcessingError) as exc_info,
        ):
            audio_processor.get_audio_info(audio_file)

        assert "Failed to parse audio info" in str(exc_info.value)

    def test_get_audio_info_missing_stream(self, audio_processor, tmp_path):
        """Test getting info when audio stream is missing."""
        audio_file = tmp_path / "video.mp4"
        audio_file.write_text("fake video")

        mock_output = {
            "format": {
                "duration": "60.0",
                "size": "1000000",
                "bit_rate": "500000",
                "format_name": "mp4",
            },
            "streams": [
                {
                    "codec_type": "video",
                    "codec_name": "h264",
                },
            ],
        }

        mock_result = Mock()
        mock_result.stdout = json.dumps(mock_output)
        mock_result.returncode = 0

        with (
            patch("subprocess.run", return_value=mock_result),
            pytest.raises(AudioProcessingError) as exc_info,
        ):
            audio_processor.get_audio_info(audio_file)

        assert "No audio stream found" in str(exc_info.value)

    def test_validate_audio_valid(self, audio_processor, tmp_path):
        """Test validating a valid audio file."""
        audio_file = tmp_path / "audio.mp3"
        audio_file.write_text("fake audio")

        mock_output = {
            "format": {"duration": "60.0", "size": "1000000"},
            "streams": [{"codec_type": "audio", "codec_name": "mp3"}],
        }

        mock_result = Mock()
        mock_result.stdout = json.dumps(mock_output)
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result):
            result = audio_processor.validate_audio(audio_file)

        assert result is True

    def test_validate_audio_invalid(self, audio_processor, tmp_path):
        """Test validating an invalid audio file."""
        audio_file = tmp_path / "not_audio.txt"
        audio_file.write_text("plain text")

        with patch(
            "ei_cli.services.audio_processor.AudioProcessor.get_audio_info",
            side_effect=AudioProcessingError("Not an audio file"),
        ):
            result = audio_processor.validate_audio(audio_file)

        assert result is False


class TestAudioProcessingError:
    """Tests for AudioProcessingError exception."""

    def test_basic_error(self):
        """Test basic error with message only."""
        error = AudioProcessingError("Test error")
        assert str(error) == "Test error"
        assert error.details == {}

    def test_error_with_details(self):
        """Test error with additional details."""
        details = {"file": "test.mp3", "reason": "invalid format"}
        error = AudioProcessingError("Processing failed", details=details)
        assert str(error) == "Processing failed"
        assert error.details == details

    def test_error_inheritance(self):
        """Test that AudioProcessingError inherits from Exception."""
        error = AudioProcessingError("Test")
        assert isinstance(error, Exception)

    def test_error_can_be_raised(self):
        """Test that error can be raised and caught."""
        with pytest.raises(AudioProcessingError) as exc_info:
            raise AudioProcessingError("Test error", details={"test": True})

        assert "Test error" in str(exc_info.value)
        assert exc_info.value.details["test"] is True
