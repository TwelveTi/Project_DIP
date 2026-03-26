"""
Image Enhancement – Spatial Domain
Covers: Histogram Equalization, CLAHE, Gamma Correction,
        Log Transform, Power-Law, Negative, Contrast Stretching,
        Brightness/Contrast adjustment
"""

import cv2
import numpy as np


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _to_gray(img):
    """Return grayscale view if already 1-channel, else convert."""
    if len(img.shape) == 2:
        return img, False
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), True

def _apply_per_channel(img, fn, **kw):
    """Apply a grayscale function channel-by-channel on a BGR image."""
    if len(img.shape) == 2:
        return fn(img, **kw)
    channels = cv2.split(img)
    processed = [fn(c, **kw) for c in channels]
    return cv2.merge(processed)


# ──────────────────────────────────────────────────────────────────────────────
# 1. Histogram Equalization
# ──────────────────────────────────────────────────────────────────────────────

def histogram_equalization(img: np.ndarray) -> np.ndarray:
    """
    Global histogram equalization.
    For color images uses YCrCb space to equalize only luminance (Y),
    preserving hue/saturation.
    """
    if len(img.shape) == 2:
        return cv2.equalizeHist(img)

    ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
    ycrcb[:, :, 0] = cv2.equalizeHist(ycrcb[:, :, 0])
    return cv2.cvtColor(ycrcb, cv2.COLOR_YCrCb2BGR)


# ──────────────────────────────────────────────────────────────────────────────
# 2. CLAHE – Contrast Limited Adaptive Histogram Equalization
# ──────────────────────────────────────────────────────────────────────────────

def clahe_enhancement(img: np.ndarray,
                       clip_limit: float = 2.0,
                       tile_grid: tuple = (8, 8)) -> np.ndarray:
    """
    CLAHE operates on small tiles; clip_limit prevents over-amplification.
    For color: applied only to Y channel.
    """
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid)

    if len(img.shape) == 2:
        return clahe.apply(img)

    ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
    ycrcb[:, :, 0] = clahe.apply(ycrcb[:, :, 0])
    return cv2.cvtColor(ycrcb, cv2.COLOR_YCrCb2BGR)


# ──────────────────────────────────────────────────────────────────────────────
# 3. Gamma Correction  (Power-Law / s = c · r^γ)
# ──────────────────────────────────────────────────────────────────────────────

def gamma_correction(img: np.ndarray, gamma: float = 1.0) -> np.ndarray:
    """
    s = (r / 255)^γ × 255
    γ < 1  → brighter (expand dark regions)
    γ > 1  → darker  (compress dark regions)
    """
    if gamma <= 0:
        raise ValueError("Gamma must be > 0")

    inv_gamma = 1.0 / gamma
    # Build lookup table for speed
    lut = np.array([((i / 255.0) ** inv_gamma) * 255
                    for i in np.arange(256)], dtype=np.uint8)
    return cv2.LUT(img, lut)


def power_law_transform(img: np.ndarray, c: float = 1.0, gamma: float = 1.0) -> np.ndarray:
    """General power-law: s = c · r^γ (values clipped to [0,255])."""
    normalized = img.astype(np.float32) / 255.0
    result = c * np.power(normalized, gamma)
    return np.clip(result * 255, 0, 255).astype(np.uint8)


# ──────────────────────────────────────────────────────────────────────────────
# 4. Log Transform  (s = c · log(1 + r))
# ──────────────────────────────────────────────────────────────────────────────

def log_transform(img: np.ndarray, c: float | None = None) -> np.ndarray:
    """
    s = c · log(1 + r)
    c is auto-computed so that output max ≈ 255.
    Expands dark pixel values; compresses bright ones.
    """
    img_float = img.astype(np.float32)
    log_img = np.log1p(img_float)           # log(1 + r)
    if c is None:
        c = 255.0 / np.log1p(255.0)
    result = c * log_img
    return np.clip(result, 0, 255).astype(np.uint8)


# ──────────────────────────────────────────────────────────────────────────────
# 5. Negative Transform  (s = L − 1 − r)
# ──────────────────────────────────────────────────────────────────────────────

def negative_transform(img: np.ndarray) -> np.ndarray:
    """s = 255 − r  (bitwise NOT for uint8)."""
    return cv2.bitwise_not(img)


# ──────────────────────────────────────────────────────────────────────────────
# 6. Contrast Stretching  (piecewise-linear)
# ──────────────────────────────────────────────────────────────────────────────

def contrast_stretching(img: np.ndarray,
                         r_min: int = 0,
                         r_max: int = 255) -> np.ndarray:
    """
    Linearly map [r_min, r_max] → [0, 255].
    Pixels below r_min → 0, above r_max → 255.
    """
    r_min = max(0, min(r_min, 254))
    r_max = max(r_min + 1, min(r_max, 255))

    def _stretch(channel):
        lut = np.zeros(256, dtype=np.uint8)
        for i in range(256):
            if i <= r_min:
                lut[i] = 0
            elif i >= r_max:
                lut[i] = 255
            else:
                lut[i] = int((i - r_min) / (r_max - r_min) * 255)
        return cv2.LUT(channel, lut)

    return _apply_per_channel(img, _stretch)


# ──────────────────────────────────────────────────────────────────────────────
# 7. Brightness / Contrast
# ──────────────────────────────────────────────────────────────────────────────

def brightness_contrast(img: np.ndarray,
                         brightness: int = 0,
                         contrast: float = 1.0) -> np.ndarray:
    """
    g(x,y) = contrast × f(x,y) + brightness
    Equivalent to OpenCV's convertScaleAbs with alpha=contrast, beta=brightness.
    """
    result = cv2.convertScaleAbs(img, alpha=contrast, beta=brightness)
    return result
