"""
ConVar Tweaks Panel
Sliders and toggles for individual convar adjustments
"""

import json
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


class ConVarToggle(ctk.CTkFrame):
    """Toggle switch for boolean convars"""
    
    def __init__(
        self,
        parent,
        name: str,
        display: str,
        description: str,
        default: str = "1",
        inverse: bool = False,
        on_change: Optional[Callable] = None,
        **kwargs
    ):
        super().__init__(parent, fg_color="transparent", **kwargs)
        
        self.name = name
        self.inverse = inverse
        self.on_change = on_change
        
        # Label
        self.label = ctk.CTkLabel(
            self,
            text=display,
            font=ctk.CTkFont(size=12),
            width=180,
            anchor="w"
        )
        self.label.pack(side="left", padx=(0, 10))
        
        # Switch
        self.switch_var = ctk.BooleanVar(value=self._parse_default(default))
        self.switch = ctk.CTkSwitch(
            self,
            text="",
            variable=self.switch_var,
            onvalue=True,
            offvalue=False,
            command=self._on_toggle,
            width=40
        )
        self.switch.pack(side="left")
        
        # Status label
        self.status_label = ctk.CTkLabel(
            self,
            text="ON" if self.switch_var.get() else "OFF",
            font=ctk.CTkFont(size=11),
            width=40,
            text_color="#4ade80" if self.switch_var.get() else "#f87171"
        )
        self.status_label.pack(side="left", padx=5)
        
        # Tooltip-style description
        self.desc_label = ctk.CTkLabel(
            self,
            text=description,
            font=ctk.CTkFont(size=10),
            text_color="gray"
        )
        self.desc_label.pack(side="right", padx=10)
    
    def _parse_default(self, default: str) -> bool:
        val = default.lower() in ("1", "true", "on")
        return not val if self.inverse else val
    
    def _on_toggle(self):
        is_on = self.switch_var.get()
        self.status_label.configure(
            text="ON" if is_on else "OFF",
            text_color="#4ade80" if is_on else "#f87171"
        )
        
        if self.on_change:
            # Convert to convar value
            if self.inverse:
                value = "0" if is_on else "1"
            else:
                value = "1" if is_on else "0"
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
        self.status_label.configure(
            text="ON" if is_on else "OFF",
            text_color="#4ade80" if is_on else "#f87171"
        )


class ConVarSlider(ctk.CTkFrame):
    """Slider for numeric convars"""
    
    def __init__(
        self,
        parent,
        name: str,
        display: str,
        description: str,
        min_val: float,
        max_val: float,
        default: str = "0",
        step: float = 1,
        labels: Optional[list[str]] = None,
        on_change: Optional[Callable] = None,
        **kwargs
    ):
        super().__init__(parent, fg_color="transparent", **kwargs)
        
        self.name = name
        self.min_val = min_val
        self.max_val = max_val
        self.step = step
        self.labels = labels
        self.on_change = on_change
        
        # Label
        self.label = ctk.CTkLabel(
            self,
            text=display,
            font=ctk.CTkFont(size=12),
            width=150,
            anchor="w"
        )
        self.label.pack(side="left", padx=(0, 10))
        
        # Slider
        default_val = float(default) if default else min_val
        self.slider = ctk.CTkSlider(
            self,
            from_=min_val,
            to=max_val,
            number_of_steps=int((max_val - min_val) / step) if step else None,
            width=200,
            command=self._on_slide
        )
        self.slider.set(default_val)
        self.slider.pack(side="left", padx=5)
        
        # Value display
        self.value_label = ctk.CTkLabel(
            self,
            text=self._format_value(default_val),
            font=ctk.CTkFont(size=11, weight="bold"),
            width=80
        )
        self.value_label.pack(side="left", padx=5)
    
    def _format_value(self, val: float) -> str:
        if self.labels:
            idx = int(val - self.min_val)
            if 0 <= idx < len(self.labels):
                return self.labels[idx]
        
        if self.step >= 1:
            return str(int(val))
        return f"{val:.1f}"
    
    def _on_slide(self, val):
        self.value_label.configure(text=self._format_value(val))
        
        if self.on_change:
            self.on_change(self.name, str(int(val) if self.step >= 1 else val))
    
    def get_value(self) -> str:
        val = self.slider.get()
        return str(int(val) if self.step >= 1 else val)
    
    def set_value(self, value: str):
        try:
            val = float(value)
            self.slider.set(val)
            self.value_label.configure(text=self._format_value(val))
        except ValueError:
            pass


class ConVarCategory(ctk.CTkFrame):
    """Category section with multiple convars"""
    
    def __init__(self, parent, name: str, icon: str, convars: list, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.configure(corner_radius=8, fg_color="#1f2937")
        
        # Header
        header = ctk.CTkLabel(
            self,
            text=f"{icon} {name}",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        header.pack(anchor="w", padx=10, pady=(8, 5))
        
        # Convars
        self.controls = {}
        
        for cv in convars:
            cv_type = cv.get("type", "toggle")
            
            if cv_type == "toggle" or cv_type == "toggle_inverse":
                control = ConVarToggle(
                    self,
                    name=cv["name"],
                    display=cv["display"],
                    description=cv.get("description", ""),
                    default=cv.get("default", "1"),
                    inverse=(cv_type == "toggle_inverse")
                )
            elif cv_type == "slider":
                control = ConVarSlider(
                    self,
                    name=cv["name"],
                    display=cv["display"],
                    description=cv.get("description", ""),
                    min_val=cv.get("min", 0),
                    max_val=cv.get("max", 100),
                    default=cv.get("default", "0"),
                    step=cv.get("step", 1),
                    labels=cv.get("labels")
                )
            else:
                continue
            
            control.pack(fill="x", padx=10, pady=3)
            self.controls[cv["name"]] = control
    
    def get_values(self) -> dict[str, str]:
        return {name: ctrl.get_value() for name, ctrl in self.controls.items()}


class ConVarPanel(ctk.CTkScrollableFrame):
    """Main convar tweaks panel with all categories"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.categories: list[ConVarCategory] = []
        self._build_panel()
    
    def _build_panel(self):
        data = load_convar_definitions()
        
        for cat_data in data.get("categories", []):
            category = ConVarCategory(
                self,
                name=cat_data["name"],
                icon=cat_data.get("icon", "⚙️"),
                convars=cat_data.get("convars", [])
            )
            category.pack(fill="x", pady=5, padx=5)
            self.categories.append(category)
    
    def get_all_values(self) -> dict[str, str]:
        """Get all convar values from all categories"""
        values = {}
        for category in self.categories:
            values.update(category.get_values())
        return values
