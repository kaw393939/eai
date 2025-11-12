"""
Tests for ImageService.

Tests image processing operations including cropping, background removal,
and optimization with proper validation and error handling.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest
from PIL import Image

from ei_cli.services.base import ServiceError
from ei_cli.services.image_service import (
    CropResult,
    ImageService,
    OptimizeResult,
    RemoveBgResult,
)


@pytest.fixture
def service():
    """Create ImageService instance."""
    return ImageService()


@pytest.fixture
def temp_image():
    """Create a temporary test image."""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        # Create a simple image with white background and red square in center
        img = Image.new("RGB", (100, 100), "white")
        for x in range(40, 60):
            for y in range(40, 60):
                img.putpixel((x, y), (255, 0, 0))
        img.save(f.name)
        yield f.name
        Path(f.name).unlink(missing_ok=True)


@pytest.fixture
def temp_rgba_image():
    """Create a temporary RGBA test image."""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        # Create RGBA image with transparent background
        img = Image.new("RGBA", (100, 100), (255, 255, 255, 0))
        for x in range(40, 60):
            for y in range(40, 60):
                img.putpixel((x, y), (255, 0, 0, 255))
        img.save(f.name)
        yield f.name
        Path(f.name).unlink(missing_ok=True)


class TestImageServiceInitialization:
    """Test ImageService initialization."""

    def test_initialization(self, service):
        """Test service initializes correctly."""
        assert service is not None

    def test_check_available_success(self, service):
        """Test availability check succeeds with dependencies."""
        available, error = service.check_available()
        assert available is True
        assert error is None

    @patch("ei_cli.services.image_service.DEPENDENCIES_AVAILABLE", False)
    def test_check_available_missing_dependencies(self):
        """Test availability check fails without dependencies."""
        service = ImageService()
        available, error = service.check_available()
        assert available is False
        assert "pillow and/or numpy" in error.lower()


class TestImageServiceCrop:
    """Test image cropping functionality."""

    def test_crop_basic(self, service, temp_image):
        """Test basic image cropping."""
        output_path = temp_image.replace(".png", "_cropped.png")

        result = service.crop(temp_image, output_path=output_path)

        assert isinstance(result, CropResult)
        assert result.success is True
        assert result.input_path == temp_image
        assert result.output_path == output_path
        assert result.original_size == (100, 100)
        # Should crop to approximately the red square (40-60 range)
        assert result.cropped_size[0] < 100
        assert result.cropped_size[1] < 100
        assert Path(output_path).exists()

        # Cleanup
        Path(output_path).unlink(missing_ok=True)

    def test_crop_auto_output_path(self, service, temp_image):
        """Test cropping with auto-generated output path."""
        result = service.crop(temp_image)

        assert result.success is True
        assert "_cropped.png" in result.output_path
        assert Path(result.output_path).exists()

        # Cleanup
        Path(result.output_path).unlink(missing_ok=True)

    def test_crop_with_padding(self, service, temp_image):
        """Test cropping with padding."""
        output_path = temp_image.replace(".png", "_cropped_padded.png")

        result = service.crop(temp_image, output_path=output_path, padding=5)

        assert result.success is True
        # With padding, should be slightly larger than without
        assert Path(output_path).exists()

        # Cleanup
        Path(output_path).unlink(missing_ok=True)

    def test_crop_with_tolerance(self, service, temp_image):
        """Test cropping with different tolerance."""
        output_path = temp_image.replace(".png", "_cropped_tolerance.png")

        result = service.crop(
            temp_image, output_path=output_path, tolerance=50,
        )

        assert result.success is True
        assert Path(output_path).exists()

        # Cleanup
        Path(output_path).unlink(missing_ok=True)

    def test_crop_rgba_image(self, service, temp_rgba_image):
        """Test cropping RGBA image with alpha channel."""
        output_path = temp_rgba_image.replace(".png", "_cropped.png")

        result = service.crop(temp_rgba_image, output_path=output_path)

        assert result.success is True
        assert Path(output_path).exists()

        # Verify transparency preserved
        img = Image.open(output_path)
        assert img.mode == "RGBA"

        # Cleanup
        Path(output_path).unlink(missing_ok=True)

    def test_crop_nonexistent_file(self, service):
        """Test cropping nonexistent file raises error."""
        with pytest.raises(ServiceError) as exc_info:
            service.crop("/nonexistent/file.png")

        assert "not found" in str(exc_info.value).lower()
        assert exc_info.value.service_name == "image"

    def test_crop_invalid_image(self, service):
        """Test cropping invalid image file raises error."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"not an image")
            temp_path = f.name

        try:
            with pytest.raises(ServiceError) as exc_info:
                service.crop(temp_path)

            assert exc_info.value.service_name == "image"
        finally:
            Path(temp_path).unlink(missing_ok=True)


