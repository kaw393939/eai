"""Enhanced error handling with contextual suggestions.

This module provides user-friendly error messages with actionable next steps.
"""

import sys

import click

from ei_cli.services.exceptions import (
    APIKeyMissingError,
    AudioConversionError,
    InvalidAudioError,
    TranscriptionError,
    TTSError,
    VideoDownloadError,
)


def handle_api_key_error(error: APIKeyMissingError) -> None:
    """Show helpful message for missing API key."""
    click.secho("\n❌ API Key Missing", fg="red", bold=True)
    click.echo(f"\n{error}")
    click.echo("\n📝 You can configure your API key in 3 ways:")
    click.echo("\n1. Environment variable:")
    click.echo("   export API__OPENAI_API_KEY='your-key-here'")
    click.echo("\n2. .env file (recommended):")
    click.echo("   echo 'API__OPENAI_API_KEY=your-key-here' >> .env")
    click.echo("\n3. Config file:")
    click.echo("   ei-cli --config config.yaml <command>")
    click.echo("\n💡 Get your API key at: https://platform.openai.com/api-keys")
    sys.exit(1)


def handle_video_download_error(error: VideoDownloadError) -> None:
    """Show helpful message for video download failures."""
    click.secho("\n❌ Video Download Failed", fg="red", bold=True)
    click.echo(f"\n{error}")

    error_msg = str(error).lower()

    # Provide specific suggestions based on error type
    if "age-restricted" in error_msg or "age limit" in error_msg:
        click.echo("\n💡 Suggestions:")
        click.echo("   • Use --cookies-from-browser to authenticate:")
        click.echo("     ei-cli transcribe-video <url> --cookies-from-browser chrome")
        click.echo("   • Supported browsers: chrome, firefox, safari, edge")
    elif "login" in error_msg or "requires" in error_msg or "sign in" in error_msg:
        click.echo("\n💡 Suggestions:")
        click.echo("   • Use --cookies-from-browser to authenticate:")
        click.echo("     ei-cli transcribe-video <url> --cookies-from-browser chrome")
        click.echo("   • Make sure you're logged into the browser")
    elif "private" in error_msg or "unavailable" in error_msg:
        click.echo("\n💡 Suggestions:")
        click.echo("   • Verify the video URL is correct")
        click.echo("   • Check if the video is private or deleted")
        click.echo("   • If you have access, use --cookies-from-browser chrome")
    elif "copyright" in error_msg or "blocked" in error_msg:
        click.echo("\n💡 This video cannot be downloaded:")
        click.echo("   • The content is blocked or removed due to copyright")
        click.echo("   • Try a different video")
    elif "region" in error_msg or "not available" in error_msg:
        click.echo("\n💡 Suggestions:")
        click.echo("   • Video may not be available in your region")
        click.echo("   • Try using a VPN or different video")
    else:
        click.echo("\n💡 Suggestions:")
        click.echo("   • Verify the video URL is correct")
        click.echo("   • Try using --cookies-from-browser if authentication needed")
        click.echo("   • Check your internet connection")

    sys.exit(1)


def handle_transcription_error(error: TranscriptionError) -> None:
    """Show helpful message for transcription failures."""
    click.secho("\n❌ Transcription Failed", fg="red", bold=True)
    click.echo(f"\n{error}")

    error_msg = str(error).lower()

    if "api key" in error_msg:
        click.echo("\n💡 Check your OpenAI API key configuration")
        click.echo("   See 'ei-cli --help' for configuration options")
    elif "rate limit" in error_msg or "quota" in error_msg:
        click.echo("\n💡 Rate limit reached:")
        click.echo("   • Wait a few minutes and try again")
        click.echo("   • Check your OpenAI usage at: https://platform.openai.com/usage")
        click.echo("   • Consider upgrading your OpenAI plan")
    elif "invalid" in error_msg or "format" in error_msg:
        click.echo("\n💡 Audio file may be invalid:")
        click.echo("   • Ensure the file is a valid audio/video format")
        click.echo("   • Try converting to MP3 or WAV first")
        click.echo("   • Maximum file size is 25 MB for Whisper API")
    elif "timeout" in error_msg:
        click.echo("\n💡 Request timed out:")
        click.echo("   • Check your internet connection")
        click.echo("   • Try again in a few moments")
        click.echo("   • For large files, ensure stable connection")
    else:
        click.echo("\n💡 Suggestions:")
        click.echo("   • Verify the audio file is valid")
        click.echo("   • Check your OpenAI API key and quota")
        click.echo("   • Try with a smaller audio file")

    sys.exit(1)


