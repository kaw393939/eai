"""Comprehensive tests for configuration system.

Tests cover:
- Model validation
- Environment variable loading
- YAML/JSON file loading
- Default values
- Error handling
"""

from pathlib import Path

import pytest
from pydantic import ValidationError

from ei_cli.config import (
    APIConfig,
    Settings,
    TranscriptionConfig,
    TTSConfig,
    WorkflowConfig,
    YouTubeConfig,
    get_settings,
    reload_settings,
    reset_settings,
)


class TestYouTubeConfig:
    """Test YouTube configuration model."""

    def test_default_values(self):
        """Test default configuration values."""
        config = YouTubeConfig()

        assert config.cookies_browser is None
        assert config.cookies_file is None
        assert config.max_fragment_failures == 10
        assert config.retry_attempts == 3
        assert config.timeout_seconds == 300

    def test_custom_values(self):
        """Test setting custom values."""
        config = YouTubeConfig(
            cookies_browser="safari",
            max_fragment_failures=5,
            retry_attempts=5,
        )

        assert config.cookies_browser == "safari"
        assert config.max_fragment_failures == 5
        assert config.retry_attempts == 5

    def test_cookies_file_expansion(self, tmp_path):
        """Test that ~ is expanded in cookies file path."""
        config = YouTubeConfig(cookies_file="~/cookies.txt")

        assert config.cookies_file is not None
        assert "~" not in str(config.cookies_file)
        assert config.cookies_file.is_absolute()

    def test_invalid_browser(self):
        """Test that invalid browser raises error."""
        with pytest.raises(ValidationError) as exc_info:
            YouTubeConfig(cookies_browser="invalid")

        assert "cookies_browser" in str(exc_info.value)

    def test_max_fragment_failures_range(self):
        """Test validation of max_fragment_failures range."""
        # Valid values
        YouTubeConfig(max_fragment_failures=1)
        YouTubeConfig(max_fragment_failures=50)

        # Invalid values
        with pytest.raises(ValidationError):
            YouTubeConfig(max_fragment_failures=0)

        with pytest.raises(ValidationError):
            YouTubeConfig(max_fragment_failures=51)


class TestTranscriptionConfig:
    """Test transcription configuration model."""

    def test_default_values(self):
        """Test default configuration values."""
        config = TranscriptionConfig()

        assert config.auto_chunk is True
        assert config.max_chunk_size_mb == 20
        assert config.chunk_duration_seconds == 600
        assert config.language is None
        assert config.save_intermediate is False

    def test_language_validation(self):
        """Test ISO-639-1 language code validation."""
        # Valid codes
        config = TranscriptionConfig(language="en")
        assert config.language == "en"

        config = TranscriptionConfig(language="ES")
        assert config.language == "es"  # Converted to lowercase

        # Invalid code (must be 2 characters)
        with pytest.raises(ValidationError) as exc_info:
            TranscriptionConfig(language="eng")

        assert "2 characters" in str(exc_info.value)

    def test_chunk_size_range(self):
        """Test validation of chunk size range."""
        # Valid values
        TranscriptionConfig(max_chunk_size_mb=5)
        TranscriptionConfig(max_chunk_size_mb=50)

        # Invalid values
        with pytest.raises(ValidationError):
            TranscriptionConfig(max_chunk_size_mb=4)

        with pytest.raises(ValidationError):
            TranscriptionConfig(max_chunk_size_mb=51)


class TestTTSConfig:
    """Test TTS configuration model."""

    def test_default_values(self):
        """Test default configuration values."""
        config = TTSConfig()

        assert config.voice == "nova"
        assert config.model == "tts-1-hd"
        assert config.speed == 1.0

    def test_all_voices(self):
        """Test all valid voice options."""
        voices = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]

        for voice in voices:
            config = TTSConfig(voice=voice)
            assert config.voice == voice

    def test_invalid_voice(self):
        """Test that invalid voice raises error."""
        with pytest.raises(ValidationError):
            TTSConfig(voice="invalid")

    def test_speed_range(self):
        """Test validation of speed range."""
        # Valid values
        TTSConfig(speed=0.25)
        TTSConfig(speed=4.0)

        # Invalid values
        with pytest.raises(ValidationError):
            TTSConfig(speed=0.24)

        with pytest.raises(ValidationError):
            TTSConfig(speed=4.1)


class TestAPIConfig:
    """Test API configuration model."""

    def test_api_key_defaults_to_empty(self):
        """Test that API key defaults to empty string (validated at usage)."""
        config = APIConfig()
        assert config.openai_api_key.get_secret_value() == ""

    def test_secret_str(self):
        """Test that API key is stored as SecretStr."""
        config = APIConfig(openai_api_key="sk-test-key-12345")

        # SecretStr hides value in repr
        assert "sk-test" not in repr(config)

        # But can be retrieved
        assert config.openai_api_key.get_secret_value() == "sk-test-key-12345"

    def test_default_values(self):
        """Test default configuration values."""
        config = APIConfig(openai_api_key="sk-test")

        assert config.openai_base_url is None
        assert config.timeout_seconds == 600
        assert config.max_retries == 3

    def test_custom_base_url(self):
        """Test custom API base URL."""
        config = APIConfig(
            openai_api_key="sk-test",
            openai_base_url="https://custom.api.com",
        )

        assert config.openai_base_url == "https://custom.api.com"


