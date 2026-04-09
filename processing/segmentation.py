"""Background segmentation and ROI processing"""
import cv2
import numpy as np
from scipy import ndimage

try:
    import mediapipe as mp
except ImportError:
    mp = None


def _prepare_segmentation_image(image):
    """Enhance local contrast and estimate highlight severity for robust segmentation."""
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    v = hsv[:, :, 2]
    s = hsv[:, :, 1]

    # Bright, low-saturation pixels usually indicate overexposed/backlit regions.
    highlight_mask = ((v > 225) & (s < 55)).astype(np.uint8)
    overexposure_score = float(np.count_nonzero(highlight_mask)) / float(highlight_mask.size)

    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)

    # Stronger CLAHE when image is highly overexposed.
    clip_limit = 4.0 if overexposure_score > 0.12 else 2.6
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(8, 8))
    l = clahe.apply(l)

    prepared = cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2BGR)
    prepared = cv2.bilateralFilter(prepared, 7, 45, 45)
    return prepared, overexposure_score


def _foreground_seed_from_border_contrast(image, border_ring, inner_lasso):
    """Estimate likely foreground by color contrast against border/background ring."""
    if cv2.countNonZero(border_ring) < 30 or cv2.countNonZero(inner_lasso) < 30:
        return np.zeros_like(inner_lasso)

    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB).astype(np.float32)
    bg_pixels = lab[border_ring > 0]
    if bg_pixels.shape[0] < 30:
        return np.zeros_like(inner_lasso)

    bg_mean = np.mean(bg_pixels, axis=0)
    bg_std = np.std(bg_pixels, axis=0)
    bg_std = np.maximum(bg_std, np.array([8.0, 6.0, 6.0], dtype=np.float32))

    z = (lab - bg_mean) / bg_std
    # Heavier weight on luminance difference for backlit photos.
    fg_score = (1.25 * z[:, :, 0] * z[:, :, 0]) + (z[:, :, 1] * z[:, :, 1]) + (z[:, :, 2] * z[:, :, 2])

    inside_vals = fg_score[inner_lasso > 0]
    if inside_vals.size < 30:
        return np.zeros_like(inner_lasso)

    thr = float(np.percentile(inside_vals, 68))
    seed = np.where((fg_score >= thr) & (inner_lasso > 0), 255, 0).astype(np.uint8)

    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    seed = cv2.morphologyEx(seed, cv2.MORPH_OPEN, k, iterations=1)
    seed = cv2.morphologyEx(seed, cv2.MORPH_CLOSE, k, iterations=1)
    return seed


def _second_pass_grabcut_refine(image, lasso_bin, initial_mask, iterations=2):
    """Run a second GrabCut pass seeded by an initial mask to detach leaked background."""
    if cv2.countNonZero(initial_mask) == 0:
        return initial_mask

    h, w = lasso_bin.shape[:2]
    gc_mask = np.full((h, w), cv2.GC_BGD, dtype=np.uint8)
    gc_mask[lasso_bin > 0] = cv2.GC_PR_BGD

    dil = cv2.dilate(initial_mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)), iterations=1)
    sure_fg = cv2.erode(initial_mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)), iterations=1)
    sure_bg = cv2.bitwise_and(lasso_bin, cv2.bitwise_not(dil))

    gc_mask[dil > 0] = cv2.GC_PR_FGD
    gc_mask[sure_bg > 0] = cv2.GC_BGD
    gc_mask[sure_fg > 0] = cv2.GC_FGD

    x, y, rw, rh = cv2.boundingRect(lasso_bin)
    bgd_model = np.zeros((1, 65), np.float64)
    fgd_model = np.zeros((1, 65), np.float64)

    try:
        cv2.grabCut(
            image,
            gc_mask,
            (x, y, rw, rh),
            bgd_model,
            fgd_model,
            iterCount=max(1, int(iterations)),
            mode=cv2.GC_INIT_WITH_MASK,
        )
    except cv2.error:
        return initial_mask

    refined = np.where(
        (gc_mask == cv2.GC_FGD) | (gc_mask == cv2.GC_PR_FGD),
        255,
        0,
    ).astype(np.uint8)
    refined = cv2.bitwise_and(refined, lasso_bin)

    if cv2.countNonZero(refined) == 0:
        return initial_mask
    return refined


