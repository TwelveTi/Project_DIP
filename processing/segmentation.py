"""Background segmentation and ROI processing"""
import cv2
import numpy as np
from scipy import ndimage

try:
    import mediapipe as mp
except ImportError:
    mp = None


def remove_background_selfie(image):
    """
    Remove background using MediaPipe Selfie Segmentation.
    Returns image with transparent background (RGBA).
    """
    if mp is None:
        raise ImportError("Install mediapipe: pip install mediapipe")
    
    # Check if mediapipe.solutions is available
    if not hasattr(mp, 'solutions'):
        raise ImportError(
            "MediaPipe installation incomplete. Please run:\n"
            "pip uninstall mediapipe -y && pip install mediapipe"
        )
    
    try:
        # Convert BGR to RGB
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        h, w = rgb.shape[:2]
        
        # Initialize selfie segmentation
        BG_COLOR = (255, 255, 255)
        selfie_segmentation = mp.solutions.selfie_segmentation.SelfieSegmentation(
            model_selection=0  # 0 for image, 1 for video (faster)
        )
    except AttributeError as e:
        raise ImportError(
            f"MediaPipe not properly installed. Error: {str(e)}\n"
            "Try: pip install --upgrade mediapipe"
        ) from e
    
    # Process image
    results = selfie_segmentation.process(rgb)
    mask = results.segmentation_mask
    
    # Threshold to get binary mask
    condition = np.stack((results.segmentation_mask,) * 3, axis=2) > 0.1
    output_image = np.where(condition, rgb, BG_COLOR)
    
    # Convert back to BGR and add alpha channel
    output_bgr = cv2.cvtColor(output_image.astype(np.uint8), cv2.COLOR_RGB2BGR)
    
    # Create mask as uint8
    mask_uint8 = (mask * 255).astype(np.uint8)
    
    # Apply morphological operations to clean up mask
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask_uint8 = cv2.morphologyEx(mask_uint8, cv2.MORPH_CLOSE, kernel, iterations=1)
    
    # Add alpha channel
    bgra = cv2.cvtColor(output_bgr, cv2.COLOR_BGR2BGRA)
    bgra[:, :, 3] = mask_uint8
    
    selfie_segmentation.close()
    return bgra


def remove_background_simple(image):
    """
    Simple background removal using color detection (for white/uniform backgrounds).
    Returns BGR image with transparent area (RGBA).
    """
    # Convert to HSV for better color detection
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    
    # Define white color range
    lower_white = np.array([0, 0, 200])
    upper_white = np.array([180, 50, 255])
    
    # Create mask
    mask = cv2.inRange(hsv, lower_white, upper_white)
    inv_mask = cv2.bitwise_not(mask)
    
    # Apply morphological operations
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    inv_mask = cv2.morphologyEx(inv_mask, cv2.MORPH_CLOSE, kernel, iterations=1)
    inv_mask = cv2.morphologyEx(inv_mask, cv2.MORPH_OPEN, kernel, iterations=1)
    
    # Add alpha channel
    bgra = cv2.cvtColor(image, cv2.COLOR_BGR2BGRA)
    bgra[:, :, 3] = inv_mask
    
    return bgra


def apply_to_roi(image, roi_mask, processing_func, *args, **kwargs):
    """
    Apply a processing function only to the selected ROI.
    
    Args:
        image: Input BGR image
        roi_mask: Binary mask where white = ROI area
        processing_func: Function to apply to ROI
        *args, **kwargs: Arguments to pass to processing_func
    
    Returns:
        Processed image with changes only in ROI
    """
    # Process full image
    processed = processing_func(image, *args, **kwargs)
    
    # Blend original and processed using mask
    result = image.copy()
    mask_inv = cv2.bitwise_not(roi_mask)
    
    # Apply: result = (processed & ROI_mask) | (original & ~ROI_mask)
    roi_processed = cv2.bitwise_and(processed, processed, mask=roi_mask)
    roi_original = cv2.bitwise_and(image, image, mask=mask_inv)
    result = cv2.add(roi_processed, roi_original)
    
    return result


def apply_edge_blur(image, blur_strength=15):
    """Blur edges to blend ROI naturally"""
    kernel_size = blur_strength | 1  # Ensure odd number
    return cv2.GaussianBlur(image, (kernel_size, kernel_size), 0)
