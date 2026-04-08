"""
Main Application Window
OptiLock Config Manager UI - Premium Edition
"""

import customtkinter as ctk
from pathlib import Path
from typing import Optional
import threading
import webbrowser

from src.core.detector import find_deadlock, get_current_config_info, validate_deadlock_path
from src.core.backup import create_backup, list_backups, restore_backup, ensure_vanilla_backup
from src.core.config import list_presets, apply_preset, get_presets_dir
from src.core.updater import check_for_updates, get_version_string
from src.ui.preset_cards import PresetCardsFrame
from src.ui.convar_panel import ConVarPanel
from src import __version__


# ============================================================================
# THEME CONFIGURATION
# ============================================================================

# Color Palette - Gaming aesthetic with purple/cyan accents
COLORS = {
    "bg_dark": "#0a0a0f",
    "bg_card": "#12121a",
    "bg_card_hover": "#1a1a25",
    "bg_elevated": "#1e1e2e",
    "border": "#2a2a3a",
    "border_glow": "#6366f1",
    "accent_primary": "#8b5cf6",      # Purple
    "accent_secondary": "#06b6d4",    # Cyan
    "accent_success": "#10b981",      # Green
    "accent_warning": "#f59e0b",      # Amber
    "accent_danger": "#ef4444",       # Red
    "text_primary": "#ffffff",
    "text_secondary": "#a1a1aa",
    "text_muted": "#71717a",
    "gradient_start": "#8b5cf6",
    "gradient_end": "#06b6d4",
}

ctk.set_appearance_mode("dark")


# ============================================================================
# CUSTOM COMPONENTS
# ============================================================================

class GlowFrame(ctk.CTkFrame):
    """Frame with subtle glow effect on hover"""
    
    def __init__(self, parent, glow_color=None, **kwargs):
        self.glow_color = glow_color or COLORS["border_glow"]
        self.base_border = kwargs.pop("border_color", COLORS["border"])
        
        super().__init__(
            parent,
            corner_radius=12,
            border_width=1,
            border_color=self.base_border,
            fg_color=COLORS["bg_card"],
            **kwargs
        )
        
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
    
    def _on_enter(self, e=None):
        self.configure(border_color=self.glow_color)
    
    def _on_leave(self, e=None):
        self.configure(border_color=self.base_border)


class GradientButton(ctk.CTkButton):
    """Button with gradient-like styling"""
    
    def __init__(self, parent, style="primary", **kwargs):
        styles = {
            "primary": {
                "fg_color": COLORS["accent_primary"],
                "hover_color": "#7c3aed",
                "text_color": "white"
            },
            "success": {
                "fg_color": COLORS["accent_success"],
                "hover_color": "#059669",
                "text_color": "white"
            },
            "secondary": {
                "fg_color": COLORS["bg_elevated"],
                "hover_color": COLORS["bg_card_hover"],
                "text_color": COLORS["text_primary"],
                "border_width": 1,
                "border_color": COLORS["border"]
            },
            "danger": {
                "fg_color": COLORS["accent_danger"],
                "hover_color": "#dc2626",
                "text_color": "white"
            }
        }
        
        style_config = styles.get(style, styles["primary"])
        
        super().__init__(
            parent,
            corner_radius=8,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            **style_config,
            **kwargs
        )