def _trim_mask_halo(image, mask, bg_hint_mask=None, delta_thresh=20.0):
    """Remove a thin leaked halo where boundary color is too similar to local background."""
    if mask is None or cv2.countNonZero(mask) == 0:
        return mask

    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    inner = cv2.erode(mask, k, iterations=1)
    boundary = cv2.subtract(mask, inner)
    if cv2.countNonZero(boundary) < 20:
        return mask

    outer_shell = cv2.subtract(cv2.dilate(mask, k, iterations=1), mask)
    bg_region = outer_shell
    if bg_hint_mask is not None and cv2.countNonZero(bg_hint_mask) > 0:
        bg_region = cv2.bitwise_or(bg_region, bg_hint_mask)

    if cv2.countNonZero(bg_region) < 20:
        return mask

    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB).astype(np.float32)
    bg_vals = lab[bg_region > 0]
    if bg_vals.shape[0] < 20:
        return mask

    bg_mean = np.mean(bg_vals, axis=0)
    b_lab = lab[boundary > 0]
    if b_lab.shape[0] == 0:
        return mask

    d = np.sqrt(np.sum((b_lab - bg_mean) ** 2, axis=1))
    trim_pixels = (d < float(delta_thresh)).astype(np.uint8)
    if np.count_nonzero(trim_pixels) == 0:
        return mask

    trimmed_boundary = np.zeros_like(mask)
    by, bx = np.where(boundary > 0)
    trimmed_boundary[by[trim_pixels > 0], bx[trim_pixels > 0]] = 255

    refined = mask.copy()
    refined[trimmed_boundary > 0] = 0
    refined = cv2.morphologyEx(refined, cv2.MORPH_CLOSE, k, iterations=1)

    if cv2.countNonZero(refined) == 0:
        return mask
    return refined


def _auto_tighten_against_lasso_border(mask, border_ring, max_steps=2):
    """If mask still sticks to lasso border, tighten slightly until border contact is reduced."""
    if mask is None or cv2.countNonZero(mask) == 0:
        return mask
    if border_ring is None or cv2.countNonZero(border_ring) == 0:
        return mask

    work = mask.copy()
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    border_prox = cv2.dilate(border_ring, k, iterations=1)

    def _contact_ratio(m):
        area = max(1, cv2.countNonZero(m))
        touch = cv2.countNonZero(cv2.bitwise_and(m, border_prox))
        return float(touch) / float(area)

    ratio = _contact_ratio(work)
    target = 0.015
    steps = 0

    while ratio > target and steps < max_steps:
        candidate = cv2.erode(work, k, iterations=1)
        if cv2.countNonZero(candidate) == 0:
            break

        # Keep only strongest component after erosion to avoid scattered fragments.
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(candidate, connectivity=8)
        if num_labels > 1:
            best = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])
            candidate = np.where(labels == best, 255, 0).astype(np.uint8)

        new_ratio = _contact_ratio(candidate)
        if new_ratio >= ratio:
            break

        work = candidate
        ratio = new_ratio
        steps += 1

    return work


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


