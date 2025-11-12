"""Tests for translate-audio CLI command."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from ei_cli.cli.commands.translate_audio import translate_audio
from ei_cli.core.errors import AIServiceError, ConfigurationError
from ei_cli.services.base import ServiceUnavailableError


class TestTranslateAudioCommand:
    """Test suite for translate-audio command."""

    @pytest.fixture
    def runner(self):
        """Create CLI runner."""
        return CliRunner()

    @pytest.fixture
    def mock_service_factory(self):
        """Mock ServiceFactory."""
        with patch(
            "ei_cli.cli.commands.translate_audio.ServiceFactory",
        ) as mock:
            yield mock

    @pytest.fixture
    def mock_ai_service(self):
        """Create mock AI service with translation result."""
        service = MagicMock()
        service.check_available.return_value = True

        # Mock translation result
        result = MagicMock()
        result.text = "This is the translated English text."
        result.language = "es"
        result.duration = 45.5
        result.model = "whisper-1"
        service.translate_audio.return_value = result

        return service

    @pytest.fixture
    def audio_file(self, tmp_path):
        """Create temporary audio file."""
        audio = tmp_path / "test_audio.mp3"
        audio.write_bytes(b"fake audio data")
        return audio

    def test_basic_translation(
        self, runner, mock_service_factory, mock_ai_service, audio_file,
    ):
        """Test basic audio translation."""
        mock_service_factory.return_value.get_ai_service.return_value = (
            mock_ai_service
        )

        result = runner.invoke(translate_audio, [str(audio_file)])

        assert result.exit_code == 0
        assert "Translating audio to English" in result.output
        assert "This is the translated English text." in result.output
        assert "Translation complete" in result.output or "Translation:" in result.output
        mock_ai_service.translate_audio.assert_called_once()

    def test_translation_with_json_format(
        self, runner, mock_service_factory, mock_ai_service, audio_file,
    ):
        """Test translation with JSON output format."""
        mock_service_factory.return_value.get_ai_service.return_value = (
            mock_ai_service
        )

        result = runner.invoke(
            translate_audio, [str(audio_file), "--format", "json"],
        )

        assert result.exit_code == 0
        assert "text" in result.output
        assert "language" in result.output
        assert "duration" in result.output
        assert "This is the translated English text." in result.output

    def test_translation_with_srt_format(
        self, runner, mock_service_factory, mock_ai_service, audio_file,
    ):
        """Test translation with SRT subtitle format."""
        mock_ai_service.translate_audio.return_value.text = (
            "1\n00:00:00,000 --> 00:00:05,000\nHello world"
        )
        mock_service_factory.return_value.get_ai_service.return_value = (
            mock_ai_service
        )

        result = runner.invoke(
            translate_audio, [str(audio_file), "--format", "srt"],
        )

        assert result.exit_code == 0
        mock_ai_service.translate_audio.assert_called_once_with(
            audio_path=audio_file,
            prompt=None,
            response_format="srt",
            temperature=0.0,
            preprocess=True,
        )

    def test_translation_with_output_file(
        self,
        runner,
        mock_service_factory,
        mock_ai_service,
        audio_file,
        tmp_path,
    ):
        """Test translation with output file."""
        output_file = tmp_path / "translation.txt"
        mock_service_factory.return_value.get_ai_service.return_value = (
            mock_ai_service
        )

        result = runner.invoke(
            translate_audio, [str(audio_file), "--output", str(output_file)],
        )

        assert result.exit_code == 0
        assert output_file.exists()
        assert "Translation complete!" in result.output
        content = output_file.read_text()
        assert "This is the translated English text." in content

    def test_translation_with_prompt(
        self, runner, mock_service_factory, mock_ai_service, audio_file,
    ):
        """Test translation with style prompt."""
        mock_service_factory.return_value.get_ai_service.return_value = (
            mock_ai_service
        )

        result = runner.invoke(
            translate_audio,
            [str(audio_file), "--prompt", "Formal business translation"],
        )

        assert result.exit_code == 0
        mock_ai_service.translate_audio.assert_called_once_with(
            audio_path=audio_file,
            prompt="Formal business translation",
            response_format="text",
            temperature=0.0,
            preprocess=True,
        )

    def test_translation_with_temperature(
        self, runner, mock_service_factory, mock_ai_service, audio_file,
    ):
        """Test translation with custom temperature."""
        mock_service_factory.return_value.get_ai_service.return_value = (
            mock_ai_service
        )

        result = runner.invoke(
            translate_audio, [str(audio_file), "--temperature", "0.5"],
        )

        assert result.exit_code == 0
        mock_ai_service.translate_audio.assert_called_once_with(
            audio_path=audio_file,
            prompt=None,
            response_format="text",
            temperature=0.5,
            preprocess=True,
        )

    def test_translation_no_preprocess(
        self, runner, mock_service_factory, mock_ai_service, audio_file,
    ):
        """Test translation without preprocessing."""
        mock_service_factory.return_value.get_ai_service.return_value = (
            mock_ai_service
        )

        result = runner.invoke(
            translate_audio, [str(audio_file), "--no-preprocess"],
        )

        assert result.exit_code == 0
        mock_ai_service.translate_audio.assert_called_once_with(
            audio_path=audio_file,
            prompt=None,
            response_format="text",
            temperature=0.0,
            preprocess=False,
        )

    def test_translation_with_vtt_format(
        self, runner, mock_service_factory, mock_ai_service, audio_file,
    ):
        """Test translation with VTT subtitle format."""
        mock_ai_service.translate_audio.return_value.text = (
            "WEBVTT\n\n00:00:00.000 --> 00:00:05.000\nHello world"
        )
        mock_service_factory.return_value.get_ai_service.return_value = (
            mock_ai_service
        )

        result = runner.invoke(
            translate_audio, [str(audio_file), "--format", "vtt"],
        )

        assert result.exit_code == 0
        mock_ai_service.translate_audio.assert_called_once_with(
            audio_path=audio_file,
            prompt=None,
            response_format="vtt",
            temperature=0.0,
            preprocess=True,
        )

    def test_translation_json_output_to_file(
        self,
        runner,
        mock_service_factory,
        mock_ai_service,
        audio_file,
        tmp_path,
    ):
        """Test JSON format output to file."""
        output_file = tmp_path / "translation.json"
        mock_service_factory.return_value.get_ai_service.return_value = (
            mock_ai_service
        )

        result = runner.invoke(
            translate_audio,
            [
                str(audio_file),
                "--format",
                "json",
                "--output",
                str(output_file),
            ],
        )

        assert result.exit_code == 0
        assert output_file.exists()
        content = output_file.read_text()
        assert '"text"' in content
        assert '"language"' in content
        assert '"duration"' in content

    def test_file_not_found(self, runner, mock_service_factory):
        """Test translation with non-existent file."""
        result = runner.invoke(
            translate_audio, ["nonexistent_audio.mp3"],
        )

        assert result.exit_code != 0
        assert "does not exist" in result.output.lower() or "Error" in result.output

    def test_configuration_error(
        self, runner, mock_service_factory, audio_file,
    ):
        """Test translation with configuration error."""
        mock_service_factory.return_value.get_ai_service.side_effect = (
            ConfigurationError("API key not configured")
        )

        result = runner.invoke(translate_audio, [str(audio_file)])

        assert result.exit_code == 1
        assert "Configuration Error" in result.output
        assert "API key not configured" in result.output

    def test_service_unavailable(
        self, runner, mock_service_factory, mock_ai_service, audio_file,
    ):
        """Test translation when service is unavailable."""
        # Mock the service to raise ServiceUnavailableError properly
        mock_ai_service.translate_audio.side_effect = (
            ServiceUnavailableError(
                "OpenAI API key not configured",
                service_name="AI Service",
            )
        )
        mock_service_factory.return_value.get_ai_service.return_value = (
            mock_ai_service
        )

        result = runner.invoke(translate_audio, [str(audio_file)])

        assert result.exit_code == 1
        assert (
            "Service Unavailable" in result.output
            or "not configured" in result.output
        )

    def test_ai_service_error(
        self, runner, mock_service_factory, mock_ai_service, audio_file,
    ):
        """Test translation with AI service error."""
        mock_ai_service.translate_audio.side_effect = AIServiceError(
            "Translation failed", code="translation_error",
        )
        mock_service_factory.return_value.get_ai_service.return_value = (
            mock_ai_service
        )

        result = runner.invoke(translate_audio, [str(audio_file)])

        assert result.exit_code == 1
        assert "AI Service Error" in result.output
        assert "Translation failed" in result.output

    def test_generic_exception(
        self, runner, mock_service_factory, mock_ai_service, audio_file,
    ):
        """Test translation with unexpected error."""
        mock_ai_service.translate_audio.side_effect = RuntimeError(
            "Unexpected error",
        )
        mock_service_factory.return_value.get_ai_service.return_value = (
            mock_ai_service
        )

        result = runner.invoke(translate_audio, [str(audio_file)])

        assert result.exit_code == 1
        assert "Error" in result.output
        assert "Unexpected error" in result.output

    def test_shows_file_info(
        self, runner, mock_service_factory, mock_ai_service, audio_file,
    ):
        """Test that command shows file information."""
        mock_service_factory.return_value.get_ai_service.return_value = (
            mock_ai_service
        )

        result = runner.invoke(translate_audio, [str(audio_file)])

        assert result.exit_code == 0
        assert str(audio_file) in result.output
        assert "text" in result.output.lower()

    def test_shows_metadata(
        self, runner, mock_service_factory, mock_ai_service, audio_file,
    ):
        """Test that command shows metadata for text output."""
        mock_service_factory.return_value.get_ai_service.return_value = (
            mock_ai_service
        )

        result = runner.invoke(translate_audio, [str(audio_file)])

        assert result.exit_code == 0
        # Metadata should be shown for text output without file
        assert (
            "Metadata:" in result.output
            or "Language:" in result.output
            or "whisper" in result.output.lower()
        )

    def test_combined_options(
        self,
        runner,
        mock_service_factory,
        mock_ai_service,
        audio_file,
        tmp_path,
    ):
        """Test translation with multiple options combined."""
        output_file = tmp_path / "output.srt"
        mock_service_factory.return_value.get_ai_service.return_value = (
            mock_ai_service
        )

        result = runner.invoke(
            translate_audio,
            [
                str(audio_file),
                "--format",
                "srt",
                "--output",
                str(output_file),
                "--prompt",
                "Medical terminology",
                "--temperature",
                "0.2",
                "--no-preprocess",
            ],
        )

        assert result.exit_code == 0
        assert output_file.exists()
        mock_ai_service.translate_audio.assert_called_once_with(
            audio_path=audio_file,
            prompt="Medical terminology",
            response_format="srt",
            temperature=0.2,
            preprocess=False,
        )
