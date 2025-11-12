#!/usr/bin/env python3
"""
Direct image cropping script to remove whitespace around logos.
"""

import sys
from pathlib import Path

import numpy as np
from PIL import Image


def find_content_bounds(img_array, tolerance=10):
    """Find the bounding box of non-transparent/non-background content."""
    height, width = img_array.shape[:2]

    # For RGBA images, use alpha channel to find content
    if len(img_array.shape) == 3 and img_array.shape[2] == 4:
        # Use alpha channel - anything not fully transparent is content
        alpha = img_array[:, :, 3]
        content_mask = alpha > 0
    else:
        # For non-RGBA images, detect background color from corners
        corners = [
            img_array[0, 0],      # top-left
            img_array[0, -1],     # top-right
            img_array[-1, 0],     # bottom-left
            img_array[-1, -1],    # bottom-right
        ]

        # Use top-left corner as background color
        bg_color = corners[0]

        if len(img_array.shape) == 3:
            # RGB image
            diff = np.abs(img_array.astype(int) - bg_color.astype(int))
            content_mask = np.any(diff > tolerance, axis=2)
        else:
            # Grayscale image
            diff = np.abs(img_array.astype(int) - int(bg_color))
            content_mask = diff > tolerance

    # Find bounding box of content
    content_rows = np.any(content_mask, axis=1)
    content_cols = np.any(content_mask, axis=0)

    if not np.any(content_rows) or not np.any(content_cols):
        # No content found, return original bounds
        return (0, 0, width, height)

    top = np.argmax(content_rows)
    bottom = height - 1 - np.argmax(content_rows[::-1])
    left = np.argmax(content_cols)
    right = width - 1 - np.argmax(content_cols[::-1])

    return (left, top, right + 1, bottom + 1)


def crop_image(input_path, output_path=None, padding=5, tolerance=10):
    """Crop image to remove whitespace."""
    input_path = Path(input_path)

    if output_path is None:
        output_path = input_path.parent / f"{input_path.stem}-tight-cropped.png"
    else:
        output_path = Path(output_path)

    # Load image
    with Image.open(input_path) as img:
        print(f"Original size: {img.size}")

        # Convert to numpy array
        img_array = np.array(img)

        # Find content bounds
        left, top, right, bottom = find_content_bounds(img_array, tolerance)

        print(f"Content bounds: left={left}, top={top}, right={right}, bottom={bottom}")

        # Add padding
        left = max(0, left - padding)
        top = max(0, top - padding)
        right = min(img.width, right + padding)
        bottom = min(img.height, bottom + padding)

        print(f"With padding: left={left}, top={top}, right={right}, bottom={bottom}")

        # Crop image
        cropped_img = img.crop((left, top, right, bottom))

        print(f"New size: {cropped_img.size}")

        # Save cropped image
        output_path.parent.mkdir(parents=True, exist_ok=True)
        cropped_img.save(output_path, "PNG", optimize=True)

        print(f"Saved to: {output_path}")

        return str(output_path)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python crop_logo.py <input_path> [output_path] [padding] [tolerance]")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    padding = int(sys.argv[3]) if len(sys.argv) > 3 else 5
    tolerance = int(sys.argv[4]) if len(sys.argv) > 4 else 10

    try:
        result = crop_image(input_path, output_path, padding, tolerance)
        print(f"✅ Successfully cropped: {result}")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