def segment_object_from_rect(image, rect, iterations=6, border_margin_ratio=0.08, tighten_iterations=1):
    """
    Segment the most likely object inside a user-drawn rectangle.

    Args:
        image: Input BGR image
        rect: (x1, y1, x2, y2) rectangle drawn by the user
        iterations: GrabCut refinement iterations

    Returns:
        Binary mask where the segmented object is white (255)
    """
    if image is None:
        raise ValueError("Image is required for segmentation")

    h, w = image.shape[:2]
    x1, y1, x2, y2 = rect

    x1 = max(0, min(int(x1), w - 1))
    y1 = max(0, min(int(y1), h - 1))
    x2 = max(x1 + 1, min(int(x2), w))
    y2 = max(y1 + 1, min(int(y2), h))

    rect_w = x2 - x1
    rect_h = y2 - y1
    if rect_w < 5 or rect_h < 5:
        raise ValueError("Selection is too small for object segmentation")

    work_img, overexposure_score = _prepare_segmentation_image(image)

    mask = np.full((h, w), cv2.GC_BGD, np.uint8)
    bgd_model = np.zeros((1, 65), np.float64)
    fgd_model = np.zeros((1, 65), np.float64)

    adaptive_margin = border_margin_ratio + (0.03 if overexposure_score > 0.12 else 0.0)
    margin_x = max(1, int(rect_w * adaptive_margin))
    margin_y = max(1, int(rect_h * adaptive_margin))
    inner_x1 = min(x2 - 1, x1 + margin_x)
    inner_y1 = min(y2 - 1, y1 + margin_y)
    inner_x2 = max(inner_x1 + 1, x2 - margin_x)
    inner_y2 = max(inner_y1 + 1, y2 - margin_y)

    # Help GrabCut by marking the selection border as probable background
    # and the center as probable foreground.
    mask[y1:y2, x1:x2] = cv2.GC_PR_BGD
    mask[inner_y1:inner_y2, inner_x1:inner_x2] = cv2.GC_PR_FGD

    try:
        cv2.grabCut(
            work_img,
            mask,
            (x1, y1, rect_w, rect_h),
            bgd_model,
            fgd_model,
            iterCount=max(1, int(iterations) + (2 if overexposure_score > 0.12 else 0)),
            mode=cv2.GC_INIT_WITH_MASK,
        )
    except cv2.error as exc:
        try:
            mask = np.zeros((h, w), np.uint8)
            cv2.grabCut(
                work_img,
                mask,
                (x1, y1, rect_w, rect_h),
                bgd_model,
                fgd_model,
                iterCount=max(1, int(iterations) + (2 if overexposure_score > 0.12 else 0)),
                mode=cv2.GC_INIT_WITH_RECT,
            )
        except cv2.error as fallback_exc:
            raise ValueError(f"GrabCut failed: {fallback_exc}") from fallback_exc

    binary_mask = np.where(
        (mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD),
        255,
        0,
    ).astype(np.uint8)

    if overexposure_score > 0.12:
        area_ratio = cv2.countNonZero(binary_mask) / max(1, (rect_w * rect_h))
        adj_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        if area_ratio > 0.70:
            binary_mask = cv2.erode(binary_mask, adj_kernel, iterations=1)
        elif area_ratio < 0.14:
            binary_mask = cv2.dilate(binary_mask, adj_kernel, iterations=1)

    rect_border = np.zeros((h, w), dtype=np.uint8)
    rect_border[y1:y2, x1:x2] = 255
    rect_border = cv2.subtract(rect_border, cv2.erode(rect_border, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)), iterations=1))
    binary_mask = _trim_mask_halo(work_img, binary_mask, bg_hint_mask=rect_border, delta_thresh=20.0)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    binary_mask = cv2.morphologyEx(binary_mask, cv2.MORPH_OPEN, kernel, iterations=1)
    binary_mask = cv2.morphologyEx(binary_mask, cv2.MORPH_CLOSE, kernel, iterations=2)

    if tighten_iterations > 0:
        binary_mask = cv2.erode(binary_mask, kernel, iterations=int(tighten_iterations))

    # Keep the strongest connected component to avoid loose background fragments.
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary_mask, connectivity=8)
    if num_labels > 1:
        largest_label = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])
        binary_mask = np.where(labels == largest_label, 255, 0).astype(np.uint8)

    if cv2.countNonZero(binary_mask) == 0:
        raise ValueError("No object could be segmented inside the selected area")

    return binary_mask


