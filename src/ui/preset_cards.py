"""
Preset Selection Cards
Visual cards for selecting config presets
"""

import customtkinter as ctk
from pathlib import Path
from typing import Callable, Optional

from src.core.config import list_presets, get_presets_dir


class PresetCard(ctk.CTkFrame):
    """Individual preset card"""
    
    def __init__(
        self,
        parent,
        preset_name: str,
        display_name: str,
        description: str,
        on_click: Callable,
        **kwargs
    ):
        super().__init__(parent, **kwargs)
        
        self.preset_name = preset_name
        self.on_click = on_click
        self.selected = False
        
        # Configure frame
        self.configure(
            corner_radius=10,
            border_width=2,
            border_color="gray",
            fg_color="#1f2937"
        )
        
        # Make clickable
        self.bind("<Button-1>", self._on_click)
        self.bind("<Enter>", self._on_hover)
        self.bind("<Leave>", self._on_leave)
        
        # Content
        self.name_label = ctk.CTkLabel(
            self,
            text=display_name,
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.name_label.pack(pady=(15, 5))
        self.name_label.bind("<Button-1>", self._on_click)
        
        self.desc_label = ctk.CTkLabel(
            self,
            text=description,
            font=ctk.CTkFont(size=11),
            text_color="gray",
            wraplength=130
        )
        self.desc_label.pack(pady=(0, 15), padx=10)
        self.desc_label.bind("<Button-1>", self._on_click)
    
    def _on_click(self, event=None):
        self.on_click(self.preset_name)
    
    def _on_hover(self, event=None):
        if not self.selected:
            self.configure(border_color="#6366f1")
    
    def _on_leave(self, event=None):
        if not self.selected:
            self.configure(border_color="gray")
    
    def set_selected(self, selected: bool):
        self.selected = selected
        if selected:
            self.configure(
                border_color="#22c55e",
                border_width=3
            )
            self.name_label.configure(text_color="#22c55e")
        else:
            self.configure(
                border_color="gray",
                border_width=2
            )
            self.name_label.configure(text_color="white")


class PresetCardsFrame(ctk.CTkFrame):
    """Container for preset cards"""
    
    def __init__(self, parent, on_select: Callable[[str], None], **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        
        self.on_select = on_select
        self.cards: dict[str, PresetCard] = {}
        self.selected_preset: Optional[str] = None
        
        self._build_cards()
    
    def _build_cards(self):
        # Default presets if no preset files exist yet
        default_presets = [
            {
                "name": "potato",
                "display": "🥔 Potato",
                "description": "Max FPS, minimum visuals"
            },
            {
                "name": "balanced",
                "display": "⚖️ Balanced",
                "description": "Recommended for most PCs"
            },
            {
                "name": "quality",
                "display": "💎 Quality",
                "description": "Better visuals, still optimized"
            },
            {
                "name": "competitive",
                "display": "🎯 Competitive",
                "description": "Max visibility for ranked"
            }
        ]
        
        # Try to load actual presets
        try:
            actual_presets = list_presets()
            if actual_presets:
                presets = actual_presets
            else:
                presets = default_presets
        except:
            presets = default_presets
        
        # Create cards grid
        cards_container = ctk.CTkFrame(self, fg_color="transparent")
        cards_container.pack(fill="x", expand=True)
        
        for i, preset in enumerate(presets):
            card = PresetCard(
                cards_container,
                preset_name=preset.get("name", preset.get("display", "")),
                display_name=preset.get("display", preset.get("name", "Unknown")),
                description=preset.get("description", ""),
                on_click=self._on_card_click,
                width=150,
                height=100
            )
            card.grid(row=0, column=i, padx=8, pady=5, sticky="nsew")
            
            self.cards[preset.get("name", preset.get("display", ""))] = card
        
        # Configure grid weights
        for i in range(len(presets)):
            cards_container.grid_columnconfigure(i, weight=1)
    
    def _on_card_click(self, preset_name: str):
        # Deselect previous
        if self.selected_preset and self.selected_preset in self.cards:
            self.cards[self.selected_preset].set_selected(False)
        
        # Select new
        self.selected_preset = preset_name
        if preset_name in self.cards:
            self.cards[preset_name].set_selected(True)
        
        # Callback
        self.on_select(preset_name)
    
    def get_selected(self) -> Optional[str]:
        return self.selected_preset


class NoPresetsFrame(ctk.CTkFrame):
    """Shown when no presets are available"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        label = ctk.CTkLabel(
            self,
            text="⚠️ No preset configs found",
            font=ctk.CTkFont(size=14)
        )
        label.pack(pady=10)
        
        sublabel = ctk.CTkLabel(
            self,
            text=f"Add .gi files to: {get_presets_dir()}",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        sublabel.pack(pady=(0, 10))
