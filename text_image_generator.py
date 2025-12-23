#!/usr/bin/env python3

"""
Text Image Generator for Source 2 Hammer
Generates white text on transparent background with threaded loading, optimized rendering,
and VMAT generation.
"""

import sys
import subprocess
import importlib.util
import os
import platform
import threading
import time
import datetime
import traceback
import json
from concurrent.futures import ThreadPoolExecutor

# ============================================================================
# LOGGING & COLORS (Standardized)
# ============================================================================

class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    GRAY = "\033[90m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"

class Log:
    @staticmethod
    def _timestamp():
        return datetime.datetime.now().strftime("%H:%M:%S")

    @staticmethod
    def info(tag, message):
        print(f"{Colors.GRAY}[{Log._timestamp()}]{Colors.RESET} {Colors.BLUE}[{tag}]{Colors.RESET} {message}")

    @staticmethod
    def success(tag, message, time_taken=None):
        t_str = f" {Colors.MAGENTA}[{time_taken:.2f}s]{Colors.RESET}" if time_taken is not None else ""
        print(f"{Colors.GRAY}[{Log._timestamp()}]{Colors.RESET} {Colors.GREEN}[{tag}]{Colors.RESET} {message}{t_str}")

    @staticmethod
    def warning(tag, message):
        print(f"{Colors.GRAY}[{Log._timestamp()}]{Colors.RESET} {Colors.YELLOW}[{tag}]{Colors.RESET} {message}")

    @staticmethod
    def error(tag, message):
        print(f"{Colors.GRAY}[{Log._timestamp()}]{Colors.RESET} {Colors.RED}[{tag}]{Colors.RESET} {message}")

    @staticmethod
    def section(title):
        print(f"\n{Colors.BOLD}{Colors.WHITE}=== {title} ==={Colors.RESET}")

    @staticmethod
    def trace(tag, exc):
        print(f"{Colors.GRAY}[{Log._timestamp()}]{Colors.RESET} {Colors.RED}[{tag} EXCEPTION]{Colors.RESET} {exc}")
        traceback.print_exc()

if os.name == 'nt':
    os.system('color')

# ============================================================================
# OPTIMIZED IMPORTS (Optimistic Loading)
# ============================================================================

def _install_and_retry():
    """Only runs if imports fail. Installs packages and restarts."""
    Log.section("INSTALLING MISSING LIBRARIES")
    required = {'Pillow': 'PIL', 'customtkinter': 'customtkinter'}
    
    for package, import_name in required.items():
        try:
            importlib.import_module(import_name)
        except ImportError:
            Log.warning("SYS", f"Installing {package}...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", package])
                Log.success("SYS", f"Installed {package}")
            except subprocess.CalledProcessError:
                Log.error("SYS", f"Failed to install {package}.")
                sys.exit(1)
    
    Log.success("SYS", "Dependencies installed. Restarting...")
    # Restart the script to load new libraries cleanly
    os.execv(sys.executable, ['python'] + sys.argv)

try:
    # 1. Try to import normally (Fastest path: 0ms overhead)
    import tkinter as tk
    from tkinter import filedialog, messagebox, colorchooser
    import customtkinter as ctk
    from PIL import Image, ImageDraw, ImageFont, ImageTk
except ImportError:
    # 2. Only if that fails, run the slow installation logic
    _install_and_retry()

# --- WEB THEME CONFIGURATION (MATCHING LAYER GENERATOR) ---
class WebTheme:
    BG_MAIN = "#1b1b1b"        # Deepest dark background
    BG_CARD = "#1e1e1e"        # Card/Panel background
    BG_INPUT = "#121212"       # Input field background
    BORDER = "#3f3f46"         # Panel border color
    
    TEXT = "#ffffff"           # Primary white text
    TEXT_DIM = "#a1a1aa"       # Dimmed text (Zinc-400)
    
    # Primary (Blue)
    PRIMARY = "#3b82f6"        # "Download" Blue (Blue-500)
    PRIMARY_HOVER = "#2563eb"  # Darker Blue hover (Blue-600)
    PRIMARY_BORDER = "#60a5fa" # Lighter Blue for border (Blue-400)
    
    SECONDARY = "#10b981"      # "Material" Green (Emerald-500)
    SECONDARY_HOVER = "#059669"
    SECONDARY_BORDER = "#6ee7b7"
    
    # Neutral / Surface Buttons
    BTN_SURFACE = "#27272a"    # Neutral button background (Zinc-800)
    BTN_HOVER = "#3f3f46"      # Neutral button hover (Zinc-700)
    BTN_BORDER = "#52525b"     # Lighter border for neutral buttons (Zinc-600)
    
    # Danger (Red)
    DANGER = "#ef4444"         # Red-500
    DANGER_BORDER = "#f87171"  # Lighter Red for border (Red-400)
    
    RADIUS = 8                 # Rounded corners

# Configuration for CustomTkinter
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

# ============================================================================
# MAIN APPLICATION
# ============================================================================

