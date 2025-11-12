"""Tests for AudioChunker service."""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from ei_cli.services.audio_chunker import AudioChunker, AudioChunkerError


@pytest.fixture
def audio_chunker():
    """Create AudioChunker instance with mocked processor."""
    mock_processor = Mock()
    return AudioChunker(processor=mock_processor)


@pytest.fixture
def temp_audio_file(tmp_path):
    """Create a temporary audio file for testing."""
    audio_file = tmp_path / "test_audio.mp3"
    # Create a file larger than 25MB
    audio_file.write_bytes(b"0" * (26 * 1024 * 1024))
    return audio_file


@pytest.fixture
def small_audio_file(tmp_path):
    """Create a small temporary audio file."""
    audio_file = tmp_path / "small_audio.mp3"
    audio_file.write_bytes(b"0" * (1 * 1024 * 1024))  # 1MB
    return audio_file


class TestAudioChunkerInit:
    """Tests for AudioChunker initialization."""

    def test_init_with_processor(self):
        """Test initialization with audio processor."""
        mock_processor = Mock()
        chunker = AudioChunker(processor=mock_processor)
        assert chunker.processor == mock_processor

    def test_max_file_size_constant(self):
        """Test MAX_FILE_SIZE_MB constant is correctly set."""
        assert AudioChunker.MAX_FILE_SIZE_MB == 25


class TestNeedsChunking:
    """Tests for needs_chunking method."""

    def test_needs_chunking_large_file(self, audio_chunker, temp_audio_file):
        """Test that large files (>25MB) need chunking."""
        result = audio_chunker.needs_chunking(temp_audio_file)
        assert result is True

    def test_needs_chunking_small_file(self, audio_chunker, small_audio_file):
        """Test that small files (<25MB) don't need chunking."""
        result = audio_chunker.needs_chunking(small_audio_file)
        assert result is False

    def test_needs_chunking_exactly_25mb(self, audio_chunker, tmp_path):
        """Test file exactly at 25MB threshold."""
        audio_file = tmp_path / "exact_25mb.mp3"
        audio_file.write_bytes(b"0" * (25 * 1024 * 1024))
        result = audio_chunker.needs_chunking(audio_file)
        assert result is False  # Should be False (not greater than)

    def test_needs_chunking_empty_file(self, audio_chunker, tmp_path):
        """Test empty file."""
        audio_file = tmp_path / "empty.mp3"
        audio_file.write_bytes(b"")
        result = audio_chunker.needs_chunking(audio_file)
        assert result is False

    def test_needs_chunking_nonexistent_file(self, audio_chunker):
        """Test with non-existent file raises error."""
        fake_path = Path("/nonexistent/file.mp3")
        with pytest.raises(AudioChunkerError) as exc_info:
            audio_chunker.needs_chunking(fake_path)
        assert "Audio file not found" in str(exc_info.value)


class TestExtractChunk:
    """Tests for _extract_chunk method."""

    @patch("ei_cli.services.audio_chunker.subprocess.run")
    def test_extract_chunk_success(self, mock_run, audio_chunker, tmp_path):
        """Test successful chunk extraction."""
        input_file = tmp_path / "input.mp3"
        output_file = tmp_path / "chunk.wav"
        input_file.write_bytes(b"audio data")

        mock_run.return_value = Mock(returncode=0)

        audio_chunker._extract_chunk(
            input_path=input_file,
            output_path=output_file,
            start_time=0.0,
            duration=10.0,
        )

        # Verify FFmpeg was called with correct arguments
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "ffmpeg"
        assert "-i" in call_args
        assert str(input_file) in call_args
        assert "-ss" in call_args
        assert "0.0" in call_args
        assert "-t" in call_args
        assert "10.0" in call_args

    @patch("ei_cli.services.audio_chunker.subprocess.run")
    def test_extract_chunk_ffmpeg_failure(self, mock_run, audio_chunker, tmp_path):
        """Test FFmpeg failure handling."""
        input_file = tmp_path / "input.mp3"
        output_file = tmp_path / "chunk.wav"
        input_file.write_bytes(b"audio data")

        mock_run.return_value = Mock(returncode=1, stderr="FFmpeg error")

        with pytest.raises(AudioChunkerError) as exc_info:
            audio_chunker._extract_chunk(
                input_path=input_file,
                output_path=output_file,
                start_time=0.0,
                duration=10.0,
            )

        assert "FFmpeg chunk extraction failed" in str(exc_info.value)

    @patch("ei_cli.services.audio_chunker.subprocess.run")
    def test_extract_chunk_subprocess_error(self, mock_run, audio_chunker, tmp_path):
        """Test subprocess exception handling."""
        input_file = tmp_path / "input.mp3"
        output_file = tmp_path / "chunk.wav"
        input_file.write_bytes(b"audio data")

        mock_run.side_effect = FileNotFoundError("ffmpeg not found")

        with pytest.raises(AudioChunkerError) as exc_info:
            audio_chunker._extract_chunk(
                input_path=input_file,
                output_path=output_file,
                start_time=0.0,
                duration=10.0,
            )

        assert "FFmpeg not found" in str(exc_info.value)


