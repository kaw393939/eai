"""Tests for speak command."""
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from ei_cli.cli.commands.speak import speak
from ei_cli.core.errors import AIServiceError, ConfigurationError
from ei_cli.services.ai_service import TextToSpeechResult


@pytest.fixture
def mock_service_factory():
    """Mock service factory."""
    factory = Mock()
    return factory


@pytest.fixture
def mock_ai_service():
    """Mock AI service."""
    service = Mock()
    service.check_available.return_value = True
    service.text_to_speech.return_value = TextToSpeechResult(
        audio_path=Path("/tmp/output.mp3"),
        model="tts-1",
        voice="alloy",
    )
    return service


class TestSpeakCommand:
    """Test suite for speak command."""

    def test_speak_with_text_argument(
        self,
        mock_service_factory,
        mock_ai_service,
        tmp_path,
    ):
        """Test speak command with text argument."""
        runner = CliRunner()
        output_file = tmp_path / "output.mp3"

        mock_service_factory.get_ai_service.return_value = mock_ai_service

        with patch(
            "ei_cli.cli.commands.speak.ServiceFactory",
            return_value=mock_service_factory,
        ):
            result = runner.invoke(
                speak,
                ["Hello, world!", "-o", str(output_file)],
            )

        assert result.exit_code == 0
        assert "Speech generated!" in result.output
        mock_ai_service.text_to_speech.assert_called_once()

    def test_speak_with_input_file(
        self,
        mock_service_factory,
        mock_ai_service,
        tmp_path,
    ):
        """Test speak command with input file."""
        runner = CliRunner()
        input_file = tmp_path / "input.txt"
        input_file.write_text("This is a test.")
        output_file = tmp_path / "output.mp3"

        mock_service_factory.get_ai_service.return_value = mock_ai_service

        with patch(
            "ei_cli.cli.commands.speak.ServiceFactory",
            return_value=mock_service_factory,
        ):
            result = runner.invoke(
                speak,
                ["-i", str(input_file), "-o", str(output_file)],
            )

        assert result.exit_code == 0
        assert "Speech generated!" in result.output

    def test_speak_with_voice_option(
        self,
        mock_service_factory,
        mock_ai_service,
        tmp_path,
    ):
        """Test speak command with custom voice."""
        runner = CliRunner()
        output_file = tmp_path / "output.mp3"

        mock_service_factory.get_ai_service.return_value = mock_ai_service

        with patch(
            "ei_cli.cli.commands.speak.ServiceFactory",
            return_value=mock_service_factory,
        ):
            result = runner.invoke(
                speak,
                ["Test text", "-v", "nova", "-o", str(output_file)],
            )

        assert result.exit_code == 0
        assert "Voice: nova" in result.output
        call_kwargs = mock_ai_service.text_to_speech.call_args[1]
        assert call_kwargs["voice"] == "nova"

    def test_speak_with_speed_option(
        self,
        mock_service_factory,
        mock_ai_service,
        tmp_path,
    ):
        """Test speak command with custom speed."""
        runner = CliRunner()
        output_file = tmp_path / "output.mp3"

        mock_service_factory.get_ai_service.return_value = mock_ai_service

        with patch(
            "ei_cli.cli.commands.speak.ServiceFactory",
            return_value=mock_service_factory,
        ):
            result = runner.invoke(
                speak,
                ["Test text", "-s", "1.5", "-o", str(output_file)],
            )

        assert result.exit_code == 0
        assert "Speed: 1.5x" in result.output
        call_kwargs = mock_ai_service.text_to_speech.call_args[1]
        assert call_kwargs["speed"] == 1.5

    def test_speak_with_model_option(
        self,
        mock_service_factory,
        mock_ai_service,
        tmp_path,
    ):
        """Test speak command with HD model."""
        runner = CliRunner()
        output_file = tmp_path / "output.mp3"

        mock_service_factory.get_ai_service.return_value = mock_ai_service

        with patch(
            "ei_cli.cli.commands.speak.ServiceFactory",
            return_value=mock_service_factory,
        ):
            result = runner.invoke(
                speak,
                ["Test text", "-m", "tts-1-hd", "-o", str(output_file)],
            )

        assert result.exit_code == 0
        assert "Model: tts-1-hd" in result.output
        call_kwargs = mock_ai_service.text_to_speech.call_args[1]
        assert call_kwargs["model"] == "tts-1-hd"

    def test_speak_no_text_or_input(
        self,
        mock_service_factory,
        mock_ai_service,
        tmp_path,
    ):
        """Test error when neither text nor input file provided."""
        runner = CliRunner()
        output_file = tmp_path / "output.mp3"

        with patch(
            "ei_cli.cli.commands.speak.ServiceFactory",
            return_value=mock_service_factory,
        ):
            result = runner.invoke(speak, ["-o", str(output_file)])

        assert result.exit_code != 0  # Should fail
        assert "Must provide either text argument or --input file" in (
            result.output
        )

    def test_speak_both_text_and_input(
        self,
        mock_service_factory,
        mock_ai_service,
        tmp_path,
    ):
        """Test error when both text and input file provided."""
        runner = CliRunner()
        input_file = tmp_path / "input.txt"
        input_file.write_text("Test")
        output_file = tmp_path / "output.mp3"

        with patch(
            "ei_cli.cli.commands.speak.ServiceFactory",
            return_value=mock_service_factory,
        ):
            result = runner.invoke(
                speak,
                ["Test text", "-i", str(input_file), "-o", str(output_file)],
            )

        assert result.exit_code != 0  # Should fail
        assert "Cannot use both text argument and --input file" in (
            result.output
        )

    def test_speak_empty_input_file(
        self,
        mock_service_factory,
        mock_ai_service,
        tmp_path,
    ):
        """Test error when input file is empty."""
        runner = CliRunner()
        input_file = tmp_path / "empty.txt"
        input_file.write_text("")
        output_file = tmp_path / "output.mp3"

        with patch(
            "ei_cli.cli.commands.speak.ServiceFactory",
            return_value=mock_service_factory,
        ):
            result = runner.invoke(
                speak,
                ["-i", str(input_file), "-o", str(output_file)],
            )

        assert result.exit_code == 1
        assert "Input file is empty" in result.output

    def test_speak_configuration_error(
        self,
        mock_service_factory,
        tmp_path,
    ):
        """Test handling of configuration error."""
        runner = CliRunner()
        output_file = tmp_path / "output.mp3"

        mock_service_factory.get_ai_service.side_effect = (
            ConfigurationError("API key not set")
        )

        with patch(
            "ei_cli.cli.commands.speak.ServiceFactory",
            return_value=mock_service_factory,
        ):
            result = runner.invoke(
                speak,
                ["Test text", "-o", str(output_file)],
            )

        assert result.exit_code == 1
        assert "Configuration Error" in result.output

    def test_speak_service_unavailable(
        self,
        mock_service_factory,
        mock_ai_service,
        tmp_path,
    ):
        """Test handling when service is unavailable."""
        runner = CliRunner()
        output_file = tmp_path / "output.mp3"

        mock_ai_service.check_available.return_value = False
        mock_service_factory.get_ai_service.return_value = mock_ai_service

        with patch(
            "ei_cli.cli.commands.speak.ServiceFactory",
            return_value=mock_service_factory,
        ):
            result = runner.invoke(
                speak,
                ["Test text", "-o", str(output_file)],
            )

        assert result.exit_code == 1
        assert "Service Unavailable" in result.output

    def test_speak_ai_service_error(
        self,
        mock_service_factory,
        mock_ai_service,
        tmp_path,
    ):
        """Test handling of AI service error."""
        runner = CliRunner()
        output_file = tmp_path / "output.mp3"

        mock_ai_service.text_to_speech.side_effect = AIServiceError(
            message="API error",
            code="api_error",
        )
        mock_service_factory.get_ai_service.return_value = mock_ai_service

        with patch(
            "ei_cli.cli.commands.speak.ServiceFactory",
            return_value=mock_service_factory,
        ):
            result = runner.invoke(
                speak,
                ["Test text", "-o", str(output_file)],
            )

        assert result.exit_code == 1
        assert "AI Service Error" in result.output

    def test_speak_all_voices(
        self,
        mock_service_factory,
        mock_ai_service,
        tmp_path,
    ):
        """Test all available voices with appropriate models."""
        runner = CliRunner()

        # Standard voices work with both models
        standard_voices = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
        # tts-1 exclusive voices
        tts1_voices = ["ash", "ballad", "coral", "sage", "verse"]
        # tts-1-hd exclusive voices
        hd_voices = ["marin", "cedar"]

        mock_service_factory.get_ai_service.return_value = mock_ai_service

        # Test standard voices with tts-1
        for voice in standard_voices:
            output_file = tmp_path / f"{voice}_standard.mp3"

            with patch(
                "ei_cli.cli.commands.speak.ServiceFactory",
                return_value=mock_service_factory,
            ):
                result = runner.invoke(
                    speak,
                    ["Test", "-v", voice, "-o", str(output_file)],
                )

            assert result.exit_code == 0
            assert f"Voice: {voice}" in result.output

        # Test tts-1 exclusive voices
        for voice in tts1_voices:
            output_file = tmp_path / f"{voice}_tts1.mp3"

            with patch(
                "ei_cli.cli.commands.speak.ServiceFactory",
                return_value=mock_service_factory,
            ):
                result = runner.invoke(
                    speak,
                    ["Test", "-v", voice, "-m", "tts-1", "-o", str(output_file)],
                )

            assert result.exit_code == 0
            assert f"Voice: {voice}" in result.output

        # Test tts-1-hd exclusive voices
        for voice in hd_voices:
            output_file = tmp_path / f"{voice}_hd.mp3"

            with patch(
                "ei_cli.cli.commands.speak.ServiceFactory",
                return_value=mock_service_factory,
            ):
                result = runner.invoke(
                    speak,
                    ["Test", "-v", voice, "-m", "tts-1-hd", "-o", str(output_file)],
                )

            assert result.exit_code == 0
            assert f"Voice: {voice}" in result.output

    def test_speak_voice_model_validation(
        self,
        mock_service_factory,
        mock_ai_service,
        tmp_path,
    ):
        """Test voice/model compatibility validation."""
        runner = CliRunner()
        output_file = tmp_path / "output.mp3"

        mock_service_factory.get_ai_service.return_value = mock_ai_service

        # Test marin voice requires tts-1-hd
        with patch(
            "ei_cli.cli.commands.speak.ServiceFactory",
            return_value=mock_service_factory,
        ):
            result = runner.invoke(
                speak,
                ["Test", "-v", "marin", "-m", "tts-1", "-o", str(output_file)],
            )

        assert result.exit_code == 1
        assert "only available with tts-1-hd" in result.output

        # Test cedar voice requires tts-1-hd
        with patch(
            "ei_cli.cli.commands.speak.ServiceFactory",
            return_value=mock_service_factory,
        ):
            result = runner.invoke(
                speak,
                ["Test", "-v", "cedar", "-m", "tts-1", "-o", str(output_file)],
            )

        assert result.exit_code == 1
        assert "only available with tts-1-hd" in result.output

        # Test ballad voice requires tts-1
        with patch(
            "ei_cli.cli.commands.speak.ServiceFactory",
            return_value=mock_service_factory,
        ):
            result = runner.invoke(
                speak,
                ["Test", "-v", "ballad", "-m", "tts-1-hd", "-o", str(output_file)],
            )

        assert result.exit_code == 1
        assert "only available with tts-1" in result.output

        # Test sage voice requires tts-1
        with patch(
            "ei_cli.cli.commands.speak.ServiceFactory",
            return_value=mock_service_factory,
        ):
            result = runner.invoke(
                speak,
                ["Test", "-v", "sage", "-m", "tts-1-hd", "-o", str(output_file)],
            )

        assert result.exit_code == 1
        assert "only available with tts-1" in result.output

    def test_speak_speed_range(
        self,
        mock_service_factory,
        mock_ai_service,
        tmp_path,
    ):
        """Test speed range validation."""
        runner = CliRunner()
        output_file = tmp_path / "output.mp3"

        mock_service_factory.get_ai_service.return_value = mock_ai_service

        # Test minimum speed
        with patch(
            "ei_cli.cli.commands.speak.ServiceFactory",
            return_value=mock_service_factory,
        ):
            result = runner.invoke(
                speak,
                ["Test", "-s", "0.25", "-o", str(output_file)],
            )
        assert result.exit_code == 0

        # Test maximum speed
        with patch(
            "ei_cli.cli.commands.speak.ServiceFactory",
            return_value=mock_service_factory,
        ):
            result = runner.invoke(
                speak,
                ["Test", "-s", "4.0", "-o", str(output_file)],
            )
        assert result.exit_code == 0

    def test_speak_generic_exception(
        self,
        mock_service_factory,
        mock_ai_service,
        tmp_path,
    ):
        """Test handling of generic exception."""
        runner = CliRunner()
        output_file = tmp_path / "output.mp3"

        mock_ai_service.text_to_speech.side_effect = Exception(
            "Unexpected error",
        )
        mock_service_factory.get_ai_service.return_value = mock_ai_service

        with patch(
            "ei_cli.cli.commands.speak.ServiceFactory",
            return_value=mock_service_factory,
        ):
            result = runner.invoke(
                speak,
                ["Test text", "-o", str(output_file)],
            )

        assert result.exit_code == 1
        assert "Error" in result.output

    def test_speak_with_playback_success(
        self,
        mock_service_factory,
        mock_ai_service,
        tmp_path,
    ):
        """Test speak with playback when dependencies are available."""
        runner = CliRunner()
        output_file = tmp_path / "output.mp3"

        mock_result = Mock()
        mock_result.audio_path = output_file
        mock_ai_service.text_to_speech.return_value = mock_result
        mock_service_factory.get_ai_service.return_value = mock_ai_service

        # Create actual audio file for playback
        output_file.write_bytes(b"fake audio data")

        # Mock pydub modules
        mock_audio_segment = Mock()
        mock_play = Mock()

        with patch(
            "ei_cli.cli.commands.speak.ServiceFactory",
            return_value=mock_service_factory,
        ), patch.dict(
            "sys.modules",
            {
                "pydub": Mock(AudioSegment=mock_audio_segment),
                "pydub.playback": Mock(play=mock_play),
            },
        ):
            result = runner.invoke(
                speak,
                ["Test text", "-o", str(output_file), "--play"],
            )

        assert result.exit_code == 0
        assert "Speech generated" in result.output
        assert "Playing audio" in result.output

    def test_speak_with_playback_missing_dependencies(
        self,
        mock_service_factory,
        mock_ai_service,
        tmp_path,
    ):
        """Test speak with playback when dependencies are missing."""
        runner = CliRunner()
        output_file = tmp_path / "output.mp3"

        mock_result = Mock()
        mock_result.audio_path = output_file
        mock_ai_service.text_to_speech.return_value = mock_result
        mock_service_factory.get_ai_service.return_value = mock_ai_service

        output_file.write_bytes(b"fake audio data")

        with patch(
            "ei_cli.cli.commands.speak.ServiceFactory",
            return_value=mock_service_factory,
        ):
            result = runner.invoke(
                speak,
                ["Test text", "-o", str(output_file), "--play"],
            )

        assert result.exit_code == 0
        assert "Speech generated" in result.output
        assert "Playback unavailable" in result.output
        assert "pip install pydub simpleaudio" in result.output

    def test_speak_with_playback_error(
        self,
        mock_service_factory,
        mock_ai_service,
        tmp_path,
    ):
        """Test speak with playback when playback fails."""
        runner = CliRunner()
        output_file = tmp_path / "output.mp3"

        mock_result = Mock()
        mock_result.audio_path = output_file
        mock_ai_service.text_to_speech.return_value = mock_result
        mock_service_factory.get_ai_service.return_value = mock_ai_service

        output_file.write_bytes(b"fake audio data")

        # Mock pydub but make play fail
        mock_audio_segment = Mock()
        mock_audio_segment.from_file.side_effect = Exception("Playback error")
        mock_play = Mock()

        with patch(
            "ei_cli.cli.commands.speak.ServiceFactory",
            return_value=mock_service_factory,
        ), patch.dict(
            "sys.modules",
            {
                "pydub": Mock(AudioSegment=mock_audio_segment),
                "pydub.playback": Mock(play=mock_play),
            },
        ):
            result = runner.invoke(
                speak,
                ["Test text", "-o", str(output_file), "--play"],
            )

        assert result.exit_code == 0
        assert "Speech generated" in result.output
        assert "Playback failed" in result.output

    def test_speak_integration_all_options(
        self,
        mock_service_factory,
        mock_ai_service,
        tmp_path,
    ):
        """Integration test with all options combined."""
        runner = CliRunner()
        output_file = tmp_path / "integration.flac"
        input_file = tmp_path / "input.txt"
        input_file.write_text("Integration test text")

        mock_result = Mock()
        mock_result.audio_path = output_file
        mock_ai_service.text_to_speech_stream.return_value = mock_result
        mock_service_factory.get_ai_service.return_value = mock_ai_service

        with patch(
            "ei_cli.cli.commands.speak.ServiceFactory",
            return_value=mock_service_factory,
        ):
            result = runner.invoke(
                speak,
                [
                    "--input", str(input_file),
                    "-o", str(output_file),
                    "-v", "marin",
                    "-m", "tts-1-hd",
                    "-s", "0.9",
                    "-f", "flac",
                    "--instructions", "Speak clearly",
                    "--stream",
                ],
            )

        assert result.exit_code == 0
        assert "Speech generated" in result.output

        # Verify all parameters were passed correctly
        call_kwargs = mock_ai_service.text_to_speech_stream.call_args[1]
        assert call_kwargs["voice"] == "marin"
        assert call_kwargs["model"] == "tts-1-hd"
        assert call_kwargs["speed"] == 0.9
        assert call_kwargs["response_format"] == "flac"
        assert call_kwargs["instructions"] == "Speak clearly"

    def test_speak_integration_format_with_streaming(
        self,
        mock_service_factory,
        mock_ai_service,
        tmp_path,
    ):
        """Integration test: different formats work with streaming."""
        runner = CliRunner()

        formats = ["mp3", "opus", "aac", "flac", "wav", "pcm"]

        for fmt in formats:
            output_file = tmp_path / f"test.{fmt}"

            mock_result = Mock()
            mock_result.audio_path = output_file
            mock_ai_service.text_to_speech_stream.return_value = mock_result
            mock_service_factory.get_ai_service.return_value = mock_ai_service

            with patch(
                "ei_cli.cli.commands.speak.ServiceFactory",
                return_value=mock_service_factory,
            ):
                result = runner.invoke(
                    speak,
                    [
                        "Test format",
                        "-o", str(output_file),
                        "-f", fmt,
                        "--stream",
                    ],
                )

            assert result.exit_code == 0, f"Format {fmt} failed"
            assert "Speech generated" in result.output

    def test_speak_integration_voices_with_models(
        self,
        mock_service_factory,
        mock_ai_service,
        tmp_path,
    ):
        """Integration test: verify voice/model compatibility."""
        runner = CliRunner()
        output_file = tmp_path / "voice_test.mp3"

        mock_result = Mock()
        mock_result.audio_path = output_file
        mock_ai_service.text_to_speech.return_value = mock_result
        mock_service_factory.get_ai_service.return_value = mock_ai_service

        # Test HD-exclusive voice with tts-1-hd (should work)
        with patch(
            "ei_cli.cli.commands.speak.ServiceFactory",
            return_value=mock_service_factory,
        ):
            result = runner.invoke(
                speak,
                ["Test", "-o", str(output_file), "-v", "marin", "-m", "tts-1-hd"],
            )

        assert result.exit_code == 0
        assert "Speech generated" in result.output

        # Test HD-exclusive voice with tts-1 (should fail)
        with patch(
            "ei_cli.cli.commands.speak.ServiceFactory",
            return_value=mock_service_factory,
        ):
            result = runner.invoke(
                speak,
                ["Test", "-o", str(output_file), "-v", "marin", "-m", "tts-1"],
            )

        assert result.exit_code == 1
        assert "only available with tts-1-hd" in result.output
