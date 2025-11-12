"""Configuration management for EverydayAI CLI."""

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class YouTubeConfig(BaseModel):
    """YouTube video download configuration.
    
    Attributes:
        cookies_browser: Browser to extract cookies from (chrome, firefox, safari, edge)
        cookies_file: Path to Netscape format cookies file
        max_fragment_failures: Max consecutive fragment failures before aborting
        retry_attempts: Number of download retry attempts
        timeout_seconds: Download timeout in seconds
    """

    cookies_browser: Literal["chrome", "firefox", "safari", "edge"] | None = Field(
        default=None,
        description="Browser to extract YouTube cookies from",
    )
    cookies_file: Path | None = Field(
        default=None,
        description="Path to cookies file in Netscape format",
    )
    max_fragment_failures: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Max consecutive fragment failures before aborting download",
    )
    retry_attempts: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Number of retry attempts for failed downloads",
    )
    timeout_seconds: int = Field(
        default=300,
        ge=30,
        description="Download timeout in seconds",
    )

    @field_validator("cookies_file", mode="before")
    @classmethod
    def expand_cookies_path(cls, v):
        """Expand ~ and environment variables in cookies file path."""
        if v is None:
            return v
        return Path(v).expanduser()


class TranscriptionConfig(BaseModel):
    """Audio transcription configuration.
    
    Attributes:
        auto_chunk: Automatically chunk large audio files
        max_chunk_size_mb: Maximum chunk size in megabytes
        chunk_duration_seconds: Chunk duration in seconds (if time-based chunking)
        language: ISO-639-1 language code for transcription
        save_intermediate: Keep intermediate chunk files
    """

    auto_chunk: bool = Field(
        default=True,
        description="Automatically chunk large audio files for transcription",
    )
    max_chunk_size_mb: int = Field(
        default=20,
        ge=5,
        le=50,
        description="Maximum audio chunk size in MB (API limit is 25MB with overhead)",
    )
    chunk_duration_seconds: int = Field(
        default=600,
        ge=60,
        description="Target chunk duration in seconds (10 minutes default)",
    )
    language: str | None = Field(
        default=None,
        description="ISO-639-1 language code (e.g., 'en', 'es', 'fr')",
    )
    save_intermediate: bool = Field(
        default=False,
        description="Keep intermediate chunk files after transcription",
    )

    @field_validator("language")
    @classmethod
    def validate_language_code(cls, v):
        """Validate ISO-639-1 language code format."""
        if v is not None and len(v) != 2:
            raise ValueError("Language code must be 2 characters (ISO-639-1)")
        return v.lower() if v else v


class TTSConfig(BaseModel):
    """Text-to-speech configuration.
    
    Attributes:
        voice: OpenAI TTS voice name
        model: OpenAI TTS model (tts-1 or tts-1-hd)
        speed: Playback speed multiplier
    """

    voice: Literal["alloy", "echo", "fable", "onyx", "nova", "shimmer"] = Field(
        default="nova",
        description="OpenAI TTS voice (nova recommended for professional content)",
    )
    model: Literal["tts-1", "tts-1-hd"] = Field(
        default="tts-1-hd",
        description="TTS model: tts-1 (faster) or tts-1-hd (higher quality)",
    )
    speed: float = Field(
        default=1.0,
        ge=0.25,
        le=4.0,
        description="Playback speed multiplier (0.25 to 4.0)",
    )


class APIConfig(BaseModel):
    """API configuration for various AI services."""

    # Required API keys
    openai_api_key: SecretStr = Field(
        default=SecretStr(""),  # Empty default, validated at usage
        description="OpenAI API key (required)",
    )

    # Optional API keys for other services
    browseruse_api_key: SecretStr | None = Field(
        default=None,
        description="BrowserUse API key (optional)",
    )
    anthropic_api_key: SecretStr | None = Field(
        default=None,
        description="Anthropic/Claude API key (optional)",
    )
    google_api_key: SecretStr | None = Field(
        default=None,
        description="Google AI API key (optional)",
    )
    elevenlabs_api_key: SecretStr | None = Field(
        default=None,
        description="ElevenLabs TTS API key (optional)",
    )

    # OpenAI specific settings
    openai_base_url: str | None = Field(
        default=None,
        description="Custom OpenAI API base URL (for proxies)",
    )
    timeout_seconds: int = Field(
        default=600,
        ge=30,
        description="API request timeout in seconds",
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum retry attempts for failed API calls",
    )


