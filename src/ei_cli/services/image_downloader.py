"""
Image downloader utility for handling image URLs and base64 data.

Provides functionality to download images from URLs and decode base64 data,
with progress tracking and format detection.
"""

import base64
from pathlib import Path
from urllib.parse import urlparse

import httpx
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)

from ei_cli.core.errors import AIServiceError


class ImageDownloader:
    """
    Utility for downloading images from URLs or decoding base64 data.
    
    Supports:
    - HTTP/HTTPS URL downloads with progress tracking
    - Base64 data decoding
    - Automatic format detection
    - Multiple image formats (PNG, JPEG, WebP)
    """

    SUPPORTED_FORMATS = {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/webp": ".webp",
    }

    def __init__(self, timeout: int = 30):
        """
        Initialize image downloader.
        
        Args:
            timeout: Request timeout in seconds (default: 30)
        """
        self.timeout = timeout

    def is_url(self, source: str) -> bool:
        """
        Check if source is a URL.
        
        Args:
            source: String to check
            
        Returns:
            True if source is an HTTP/HTTPS URL
        """
        try:
            result = urlparse(source)
            return result.scheme in ("http", "https")
        except Exception:
            return False

    def is_base64(self, source: str) -> bool:
        """
        Check if source is base64-encoded data.
        
        Args:
            source: String to check
            
        Returns:
            True if source appears to be base64 data
        """
        # Check for data URI format
        if source.startswith("data:image/"):
            return True

        # Check if it looks like raw base64 (at least 100 chars, valid base64)
        if len(source) > 100:
            try:
                base64.b64decode(source[:100], validate=True)
                return True
            except Exception:
                pass

        return False

    def detect_format(self, data: bytes) -> str:
        """
        Detect image format from binary data.
        
        Args:
            data: Image binary data
            
        Returns:
            File extension (e.g., '.png', '.jpg')
            
        Raises:
            AIServiceError: If format cannot be detected
        """
        # Check PNG signature
        if data.startswith(b"\x89PNG\r\n\x1a\n"):
            return ".png"

        # Check JPEG signature
        if data.startswith(b"\xff\xd8\xff"):
            return ".jpg"

        # Check WebP signature
        if data[0:4] == b"RIFF" and data[8:12] == b"WEBP":
            return ".webp"

        # Check GIF signature
        if data.startswith(b"GIF87a") or data.startswith(b"GIF89a"):
            return ".gif"

        raise AIServiceError(
            message="Unable to detect image format from data",
            code="UNSUPPORTED_FORMAT",
        )

    def download_from_url(
        self,
        url: str,
        output_path: Path,
        *,
        show_progress: bool = True,
    ) -> Path:
        """
        Download image from URL.
        
        Args:
            url: Image URL
            output_path: Path to save image
            show_progress: Whether to show progress bar
            
        Returns:
            Path to saved image
            
        Raises:
            AIServiceError: If download fails
        """
        try:
            with httpx.Client(timeout=self.timeout) as client:
                # Make request with streaming
                with client.stream("GET", url) as response:
                    response.raise_for_status()

                    # Get content length for progress bar
                    total = int(response.headers.get("content-length", 0))

                    # Determine file extension from content type or URL
                    content_type = response.headers.get("content-type", "")
                    ext = self.SUPPORTED_FORMATS.get(content_type)

                    if not ext:
                        # Try to get extension from URL
                        url_path = urlparse(url).path
                        ext = Path(url_path).suffix or ".jpg"

                    # Ensure output path has correct extension
                    if not output_path.suffix:
                        output_path = output_path.with_suffix(ext)

                    # Create parent directory if needed
                    output_path.parent.mkdir(parents=True, exist_ok=True)

                    # Download with progress
                    if show_progress and total > 0:
                        with Progress(
                            TextColumn("[bold blue]{task.description}"),
                            BarColumn(),
                            DownloadColumn(),
                            TransferSpeedColumn(),
                            TimeRemainingColumn(),
                        ) as progress:
                            task = progress.add_task(
                                "Downloading...",
                                total=total,
                            )

                            with open(output_path, "wb") as f:
                                for chunk in response.iter_bytes(chunk_size=8192):
                                    f.write(chunk)
                                    progress.update(task, advance=len(chunk))
                    else:
                        # Download without progress
                        with open(output_path, "wb") as f:
                            for chunk in response.iter_bytes(chunk_size=8192):
                                f.write(chunk)

                    return output_path

        except httpx.HTTPError as e:
            raise AIServiceError(
                message=f"Failed to download image from URL: {e}",
                code="DOWNLOAD_ERROR",
            ) from e
        except Exception as e:
            raise AIServiceError(
                message=f"Unexpected error downloading image: {e}",
                code="DOWNLOAD_ERROR",
            ) from e

    def decode_base64(
        self,
        data: str,
        output_path: Path,
    ) -> Path:
        """
        Decode base64 image data and save to file.
        
        Args:
            data: Base64-encoded image data (with or without data URI prefix)
            output_path: Path to save image
            
        Returns:
            Path to saved image
            
        Raises:
            AIServiceError: If decoding fails
        """
        try:
            # Handle data URI format: data:image/png;base64,<data>
            if data.startswith("data:"):
                # Extract the base64 data after the comma
                if "," in data:
                    data = data.split(",", 1)[1]

            # Decode base64 data
            image_bytes = base64.b64decode(data)

            # Detect format if extension not provided
            if not output_path.suffix:
                ext = self.detect_format(image_bytes)
                output_path = output_path.with_suffix(ext)

            # Create parent directory if needed
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Save image
            with open(output_path, "wb") as f:
                f.write(image_bytes)

            return output_path

        except Exception as e:
            raise AIServiceError(
                message=f"Failed to decode base64 image: {e}",
                code="DECODE_ERROR",
            ) from e

    def save_image(
        self,
        source: str,
        output_path: Path,
        *,
        show_progress: bool = True,
    ) -> Path:
        """
        Save image from URL or base64 data.
        
        Automatically detects whether source is a URL or base64 data
        and uses the appropriate method.
        
        Args:
            source: Image URL or base64 data
            output_path: Path to save image
            show_progress: Whether to show progress for downloads
            
        Returns:
            Path to saved image
            
        Raises:
            AIServiceError: If saving fails
        """
        if self.is_url(source):
            return self.download_from_url(
                source,
                output_path,
                show_progress=show_progress,
            )
        if self.is_base64(source):
            return self.decode_base64(source, output_path)
        raise AIServiceError(
            message="Source is neither a valid URL nor base64 data",
            code="INVALID_SOURCE",
        )
