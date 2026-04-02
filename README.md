# Image Editor — DIP Tool

> Digital Image Processing Tool | Enhance & Filter Photos  
> Academic Project | Digital Image Processing Course

---

## Quick Start

### Install

```bash
pip install -r requirements.txt
```

### Run

```bash
python main.py
```

---

## How to Use

### 1. **Load an Image**

- Click `Open Image`
- Select any image from your computer (PNG, JPG, BMP, TIFF, WebP)
- Image appears in the left panel

### 2. **Choose a Tool**

Pick from the left sidebar based on what you want to do:

#### **Quality Adjustment** — Make image look better

- **Auto Contrast** → Automatically improve brightness & contrast
- **Smart Contrast** → Better version (preserves local details)
- **Brightness Correction** → Adjust overall brightness
  - Darker ← | Normal | → Brighter
- **Brighten Dark Areas** → Bring out hidden details in shadows
- **Invert Colors** → Create a negative/inverse image
- **Fine-tune** → Manual brightness & contrast sliders

#### **Smooth & Denoise** — Remove noise & blur

Choose filter size (3, 5, 7, or 9):

- **Quick Smooth** → Simple blur (fast)
- **Gentle Smooth** → Natural blur (better quality)
- **Remove Spots** → Best for noisy photos (removes speckles)

#### **Sharpen & Enhance Details** — Make image crisper

- **Sharpen** → Quick edge enhancement
- **Smart Sharpen** → Control sharpening strength (slider)
- **Enhanced Sharpen** → Strong sharpening (slider)

#### **Detect Edges** — Find boundaries & contours

- **Auto Detect (Best)** → Smart edge detection
- **Sobel Edges** → Horizontal & vertical edges
- **Prewitt Edges** → Similar to Sobel
- **Laplacian Edges** → All-direction edges

#### **Test with Noise** — Add noise (for testing filters)

- **Add Spots** → Random white/black dots
- **Add Blur Noise** → Gaussian noise
- **Add Texture Noise** → Speckle/film grain

#### **Advanced** — Build custom filters

- Enter numbers in the 3×3 matrix
- Click `Apply Custom Kernel`

### 3. **View Results**

- **Split** view: Compare original (left) vs processed (right)
- **Original** view: See original image only
- **Processed** view: See result only

### 4. **Save Your Work**

- Click `Save Result`
- Choose filename & format (PNG or JPG)

---

## Demo Workflow

**Scenario 1: Noisy Photo → Clean Image**

1. Open image
2. Go to Test with Noise → Add a bit of noise (test)
3. Go to Smooth & Denoise → Apply "Remove Spots" with size 5-7
4. View result in Split mode

**Scenario 2: Dark Photo → Bright & Clear**

1. Open dark photo
2. Go to Quality Adjustment → Click "Auto Contrast"
3. If still dark: Use "Brightness Correction" slider
4. Go to Sharpen & Enhance Details → Apply "Smart Sharpen" (optional)

**Scenario 3: Find Edges**

1. Open photo
2. Go to Detect Edges → Click "Auto Detect (Best)"
3. Try other edge detectors to compare

---

## Features & Algorithms

### Quality Adjustment (Enhancement)

| Feature                   | Algorithm                            | Technical Name             | Purpose                                                       |
| ------------------------- | ------------------------------------ | -------------------------- | ------------------------------------------------------------- |
| **Auto Contrast**         | Global Histogram Equalization        | `histogram_equalization()` | Spread pixel values across full range → better contrast       |
| **Smart Contrast**        | CLAHE (Contrast Limited Adaptive HE) | `clahe_enhancement()`      | Adaptive histogram eq. on tiles → preserve local details      |
| **Brightness Correction** | Gamma Correction / Power-Law         | `gamma_correction(gamma)`  | s = (r/255)^(1/γ) × 255 <br> γ < 1 → brighter, γ > 1 → darker |
| **Brighten Dark Areas**   | Log Transform                        | `log_transform()`          | s = c × log(1 + r) → compress highlights, expand shadows      |
| **Invert Colors**         | Negative Transform                   | `negative_transform()`     | s = 255 - r → invert all pixel values                         |
| **Fine-tune**             | Linear brightness & contrast         | `brightness_contrast()`    | g = α·f + β (pixel-by-pixel)                                  |

### Smoothing & Denoising Filters

| Filter            | Algorithm           | Kernel                   | Best For                           |
| ----------------- | ------------------- | ------------------------ | ---------------------------------- |
| **Quick Smooth**  | Mean/Average Filter | All 1/(k²)               | Fast blur, general smoothing       |
| **Gentle Smooth** | Gaussian Blur       | Gaussian distribution    | Natural blur, less detail loss     |
| **Remove Spots**  | Median Filter       | Sort neighborhood values | Salt & pepper noise, impulse noise |

