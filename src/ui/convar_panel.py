"""
ConVar Tweaks Panel
Sliders and toggles for individual convar adjustments
"""

import json
import re
import customtkinter as ctk
from pathlib import Path
from typing import Callable, Optional


def load_convar_definitions() -> dict:
    """Load convar definitions from JSON"""
    json_path = Path(__file__).parent.parent / "data" / "convars.json"
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Failed to load convars.json: {e}")
        return {"categories": []}


def read_current_convars(gameinfo_path: Path) -> dict[str, str]:
    """Read current convar values from gameinfo.gi"""
    convars = {}
    
    if not gameinfo_path or not gameinfo_path.exists():
        return convars
    
    try:
        with open(gameinfo_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        convars_match = re.search(r'ConVars\s*\{(.+?)^\s*\}', content, re.MULTILINE | re.DOTALL)
        
        if convars_match:
            convars_section = convars_match.group(1)
            # Match both: "name" "value" AND name "value" formats
            pattern = r'^\s*"?([a-z_][a-z0-9_]*)"?\s+"([^"]+)"'
            
            for match in re.finditer(pattern, convars_section, re.MULTILINE | re.IGNORECASE):
                name = match.group(1).strip()
                value = match.group(2).strip()
                if not name.startswith('//'):
                    convars[name] = value
    except Exception as e:
        print(f"Failed to read convars: {e}")
    
    return convars


def read_video_settings(video_path: Path) -> dict[str, str]:
    """Read current video settings from video.txt"""
    settings = {}
    
    if not video_path or not video_path.exists():
        return settings
    
    try:
        with open(video_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse lines like: "setting.r_shadows"		"0"
        pattern = r'"setting\.([^"]+)"\s+"([^"]*)"'
        
        for match in re.finditer(pattern, content):
            name = match.group(1)
            value = match.group(2)
            settings[name] = value
    
    except Exception as e:
        print(f"Failed to read video settings: {e}")
    
    return settings


def read_all_settings(gameinfo_path: Path, video_path: Path) -> dict[str, str]:
    """Read settings from both gameinfo.gi and video.txt"""
    settings = {}
    settings.update(read_current_convars(gameinfo_path))
    settings.update(read_video_settings(video_path))
    return settings


class ConVarToggle(ctk.CTkFrame):
    """Toggle switch for boolean convars"""
    
    def __init__(self, parent, name: str, display: str, description: str,
                 default: str = "1", inverse: bool = False,
                 on_change: Optional[Callable] = None, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        
        self.name = name
        self.display = display
        self.description = description
        self.inverse = inverse
        self.on_change = on_change
        
        self.label = ctk.CTkLabel(self, text=display, font=ctk.CTkFont(size=12),
                                  width=180, anchor="w")
        self.label.pack(side="left", padx=(0, 10))
        
        self.switch_var = ctk.BooleanVar(value=self._parse_default(default))
        self.switch = ctk.CTkSwitch(self, text="", variable=self.switch_var,
                                    onvalue=True, offvalue=False,
                                    command=self._on_toggle, width=40)
        self.switch.pack(side="left")
        
        self.status_label = ctk.CTkLabel(
            self, text="ON" if self.switch_var.get() else "OFF",
            font=ctk.CTkFont(size=11), width=40,
            text_color="#4ade80" if self.switch_var.get() else "#f87171"
        )
        self.status_label.pack(side="left", padx=5)
        
        self.desc_label = ctk.CTkLabel(self, text=description,
                                       font=ctk.CTkFont(size=10), text_color="gray")
        self.desc_label.pack(side="right", padx=10)
    
    def _parse_default(self, default: str) -> bool:
        val = default.lower() in ("1", "true", "on")
        return not val if self.inverse else val
    
    def _on_toggle(self):
        is_on = self.switch_var.get()
        self.status_label.configure(text="ON" if is_on else "OFF",
                                   text_color="#4ade80" if is_on else "#f87171")
        if self.on_change:
            value = "0" if (is_on if self.inverse else not is_on) else "1"
            self.on_change(self.name, value)
    
    def get_value(self) -> str:
        is_on = self.switch_var.get()
        if self.inverse:
            return "0" if is_on else "1"
        return "1" if is_on else "0"
    
    def set_value(self, value: str):
        is_on = value.lower() in ("1", "true", "on")
        if self.inverse:
            is_on = not is_on
        self.switch_var.set(is_on)
        self.status_label.configure(text="ON" if is_on else "OFF",
                                   text_color="#4ade80" if is_on else "#f87171")
    
    def matches_search(self, query: str) -> bool:
        """Check if this control matches search query"""
        q = query.lower()
        return (q in self.name.lower() or q in self.display.lower() or 
                q in self.description.lower())


class ConVarSlider(ctk.CTkFrame):
    """Slider for numeric convars"""
    
    def __init__(self, parent, name: str, display: str, description: str,
                 min_val: float, max_val: float, default: str = "0",
                 step: float = 1, labels: Optional[list[str]] = None,
                 values: Optional[list[str]] = None,
                 on_change: Optional[Callable] = None, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        
        self.name = name
        self.display = display
        self.description = description
        self.min_val = min_val
        self.max_val = max_val
        self.step = step
        self.labels = labels
        self.values = values  # Maps slider position to actual value
        self.on_change = on_change
        
        self.label = ctk.CTkLabel(self, text=display, font=ctk.CTkFont(size=12),
                                  width=150, anchor="w")
        self.label.pack(side="left", padx=(0, 10))
        
        default_val = float(default) if default else min_val
        self.slider = ctk.CTkSlider(
            self, from_=min_val, to=max_val,
            number_of_steps=int((max_val - min_val) / step) if step else None,
            width=200, command=self._on_slide
        )
        self.slider.set(default_val)
        self.slider.pack(side="left", padx=5)
        
        self.value_label = ctk.CTkLabel(self, text=self._format_value(default_val),
                                        font=ctk.CTkFont(size=11, weight="bold"), width=80)
        self.value_label.pack(side="left", padx=5)
    
    def _format_value(self, val: float) -> str:
        if self.labels:
            idx = int(val - self.min_val)
            if 0 <= idx < len(self.labels):
                return self.labels[idx]
        return str(int(val)) if self.step >= 1 else f"{val:.1f}"
    
    def _on_slide(self, val):
        self.value_label.configure(text=self._format_value(val))
        if self.on_change:
            self.on_change(self.name, str(int(val) if self.step >= 1 else val))
    
    def get_value(self) -> str:
        val = self.slider.get()
        idx = int(val - self.min_val)
        # If values array exists, return mapped value
        if self.values and 0 <= idx < len(self.values):
            return self.values[idx]
        return str(int(val) if self.step >= 1 else val)
    
    def set_value(self, value: str):
        try:
            # If values array exists, find position by value
            if self.values:
                if value in self.values:
                    idx = self.values.index(value)
                    val = self.min_val + idx
                else:
                    # Try to find closest match for float values
                    try:
                        target = float(value)
                        closest_idx = min(range(len(self.values)), 
                                         key=lambda i: abs(float(self.values[i]) - target))
                        val = self.min_val + closest_idx
                    except:
                        val = float(value)
            else:
                val = float(value)
            self.slider.set(val)
            self.value_label.configure(text=self._format_value(val))
        except ValueError:
            pass
    
    def matches_search(self, query: str) -> bool:
        q = query.lower()
        return (q in self.name.lower() or q in self.display.lower() or 
                q in self.description.lower())


class ConVarCategory(ctk.CTkFrame):
    """Category section with multiple convars"""
    
    def __init__(self, parent, name: str, icon: str, convars: list, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.category_name = name
        self.icon = icon
        self.configure(corner_radius=8, fg_color="#1f2937")
        
        self.header = ctk.CTkLabel(self, text=f"{icon} {name}",
                                   font=ctk.CTkFont(size=13, weight="bold"))
        self.header.pack(anchor="w", padx=10, pady=(8, 5))
        
        self.controls = {}
        self.control_frames = []
        
        for cv in convars:
            cv_type = cv.get("type", "toggle")
            
            if cv_type in ("toggle", "toggle_inverse"):
                control = ConVarToggle(
                    self, name=cv["name"], display=cv["display"],
                    description=cv.get("description", ""),
                    default=cv.get("default", "1"),
                    inverse=(cv_type == "toggle_inverse")
                )
            elif cv_type == "slider":
                control = ConVarSlider(
                    self, name=cv["name"], display=cv["display"],
                    description=cv.get("description", ""),
                    min_val=cv.get("min", 0), max_val=cv.get("max", 100),
                    default=cv.get("default", "0"), step=cv.get("step", 1),
                    labels=cv.get("labels"),
                    values=cv.get("values")
                )
            else:
                continue
            
            control.pack(fill="x", padx=10, pady=3)
            self.controls[cv["name"]] = control
            self.control_frames.append(control)
    
    def get_values(self) -> dict[str, str]:
        return {name: ctrl.get_value() for name, ctrl in self.controls.items()}
    
    def filter_controls(self, query: str) -> int:
        """Filter controls by search query. Returns number of visible controls."""
        visible = 0
        for control in self.control_frames:
            if not query or control.matches_search(query):
                control.pack(fill="x", padx=10, pady=3)
                visible += 1
            else:
                control.pack_forget()
        return visible


class ConVarPanel(ctk.CTkFrame):
    """Main convar tweaks panel with search and all categories"""
    
    def __init__(self, parent, gameinfo_path: Optional[Path] = None, video_path: Optional[Path] = None, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.gameinfo_path = gameinfo_path
        self.video_path = video_path
        self.categories: list[ConVarCategory] = []
        self.all_controls: dict[str, any] = {}
        self.control_sources: dict[str, str] = {}  # name -> "video" or "convar"
        self._build_panel()
    
    def _build_panel(self):
        # Search bar
        search_frame = ctk.CTkFrame(self, fg_color="transparent")
        search_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        ctk.CTkLabel(search_frame, text="🔍", font=ctk.CTkFont(size=16)).pack(side="left", padx=(0, 5))
        
        self.search_entry = ctk.CTkEntry(
            search_frame, placeholder_text="Search settings...",
            width=300, height=35
        )
        self.search_entry.pack(side="left", fill="x", expand=True)
        self.search_entry.bind("<KeyRelease>", self._on_search)
        
        self.search_count = ctk.CTkLabel(search_frame, text="",
                                         font=ctk.CTkFont(size=11), text_color="gray")
        self.search_count.pack(side="right", padx=10)
        
        # Scrollable content
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        data = load_convar_definitions()
        
        for cat_data in data.get("categories", []):
            category = ConVarCategory(
                self.scroll_frame,
                name=cat_data["name"],
                icon=cat_data.get("icon", "⚙️"),
                convars=cat_data.get("convars", [])
            )
            category.pack(fill="x", pady=5, padx=5)
            self.categories.append(category)
            self.all_controls.update(category.controls)
            
            # Track which source each convar uses
            for convar in cat_data.get("convars", []):
                self.control_sources[convar["name"]] = convar.get("source", "convar")
    
    def _on_search(self, event=None):
        """Filter controls based on search query"""
        query = self.search_entry.get().strip()
        
        total_visible = 0
        for category in self.categories:
            visible = category.filter_controls(query)
            total_visible += visible
            
            # Hide category if no controls match
            if visible == 0 and query:
                category.pack_forget()
            else:
                category.pack(fill="x", pady=5, padx=5)
        
        if query:
            self.search_count.configure(text=f"{total_visible} results")
        else:
            self.search_count.configure(text="")
    
    def load_current_values(self, gameinfo_path: Path, video_path: Path = None):
        """Load current values from gameinfo.gi and video.txt"""
        self.gameinfo_path = gameinfo_path
        self.video_path = video_path
        
        # Read from both sources
        current_values = read_all_settings(gameinfo_path, video_path)
        
        for name, value in current_values.items():
            if name in self.all_controls:
                try:
                    # Handle video.txt boolean values (true/false vs 1/0)
                    if value.lower() == "true":
                        value = "1"
                    elif value.lower() == "false":
                        value = "0"
                    self.all_controls[name].set_value(value)
                except Exception as e:
                    print(f"Failed to set {name} = {value}: {e}")
    
    def get_all_values(self) -> dict[str, str]:
        """Get all convar values from all categories"""
        values = {}
        for category in self.categories:
            values.update(category.get_values())
        return values
    
    def get_values_by_source(self) -> tuple[dict[str, str], dict[str, str]]:
        """Get values separated by source: (convar_values, video_values)"""
        all_values = self.get_all_values()
        convar_values = {}
        video_values = {}
        
        for name, value in all_values.items():
            source = self.control_sources.get(name, "convar")
            if source == "video":
                video_values[name] = value
            else:
                convar_values[name] = value
        
        return convar_values, video_values


class CrosshairPreview(ctk.CTkFrame):
    """Visual preview of crosshair settings"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.configure(fg_color="#1a1a2e", corner_radius=10)
        
        # Canvas for drawing crosshair
        self.canvas = ctk.CTkCanvas(self, width=200, height=200,
                                    bg="#1a1a2e", highlightthickness=0)
        self.canvas.pack(padx=20, pady=20)
        
        # Default values
        self.gap = 3
        self.pip_height = 16
        self.pip_width = 4
        self.pip_opacity = 0.4
        self.dot_opacity = 0.7
        
        self.draw_crosshair()
    
    def update_settings(self, gap=None, pip_height=None, pip_width=None,
                       pip_opacity=None, dot_opacity=None):
        """Update crosshair settings and redraw"""
        if gap is not None:
            self.gap = gap
        if pip_height is not None:
            self.pip_height = pip_height
        if pip_width is not None:
            self.pip_width = pip_width
        if pip_opacity is not None:
            self.pip_opacity = pip_opacity
        if dot_opacity is not None:
            self.dot_opacity = dot_opacity
        
        self.draw_crosshair()
    
    def draw_crosshair(self):
        """Draw the crosshair on canvas"""
        self.canvas.delete("all")
        
        cx, cy = 100, 100  # Center
        
        # Convert opacity to hex color (white with opacity)
        pip_color = self._opacity_to_color(self.pip_opacity)
        dot_color = self._opacity_to_color(self.dot_opacity)
        
        # Scale for preview
        gap = self.gap * 2
        height = self.pip_height * 1.5
        width = self.pip_width * 1.5
        
        # Top pip
        self.canvas.create_rectangle(
            cx - width/2, cy - gap - height,
            cx + width/2, cy - gap,
            fill=pip_color, outline=""
        )
        
        # Bottom pip
        self.canvas.create_rectangle(
            cx - width/2, cy + gap,
            cx + width/2, cy + gap + height,
            fill=pip_color, outline=""
        )
        
        # Left pip
        self.canvas.create_rectangle(
            cx - gap - height, cy - width/2,
            cx - gap, cy + width/2,
            fill=pip_color, outline=""
        )
        
        # Right pip
        self.canvas.create_rectangle(
            cx + gap, cy - width/2,
            cx + gap + height, cy + width/2,
            fill=pip_color, outline=""
        )
        
        # Center dot
        dot_size = 3
        self.canvas.create_oval(
            cx - dot_size, cy - dot_size,
            cx + dot_size, cy + dot_size,
            fill=dot_color, outline=""
        )
    
    def _opacity_to_color(self, opacity: float) -> str:
        """Convert opacity (0-1) to grayscale hex color"""
        val = int(255 * min(1, max(0, opacity)))
        return f"#{val:02x}{val:02x}{val:02x}"