def segment_object_from_lasso(image, lasso_mask, iterations=3, tighten_iterations=0):
    """
    Segment object inside a user-drawn freehand contour.

    Args:
        image: Input BGR image
        lasso_mask: Binary mask built from traced contour (white = inside contour)
        iterations: GrabCut refinement iterations
        tighten_iterations: Optional erosion to tighten object boundary

    Returns:
        Binary mask where the segmented object is white (255)
    """
    if image is None:
        raise ValueError("Image is required for segmentation")
    if lasso_mask is None:
        raise ValueError("Lasso mask is required")

    h, w = image.shape[:2]
    if lasso_mask.shape[:2] != (h, w):
        raise ValueError("Lasso mask size must match image size")

    lasso_bin = np.where(lasso_mask > 0, 255, 0).astype(np.uint8)
    if cv2.countNonZero(lasso_bin) == 0:
        raise ValueError("Lasso mask is empty")

    work_img, overexposure_score = _prepare_segmentation_image(image)

    mask = np.full((h, w), cv2.GC_BGD, dtype=np.uint8)
    # Avoid forcing wide lasso interiors to foreground.
    # Start as probable background and let seeds promote true object regions.
    mask[lasso_bin > 0] = cv2.GC_PR_BGD

    # Build trimap from the traced contour:
    # - border ring near lasso edge: probable background
    # - center core: sure foreground
    ring_size = 13 if overexposure_score > 0.12 else 9
    ring_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (ring_size, ring_size))
    inner_lasso = cv2.erode(lasso_bin, ring_kernel, iterations=1)
    border_ring = cv2.subtract(lasso_bin, inner_lasso)
    mask[border_ring > 0] = cv2.GC_BGD

    # Build distance-based foreground zones so segmentation is less sensitive
    # to how loosely the contour was drawn.
    dist = cv2.distanceTransform(inner_lasso, cv2.DIST_L2, 5)
    max_dist = float(dist.max())
    if max_dist > 0:
        probable_fg = np.where(dist >= 0.20 * max_dist, 255, 0).astype(np.uint8)
        sure_fg = np.where(dist >= 0.45 * max_dist, 255, 0).astype(np.uint8)
    else:
        probable_fg = np.zeros_like(lasso_bin)
        sure_fg = np.zeros_like(lasso_bin)

    if cv2.countNonZero(probable_fg) > 0:
        mask[probable_fg > 0] = cv2.GC_PR_FGD

    if cv2.countNonZero(sure_fg) == 0:
        core_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (13, 13))
        sure_fg = cv2.erode(inner_lasso, core_kernel, iterations=1)
    if cv2.countNonZero(sure_fg) == 0:
        # Fallback for very small contour.
        sure_fg = cv2.erode(lasso_bin, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)), iterations=1)

    color_seed = _foreground_seed_from_border_contrast(work_img, border_ring, inner_lasso)
    if cv2.countNonZero(color_seed) > 0:
        mask[color_seed > 0] = cv2.GC_PR_FGD
        sure_fg = cv2.bitwise_or(sure_fg, color_seed)
    mask[sure_fg > 0] = cv2.GC_FGD

    x, y, rw, rh = cv2.boundingRect(lasso_bin)
    bgd_model = np.zeros((1, 65), np.float64)
    fgd_model = np.zeros((1, 65), np.float64)

    try:
        cv2.grabCut(
            work_img,
            mask,
            (x, y, rw, rh),
            bgd_model,
            fgd_model,
            iterCount=max(1, int(iterations) + (2 if overexposure_score > 0.12 else 0)),
            mode=cv2.GC_INIT_WITH_MASK,
        )
    except cv2.error as exc:
        raise ValueError(f"GrabCut failed: {exc}") from exc

    binary_mask = np.where(
        (mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD),
        255,
        0,
    ).astype(np.uint8)

    # Watershed refinement tends to respect strong image boundaries better
    # for cartoon/illustration edges.
    ws_img = cv2.GaussianBlur(work_img, (5, 5), 0)
    markers = np.zeros((h, w), dtype=np.int32)
    markers[lasso_bin == 0] = 1
    markers[border_ring > 0] = 1
    markers[sure_fg > 0] = 2
    markers = cv2.watershed(ws_img, markers)
    ws_mask = np.where(markers == 2, 255, 0).astype(np.uint8)

    # Intersect both estimations for a tighter contour.
    if cv2.countNonZero(ws_mask) > 0:
        merged = cv2.bitwise_and(binary_mask, ws_mask)
        if cv2.countNonZero(merged) > 0:
            binary_mask = merged

    # Keep result inside traced boundary while excluding the traced border itself.
    constraint_size = 7 if overexposure_score > 0.12 else 5
    constraint_lasso = cv2.erode(
        lasso_bin,
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (constraint_size, constraint_size)),
        iterations=1,
    )
    if cv2.countNonZero(constraint_lasso) == 0:
        constraint_lasso = lasso_bin

    binary_mask[border_ring > 0] = 0
    binary_mask = cv2.bitwise_and(binary_mask, constraint_lasso)

    if overexposure_score > 0.12:
        area_ratio = cv2.countNonZero(binary_mask) / max(1, cv2.countNonZero(lasso_bin))
        adj_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        if area_ratio > 0.72:
            binary_mask = cv2.erode(binary_mask, adj_kernel, iterations=1)
        elif area_ratio < 0.14:
            binary_mask = cv2.dilate(binary_mask, adj_kernel, iterations=1)
            binary_mask = cv2.morphologyEx(binary_mask, cv2.MORPH_CLOSE, adj_kernel, iterations=1)

    post_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    binary_mask = cv2.morphologyEx(binary_mask, cv2.MORPH_OPEN, post_kernel, iterations=1)
    binary_mask = cv2.morphologyEx(binary_mask, cv2.MORPH_CLOSE, post_kernel, iterations=2)

    if tighten_iterations > 0:
        binary_mask = cv2.erode(binary_mask, post_kernel, iterations=int(tighten_iterations))

    # Prefer the object component that is central and not connected to traced border.
    border_proximity = cv2.dilate(
        border_ring,
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)),
        iterations=1,
    )

    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary_mask, connectivity=8)
    if num_labels > 1:
        seed_m = cv2.moments(sure_fg)
        if seed_m["m00"] > 0:
            seed_cx = seed_m["m10"] / seed_m["m00"]
            seed_cy = seed_m["m01"] / seed_m["m00"]
        else:
            seed_cx = w / 2.0
            seed_cy = h / 2.0

        candidates = []
        for label_id in range(1, num_labels):
            area = int(stats[label_id, cv2.CC_STAT_AREA])
            if area < 80:
                continue

            comp_mask = (labels == label_id)
            overlap = int(np.count_nonzero(comp_mask & (sure_fg > 0)))
            color_overlap = int(np.count_nonzero(comp_mask & (color_seed > 0))) if cv2.countNonZero(color_seed) > 0 else 0
            touch_pixels = int(np.count_nonzero(comp_mask & (border_proximity > 0)))
            touches_border = touch_pixels > 0

            comp_m = cv2.moments(comp_mask.astype(np.uint8))
            if comp_m["m00"] > 0:
                comp_cx = comp_m["m10"] / comp_m["m00"]
                comp_cy = comp_m["m01"] / comp_m["m00"]
                center_dist = float(np.hypot(comp_cx - seed_cx, comp_cy - seed_cy))
            else:
                center_dist = 1e9

            # Priority: avoid border-connected regions, then maximize seed overlap and area.
            score = (not touches_border, overlap, color_overlap, -center_dist, area, -touch_pixels)
            candidates.append((score, label_id))

        if candidates:
            best_label = max(candidates, key=lambda t: t[0])[1]
            binary_mask = np.where(labels == best_label, 255, 0).astype(np.uint8)

    # One more refinement pass to peel off attached background chunks.
    binary_mask = _second_pass_grabcut_refine(
        work_img,
        constraint_lasso,
        binary_mask,
        iterations=2 if overexposure_score <= 0.12 else 3,
    )

    binary_mask = _trim_mask_halo(
        work_img,
        binary_mask,
        bg_hint_mask=border_ring,
        delta_thresh=20.0 if overexposure_score <= 0.12 else 24.0,
    )

    binary_mask = _auto_tighten_against_lasso_border(
        binary_mask,
        border_ring,
        max_steps=3 if overexposure_score <= 0.12 else 2,
    )

    binary_mask = cv2.morphologyEx(binary_mask, cv2.MORPH_OPEN, post_kernel, iterations=1)
    binary_mask = cv2.morphologyEx(binary_mask, cv2.MORPH_CLOSE, post_kernel, iterations=1)

    if cv2.countNonZero(binary_mask) == 0:
        raise ValueError("No object could be segmented inside the traced contour")

    return binary_mask


def apply_edge_blur(image, blur_strength=15):
    """Blur edges to blend ROI naturally"""
    kernel_size = blur_strength | 1  # Ensure odd number
    return cv2.GaussianBlur(image, (kernel_size, kernel_size), 0)
