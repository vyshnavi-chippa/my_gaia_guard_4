from __future__ import annotations

import cv2
import numpy as np


def detect_changes(
    before_image_path: str,
    after_image_path: str,
    threshold_value: int = 30,
) -> tuple[np.ndarray, float]:
    """
    Detect visual changes between two images using OpenCV.

    Returns:
        change_mask: Binary mask (uint8) where changed pixels are 255.
        percentage_change: Percent of changed pixels in [0, 100].
    """
    before = cv2.imread(before_image_path)
    after = cv2.imread(after_image_path)

    if before is None:
        raise ValueError(f"Could not read before image: {before_image_path}")
    if after is None:
        raise ValueError(f"Could not read after image: {after_image_path}")

    if before.shape != after.shape:
        # Keep demo simple: resize "after" to "before" size.
        after = cv2.resize(after, (before.shape[1], before.shape[0]))

    before_gray = cv2.cvtColor(before, cv2.COLOR_BGR2GRAY)
    after_gray = cv2.cvtColor(after, cv2.COLOR_BGR2GRAY)

    before_blur = cv2.GaussianBlur(before_gray, (5, 5), 0)
    after_blur = cv2.GaussianBlur(after_gray, (5, 5), 0)

    diff = cv2.absdiff(before_blur, after_blur)
    _, change_mask = cv2.threshold(diff, threshold_value, 255, cv2.THRESH_BINARY)

    kernel = np.ones((3, 3), np.uint8)
    change_mask = cv2.morphologyEx(change_mask, cv2.MORPH_OPEN, kernel, iterations=1)
    change_mask = cv2.morphologyEx(change_mask, cv2.MORPH_CLOSE, kernel, iterations=1)

    changed_pixels = int(np.count_nonzero(change_mask))
    total_pixels = int(change_mask.size)
    percentage_change = (changed_pixels / total_pixels) * 100 if total_pixels else 0.0

    return change_mask, round(percentage_change, 2)


def save_change_mask(change_mask: np.ndarray, output_path: str) -> None:
    """Save change mask as image file."""
    ok = cv2.imwrite(output_path, change_mask)
    if not ok:
        raise ValueError(f"Could not save change mask to: {output_path}")