class TestSplitAudio:
    """Tests for split_audio method."""

    def test_split_audio_single_chunk(self, audio_chunker, tmp_path):
        """Test splitting audio that results in a single chunk."""
        audio_file = tmp_path / "audio.mp3"
        audio_file.write_bytes(b"audio data")
        output_dir = tmp_path / "chunks"

        # Mock 5 minute audio with 10 minute chunks = 1 chunk
        audio_chunker.processor.get_audio_info.return_value = {
            "duration": 300.0,
        }

        with patch(
            "ei_cli.services.audio_chunker.AudioChunker._extract_chunk",
        ):
            chunks = audio_chunker.split_audio(
                audio_path=audio_file,
                output_dir=output_dir,
                chunk_duration=600,
            )

        assert len(chunks) == 1
        assert chunks[0].name == "chunk_0000.wav"

    def test_split_audio_multiple_chunks(self, audio_chunker, tmp_path):
        """Test splitting audio into multiple chunks."""
        audio_file = tmp_path / "audio.mp3"
        audio_file.write_bytes(b"audio data")
        output_dir = tmp_path / "chunks"

        # Mock 25 minute audio with 10 minute chunks = 3 chunks
        audio_chunker.processor.get_audio_info.return_value = {
            "duration": 1500.0,
        }

        with patch(
            "ei_cli.services.audio_chunker.AudioChunker._extract_chunk",
        ):
            chunks = audio_chunker.split_audio(
                audio_path=audio_file,
                output_dir=output_dir,
                chunk_duration=600,
            )

        assert len(chunks) == 3
        assert chunks[0].name == "chunk_0000.wav"
        assert chunks[1].name == "chunk_0001.wav"
        assert chunks[2].name == "chunk_0002.wav"

    def test_split_audio_creates_output_dir(self, audio_chunker, tmp_path):
        """Test that output directory is created if it doesn't exist."""
        audio_file = tmp_path / "audio.mp3"
        audio_file.write_bytes(b"audio data")
        output_dir = tmp_path / "new_chunks_dir"

        audio_chunker.processor.get_audio_info.return_value = {
            "duration": 300.0,
        }

        with patch(
            "ei_cli.services.audio_chunker.AudioChunker._extract_chunk",
        ):
            audio_chunker.split_audio(
                audio_path=audio_file,
                output_dir=output_dir,
                chunk_duration=600,
            )

        assert output_dir.exists()
        assert output_dir.is_dir()

    def test_split_audio_no_duration(self, audio_chunker, tmp_path):
        """Test with missing duration raises error."""
        audio_file = tmp_path / "audio.mp3"
        audio_file.write_bytes(b"audio data")
        output_dir = tmp_path / "chunks"

        audio_chunker.processor.get_audio_info.return_value = {
            "duration": None,
        }

        with pytest.raises(AudioChunkerError, match="Could not determine"):
            audio_chunker.split_audio(
                audio_path=audio_file,
                output_dir=output_dir,
                chunk_duration=600,
            )


