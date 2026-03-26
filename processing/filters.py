"""
Spatial Domain Filters
Covers: Mean, Gaussian, Median (smoothing)
        Laplacian Sharpen, Unsharp Masking, High-Boost (sharpening)
        Sobel, Prewitt, Laplacian, Canny (edge detection)
        Custom Kernel
"""

import cv2
import numpy as np


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _ensure_odd(k: int) -> int:
    return k if k % 2 == 1 else k + 1


# ──────────────────────────────────────────────────────────────────────────────
# 1. Smoothing / Low-pass Filters
# ──────────────────────────────────────────────────────────────────────────────

def mean_filter(img: np.ndarray, ksize: int = 3) -> np.ndarray:
    """
    Average (box) filter.
    Each output pixel = arithmetic mean of ksize×ksize neighbourhood.
    Kernel: all 1/(k²)
    """
    k = _ensure_odd(ksize)
    return cv2.blur(img, (k, k))


def gaussian_filter(img: np.ndarray, ksize: int = 3, sigma: float = 0) -> np.ndarray:
    """
    Gaussian blur.
    Weights follow 2-D Gaussian distribution; preserves edges better than mean.
    sigma=0 → OpenCV auto-computes from ksize.
    """
    k = _ensure_odd(ksize)
    return cv2.GaussianBlur(img, (k, k), sigma)


def median_filter(img: np.ndarray, ksize: int = 3) -> np.ndarray:
    """
    Median filter – excellent for salt-and-pepper noise.
    Replaces each pixel with the median of its neighbourhood.
    """
    k = _ensure_odd(ksize)
    return cv2.medianBlur(img, k)


# ──────────────────────────────────────────────────────────────────────────────
# 2. Sharpening / High-pass Filters
# ──────────────────────────────────────────────────────────────────────────────

def laplacian_sharpen(img: np.ndarray) -> np.ndarray:
    """
    Laplacian-based sharpening:
      g = f − ∇²f   (when centre of Laplacian kernel is negative)
    Uses 4-connectivity Laplacian, then adds back to original.
    """
    # Laplacian kernel (4-neighbour):
    #  [ 0  -1  0 ]
    #  [-1   4 -1 ]
    #  [ 0  -1  0 ]
    gray = len(img.shape) == 2

    if gray:
        lap = cv2.Laplacian(img.astype(np.float32), cv2.CV_32F, ksize=3)
        sharpened = img.astype(np.float32) - lap
    else:
        lap = cv2.Laplacian(img.astype(np.float32), cv2.CV_32F, ksize=3)
        sharpened = img.astype(np.float32) - lap

    return np.clip(sharpened, 0, 255).astype(np.uint8)


def unsharp_masking(img: np.ndarray, ksize: int = 5, sigma: float = 1.0,
                     k: float = 1.5) -> np.ndarray:
    """
    Unsharp Masking:
      mask     = f − f_blurred
      g        = f + k × mask
              = (1+k)·f − k·f_blurred
    k controls sharpening strength.
    """
    blurred = cv2.GaussianBlur(img, (_ensure_odd(ksize), _ensure_odd(ksize)), sigma)
    img_f = img.astype(np.float32)
    blr_f = blurred.astype(np.float32)
    mask = img_f - blr_f
    result = img_f + k * mask
    return np.clip(result, 0, 255).astype(np.uint8)


def high_boost_filter(img: np.ndarray, ksize: int = 5,
                       sigma: float = 1.0, A: float = 2.0) -> np.ndarray:
    """
    High-Boost Filter:
      g = A·f − f_blurred
        = (A−1)·f + (f − f_blurred)
    A = 1 → standard unsharp masking
    A > 1 → amplifies original + edges
    """
    blurred = cv2.GaussianBlur(img, (_ensure_odd(ksize), _ensure_odd(ksize)), sigma)
    img_f = img.astype(np.float32)
    blr_f = blurred.astype(np.float32)
    result = A * img_f - blr_f
    return np.clip(result, 0, 255).astype(np.uint8)


# ──────────────────────────────────────────────────────────────────────────────
# 3. Edge Detection
# ──────────────────────────────────────────────────────────────────────────────

def _to_gray_if_color(img):
    if len(img.shape) == 3:
        return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return img


def sobel_edge(img: np.ndarray) -> np.ndarray:
    """
    Sobel operator – uses 3×3 kernels for Gx and Gy:
      Gx = [[-1,0,1],[-2,0,2],[-1,0,1]]
      Gy = [[-1,-2,-1],[0,0,0],[1,2,1]]
    Gradient magnitude: G = sqrt(Gx²+Gy²)  ≈ |Gx|+|Gy|
    """
    gray = _to_gray_if_color(img)
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    magnitude = np.sqrt(gx**2 + gy**2)
    magnitude = np.clip(magnitude, 0, 255).astype(np.uint8)
    return cv2.cvtColor(magnitude, cv2.COLOR_GRAY2BGR)


def prewitt_edge(img: np.ndarray) -> np.ndarray:
    """
    Prewitt operator:
      Gx = [[-1,0,1],[-1,0,1],[-1,0,1]]
      Gy = [[-1,-1,-1],[0,0,0],[1,1,1]]
    Similar to Sobel but without centre-row weighting.
    """
    gray = _to_gray_if_color(img).astype(np.float32)
    kx = np.array([[-1, 0, 1], [-1, 0, 1], [-1, 0, 1]], dtype=np.float32)
    ky = np.array([[-1, -1, -1], [0, 0, 0], [1, 1, 1]], dtype=np.float32)
    gx = cv2.filter2D(gray, -1, kx)
    gy = cv2.filter2D(gray, -1, ky)
    magnitude = np.clip(np.sqrt(gx**2 + gy**2), 0, 255).astype(np.uint8)
    return cv2.cvtColor(magnitude, cv2.COLOR_GRAY2BGR)


def laplacian_edge(img: np.ndarray) -> np.ndarray:
    """
    Laplacian edge detection (2nd-order derivative):
    ∇²f highlights regions of rapid intensity change.
    """
    gray = _to_gray_if_color(img)
    lap = cv2.Laplacian(gray, cv2.CV_16S, ksize=3)
    lap_abs = cv2.convertScaleAbs(lap)
    return cv2.cvtColor(lap_abs, cv2.COLOR_GRAY2BGR)


def canny_edge(img: np.ndarray,
               low_thresh: int = 50,
               high_thresh: int = 150) -> np.ndarray:
    """
    Canny edge detector (multi-stage):
    1. Gaussian smoothing
    2. Gradient magnitude + direction
    3. Non-maximum suppression
    4. Double threshold + hysteresis
    """
    gray = _to_gray_if_color(img)
    edges = cv2.Canny(gray, low_thresh, high_thresh)
    return cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)


# ──────────────────────────────────────────────────────────────────────────────
# 4. Custom Kernel Convolution
# ──────────────────────────────────────────────────────────────────────────────

def custom_kernel_filter(img: np.ndarray, kernel: np.ndarray) -> np.ndarray:
    """
    Apply any user-defined kernel via 2D convolution.
    Kernel should be a 2D numpy float32 array.
    """
    if kernel.ndim != 2:
        raise ValueError("Kernel must be 2-D.")
    result = cv2.filter2D(img.astype(np.float32), -1, kernel)
    return np.clip(result, 0, 255).astype(np.uint8)