**How they work:**  
Convolution with kernel (3×3, 5×5, etc.) → replace each pixel with weighted average of neighbors

### Sharpening Filters

| Filter               | Algorithm       | Formula                 | Strength             |
| -------------------- | --------------- | ----------------------- | -------------------- |
| **Sharpen**          | Laplacian       | g = f - ∇²f             | Medium               |
| **Smart Sharpen**    | Unsharp Masking | g = f + k×(f - blurred) | Adjustable (0.5-3.0) |
| **Enhanced Sharpen** | High-Boost      | g = A×f - blurred       | Adjustable (1.0-5.0) |

**How they work:**  
Highlight edges by subtracting blurred version from original → brings out details

### Edge Detection

| Detector        | Algorithm           | Edge Type             | Method                                                      |
| --------------- | ------------------- | --------------------- | ----------------------------------------------------------- |
| **Auto Detect** | Canny Edge Detector | Multi-directional     | 4-stage: blur → gradient → non-max suppression → hysteresis |
| **Sobel**       | Sobel Operator      | Horizontal & vertical | Gradient computed via 3×3 kernels                           |
| **Prewitt**     | Prewitt Operator    | Similar to Sobel      | Slightly different kernel weights                           |
| **Laplacian**   | Laplacian Operator  | All directions        | 2nd derivative → finds sharp intensity changes              |

**How they work:**  
Find areas where pixel intensity changes rapidly (edges) using gradient operators

### Noise (for testing)

| Noise Type        | Formula                                | Characteristics                       |
| ----------------- | -------------------------------------- | ------------------------------------- |
| **Salt & Pepper** | Random 0 or 255 at `amount%` of pixels | Impulse noise (white dots/black dots) |
| **Gaussian**      | g(x,y) = f(x,y) + η, η~N(0,σ)          | Additive normal distribution          |
| **Speckle**       | g(x,y) = f(x,y) + f×η                  | Multiplicative (depends on signal)    |

---

## Project Structure

```
dip_tool/
├── main.py                    # GUI (CustomTkinter)
├── README.md
├── requirements.txt
└── processing/
    ├── __init__.py
    ├── enhancement.py         # Intensity transforms
    ├── filters.py             # Spatial filtering (convolution)
    └── noise.py               # Noise generation
```

---

## Technical Details

### Library Stack

- **OpenCV** (`cv2`) → Image I/O, matrix operations
- **NumPy** (`np`) → Numerical array operations
- **PIL/Pillow** → Image display in GUI
- **CustomTkinter** → Modern GUI framework
- **Matplotlib** → Histograms visualization

### Processing Pipeline

```
Input Image (BGR)
    ↓
Convert BGR → Grayscale (if needed)
    ↓
Apply kernel/transform (enhancement/filter)
    ↓
Normalize to [0, 255]
    ↓
Display & allow chaining operations
```

### Color Space

- **Input/Output**: BGR (OpenCV default)
- **Enhancement**: YCrCb for color images (process only Y channel → preserve color)
- **Display**: Convert BGR → RGB → PIL Image → Display

### Convolution (Spatial Filtering)

Each smoothing/sharpening filter uses **2D convolution**:

1. Slide kernel over image
2. Multiply kernel elements with image neighborhood
3. Sum products → output pixel
4. Repeat for entire image

---

## Learning Outcomes

This project demonstrates:

- Spatial domain image processing techniques
- Pixel-level transformations (enhancement)
- Neighborhood operations (filtering via convolution)
- Edge detection algorithms
- GUI programming in Python
- Real-time image processing visualization

---

## Demo Images

Recommended to test with:

- **Bright photo** → good for noise/sharpening
- **Dark photo** → test brightness correction
- **Noisy screenshot** → test denoising filters
- **Landscape** → test edge detection

---

## Tips

1. **Use Split view** for A/B comparison
2. **Start with small filter sizes (3-5)** → larger = more effect
3. **Add noise first** → then apply filter to see effectiveness
4. **Try multiple methods** on same image → see differences
5. **Check Histogram** → see before/after distribution

---

## References

Based on **Digital Image Processing** principles (Gonzalez & Woods):

- Chapter 3: Intensity Transformations
- Chapter 4: Spatial Filtering
- Chapter 10: Image Segmentation & Edge Detection

---

## License

Academic Project | Educational Use Only

---

**Author**: Student  
**Course**: Digital Image Processing  
**Year**: 2024-2025