class TestMergeTranscriptions:
    """Tests for merge_transcriptions method."""

    def test_merge_text_format(self, audio_chunker):
        """Test merging text format transcriptions."""
        chunks = ["Hello world", "This is a test", "Final chunk"]

        result = audio_chunker.merge_transcriptions(chunks, format_type="text")

        assert result == "Hello world This is a test Final chunk"

    def test_merge_json_format(self, audio_chunker):
        """Test merging JSON format transcriptions."""
        chunks = [
            json.dumps({"text": "First part"}),
            json.dumps({"text": "Second part"}),
            json.dumps({"text": "Third part"}),
        ]

        result = audio_chunker.merge_transcriptions(chunks, format_type="json")
        result_dict = json.loads(result)

        assert result_dict["text"] == "First part Second part Third part"

    def test_merge_json_empty_text(self, audio_chunker):
        """Test merging JSON with missing text keys."""
        chunks = [
            json.dumps({"text": "First"}),
            json.dumps({}),  # Missing text key
            json.dumps({"text": "Third"}),
        ]

        result = audio_chunker.merge_transcriptions(chunks, format_type="json")
        result_dict = json.loads(result)

        assert result_dict["text"] == "First  Third"

    @patch.object(AudioChunker, "_merge_subtitles")
    def test_merge_srt_format(self, mock_merge_subtitles, audio_chunker):
        """Test merging SRT format calls subtitle merger."""
        chunks = ["chunk1 srt", "chunk2 srt"]
        mock_merge_subtitles.return_value = "merged srt"

        result = audio_chunker.merge_transcriptions(chunks, format_type="srt")

        assert result == "merged srt"
        mock_merge_subtitles.assert_called_once_with(chunks, "srt")

    @patch.object(AudioChunker, "_merge_subtitles")
    def test_merge_vtt_format(self, mock_merge_subtitles, audio_chunker):
        """Test merging VTT format calls subtitle merger."""
        chunks = ["chunk1 vtt", "chunk2 vtt"]
        mock_merge_subtitles.return_value = "merged vtt"

        result = audio_chunker.merge_transcriptions(chunks, format_type="vtt")

        assert result == "merged vtt"
        mock_merge_subtitles.assert_called_once_with(chunks, "vtt")

    def test_merge_unsupported_format(self, audio_chunker):
        """Test merging with unsupported format raises error."""
        chunks = ["chunk1", "chunk2"]

        with pytest.raises(AudioChunkerError) as exc_info:
            audio_chunker.merge_transcriptions(chunks, format_type="xml")

        assert "Unsupported format" in str(exc_info.value)
        assert "xml" in str(exc_info.value)


class TestMergeSubtitles:
    """Tests for _merge_subtitles method."""

    def test_merge_srt_basic(self, audio_chunker):
        """Test basic SRT merging."""
        chunks = [
            "1\n00:00:01,000 --> 00:00:05,000\nFirst subtitle\n\n",
            "1\n00:00:01,000 --> 00:00:05,000\nSecond subtitle\n\n",
        ]

        result = audio_chunker._merge_subtitles(chunks, format_type="srt")

        # Should have sequential numbering and timestamps
        assert "1\n" in result
        assert "2\n" in result
        assert "First subtitle" in result
        assert "Second subtitle" in result

    def test_merge_vtt_with_header(self, audio_chunker):
        """Test VTT merging skips headers."""
        chunks = [
            "WEBVTT\n\n00:00:01.000 --> 00:00:05.000\nFirst subtitle\n\n",
            "WEBVTT\n\n00:00:01.000 --> 00:00:05.000\nSecond subtitle\n\n",
        ]

        result = audio_chunker._merge_subtitles(chunks, format_type="vtt")

        # Should only have one WEBVTT header at the start
        assert result.startswith("WEBVTT")
        assert result.count("WEBVTT") == 1
        assert "First subtitle" in result
        assert "Second subtitle" in result

    def test_merge_subtitles_empty_chunks(self, audio_chunker):
        """Test merging empty subtitle chunks."""
        chunks = ["", "\n\n", ""]

        result = audio_chunker._merge_subtitles(chunks, format_type="srt")

        assert result == ""