class TestImageServiceRemoveBackground:
    """Test background removal functionality."""

    def test_remove_background_basic(self, service, temp_image):
        """Test basic background removal."""
        output_path = temp_image.replace(".png", "_no_bg.png")

        result = service.remove_background(temp_image, output_path=output_path)

        assert isinstance(result, RemoveBgResult)
        assert result.success is True
        assert result.input_path == temp_image
        assert result.output_path == output_path
        assert result.method_used == "white_background_removal"
        assert Path(output_path).exists()

        # Verify output is RGBA
        img = Image.open(output_path)
        assert img.mode == "RGBA"

        # Cleanup
        Path(output_path).unlink(missing_ok=True)

    def test_remove_background_auto_output_path(self, service, temp_image):
        """Test background removal with auto-generated output path."""
        result = service.remove_background(temp_image)

        assert result.success is True
        assert "_no_bg.png" in result.output_path
        assert Path(result.output_path).exists()

        # Cleanup
        Path(result.output_path).unlink(missing_ok=True)

    def test_remove_background_with_tolerance(self, service, temp_image):
        """Test background removal with different tolerance."""
        output_path = temp_image.replace(".png", "_no_bg_tolerance.png")

        result = service.remove_background(
            temp_image, output_path=output_path, tolerance=50,
        )

        assert result.success is True
        assert Path(output_path).exists()

        # Cleanup
        Path(output_path).unlink(missing_ok=True)

    def test_remove_background_rgba_image(self, service, temp_rgba_image):
        """Test background removal on RGBA image."""
        output_path = temp_rgba_image.replace(".png", "_no_bg.png")

        result = service.remove_background(
            temp_rgba_image, output_path=output_path,
        )

        assert result.success is True
        assert Path(output_path).exists()

        # Cleanup
        Path(output_path).unlink(missing_ok=True)

    def test_remove_background_nonexistent_file(self, service):
        """Test background removal on nonexistent file raises error."""
        with pytest.raises(ServiceError) as exc_info:
            service.remove_background("/nonexistent/file.png")

        assert "not found" in str(exc_info.value).lower()
        assert exc_info.value.service_name == "image"

    def test_remove_background_invalid_image(self, service):
        """Test background removal on invalid image raises error."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"not an image")
            temp_path = f.name

        try:
            with pytest.raises(ServiceError) as exc_info:
                service.remove_background(temp_path)

            assert exc_info.value.service_name == "image"
        finally:
            Path(temp_path).unlink(missing_ok=True)


class TestImageServiceOptimize:
    """Test image optimization functionality."""

    def test_optimize_basic(self, service, temp_image):
        """Test basic image optimization."""
        output_path = temp_image.replace(".png", "_optimized.png")

        result = service.optimize(temp_image, output_path=output_path)

        assert isinstance(result, OptimizeResult)
        assert result.success is True
        assert result.input_path == temp_image
        assert result.output_path == output_path
        assert result.original_size_bytes > 0
        assert result.optimized_size_bytes > 0
        assert isinstance(result.compression_ratio, float)
        assert Path(output_path).exists()

        # Cleanup
        Path(output_path).unlink(missing_ok=True)

    def test_optimize_auto_output_path(self, service, temp_image):
        """Test optimization with auto-generated output path."""
        result = service.optimize(temp_image)

        assert result.success is True
        assert "_optimized" in result.output_path
        assert Path(result.output_path).exists()

        # Cleanup
        Path(result.output_path).unlink(missing_ok=True)

    def test_optimize_with_quality(self, service):
        """Test optimization with quality setting."""
        # Create JPEG for quality test
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            img = Image.new("RGB", (200, 200), "blue")
            img.save(f.name)
            temp_path = f.name

        try:
            output_path = temp_path.replace(".jpg", "_optimized.jpg")
            result = service.optimize(
                temp_path, output_path=output_path, quality=50,
            )

            assert result.success is True
            assert Path(output_path).exists()

            # Lower quality should result in smaller file
            assert result.optimized_size_bytes < result.original_size_bytes

            # Cleanup
            Path(output_path).unlink(missing_ok=True)
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_optimize_with_max_dimension(self, service):
        """Test optimization with size limit."""
        # Create larger image
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            img = Image.new("RGB", (500, 500), "green")
            img.save(f.name)
            temp_path = f.name

        try:
            output_path = temp_path.replace(".png", "_optimized.png")
            result = service.optimize(
                temp_path, output_path=output_path, max_dimension=200,
            )

            assert result.success is True
            assert Path(output_path).exists()

            # Check size was reduced
            img = Image.open(output_path)
            assert max(img.size) <= 200

            # Cleanup
            Path(output_path).unlink(missing_ok=True)
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_optimize_rgba_image(self, service, temp_rgba_image):
        """Test optimization preserves transparency."""
        output_path = temp_rgba_image.replace(".png", "_optimized.png")

        result = service.optimize(temp_rgba_image, output_path=output_path)

        assert result.success is True
        assert Path(output_path).exists()

        # Verify transparency preserved
        img = Image.open(output_path)
        assert img.mode == "RGBA"

        # Cleanup
        Path(output_path).unlink(missing_ok=True)

    def test_optimize_nonexistent_file(self, service):
        """Test optimization on nonexistent file raises error."""
        with pytest.raises(ServiceError) as exc_info:
            service.optimize("/nonexistent/file.png")

        assert "not found" in str(exc_info.value).lower()
        assert exc_info.value.service_name == "image"

    def test_optimize_invalid_image(self, service):
        """Test optimization on invalid image raises error."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"not an image")
            temp_path = f.name

        try:
            with pytest.raises(ServiceError) as exc_info:
                service.optimize(temp_path)

            assert exc_info.value.service_name == "image"
        finally:
            Path(temp_path).unlink(missing_ok=True)