class TextImageGenerator:
    def __init__(self):
        Log.section("INITIALIZATION")
        Log.info("GUI", "Initializing UI Window...")

        self.root = ctk.CTk()
        self.root.title("Text Image Generator")
        self.root.geometry("1100x850")
        
        # Apply Main Web Theme Background
        self.root.configure(fg_color=WebTheme.BG_MAIN)
        
        # --- Core State ---
        self.current_size = ctk.IntVar(value=512)
        self.text_align_var = ctk.StringVar(value="Center")
        self.text_position_var = ctk.StringVar(value="Center")
        
        # Padding State
        self.padding_var = ctk.IntVar(value=20)
        self.padding_str_var = ctk.StringVar(value="20")

        # Line Spacing State
        self.line_spacing_var = ctk.IntVar(value=4)
        self.line_spacing_str_var = ctk.StringVar(value="4")
        
        self.font_size_var = ctk.IntVar(value=50)
        self.font_size_str_var = ctk.StringVar(value="50")
        self.font_family_var = ctk.StringVar(value="calibri") 
        
        # --- Colors ---
        self.outline_color_hex = "#000000"
        self.outline_color_rgb = (0, 0, 0, 255)
        self.text_color_hex = "#FFFFFF"
        self.text_color_rgb = (255, 255, 255, 255)
        
        # --- Layers State ---
        self.outline_enabled = ctk.BooleanVar(value=False)
        self.outline_width_var = ctk.IntVar(value=4)
        self.outline_width_str_var = ctk.StringVar(value="4")
        
        # Export
        self.filename_var = ctk.StringVar(value="text_layer")
        self.mask_layer_enabled = ctk.BooleanVar(value=False)
        self.vmat_enabled = ctk.BooleanVar(value=False)
        self.shader_var = ctk.StringVar(value="csgo_static_overlay.vfx")
        
        # --- Optimization Caches ---
        self.font_paths = {} 
        self.available_fonts = []
        self._font_obj_cache = {}
        self._checkerboard_cache = {}
        self.preview_image_ref = None
        self.font_preview_cache = {}
        
        # Threading
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.debounce_timer = None
        self.preview_req_id = 0
        
        # --- UI Setup ---
        self.create_widgets()
        self.setup_window_geometry()
        
        # Start background tasks
        self.start_font_scan()
        
        # Initial Preview
        self.root.after(200, self.trigger_preview_update)
        
        Log.success("GUI", "Window initialized successfully.")

    def setup_window_geometry(self):
        width = 1100
        height = 800
        
        # Center it
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.minsize(1000, 600)

    # --- SYSTEM PATH HELPER ---
    def _get_cache_file_path(self):
        """Determines the system-appropriate path for the cache file."""
        app_name = "Source2TextImageGenerator"
        
        if platform.system() == "Windows":
            base_path = os.getenv('LOCALAPPDATA') or os.path.expanduser("~\\AppData\\Local")
        elif platform.system() == "Darwin":
            base_path = os.path.expanduser("~/Library/Application Support")
        else:
            # Linux / Unix standard (XDG)
            base_path = os.path.expanduser("~/.local/share")
            
        # Ensure the directory exists
        full_dir = os.path.join(base_path, app_name)
        try:
            os.makedirs(full_dir, exist_ok=True)
        except OSError:
            # Fallback to local execution dir if permissions fail
            Log.warning("SYS", "Could not create system appdata folder, using local dir.")
            return "font_cache.json"

        return os.path.join(full_dir, "font_cache.json")

    # --- OPTIMIZED FONT SCANNING (CACHED) ---
    def start_font_scan(self):
        threading.Thread(target=self._scan_fonts_thread, daemon=True).start()

    def _scan_fonts_thread(self):
        # 1. ATTEMPT TO LOAD FROM CACHE
        cache_file = self._get_cache_file_path()
        
        if os.path.exists(cache_file):
            try:
                Log.info("FONT", f"Checking font cache at: {cache_file}")
                with open(cache_file, "r") as f:
                    data = json.load(f)
                    self.available_fonts = data["names"]
                    self.font_paths = data["paths"]
                    Log.success("FONT", f"Loaded {len(self.available_fonts)} fonts from cache (FAST).")
                    return # Exit early if cache is good
            except Exception as e:
                Log.warning("FONT", f"Cache corrupted ({e}), rescanning system...")

        # 2. PERFORM SYSTEM SCAN (If no cache or cache failed)
        Log.info("FONT", "Scanning system fonts (This may take a moment)...")
        if platform.system() == "Windows":
            font_dirs = [r"C:\Windows\Fonts", os.path.expanduser(r"~\AppData\Local\Microsoft\Windows\Fonts")]
        elif platform.system() == "Darwin":
            font_dirs = ["/Library/Fonts", "/System/Library/Fonts", os.path.expanduser("~/Library/Fonts")]
        else:
            font_dirs = ["/usr/share/fonts", os.path.expanduser("~/.fonts"), os.path.expanduser("~/.local/share/fonts")]
        
        temp_paths = {}
        verified_fonts = []
        
        for font_dir in font_dirs:
            if not os.path.exists(font_dir): continue
            for root, _, files in os.walk(font_dir):
                for file in files:
                    if file.lower().endswith(('.ttf', '.otf')):
                        font_name = os.path.splitext(file)[0]
                        # Clean up common font name suffixes for cleaner UI
                        for suffix in ['-Regular', '-Bold', 'Regular', 'Bold', 'Italic', '-Italic']:
                            if font_name.endswith(suffix):
                                font_name = font_name[:-len(suffix)]
                                break
                        if font_name and font_name not in temp_paths:
                            verified_fonts.append(font_name)
                            temp_paths[font_name] = os.path.join(root, file)

        self.available_fonts = sorted(list(set(verified_fonts)))
        self.font_paths = temp_paths
        
        # 3. SAVE TO CACHE
        try:
            with open(cache_file, "w") as f:
                json.dump({"names": self.available_fonts, "paths": self.font_paths}, f)
            Log.success("FONT", f"Found {len(self.available_fonts)} fonts and saved to {cache_file}.")
        except Exception as e:
            Log.error("FONT", f"Failed to save font cache: {e}")

    # --- UI CREATION ---
    def create_widgets(self):
        self.root.columnconfigure(0, weight=0)
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)

        # LEFT PANEL CONTAINER (Holds the border)
        self.left_container = ctk.CTkFrame(
            self.root,
            width=440,
            fg_color=WebTheme.BG_CARD,
            border_width=1,
            border_color=WebTheme.BORDER,
            corner_radius=WebTheme.RADIUS
        )
        self.left_container.grid(row=0, column=0, sticky="nsew", padx=15, pady=15)
        
        # Configure grid for container
        self.left_container.columnconfigure(0, weight=1)
        self.left_container.rowconfigure(0, weight=1)

        # LEFT PANEL (Scrollable Content - Transparent, inside container)
        # Added explicit width=440 to prevent shrinking
        self.left_panel = ctk.CTkScrollableFrame(
            self.left_container, 
            width=440,
            fg_color="transparent",
            border_width=0,             
            corner_radius=WebTheme.RADIUS
        )
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=3, pady=3)
        
        # Spacer for top margin
        ctk.CTkFrame(self.left_panel, height=5, fg_color="transparent").pack()

        self.create_input_section()
        self.create_size_section()
        self.create_font_section()
        self.create_effects_section()
        self.create_output_section()

        # RIGHT PANEL (Preview) - Card Style
        self.right_panel = ctk.CTkFrame(self.root, fg_color=WebTheme.BG_CARD, border_width=1, border_color=WebTheme.BORDER, corner_radius=WebTheme.RADIUS)
        self.right_panel.grid(row=0, column=1, sticky="nsew", padx=(0, 15), pady=15)
        self.right_panel.columnconfigure(0, weight=1)
        self.right_panel.rowconfigure(0, weight=1)
        self.right_panel.rowconfigure(1, weight=0)
        
        # Preview Label
        self.preview_label = ctk.CTkLabel(self.right_panel, text="Generating Preview...", text_color=WebTheme.TEXT_DIM)
        self.preview_label.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        btn_frame = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        btn_frame.grid(row=1, column=0, sticky="ew", padx=15, pady=(0, 15))
        btn_frame.columnconfigure(0, weight=1)
        btn_frame.columnconfigure(1, weight=1)
        
        # Generate Button (Primary Style)
        self.gen_btn = ctk.CTkButton(
            btn_frame, text="Generate & Save Image", command=self.generate_image, height=40, font=("Segoe UI", 13, "bold"),
            fg_color=WebTheme.PRIMARY, hover_color=WebTheme.PRIMARY_HOVER, text_color=WebTheme.TEXT,
            border_width=1, border_color=WebTheme.PRIMARY_BORDER, corner_radius=WebTheme.RADIUS
        )
        self.gen_btn.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        
        # Numbers Button (Neutral Style)
        self.num_btn = ctk.CTkButton(
            btn_frame, text="Generate Numbers (0-9)", command=self.generate_numbers, height=40, font=("Segoe UI", 13, "bold"),
            fg_color=WebTheme.BTN_SURFACE, hover_color=WebTheme.BTN_HOVER, text_color=WebTheme.TEXT,
            border_width=1, border_color=WebTheme.BTN_BORDER, corner_radius=WebTheme.RADIUS
        )
        self.num_btn.grid(row=0, column=1, sticky="ew", padx=(5, 0))

    def create_section_frame(self, title):
        # Transparent Container (No outline, no background)
        frame = ctk.CTkFrame(
            self.left_panel, 
            fg_color="transparent",
            border_width=0
        )
        frame.pack(fill="x", pady=(0, 2))
        
        # Header inside panel
        h = ctk.CTkFrame(frame, fg_color="transparent")
        h.pack(fill="x", padx=10, pady=(10, 5))
        ctk.CTkLabel(h, text=title, font=("Segoe UI", 13, "bold"), text_color=WebTheme.TEXT).pack(side="left")
        
        # Separator Line (To distinguish sections without boxes)
        sep = ctk.CTkFrame(frame, height=1, fg_color=WebTheme.BORDER)
        sep.pack(fill="x", padx=10, pady=(0, 10))

        content = ctk.CTkFrame(frame, fg_color="transparent")
        content.pack(fill="x", padx=5, pady=(0, 5))
        return content

    def create_property_slider(self, parent, label_text, int_var, str_var, min_val, max_val, command):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=(0, 5))
        
        ctk.CTkLabel(row, text=label_text, width=60, anchor="w", font=("Segoe UI", 12), text_color=WebTheme.TEXT_DIM).pack(side="left")
        
        # Styled Entry
        entry = ctk.CTkEntry(
            row, textvariable=str_var, width=50, height=24,
            fg_color=WebTheme.BG_INPUT, border_color=WebTheme.BORDER, border_width=1, 
            text_color=WebTheme.TEXT, corner_radius=WebTheme.RADIUS
        )
        entry.pack(side="right")
        
        # Styled Slider
        slider = ctk.CTkSlider(
            row, from_=min_val, to=max_val, variable=int_var, command=lambda v: command(v, int_var, str_var), height=16,
            button_color=WebTheme.PRIMARY, button_hover_color=WebTheme.PRIMARY_HOVER, progress_color=WebTheme.PRIMARY
        )
        slider.pack(side="left", fill="x", expand=True, padx=8)
        
        def on_entry(event=None):
            try:
                val = float(str_var.get())
                if val < min_val: val = min_val
                current_max = slider.cget("to")
                if val > current_max: val = current_max
                
                int_var.set(val)
                str_var.set(str(round(val, 2) if isinstance(val, float) else int(val)))
                self.trigger_preview_update()
            except ValueError: pass
            
        entry.bind("<Return>", on_entry)
        entry.bind("<FocusOut>", on_entry)
        return slider

    def create_input_section(self):
        parent = self.create_section_frame("TEXT CONTENT")
        
        # Styled Textbox
        self.text_input = ctk.CTkTextbox(
            parent, 
            height=60, 
            wrap="word",
            border_width=1,
            corner_radius=WebTheme.RADIUS,
            fg_color=WebTheme.BG_INPUT,
            border_color=WebTheme.BORDER,
            text_color=WebTheme.TEXT,
            font=("Segoe UI", 12)
        )
        self.text_input.insert("1.0", "SAMPLE TEXT")
        self.text_input.pack(fill="x", padx=10, pady=(0, 10))
        self.text_input.bind("<KeyRelease>", self._on_text_key_release)
        
        # Color Button
        self.color_btn = ctk.CTkButton(
            parent, text="Choose Color", command=self.choose_text_color, 
            fg_color=WebTheme.BTN_SURFACE, hover_color=WebTheme.BTN_HOVER, 
            border_color=WebTheme.BTN_BORDER, border_width=1,
            height=28, corner_radius=WebTheme.RADIUS, text_color=WebTheme.TEXT
        )
        self.color_btn.pack(fill="x", padx=10, pady=(0, 5))

        # Alignment Control
        align_row = ctk.CTkFrame(parent, fg_color="transparent")
        align_row.pack(fill="x", padx=10, pady=(0, 5))
        
        ctk.CTkLabel(align_row, text="Alignment:", width=70, anchor="w", font=("Segoe UI", 12), text_color=WebTheme.TEXT_DIM).pack(side="left")
        
        self.align_menu = ctk.CTkComboBox(
            align_row, 
            values=["Left", "Center", "Right"],
            variable=self.text_align_var,
            command=lambda x: self.trigger_preview_update(),
            height=28,
            fg_color=WebTheme.BG_INPUT, 
            button_color=WebTheme.BORDER, button_hover_color=WebTheme.BTN_HOVER,
            border_color=WebTheme.BORDER, border_width=1,
            text_color=WebTheme.TEXT, corner_radius=WebTheme.RADIUS, dropdown_fg_color=WebTheme.BG_CARD
        )
        self.align_menu.pack(side="left", fill="x", expand=True)

        # Position Control
        pos_row = ctk.CTkFrame(parent, fg_color="transparent")
        pos_row.pack(fill="x", padx=10, pady=(0, 5))
        
        ctk.CTkLabel(pos_row, text="Position:", width=70, anchor="w", font=("Segoe UI", 12), text_color=WebTheme.TEXT_DIM).pack(side="left")
        
        self.pos_menu = ctk.CTkComboBox(
            pos_row, 
            values=[
                "Top Left", "Top Center", "Top Right",
                "Middle Left", "Center", "Middle Right",
                "Bottom Left", "Bottom Center", "Bottom Right"
            ],
            variable=self.text_position_var,
            command=lambda x: self.trigger_preview_update(),
            height=28,
            fg_color=WebTheme.BG_INPUT, 
            button_color=WebTheme.BORDER, button_hover_color=WebTheme.BTN_HOVER,
            border_color=WebTheme.BORDER, border_width=1,
            text_color=WebTheme.TEXT, corner_radius=WebTheme.RADIUS, dropdown_fg_color=WebTheme.BG_CARD
        )
        self.pos_menu.pack(side="left", fill="x", expand=True)

        # Padding Slider
        self.create_property_slider(
            parent, "Padding:",
            self.padding_var,
            self.padding_str_var,
            0, 200,
            self.generic_slider_update
        )

        # Line Spacing Slider
        self.create_property_slider(
            parent, "Line Spc:",
            self.line_spacing_var,
            self.line_spacing_str_var,
            -50, 150,
            self.generic_slider_update
        )

    def _on_text_key_release(self, event):
        self.trigger_preview_update()
        try:
            text_content = self.text_input.get("1.0", "end-1c")
            num_lines = text_content.count('\n') + 1
            new_height = min(max(60, 30 + (num_lines * 20)), 200)
            if self.text_input.cget("height") != new_height:
                self.text_input.configure(height=new_height)
        except:
            pass

    def create_size_section(self):
        parent = self.create_section_frame("RESOLUTION")
        grid = ctk.CTkFrame(parent, fg_color="transparent")
        grid.pack(fill="x", padx=5, pady=0)
        sizes = [("256x256", 256), ("512x512", 512), ("1024x1024", 1024)]
        for i, (txt, val) in enumerate(sizes):
            ctk.CTkRadioButton(
                grid, text=txt, variable=self.current_size, value=val, command=self.on_resolution_change, font=("Segoe UI", 12),
                fg_color=WebTheme.PRIMARY, hover_color=WebTheme.PRIMARY_HOVER, text_color=WebTheme.TEXT
            ).grid(row=0, column=i, padx=8)

    def create_font_section(self):
        parent = self.create_section_frame("TYPOGRAPHY")
        row1 = ctk.CTkFrame(parent, fg_color="transparent")
        row1.pack(fill="x", padx=10, pady=(0, 5))
        
        self.font_display = ctk.CTkEntry(
            row1, textvariable=self.font_family_var, state="readonly", height=28,
            fg_color=WebTheme.BG_INPUT, border_color=WebTheme.BORDER, border_width=1, 
            text_color=WebTheme.TEXT, corner_radius=WebTheme.RADIUS
        )
        self.font_display.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        ctk.CTkButton(
            row1, text="Browse", width=60, height=28, command=self.open_font_selector,
            fg_color=WebTheme.PRIMARY, hover_color=WebTheme.PRIMARY_HOVER, 
            border_width=1, border_color=WebTheme.PRIMARY_BORDER, corner_radius=WebTheme.RADIUS,
            text_color=WebTheme.TEXT
        ).pack(side="right")
        
        self.font_size_slider = self.create_property_slider(
            parent, "Size:", 
            self.font_size_var, 
            self.font_size_str_var, 
            12, 
            self.current_size.get(),  
            self.generic_slider_update
        )

    def create_effects_section(self):
        parent = self.create_section_frame("EFFECTS")
        
        # --- OUTLINE ---
        self.outline_container = ctk.CTkFrame(parent, fg_color="transparent")
        self.outline_container.pack(fill="x", pady=2)
        ctk.CTkCheckBox(
            self.outline_container, text="Enable Outline", variable=self.outline_enabled, command=self.toggle_effects, 
            font=("Segoe UI", 12), text_color=WebTheme.TEXT, 
            fg_color=WebTheme.PRIMARY, hover_color=WebTheme.PRIMARY_HOVER, corner_radius=8
        ).pack(anchor="w", padx=10, pady=(5, 5))
        
        self.outline_opts = ctk.CTkFrame(self.outline_container, fg_color="transparent")
        self.create_property_slider(self.outline_opts, "Width:", self.outline_width_var, self.outline_width_str_var, 0, 32, self.generic_slider_update)
        
        self.outline_color_btn = ctk.CTkButton(
            self.outline_opts, text="Outline Color", command=self.choose_outline_color, 
            fg_color=WebTheme.BTN_SURFACE, hover_color=WebTheme.BTN_HOVER, height=24,
            border_color=WebTheme.BTN_BORDER, border_width=1, corner_radius=WebTheme.RADIUS
        )
        self.outline_color_btn.pack(fill="x", padx=10, pady=(0, 5))

    def create_output_section(self):
        parent = self.create_section_frame("EXPORT")
        row1 = ctk.CTkFrame(parent, fg_color="transparent")
        row1.pack(fill="x", padx=10, pady=(0, 5))
        
        ctk.CTkLabel(row1, text="Prefix:", width=60, anchor="w", font=("Segoe UI", 12), text_color=WebTheme.TEXT_DIM).pack(side="left")
        
        ctk.CTkEntry(
            row1, textvariable=self.filename_var, height=28,
            fg_color=WebTheme.BG_INPUT, border_color=WebTheme.BORDER, border_width=1, 
            text_color=WebTheme.TEXT, corner_radius=WebTheme.RADIUS
        ).pack(side="left", fill="x", expand=True, padx=(10, 0))
        
        cb_conf = {"font": ("Segoe UI", 12), "text_color": WebTheme.TEXT, "fg_color": WebTheme.PRIMARY, "hover_color": WebTheme.PRIMARY_HOVER, "corner_radius": 8}

        ctk.CTkCheckBox(parent, text="Generate Transparency Mask", variable=self.mask_layer_enabled, **cb_conf).pack(anchor="w", padx=10, pady=(5, 5))
        ctk.CTkCheckBox(parent, text="Generate .vmat", variable=self.vmat_enabled, command=self.toggle_vmat_options, **cb_conf).pack(anchor="w", padx=10, pady=(0, 5))
        
        self.vmat_opts = ctk.CTkFrame(parent, fg_color="transparent")
        shader_row = ctk.CTkFrame(self.vmat_opts, fg_color="transparent")
        shader_row.pack(fill="x", padx=10, pady=(5, 0))
        
        ctk.CTkLabel(shader_row, text="Shader:", width=60, anchor="w", font=("Segoe UI", 12), text_color=WebTheme.TEXT_DIM).pack(side="left")
        
        self.shader_menu = ctk.CTkComboBox(
            shader_row, 
            values=["csgo_static_overlay.vfx", "csgo_complex.vfx"],
            variable=self.shader_var,
            width=200, height=28,                  
            corner_radius=WebTheme.RADIUS,            
            border_width=1,             
            border_color=WebTheme.BORDER,    
            fg_color=WebTheme.BG_INPUT,        
            button_color=WebTheme.BORDER,     
            button_hover_color=WebTheme.BTN_HOVER,
            text_color=WebTheme.TEXT,
            dropdown_fg_color=WebTheme.BG_CARD,
            state="readonly"            
        )
        self.shader_menu.pack(side="left")

        self.progress_bar = ctk.CTkProgressBar(parent, height=10, progress_color=WebTheme.SECONDARY, corner_radius=8)
        self.progress_bar.set(0) # Start empty
        self.progress_bar.pack(fill="x", padx=10, pady=(15, 2))

        self.status_lbl = ctk.CTkLabel(parent, text="Ready", text_color=WebTheme.PRIMARY, font=("Segoe UI", 11), anchor="w")
        self.status_lbl.pack(anchor="w", padx=10, pady=(2, 5))

    # ================= EVENT HANDLERS =================

    def toggle_effects(self):
        if self.outline_enabled.get(): self.outline_opts.pack(fill="x", padx=0, pady=(0, 5))
        else: self.outline_opts.pack_forget()
        self.trigger_preview_update()

    def toggle_vmat_options(self):
        if self.vmat_enabled.get():
            self.vmat_opts.pack(fill="x", padx=0, pady=(0, 5), before=self.progress_bar)
            self.mask_layer_enabled.set(True)
        else:
            self.vmat_opts.pack_forget()

    def generic_slider_update(self, value, int_var, str_var):
        if isinstance(int_var.get(), float):
            str_var.set(f"{float(value):.1f}")
        else:
            str_var.set(str(int(value)))
        self.trigger_preview_update()

    def on_resolution_change(self):
        new_res = self.current_size.get()
        if hasattr(self, 'font_size_slider'):
            self.font_size_slider.configure(to=new_res)
            current_val = self.font_size_var.get()
            if current_val > new_res:
                current_val = new_res
                self.font_size_var.set(current_val)
                self.font_size_str_var.set(str(current_val))
            self.font_size_slider.set(current_val)
        self.trigger_preview_update()

    def choose_text_color(self):
        color = colorchooser.askcolor(title="Text Color", initialcolor=self.text_color_hex)
        if color[1]:
            self.text_color_hex = color[1]
            self.text_color_rgb = (int(color[0][0]), int(color[0][1]), int(color[0][2]), 255)
            self.color_btn.configure(fg_color=color[1])
            rgb = color[0]
            brightness = (rgb[0] * 299 + rgb[1] * 587 + rgb[2] * 114) / 1000
            self.color_btn.configure(text_color="black" if brightness > 128 else "white")
            self.trigger_preview_update()

    def choose_outline_color(self):
        color = colorchooser.askcolor(title="Outline Color", initialcolor=self.outline_color_hex)
        if color[1]:
            self.outline_color_hex = color[1]
            self.outline_color_rgb = (int(color[0][0]), int(color[0][1]), int(color[0][2]), 255)
            self.outline_color_btn.configure(fg_color=color[1])
            rgb = color[0]
            brightness = (rgb[0] * 299 + rgb[1] * 587 + rgb[2] * 114) / 1000
            self.outline_color_btn.configure(text_color="black" if brightness > 128 else "white")
            self.trigger_preview_update()

    # ================= FONT SELECTOR =================

    def open_font_selector(self):
        self.root.update_idletasks()
        main_x = self.root.winfo_x()
        main_y = self.root.winfo_y()
        main_height = self.root.winfo_height()
        
        width = 320 
        height = main_height
        
        x = main_x - width - 10 
        y = main_y

        toplevel = ctk.CTkToplevel(self.root)
        toplevel.title("Select Font")
        toplevel.geometry(f"{width}x{height}+{x}+{y}")
        toplevel.configure(fg_color=WebTheme.BG_MAIN)
        toplevel.transient(self.root)
        toplevel.grab_set()
        
        # Header Frame (Search + Rescan Button)
        header_frame = ctk.CTkFrame(toplevel, fg_color=WebTheme.BG_CARD, border_width=1, border_color=WebTheme.BORDER)
        header_frame.pack(fill="x", padx=10, pady=10)
        
        search_var = ctk.StringVar()
        entry = ctk.CTkEntry(
            header_frame, textvariable=search_var, placeholder_text="Search...",
            fg_color=WebTheme.BG_INPUT, border_color=WebTheme.BORDER, border_width=1,
            text_color=WebTheme.TEXT, corner_radius=WebTheme.RADIUS
        )
        entry.pack(side="left", fill="x", expand=True, padx=5, pady=5)
        
        # RESCAN BUTTON
        def rescan_fonts_action():
            # Clear UI
            for widget in scroll_frame.winfo_children():
                widget.destroy()
            ctk.CTkLabel(scroll_frame, text="Clearing Cache...").pack(pady=5)
            
            # Clear internal lists
            self.available_fonts = []
            self.font_paths = {}
            
            # Delete cache file
            cache_file = self._get_cache_file_path()
            if os.path.exists(cache_file):
                try:
                    os.remove(cache_file)
                    Log.info("FONT", f"Deleted cache file: {cache_file}")
                except Exception as e: 
                    Log.error("FONT", f"Could not delete cache: {e}")
            
            # Start scan again
            self.start_font_scan()
            populate_fonts() # Will trigger the waiting loop

        rescan_btn = ctk.CTkButton(
            header_frame, text="Rescan", width=60, command=rescan_fonts_action,
            fg_color=WebTheme.BTN_SURFACE, hover_color=WebTheme.BTN_HOVER, border_width=1, border_color=WebTheme.BTN_BORDER
        )
        rescan_btn.pack(side="right", padx=5)
        
        scroll_frame = ctk.CTkScrollableFrame(toplevel, fg_color=WebTheme.BG_CARD)
        scroll_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        def populate_fonts(query=""):
            for widget in scroll_frame.winfo_children():
                widget.destroy()
            
            # Check if scanning is still in progress (empty list means scanning or empty system)
            if not self.available_fonts:
                ctk.CTkLabel(scroll_frame, text="Scanning System Fonts...\nPlease Wait.", text_color="orange").pack(pady=20)
                # Check again in 1 second
                toplevel.after(1000, lambda: populate_fonts(query))
                return

            fonts_to_show = [f for f in self.available_fonts if query.lower() in f.lower()]
            
            if not fonts_to_show:
                ctk.CTkLabel(scroll_frame, text="No fonts found.").pack(pady=20)
                return
                
            for font_name in fonts_to_show:
                self.create_font_item(scroll_frame, font_name, toplevel)

        def on_search(*args): populate_fonts(search_var.get())
        search_var.trace('w', on_search)
        toplevel.after(100, populate_fonts)

    def create_font_item(self, parent, font_name, toplevel):
        if font_name not in self.font_preview_cache:
            try:
                font_path = self.font_paths.get(font_name)
                pil_font = ImageFont.truetype(font_path, 24)
                w, h = 300, 40
                img_dark = Image.new("RGBA", (w, h), (0,0,0,0))
                ImageDraw.Draw(img_dark).text((5, 5), font_name, font=pil_font, fill="white")
                img_light = Image.new("RGBA", (w, h), (0,0,0,0))
                ImageDraw.Draw(img_light).text((5, 5), font_name, font=pil_font, fill="black")
                ctk_img = ctk.CTkImage(light_image=img_light, dark_image=img_dark, size=(w, h))
                self.font_preview_cache[font_name] = ctk_img
            except: self.font_preview_cache[font_name] = None

        lbl = ctk.CTkLabel(
            parent, text="" if self.font_preview_cache.get(font_name) else font_name, 
            image=self.font_preview_cache.get(font_name), fg_color="transparent", corner_radius=4, height=45, anchor="w"
        )
        lbl.pack(fill="x", pady=2)
        def on_click(e): self.select_font(font_name, toplevel)
        lbl.bind("<Enter>", lambda e: lbl.configure(fg_color=WebTheme.BTN_HOVER))
        lbl.bind("<Leave>", lambda e: lbl.configure(fg_color="transparent"))
        lbl.bind("<Button-1>", on_click)

    def select_font(self, font_name, window):
        self.font_family_var.set(font_name)
        window.destroy()
        self.trigger_preview_update()

    # ================= CORE LOGIC (OPTIMIZED) =================

    def get_font_object(self, size):
        font_name = self.font_family_var.get()
        cache_key = (font_name, size)
        if cache_key in self._font_obj_cache: return self._font_obj_cache[cache_key]
        if font_name in self.font_paths:
            try:
                font = ImageFont.truetype(self.font_paths[font_name], size)
                if len(self._font_obj_cache) > 50: self._font_obj_cache.clear()
                self._font_obj_cache[cache_key] = font
                return font
            except: pass
        return ImageFont.load_default()

    def get_cached_checkerboard(self, size, square_size=20):
        if size in self._checkerboard_cache: return self._checkerboard_cache[size].copy()
        img = Image.new("RGB", (size, size), "#2b2b2b")
        draw = ImageDraw.Draw(img)
        for i in range(0, size, square_size):
            for j in range(0, size, square_size):
                if (i // square_size + j // square_size) % 2 == 0:
                    draw.rectangle([i, j, i + square_size, j + square_size], fill="#383838")
        self._checkerboard_cache[size] = img
        return img.copy()

    def create_text_image_pil(self, text, size, font_size, font_obj=None, alignment="Center", position="Center", padding=0, line_spacing=4):
        if font_obj is None: font_obj = self.get_font_object(font_size)
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Calculate bounding box (Including spacing)
        align_lower = alignment.lower()
        left, top, right, bottom = draw.textbbox((0, 0), text, font=font_obj, align=align_lower, spacing=line_spacing)
        w = right - left
        h = bottom - top
        
        pos = position.lower()
        
        # Horizontal Position
        if "left" in pos: 
            x = padding - left 
        elif "right" in pos:
            x = size - w - left - padding
        else: # Center
            x = (size - w) // 2 - left

        # Vertical Position
        if "top" in pos:
            y = padding - top
        elif "bottom" in pos:
            y = size - h - top - padding
        else: # Middle/Center
            y = (size - h) // 2 - top
        
        if self.outline_enabled.get():
            o_width = self.outline_width_var.get()
            draw.text((x, y), text, font=font_obj, fill=self.text_color_rgb, stroke_width=o_width, stroke_fill=self.outline_color_rgb, align=align_lower, spacing=line_spacing)
        else:
            draw.text((x, y), text, font=font_obj, fill=self.text_color_rgb, align=align_lower, spacing=line_spacing)
        return img

    def create_mask_image(self, text, size, font_obj, alignment="Center", position="Center", padding=0, line_spacing=4):
        img = Image.new("L", (size, size), 0)
        draw = ImageDraw.Draw(img)
        
        align_lower = alignment.lower()
        left, top, right, bottom = draw.textbbox((0, 0), text, font=font_obj, align=align_lower, spacing=line_spacing)
        w = right - left
        h = bottom - top
        
        pos = position.lower()
        
        # Horizontal Position
        if "left" in pos: 
            x = padding - left 
        elif "right" in pos:
            x = size - w - left - padding
        else: # Center
            x = (size - w) // 2 - left

        # Vertical Position
        if "top" in pos:
            y = padding - top
        elif "bottom" in pos:
            y = size - h - top - padding
        else: # Middle/Center
            y = (size - h) // 2 - top
        
        stroke_w = 0
        if self.outline_enabled.get(): stroke_w = self.outline_width_var.get()
        draw.text((x, y), text, font=font_obj, fill=255, stroke_width=stroke_w, stroke_fill=255, align=align_lower, spacing=line_spacing)
        return img

    # --- VMAT & Paths ---
    def get_relative_texture_path(self, absolute_path):
        normalized = absolute_path.replace("\\", "/")
        if "/materials/" in normalized:
             split_part = normalized.split("/materials/", 1)[1]
             return f"materials/{split_part}"
        parent = os.path.basename(os.path.dirname(normalized))
        filename = os.path.basename(normalized)
        return f"materials/{parent}/{filename}"

    def generate_vmat_content(self, shader, color_path, trans_path):
        # Base Content
        content = f"""// THIS FILE IS AUTO-GENERATED

Layer0
{{
\tshader "{shader}"

\t//---- Blend Mode ----
\tF_BLEND_MODE 1 // Translucent

\t//---- Color ----
\tg_flModelTintAmount "1.000"
\tg_vColorTint "[1.000000 1.000000 1.000000 0.000000]"
\tTextureColor "{color_path}"

\t//---- Fog ----
\tg_bFogEnabled "1"

\t//---- Translucent ----
\tg_flOpacityScale "1.000"
\tTextureTranslucency "{trans_path}"
}}
"""
        return content

    # ================= ASYNC PREVIEW =================

    def trigger_preview_update(self):
        if self.debounce_timer: self.root.after_cancel(self.debounce_timer)
        self.debounce_timer = self.root.after(150, self.update_preview_thread_launcher)

    def update_preview_thread_launcher(self):
        self.preview_req_id += 1
        req_id = self.preview_req_id
        try:
            size = self.current_size.get()
            text = self.text_input.get("1.0", "end-1c") or " "
            font_size = self.font_size_var.get()
            font_obj = self.get_font_object(font_size)
            alignment = self.text_align_var.get()
            position = self.text_position_var.get()
            padding = self.padding_var.get()
            line_spacing = self.line_spacing_var.get()
            
            panel_w = self.right_panel.winfo_width()
            panel_h = self.right_panel.winfo_height() - 60
            
            if panel_w < 200: panel_w = 500
            if panel_h < 200: panel_h = 500
            
        except: return

        self.executor.submit(self._threaded_render, size, text, font_size, font_obj, alignment, position, padding, line_spacing, panel_w, panel_h, req_id)

    def _threaded_render(self, size, text, font_size, font_obj, alignment, position, padding, line_spacing, panel_w, panel_h, req_id):
        try:
            text_layer = self.create_text_image_pil(text, size, font_size, font_obj, alignment, position, padding, line_spacing)
            bg = self.get_cached_checkerboard(size)
            bg.paste(text_layer, (0, 0), text_layer)
            
            scale = min(panel_w, panel_h) / size
            if scale > 1: scale = 1
            display_size = int(size * scale)
            display_size = max(display_size, 100) 
            
            if display_size != size:
                bg = bg.resize((display_size, display_size), Image.Resampling.LANCZOS)

            self.root.after(0, lambda: self._apply_preview(bg, display_size, req_id))
        except Exception as e:
            Log.error("RENDER", f"Error rendering preview: {e}")

    def _apply_preview(self, pil_image, display_size, req_id):
        if req_id != self.preview_req_id: return
        try:
            self.preview_image_ref = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(display_size, display_size))
            self.preview_label.configure(image=self.preview_image_ref, text="")
        except: pass

    # ================= SAVE LOGIC =================

    def generate_image(self):
        filename = self.filename_var.get().strip() or "text_layer"
        save_path = filedialog.asksaveasfilename(initialfile=f"{filename}_color.png", filetypes=[("PNG files", "*.png")])
        if not save_path: return
        
        # Start Progress
        self.progress_bar.configure(mode="indeterminate")
        self.progress_bar.start()
        self.status_lbl.configure(text="Saving...", text_color="orange")
        
        self.executor.submit(self._threaded_save, save_path)

    def _threaded_save(self, save_path):
        try: self.root.after(0, lambda: self._gather_and_save(save_path))
        except: pass
            
    def _gather_and_save(self, save_path):
        data = {
            'size': self.current_size.get(),
            'text': self.text_input.get("1.0", "end-1c"), 
            'font_size': self.font_size_var.get(),
            'font_obj': self.get_font_object(self.font_size_var.get()),
            'alignment': self.text_align_var.get(),
            'position': self.text_position_var.get(),
            'padding': self.padding_var.get(),
            'line_spacing': self.line_spacing_var.get(),
            'mask': self.mask_layer_enabled.get(),
            'vmat': self.vmat_enabled.get(),
            'shader': self.shader_var.get(),
        }
        self.executor.submit(self._perform_save, save_path, data)

    def _perform_save(self, save_path, data):
        try:
            base_path = save_path.replace("_color.png", "").replace(".png", "")
            img = self.create_text_image_pil(data['text'], data['size'], data['font_size'], data['font_obj'], data['alignment'], data['position'], data['padding'], data['line_spacing'])
            
            color_filename = f"{base_path}_color.png"
            img.save(color_filename)
            
            trans_filename = f"{base_path}_trans.png"
            mask = self.create_mask_image(data['text'], data['size'], data['font_obj'], data['alignment'], data['position'], data['padding'], data['line_spacing'])
            if data['mask'] or data['vmat']:
                mask.save(trans_filename)
            
            if data['vmat']:
                color_abs = os.path.abspath(color_filename)
                trans_abs = os.path.abspath(trans_filename)
                
                vmat_content = self.generate_vmat_content(
                    data['shader'], 
                    self.get_relative_texture_path(color_abs), 
                    self.get_relative_texture_path(trans_abs)
                )
                
                with open(f"{base_path}.vmat", "w") as f:
                    f.write(vmat_content)
            
            output_dir = os.path.dirname(base_path)
            self.root.after(0, lambda: self._show_success(f"Saved files to {output_dir}", output_dir))
            Log.success("EXPORT", f"Saved files to {base_path}")
        except Exception as e:
            Log.error("EXPORT", f"Failed to save: {e}")
            self.root.after(0, lambda: self._stop_loading_error(str(e)))

    def _stop_loading_error(self, error_msg):
        self.progress_bar.stop()
        self.progress_bar.configure(mode="determinate")
        self.progress_bar.set(0)
        self.status_lbl.configure(text="Error", text_color="red")
        messagebox.showerror("Error", error_msg)

    def _show_success(self, msg, path_to_open=None):
        # Stop Progress
        self.progress_bar.stop()
        self.progress_bar.configure(mode="determinate")
        self.progress_bar.set(1) # Full
        self.status_lbl.configure(text="Export Successful", text_color=WebTheme.SECONDARY)
        
        if path_to_open:
            if messagebox.askyesno("Success", f"{msg}\n\nOpen output folder?"):
                try:
                    if platform.system() == "Windows": os.startfile(path_to_open)
                    elif platform.system() == "Darwin": subprocess.Popen(["open", path_to_open])
                    else: subprocess.Popen(["xdg-open", path_to_open])
                except Exception as e:
                    Log.error("SYS", f"Could not open explorer: {e}")
        else:
            messagebox.showinfo("Success", msg)

    def generate_numbers(self):
        directory = filedialog.askdirectory()
        if not directory: return
        
        # Start Progress
        self.progress_bar.configure(mode="indeterminate")
        self.progress_bar.start()
        self.status_lbl.configure(text="Batching...", text_color="orange")
        
        self.executor.submit(self._threaded_batch_numbers, directory)

    def _threaded_batch_numbers(self, directory):
        self.root.after(0, lambda: self._batch_numbers_logic(directory))

    def _batch_numbers_logic(self, directory):
        data = {
            'size': self.current_size.get(),
            'font_size': self.current_size.get(),
            'font_obj': self.get_font_object(self.current_size.get()),
            'alignment': self.text_align_var.get(),
            'position': self.text_position_var.get(),
            'padding': self.padding_var.get(),
            'line_spacing': self.line_spacing_var.get(),
            'mask': self.mask_layer_enabled.get(),
            'vmat': self.vmat_enabled.get(),
            'shader': self.shader_var.get(),
        }
        self.executor.submit(self._perform_batch, directory, data)

    def _perform_batch(self, directory, data):
        try:
            Log.section("BATCH EXPORT")
            for i in range(10):
                text = str(i)
                base = os.path.join(directory, f"{i}")
                
                img = self.create_text_image_pil(text, data['size'], data['font_size'], data['font_obj'], data['alignment'], data['position'], data['padding'], data['line_spacing'])
                img.save(f"{base}_color.png")
                
                mask = self.create_mask_image(text, data['size'], data['font_obj'], data['alignment'], data['position'], data['padding'], data['line_spacing'])
                if data['mask'] or data['vmat']:
                    mask.save(f"{base}_trans.png")
                
                if data['vmat']:
                    c_path = self.get_relative_texture_path(os.path.abspath(f"{base}_color.png"))
                    t_path = self.get_relative_texture_path(os.path.abspath(f"{base}_trans.png"))
                    
                    content = self.generate_vmat_content(data['shader'], c_path, t_path)
                    with open(f"{base}.vmat", "w") as f: f.write(content)
                Log.info("BATCH", f"Generated number: {i}")
            
            self.root.after(0, lambda: self._show_success(f"Batch complete in {directory}", directory))
            Log.success("BATCH", f"Batch generation complete in {directory}")
        except Exception as e:
            Log.error("BATCH", f"Batch failed: {e}")
            self.root.after(0, lambda: self._stop_loading_error(str(e)))

if __name__ == "__main__":
    app = TextImageGenerator()
    app.root.mainloop()