class TestWorkflowConfig:
    """Test workflow configuration model."""

    def test_default_values(self):
        """Test default configuration values."""
        config = WorkflowConfig()

        assert config.output_dir == Path.cwd() / "workflow_outputs"
        assert config.save_state is True
        assert config.parallel_execution is False
        assert config.fail_fast is True

    def test_output_dir_expansion(self):
        """Test that ~ is expanded in output directory."""
        config = WorkflowConfig(output_dir="~/outputs")

        assert "~" not in str(config.output_dir)
        assert config.output_dir.is_absolute()


class TestSettings:
    """Test main Settings class."""

    def setup_method(self):
        """Reset settings before each test."""
        reset_settings()

    def test_env_variable_loading(self, monkeypatch):
        """Test loading from environment variables."""
        monkeypatch.setenv("API__OPENAI_API_KEY", "sk-test-env-key")
        monkeypatch.setenv("YOUTUBE__COOKIES_BROWSER", "safari")
        monkeypatch.setenv("TTS__VOICE", "echo")
        monkeypatch.setenv("TRANSCRIPTION__LANGUAGE", "es")

        settings = Settings()

        assert settings.api.openai_api_key.get_secret_value() == "sk-test-env-key"
        assert settings.youtube.cookies_browser == "safari"
        assert settings.tts.voice == "echo"
        assert settings.transcription.language == "es"

    def test_nested_env_variables(self, monkeypatch):
        """Test nested environment variable syntax."""
        monkeypatch.setenv("API__OPENAI_API_KEY", "sk-test")
        monkeypatch.setenv("YOUTUBE__MAX_FRAGMENT_FAILURES", "5")
        monkeypatch.setenv("TTS__SPEED", "1.5")

        settings = Settings()

        assert settings.youtube.max_fragment_failures == 5
        assert settings.tts.speed == 1.5

    def test_yaml_loading(self, tmp_path, monkeypatch):
        """Test loading configuration from YAML file."""
        monkeypatch.setenv("API__OPENAI_API_KEY", "sk-test")

        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
api:
  openai_api_key: sk-yaml-key
youtube:
  cookies_browser: safari
  max_fragment_failures: 5
tts:
  voice: echo
  model: tts-1
transcription:
  language: en
  auto_chunk: false
        """)

        settings = Settings.from_yaml(config_file)

        assert settings.api.openai_api_key.get_secret_value() == "sk-yaml-key"
        assert settings.youtube.cookies_browser == "safari"
        assert settings.youtube.max_fragment_failures == 5
        assert settings.tts.voice == "echo"
        assert settings.tts.model == "tts-1"
        assert settings.transcription.language == "en"
        assert settings.transcription.auto_chunk is False

    def test_json_loading(self, tmp_path, monkeypatch):
        """Test loading configuration from JSON file."""
        monkeypatch.setenv("API__OPENAI_API_KEY", "sk-test")

        config_file = tmp_path / "config.json"
        config_file.write_text("""{
  "api": {
    "openai_api_key": "sk-json-key"
  },
  "youtube": {
    "cookies_browser": "chrome"
  },
  "tts": {
    "voice": "fable"
  }
}
        """)

        settings = Settings.from_json(config_file)

        assert settings.api.openai_api_key.get_secret_value() == "sk-json-key"
        assert settings.youtube.cookies_browser == "chrome"
        assert settings.tts.voice == "fable"

    def test_missing_config_file(self):
        """Test error when config file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            Settings.from_yaml(Path("nonexistent.yaml"))

    def test_invalid_yaml(self, tmp_path, monkeypatch):
        """Test error with invalid YAML."""
        monkeypatch.setenv("API__OPENAI_API_KEY", "sk-test")

        config_file = tmp_path / "bad.yaml"
        config_file.write_text("{ invalid yaml [[[")

        with pytest.raises(ValueError) as exc_info:
            Settings.from_yaml(config_file)

        assert "Failed to load config" in str(exc_info.value)

    def test_to_yaml(self, tmp_path, monkeypatch):
        """Test saving settings to YAML."""
        monkeypatch.setenv("API__OPENAI_API_KEY", "sk-test")

        settings = Settings()
        output_file = tmp_path / "output.yaml"

        settings.to_yaml(output_file)

        assert output_file.exists()
        content = output_file.read_text()
        assert "YOUR_API_KEY_HERE" in content  # API key should be redacted
        assert "nova" in content  # Default voice

    def test_validate_api_key(self, monkeypatch):
        """Test API key validation."""
        # Valid key
        monkeypatch.setenv("API__OPENAI_API_KEY", "sk-proj-12345678901234567890")
        settings = Settings()
        assert settings.validate_api_key() is True

        # Invalid key (too short)
        monkeypatch.setenv("API__OPENAI_API_KEY", "sk-short")
        settings = Settings()
        assert settings.validate_api_key() is False

        # Invalid key (wrong prefix)
        monkeypatch.setenv("API__OPENAI_API_KEY", "invalid-12345678901234567890")
        settings = Settings()
        assert settings.validate_api_key() is False

    def test_default_factory(self, monkeypatch):
        """Test that default factories create independent instances."""
        monkeypatch.setenv("API__OPENAI_API_KEY", "sk-test")

        settings1 = Settings()
        settings2 = Settings()

        # Each should have its own config instances
        assert settings1.youtube is not settings2.youtube
        assert settings1.tts is not settings2.tts