class IconLabel(ctk.CTkFrame):
    """Label with icon and text"""
    
    def __init__(self, parent, icon: str, text: str, size=14, color=None, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        
        self.icon_label = ctk.CTkLabel(
            self,
            text=icon,
            font=ctk.CTkFont(size=size + 4)
        )
        self.icon_label.pack(side="left", padx=(0, 8))
        
        self.text_label = ctk.CTkLabel(
            self,
            text=text,
            font=ctk.CTkFont(family="Segoe UI", size=size),
            text_color=color or COLORS["text_primary"]
        )
        self.text_label.pack(side="left")
    
    def configure_text(self, **kwargs):
        self.text_label.configure(**kwargs)


# ============================================================================
# HERO HEADER
# ============================================================================

class HeroHeader(ctk.CTkFrame):
    """Premium header with branding"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        
        # Main title container
        title_container = ctk.CTkFrame(self, fg_color="transparent")
        title_container.pack(pady=(20, 10))
        
        # Logo/Icon
        logo = ctk.CTkLabel(
            title_container,
            text="⚡",
            font=ctk.CTkFont(size=48)
        )
        logo.pack(side="left", padx=(0, 15))
        
        # Title stack
        title_stack = ctk.CTkFrame(title_container, fg_color="transparent")
        title_stack.pack(side="left")
        
        title = ctk.CTkLabel(
            title_stack,
            text="OPTILOCK",
            font=ctk.CTkFont(family="Segoe UI", size=36, weight="bold"),
            text_color=COLORS["text_primary"]
        )
        title.pack(anchor="w")
        
        subtitle = ctk.CTkLabel(
            title_stack,
            text="CONFIG MANAGER",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color=COLORS["accent_primary"]
        )
        subtitle.pack(anchor="w")
        
        # Tagline
        tagline = ctk.CTkLabel(
            self,
            text="Unlock peak performance for Deadlock",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=COLORS["text_muted"]
        )
        tagline.pack(pady=(0, 15))
        
        # Divider line with gradient effect (simulated)
        divider = ctk.CTkFrame(
            self,
            height=2,
            fg_color=COLORS["accent_primary"]
        )
        divider.pack(fill="x", padx=50)


# ============================================================================
# STATUS SECTION
# ============================================================================

class StatusCard(GlowFrame):
    """Game detection status card"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.configure(height=100)
        
        # Content container
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=20, pady=15)
        
        # Left side - status info
        left = ctk.CTkFrame(content, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True)
        
        self.status_icon = ctk.CTkLabel(
            left,
            text="🔍",
            font=ctk.CTkFont(size=28)
        )
        self.status_icon.pack(side="left", padx=(0, 15))
        
        info_stack = ctk.CTkFrame(left, fg_color="transparent")
        info_stack.pack(side="left", fill="y")
        
        self.title_label = ctk.CTkLabel(
            info_stack,
            text="Searching for Deadlock...",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color=COLORS["text_primary"]
        )
        self.title_label.pack(anchor="w")
        
        self.path_label = ctk.CTkLabel(
            info_stack,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=COLORS["text_muted"],
            wraplength=400
        )
        self.path_label.pack(anchor="w", pady=(2, 0))
        
        self.config_label = ctk.CTkLabel(
            info_stack,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=COLORS["text_secondary"]
        )
        self.config_label.pack(anchor="w", pady=(4, 0))
        
        # Right side - browse button
        self.browse_btn = GradientButton(
            content,
            text="Browse",
            style="secondary",
            width=90,
            height=36,
            command=None
        )
        self.browse_btn.pack(side="right", padx=(15, 0))
        
        self.on_browse = None
    
    def set_status(self, found: bool, path: Optional[Path] = None, config_info: dict = None):
        if found and path:
            self.status_icon.configure(text="🎮")
            self.title_label.configure(
                text="Deadlock Detected",
                text_color=COLORS["accent_success"]
            )
            self.path_label.configure(text=str(path))
            
            if config_info and config_info.get("installed"):
                version = f" v{config_info['version']}" if config_info.get('version') else ""
                self.config_label.configure(
                    text=f"✨ {config_info['name']}{version} active",
                    text_color=COLORS["accent_primary"]
                )
            else:
                self.config_label.configure(
                    text="⚠️ Using vanilla config",
                    text_color=COLORS["accent_warning"]
                )
        else:
            self.status_icon.configure(text="❌")
            self.title_label.configure(
                text="Deadlock Not Found",
                text_color=COLORS["accent_danger"]
            )
            self.path_label.configure(text="Click Browse to locate your installation")
            self.config_label.configure(text="")


# ============================================================================
# PRESET CARDS (PREMIUM)
# ============================================================================