class TestAdjustTimestamp:
    """Tests for _adjust_timestamp method."""

    def test_adjust_srt_timestamp(self, audio_chunker):
        """Test adjusting SRT timestamp."""
        timestamp_line = "00:00:01,000 --> 00:00:05,000"
        offset = 10.0

        result = audio_chunker._adjust_timestamp(timestamp_line, offset)

        assert "00:00:11,000 --> 00:00:15,000" in result

    def test_adjust_vtt_timestamp(self, audio_chunker):
        """Test adjusting VTT timestamp."""
        timestamp_line = "00:00:01.000 --> 00:00:05.000"
        offset = 10.0

        result = audio_chunker._adjust_timestamp(timestamp_line, offset)

        assert "00:00:11.000 --> 00:00:15.000" in result

    def test_adjust_timestamp_zero_offset(self, audio_chunker):
        """Test adjusting timestamp with zero offset."""
        timestamp_line = "00:00:01,000 --> 00:00:05,000"
        offset = 0.0

        result = audio_chunker._adjust_timestamp(timestamp_line, offset)

        assert result == timestamp_line

    def test_adjust_timestamp_large_offset(self, audio_chunker):
        """Test adjusting timestamp with large offset."""
        timestamp_line = "00:00:01,000 --> 00:00:05,000"
        offset = 3600.0  # 1 hour

        result = audio_chunker._adjust_timestamp(timestamp_line, offset)

        assert "01:00:01,000 --> 01:00:05,000" in result


class TestCleanupChunks:
    """Tests for cleanup_chunks method."""

    def test_cleanup_existing_chunks(self, audio_chunker, tmp_path):
        """Test cleanup removes all chunk files."""
        # Create some chunk files
        chunk1 = tmp_path / "chunk_001.wav"
        chunk2 = tmp_path / "chunk_002.wav"
        chunk3 = tmp_path / "chunk_003.wav"
        chunk1.write_bytes(b"chunk1")
        chunk2.write_bytes(b"chunk2")
        chunk3.write_bytes(b"chunk3")

        chunks = [chunk1, chunk2, chunk3]

        audio_chunker.cleanup_chunks(chunks)

        assert not chunk1.exists()
        assert not chunk2.exists()
        assert not chunk3.exists()

    def test_cleanup_nonexistent_files(self, audio_chunker, tmp_path):
        """Test cleanup handles non-existent files gracefully."""
        chunk1 = tmp_path / "nonexistent_001.wav"
        chunk2 = tmp_path / "nonexistent_002.wav"

        chunks = [chunk1, chunk2]

        # Should not raise error
        audio_chunker.cleanup_chunks(chunks)

    def test_cleanup_mixed_files(self, audio_chunker, tmp_path):
        """Test cleanup with mix of existing and non-existent files."""
        chunk1 = tmp_path / "exists.wav"
        chunk2 = tmp_path / "nonexistent.wav"
        chunk1.write_bytes(b"exists")

        chunks = [chunk1, chunk2]

        audio_chunker.cleanup_chunks(chunks)

        assert not chunk1.exists()

    def test_cleanup_empty_list(self, audio_chunker):
        """Test cleanup with empty list."""
        # Should not raise error
        audio_chunker.cleanup_chunks([])


class TestAudioChunkerError:
    """Tests for AudioChunkerError exception."""

    def test_error_with_message(self):
        """Test error creation with message."""
        error = AudioChunkerError("Test error")
        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.details == {}

    def test_error_with_details(self):
        """Test error creation with details."""
        details = {"file": "test.mp3", "duration": 120}
        error = AudioChunkerError("Test error", details=details)

        assert error.message == "Test error"
        assert error.details == details
        assert error.details["file"] == "test.mp3"
        assert error.details["duration"] == 120

    def test_error_inherits_from_exception(self):
        """Test that AudioChunkerError inherits from Exception."""
        error = AudioChunkerError("Test")
        assert isinstance(error, Exception)