class WorkflowConfig(BaseModel):
    """Workflow execution configuration.
    
    Attributes:
        output_dir: Directory for workflow outputs
        save_state: Enable workflow state persistence
        parallel_execution: Enable parallel execution of independent tasks
        fail_fast: Stop workflow on first error (vs continue with warnings)
    """

    output_dir: Path = Field(
        default_factory=lambda: Path.cwd() / "workflow_outputs",
        description="Directory for workflow output files",
    )
    save_state: bool = Field(
        default=True,
        description="Save workflow state for resumability",
    )
    parallel_execution: bool = Field(
        default=False,
        description="Enable parallel execution of independent tasks (experimental)",
    )
    fail_fast: bool = Field(
        default=True,
        description="Stop workflow on first error (vs continue with warnings)",
    )

    @field_validator("output_dir", mode="before")
    @classmethod
    def expand_output_dir(cls, v):
        """Expand ~ and environment variables in output directory path."""
        if isinstance(v, str):
            v = Path(v)
        return v.expanduser().resolve()


class Settings(BaseSettings):
    """Main application settings.
    
    Settings are loaded from:
    1. .env file (automatically discovered)
    2. Environment variables (take precedence)
    3. config.yaml or config.json file (if provided)
    
    Environment variables use double underscore for nesting:
        API__OPENAI_API_KEY=sk-...          -> settings.api.openai_api_key
        YOUTUBE__COOKIES_BROWSER=safari     -> settings.youtube.cookies_browser
        TTS__VOICE=echo                     -> settings.tts.voice
    """

    model_config = SettingsConfigDict(
        # Automatically load .env file from current directory or parent dirs
        env_file=".env",
        env_file_encoding="utf-8",

        # Support nested config via double underscore
        # Example: YOUTUBE__COOKIES_BROWSER=safari
        # Example: API__OPENAI_API_KEY=sk-...
        env_nested_delimiter="__",

        # Case insensitive environment variables
        case_sensitive=False,

        # Ignore extra fields in config files
        extra="ignore",

        # Look for .env in parent directories too
        env_prefix="",
    )

    # API Configuration (required)
    api: APIConfig = APIConfig()

    # Feature Configuration (optional with defaults)
    youtube: YouTubeConfig = YouTubeConfig()
    transcription: TranscriptionConfig = TranscriptionConfig()
    tts: TTSConfig = TTSConfig()
    workflow: WorkflowConfig = WorkflowConfig()

    @classmethod
    def from_yaml(cls, config_file: Path) -> "Settings":
        """Load settings from YAML file.
        
        Args:
            config_file: Path to YAML configuration file
            
        Returns:
            Settings instance with loaded configuration
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If YAML is invalid
        """
        if not config_file.exists():
            raise FileNotFoundError(f"Config file not found: {config_file}")

        try:
            import yaml
            with open(config_file) as f:
                config_data = yaml.safe_load(f)
            return cls(**config_data)
        except Exception as e:
            raise ValueError(f"Failed to load config from {config_file}: {e}")

    @classmethod
    def from_json(cls, config_file: Path) -> "Settings":
        """Load settings from JSON file.
        
        Args:
            config_file: Path to JSON configuration file
            
        Returns:
            Settings instance with loaded configuration
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If JSON is invalid
        """
        if not config_file.exists():
            raise FileNotFoundError(f"Config file not found: {config_file}")

        try:
            import json
            with open(config_file) as f:
                config_data = json.load(f)
            return cls(**config_data)
        except Exception as e:
            raise ValueError(f"Failed to load config from {config_file}: {e}")

    def to_yaml(self, output_file: Path):
        """Save settings to YAML file.
        
        Args:
            output_file: Path to save YAML configuration
        """

        # Convert to dict, handling SecretStr
        config_dict = self.model_dump(mode="json", exclude={"api": {"openai_api_key"}})
        config_dict["api"]["openai_api_key"] = "YOUR_API_KEY_HERE"

        with open(output_file, "w") as f:
            yaml.safe_dump(config_dict, f, default_flow_style=False, sort_keys=False)

    def validate_api_key(self) -> bool:
        """Validate that API key is set and has correct format.
        
        Returns:
            True if API key appears valid
        """
        key = self.api.openai_api_key.get_secret_value()
        return key.startswith("sk-") and len(key) > 20
