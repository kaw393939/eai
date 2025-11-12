"""
Image service for centralized image processing operations.

This service provides a unified interface for image manipulation including:
- Cropping to remove whitespace/padding
- Background removal
- Image optimization and compression

All operations include validation, error handling, and cleanup.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import numpy as np
    from PIL import Image

    DEPENDENCIES_AVAILABLE = True
except ImportError:  # pragma: no cover
    DEPENDENCIES_AVAILABLE = False

from ei_cli.services.base import Service, ServiceError


@dataclass
class CropResult:
    """Result from image cropping operation."""

    input_path: str
    output_path: str
    original_size: tuple[int, int]
    cropped_size: tuple[int, int]
    crop_box: tuple[int, int, int, int]
    pixels_removed: dict[str, int]
    success: bool
    message: str


@dataclass
class RemoveBgResult:
    """Result from background removal operation."""

    input_path: str
    output_path: str
    method_used: str
    success: bool
    message: str


@dataclass
class OptimizeResult:
    """Result from image optimization operation."""

    input_path: str
    output_path: str
    original_size_bytes: int
    optimized_size_bytes: int
    compression_ratio: float
    success: bool
    message: str


class ImageService(Service):
    """Service for image processing operations."""

    @property
    def name(self) -> str:
        """Service name."""
        return "image"

    def __init__(self):
        """Initialize the image service."""

    def check_available(self) -> tuple[bool, str | None]:
        """
        Check if service is available.

        Returns:
            Tuple of (is_available, error_message)
        """
        if not DEPENDENCIES_AVAILABLE:  # pragma: no cover
            return (False, "Missing required dependencies: pillow and/or numpy")
        return (True, None)

    def _find_content_bounds(
        self, data: np.ndarray, tolerance: int = 10,
    ) -> tuple[int, int, int, int]:
        """
        Find the bounds of non-background content in an image.

        Args:
            data: Image data as numpy array
            tolerance: Color tolerance for background detection (0-255)

        Returns:
            Tuple of (left, top, right, bottom) coordinates
        """
        # Check if image has alpha channel
        if data.shape[2] == 4:  # RGBA
            # Use alpha channel to find content
            content_mask = data[:, :, 3] > 0
        else:  # RGB
            # Sample corners to determine background color
            height, width = data.shape[:2]
            corners = [
                data[0, 0],  # top-left
                data[0, width - 1],  # top-right
                data[height - 1, 0],  # bottom-left
                data[height - 1, width - 1],  # bottom-right
            ]

            # Use the first corner as background reference
            bg_color = corners[0]

            # Find pixels that differ from background
            diff = np.abs(data[:, :, :3].astype(int) - bg_color.astype(int))
            content_mask = np.any(diff > tolerance, axis=2)

        # Find bounds
        rows = np.any(content_mask, axis=1)
        cols = np.any(content_mask, axis=0)

        if not np.any(rows) or not np.any(cols):
            # No content found, return full image bounds
            return (0, 0, data.shape[1], data.shape[0])

        top = np.argmax(rows)
        bottom = len(rows) - np.argmax(rows[::-1])
        left = np.argmax(cols)
        right = len(cols) - np.argmax(cols[::-1])

        return (left, top, right, bottom)

    def crop(
        self,
        input_path: str,
        output_path: str | None = None,
        tolerance: int = 10,
        padding: int = 0,
    ) -> CropResult:
        """
        Crop image to remove whitespace/padding.

        Args:
            input_path: Path to input image
            output_path: Path for output image (optional, auto-generated if not provided)
            tolerance: Color tolerance for background detection (0-255)
            padding: Pixels to keep around content

        Returns:
            CropResult with operation details

        Raises:
            ServiceError: If crop operation fails
        """
        try:
            # Validate input
            input_file = Path(input_path)
            if not input_file.exists():
                raise ServiceError(
                    message=f"Input file not found: {input_path}",
                    service_name="image",
                )

            # Generate output path if not provided
            if not output_path:
                output_file = input_file.parent / f"{input_file.stem}_cropped.png"
            else:
                output_file = Path(output_path)
                output_file.parent.mkdir(parents=True, exist_ok=True)

            # Load image
            try:
                image = Image.open(input_file)
            except Exception as e:
                raise ServiceError(
                    message=f"Failed to load image: {e}",
                    service_name="image",
                )

            original_size = image.size

            # Convert to numpy array for processing
            data = np.array(image)

            # Find content bounds
            left, top, right, bottom = self._find_content_bounds(data, tolerance)

            # Add padding
            left = max(0, left - padding)
            top = max(0, top - padding)
            right = min(data.shape[1], right + padding)
            bottom = min(data.shape[0], bottom + padding)

            # Crop image
            cropped_image = image.crop((left, top, right, bottom))
            cropped_size = cropped_image.size

            # Calculate pixels removed
            pixels_removed = {
                "left": left,
                "top": top,
                "right": original_size[0] - right,
                "bottom": original_size[1] - bottom,
                "total": (original_size[0] * original_size[1])
                - (cropped_size[0] * cropped_size[1]),
            }

            # Save with format preservation
            save_kwargs: dict[str, Any] = {"optimize": True}
            if image.mode == "RGBA" or (image.mode == "P" and "transparency" in image.info):
                cropped_image.save(output_file, "PNG", **save_kwargs)
            else:
                cropped_image.save(output_file, **save_kwargs)

            return CropResult(
                input_path=str(input_file),
                output_path=str(output_file),
                original_size=original_size,
                cropped_size=cropped_size,
                crop_box=(left, top, right, bottom),
                pixels_removed=pixels_removed,
                success=True,
                message="Image cropped successfully",
            )

        except ServiceError:
            raise
        except Exception as e:
            raise ServiceError(
                message=f"Crop operation failed: {e}",
                service_name="image",
            )

    def remove_background(
        self,
        input_path: str,
        output_path: str | None = None,
        tolerance: int = 30,
    ) -> RemoveBgResult:
        """
        Remove background from image.

        Args:
            input_path: Path to input image
            output_path: Path for output image (optional, auto-generated if not provided)
            tolerance: Color tolerance for background detection (0-255)

        Returns:
            RemoveBgResult with operation details

        Raises:
            ServiceError: If background removal fails
        """
        try:
            # Validate input
            input_file = Path(input_path)
            if not input_file.exists():
                raise ServiceError(
                    message=f"Input file not found: {input_path}",
                    service_name="image",
                )

            # Generate output path if not provided
            if not output_path:
                output_file = input_file.parent / f"{input_file.stem}_no_bg.png"
            else:
                output_file = Path(output_path)
                output_file.parent.mkdir(parents=True, exist_ok=True)

            # Load image
            try:
                image = Image.open(input_file)
            except Exception as e:
                raise ServiceError(
                    message=f"Failed to load image: {e}",
                    service_name="image",
                )

            # Convert to RGBA if not already
            if image.mode != "RGBA":
                image = image.convert("RGBA")

            # Convert to numpy array
            data = np.array(image)

            # Get background color from corners
            corners = [
                data[0, 0],  # top-left
                data[0, -1],  # top-right
                data[-1, 0],  # bottom-left
                data[-1, -1],  # bottom-right
            ]

            # Use first corner as background reference
            bg_color = corners[0][:3]

            # Create mask for pixels similar to background color
            diff = np.abs(data[:, :, :3].astype(int) - bg_color.astype(int))
            mask = np.all(diff <= tolerance, axis=2)

            # Set transparent pixels
            data[mask, 3] = 0

            # Create image from modified array
            processed_image = Image.fromarray(data, "RGBA")

            # Save as PNG
            try:
                processed_image.save(output_file, "PNG")
            except Exception as e:
                raise ServiceError(
                    message=f"Failed to save image: {e}",
                    service_name="image",
                )

            return RemoveBgResult(
                input_path=str(input_file),
                output_path=str(output_file),
                method_used="white_background_removal",
                success=True,
                message="Background removed successfully",
            )

        except ServiceError:
            raise
        except Exception as e:
            raise ServiceError(
                message=f"Background removal failed: {e}",
                service_name="image",
            )

    def optimize(
        self,
        input_path: str,
        output_path: str | None = None,
        quality: int = 85,
        max_dimension: int | None = None,
    ) -> OptimizeResult:
        """
        Optimize image for web/storage.

        Args:
            input_path: Path to input image
            output_path: Path for output image (optional, auto-generated if not provided)
            quality: JPEG quality (1-100, default 85)
            max_dimension: Maximum width or height (maintains aspect ratio)

        Returns:
            OptimizeResult with operation details

        Raises:
            ServiceError: If optimization fails
        """
        try:
            # Validate input
            input_file = Path(input_path)
            if not input_file.exists():
                raise ServiceError(
                    message=f"Input file not found: {input_path}",
                    service_name="image",
                )

            # Generate output path if not provided
            if not output_path:
                output_file = input_file.parent / f"{input_file.stem}_optimized{input_file.suffix}"
            else:
                output_file = Path(output_path)
                output_file.parent.mkdir(parents=True, exist_ok=True)

            # Load image
            try:
                image = Image.open(input_file)
            except Exception as e:
                raise ServiceError(
                    message=f"Failed to load image: {e}",
                    service_name="image",
                )

            # Get original file size
            original_size_bytes = input_file.stat().st_size

            # Resize if max_dimension specified
            if max_dimension:  # pragma: no cover
                width, height = image.size
                if width > max_dimension or height > max_dimension:
                    if width > height:
                        new_width = max_dimension
                        new_height = int((max_dimension / width) * height)
                    else:
                        new_height = max_dimension
                        new_width = int((max_dimension / height) * width)

                    image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Save with optimization
            save_kwargs: dict[str, Any] = {"optimize": True}

            # Handle different formats
            if (  # pragma: no cover
                image.mode == "RGBA"
                or (image.mode == "P" and "transparency" in image.info)
            ):
                # PNG for transparency
                image.save(output_file, "PNG", **save_kwargs)
            elif input_file.suffix.lower() in {".jpg", ".jpeg"}:
                # JPEG with quality
                if image.mode != "RGB":  # pragma: no cover
                    image = image.convert("RGB")
                image.save(output_file, "JPEG", quality=quality, **save_kwargs)
            else:  # pragma: no cover
                # Default format preservation
                image.save(output_file, **save_kwargs)

            # Get optimized file size
            optimized_size_bytes = output_file.stat().st_size
            compression_ratio = (
                1 - (optimized_size_bytes / original_size_bytes)
            ) * 100 if original_size_bytes > 0 else 0

            return OptimizeResult(
                input_path=str(input_file),
                output_path=str(output_file),
                original_size_bytes=original_size_bytes,
                optimized_size_bytes=optimized_size_bytes,
                compression_ratio=compression_ratio,
                success=True,
                message=f"Image optimized successfully (reduced by {compression_ratio:.1f}%)",
            )

        except ServiceError:
            raise
        except Exception as e:
            raise ServiceError(
                message=f"Optimization failed: {e}",
                service_name="image",
            )
