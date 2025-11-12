"""Service-specific exceptions for EI-CLI.

These exceptions are used by various services and provide
specific error types for different failure scenarios.
"""

from ei_cli.core.errors import VibeError


class APIKeyMissingError(VibeError):
    """Raised when API key is missing."""

    def __init__(self, message: str = "API key not configured") -> None:
        """Initialize APIKeyMissingError."""
        super().__init__(
            message=message,
            code="MISSING_API_KEY",
            recoverable=True,
            suggestion=(
                "Set API key: export API__OPENAI_API_KEY='your-key' "
                "or add to config file"
            ),
        )


class TranscriptionError(VibeError):
    """Raised when transcription fails."""

    def __init__(
        self,
        message: str = "Transcription failed",
        context: dict | None = None,
    ) -> None:
        """Initialize TranscriptionError."""
        super().__init__(
            message=message,
            code="TRANSCRIPTION_FAILED",
            recoverable=True,
            context=context or {},
            suggestion="Check audio file format and API key",
        )


class AudioConversionError(VibeError):
    """Raised when audio conversion fails."""

    def __init__(
        self,
        message: str = "Audio conversion failed",
        context: dict | None = None,
    ) -> None:
        """Initialize AudioConversionError."""
        super().__init__(
            message=message,
            code="AUDIO_CONVERSION_FAILED",
            recoverable=True,
            context=context or {},
            suggestion="Check FFmpeg installation and audio file integrity",
        )


class InvalidAudioError(VibeError):
    """Raised when audio file is invalid."""

    def __init__(
        self,
        message: str = "Invalid audio file",
        context: dict | None = None,
    ) -> None:
        """Initialize InvalidAudioError."""
        super().__init__(
            message=message,
            code="INVALID_AUDIO",
            recoverable=True,
            context=context or {},
            suggestion="Check audio file format (supported: mp3, wav, m4a, mp4)",
        )


class VideoDownloadError(VibeError):
    """Raised when video download fails."""

    def __init__(
        self,
        message: str = "Video download failed",
        context: dict | None = None,
    ) -> None:
        """Initialize VideoDownloadError."""
        super().__init__(
            message=message,
            code="VIDEO_DOWNLOAD_FAILED",
            recoverable=True,
            context=context or {},
            suggestion=(
                "Check URL, internet connection, and yt-dlp installation. "
                "For age-restricted videos, use --cookies-from-browser"
            ),
        )


class TTSError(VibeError):
    """Raised when text-to-speech fails."""

    def __init__(
        self,
        message: str = "Text-to-speech failed",
        context: dict | None = None,
    ) -> None:
        """Initialize TTSError."""
        super().__init__(
            message=message,
            code="TTS_FAILED",
            recoverable=True,
            context=context or {},
            suggestion="Check API key and text content",
        )


class ImageProcessingError(VibeError):
    """Raised when image processing fails."""

    def __init__(
        self,
        message: str = "Image processing failed",
        context: dict | None = None,
    ) -> None:
        """Initialize ImageProcessingError."""
        super().__init__(
            message=message,
            code="IMAGE_PROCESSING_FAILED",
            recoverable=True,
            context=context or {},
            suggestion="Check image file format and integrity",
        )


class SearchError(VibeError):
    """Raised when search fails."""

    def __init__(
        self,
        message: str = "Search failed",
        context: dict | None = None,
    ) -> None:
        """Initialize SearchError."""
        super().__init__(
            message=message,
            code="SEARCH_FAILED",
            recoverable=True,
            context=context or {},
            suggestion="Check search query and API configuration",
        )