class PremiumPresetCard(ctk.CTkFrame):
    """Premium styled preset card"""
    
    PRESETS_META = {
        "potato": {"icon": "🥔", "color": "#f59e0b", "glow": "#f59e0b"},
        "balanced": {"icon": "⚖️", "color": "#8b5cf6", "glow": "#8b5cf6"},
        "quality": {"icon": "💎", "color": "#06b6d4", "glow": "#06b6d4"},
        "competitive": {"icon": "🎯", "color": "#ef4444", "glow": "#ef4444"},
    }
    
    def __init__(self, parent, preset_name: str, display_name: str, description: str, on_click, **kwargs):
        super().__init__(parent, fg_color=COLORS["bg_card"], corner_radius=12, **kwargs)
        
        self.preset_name = preset_name
        self.on_click = on_click
        self.selected = False
        
        # Get preset metadata
        meta = self.PRESETS_META.get(preset_name.lower(), {"icon": "📦", "color": COLORS["accent_primary"], "glow": COLORS["border_glow"]})
        self.accent_color = meta["color"]
        self.glow_color = meta["glow"]
        
        self.configure(
            border_width=2,
            border_color=COLORS["border"]
        )
        
        # Bind events
        self.bind("<Button-1>", self._on_click)
        self.bind("<Enter>", self._on_hover)
        self.bind("<Leave>", self._on_leave)
        
        # Icon
        self.icon_label = ctk.CTkLabel(
            self,
            text=meta["icon"],
            font=ctk.CTkFont(size=36)
        )
        self.icon_label.pack(pady=(20, 8))
        self.icon_label.bind("<Button-1>", self._on_click)
        
        # Name
        self.name_label = ctk.CTkLabel(
            self,
            text=display_name.replace(meta["icon"], "").strip(),
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=COLORS["text_primary"]
        )
        self.name_label.pack(pady=(0, 4))
        self.name_label.bind("<Button-1>", self._on_click)
        
        # Description
        self.desc_label = ctk.CTkLabel(
            self,
            text=description,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=COLORS["text_muted"],
            wraplength=120
        )
        self.desc_label.pack(pady=(0, 20), padx=10)
        self.desc_label.bind("<Button-1>", self._on_click)
    
    def _on_click(self, e=None):
        self.on_click(self.preset_name)
    
    def _on_hover(self, e=None):
        if not self.selected:
            self.configure(
                border_color=self.glow_color,
                fg_color=COLORS["bg_card_hover"]
            )
    
    def _on_leave(self, e=None):
        if not self.selected:
            self.configure(
                border_color=COLORS["border"],
                fg_color=COLORS["bg_card"]
            )
    
    def set_selected(self, selected: bool):
        self.selected = selected
        if selected:
            self.configure(
                border_color=self.accent_color,
                border_width=3,
                fg_color=COLORS["bg_card_hover"]
            )
            self.name_label.configure(text_color=self.accent_color)
        else:
            self.configure(
                border_color=COLORS["border"],
                border_width=2,
                fg_color=COLORS["bg_card"]
            )
            self.name_label.configure(text_color=COLORS["text_primary"])


