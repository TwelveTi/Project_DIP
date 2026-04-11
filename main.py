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
    apply_to_roi, segment_object_from_lasso, segment_object_from_rect
)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class DIPTool(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("DIP Tool — Advanced Image Processing")

        self.ui = {
            "bg": "#0e1116",
            "sidebar": "#121821",
            "main": "#0f141b",
            "panel": "#171e28",
            "panel_alt": "#1c2430",
            "border": "#2a3441",
            "accent": "#4aa3a2",
            "accent_hover": "#5ab5b4",
            "success": "#2f8f66",
            "success_hover": "#38a878",
            "danger": "#b56c4c",
            "danger_hover": "#c57b58",
            "muted": "#95a2b0",
            "text": "#e9eef3",
            "title": "#ffffff",
            "font": "Segoe UI",
        }
        self.configure(fg_color=self.ui["bg"])
        
        # Start with screen-sized geometry, then force maximize after render.
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        self.geometry(f"{screen_width}x{screen_height}+0+0")
        self.minsize(1300, 750)

        self.original_image = None
        self.current_image = None
        self.preview_image = None
        self.roi_mask = None
        self.drawing_roi = False
        self.roi_start = None
        self.roi_points = []
        self.display_mode = "split"
        self.is_fullscreen = False
        
        # Throttle refresh to avoid lag
        self.last_refresh_time = 0
        self.refresh_timer = None
        self.adjust_timer = None
        self.pending_adjustment = None
        
        self._build_ui()
        self.after(50, self._apply_startup_window_state)
        self.bind("<F11>", self._toggle_fullscreen)
        self.bind("<Escape>", self._exit_fullscreen)

    def _apply_startup_window_state(self):
        """Force maximized state after the window is mapped (more reliable on Windows/Spyder)."""
        try:
            self.state("zoomed")
        except Exception:
            pass

        # Fallback: force exact screen bounds if zoomed is ignored by host environment.
        self.update_idletasks()
        if self.winfo_width() < self.winfo_screenwidth() - 40 or self.winfo_height() < self.winfo_screenheight() - 40:
            self.geometry(f"{self.winfo_screenwidth()}x{self.winfo_screenheight()}+0+0")

    def _toggle_fullscreen(self, event=None):
        self.is_fullscreen = not self.is_fullscreen
        self.attributes("-fullscreen", self.is_fullscreen)
        if not self.is_fullscreen:
            self.after(10, self._apply_startup_window_state)

    def _exit_fullscreen(self, event=None):
        if self.is_fullscreen:
            self.is_fullscreen = False
            self.attributes("-fullscreen", False)
            self.after(10, self._apply_startup_window_state)

    def _build_ui(self):
        # Main layout: sidebar + main area
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ─── LEFT SIDEBAR ───────────────────────────
        self.sidebar = ctk.CTkScrollableFrame(
            self, width=280, corner_radius=0,
            fg_color=self.ui["sidebar"],
            border_width=0
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self._build_sidebar()

        # ─── RIGHT MAIN AREA ────────────────────────
        self.main_area = ctk.CTkFrame(self, fg_color=self.ui["main"])
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
            header_frame, text="DIP Studio",
            font=ctk.CTkFont(family=self.ui["font"], size=24, weight="bold"),
            text_color=self.ui["title"]
        ).pack()
        ctk.CTkLabel(
            header_frame, text="Image editing workspace",
            font=ctk.CTkFont(family=self.ui["font"], size=10),
            text_color=self.ui["muted"]
        ).pack()

        # ═══════════════════════════════════════════════
        # SECTION 1: FILE / IMAGE MANAGEMENT
        # ═══════════════════════════════════════════════
        self._create_collapsible_section(
            title="File",
            color_top=self.ui["accent"],
            color_buttons=self.ui["panel_alt"],
            content_fn=self._build_file_section
        )

        # ═══════════════════════════════════════════════
        # SECTION 2: ENHANCEMENT & CORRECTIONS
        # ═══════════════════════════════════════════════
        self._create_collapsible_section(
            title="Enhance",
            color_top=self.ui["accent"],
            color_buttons=self.ui["panel_alt"],
            content_fn=self._build_enhancement_section
        )

        # ═══════════════════════════════════════════════
        # SECTION 3: ADJUSTMENTS (SLIDERS)
        # ═══════════════════════════════════════════════
        self._create_collapsible_section(
            title="Adjust",
            color_top=self.ui["accent"],
            color_buttons=self.ui["panel_alt"],
            content_fn=self._build_adjustments_section
        )

        # ═══════════════════════════════════════════════
        # SECTION 4: FILTERS & EFFECTS
        # ═══════════════════════════════════════════════
        self._create_collapsible_section(
            title="Filters",
            color_top=self.ui["accent"],
            color_buttons=self.ui["panel_alt"],
            content_fn=self._build_filters_section
        )

        # ═══════════════════════════════════════════════
        # SECTION 5: ADVANCED TOOLS
        # ═══════════════════════════════════════════════
        self._create_collapsible_section(
            title="Tools",
            color_top=self.ui["accent"],
            color_buttons=self.ui["panel_alt"],
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
            font=ctk.CTkFont(family=self.ui["font"], size=12, weight="bold"),
            text_color=self.ui["title"]
        )
        title_label.pack(anchor="w", pady=(0, 8))
        
        # Content container
        content_frame = ctk.CTkFrame(
            self.sidebar,
            fg_color=self.ui["panel"],
            corner_radius=12,
            border_width=1,
            border_color=self.ui["border"]
        )
        content_frame.pack(fill="x", padx=12, pady=(0, 4))
        
        # Build content
        content_fn(content_frame, color_buttons)

    def _build_file_section(self, parent, color):
        """File Management buttons"""
        buttons_config = [
            ("Open Image", self.open_image, self.ui["panel_alt"], self.ui["accent"]),
            ("Save Result", self.save_image, self.ui["panel_alt"], self.ui["success"]),
            ("Reset to Original", self.reset_image, self.ui["panel_alt"], self.ui["danger"]),
        ]
        
        for text, cmd, fg_color, hover_color in buttons_config:
            ctk.CTkButton(
                parent, text=text,
                command=cmd,
                fg_color=fg_color, hover_color=hover_color,
                height=38, font=ctk.CTkFont(family=self.ui["font"], size=10, weight="bold"),
                corner_radius=10, border_width=1, border_color=self.ui["border"]
            ).pack(fill="x", padx=10, pady=5)

    def _build_enhancement_section(self, parent, color):
        """Enhancement buttons"""
        # Two-column grid for better layout
        btns_config = [
            ("Auto Contrast", self.apply_histeq, self.ui["panel_alt"]),
            ("Smart Contrast (CLAHE)", self.apply_clahe, self.ui["panel_alt"]),
            ("Enhance Blurry", self.apply_enhance_blurry, self.ui["panel_alt"]),
            ("Reduce Glare", self.apply_reduce_glare, self.ui["panel_alt"]),
            ("Anti-Backlight", self.apply_anti_backlight, self.ui["panel_alt"]),
        ]
        
        for text, cmd, fg_color in btns_config:
            ctk.CTkButton(
                parent, text=text,
                command=cmd,
                fg_color=fg_color, hover_color=self.ui["accent"],
                height=34, font=ctk.CTkFont(family=self.ui["font"], size=9),
                corner_radius=8, border_width=1, border_color=self.ui["border"]
            ).pack(fill="x", padx=10, pady=4)

    def _build_adjustments_section(self, parent, color):
        """Slider controls for real-time adjustments"""
        # Brightness
        bright_label = ctk.CTkLabel(
            parent, text="Brightness",
            font=ctk.CTkFont(family=self.ui["font"], size=10, weight="bold"),
            text_color=self.ui["text"]
        )
        bright_label.pack(anchor="w", padx=12, pady=(10, 2))
        
        self.bright_slider = ctk.CTkSlider(
            parent, from_=-100, to=100, number_of_steps=200,
            command=self._on_brightness_change, fg_color=self.ui["accent"]
        )
        self.bright_slider.set(0)
        self.bright_slider.pack(fill="x", padx=12, pady=2)
        
        self.bright_label = ctk.CTkLabel(
            parent, text="0", font=ctk.CTkFont(size=9),
            text_color=self.ui["muted"]
        )
        self.bright_label.pack(anchor="e", padx=12, pady=(0, 6))

        # Contrast
        contrast_label = ctk.CTkLabel(
            parent, text="Contrast",
            font=ctk.CTkFont(family=self.ui["font"], size=10, weight="bold"),
            text_color=self.ui["text"]
        )
        contrast_label.pack(anchor="w", padx=12, pady=(10, 2))
        
        self.contrast_slider = ctk.CTkSlider(
            parent, from_=0.1, to=3.0, number_of_steps=59,
            command=self._on_contrast_change, fg_color=self.ui["accent"]
        )
        self.contrast_slider.set(1.0)
        self.contrast_slider.pack(fill="x", padx=12, pady=2)
        
        self.contrast_label = ctk.CTkLabel(
            parent, text="1.0", font=ctk.CTkFont(size=9),
            text_color=self.ui["muted"]
        )
        self.contrast_label.pack(anchor="e", padx=12, pady=(0, 6))

        # Gamma Correction
        gamma_label = ctk.CTkLabel(
            parent, text="Gamma Correction",
            font=ctk.CTkFont(family=self.ui["font"], size=10, weight="bold"),
            text_color=self.ui["text"]
        )
        gamma_label.pack(anchor="w", padx=12, pady=(10, 2))
        
        self.gamma_slider = ctk.CTkSlider(
            parent, from_=0.1, to=5.0, number_of_steps=49,
            command=self._on_gamma_change, fg_color=self.ui["accent"]
        )
        self.gamma_slider.set(1.0)
        self.gamma_slider.pack(fill="x", padx=12, pady=2)
        
        self.gamma_label = ctk.CTkLabel(
            parent, text="1.0", font=ctk.CTkFont(size=9),
            text_color=self.ui["muted"]
        )
        self.gamma_label.pack(anchor="e", padx=12, pady=(0, 10))

    def _build_filters_section(self, parent, color):
        """Filters grouped by type"""
        # Filter kernel size selector
        size_label = ctk.CTkLabel(
            parent, text="Filter Kernel Size",
            font=ctk.CTkFont(family=self.ui["font"], size=10, weight="bold"),
            text_color=self.ui["text"]
        )
        size_label.pack(anchor="w", padx=12, pady=(10, 6))
        
        self.kernel_var = ctk.StringVar(value="3")
        ks_frame = ctk.CTkFrame(parent, fg_color="transparent")
        ks_frame.pack(fill="x", padx=10, pady=2)
        
        for k in ["3", "5", "7", "9"]:
            ctk.CTkRadioButton(
                ks_frame, text=k, variable=self.kernel_var, value=k,
                width=50, text_color=self.ui["muted"]
            ).pack(side="left", padx=3)

        # Smoothing filters
        smooth_label = ctk.CTkLabel(
            parent, text="Smoothing",
            font=ctk.CTkFont(family=self.ui["font"], size=9, weight="bold"),
            text_color=self.ui["muted"]
        )
        smooth_label.pack(anchor="w", padx=12, pady=(10, 2))
        
        smooth_btns = [
            ("Mean Filter", self.apply_mean),
            ("Gaussian Blur", self.apply_gaussian),
            ("Median (Remove Spots)", self.apply_median),
        ]
        
        for text, cmd in smooth_btns:
            ctk.CTkButton(
                parent, text=text,
                command=cmd,
                fg_color=self.ui["panel_alt"], hover_color=self.ui["accent"],
                height=32, font=ctk.CTkFont(family=self.ui["font"], size=9),
                corner_radius=8, border_width=1, border_color=self.ui["border"]
            ).pack(fill="x", padx=10, pady=4)

        # Edge detection / Enhancement
        edge_label = ctk.CTkLabel(
            parent, text="Sharpening & Edges",
            font=ctk.CTkFont(family=self.ui["font"], size=9, weight="bold"),
            text_color=self.ui["muted"]
        )
        edge_label.pack(anchor="w", padx=12, pady=(10, 2))
        
        edge_btns = [
            ("Sharpen", self.apply_laplacian_sharp),
            ("Detect Edges (Canny)", self.apply_canny),
        ]
        
        for text, cmd in edge_btns:
            ctk.CTkButton(
                parent, text=text,
                command=cmd,
                fg_color=self.ui["panel_alt"], hover_color=self.ui["accent"],
                height=32, font=ctk.CTkFont(family=self.ui["font"], size=9),
                corner_radius=8, border_width=1, border_color=self.ui["border"]
            ).pack(fill="x", padx=10, pady=4)

    def _build_advanced_section(self, parent, color):
        """Advanced tools"""
        btns_config = [
            ("Trace Object (Freehand)", self.start_roi_drawing, self.ui["panel_alt"]),
            ("Remove Background", self.remove_bg_ai, self.ui["panel_alt"]),
            ("Show Histogram", self.show_histogram, self.ui["panel_alt"]),
        ]
        
        for text, cmd, fg_color in btns_config:
            ctk.CTkButton(
                parent, text=text,
                command=cmd,
                fg_color=fg_color, hover_color=self.ui["accent"],
                height=38, font=ctk.CTkFont(family=self.ui["font"], size=10, weight="bold"),
                corner_radius=10, border_width=1, border_color=self.ui["border"]
            ).pack(fill="x", padx=10, pady=5)

    # ═══════════════════════════════════════════════
    # MAIN AREA
    # ═══════════════════════════════════════════════
    def _build_main_area(self):
        # Top toolbar
        toolbar = ctk.CTkFrame(
            self.main_area, height=42,
            fg_color=self.ui["panel"]
        )
        toolbar.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        toolbar.pack_propagate(False)

        # Status info
        self.status_label = ctk.CTkLabel(
            toolbar,
            text="Load an image to begin",
            font=ctk.CTkFont(family=self.ui["font"], size=11),
            text_color=self.ui["muted"]
        )
        self.status_label.pack(side="left", padx=12, pady=4)

        # Spacer
        spacer = ctk.CTkFrame(toolbar, fg_color="transparent")
        spacer.pack(side="left", fill="x", expand=True)

        # View mode buttons
        ctk.CTkLabel(
            toolbar, text="View:",
            font=ctk.CTkFont(family=self.ui["font"], size=10),
            text_color=self.ui["muted"]
        ).pack(side="right", padx=(0, 8))
        
        for label, val in [("Source", "original"), ("Preview", "processed"), ("Split", "split")]:
            ctk.CTkButton(
                toolbar, text=label, width=90,
                command=lambda v=val: self.set_view_mode(v),
                fg_color=self.ui["panel_alt"], hover_color=self.ui["accent"],
                height=28, border_width=1, border_color=self.ui["border"]
            ).pack(side="right", padx=2, pady=3)

        # Main separator
        sep = ctk.CTkFrame(self.main_area, height=1, fg_color=self.ui["border"])
        sep.grid(row=1, column=0, sticky="ew", padx=0, pady=0)

        # Canvas area with labels and buttons
        self.canvas_frame = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.canvas_frame.grid(row=2, column=0, sticky="nsew", padx=0, pady=0)
        self.canvas_frame.grid_rowconfigure(0, weight=1)
        self.canvas_frame.grid_columnconfigure(0, weight=1, uniform="canvas_col")
        self.canvas_frame.grid_columnconfigure(1, weight=1, uniform="canvas_col")

        # Original image section
        self.orig_frame = ctk.CTkFrame(self.canvas_frame, fg_color="transparent")
        self.orig_frame.grid(row=0, column=0, sticky="nsew", padx=2, pady=0)
        self.orig_frame.grid_rowconfigure(0, weight=0)
        self.orig_frame.grid_rowconfigure(1, weight=1)
        self.orig_frame.grid_rowconfigure(2, weight=0)
        self.orig_frame.grid_columnconfigure(0, weight=1)
        
        label_orig = ctk.CTkLabel(
            self.orig_frame, text="Source",
            font=ctk.CTkFont(family=self.ui["font"], size=10, weight="bold"),
            text_color=self.ui["text"], height=16
        )
        label_orig.grid(row=0, column=0, sticky="ew", padx=0, pady=2)
        
        self.img_orig = ctk.CTkLabel(
            self.orig_frame, text="Open an image",
            fg_color=self.ui["panel"], corner_radius=10
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
            self.proc_frame, text="Preview",
            font=ctk.CTkFont(family=self.ui["font"], size=10, weight="bold"),
            text_color=self.ui["accent"], height=16
        )
        label_proc.grid(row=0, column=0, sticky="ew", padx=0, pady=2)
        
        self.img_proc = ctk.CTkLabel(
            self.proc_frame, text="",
            fg_color=self.ui["panel"], corner_radius=10
        )
        self.img_proc.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)

        # Apply button row
        button_frame = ctk.CTkFrame(self.proc_frame, fg_color="transparent", height=28)
        button_frame.grid(row=2, column=0, sticky="ew", padx=0, pady=0)
        button_frame.grid_propagate(False)
        
        ctk.CTkButton(
            button_frame, text="Apply Changes",
            command=self.apply_changes,
            fg_color=self.ui["success"], hover_color=self.ui["success_hover"],
            height=26, font=ctk.CTkFont(family=self.ui["font"], size=9, weight="bold"),
            border_width=1, border_color=self.ui["border"]
        ).pack(side="right", padx=2, pady=1)
        
        ctk.CTkButton(
            button_frame, text="Undo",
            command=self.undo_changes,
            fg_color=self.ui["danger"], hover_color=self.ui["danger_hover"],
            height=26, font=ctk.CTkFont(family=self.ui["font"], size=9, weight="bold"),
            border_width=1, border_color=self.ui["border"]
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

        current_view = self._overlay_roi_outline(self.current_image)
        preview_view = self._overlay_roi_outline(self.preview_image)
        
        # Use actual drawable area from canvas container to avoid offsets.
        self.update_idletasks()
        canvas_w = max(320, self.canvas_frame.winfo_width() - 8)
        canvas_h = max(260, self.canvas_frame.winfo_height() - 8)
        h = max(200, canvas_h - 44)

        # Control what displays based on view mode
        if self.display_mode == "split":
            # Split: Left=current output, Right=preview (editing)
            w = max(180, (canvas_w - 4) // 2)
            self.orig_frame.grid(row=0, column=0, columnspan=1, sticky="nsew", padx=2, pady=0)
            self.proc_frame.grid(row=0, column=1, columnspan=1, sticky="nsew", padx=2, pady=0)
            self._show_cv(self.img_orig, current_view, w, h)
            self._show_cv(self.img_proc, preview_view, w, h)
        elif self.display_mode == "original":
            # Compare: Left=original (as uploaded), Right=current (edited)
            w = max(180, (canvas_w - 4) // 2)
            self.orig_frame.grid(row=0, column=0, columnspan=1, sticky="nsew", padx=2, pady=0)
            self.proc_frame.grid(row=0, column=1, columnspan=1, sticky="nsew", padx=2, pady=0)
            self._show_cv(self.img_orig, self.original_image, w, h)
            self._show_cv(self.img_proc, current_view, w, h)
        else:  # processed
            # Processed: Show only right pane with preview
            w = max(280, canvas_w - 2)
            self.orig_frame.grid_remove()
            self.proc_frame.grid(row=0, column=0, columnspan=2, sticky="nsew", padx=2, pady=0)
            self._show_cv(self.img_proc, preview_view, w, h)

    def _overlay_roi_outline(self, image):
        """Render selected ROI contour on top of image for clearer visual feedback."""
        if image is None or self.roi_mask is None:
            return image

        if self.roi_mask.shape[:2] != image.shape[:2]:
            mask = cv2.resize(self.roi_mask, (image.shape[1], image.shape[0]), interpolation=cv2.INTER_NEAREST)
        else:
            mask = self.roi_mask

        if cv2.countNonZero(mask) == 0:
            return image

        outlined = image.copy()
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            # High-contrast dual stroke is easier to read than yellow on bright cartoons.
            cv2.drawContours(outlined, contours, -1, (255, 255, 255), 5)
            cv2.drawContours(outlined, contours, -1, (0, 0, 255), 3)
        return outlined

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
    def _schedule_adjustment(self, kind, delay_ms=60):
        """Debounce slider updates so dragging feels smoother."""
        self.pending_adjustment = kind
        if self.adjust_timer is not None:
            self.after_cancel(self.adjust_timer)
            self.adjust_timer = None
        self.adjust_timer = self.after(delay_ms, self._run_pending_adjustment)

    def _run_pending_adjustment(self):
        self.adjust_timer = None
        kind = self.pending_adjustment
        self.pending_adjustment = None

        if kind == "bc":
            self.apply_brightness_contrast()
        elif kind == "gamma":
            self.apply_gamma()

    def _on_brightness_change(self, val):
        b = int(float(val))
        self.bright_label.configure(text=f"{b:+d}")
        self._schedule_adjustment("bc")

    def _on_contrast_change(self, val):
        c = float(val)
        self.contrast_label.configure(text=f"{c:.2f}")
        self._schedule_adjustment("bc")

    def _on_gamma_change(self, val):
        gamma_val = float(val)
        self.gamma_label.configure(
            text=f"{gamma_val:.2f}" + ("←Darker" if gamma_val < 1 else "→Brighter" if gamma_val > 1 else "")
        )
        self._schedule_adjustment("gamma")

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

        self.status_label.configure(
            text="ROI mode: hold left mouse and trace around the object boundary"
        )
        
        # Create a temporary window for ROI drawing
        self._show_roi_window()

    def _show_roi_window(self):
        """Display image in a window for freehand ROI tracing"""
        from tkinter import Canvas
        
        roi_win = ctk.CTkToplevel(self)
        roi_win.title("Trace Object - Hold Mouse and Draw Around Object")
        roi_win.geometry("1000x650")
        roi_win.transient(self)
        try:
            roi_win.attributes("-topmost", True)
        except Exception:
            pass
        roi_win.lift()
        roi_win.focus_force()
        self.after(250, lambda: roi_win.attributes("-topmost", False) if roi_win.winfo_exists() else None)
        
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
        trace_points = [[]]
        line_ids = [[]]
        pending_lasso_mask = [None]
        pending_bbox = [None]

        def _clamp_display_point(x, y):
            cx = max(0, min(int(x), display_w - 1))
            cy = max(0, min(int(y), display_h - 1))
            return cx, cy

        def _clear_trace():
            for lid in line_ids[0]:
                canvas.delete(lid)
            line_ids[0].clear()
            trace_points[0] = []

        def _reset_pending():
            pending_lasso_mask[0] = None
            pending_bbox[0] = None
            apply_btn.configure(state="disabled")
            info.configure(text="Hold left mouse and trace around the object boundary, then release to preview")

        def on_mouse_down(event):
            drawing[0] = True
            _clear_trace()
            trace_points[0].append(_clamp_display_point(event.x, event.y))
            _reset_pending()

        def on_mouse_drag(event):
            if not drawing[0] or not trace_points[0]:
                return

            x, y = _clamp_display_point(event.x, event.y)
            px, py = trace_points[0][-1]

            # Ignore tiny moves to reduce noisy edges.
            if abs(x - px) + abs(y - py) < 2:
                return

            trace_points[0].append((x, y))
            line_ids[0].append(
                canvas.create_line(px, py, x, y, fill="#46d18b", width=2, smooth=True)
            )

        def on_mouse_up(event):
            if not drawing[0] or not trace_points[0]:
                return

            drawing[0] = False
            end_point = _clamp_display_point(event.x, event.y)
            if trace_points[0][-1] != end_point:
                trace_points[0].append(end_point)

            if len(trace_points[0]) < 12:
                messagebox.showwarning("Too short", "Please trace a longer contour around the object.")
                return

            sx, sy = trace_points[0][0]
            ex, ey = trace_points[0][-1]
            line_ids[0].append(canvas.create_line(ex, ey, sx, sy, fill="#46d18b", width=2, smooth=True))

            pts_disp = np.array(trace_points[0], dtype=np.float32)
            if scale > 0:
                pts_orig = np.round(pts_disp / scale).astype(np.int32)
            else:
                pts_orig = pts_disp.astype(np.int32)

            pts_orig[:, 0] = np.clip(pts_orig[:, 0], 0, orig_w - 1)
            pts_orig[:, 1] = np.clip(pts_orig[:, 1], 0, orig_h - 1)

            contour_area = abs(cv2.contourArea(pts_orig))
            if contour_area < 120:
                messagebox.showwarning("Too small", "Traced area is too small. Please draw around the full object.")
                return

            traced_mask = np.zeros((orig_h, orig_w), dtype=np.uint8)
            cv2.fillPoly(traced_mask, [pts_orig], 255)

            x1, x2 = int(pts_orig[:, 0].min()), int(pts_orig[:, 0].max())
            y1, y2 = int(pts_orig[:, 1].min()), int(pts_orig[:, 1].max())
            pending_lasso_mask[0] = traced_mask
            pending_bbox[0] = (x1, y1, x2, y2)
            apply_btn.configure(state="normal")
            info.configure(text="Contour ready. Click Apply Selection to extract object, or draw again to replace.")

        def apply_selection():
            if pending_lasso_mask[0] is None or pending_bbox[0] is None:
                messagebox.showwarning("No selection", "Please draw a contour first.")
                return

            apply_btn.configure(state="disabled")
            info.configure(text="Extracting object... please wait")
            roi_win.update_idletasks()

            try:
                edge_adjust = int(float(edge_slider.get())) if edge_slider is not None else 0
                mask = segment_object_from_lasso(
                    self.current_image,
                    pending_lasso_mask[0],
                    iterations=5,
                    tighten_iterations=2,
                    edge_adjust=edge_adjust,
                )
            except Exception as exc:
                apply_btn.configure(state="normal")
                info.configure(text="Segmentation failed. Draw tighter contour and click Apply again.")
                messagebox.showwarning(
                    "Segmentation warning",
                    f"Could not refine object inside traced contour.\n\n{exc}\n\nPlease redraw the contour a bit tighter around the object."
                )
                return

            # If result is too similar to whole traced region, fallback to rectangle object extraction.
            used_rect_fallback = False
            lasso_area = int(cv2.countNonZero(pending_lasso_mask[0]))
            mask_area = int(cv2.countNonZero(mask))
            if lasso_area > 0 and (mask_area / lasso_area) > 0.76:
                try:
                    rect_mask = segment_object_from_rect(
                        self.current_image,
                        pending_bbox[0],
                        iterations=7,
                        border_margin_ratio=0.1,
                        tighten_iterations=2,
                    )
                    safe_lasso = cv2.erode(
                        pending_lasso_mask[0],
                        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)),
                        iterations=1,
                    )
                    if cv2.countNonZero(safe_lasso) == 0:
                        safe_lasso = pending_lasso_mask[0]

                    merged = cv2.bitwise_and(rect_mask, safe_lasso)
                    if cv2.countNonZero(merged) > 0:
                        mask = merged
                        used_rect_fallback = True
                except Exception:
                    pass

            ys, xs = np.where(mask > 0)
            if len(xs) == 0 or len(ys) == 0:
                apply_btn.configure(state="normal")
                info.configure(text="No object found. Please redraw contour.")
                messagebox.showwarning("Empty mask", "No valid ROI found. Please redraw the contour.")
                return

            self.roi_mask = mask
            x1, x2 = int(xs.min()), int(xs.max())
            y1, y2 = int(ys.min()), int(ys.max())
            mask_area = int(cv2.countNonZero(self.roi_mask))
            self.status_label.configure(
                text=(
                    f"Object selected: ({x1},{y1}) to ({x2},{y2}) - Mask area: {mask_area}px²"
                    + (" | mode: object-in-box" if used_rect_fallback else " | mode: lasso-refine")
                )
            )
            self.refresh_display()

            roi_win.destroy()
            messagebox.showinfo("Success", "ROI applied. Filters will be applied only on the selected object.")

        def redraw_selection():
            _clear_trace()
            _reset_pending()
        
        # Bind events
        canvas.bind("<Button-1>", on_mouse_down)
        canvas.bind("<B1-Motion>", on_mouse_drag)
        canvas.bind("<ButtonRelease-1>", on_mouse_up)

        controls = ctk.CTkFrame(roi_win, fg_color="transparent")
        controls.pack(pady=(2, 6))

        ctk.CTkButton(
            controls,
            text="Redraw",
            command=redraw_selection,
            fg_color=self.ui["panel_alt"],
            hover_color=self.ui["accent"],
            border_width=1,
            border_color=self.ui["border"],
            width=120
        ).pack(side="left", padx=6)

        apply_btn = ctk.CTkButton(
            controls,
            text="Apply Selection",
            command=apply_selection,
            state="disabled",
            fg_color=self.ui["success"],
            hover_color=self.ui["success_hover"],
            border_width=1,
            border_color=self.ui["border"],
            width=140
        )
        apply_btn.pack(side="left", padx=6)

        edge_frame = ctk.CTkFrame(roi_win, fg_color="transparent")
        edge_frame.pack(pady=(0, 6))
        ctk.CTkLabel(
            edge_frame,
            text="Edge Tighten",
            font=ctk.CTkFont(family=self.ui["font"], size=10, weight="bold"),
            text_color=self.ui["text"]
        ).pack(side="left", padx=(0, 8))
        edge_value = ctk.StringVar(value="0")
        edge_label = ctk.CTkLabel(edge_frame, textvariable=edge_value, text_color=self.ui["muted"])
        edge_label.pack(side="right", padx=(8, 0))
        edge_slider = ctk.CTkSlider(
            edge_frame,
            from_=-4, to=4,
            number_of_steps=8,
            width=220,
            command=lambda v: edge_value.set(str(int(float(v))))
        )
        edge_slider.set(0)
        edge_slider.pack(side="right")

        ctk.CTkButton(
            controls,
            text="Cancel",
            command=roi_win.destroy,
            fg_color=self.ui["danger"],
            hover_color=self.ui["danger_hover"],
            border_width=1,
            border_color=self.ui["border"],
            width=100
        ).pack(side="left", padx=6)
        
        # Instructions
        info = ctk.CTkLabel(
            roi_win,
            text="Hold left mouse and trace around the object boundary, then release to preview",
            font=ctk.CTkFont(family=self.ui["font"], size=10),
            text_color=self.ui["muted"]
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
        win.configure(fg_color=self.ui["main"])
        
        fig, axes = plt.subplots(1, 2, figsize=(12, 4), facecolor=self.ui["main"])
        colors_bgr = [self.ui["accent"], self.ui["success"], self.ui["danger"]]
        labels = ['Blue', 'Green', 'Red']
        
        for ax, img, title in zip(
            axes,
            [self.original_image, self.current_image],
            ["Original", "Current"]
        ):
            ax.set_facecolor(self.ui["panel"])
            ax.set_title(title, color=self.ui["accent"], fontsize=13, weight="bold")
            ax.tick_params(colors=self.ui["muted"])
            
            for spine in ax.spines.values():
                spine.set_edgecolor(self.ui["border"])
            
            if len(img.shape) == 2:
                hist = cv2.calcHist([img], [0], None, [256], [0, 256])
                ax.plot(hist, color=self.ui["accent"], linewidth=1.5)
            elif img.shape[2] == 3:
                for i, (c, lbl) in enumerate(zip(colors_bgr, labels)):
                    hist = cv2.calcHist([img], [i], None, [256], [0, 256])
                    ax.plot(hist, color=c, linewidth=1.5, label=lbl, alpha=0.85)
                ax.legend(facecolor=self.ui["panel"], labelcolor="white", fontsize=9)
            
            ax.set_xlim([0, 256])
        
        plt.tight_layout(pad=2)
        canvas = FigureCanvasTkAgg(fig, master=win)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)


if __name__ == "__main__":
    app = DIPTool()
    app.display_mode = "split"
    app.mainloop()