class TestImageServiceHelpers:
    """Test internal helper methods."""

    def test_find_content_bounds_rgba(self, service):
        """Test finding content bounds with alpha channel."""
        # Create test data with transparent border
        data = np.zeros((100, 100, 4), dtype=np.uint8)
        # Set content area (center 20x20) to opaque
        data[40:60, 40:60, 3] = 255

        left, top, right, bottom = service._find_content_bounds(data)

        assert left == 40
        assert top == 40
        assert right == 60
        assert bottom == 60

    def test_find_content_bounds_rgb(self, service):
        """Test finding content bounds without alpha channel."""
        # Create test data with white background and red center
        data = np.full((100, 100, 3), 255, dtype=np.uint8)
        data[40:60, 40:60] = [255, 0, 0]  # Red square

        left, top, right, bottom = service._find_content_bounds(
            data, tolerance=10,
        )

        assert left == 40
        assert top == 40
        assert right == 60
        assert bottom == 60

    def test_find_content_bounds_no_content(self, service):
        """Test finding content bounds with uniform image."""
        # Create uniform data (all same color)
        data = np.full((100, 100, 3), 255, dtype=np.uint8)

        left, top, right, bottom = service._find_content_bounds(data)

        # Should return full image bounds
        assert left == 0
        assert top == 0
        assert right == 100
        assert bottom == 100
