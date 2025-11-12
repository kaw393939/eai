"""Global settings manager for EverydayAI CLI.

Provides singleton access to application settings.
"""

from pathlib import Path

from ei_cli.config.models import Settings

# Global settings instance
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get or create global settings instance.
    
    Settings are loaded from:
    1. .env file (auto-discovered)
    2. Environment variables
    3. Default values
    
    Returns:
        Global Settings instance
        
    Example:
        >>> from ei_cli.config import get_settings
        >>> settings = get_settings()
        >>> api_key = settings.api.openai_api_key.get_secret_value()
    """
    global _settings

    if _settings is None:
        _settings = Settings()

    return _settings


def reload_settings(config_file: Path | None = None) -> Settings:
    """Reload settings, optionally from a config file.
    
    Useful for:
    - Loading custom configuration files
    - Reloading after environment changes
    - Testing with different configurations
    
    Args:
        config_file: Optional path to YAML or JSON config file
        
    Returns:
        Newly loaded Settings instance
        
    Example:
        >>> from ei_cli.config import reload_settings
        >>> settings = reload_settings(Path("custom_config.yaml"))
    """
    global _settings

    if config_file is not None:
        if config_file.suffix in [".yaml", ".yml"]:
            _settings = Settings.from_yaml(config_file)
        elif config_file.suffix == ".json":
            _settings = Settings.from_json(config_file)
        else:
            raise ValueError(
                f"Unsupported config file format: {config_file.suffix}. "
                "Use .yaml, .yml, or .json",
            )
    else:
        _settings = Settings()

    return _settings


def reset_settings():
    """Reset global settings (mainly for testing).
    
    Example:
        >>> from ei_cli.config import reset_settings
        >>> reset_settings()  # Force reload on next get_settings()
    """
    global _settings
    _settings = None
