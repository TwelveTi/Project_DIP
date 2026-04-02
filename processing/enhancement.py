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


# ──────────────────────────────────────────────────────────────────────────────
# 8. Combined Enhancement for Blurry Images
# ──────────────────────────────────────────────────────────────────────────────

def enhance_blurry_image(img: np.ndarray,
                         clahe_clip: float = 3.0,
                         clahe_tiles: tuple = (8, 8),
                         sharpen_strength: float = 2.0) -> np.ndarray:
    """
    Combined enhancement for motion-blurred or soft images.
    
    Steps:
    1. Apply CLAHE for contrast enhancement
    2. Apply unsharp masking for sharpening
    
    Args:
        img: Input image (BGR or grayscale)
        clahe_clip: Clip limit for CLAHE (higher = stronger)
        clahe_tiles: Tile grid size for CLAHE
        sharpen_strength: Unsharp masking strength (k parameter)
    
    Returns:
        Enhanced image with better clarity and sharpness
    """
    # Step 1: CLAHE for contrast enhancement
    enhanced = clahe_enhancement(img, clip_limit=clahe_clip, tile_grid=clahe_tiles)
    
    # Step 2: Unsharp masking for sharpening
    blurred = cv2.GaussianBlur(enhanced, (5, 5), 1.0)
    enhanced_f = enhanced.astype(np.float32)
    blurred_f = blurred.astype(np.float32)
    mask = enhanced_f - blurred_f
    result = enhanced_f + sharpen_strength * mask
    
    return np.clip(result, 0, 255).astype(np.uint8)


# ──────────────────────────────────────────────────────────────────────────────
# 9. Reduce Glare / Anti-Backlight Enhancement
# ──────────────────────────────────────────────────────────────────────────────

def reduce_glare_exposure(img: np.ndarray,
                          gamma: float = 1.5,
                          clahe_clip: float = 2.5,
                          highlights_recover: float = 0.3) -> np.ndarray:
    """
    Reduce glare and overexposure for backlit images.
    Suitable for images with excessive bright areas or highlights.
    
    Steps:
    1. Apply gamma correction (gamma > 1) to darken bright areas
    2. Apply CLAHE to recover shadow details
    3. Blend with original to preserve natural look
    
    Args:
        img: Input image (BGR or grayscale)
        gamma: Gamma correction (1.5 = moderate darkening, 2.0+ = strong)
        clahe_clip: CLAHE clip limit for detail recovery
        highlights_recover: Blend factor [0-1] to control strength correction
    
    Returns:
        Image with reduced glare and balanced exposure
    """
    # Step 1: Gamma correction to darken highlights
    corrected = gamma_correction(img, gamma=gamma)
    
    # Step 2: Apply CLAHE to recover shadow details
    enhanced = clahe_enhancement(corrected, clip_limit=clahe_clip, tile_grid=(8, 8))
    
    # Step 3: Blend with original to avoid over-darkening
    img_f = img.astype(np.float32)
    enhanced_f = enhanced.astype(np.float32)
    result = img_f * (1 - highlights_recover) + enhanced_f * highlights_recover
    
    return np.clip(result, 0, 255).astype(np.uint8)


def anti_backlight_enhancement(img: np.ndarray,
                                shadow_boost: float = 1.3,
                                highlight_reduce: float = 0.7) -> np.ndarray:
    """
    Advanced anti-backlight enhancement using tone mapping.
    Brightens shadows and tones down highlights for balanced exposure.
    
    Args:
        img: Input image (BGR or grayscale)
        shadow_boost: Multiplicative factor for shadow areas (higher = brighter shadows)
        highlight_reduce: Multiplicative factor for highlights (lower = darker highlights)
    
    Returns:
        Balanced image with improved backlight handling
    """
    img_float = img.astype(np.float32) / 255.0
    
    # Simple tone mapping: expand midtones, compress extremes
    mid = 0.5
    result = np.where(
        img_float < mid,
        img_float ** (1 / shadow_boost),  # Boost shadows
        img_float ** highlight_reduce      # Reduce highlights
    )
    
    return np.clip(result * 255, 0, 255).astype(np.uint8)

