import customtkinter as ctk
from tkinter import filedialog, messagebox
import cv2
import numpy as np
from PIL import Image, ImageTk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib
import time
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
from processing.segmentation import (
    remove_background_selfie, remove_background_simple,
    apply_to_roi, segment_object_from_rect
)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class DIPTool(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("DIP Tool — Advanced Image Processing")
        
        # Get screen dimensions and maximize window
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        self.geometry(f"{screen_width}x{screen_height}+0+0")
        self.state('zoomed')  # Maximize on Windows
        self.minsize(1300, 750)

        self.original_image = None
        self.current_image = None
        self.preview_image = None
        self.roi_mask = None
        self.drawing_roi = False
        self.roi_start = None
        self.roi_points = []
        self.display_mode = "split"
        
        # Throttle refresh to avoid lag
        self.last_refresh_time = 0
        self.refresh_timer = None
        
        self._build_ui()

    def _build_ui(self):
        # Main layout: sidebar + main area
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ─── LEFT SIDEBAR ───────────────────────────
        self.sidebar = ctk.CTkScrollableFrame(
            self, width=280, corner_radius=0,
            fg_color=("#1a1a2e", "#0f0f1a")
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self._build_sidebar()

        # ─── RIGHT MAIN AREA ────────────────────────
        self.main_area = ctk.CTkFrame(self, fg_color=("#111122", "#08080f"))
        self.main_area.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        self.main_area.grid_rowconfigure(2, weight=1)
        self.main_area.grid_columnconfigure(0, weight=1)
        self._build_main_area()

        self.bind("<Configure>", self._on_resize)

    # ═══════════════════════════════════════════════
    # SIDEBAR - IMPROVED UI/UX
    # ═══════════════════════════════════════════════
    def _build_sidebar(self):
        # ─── HEADER ─────────────────────────────────
        header_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        header_frame.pack(pady=(16, 12), padx=12)
        
        ctk.CTkLabel(
            header_frame, text="📷 DIP Studio",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="#00d4ff"
        ).pack()
        ctk.CTkLabel(
            header_frame, text="Advanced Image Processing",
            font=ctk.CTkFont(size=10), text_color="#888"
        ).pack()

        # ═══════════════════════════════════════════════
        # SECTION 1: FILE / IMAGE MANAGEMENT
        # ═══════════════════════════════════════════════
        self._create_collapsible_section(
            title="📁 File Management",
            color_top="#0066cc",
            color_buttons="#0066cc",
            content_fn=self._build_file_section
        )

        # ═══════════════════════════════════════════════
        # SECTION 2: ENHANCEMENT & CORRECTIONS
        # ═══════════════════════════════════════════════
        self._create_collapsible_section(
            title="✨ Enhancement",
            color_top="#1e5f3f",
            color_buttons="#1e5f3f",
            content_fn=self._build_enhancement_section
        )

        # ═══════════════════════════════════════════════
        # SECTION 3: ADJUSTMENTS (SLIDERS)
        # ═══════════════════════════════════════════════
        self._create_collapsible_section(
            title="🎚️ Adjustments",
            color_top="#5f5f1e",
            color_buttons="#666600",
            content_fn=self._build_adjustments_section
        )

        # ═══════════════════════════════════════════════
        # SECTION 4: FILTERS & EFFECTS
        # ═══════════════════════════════════════════════
        self._create_collapsible_section(
            title="🔧 Filters",
            color_top="#2a4f5f",
            color_buttons="#2a4f5f",
            content_fn=self._build_filters_section
        )

        # ═══════════════════════════════════════════════
        # SECTION 5: ADVANCED TOOLS
        # ═══════════════════════════════════════════════
        self._create_collapsible_section(
            title="⚙️ Advanced Tools",
            color_top="#4f3f5f",
            color_buttons="#4f3f5f",
            content_fn=self._build_advanced_section
        )

    def _create_collapsible_section(self, title, color_top, color_buttons, content_fn):
        """Create a collapsible section with title, divider, and content"""
        # Header with collapse/expand toggle
        section_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        section_frame.pack(fill="x", padx=12, pady=(16, 0))
        
        # Separator line on top
        sep = ctk.CTkFrame(section_frame, height=2, fg_color=color_top)
        sep.pack(fill="x", pady=(0, 8))
        
        # Title label
        title_label = ctk.CTkLabel(
            section_frame, text=title,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=color_top
        )
        title_label.pack(anchor="w", pady=(0, 8))
        
        # Content container
        content_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        content_frame.pack(fill="x", padx=0, pady=(0, 4))
        
        # Build content
        content_fn(content_frame, color_buttons)

    def _build_file_section(self, parent, color):
        """File Management buttons"""
        buttons_config = [
            ("📂 Open Image", self.open_image, "#0066cc", "#0055aa"),
            ("💾 Save Result", self.save_image, "#006633", "#005522"),
            ("🔄 Reset to Original", self.reset_image, "#663300", "#552200"),
        ]
        
        for text, cmd, fg_color, hover_color in buttons_config:
            ctk.CTkButton(
                parent, text=text,
                command=cmd,
                fg_color=fg_color, hover_color=hover_color,
                height=36, font=ctk.CTkFont(size=10, weight="bold"),
                corner_radius=6
            ).pack(fill="x", padx=12, pady=4)

    def _build_enhancement_section(self, parent, color):
        """Enhancement buttons"""
        # Two-column grid for better layout
        btns_config = [
            ("Auto Contrast", self.apply_histeq, "#1e5f3f"),
            ("Smart Contrast (CLAHE)", self.apply_clahe, "#1e5f3f"),
            ("Enhance Blurry", self.apply_enhance_blurry, "#2a7050"),
            ("Reduce Glare", self.apply_reduce_glare, "#3a8060"),
            ("Anti-Backlight", self.apply_anti_backlight, "#4a9070"),
        ]
        
        for text, cmd, fg_color in btns_config:
            ctk.CTkButton(
                parent, text=text,
                command=cmd,
                fg_color=fg_color, hover_color=self._lighten_color(fg_color),
                height=32, font=ctk.CTkFont(size=9),
                corner_radius=4
            ).pack(fill="x", padx=12, pady=2)

    def _build_adjustments_section(self, parent, color):
        """Slider controls for real-time adjustments"""
        # Brightness
        bright_label = ctk.CTkLabel(
            parent, text="Brightness",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="#ffcc00"
        )
        bright_label.pack(anchor="w", padx=14, pady=(8, 2))
        
        self.bright_slider = ctk.CTkSlider(
            parent, from_=-100, to=100, number_of_steps=200,
            command=self._on_brightness_change, fg_color="#666600"
        )
        self.bright_slider.set(0)
        self.bright_slider.pack(fill="x", padx=12, pady=2)
        
        self.bright_label = ctk.CTkLabel(
            parent, text="0", font=ctk.CTkFont(size=9),
            text_color="#888"
        )
        self.bright_label.pack(anchor="e", padx=14, pady=(0, 4))

        # Contrast
        contrast_label = ctk.CTkLabel(
            parent, text="Contrast",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="#ffcc00"
        )
        contrast_label.pack(anchor="w", padx=14, pady=(8, 2))
        
        self.contrast_slider = ctk.CTkSlider(
            parent, from_=0.1, to=3.0, number_of_steps=59,
            command=self._on_contrast_change, fg_color="#666600"
        )
        self.contrast_slider.set(1.0)
        self.contrast_slider.pack(fill="x", padx=12, pady=2)
        
        self.contrast_label = ctk.CTkLabel(
            parent, text="1.0", font=ctk.CTkFont(size=9),
            text_color="#888"
        )
        self.contrast_label.pack(anchor="e", padx=14, pady=(0, 4))

        # Gamma Correction
        gamma_label = ctk.CTkLabel(
            parent, text="Gamma Correction",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="#ffcc00"
        )
        gamma_label.pack(anchor="w", padx=14, pady=(8, 2))
        
        self.gamma_slider = ctk.CTkSlider(
            parent, from_=0.1, to=5.0, number_of_steps=49,
            command=self._on_gamma_change, fg_color="#666600"
        )
        self.gamma_slider.set(1.0)
        self.gamma_slider.pack(fill="x", padx=12, pady=2)
        
        self.gamma_label = ctk.CTkLabel(
            parent, text="1.0", font=ctk.CTkFont(size=9),
            text_color="#888"
        )
        self.gamma_label.pack(anchor="e", padx=14, pady=(0, 12))

    def _build_filters_section(self, parent, color):
        """Filters grouped by type"""
        # Filter kernel size selector
        size_label = ctk.CTkLabel(
            parent, text="Filter Kernel Size",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="#88ccff"
        )
        size_label.pack(anchor="w", padx=14, pady=(6, 6))
        
        self.kernel_var = ctk.StringVar(value="3")
        ks_frame = ctk.CTkFrame(parent, fg_color="transparent")
        ks_frame.pack(fill="x", padx=12, pady=2)
        
        for k in ["3", "5", "7", "9"]:
            ctk.CTkRadioButton(
                ks_frame, text=k, variable=self.kernel_var, value=k,
                width=50, text_color="#88ccff"
            ).pack(side="left", padx=3)

        # Smoothing filters
        smooth_label = ctk.CTkLabel(
            parent, text="Smoothing",
            font=ctk.CTkFont(size=9, weight="bold"),
            text_color="#ccccff"
        )
        smooth_label.pack(anchor="w", padx=14, pady=(8, 2))
        
        smooth_btns = [
            ("Mean Filter", self.apply_mean),
            ("Gaussian Blur", self.apply_gaussian),
            ("Median (Remove Spots)", self.apply_median),
        ]
        
        for text, cmd in smooth_btns:
            ctk.CTkButton(
                parent, text=text,
                command=cmd,
                fg_color="#2a4f5f", hover_color="#3a6f7f",
                height=28, font=ctk.CTkFont(size=9),
                corner_radius=4
            ).pack(fill="x", padx=12, pady=2)

        # Edge detection / Enhancement
        edge_label = ctk.CTkLabel(
            parent, text="Sharpening & Edges",
            font=ctk.CTkFont(size=9, weight="bold"),
            text_color="#ccccff"
        )
        edge_label.pack(anchor="w", padx=14, pady=(8, 2))
        
        edge_btns = [
            ("Sharpen", self.apply_laplacian_sharp),
            ("Detect Edges (Canny)", self.apply_canny),
        ]
        
        for text, cmd in edge_btns:
            ctk.CTkButton(
                parent, text=text,
                command=cmd,
                fg_color="#2a4f5f", hover_color="#3a6f7f",
                height=28, font=ctk.CTkFont(size=9),
                corner_radius=4
            ).pack(fill="x", padx=12, pady=2)

    def _build_advanced_section(self, parent, color):
        """Advanced tools"""
        btns_config = [
            ("🎯 Draw ROI (Select Area)", self.start_roi_drawing, "#5f3f5f"),
            ("🤖 Remove Background (AI)", self.remove_bg_ai, "#6f4f7f"),
            ("📊 Show Histogram", self.show_histogram, "#5f4f6f"),
        ]
        
        for text, cmd, fg_color in btns_config:
            ctk.CTkButton(
                parent, text=text,
                command=cmd,
                fg_color=fg_color, hover_color=self._lighten_color(fg_color),
                height=36, font=ctk.CTkFont(size=10, weight="bold"),
                corner_radius=6
            ).pack(fill="x", padx=12, pady=4)

    def _lighten_color(self, hex_color):
        """Lighten a hex color by returning a slightly lighter shade"""
        # Simple approach: return a brighter version
        color_map = {
            "#0066cc": "#0088ff",
            "#1e5f3f": "#2a8050",
            "#2a4f5f": "#3a6f7f",
            "#4f3f5f": "#6f5f7f",
            "#5f3f5f": "#7f5f7f",
            "#2a7050": "#3a9060",
            "#3a8060": "#4aa070",
            "#4a9070": "#5ab080",
            "#5f4f6f": "#7f6f8f",
            "#6f4f7f": "#8f6f9f",
        }
        return color_map.get(hex_color, "#00d4ff")

    # ═══════════════════════════════════════════════
    # MAIN AREA
    # ═══════════════════════════════════════════════
    def _build_main_area(self):
        # Top toolbar
        toolbar = ctk.CTkFrame(
            self.main_area, height=42,
            fg_color=("#1a1a2e", "#0f0f1a")
        )
        toolbar.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        toolbar.pack_propagate(False)

        # Status info
        self.status_label = ctk.CTkLabel(
            toolbar,
            text="Open an image to begin",
            font=ctk.CTkFont(size=11),
            text_color="#888"
        )
        self.status_label.pack(side="left", padx=12, pady=4)

        # Spacer
        spacer = ctk.CTkFrame(toolbar, fg_color="transparent")
        spacer.pack(side="left", fill="x", expand=True)

        # View mode buttons
        ctk.CTkLabel(
            toolbar, text="View:",
            font=ctk.CTkFont(size=10)
        ).pack(side="right", padx=(0, 8))
        
        for label, val in [("Original", "original"), ("Processed", "processed"), ("Split", "split")]:
            ctk.CTkButton(
                toolbar, text=label, width=90,
                command=lambda v=val: self.set_view_mode(v),
                fg_color="#1e3a5f", hover_color="#2a5080",
                height=28
            ).pack(side="right", padx=2, pady=3)

        # Main separator
        sep = ctk.CTkFrame(self.main_area, height=1, fg_color="#333366")
        sep.grid(row=1, column=0, sticky="ew", padx=0, pady=0)

        # Canvas area with labels and buttons
        self.canvas_frame = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.canvas_frame.grid(row=2, column=0, sticky="nsew", padx=0, pady=0)
        self.canvas_frame.grid_rowconfigure(0, weight=1)
        self.canvas_frame.grid_columnconfigure(0, weight=1)
        self.canvas_frame.grid_columnconfigure(1, weight=1)

        # Original image section
        self.orig_frame = ctk.CTkFrame(self.canvas_frame, fg_color="transparent")
        self.orig_frame.grid(row=0, column=0, sticky="nsew", padx=2, pady=0)
        self.orig_frame.grid_rowconfigure(0, weight=0)
        self.orig_frame.grid_rowconfigure(1, weight=1)
        self.orig_frame.grid_rowconfigure(2, weight=0)
        self.orig_frame.grid_columnconfigure(0, weight=1)
        
        label_orig = ctk.CTkLabel(
            self.orig_frame, text="Current Output",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="#aaa", height=16
        )
        label_orig.grid(row=0, column=0, sticky="ew", padx=0, pady=2)
        
        self.img_orig = ctk.CTkLabel(
            self.orig_frame, text="Open an image",
            fg_color=("#0d0d1f", "#050510"), corner_radius=4
        )
        self.img_orig.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        
        # Spacer to match button_frame height on right
        spacer_left = ctk.CTkFrame(self.orig_frame, fg_color="transparent", height=28)
        spacer_left.grid(row=2, column=0, sticky="ew", padx=0, pady=0)
        spacer_left.grid_propagate(False)

        # Processed image section with Apply button
        self.proc_frame = ctk.CTkFrame(self.canvas_frame, fg_color="transparent")
        self.proc_frame.grid(row=0, column=1, sticky="nsew", padx=2, pady=0)
        self.proc_frame.grid_rowconfigure(0, weight=0)
        self.proc_frame.grid_rowconfigure(1, weight=1)
        self.proc_frame.grid_rowconfigure(2, weight=0)
        self.proc_frame.grid_columnconfigure(0, weight=1)
        
        label_proc = ctk.CTkLabel(
            self.proc_frame, text="Preview (Editing)",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="#00d4ff", height=16
        )
        label_proc.grid(row=0, column=0, sticky="ew", padx=0, pady=2)
        
        self.img_proc = ctk.CTkLabel(
            self.proc_frame, text="",
            fg_color=("#0d0d1f", "#050510"), corner_radius=4
        )
        self.img_proc.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)

        # Apply button row
        button_frame = ctk.CTkFrame(self.proc_frame, fg_color="transparent", height=28)
        button_frame.grid(row=2, column=0, sticky="ew", padx=0, pady=0)
        button_frame.grid_propagate(False)
        
        ctk.CTkButton(
            button_frame, text="Apply Changes",
            command=self.apply_changes,
            fg_color="#00aa44", hover_color="#00cc55",
            height=26, font=ctk.CTkFont(size=9, weight="bold")
        ).pack(side="right", padx=2, pady=1)
        
        ctk.CTkButton(
            button_frame, text="Undo",
            command=self.undo_changes,
            fg_color="#aa4400", hover_color="#cc5500",
            height=26, font=ctk.CTkFont(size=9, weight="bold")
        ).pack(side="right", padx=2, pady=1)

    # ═══════════════════════════════════════════════
    # FILE OPERATIONS
    # ═══════════════════════════════════════════════
    def _normalize_image_size(self, img, target_width=1280):
        """Resize image to standard width while maintaining aspect ratio"""
        h, w = img.shape[:2]
        
        # If image is smaller than target, upscale it
        # If larger, downscale to target width
        if w < target_width:
            scale = target_width / w
            new_w = int(w * scale)
            new_h = int(h * scale)
            img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
        elif w > target_width:
            scale = target_width / w
            new_w = int(w * scale)
            new_h = int(h * scale)
            img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        
        return img

    def open_image(self):
        path = filedialog.askopenfilename(
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.tiff *.webp"), ("All", "*.*")]
        )
        if not path:
            return
        
        img = cv2.imread(path)
        if img is None:
            messagebox.showerror("Error", "Cannot read image.")
            return
        
        # Normalize image size to standard width (1280px)
        img = self._normalize_image_size(img, target_width=1280)
        
        self.original_image = img.copy()
        self.current_image = img.copy()
        self.preview_image = img.copy()
        self.roi_mask = None
        
        h, w = img.shape[:2]
        filename = path.split('/')[-1]
        self.status_label.configure(text=f"{filename} ({w}×{h}px)")
        
        self.refresh_display()

    def save_image(self):
        if self.current_image is None:
            messagebox.showwarning("Warning", "No image to save.")
            return
        
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg"), ("BMP", "*.bmp")]
        )
        
        if path:
            cv2.imwrite(path, self.current_image)
            messagebox.showinfo("Success", f"Saved to:\n{path}")

    def reset_image(self):
        if self.original_image is None:
            messagebox.showwarning("Warning", "No image loaded.")
            return
        
        self.current_image = self.original_image.copy()
        self.preview_image = self.original_image.copy()
        self.roi_mask = None
        self.refresh_display()
        self.status_label.configure(text="Reset to original")

    # ═══════════════════════════════════════════════
    # APPLY / UNDO
    # ═══════════════════════════════════════════════
    def apply_changes(self):
        """Confirm and apply all preview changes to current_image"""
        if self.preview_image is None:
            messagebox.showwarning("Warning", "No changes to apply.")
            return
        
        if np.array_equal(self.preview_image, self.current_image):
            messagebox.showinfo("Info", "No changes made.")
            return
        
        self.current_image = self.preview_image.copy()
        self.preview_image = self.current_image.copy()  # Reset preview = current
        self.refresh_display()
        messagebox.showinfo("Success", "Changes applied successfully!")

    def undo_changes(self):
        """Discard preview changes and restore preview_image to match current_image"""
        if self.current_image is None:
            return
        
        self.preview_image = self.current_image.copy()
        self.refresh_display()
        self.status_label.configure(text="Changes discarded")

    # ═══════════════════════════════════════════════
    # DISPLAY
    # ═══════════════════════════════════════════════
    def set_view_mode(self, mode):
        self.display_mode = mode
        self.refresh_display()

    def refresh_display(self):
        """Refresh display with throttling to prevent lag"""
        # Cancel previous timer if exists
        if self.refresh_timer:
            self.after_cancel(self.refresh_timer)
            self.refresh_timer = None
        
        # Throttle: only refresh every 50ms max
        current_time = time.time()
        elapsed = (current_time - self.last_refresh_time) * 1000
        
        if elapsed < 50:
            # Schedule refresh later
            self.refresh_timer = self.after(50 - int(elapsed), self._do_refresh)
        else:
            self._do_refresh()
    
    def _do_refresh(self):
        """Actual display refresh logic"""
        self.last_refresh_time = time.time()
        self.refresh_timer = None
        
        if self.original_image is None:
            return
        
        # Ensure all images are same size
        if self.current_image is not None and self.current_image.shape != self.original_image.shape:
            self.current_image = cv2.resize(self.current_image, (self.original_image.shape[1], self.original_image.shape[0]))
        
        if self.preview_image is not None and self.preview_image.shape != self.original_image.shape:
            self.preview_image = cv2.resize(self.preview_image, (self.original_image.shape[1], self.original_image.shape[0]))
        
        # Use window dimensions directly
        win_w = self.winfo_width()
        win_h = self.winfo_height()
        
        # Account for sidebar (280px) and margins
        canvas_w = max(600, win_w - 300)
        canvas_h = max(500, win_h - 100)
        
        # Each pane gets half
        w = (canvas_w - 4) // 2
        h = canvas_h - 44

        # Control what displays based on view mode
        if self.display_mode == "split":
            # Split: Left=current output, Right=preview (editing)
            self._show_cv(self.img_orig, self.current_image, w, h)
            self._show_cv(self.img_proc, self.preview_image, w, h)
            self.orig_frame.grid()
            self.proc_frame.grid()
        elif self.display_mode == "original":
            # Compare: Left=original (as uploaded), Right=current (edited)
            self._show_cv(self.img_orig, self.original_image, w, h)
            self._show_cv(self.img_proc, self.current_image, w, h)
            self.orig_frame.grid()
            self.proc_frame.grid()
        else:  # processed
            # Processed: Show only right pane with preview
            self._show_cv(self.img_proc, self.preview_image, w, h)
            self.orig_frame.grid_remove()
            self.proc_frame.grid()

    def _show_cv(self, label_widget, bgr_img, max_w, max_h, side=""):
        """Convert BGR to PIL and display on CTkLabel - maintain aspect ratio"""
        if bgr_img is None or bgr_img.size == 0:
            label_widget.configure(image=None, text="No image")
            return
        
        # For BGRA images (with alpha), convert properly
        if len(bgr_img.shape) == 3 and bgr_img.shape[2] == 4:
            rgb = cv2.cvtColor(bgr_img, cv2.COLOR_BGRA2RGBA)
            pil = Image.fromarray(rgb, 'RGBA')
        else:
            rgb = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2RGB)
            pil = Image.fromarray(rgb)
        
        orig_w, orig_h = pil.size
        if orig_w <= 0 or orig_h <= 0:
            label_widget.configure(image=None, text="Invalid image")
            return
        
        # Calculate scale to fit within max bounds
        # BUT: Never upscale - only downscale if needed
        scale_w = max_w / orig_w
        scale_h = max_h / orig_h
        scale = min(scale_w, scale_h)
        
        # Prevent upscaling - only scale down if > 1 means we'd upscale
        if scale > 1.0:
            scale = 1.0  # Keep original size, don't upscale
        
        # Apply scale
        new_w = max(1, int(orig_w * scale))
        new_h = max(1, int(orig_h * scale))
        
        if new_w != orig_w or new_h != orig_h:
            pil = pil.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        ctk_img = ctk.CTkImage(light_image=pil, dark_image=pil, size=pil.size)
        label_widget.configure(image=ctk_img, text="")
        label_widget._image_ref = ctk_img

    def _on_resize(self, event):
        self.after(100, self.refresh_display)

    # ═══════════════════════════════════════════════
    # ADJUSTMENTS (Real-time Preview)
    # ═══════════════════════════════════════════════
    def _on_brightness_change(self, val):
        b = int(float(val))
        self.bright_label.configure(text=f"{b:+d}")
        self.apply_brightness_contrast()

    def _on_contrast_change(self, val):
        c = float(val)
        self.contrast_label.configure(text=f"{c:.2f}")
        self.apply_brightness_contrast()

    def _on_gamma_change(self, val):
        gamma_val = float(val)
        self.gamma_label.configure(
            text=f"{gamma_val:.2f}" + ("←Darker" if gamma_val < 1 else "→Brighter" if gamma_val > 1 else "")
        )
        self.apply_gamma()

    def apply_brightness_contrast(self):
        """Apply brightness and contrast in real-time"""
        if self.current_image is None:
            return
        
        b = int(self.bright_slider.get())
        c = self.contrast_slider.get()
        
        try:
            # If ROI mask exists, apply only to ROI
            if self.roi_mask is not None:
                result = apply_to_roi(self.current_image, self.roi_mask, brightness_contrast, brightness=b, contrast=c)
            else:
                result = brightness_contrast(self.current_image, brightness=b, contrast=c)
            
            self.preview_image = result
            self.refresh_display()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def apply_gamma(self):
        """Apply gamma correction in real-time"""
        if self.current_image is None:
            return
        
        g = self.gamma_slider.get()
        
        try:
            # If ROI mask exists, apply only to ROI
            if self.roi_mask is not None:
                result = apply_to_roi(self.current_image, self.roi_mask, gamma_correction, gamma=g)
            else:
                result = gamma_correction(self.current_image, gamma=g)
            
            self.preview_image = result
            self.refresh_display()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ═══════════════════════════════════════════════
    # ENHANCEMENTS
    # ═══════════════════════════════════════════════
    def _check(self):
        if self.current_image is None:
            messagebox.showwarning("Warning", "Please open an image first.")
            return False
        return True

    def _apply_filter(self, fn, *args, **kwargs):
        """Apply a filter and update preview"""
        if not self._check():
            return
        
        try:
            # If ROI mask exists, apply filter only to ROI region
            if self.roi_mask is not None:
                result = apply_to_roi(self.current_image, self.roi_mask, fn, *args, **kwargs)
            else:
                result = fn(self.current_image, *args, **kwargs)
            
            self.preview_image = result
            self.refresh_display()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def apply_histeq(self):
        self._apply_filter(histogram_equalization)

    def apply_clahe(self):
        self._apply_filter(clahe_enhancement)

    def apply_enhance_blurry(self):
        self._apply_filter(enhance_blurry_image, clahe_clip=3.0, sharpen_strength=2.0)

    def apply_reduce_glare(self):
        self._apply_filter(reduce_glare_exposure, gamma=1.5, clahe_clip=2.5, highlights_recover=0.4)

    def apply_anti_backlight(self):
        self._apply_filter(anti_backlight_enhancement, shadow_boost=1.3, highlight_reduce=0.7)

    # ═══════════════════════════════════════════════
    # FILTERS
    # ═══════════════════════════════════════════════
    def _ksize(self):
        return int(self.kernel_var.get())

    def apply_mean(self):
        self._apply_filter(mean_filter, ksize=self._ksize())

    def apply_gaussian(self):
        self._apply_filter(gaussian_filter, ksize=self._ksize())

    def apply_median(self):
        self._apply_filter(median_filter, ksize=self._ksize())

    def apply_laplacian_sharp(self):
        self._apply_filter(laplacian_sharpen)

    def apply_canny(self):
        self._apply_filter(canny_edge)

    # ═══════════════════════════════════════════════
    # ROI & SEGMENTATION
    # ═══════════════════════════════════════════════
    def start_roi_drawing(self):
        """Start object selection mode"""
        if not self._check():
            return
        
        if self.roi_mask is not None:
            if messagebox.askyesno("Existing ROI", "Clear existing ROI and draw new one?"):
                self.roi_mask = None
            else:
                return
        
        messagebox.showinfo(
            "Select Object",
            "Click and drag to draw a rectangle around the object you want to edit.\n\n"
            "The app will try to detect the object inside that box and build a mask for future edits.\n\n"
            "Close this dialog then click on the image to start."
        )
        
        # Create a temporary window for ROI drawing
        self._show_roi_window()

    def _show_roi_window(self):
        """Display image in a window for object-based ROI selection"""
        from tkinter import Canvas
        
        roi_win = ctk.CTkToplevel(self)
        roi_win.title("Select Object - Click and Drag Around the Object")
        roi_win.geometry("1000x650")
        
        # Convert image for display
        rgb = cv2.cvtColor(self.current_image, cv2.COLOR_BGR2RGB)
        orig_h, orig_w = rgb.shape[:2]
        
        # Resize for display
        max_w, max_h = 950, 600
        scale_w = max_w / orig_w if orig_w > 0 else 1
        scale_h = max_h / orig_h if orig_h > 0 else 1
        scale = min(scale_w, scale_h)
        
        display_w = int(orig_w * scale)
        display_h = int(orig_h * scale)
        
        rgb_resized = cv2.resize(rgb, (display_w, display_h))
        pil = Image.fromarray(rgb_resized)
        photo = ImageTk.PhotoImage(pil)
        
        # Create Canvas for event binding
        canvas = Canvas(roi_win, bg="black", width=display_w, height=display_h, cursor="crosshair")
        canvas.pack(padx=10, pady=10)
        
        # Display image on canvas
        canvas.create_image(0, 0, image=photo, anchor="nw")
        canvas.image = photo  # Keep reference
        
        # Drawing state
        drawing = [False]
        start_pos = [None]
        rect_id = [None]
        
        def on_mouse_down(event):
            drawing[0] = True
            start_pos[0] = (event.x, event.y)
            # Clear previous rect
            if rect_id[0]:
                canvas.delete(rect_id[0])
                rect_id[0] = None
        
        def on_mouse_drag(event):
            if not drawing[0] or start_pos[0] is None:
                return
            
            # Clear previous rect
            if rect_id[0]:
                canvas.delete(rect_id[0])
            
            # Draw new rect preview
            x1, y1 = start_pos[0]
            x2, y2 = event.x, event.y
            rect_id[0] = canvas.create_rectangle(
                x1, y1, x2, y2, 
                outline="lime", width=2
            )
        
        def on_mouse_up(event):
            if not drawing[0]:
                return
            
            drawing[0] = False
            end_pos = (event.x, event.y)
            
            if start_pos[0] is None:
                return
            
            # Get coordinates in display space
            x1_disp = min(start_pos[0][0], end_pos[0])
            x2_disp = max(start_pos[0][0], end_pos[0])
            y1_disp = min(start_pos[0][1], end_pos[1])
            y2_disp = max(start_pos[0][1], end_pos[1])
            
            # Minimum size check
            if (x2_disp - x1_disp) < 10 or (y2_disp - y1_disp) < 10:
                messagebox.showwarning("Too small", "ROI area too small. Please draw a larger area.")
                roi_win.destroy()
                return
            
            # Convert to original image coordinates
            if scale > 0:
                x1 = int(x1_disp / scale)
                x2 = int(x2_disp / scale)
                y1 = int(y1_disp / scale)
                y2 = int(y2_disp / scale)
            else:
                x1, x2, y1, y2 = 0, orig_w, 0, orig_h
            
            # Clamp to bounds
            x1 = max(0, min(x1, orig_w - 1))
            x2 = max(x1 + 1, min(x2, orig_w))
            y1 = max(0, min(y1, orig_h - 1))
            y2 = max(y1 + 1, min(y2, orig_h))
            
            # Segment the object inside the rectangle.
            try:
                mask = segment_object_from_rect(self.current_image, (x1, y1, x2, y2))
            except Exception as exc:
                use_rect = messagebox.askyesno(
                    "Segmentation failed",
                    f"Could not isolate the object inside the selected area.\n\n{exc}\n\nUse the full rectangle as ROI instead?"
                )
                if not use_rect:
                    return

                mask = np.zeros((orig_h, orig_w), dtype=np.uint8)
                mask[y1:y2, x1:x2] = 255
            
            self.roi_mask = mask
            mask_area = int(cv2.countNonZero(mask))
            self.status_label.configure(
                text=f"Object selected: ({x1},{y1}) to ({x2},{y2}) - Mask area: {mask_area}px²"
            )
            
            roi_win.destroy()
            messagebox.showinfo("Success", f"Object selected!\n\nFilters will be applied to the detected object only.")
        
        # Bind events
        canvas.bind("<Button-1>", on_mouse_down)
        canvas.bind("<B1-Motion>", on_mouse_drag)
        canvas.bind("<ButtonRelease-1>", on_mouse_up)
        
        # Instructions
        info = ctk.CTkLabel(
            roi_win,
            text="Click and drag to draw a rectangle around the object you want to edit",
            font=ctk.CTkFont(size=10),
            text_color="#888"
        )
        info.pack(pady=5)

    def remove_bg_ai(self):
        """Remove background using AI"""
        if not self._check():
            return
        
        try:
            self.status_label.configure(text="Processing... removing background...")
            self.update()
            
            result = remove_background_selfie(self.current_image)
            self.preview_image = result
            self.refresh_display()
            
            self.status_label.configure(text="Background removed successfully!")
        except ImportError:
            messagebox.showerror(
                "Missing Module",
                "MediaPipe not installed.\n\nRun: pip install mediapipe"
            )
        except Exception as e:
            messagebox.showerror("Error", f"Failed to remove background:\n{str(e)}")

    # ═══════════════════════════════════════════════
    # HISTOGRAM
    # ═══════════════════════════════════════════════
    def show_histogram(self):
        """Display histogram comparison window"""
        if not self._check():
            return
        
        win = ctk.CTkToplevel(self)
        win.title("Histogram Comparison")
        win.geometry("1000x450")
        win.configure(fg_color="#0a0a1a")
        
        fig, axes = plt.subplots(1, 2, figsize=(12, 4), facecolor="#0a0a1a")
        colors_bgr = ['#3399ff', '#00cc66', '#ff4444']
        labels = ['Blue', 'Green', 'Red']
        
        for ax, img, title in zip(
            axes,
            [self.original_image, self.current_image],
            ["Original", "Current"]
        ):
            ax.set_facecolor("#0d0d1f")
            ax.set_title(title, color="#00d4ff", fontsize=13, weight="bold")
            ax.tick_params(colors="#888")
            
            for spine in ax.spines.values():
                spine.set_edgecolor("#333")
            
            if len(img.shape) == 2:
                hist = cv2.calcHist([img], [0], None, [256], [0, 256])
                ax.plot(hist, color="#00d4ff", linewidth=1.5)
            elif img.shape[2] == 3:
                for i, (c, lbl) in enumerate(zip(colors_bgr, labels)):
                    hist = cv2.calcHist([img], [i], None, [256], [0, 256])
                    ax.plot(hist, color=c, linewidth=1.5, label=lbl, alpha=0.85)
                ax.legend(facecolor="#111", labelcolor="white", fontsize=9)
            
            ax.set_xlim([0, 256])
        
        plt.tight_layout(pad=2)
        canvas = FigureCanvasTkAgg(fig, master=win)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)


if __name__ == "__main__":
    app = DIPTool()
    app.display_mode = "split"
    app.mainloop()