class PremiumPresetsSection(ctk.CTkFrame):
    """Section containing preset cards"""
    
    def __init__(self, parent, on_select, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        
        self.on_select = on_select
        self.cards = {}
        self.selected_preset = None
        
        # Section header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0, 15))
        
        IconLabel(header, "📦", "CONFIG PRESETS", size=14, color=COLORS["text_secondary"]).pack(side="left")
        
        # Cards container
        cards_frame = ctk.CTkFrame(self, fg_color="transparent")
        cards_frame.pack(fill="x")
        
        # Default presets
        presets = [
            {"name": "potato", "display": "🥔 Potato", "description": "Max FPS, minimum visuals"},
            {"name": "balanced", "display": "⚖️ Balanced", "description": "Best of both worlds"},
            {"name": "quality", "display": "💎 Quality", "description": "Enhanced visuals"},
            {"name": "competitive", "display": "🎯 Competitive", "description": "Pro visibility settings"},
        ]
        
        # Try loading actual presets
        try:
            actual = list_presets()
            if actual:
                presets = actual
        except:
            pass
        
        for i, p in enumerate(presets):
            card = PremiumPresetCard(
                cards_frame,
                preset_name=p.get("name", ""),
                display_name=p.get("display", p.get("name", "")),
                description=p.get("description", ""),
                on_click=self._on_card_click,
                width=150,
                height=140
            )
            card.grid(row=0, column=i, padx=8, pady=5, sticky="nsew")
            self.cards[p.get("name", "")] = card
        
        for i in range(len(presets)):
            cards_frame.grid_columnconfigure(i, weight=1)
    
    def _on_card_click(self, name: str):
        if self.selected_preset and self.selected_preset in self.cards:
            self.cards[self.selected_preset].set_selected(False)
        
        self.selected_preset = name
        if name in self.cards:
            self.cards[name].set_selected(True)
        
        self.on_select(name)


# ============================================================================
# ACTION BAR
# ============================================================================

class ActionBar(ctk.CTkFrame):
    """Bottom action buttons bar"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        
        # Left actions
        left = ctk.CTkFrame(self, fg_color="transparent")
        left.pack(side="left")
        
        self.backup_btn = GradientButton(
            left,
            text="💾 Backup",
            style="secondary",
            width=110,
            height=42
        )
        self.backup_btn.pack(side="left", padx=(0, 10))
        
        self.restore_btn = GradientButton(
            left,
            text="↩️ Restore",
            style="secondary",
            width=110,
            height=42
        )
        self.restore_btn.pack(side="left", padx=(0, 10))
        
        # Center - main apply button
        self.apply_btn = GradientButton(
            self,
            text="⚡ APPLY CONFIG",
            style="success",
            width=180,
            height=48,
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold")
        )
        self.apply_btn.pack(side="left", expand=True)
        
        # Right actions
        right = ctk.CTkFrame(self, fg_color="transparent")
        right.pack(side="right")
        
        self.update_btn = GradientButton(
            right,
            text="🔄 Update",
            style="secondary",
            width=100,
            height=42
        )
        self.update_btn.pack(side="right")


# ============================================================================
# FOOTER
# ============================================================================

class Footer(ctk.CTkFrame):
    """Bottom footer with version and links"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color=COLORS["bg_card"], height=40, **kwargs)
        
        self.pack_propagate(False)
        
        # Version
        version = ctk.CTkLabel(
            self,
            text=f"v{__version__}",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=COLORS["text_muted"]
        )
        version.pack(side="left", padx=15)
        
        # Status
        self.status_label = ctk.CTkLabel(
            self,
            text="Ready",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=COLORS["text_secondary"]
        )
        self.status_label.pack(side="left", padx=15)
        
        # Links
        links = ctk.CTkFrame(self, fg_color="transparent")
        links.pack(side="right", padx=10)
        
        github_btn = ctk.CTkButton(
            links,
            text="GitHub",
            font=ctk.CTkFont(size=11),
            fg_color="transparent",
            hover_color=COLORS["bg_elevated"],
            text_color=COLORS["text_muted"],
            width=60,
            height=28,
            command=lambda: webbrowser.open("https://github.com/BradyM37/Config-Manager")
        )
        github_btn.pack(side="right")
    
    def set_status(self, text: str, color: str = None):
        self.status_label.configure(
            text=text,
            text_color=color or COLORS["text_secondary"]
        )


# ============================================================================
# MAIN APPLICATION
# ============================================================================

class App(ctk.CTk):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        
        # Window setup
        self.title("OptiLock Config Manager")
        self.geometry("750x820")
        self.minsize(700, 700)
        self.configure(fg_color=COLORS["bg_dark"])
        
        # State
        self.deadlock_path: Optional[Path] = None
        self.selected_preset: Optional[str] = None
        
        # Build UI
        self._build_ui()
        
        # Auto-detect
        self.after(100, self._detect_deadlock)
    
    def _build_ui(self):
        # Main container with padding
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Hero header
        self.header = HeroHeader(main)
        self.header.pack(fill="x")
        
        # Status card
        self.status_card = StatusCard(main)
        self.status_card.pack(fill="x", pady=20)
        self.status_card.browse_btn.configure(command=self._browse_path)
        
        # Presets section
        self.presets_section = PremiumPresetsSection(main, on_select=self._on_preset_select)
        self.presets_section.pack(fill="x", pady=(0, 20))
        
        # ConVar panel (scrollable)
        convars_header = ctk.CTkFrame(main, fg_color="transparent")
        convars_header.pack(fill="x", pady=(0, 10))
        IconLabel(convars_header, "🎛️", "ADVANCED TWEAKS", size=14, color=COLORS["text_secondary"]).pack(side="left")
        
        self.convar_panel = ConVarPanel(main, fg_color=COLORS["bg_card"], corner_radius=12)
        self.convar_panel.pack(fill="both", expand=True)
        
        # Action bar
        self.action_bar = ActionBar(main)
        self.action_bar.pack(fill="x", pady=20)
        
        # Connect actions
        self.action_bar.apply_btn.configure(command=self._apply_config)
        self.action_bar.backup_btn.configure(command=self._create_backup)
        self.action_bar.restore_btn.configure(command=self._show_restore_dialog)
        self.action_bar.update_btn.configure(command=self._check_updates)
        
        # Footer
        self.footer = Footer(self)
        self.footer.pack(fill="x", side="bottom")
    
    def _detect_deadlock(self):
        self.footer.set_status("Searching for Deadlock...", COLORS["text_muted"])
        
        def detect():
            path = find_deadlock()
            self.after(0, lambda: self._on_detection_complete(path))
        
        threading.Thread(target=detect, daemon=True).start()
    
    def _on_detection_complete(self, path: Optional[Path]):
        self.deadlock_path = path
        
        if path:
            info = get_current_config_info(path)
            self.status_card.set_status(True, path, info)
            self.footer.set_status("Ready", COLORS["accent_success"])
            ensure_vanilla_backup(path)
        else:
            self.status_card.set_status(False)
            self.footer.set_status("Please locate Deadlock", COLORS["accent_warning"])
        
        self._update_controls_state()
    
    def _browse_path(self):
        path = ctk.filedialog.askdirectory(title="Select Deadlock Installation")
        if path:
            path = Path(path)
            if validate_deadlock_path(path):
                self.deadlock_path = path
                info = get_current_config_info(path)
                self.status_card.set_status(True, path, info)
                self.footer.set_status("Ready", COLORS["accent_success"])
                ensure_vanilla_backup(path)
                self._update_controls_state()
            else:
                self.footer.set_status("Invalid Deadlock path", COLORS["accent_danger"])
    
    def _update_controls_state(self):
        state = "normal" if self.deadlock_path else "disabled"
        self.action_bar.apply_btn.configure(state=state)
        self.action_bar.backup_btn.configure(state=state)
        self.action_bar.restore_btn.configure(state=state)
    
    def _on_preset_select(self, name: str):
        self.selected_preset = name
        self.footer.set_status(f"Selected: {name.title()}", COLORS["accent_primary"])
    
    def _apply_config(self):
        if not self.deadlock_path or not self.selected_preset:
            self.footer.set_status("Select a preset first", COLORS["accent_warning"])
            return
        
        self.footer.set_status("Applying config...", COLORS["accent_warning"])
        
        presets = list_presets()
        preset = next((p for p in presets if p["name"] == self.selected_preset), None)
        
        if preset and apply_preset(self.deadlock_path, preset["path"]):
            self.footer.set_status(f"✨ Applied {preset['display']}", COLORS["accent_success"])
            info = get_current_config_info(self.deadlock_path)
            self.status_card.set_status(True, self.deadlock_path, info)
        else:
            self.footer.set_status("Failed to apply config", COLORS["accent_danger"])
    
    def _create_backup(self):
        if not self.deadlock_path:
            return
        
        self.footer.set_status("Creating backup...", COLORS["accent_warning"])
        
        if create_backup(self.deadlock_path, label="manual"):
            self.footer.set_status("✅ Backup created", COLORS["accent_success"])
        else:
            self.footer.set_status("Backup failed", COLORS["accent_danger"])
    
    def _show_restore_dialog(self):
        if not self.deadlock_path:
            return
        
        backups = list_backups()
        if not backups:
            self.footer.set_status("No backups available", COLORS["accent_warning"])
            return
        
        dialog = ctk.CTkToplevel(self)
        dialog.title("Restore Backup")
        dialog.geometry("450x350")
        dialog.configure(fg_color=COLORS["bg_dark"])
        dialog.transient(self)
        dialog.grab_set()
        
        # Header
        header = ctk.CTkLabel(
            dialog,
            text="🔄 Restore Backup",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold")
        )
        header.pack(pady=20)
        
        # List
        list_frame = ctk.CTkScrollableFrame(
            dialog,
            fg_color=COLORS["bg_card"],
            corner_radius=12,
            height=200
        )
        list_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        
        selected = ctk.StringVar()
        
        for backup in backups[:15]:
            btn = ctk.CTkRadioButton(
                list_frame,
                text=backup["display"],
                variable=selected,
                value=str(backup["path"]),
                font=ctk.CTkFont(family="Segoe UI", size=12)
            )
            btn.pack(anchor="w", pady=4, padx=10)
        
        def do_restore():
            if selected.get():
                if restore_backup(self.deadlock_path, Path(selected.get())):
                    self.footer.set_status("✅ Restored", COLORS["accent_success"])
                    info = get_current_config_info(self.deadlock_path)
                    self.status_card.set_status(True, self.deadlock_path, info)
                else:
                    self.footer.set_status("Restore failed", COLORS["accent_danger"])
                dialog.destroy()
        
        restore_btn = GradientButton(dialog, text="Restore", style="primary", width=120, height=40, command=do_restore)
        restore_btn.pack(pady=15)
    
    def _check_updates(self):
        self.footer.set_status("Checking for updates...", COLORS["accent_warning"])
        
        def check():
            update = check_for_updates()
            self.after(0, lambda: self._on_update_check(update))
        
        threading.Thread(target=check, daemon=True).start()
    
    def _on_update_check(self, update):
        if update:
            self.footer.set_status(f"Update available: v{update['version']}", COLORS["accent_success"])
            if update.get("html_url"):
                webbrowser.open(update["html_url"])
        else:
            self.footer.set_status("✅ You're up to date", COLORS["accent_success"])


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