def handle_tts_error(error: TTSError) -> None:
    """Show helpful message for TTS failures."""
    click.secho("\n❌ Text-to-Speech Failed", fg="red", bold=True)
    click.echo(f"\n{error}")

    error_msg = str(error).lower()

    if "api key" in error_msg:
        click.echo("\n💡 Check your OpenAI API key configuration")
    elif "rate limit" in error_msg or "quota" in error_msg:
        click.echo("\n💡 Rate limit reached:")
        click.echo("   • Wait a few minutes and try again")
        click.echo("   • Check your OpenAI usage")
    elif "voice" in error_msg:
        click.echo("\n💡 Available voices:")
        click.echo("   • alloy, echo, fable, onyx, nova, shimmer")
        click.echo("   • Use --voice <name> to select a different voice")
    elif "text" in error_msg or "length" in error_msg:
        click.echo("\n💡 Text may be too long:")
        click.echo("   • Maximum 4096 characters per request")
        click.echo("   • Try breaking text into smaller chunks")
    else:
        click.echo("\n💡 Suggestions:")
        click.echo("   • Check your OpenAI API key")
        click.echo("   • Verify the input text is valid")
        click.echo("   • Try with shorter text")

    sys.exit(1)


def handle_audio_conversion_error(error: AudioConversionError) -> None:
    """Show helpful message for audio conversion failures."""
    click.secho("\n❌ Audio Conversion Failed", fg="red", bold=True)
    click.echo(f"\n{error}")

    click.echo("\n💡 Requirements:")
    click.echo("   • FFmpeg must be installed on your system")
    click.echo("\n   Install FFmpeg:")
    click.echo("   • macOS: brew install ffmpeg")
    click.echo("   • Ubuntu/Debian: sudo apt install ffmpeg")
    click.echo("   • Windows: Download from https://ffmpeg.org/download.html")
    click.echo("\n   • Verify installation: ffmpeg -version")

    sys.exit(1)


def handle_invalid_audio_error(error: InvalidAudioError) -> None:
    """Show helpful message for invalid audio files."""
    click.secho("\n❌ Invalid Audio File", fg="red", bold=True)
    click.echo(f"\n{error}")

    click.echo("\n💡 Supported formats:")
    click.echo("   • Audio: MP3, WAV, M4A, FLAC, OGG, AAC")
    click.echo("   • Video: MP4, MKV, AVI, MOV, WEBM")
    click.echo("\n   Suggestions:")
    click.echo("   • Verify the file exists and is readable")
    click.echo("   • Check the file format is supported")
    click.echo("   • Try converting to MP3 or WAV first")
    click.echo("   • Ensure the file is not corrupted")

    sys.exit(1)


def handle_general_error(error: Exception) -> None:
    """Show helpful message for unexpected errors."""
    click.secho("\n❌ Unexpected Error", fg="red", bold=True)
    click.echo(f"\n{error}")

    click.echo("\n💡 Troubleshooting:")
    click.echo("   • Check the command syntax: ei-cli --help")
    click.echo("   • Verify all required arguments are provided")
    click.echo("   • Check file paths and permissions")
    click.echo("   • Report issues at: https://github.com/yourusername/ei-cli/issues")

    sys.exit(1)


def handle_error(error: Exception) -> None:
    """Central error handler that dispatches to specific handlers.

    Args:
        error: The exception to handle.
    """
    if isinstance(error, APIKeyMissingError):
        handle_api_key_error(error)
    elif isinstance(error, VideoDownloadError):
        handle_video_download_error(error)
    elif isinstance(error, TranscriptionError):
        handle_transcription_error(error)
    elif isinstance(error, TTSError):
        handle_tts_error(error)
    elif isinstance(error, AudioConversionError):
        handle_audio_conversion_error(error)
    elif isinstance(error, InvalidAudioError):
        handle_invalid_audio_error(error)
    else:
        handle_general_error(error)
