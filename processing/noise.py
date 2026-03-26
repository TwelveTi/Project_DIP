"""
Noise Generation for DIP demonstrations.
Covers: Salt & Pepper, Gaussian, Speckle, Periodic
"""

import cv2
import numpy as np


def add_salt_pepper_noise(img: np.ndarray, amount: float = 0.05,
                           salt_ratio: float = 0.5) -> np.ndarray:
    """
    Salt-and-Pepper (Impulse) Noise.
    amount     : fraction of total pixels corrupted
    salt_ratio : fraction of corrupted pixels set to 255 (white)
                 remainder set to 0 (black)
    """
    out = img.copy()
    total = img.size // (1 if len(img.shape) == 2 else img.shape[2])
    n_corrupt = int(amount * total)

    # Salt (white)
    n_salt = int(n_corrupt * salt_ratio)
    coords = [np.random.randint(0, d, n_salt) for d in img.shape[:2]]
    out[coords[0], coords[1]] = 255

    # Pepper (black)
    n_pepper = n_corrupt - n_salt
    coords = [np.random.randint(0, d, n_pepper) for d in img.shape[:2]]
    out[coords[0], coords[1]] = 0

    return out


def add_gaussian_noise(img: np.ndarray,
                        mean: float = 0,
                        sigma: float = 25.0) -> np.ndarray:
    """
    Additive Gaussian (Normal) Noise:
      g(x,y) = f(x,y) + η   where η ~ N(mean, σ²)
    σ controls noise strength.
    """
    noise = np.random.normal(mean, sigma, img.shape).astype(np.float32)
    noisy = img.astype(np.float32) + noise
    return np.clip(noisy, 0, 255).astype(np.uint8)


def add_speckle_noise(img: np.ndarray, amount: float = 0.05) -> np.ndarray:
    """
    Multiplicative (Speckle) Noise:
      g(x,y) = f(x,y) + f(x,y) · η   where η ~ U(-amount, amount)
    Common in SAR / ultrasound imagery.
    """
    noise = np.random.uniform(-amount, amount, img.shape).astype(np.float32)
    noisy = img.astype(np.float32) + img.astype(np.float32) * noise
    return np.clip(noisy, 0, 255).astype(np.uint8)


def add_periodic_noise(img: np.ndarray,
                        freq: float = 0.1,
                        amplitude: float = 30.0) -> np.ndarray:
    """
    Sinusoidal (Periodic) Noise:
      η(x,y) = A · sin(2π · f · x)
    Demonstrates noise best removed in frequency domain (shown here for comparison).
    """
    h, w = img.shape[:2]
    x = np.arange(w)
    stripe = (amplitude * np.sin(2 * np.pi * freq * x)).astype(np.float32)
    noise = np.tile(stripe, (h, 1))

    if len(img.shape) == 3:
        noise = noise[:, :, np.newaxis]

    noisy = img.astype(np.float32) + noise
    return np.clip(noisy, 0, 255).astype(np.uint8)
