import customtkinter as ctk
from tkinter import filedialog, messagebox
import cv2
import numpy as np
from PIL import Image, ImageTk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib
matplotlib.use("TkAgg")

from processing.enhancement import (
    histogram_equalization, clahe_enhancement,
    gamma_correction, contrast_stretching,
    log_transform, power_law_transform,
    negative_transform, brightness_contrast,
    enhance_blurry_image, reduce_glare_exposure,
    anti_backlight_enhancement
)
from processing.filters import (
    mean_filter, gaussian_filter, median_filter,
    laplacian_sharpen, unsharp_masking, high_boost_filter,
    sobel_edge, prewitt_edge, laplacian_edge, canny_edge,
    custom_kernel_filter
)
from processing.noise import (
    add_salt_pepper_noise, add_gaussian_noise,
    add_speckle_noise, add_periodic_noise
)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class DIPTool(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("DIP Tool — Image Enhancement & Spatial Filtering")
        self.geometry("1400x860")
        self.minsize(1200, 720)

        self.original_image = None   # numpy BGR
        self.current_image = None    # numpy BGR (after processing)
        self.display_mode = "split"  # split | original | processed

        self._build_ui()

    # ──────────────────────────────────────────────
    # UI LAYOUT
    # ──────────────────────────────────────────────
    def _build_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ── Left sidebar ──────────────────────────
        self.sidebar = ctk.CTkScrollableFrame(self, width=300, corner_radius=0,
                                               fg_color=("#1a1a2e", "#0f0f1a"))
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        ctk.CTkLabel(self.sidebar, text="� Image Editor",
                     font=ctk.CTkFont(size=22, weight="bold"),
                     text_color="#00d4ff").pack(pady=(18, 4))
        ctk.CTkLabel(self.sidebar, text="Enhance & Filter Photos",
                     font=ctk.CTkFont(size=11), text_color="#888").pack(pady=(0, 16))

        # File buttons
        self._section("📂 File")
        ctk.CTkButton(self.sidebar, text="Open Image", command=self.open_image,
                      fg_color="#0066cc", hover_color="#0055aa").pack(fill="x", padx=12, pady=3)
        ctk.CTkButton(self.sidebar, text="Save Result", command=self.save_image,
                      fg_color="#006633", hover_color="#005522").pack(fill="x", padx=12, pady=3)
        ctk.CTkButton(self.sidebar, text="Reset to Original", command=self.reset_image,
                      fg_color="#663300", hover_color="#552200").pack(fill="x", padx=12, pady=(3, 10))

        # ── Enhancement ───────────────────────────
        self._section("Quality Adjustment")

        # Auto contrast
        ctk.CTkButton(self.sidebar, text="Auto Contrast",
                      command=self.apply_histeq,
                      fg_color="#1e5f3f", hover_color="#2a7f5f").pack(fill="x", padx=12, pady=2)
        ctk.CTkLabel(self.sidebar, text="Automatically improve contrast",
                     font=ctk.CTkFont(size=9), text_color="#777").pack(anchor="w", padx=14, pady=(0, 2))
        
        ctk.CTkButton(self.sidebar, text="Smart Contrast (CLAHE)",
                      command=self.apply_clahe,
                      fg_color="#1e5f3f", hover_color="#2a7f5f").pack(fill="x", padx=12, pady=2)
        ctk.CTkLabel(self.sidebar, text="Preserve local details",
                     font=ctk.CTkFont(size=9), text_color="#777").pack(anchor="w", padx=14, pady=(0, 8))

        # Brightness Correction
        ctk.CTkLabel(self.sidebar, text="Brightness Correction", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=14, pady=(8, 0))
        self.gamma_slider = ctk.CTkSlider(self.sidebar, from_=0.1, to=5.0, number_of_steps=49,
                                           command=self._on_gamma_change)
        self.gamma_slider.set(1.0)
        self.gamma_slider.pack(fill="x", padx=12, pady=2)
        self.gamma_label = ctk.CTkLabel(self.sidebar, text="← Darker  |  Normal  |  Brighter →", font=ctk.CTkFont(size=10))
        self.gamma_label.pack(anchor="w", padx=14)
        ctk.CTkButton(self.sidebar, text="Apply",
                      command=self.apply_gamma,
                      fg_color="#1e3f5f", hover_color="#2a5f7f").pack(fill="x", padx=12, pady=(2, 8))

        # Other adjustments
        ctk.CTkButton(self.sidebar, text="Brighten Dark Areas",
                      command=self.apply_log,
                      fg_color="#5f3f1e", hover_color="#7f5f2a").pack(fill="x", padx=12, pady=2)
        ctk.CTkLabel(self.sidebar, text="Bring out hidden details",
                     font=ctk.CTkFont(size=9), text_color="#777").pack(anchor="w", padx=14, pady=(0, 4))
        
        ctk.CTkButton(self.sidebar, text="Invert Colors",
                      command=self.apply_negative,
                      fg_color="#5f1e3f", hover_color="#7f2a5f").pack(fill="x", padx=12, pady=2)
        ctk.CTkLabel(self.sidebar, text="Create negative image",
                     font=ctk.CTkFont(size=9), text_color="#777").pack(anchor="w", padx=14, pady=(0, 4))

        ctk.CTkButton(self.sidebar, text="🔍 Enhance Blurry Image",
                      command=self.apply_enhance_blurry,
                      fg_color="#3f5f1e", hover_color="#5f7f2a").pack(fill="x", padx=12, pady=2)
        ctk.CTkLabel(self.sidebar, text="Sharpen & clarify motion blur",
                     font=ctk.CTkFont(size=9), text_color="#777").pack(anchor="w", padx=14, pady=(0, 4))

        ctk.CTkButton(self.sidebar, text="☀️ Reduce Glare",
                      command=self.apply_reduce_glare,
                      fg_color="#5f5f1e", hover_color="#7f7f2a").pack(fill="x", padx=12, pady=2)
        ctk.CTkLabel(self.sidebar, text="Fix overexposed bright areas",
                     font=ctk.CTkFont(size=9), text_color="#777").pack(anchor="w", padx=14, pady=(0, 4))

        ctk.CTkButton(self.sidebar, text="🌅 Anti-Backlight",
                      command=self.apply_anti_backlight,
                      fg_color="#5f3f1e", hover_color="#7f5f2a").pack(fill="x", padx=12, pady=2)
        ctk.CTkLabel(self.sidebar, text="Balance shadows & highlights",
                     font=ctk.CTkFont(size=9), text_color="#777").pack(anchor="w", padx=14, pady=(0, 8))

        # Brightness & Contrast sliders
        ctk.CTkLabel(self.sidebar, text="Fine-tune", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=14, pady=(8, 0))
        self.bright_slider = ctk.CTkSlider(self.sidebar, from_=-100, to=100, number_of_steps=200,
                                            command=self._on_brightness_change)
        self.bright_slider.set(0)
        self.bright_slider.pack(fill="x", padx=12, pady=2)
        ctk.CTkLabel(self.sidebar, text="Brightness", font=ctk.CTkFont(size=10)).pack(anchor="w", padx=14)
        self.contrast_slider = ctk.CTkSlider(self.sidebar, from_=0.1, to=3.0, number_of_steps=59,
                                             command=self._on_contrast_change)
        self.contrast_slider.set(1.0)
        self.contrast_slider.pack(fill="x", padx=12, pady=2)
        ctk.CTkLabel(self.sidebar, text="Contrast", font=ctk.CTkFont(size=10)).pack(anchor="w", padx=14)
        ctk.CTkLabel(self.sidebar, text="Real-time preview", font=ctk.CTkFont(size=9, weight="bold"), text_color="#00d4ff").pack(anchor="w", padx=14, pady=(0, 8))

        # ── Noise ─────────────────────────────────
        self._section("Test with Noise")
        ctk.CTkLabel(self.sidebar, text="(for testing filters)",
                     font=ctk.CTkFont(size=9), text_color="#777").pack(anchor="w", padx=14, pady=(0, 4))
        ctk.CTkLabel(self.sidebar, text="Intensity", font=ctk.CTkFont(size=11)).pack(anchor="w", padx=14)
        self.noise_amount = ctk.CTkSlider(self.sidebar, from_=0.01, to=0.2, number_of_steps=19)
        self.noise_amount.set(0.05)
        self.noise_amount.pack(fill="x", padx=12, pady=2)
        ctk.CTkButton(self.sidebar, text="Add Spots (Salt & Pepper)",
                      command=self.add_salt_pepper).pack(fill="x", padx=12, pady=2)
        ctk.CTkButton(self.sidebar, text="Add Blur Noise (Gaussian)",
                      command=self.add_gaussian).pack(fill="x", padx=12, pady=2)
        ctk.CTkButton(self.sidebar, text="Add Texture Noise (Speckle)",
                      command=self.add_speckle).pack(fill="x", padx=12, pady=(2, 8))

        # ── Smoothing Filters ─────────────────────
        self._section("Smooth & Denoise")
        ctk.CTkLabel(self.sidebar, text="Filter Size", font=ctk.CTkFont(size=11)).pack(anchor="w", padx=14, pady=(4, 0))
        self.kernel_var = ctk.StringVar(value="3")
        ks_row = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        ks_row.pack(fill="x", padx=12, pady=2)
        for k in ["3", "5", "7", "9"]:
            ctk.CTkRadioButton(ks_row, text=k, variable=self.kernel_var, value=k,
                               width=44).pack(side="left")

        ctk.CTkButton(self.sidebar, text="Quick Smooth",
                      command=self.apply_mean,
                      fg_color="#1e5f3f", hover_color="#2a7f5f").pack(fill="x", padx=12, pady=2)
        ctk.CTkLabel(self.sidebar, text="Simple blur",
                     font=ctk.CTkFont(size=9), text_color="#777").pack(anchor="w", padx=14, pady=(0, 2))
        
        ctk.CTkButton(self.sidebar, text="Gentle Smooth",
                      command=self.apply_gaussian,
                      fg_color="#1e5f3f", hover_color="#2a7f5f").pack(fill="x", padx=12, pady=2)
        ctk.CTkLabel(self.sidebar, text="Natural looking",
                     font=ctk.CTkFont(size=9), text_color="#777").pack(anchor="w", padx=14, pady=(0, 2))
        
        ctk.CTkButton(self.sidebar, text="Remove Spots",
                      command=self.apply_median,
                      fg_color="#1e5f3f", hover_color="#2a7f5f").pack(fill="x", padx=12, pady=2)
        ctk.CTkLabel(self.sidebar, text="Best for noisy images",
                     font=ctk.CTkFont(size=9), text_color="#777").pack(anchor="w", padx=14, pady=(0, 8))

        # ── Sharpening ────────────────────────────
        self._section("Sharpen & Enhance Details")
        
        ctk.CTkButton(self.sidebar, text="Sharpen",
                      command=self.apply_laplacian_sharp,
                      fg_color="#5f4f1e", hover_color="#7f6f2a").pack(fill="x", padx=12, pady=2)
        ctk.CTkLabel(self.sidebar, text="Bring out edges",
                     font=ctk.CTkFont(size=9), text_color="#777").pack(anchor="w", padx=14, pady=(0, 2))

        ctk.CTkButton(self.sidebar, text="Unsharp Masking",
                      command=self.apply_unsharp,
                      fg_color="#5f4f1e", hover_color="#7f6f2a").pack(fill="x", padx=12, pady=2)
        ctk.CTkLabel(self.sidebar, text="Smart sharpening with slider",
                     font=ctk.CTkFont(size=9), text_color="#777").pack(anchor="w", padx=14, pady=(0, 4))

        ctk.CTkLabel(self.sidebar, text="Smart Sharpen", font=ctk.CTkFont(size=11)).pack(anchor="w", padx=14, pady=(6, 0))
        self.unsharp_k = ctk.CTkSlider(self.sidebar, from_=0.5, to=3.0, number_of_steps=25,
                                       command=lambda v: self.apply_unsharp())
        self.unsharp_k.set(1.5)
        self.unsharp_k.pack(fill="x", padx=12, pady=2)
        self.unsharp_label = ctk.CTkLabel(self.sidebar, text="Strength: 1.5", font=ctk.CTkFont(size=9))
        self.unsharp_label.pack(anchor="w", padx=14, pady=(2, 0))
        ctk.CTkLabel(self.sidebar, text="Move slider for real-time preview", font=ctk.CTkFont(size=9, weight="bold"), text_color="#00d4ff").pack(anchor="w", padx=14, pady=(0, 6))

        ctk.CTkLabel(self.sidebar, text="Enhanced Sharpen", font=ctk.CTkFont(size=11)).pack(anchor="w", padx=14, pady=(6, 0))
        self.highboost_a = ctk.CTkSlider(self.sidebar, from_=1.0, to=5.0, number_of_steps=40,
                                         command=lambda v: self.apply_highboost())
        self.highboost_a.set(2.0)
        self.highboost_a.pack(fill="x", padx=12, pady=2)
        self.highboost_label = ctk.CTkLabel(self.sidebar, text="Intensity: 2.0", font=ctk.CTkFont(size=9))
        self.highboost_label.pack(anchor="w", padx=14, pady=(2, 0))
        ctk.CTkLabel(self.sidebar, text="Move slider for real-time preview", font=ctk.CTkFont(size=9, weight="bold"), text_color="#00d4ff").pack(anchor="w", padx=14, pady=(0, 8))

        # ── Edge Detection ────────────────────────
        self._section("Detect Edges")
        ctk.CTkButton(self.sidebar, text="Auto Detect (Best)",
                      command=self.apply_canny,
                      fg_color="#5f1f4f", hover_color="#7f2f6f").pack(fill="x", padx=12, pady=2)
        ctk.CTkLabel(self.sidebar, text="Canny algorithm",
                     font=ctk.CTkFont(size=9), text_color="#777").pack(anchor="w", padx=14, pady=(0, 4))
        
        ctk.CTkButton(self.sidebar, text="Sobel Edges",
                      command=self.apply_sobel,
                      fg_color="#5f1f4f", hover_color="#7f2f6f").pack(fill="x", padx=12, pady=2)
        
        ctk.CTkButton(self.sidebar, text="Prewitt Edges",
                      command=self.apply_prewitt,
                      fg_color="#5f1f4f", hover_color="#7f2f6f").pack(fill="x", padx=12, pady=2)
        
        ctk.CTkButton(self.sidebar, text="Laplacian Edges",
                      command=self.apply_laplacian_edge,
                      fg_color="#5f1f4f", hover_color="#7f2f6f").pack(fill="x", padx=12, pady=(2, 8))

        # ── Custom Kernel ─────────────────────────
        self._section("Advanced (Custom Kernel)")
        ctk.CTkLabel(self.sidebar, text="Built your own 3×3 filter",
                     font=ctk.CTkFont(size=9), text_color="#777").pack(anchor="w", padx=14, pady=(0, 4))
        self.kernel_entries = []
        for r in range(3):
            row_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
            row_frame.pack(padx=12, pady=1)
            row_entries = []
            for c in range(3):
                default = "1" if r == 1 and c == 1 else "0"
                e = ctk.CTkEntry(row_frame, width=52, justify="center")
                e.insert(0, default)
                e.pack(side="left", padx=2)
                row_entries.append(e)
            self.kernel_entries.append(row_entries)
        ctk.CTkButton(self.sidebar, text="Apply Custom Kernel",
                      command=self.apply_custom_kernel,
                      fg_color="#4f4f1e", hover_color="#6f6f2a").pack(fill="x", padx=12, pady=(4, 8))

        # ── Histogram view ────────────────────────
        self._section("📊 Histogram")
        ctk.CTkButton(self.sidebar, text="Show Histogram",
                      command=self.show_histogram).pack(fill="x", padx=12, pady=2)

        # ── Right main area ───────────────────────
        self.main_area = ctk.CTkFrame(self, fg_color=("#111122", "#08080f"))
        self.main_area.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        self.main_area.grid_rowconfigure(1, weight=1)
        self.main_area.grid_columnconfigure(0, weight=1)

        # Top toolbar
        toolbar = ctk.CTkFrame(self.main_area, height=48, fg_color=("#1a1a2e", "#0f0f1a"))
        toolbar.grid(row=0, column=0, sticky="ew", padx=0, pady=0)

        ctk.CTkLabel(toolbar, text="View Mode:", font=ctk.CTkFont(size=12)).pack(side="left", padx=10)
        for label, val in [("Split", "split"), ("Original", "original"), ("Processed", "processed")]:
            ctk.CTkButton(toolbar, text=label, width=90,
                          command=lambda v=val: self.set_view_mode(v),
                          fg_color="#1e3a5f", hover_color="#2a5080").pack(side="left", padx=4, pady=6)

        self.status_label = ctk.CTkLabel(toolbar, text="No image loaded",
                                          font=ctk.CTkFont(size=11), text_color="#888")
        self.status_label.pack(side="right", padx=14)

        # Canvas area
        self.canvas_frame = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.canvas_frame.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        self.canvas_frame.grid_rowconfigure(1, weight=1)
        self.canvas_frame.grid_columnconfigure(0, weight=1)
        self.canvas_frame.grid_columnconfigure(1, weight=1)

        self.label_orig = ctk.CTkLabel(self.canvas_frame, text="Original",
                                        font=ctk.CTkFont(size=13, weight="bold"),
                                        text_color="#aaa")
        self.label_orig.grid(row=0, column=0, pady=(4, 0))
        self.label_proc = ctk.CTkLabel(self.canvas_frame, text="Processed",
                                        font=ctk.CTkFont(size=13, weight="bold"),
                                        text_color="#00d4ff")
        self.label_proc.grid(row=0, column=1, pady=(4, 0))

        self.img_orig = ctk.CTkLabel(self.canvas_frame, text="Open an image to begin",
                                      fg_color=("#0d0d1f", "#050510"), corner_radius=8)
        self.img_orig.grid(row=1, column=0, sticky="nsew", padx=2, pady=2)
        self.img_proc = ctk.CTkLabel(self.canvas_frame, text="",
                                      fg_color=("#0d0d1f", "#050510"), corner_radius=8)
        self.img_proc.grid(row=1, column=1, sticky="nsew", padx=2, pady=2)

        self.bind("<Configure>", self._on_resize)

    def _section(self, title):
        ctk.CTkLabel(self.sidebar, text=title,
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="#00d4ff").pack(anchor="w", padx=12, pady=(14, 2))
        ctk.CTkFrame(self.sidebar, height=1, fg_color="#333366").pack(fill="x", padx=12, pady=(0, 4))

    # ──────────────────────────────────────────────
    # FILE OPS
    # ──────────────────────────────────────────────
    def open_image(self):
        path = filedialog.askopenfilename(
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.tiff *.webp"), ("All", "*.*")])
        if not path:
            return
        img = cv2.imread(path)
        if img is None:
            messagebox.showerror("Error", "Cannot read image.")
            return
        self.original_image = img.copy()
        self.current_image = img.copy()
        h, w = img.shape[:2]
        self.status_label.configure(text=f"{w}×{h} px  |  {path.split('/')[-1]}")
        self.refresh_display()

    def save_image(self):
        if self.current_image is None:
            messagebox.showwarning("Warning", "No processed image.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".png",
                                             filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg")])
        if path:
            cv2.imwrite(path, self.current_image)
            messagebox.showinfo("Saved", f"Image saved to:\n{path}")

    def reset_image(self):
        if self.original_image is not None:
            self.current_image = self.original_image.copy()
            self.refresh_display()
            self.status_label.configure(text="Reset to original")

    # ──────────────────────────────────────────────
    # DISPLAY
    # ──────────────────────────────────────────────
    def set_view_mode(self, mode):
        self.display_mode = mode
        self.refresh_display()

    def refresh_display(self):
        if self.original_image is None:
            return
        
        # Dùng kích thước cửa sổ chính thay vì canvas_frame
        win_w = self.winfo_width()
        win_h = self.winfo_height()
        
        sidebar_w = 310  # chiều rộng sidebar
        toolbar_h = 60   # chiều cao toolbar
        
        available_w = max(win_w - sidebar_w, 800)
        available_h = max(win_h - toolbar_h - 10, 700)  # trừ toolbar + label
        
        w = max(available_w // 2 - 8, 400)
        h = max(available_h, 750)

        if self.display_mode == "split":
            self.label_orig.grid()
            self.img_proc.grid()
            self.label_proc.grid()
            self._show_cv(self.img_orig, self.original_image, w, h)
            self._show_cv(self.img_proc, self.current_image, w, h)
        elif self.display_mode == "original":
            self.label_orig.grid()
            self.img_proc.grid_remove()
            self.label_proc.grid_remove()
            self._show_cv(self.img_orig, self.original_image, w * 2, h)
        else:
            self.label_orig.grid_remove()
            self.img_orig.grid_remove() if False else None
            self.label_proc.grid()
            self.img_proc.grid()
            self._show_cv(self.img_proc, self.current_image, w * 2, h)

    def _show_cv(self, label_widget, bgr_img, max_w, max_h):
        rgb = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2RGB)
        pil = Image.fromarray(rgb)
        
        # Tính tỉ lệ scale để fit vào max_w x max_h (cả phóng to lẫn thu nhỏ)
        orig_w, orig_h = pil.size
        scale = min(max_w / orig_w, max_h / orig_h)
        new_w = int(orig_w * scale)
        new_h = int(orig_h * scale)
        pil = pil.resize((new_w, new_h), Image.LANCZOS)
        
        ctk_img = ctk.CTkImage(light_image=pil, dark_image=pil, size=pil.size)
        label_widget.configure(image=ctk_img, text="")
        label_widget._image_ref = ctk_img  # prevent GC

    def _on_resize(self, event):
        self.after(80, self.refresh_display)

    def _on_gamma_change(self, val):
        gamma_val = float(val)
        if gamma_val < 1.0:
            status = "← Darker"
        elif gamma_val > 1.0:
            status = "Brighter →"
        else:
            status = "Normal"
        self.gamma_label.configure(text=f"{status}  (γ = {gamma_val:.2f})")
        self.apply_gamma()

    def _on_brightness_change(self, val):
        """Real-time preview for brightness adjustment"""
        self.apply_brightness_contrast()

    def _on_contrast_change(self, val):
        """Real-time preview for contrast adjustment"""
        self.apply_brightness_contrast()

    def _on_unsharp_change(self, val):
        """Real-time preview for unsharp masking"""
        self.apply_unsharp()

    def _on_highboost_change(self, val):
        """Real-time preview for high boost filter"""
        self.apply_highboost()

    # ──────────────────────────────────────────────
    # GUARD
    # ──────────────────────────────────────────────
    def _check(self):
        if self.current_image is None:
            messagebox.showwarning("Warning", "Please open an image first.")
            return False
        return True

    def _apply(self, fn, *args, **kwargs):
        if not self._check():
            return
        try:
            # Apply effect on current_image to preserve previous changes
            result = fn(self.current_image, *args, **kwargs)
            self.current_image = result
            self.refresh_display()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ──────────────────────────────────────────────
    # ENHANCEMENT
    # ──────────────────────────────────────────────
    def apply_histeq(self):      self._apply(histogram_equalization)
    def apply_clahe(self):       self._apply(clahe_enhancement)
    def apply_log(self):         self._apply(log_transform)
    def apply_negative(self):    self._apply(negative_transform)

    def apply_gamma(self):
        g = self.gamma_slider.get()
        self._apply(gamma_correction, gamma=g)

    def apply_contrast_stretch(self):
        try:
            rmin = int(self.cs_min.get() or 0)
            rmax = int(self.cs_max.get() or 255)
        except ValueError:
            messagebox.showerror("Error", "Enter valid integer values for r_min and r_max.")
            return
        self._apply(contrast_stretching, r_min=rmin, r_max=rmax)

    def apply_brightness_contrast(self):
        b = int(self.bright_slider.get())
        c = self.contrast_slider.get()
        self._apply(brightness_contrast, brightness=b, contrast=c)

    def apply_enhance_blurry(self):
        clahe_clip = 3.0
        sharpen_strength = 2.0
        self._apply(enhance_blurry_image, clahe_clip=clahe_clip, sharpen_strength=sharpen_strength)

    def apply_reduce_glare(self):
        self._apply(reduce_glare_exposure, gamma=1.5, clahe_clip=2.5, highlights_recover=0.4)

    def apply_anti_backlight(self):
        self._apply(anti_backlight_enhancement, shadow_boost=1.3, highlight_reduce=0.7)

    # ──────────────────────────────────────────────
    # NOISE
    # ──────────────────────────────────────────────
    def add_salt_pepper(self):
        amt = self.noise_amount.get()
        self._apply(add_salt_pepper_noise, amount=amt)

    def add_gaussian(self):
        amt = self.noise_amount.get()
        self._apply(add_gaussian_noise, sigma=amt * 255)

    def add_speckle(self):
        amt = self.noise_amount.get()
        self._apply(add_speckle_noise, amount=amt)

    # ──────────────────────────────────────────────
    # FILTERS
    # ──────────────────────────────────────────────
    def _ksize(self):
        k = int(self.kernel_var.get())
        return k

    def apply_mean(self):      self._apply(mean_filter,     ksize=self._ksize())
    def apply_gaussian(self):  self._apply(gaussian_filter, ksize=self._ksize())
    def apply_median(self):    self._apply(median_filter,   ksize=self._ksize())

    def apply_laplacian_sharp(self): self._apply(laplacian_sharpen)
    def apply_sobel(self):           self._apply(sobel_edge)
    def apply_prewitt(self):         self._apply(prewitt_edge)
    def apply_laplacian_edge(self):  self._apply(laplacian_edge)
    def apply_canny(self):           self._apply(canny_edge)

    def apply_unsharp(self):
        k = self.unsharp_k.get()
        self.unsharp_label.configure(text=f"Strength: {k:.2f}")
        self._apply(unsharp_masking, k=k)

    def apply_highboost(self):
        a = self.highboost_a.get()
        self.highboost_label.configure(text=f"Intensity: {a:.2f}")
        self._apply(high_boost_filter, A=a)

    def apply_custom_kernel(self):
        if not self._check():
            return
        try:
            matrix = []
            for row in self.kernel_entries:
                matrix.append([float(e.get()) for e in row])
            kernel = np.array(matrix, dtype=np.float32)
        except ValueError:
            messagebox.showerror("Error", "All kernel cells must be numbers.")
            return
        self._apply(custom_kernel_filter, kernel=kernel)

    # ──────────────────────────────────────────────
    # HISTOGRAM
    # ──────────────────────────────────────────────
    def show_histogram(self):
        if not self._check():
            return
        win = ctk.CTkToplevel(self)
        win.title("Histogram Comparison")
        win.geometry("860x420")
        win.configure(fg_color="#0a0a1a")

        fig, axes = plt.subplots(1, 2, figsize=(10, 4), facecolor="#0a0a1a")
        colors_bgr = ['#3399ff', '#00cc66', '#ff4444']
        labels = ['Blue', 'Green', 'Red']

        for ax, img, title in zip(axes,
                                   [self.original_image, self.current_image],
                                   ["Original", "Processed"]):
            ax.set_facecolor("#0d0d1f")
            ax.set_title(title, color="#00d4ff", fontsize=13)
            ax.tick_params(colors="#888")
            for spine in ax.spines.values():
                spine.set_edgecolor("#333")
            if len(img.shape) == 2:
                ax.plot(cv2.calcHist([img], [0], None, [256], [0, 256]),
                        color="#00d4ff", linewidth=1.2)
            else:
                for i, (c, lbl) in enumerate(zip(colors_bgr, labels)):
                    hist = cv2.calcHist([img], [i], None, [256], [0, 256])
                    ax.plot(hist, color=c, linewidth=1.2, label=lbl, alpha=0.85)
                ax.legend(facecolor="#111", labelcolor="white", fontsize=9)
            ax.set_xlim([0, 256])

        plt.tight_layout(pad=2)
        canvas = FigureCanvasTkAgg(fig, master=win)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)


if __name__ == "__main__":
    app = DIPTool()
    app.mainloop()