class TestSettingsManager:
    """Test global settings manager functions."""

    def setup_method(self):
        """Reset settings before each test."""
        reset_settings()

    def test_get_settings_singleton(self, monkeypatch):
        """Test that get_settings returns singleton."""
        monkeypatch.setenv("API__OPENAI_API_KEY", "sk-test")

        settings1 = get_settings()
        settings2 = get_settings()

        assert settings1 is settings2  # Same instance

    def test_reload_settings(self, tmp_path, monkeypatch):
        """Test reloading settings with new config."""
        monkeypatch.setenv("API__OPENAI_API_KEY", "sk-test")

        # Initial settings
        settings1 = get_settings()
        assert settings1.tts.voice == "nova"  # Default

        # Create custom config
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
api:
  openai_api_key: sk-test
tts:
  voice: echo
        """)

        # Reload
        settings2 = reload_settings(config_file)
        assert settings2.tts.voice == "echo"

        # get_settings should return new instance
        settings3 = get_settings()
        assert settings3.tts.voice == "echo"
        assert settings3 is settings2

    def test_reload_with_invalid_extension(self):
        """Test error with unsupported file extension."""
        with pytest.raises(ValueError) as exc_info:
            reload_settings(Path("config.txt"))

        assert "Unsupported config file format" in str(exc_info.value)

    def test_reset_settings(self, monkeypatch):
        """Test resetting global settings."""
        monkeypatch.setenv("API__OPENAI_API_KEY", "sk-test")

        # Get initial settings
        settings1 = get_settings()

        # Reset
        reset_settings()

        # Next get_settings should create new instance
        settings2 = get_settings()
        assert settings2 is not settings1


class TestConfigIntegration:
    """Integration tests for configuration system."""

    def test_env_file_auto_loading(self, tmp_path, monkeypatch):
        """Test that .env file is automatically loaded."""
        # Create .env file
        env_file = tmp_path / ".env"
        env_file.write_text("""
API__OPENAI_API_KEY=sk-dotenv-key
YOUTUBE__COOKIES_BROWSER=safari
TTS__VOICE=echo
        """)

        # Change to that directory
        monkeypatch.chdir(tmp_path)

        # Settings should auto-load .env
        reset_settings()
        settings = get_settings()

        assert settings.api.openai_api_key.get_secret_value() == "sk-dotenv-key"
        assert settings.youtube.cookies_browser == "safari"
        assert settings.tts.voice == "echo"

    def test_env_vars_override_env_file(self, tmp_path, monkeypatch):
        """Test that environment variables override .env file."""
        # Create .env file
        env_file = tmp_path / ".env"
        env_file.write_text("""
API__OPENAI_API_KEY=sk-dotenv-key
TTS__VOICE=echo
        """)

        monkeypatch.chdir(tmp_path)

        # Override with environment variable
        monkeypatch.setenv("TTS__VOICE", "nova")

        reset_settings()
        settings = get_settings()

        # Env var should take precedence
        assert settings.tts.voice == "nova"

    def test_complete_workflow_config(self, tmp_path, monkeypatch):
        """Test complete configuration for typical workflow."""
        monkeypatch.setenv("API__OPENAI_API_KEY", "sk-test-key")

        config_file = tmp_path / "workflow.yaml"
        config_file.write_text("""
api:
  openai_api_key: sk-test-key
  timeout_seconds: 300

youtube:
  cookies_browser: safari
  max_fragment_failures: 5

transcription:
  auto_chunk: true
  max_chunk_size_mb: 15
  language: en

tts:
  voice: nova
  model: tts-1-hd
  speed: 1.0

workflow:
  output_dir: ./outputs
  save_state: true
  fail_fast: true
        """)

        settings = Settings.from_yaml(config_file)

        # Verify all settings
        assert settings.api.openai_api_key.get_secret_value() == "sk-test-key"
        assert settings.youtube.cookies_browser == "safari"
        assert settings.transcription.auto_chunk is True
        assert settings.transcription.language == "en"
        assert settings.tts.voice == "nova"
        assert settings.workflow.save_state is True
