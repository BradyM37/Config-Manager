"""
Main Application Window
Deadlock Config Manager - Premium Edition with All Features
"""

import customtkinter as ctk
from pathlib import Path
from typing import Optional
import threading
import webbrowser
import sys

from src.core.detector import find_deadlock, get_current_config_info, validate_deadlock_path, get_gameinfo_path, get_video_settings_path
from src.core.backup import create_backup, list_backups, restore_backup, ensure_vanilla_backup
from src.core.config import list_presets, apply_preset, get_presets_dir
from src.core.updater import check_for_updates, download_update, apply_update
from src.core.settings import (
    load_settings, save_settings, get_setting, set_setting,
    ACCENT_COLORS, list_profiles, save_profile, load_profile,
    list_custom_presets, save_custom_preset, export_preset, import_preset, delete_custom_preset,
    launch_deadlock, is_deadlock_running, is_startup_enabled, set_startup_enabled,
    GameLaunchWatcher, register_hotkey, start_hotkey_listener, stop_hotkey_listener,
    get_hotkey_presets, set_hotkey_preset
)
from src.core.tray import init_tray, stop_tray, get_tray, TRAY_AVAILABLE
from src.core.notifications import (
    NOTIFICATIONS_AVAILABLE, notify_preset_applied, notify_backup_created,
    notify_game_launched, notify_custom_preset_saved, notify_profile_switched
)
from src.core.config import read_convars
from src.core.community import (
    list_community_presets, install_community_preset, 
    search_community_presets, download_community_preset,
    vote_preset, get_user_vote, submit_preset
)
from src.ui.convar_panel import ConVarPanel, CrosshairPreview
from src import __version__

# App name
APP_NAME = "Deadlock Config Manager"
APP_SHORT = "DCM"


# ============================================================================
# THEME CONFIGURATION
# ============================================================================

def get_colors(accent: str = "purple") -> dict:
    """Get color scheme with selected accent"""
    accent_info = ACCENT_COLORS.get(accent, ACCENT_COLORS["purple"])
    
    return {
        "bg_dark": "#0a0a0f",
        "bg_card": "#12121a", 
        "bg_card_hover": "#1a1a25",
        "bg_elevated": "#1e1e2e",
        "bg_sidebar": "#0d0d14",
        "border": "#2a2a3a",
        "border_glow": "#6366f1",
        "accent_primary": accent_info["primary"],
        "accent_hover": accent_info["hover"],
        "accent_secondary": "#06b6d4",
        "accent_success": "#10b981",
        "accent_warning": "#f59e0b",
        "accent_danger": "#ef4444",
        "text_primary": "#ffffff",
        "text_secondary": "#a1a1aa",
        "text_muted": "#71717a",
    }


# Initial colors - will be updated on load
COLORS = get_colors("purple")

ctk.set_appearance_mode("dark")


# ============================================================================
# CUSTOM COMPONENTS
# ============================================================================

class GradientButton(ctk.CTkButton):
    def __init__(self, parent, style="primary", **kwargs):
        styles = {
            "primary": {"fg_color": COLORS["accent_primary"], "hover_color": COLORS["accent_hover"]},
            "success": {"fg_color": COLORS["accent_success"], "hover_color": "#059669"},
            "secondary": {"fg_color": COLORS["bg_elevated"], "hover_color": COLORS["bg_card_hover"], "border_width": 1, "border_color": COLORS["border"]},
            "danger": {"fg_color": COLORS["accent_danger"], "hover_color": "#dc2626"},
        }
        style_config = styles.get(style, styles["primary"])
        if "font" not in kwargs:
            kwargs["font"] = ctk.CTkFont(family="Segoe UI", size=13, weight="bold")
        super().__init__(parent, corner_radius=8, **style_config, **kwargs)


class StatCard(ctk.CTkFrame):
    def __init__(self, parent, title: str, value: str, icon: str, color: str, **kwargs):
        super().__init__(parent, fg_color=COLORS["bg_card"], corner_radius=10, **kwargs)
        self.configure(border_width=1, border_color=COLORS["border"])
        
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=20, pady=15)
        
        header = ctk.CTkFrame(content, fg_color="transparent")
        header.pack(fill="x")
        
        ctk.CTkLabel(header, text=icon, font=ctk.CTkFont(size=20)).pack(side="left")
        ctk.CTkLabel(header, text=title, font=ctk.CTkFont(size=12), text_color=COLORS["text_muted"]).pack(side="left", padx=10)
        
        self.value_label = ctk.CTkLabel(content, text=value, font=ctk.CTkFont(family="Segoe UI", size=28, weight="bold"), text_color=color)
        self.value_label.pack(anchor="w", pady=(10, 0))
    
    def set_value(self, value: str):
        self.value_label.configure(text=value)


class QuickPresetCard(ctk.CTkFrame):
    ICONS = {"potato": "🥔", "balanced": "⚖️", "quality": "💎", "competitive": "🎯"}
    COLORS_MAP = {"potato": "#f59e0b", "balanced": "#8b5cf6", "quality": "#06b6d4", "competitive": "#ef4444"}
    
    def __init__(self, parent, name: str, display: str, on_apply, **kwargs):
        super().__init__(parent, fg_color=COLORS["bg_card"], corner_radius=10, **kwargs)
        self.name = name
        self.on_apply = on_apply
        self.accent = self.COLORS_MAP.get(name.lower(), COLORS["accent_primary"])
        
        self.configure(border_width=2, border_color=COLORS["border"])
        
        # Content
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=15, pady=15)
        
        icon = ctk.CTkLabel(content, text=self.ICONS.get(name.lower(), "📦"), font=ctk.CTkFont(size=32))
        icon.pack(side="left")
        
        text_frame = ctk.CTkFrame(content, fg_color="transparent")
        text_frame.pack(side="left", padx=15, fill="both", expand=True)
        
        title = ctk.CTkLabel(text_frame, text=display.replace(self.ICONS.get(name.lower(), ""), "").strip(), 
                            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"))
        title.pack(anchor="w")
        
        subtitle = ctk.CTkLabel(text_frame, text="Click to apply", font=ctk.CTkFont(size=11), text_color=COLORS["text_muted"])
        subtitle.pack(anchor="w")
        
        # Bind click to ALL widgets
        clickable_widgets = [self, content, icon, text_frame, title, subtitle]
        for widget in clickable_widgets:
            widget.bind("<Button-1>", self._on_click)
            widget.bind("<Enter>", self._on_enter)
            widget.bind("<Leave>", self._on_leave)
    
    def _on_click(self, event=None):
        self.on_apply(self.name)
    
    def _on_enter(self, event=None):
        self.configure(border_color=self.accent)
    
    def _on_leave(self, event=None):
        # Check if mouse is still within the card bounds
        x, y = self.winfo_pointerxy()
        widget_x = self.winfo_rootx()
        widget_y = self.winfo_rooty()
        widget_w = self.winfo_width()
        widget_h = self.winfo_height()
        
        if not (widget_x <= x <= widget_x + widget_w and widget_y <= y <= widget_y + widget_h):
            self.configure(border_color=COLORS["border"])


# ============================================================================
# DIALOGS
# ============================================================================

class CreatePresetDialog(ctk.CTkToplevel):
    """Dialog for creating a custom preset"""
    
    def __init__(self, parent, gameinfo_path: Path, on_save=None):
        super().__init__(parent)
        
        self.gameinfo_path = gameinfo_path
        self.on_save = on_save
        self.result = None
        
        self.title("Create Custom Preset")
        self.geometry("400x250")
        self.resizable(False, False)
        self.configure(fg_color=COLORS["bg_dark"])
        
        # Center on parent
        self.transient(parent)
        self.grab_set()
        
        self._build_ui()
    
    def _build_ui(self):
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=30, pady=25)
        
        ctk.CTkLabel(content, text="⭐ Save Current Config as Preset", 
                    font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w")
        
        ctk.CTkLabel(content, text="This will save your current gameinfo.gi as a reusable preset.",
                    font=ctk.CTkFont(size=12), text_color=COLORS["text_muted"]).pack(anchor="w", pady=(5, 20))
        
        # Name input
        ctk.CTkLabel(content, text="Preset Name", font=ctk.CTkFont(size=12)).pack(anchor="w")
        self.name_entry = ctk.CTkEntry(content, width=340, height=40, placeholder_text="My Custom Preset")
        self.name_entry.pack(anchor="w", pady=(5, 15))
        
        # Description input
        ctk.CTkLabel(content, text="Description (optional)", font=ctk.CTkFont(size=12)).pack(anchor="w")
        self.desc_entry = ctk.CTkEntry(content, width=340, height=40, placeholder_text="What makes this preset special?")
        self.desc_entry.pack(anchor="w", pady=(5, 20))
        
        # Buttons
        btn_frame = ctk.CTkFrame(content, fg_color="transparent")
        btn_frame.pack(fill="x")
        
        GradientButton(btn_frame, text="Cancel", style="secondary", width=100, command=self.destroy).pack(side="left")
        GradientButton(btn_frame, text="Save Preset", style="success", width=120, command=self._save).pack(side="right")
    
    def _save(self):
        name = self.name_entry.get().strip()
        if not name:
            return
        
        desc = self.desc_entry.get().strip()
        result = save_custom_preset(name, self.gameinfo_path, desc)
        
        if result:
            self.result = {"name": name, "path": result}
            if self.on_save:
                self.on_save(self.result)
            notify_custom_preset_saved(name)
        
        self.destroy()


class ProfileSwitchDialog(ctk.CTkToplevel):
    """Dialog for switching/managing profiles"""
    
    def __init__(self, parent, current_profile: str, on_switch=None):
        super().__init__(parent)
        
        self.current_profile = current_profile
        self.on_switch = on_switch
        
        self.title("Config Profiles")
        self.geometry("450x400")
        self.resizable(False, False)
        self.configure(fg_color=COLORS["bg_dark"])
        
        self.transient(parent)
        self.grab_set()
        
        self._build_ui()
    
    def _build_ui(self):
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=25, pady=20)
        
        ctk.CTkLabel(content, text="📁 Config Profiles", 
                    font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(content, text="Quick switch between different setups",
                    font=ctk.CTkFont(size=12), text_color=COLORS["text_muted"]).pack(anchor="w", pady=(5, 20))
        
        # Profile list
        profiles_frame = ctk.CTkScrollableFrame(content, fg_color=COLORS["bg_card"], corner_radius=10, height=250)
        profiles_frame.pack(fill="both", expand=True)
        
        profiles = list_profiles()
        
        for profile in profiles:
            row = ctk.CTkFrame(profiles_frame, fg_color=COLORS["bg_elevated"] if profile["name"] == self.current_profile else "transparent",
                              corner_radius=8)
            row.pack(fill="x", padx=10, pady=5)
            
            row_content = ctk.CTkFrame(row, fg_color="transparent")
            row_content.pack(fill="x", padx=15, pady=12)
            
            ctk.CTkLabel(row_content, text=profile["display"], font=ctk.CTkFont(size=14, weight="bold")).pack(side="left")
            
            if profile["name"] == self.current_profile:
                ctk.CTkLabel(row_content, text="ACTIVE", font=ctk.CTkFont(size=10), 
                            text_color=COLORS["accent_success"]).pack(side="left", padx=10)
            
            GradientButton(row_content, text="Switch", style="primary" if profile["name"] != self.current_profile else "secondary",
                          width=80, height=30, command=lambda p=profile["name"]: self._switch(p)).pack(side="right")
        
        # Close button
        GradientButton(content, text="Close", style="secondary", width=100, command=self.destroy).pack(pady=(15, 0))
    
    def _switch(self, profile_name: str):
        if self.on_switch:
            self.on_switch(profile_name)
        notify_profile_switched(profile_name)
        self.destroy()


class GameRunningWarningDialog(ctk.CTkToplevel):
    """Warning dialog when trying to apply config while game is running"""
    
    def __init__(self, parent, on_continue=None, on_cancel=None):
        super().__init__(parent)
        
        self.on_continue = on_continue
        self.on_cancel = on_cancel
        self.result = False
        
        self.title("Game Running")
        self.geometry("400x200")
        self.resizable(False, False)
        self.configure(fg_color=COLORS["bg_dark"])
        
        self.transient(parent)
        self.grab_set()
        
        self._build_ui()
    
    def _build_ui(self):
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=30, pady=25)
        
        ctk.CTkLabel(content, text="⚠️ Deadlock is Running", 
                    font=ctk.CTkFont(size=18, weight="bold"),
                    text_color=COLORS["accent_warning"]).pack(anchor="w")
        
        ctk.CTkLabel(content, text="Changing config while the game is running may not\ntake effect until you restart the game.",
                    font=ctk.CTkFont(size=12), text_color=COLORS["text_muted"],
                    justify="left").pack(anchor="w", pady=(10, 25))
        
        btn_frame = ctk.CTkFrame(content, fg_color="transparent")
        btn_frame.pack(fill="x")
        
        GradientButton(btn_frame, text="Cancel", style="secondary", width=100,
                      command=self._cancel).pack(side="left")
        GradientButton(btn_frame, text="Apply Anyway", style="warning" if "warning" in dir(GradientButton) else "primary",
                      width=130, command=self._continue).pack(side="right")
    
    def _continue(self):
        self.result = True
        if self.on_continue:
            self.on_continue()
        self.destroy()
    
    def _cancel(self):
        self.result = False
        if self.on_cancel:
            self.on_cancel()
        self.destroy()


class PresetDiffDialog(ctk.CTkToplevel):
    """Shows what changes a preset will make"""
    
    def __init__(self, parent, preset_name: str, current_convars: dict, preset_convars: dict, on_apply=None):
        super().__init__(parent)
        
        self.preset_name = preset_name
        self.current_convars = current_convars
        self.preset_convars = preset_convars
        self.on_apply = on_apply
        
        self.title(f"Preview: {preset_name}")
        self.geometry("500x450")
        self.resizable(False, False)
        self.configure(fg_color=COLORS["bg_dark"])
        
        self.transient(parent)
        self.grab_set()
        
        self._build_ui()
    
    def _build_ui(self):
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=25, pady=20)
        
        ctk.CTkLabel(content, text=f"📊 Changes for {self.preset_name}", 
                    font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(content, text="These settings will be changed:",
                    font=ctk.CTkFont(size=12), text_color=COLORS["text_muted"]).pack(anchor="w", pady=(5, 15))
        
        # Changes list
        changes_frame = ctk.CTkScrollableFrame(content, fg_color=COLORS["bg_card"], corner_radius=10, height=280)
        changes_frame.pack(fill="both", expand=True)
        
        changes = []
        for name, new_val in self.preset_convars.items():
            old_val = self.current_convars.get(name, "default")
            if str(old_val) != str(new_val):
                changes.append((name, old_val, new_val))
        
        if not changes:
            ctk.CTkLabel(changes_frame, text="No changes - preset matches current config",
                        font=ctk.CTkFont(size=13), text_color=COLORS["text_muted"]).pack(pady=50)
        else:
            for name, old_val, new_val in changes:
                row = ctk.CTkFrame(changes_frame, fg_color="transparent")
                row.pack(fill="x", padx=15, pady=5)
                
                ctk.CTkLabel(row, text=name, font=ctk.CTkFont(size=12, weight="bold"),
                            width=200, anchor="w").pack(side="left")
                ctk.CTkLabel(row, text=str(old_val), font=ctk.CTkFont(size=11),
                            text_color=COLORS["accent_danger"], width=60).pack(side="left")
                ctk.CTkLabel(row, text="→", font=ctk.CTkFont(size=11),
                            text_color=COLORS["text_muted"]).pack(side="left", padx=10)
                ctk.CTkLabel(row, text=str(new_val), font=ctk.CTkFont(size=11),
                            text_color=COLORS["accent_success"], width=60).pack(side="left")
        
        # Summary
        ctk.CTkLabel(content, text=f"{len(changes)} setting(s) will change",
                    font=ctk.CTkFont(size=11), text_color=COLORS["text_muted"]).pack(anchor="w", pady=(10, 0))
        
        # Buttons
        btn_frame = ctk.CTkFrame(content, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(15, 0))
        
        GradientButton(btn_frame, text="Cancel", style="secondary", width=100,
                      command=self.destroy).pack(side="left")
        GradientButton(btn_frame, text="Apply Preset", style="success", width=130,
                      command=self._apply).pack(side="right")
    
    def _apply(self):
        if self.on_apply:
            self.on_apply()
        self.destroy()


class HotkeyDialog(ctk.CTkToplevel):
    """Dialog for configuring global hotkeys"""
    
    def __init__(self, parent, on_save=None):
        super().__init__(parent)
        
        self.on_save = on_save
        
        self.title("Configure Hotkeys")
        self.geometry("450x400")
        self.resizable(False, False)
        self.configure(fg_color=COLORS["bg_dark"])
        
        self.transient(parent)
        self.grab_set()
        
        self._build_ui()
    
    def _build_ui(self):
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=25, pady=20)
        
        ctk.CTkLabel(content, text="⌨️ Global Hotkeys", 
                    font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(content, text="Assign keyboard shortcuts to presets",
                    font=ctk.CTkFont(size=12), text_color=COLORS["text_muted"]).pack(anchor="w", pady=(5, 20))
        
        # Preset hotkey assignments
        presets_frame = ctk.CTkScrollableFrame(content, fg_color=COLORS["bg_card"], corner_radius=10, height=250)
        presets_frame.pack(fill="both", expand=True)
        
        current_hotkeys = get_hotkey_presets()
        presets = [("potato", "🥔 Potato"), ("balanced", "⚖️ Balanced"), 
                   ("quality", "💎 Quality"), ("competitive", "🎯 Competitive")]
        
        self.hotkey_entries = {}
        
        for preset_name, display in presets:
            row = ctk.CTkFrame(presets_frame, fg_color="transparent")
            row.pack(fill="x", padx=15, pady=8)
            
            ctk.CTkLabel(row, text=display, font=ctk.CTkFont(size=13),
                        width=120, anchor="w").pack(side="left")
            
            # Find current hotkey for this preset
            current = ""
            for hk, pn in current_hotkeys.items():
                if pn == preset_name:
                    current = hk
                    break
            
            entry = ctk.CTkEntry(row, width=150, height=35,
                                placeholder_text="e.g. ctrl+shift+1")
            entry.insert(0, current)
            entry.pack(side="right")
            self.hotkey_entries[preset_name] = entry
        
        # Info
        ctk.CTkLabel(content, text="Format: ctrl+shift+1, alt+f1, etc.\nLeave empty to disable.",
                    font=ctk.CTkFont(size=10), text_color=COLORS["text_muted"]).pack(anchor="w", pady=(10, 0))
        
        # Buttons
        btn_frame = ctk.CTkFrame(content, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(15, 0))
        
        GradientButton(btn_frame, text="Cancel", style="secondary", width=100,
                      command=self.destroy).pack(side="left")
        GradientButton(btn_frame, text="Save Hotkeys", style="success", width=130,
                      command=self._save).pack(side="right")
    
    def _save(self):
        for preset_name, entry in self.hotkey_entries.items():
            hotkey = entry.get().strip()
            if hotkey:
                set_hotkey_preset(hotkey, preset_name)
        
        if self.on_save:
            self.on_save()
        self.destroy()


# ============================================================================
# SIDEBAR
# ============================================================================

class Sidebar(ctk.CTkFrame):
    def __init__(self, parent, on_navigate, **kwargs):
        super().__init__(parent, fg_color=COLORS["bg_sidebar"], width=220, **kwargs)
        self.pack_propagate(False)
        self.on_navigate = on_navigate
        self.buttons = {}
        
        # Logo
        logo_frame = ctk.CTkFrame(self, fg_color="transparent")
        logo_frame.pack(fill="x", pady=25, padx=20)
        
        ctk.CTkLabel(logo_frame, text="⚡", font=ctk.CTkFont(size=36)).pack(side="left")
        
        title_frame = ctk.CTkFrame(logo_frame, fg_color="transparent")
        title_frame.pack(side="left", padx=12)
        ctk.CTkLabel(title_frame, text=APP_SHORT, font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(title_frame, text="Config Manager", font=ctk.CTkFont(size=11), text_color=COLORS["text_muted"]).pack(anchor="w")
        
        ctk.CTkFrame(self, height=1, fg_color=COLORS["border"]).pack(fill="x", padx=15)
        
        nav_items = [
            ("dashboard", "🏠", "Dashboard"),
            ("presets", "📦", "Presets"),
            ("community", "🌐", "Community"),
            ("advanced", "🎛️", "Advanced"),
            ("backups", "💾", "Backups"),
            ("settings", "⚙️", "Settings"),
        ]
        
        nav_frame = ctk.CTkFrame(self, fg_color="transparent")
        nav_frame.pack(fill="x", pady=20)
        
        for tab_id, icon, label in nav_items:
            btn = ctk.CTkButton(nav_frame, text=f"  {icon}  {label}", font=ctk.CTkFont(family="Segoe UI", size=14),
                               fg_color="transparent", hover_color=COLORS["bg_card"], anchor="w", height=45, corner_radius=8,
                               command=lambda t=tab_id: self._on_click(t))
            btn.pack(fill="x", padx=12, pady=3)
            self.buttons[tab_id] = btn
        
        # Bottom
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(side="bottom", fill="x", pady=20, padx=20)
        
        ctk.CTkLabel(bottom, text=f"v{__version__}", font=ctk.CTkFont(size=11), text_color=COLORS["text_muted"]).pack(anchor="w")
        self.status_label = ctk.CTkLabel(bottom, text="Ready", font=ctk.CTkFont(size=11), text_color=COLORS["accent_success"])
        self.status_label.pack(anchor="w")
    
    def _on_click(self, tab_id):
        self.set_active(tab_id)
        self.on_navigate(tab_id)
    
    def set_active(self, tab_id):
        for tid, btn in self.buttons.items():
            btn.configure(fg_color=COLORS["accent_primary"] if tid == tab_id else "transparent")
    
    def set_status(self, text: str, color: str = None):
        self.status_label.configure(text=text, text_color=color or COLORS["accent_success"])


# ============================================================================
# DASHBOARD TAB
# ============================================================================

class DashboardTab(ctk.CTkFrame):
    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.app = app
        self._build_ui()
    
    def _build_ui(self):
        # Header with Launch button
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(header, text="Dashboard", font=ctk.CTkFont(family="Segoe UI", size=28, weight="bold")).pack(side="left")
        
        # Launch Game Button
        self.launch_btn = GradientButton(header, text="🚀 Launch Deadlock", style="success", 
                                        width=180, height=42, command=self._launch_game)
        self.launch_btn.pack(side="right")
        
        # Reset to Vanilla
        self.reset_btn = GradientButton(header, text="🔄 Reset", style="danger",
                                        width=90, height=42, command=self._reset_to_vanilla)
        self.reset_btn.pack(side="right", padx=5)
        
        # Profile switcher
        self.profile_btn = GradientButton(header, text="📁 Profiles", style="secondary",
                                         width=100, height=42, command=self._show_profiles)
        self.profile_btn.pack(side="right", padx=5)
        
        # Stats row
        stats_frame = ctk.CTkFrame(self, fg_color="transparent")
        stats_frame.pack(fill="x", pady=(0, 25))
        
        for i in range(3):
            stats_frame.grid_columnconfigure(i, weight=1)
        
        self.game_stat = StatCard(stats_frame, "Game Status", "Searching...", "🎮", COLORS["accent_success"])
        self.game_stat.grid(row=0, column=0, padx=(0, 10), sticky="nsew")
        
        self.config_stat = StatCard(stats_frame, "Active Config", "—", "⚡", COLORS["accent_primary"])
        self.config_stat.grid(row=0, column=1, padx=10, sticky="nsew")
        
        self.backups_stat = StatCard(stats_frame, "Backups", "0", "💾", COLORS["accent_secondary"])
        self.backups_stat.grid(row=0, column=2, padx=(10, 0), sticky="nsew")
        
        # Quick Apply
        ctk.CTkLabel(self, text="⚡ Quick Apply", font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
                    text_color=COLORS["text_secondary"]).pack(anchor="w", pady=(10, 15))
        
        presets_grid = ctk.CTkFrame(self, fg_color="transparent")
        presets_grid.pack(fill="x", pady=(0, 25))
        
        presets = [("potato", "🥔 Potato"), ("balanced", "⚖️ Balanced"), ("quality", "💎 Quality"), ("competitive", "🎯 Competitive")]
        
        for i in range(4):
            presets_grid.grid_columnconfigure(i, weight=1)
        
        for i, (name, display) in enumerate(presets):
            card = QuickPresetCard(presets_grid, name, display, self._quick_apply)
            card.grid(row=0, column=i, padx=5, pady=5, sticky="nsew")
        
        # Recent Activity
        ctk.CTkLabel(self, text="📋 Recent Activity", font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
                    text_color=COLORS["text_secondary"]).pack(anchor="w", pady=(10, 15))
        
        self.activity_frame = ctk.CTkScrollableFrame(self, fg_color=COLORS["bg_card"], corner_radius=10)
        self.activity_frame.pack(fill="both", expand=True)
        
        self.activity_placeholder = ctk.CTkLabel(self.activity_frame, text="No recent activity\n\nApply a config preset to see activity here",
                                                 font=ctk.CTkFont(size=13), text_color=COLORS["text_muted"])
        self.activity_placeholder.pack(expand=True, pady=50)
    
    def _launch_game(self):
        """Launch Deadlock and optionally apply config"""
        if self.app.deadlock_path:
            # Ask if they want to apply current preset first
            self.app.sidebar.set_status("Launching...", COLORS["accent_warning"])
            notify_game_launched()
            launch_deadlock()
            self.app.sidebar.set_status("Game launched", COLORS["accent_success"])
        else:
            # Just launch anyway
            launch_deadlock()
    
    def _show_profiles(self):
        """Show profile switcher dialog"""
        current = get_setting("last_profile", "default")
        ProfileSwitchDialog(self.app, current, self._on_profile_switch)
    
    def _on_profile_switch(self, profile_name: str):
        set_setting("last_profile", profile_name)
        profile = load_profile(profile_name)
        if profile and profile.get("preset") and self.app.deadlock_path:
            self.app._apply_preset(profile["preset"])
    
    def _quick_apply(self, preset_name):
        if self.app.deadlock_path:
            self.app._apply_preset(preset_name)
    
    def _reset_to_vanilla(self):
        """Reset config to vanilla (original) state"""
        if not self.app.deadlock_path:
            self.app.sidebar.set_status("No game found", COLORS["accent_warning"])
            return
        
        # Find vanilla backup
        backups = list_backups()
        vanilla = next((b for b in backups if "vanilla" in b.get("label", "").lower()), None)
        
        if vanilla and restore_backup(self.app.deadlock_path, vanilla["path"]):
            self.app.sidebar.set_status("Reset to vanilla", COLORS["accent_success"])
            self.refresh()
        else:
            self.app.sidebar.set_status("No vanilla backup", COLORS["accent_warning"])
    
    def refresh(self):
        if self.app.deadlock_path:
            self.game_stat.set_value("Detected")
            info = get_current_config_info(self.app.deadlock_path)
            self.config_stat.set_value(info.get("name", "Vanilla") if info.get("installed") else "Vanilla")
        else:
            self.game_stat.set_value("Not Found")
            self.config_stat.set_value("—")
        
        self.backups_stat.set_value(str(len(list_backups())))


# ============================================================================
# PRESETS TAB
# ============================================================================

class PresetCard(ctk.CTkFrame):
    ICONS = {"potato": "🥔", "balanced": "⚖️", "quality": "💎", "competitive": "🎯"}
    COLORS_MAP = {"potato": "#f59e0b", "balanced": "#8b5cf6", "quality": "#06b6d4", "competitive": "#ef4444"}
    
    def __init__(self, parent, preset: dict, on_select, on_delete=None, selected=False, **kwargs):
        super().__init__(parent, fg_color=COLORS["bg_card"], corner_radius=12, **kwargs)
        self.preset = preset
        self.name = preset.get("name", "")
        self.on_select = on_select
        self.on_delete = on_delete
        self.selected = selected
        self.is_custom = preset.get("custom", False)
        self.accent = self.COLORS_MAP.get(self.name.lower(), COLORS["accent_primary"])
        
        self.configure(border_width=2, border_color=self.accent if selected else COLORS["border"])
        self.bind("<Button-1>", self._on_click)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        
        # Delete button for custom presets (top right corner)
        if self.is_custom and on_delete:
            self.delete_btn = ctk.CTkButton(self, text="✕", width=24, height=24,
                                           fg_color="transparent", hover_color=COLORS["accent_danger"],
                                           text_color=COLORS["text_muted"], font=ctk.CTkFont(size=14),
                                           command=self._on_delete_click)
            self.delete_btn.place(relx=1.0, rely=0, x=-8, y=8, anchor="ne")
        
        icon_text = "⭐" if self.is_custom else self.ICONS.get(self.name.lower(), "📦")
        icon = ctk.CTkLabel(self, text=icon_text, font=ctk.CTkFont(size=48))
        icon.pack(pady=(25, 10))
        icon.bind("<Button-1>", self._on_click)
        
        display_name = preset.get("display", self.name).replace(self.ICONS.get(self.name.lower(), ""), "").replace("⭐", "").strip()
        self.title_label = ctk.CTkLabel(self, text=display_name,
                                        font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
                                        text_color=self.accent if selected else COLORS["text_primary"])
        self.title_label.pack()
        self.title_label.bind("<Button-1>", self._on_click)
        
        ctk.CTkLabel(self, text=preset.get("description", ""), font=ctk.CTkFont(size=12),
                    text_color=COLORS["text_muted"], wraplength=160).pack(pady=(8, 25), padx=15)
    
    def _on_click(self, e=None): self.on_select(self.name)
    def _on_delete_click(self):
        if self.on_delete:
            self.on_delete(self.name)
    def _on_enter(self, e=None):
        if not self.selected: self.configure(border_color=self.accent)
    def _on_leave(self, e=None):
        if not self.selected: self.configure(border_color=COLORS["border"])
    
    def set_selected(self, selected: bool):
        self.selected = selected
        self.configure(border_color=self.accent if selected else COLORS["border"], border_width=3 if selected else 2)
        self.title_label.configure(text_color=self.accent if selected else COLORS["text_primary"])


class PresetsTab(ctk.CTkFrame):
    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.app = app
        self.cards = {}
        self.selected = None
        self._build_ui()
    
    def _build_ui(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(header, text="Config Presets", font=ctk.CTkFont(family="Segoe UI", size=28, weight="bold")).pack(side="left")
        
        # Buttons row
        btn_frame = ctk.CTkFrame(header, fg_color="transparent")
        btn_frame.pack(side="right")
        
        GradientButton(btn_frame, text="📥 Import", style="secondary", width=100, height=40, command=self._import_preset).pack(side="left", padx=5)
        GradientButton(btn_frame, text="⭐ Create", style="secondary", width=100, height=40, command=self._create_preset).pack(side="left", padx=5)
        GradientButton(btn_frame, text="Apply Selected", style="success", width=150, height=40, command=self._apply_selected).pack(side="left", padx=5)
        
        # Scrollable grid for presets
        self.grid_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.grid_scroll.pack(fill="both", expand=True)
        
        self._refresh_presets()
    
    def _refresh_presets(self):
        # Clear existing cards
        for widget in self.grid_scroll.winfo_children():
            widget.destroy()
        self.cards.clear()
        
        # Get all presets (built-in + custom)
        presets = [
            {"name": "potato", "display": "🥔 Potato", "description": "Maximum FPS, minimum visuals. For low-end PCs."},
            {"name": "balanced", "display": "⚖️ Balanced", "description": "Best of both worlds. Recommended for most."},
            {"name": "quality", "display": "💎 Quality", "description": "Enhanced visuals while staying optimized."},
            {"name": "competitive", "display": "🎯 Competitive", "description": "Pro visibility settings for ranked play."},
        ]
        
        try:
            actual = list_presets()
            if actual: presets = actual
        except: pass
        
        # Add custom presets
        custom = list_custom_presets()
        presets.extend(custom)
        
        # Create grid
        grid = ctk.CTkFrame(self.grid_scroll, fg_color="transparent")
        grid.pack(fill="both", expand=True)
        
        cols = 4
        for i in range(cols):
            grid.grid_columnconfigure(i, weight=1)
        
        for i, preset in enumerate(presets):
            row = i // cols
            col = i % cols
            card = PresetCard(grid, preset, self._on_select, on_delete=self._delete_preset if preset.get("custom") else None)
            card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
            self.cards[preset["name"]] = card
    
    def _on_select(self, name):
        if self.selected and self.selected in self.cards:
            self.cards[self.selected].set_selected(False)
        self.selected = name
        if name in self.cards:
            self.cards[name].set_selected(True)
        self.app.selected_preset = name
    
    def _apply_selected(self):
        if self.selected:
            self.app._apply_preset(self.selected)
    
    def _create_preset(self):
        """Open create preset dialog"""
        if self.app.deadlock_path:
            gameinfo = get_gameinfo_path(self.app.deadlock_path)
            CreatePresetDialog(self.app, gameinfo, self._on_preset_created)
    
    def _on_preset_created(self, result):
        self._refresh_presets()
    
    def _import_preset(self):
        """Import a preset file"""
        path = ctk.filedialog.askopenfilename(
            title="Import Preset",
            filetypes=[("Gameinfo files", "*.gi"), ("All files", "*.*")]
        )
        if path:
            result = import_preset(Path(path))
            if result:
                self.app.sidebar.set_status("Preset imported", COLORS["accent_success"])
                self._refresh_presets()
    
    def _delete_preset(self, name: str):
        """Delete a custom preset"""
        # Confirm deletion
        confirm = ctk.CTkInputDialog(
            text=f"Type 'delete' to confirm removing '{name}':",
            title="Delete Preset"
        )
        if confirm.get_input() == "delete":
            if delete_custom_preset(name):
                self.app.sidebar.set_status(f"Deleted '{name}'", COLORS["accent_success"])
                if self.selected == name:
                    self.selected = None
                self._refresh_presets()
            else:
                self.app.sidebar.set_status("Failed to delete preset", COLORS["accent_danger"])


# ============================================================================
# ADVANCED TAB
# ============================================================================

class AdvancedTab(ctk.CTkFrame):
    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.app = app
        self._build_ui()
    
    def _build_ui(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(header, text="Advanced Tweaks", font=ctk.CTkFont(family="Segoe UI", size=28, weight="bold")).pack(side="left")
        
        btn_frame = ctk.CTkFrame(header, fg_color="transparent")
        btn_frame.pack(side="right")
        
        GradientButton(btn_frame, text="🔄 Reload", style="secondary", width=100, height=40, command=self.refresh).pack(side="left", padx=5)
        GradientButton(btn_frame, text="Apply Changes", style="success", width=150, height=40, command=self._apply).pack(side="left", padx=5)
        
        # Status label
        self.status_label = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=12), text_color=COLORS["text_muted"])
        self.status_label.pack(anchor="w", pady=(0, 10))
        
        # ConVar panel
        self.panel = ConVarPanel(self, fg_color=COLORS["bg_card"], corner_radius=10)
        self.panel.pack(fill="both", expand=True)
    
    def refresh(self):
        """Load current values from gameinfo.gi and video.txt"""
        if self.app.deadlock_path:
            gameinfo = get_gameinfo_path(self.app.deadlock_path)
            video = get_video_settings_path(self.app.deadlock_path)
            self.panel.load_current_values(gameinfo, video)
            self.status_label.configure(text="✓ Loaded settings from gameinfo.gi and video.txt", text_color=COLORS["accent_success"])
        else:
            self.status_label.configure(text="⚠ Game not detected - showing defaults", text_color=COLORS["accent_warning"])
    
    def _apply(self):
        """Apply changes to gameinfo.gi (convars) and video.txt (graphics)"""
        if not self.app.deadlock_path:
            self.app.sidebar.set_status("No game found", COLORS["accent_warning"])
            return
        
        from src.core.config import modify_convars, write_video_settings
        
        convar_values, video_values = self.panel.get_values_by_source()
        
        success = True
        total = 0
        
        # Apply convars to gameinfo.gi
        if convar_values:
            if modify_convars(self.app.deadlock_path, convar_values):
                total += len(convar_values)
            else:
                success = False
        
        # Apply video settings to video.txt
        if video_values:
            if write_video_settings(self.app.deadlock_path, video_values):
                total += len(video_values)
            else:
                success = False
        
        if success:
            self.app.sidebar.set_status("Applied tweaks", COLORS["accent_success"])
            self.status_label.configure(text=f"✓ Applied {total} settings", text_color=COLORS["accent_success"])
        else:
            self.app.sidebar.set_status("Some changes failed", COLORS["accent_warning"])


# ============================================================================
# BACKUPS TAB
# ============================================================================

class BackupsTab(ctk.CTkFrame):
    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.app = app
        self._build_ui()
    
    def _build_ui(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(header, text="Backups", font=ctk.CTkFont(family="Segoe UI", size=28, weight="bold")).pack(side="left")
        GradientButton(header, text="Create Backup", style="primary", width=150, height=40, command=self._create_backup).pack(side="right")
        
        self.list_frame = ctk.CTkScrollableFrame(self, fg_color=COLORS["bg_card"], corner_radius=10)
        self.list_frame.pack(fill="both", expand=True)
        
        self.refresh()
    
    def refresh(self):
        for widget in self.list_frame.winfo_children():
            widget.destroy()
        
        backups = list_backups()
        
        if not backups:
            ctk.CTkLabel(self.list_frame, text="No backups yet\n\nCreate a backup before making changes", font=ctk.CTkFont(size=14),
                        text_color=COLORS["text_muted"]).pack(expand=True, pady=50)
            return
        
        for backup in backups[:30]:
            row = ctk.CTkFrame(self.list_frame, fg_color=COLORS["bg_elevated"], corner_radius=8)
            row.pack(fill="x", padx=10, pady=5)
            
            content = ctk.CTkFrame(row, fg_color="transparent")
            content.pack(fill="x", padx=15, pady=12)
            
            ctk.CTkLabel(content, text="💾", font=ctk.CTkFont(size=18)).pack(side="left")
            ctk.CTkLabel(content, text=backup["display"], font=ctk.CTkFont(size=13)).pack(side="left", padx=15)
            GradientButton(content, text="Restore", style="secondary", width=90, height=32, command=lambda p=backup["path"]: self._restore(p)).pack(side="right")
    
    def _create_backup(self):
        if self.app.deadlock_path:
            if create_backup(self.app.deadlock_path, label="manual"):
                self.app.sidebar.set_status("Backup created", COLORS["accent_success"])
                notify_backup_created()
                self.refresh()
    
    def _restore(self, path):
        if self.app.deadlock_path and restore_backup(self.app.deadlock_path, path):
            self.app.sidebar.set_status("Restored", COLORS["accent_success"])
            self.app.dashboard.refresh()


# ============================================================================
# COMMUNITY TAB
# ============================================================================

class CommunityPresetCard(ctk.CTkFrame):
    """Card for a community preset with voting and download stats"""
    
    def __init__(self, parent, preset: dict, on_install, on_vote, **kwargs):
        super().__init__(parent, fg_color=COLORS["bg_card"], corner_radius=10, **kwargs)
        self.preset = preset
        self.on_install = on_install
        self.on_vote = on_vote
        self.preset_id = preset.get("id", "")
        
        self.configure(border_width=1, border_color=COLORS["border"])
        self.bind("<Enter>", lambda e: self.configure(border_color=COLORS["accent_primary"]))
        self.bind("<Leave>", lambda e: self.configure(border_color=COLORS["border"]))
        
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=15, pady=15)
        
        # Header row with name and install button
        header = ctk.CTkFrame(content, fg_color="transparent")
        header.pack(fill="x")
        
        ctk.CTkLabel(header, text=preset.get("name", "Unknown"),
                    font=ctk.CTkFont(size=15, weight="bold")).pack(side="left")
        
        GradientButton(header, text="Install", style="success", width=80, height=30,
                      command=lambda: on_install(self.preset_id)).pack(side="right")
        
        # Author and stats row
        info_frame = ctk.CTkFrame(content, fg_color="transparent")
        info_frame.pack(fill="x", pady=(5, 0))
        
        ctk.CTkLabel(info_frame, text=f"by {preset.get('author', 'anonymous')}",
                    font=ctk.CTkFont(size=11), text_color=COLORS["text_muted"]).pack(side="left")
        
        # Stats: downloads
        downloads = preset.get("downloads", 0)
        ctk.CTkLabel(info_frame, text=f"📥 {downloads}",
                    font=ctk.CTkFont(size=11), text_color=COLORS["text_muted"]).pack(side="right", padx=(10, 0))
        
        # Description
        desc = preset.get("description", "")
        if desc:
            ctk.CTkLabel(content, text=desc,
                        font=ctk.CTkFont(size=12), text_color=COLORS["text_secondary"],
                        wraplength=400).pack(anchor="w", pady=(8, 0))
        
        # Bottom row: tags and voting
        bottom_frame = ctk.CTkFrame(content, fg_color="transparent")
        bottom_frame.pack(fill="x", pady=(10, 0))
        
        # Tags on the left
        tags = preset.get("tags", [])
        if tags:
            tags_frame = ctk.CTkFrame(bottom_frame, fg_color="transparent")
            tags_frame.pack(side="left")
            
            for tag in tags[:4]:
                tag_label = ctk.CTkLabel(tags_frame, text=tag,
                                        font=ctk.CTkFont(size=10),
                                        fg_color=COLORS["bg_elevated"],
                                        corner_radius=4)
                tag_label.pack(side="left", padx=(0, 5))
        
        # Voting on the right
        vote_frame = ctk.CTkFrame(bottom_frame, fg_color="transparent")
        vote_frame.pack(side="right")
        
        upvotes = preset.get("upvotes", 0)
        downvotes = preset.get("downvotes", 0)
        score = upvotes - downvotes
        
        # Downvote button
        self.downvote_btn = ctk.CTkButton(
            vote_frame, text="👎", width=32, height=28,
            fg_color="transparent", hover_color=COLORS["accent_danger"],
            font=ctk.CTkFont(size=14),
            command=lambda: self._vote(-1)
        )
        self.downvote_btn.pack(side="left", padx=2)
        
        # Score display
        score_color = COLORS["accent_success"] if score > 0 else (COLORS["accent_danger"] if score < 0 else COLORS["text_muted"])
        self.score_label = ctk.CTkLabel(vote_frame, text=f"{score:+d}" if score != 0 else "0",
                                        font=ctk.CTkFont(size=13, weight="bold"),
                                        text_color=score_color, width=40)
        self.score_label.pack(side="left", padx=5)
        
        # Upvote button
        self.upvote_btn = ctk.CTkButton(
            vote_frame, text="👍", width=32, height=28,
            fg_color="transparent", hover_color=COLORS["accent_success"],
            font=ctk.CTkFont(size=14),
            command=lambda: self._vote(1)
        )
        self.upvote_btn.pack(side="left", padx=2)
    
    def _vote(self, vote_type: int):
        """Handle vote click"""
        if self.on_vote:
            self.on_vote(self.preset_id, vote_type)


class CommunityTab(ctk.CTkFrame):
    """Community presets browser with voting and stats"""
    
    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.app = app
        self.presets = []
        self.sort_by = "downloads"  # downloads, upvotes, created_at
        self._build_ui()
    
    def _build_ui(self):
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(header, text="Community Presets",
                    font=ctk.CTkFont(family="Segoe UI", size=28, weight="bold")).pack(side="left")
        
        btn_frame = ctk.CTkFrame(header, fg_color="transparent")
        btn_frame.pack(side="right")
        
        GradientButton(btn_frame, text="🔄 Refresh", style="secondary", width=100, height=40,
                      command=self._refresh_presets).pack(side="left", padx=5)
        GradientButton(btn_frame, text="📤 Submit Yours", style="primary", width=130, height=40,
                      command=self._submit_preset).pack(side="left", padx=5)
        
        # Search and sort row
        filter_frame = ctk.CTkFrame(self, fg_color="transparent")
        filter_frame.pack(fill="x", pady=(0, 15))
        
        # Search
        ctk.CTkLabel(filter_frame, text="🔍", font=ctk.CTkFont(size=16)).pack(side="left", padx=(0, 10))
        
        self.search_entry = ctk.CTkEntry(filter_frame, placeholder_text="Search presets...",
                                         width=300, height=40)
        self.search_entry.pack(side="left")
        self.search_entry.bind("<KeyRelease>", self._on_search)
        
        # Sort dropdown
        ctk.CTkLabel(filter_frame, text="Sort by:", font=ctk.CTkFont(size=12),
                    text_color=COLORS["text_muted"]).pack(side="left", padx=(20, 5))
        
        self.sort_menu = ctk.CTkOptionMenu(
            filter_frame, values=["Most Downloads", "Most Liked", "Newest"],
            width=140, height=35,
            fg_color=COLORS["bg_elevated"],
            button_color=COLORS["bg_card"],
            button_hover_color=COLORS["bg_card_hover"],
            command=self._on_sort_change
        )
        self.sort_menu.pack(side="left")
        
        self.result_count = ctk.CTkLabel(filter_frame, text="",
                                         font=ctk.CTkFont(size=11), text_color=COLORS["text_muted"])
        self.result_count.pack(side="right", padx=10)
        
        # Presets list
        self.presets_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.presets_frame.pack(fill="both", expand=True)
        
        # Loading placeholder
        self.loading_label = ctk.CTkLabel(self.presets_frame, 
                                          text="Loading community presets...",
                                          font=ctk.CTkFont(size=14), text_color=COLORS["text_muted"])
        self.loading_label.pack(pady=50)
    
    def refresh(self):
        """Called when tab becomes visible"""
        self._refresh_presets()
    
    def _on_sort_change(self, choice: str):
        """Handle sort dropdown change"""
        sort_map = {
            "Most Downloads": "downloads",
            "Most Liked": "upvotes", 
            "Newest": "created_at"
        }
        self.sort_by = sort_map.get(choice, "downloads")
        self._refresh_presets()
    
    def _refresh_presets(self, force: bool = True):
        """Fetch and display community presets"""
        # Show loading
        for widget in self.presets_frame.winfo_children():
            widget.destroy()
        self.loading_label = ctk.CTkLabel(self.presets_frame, 
                                          text="Loading...",
                                          font=ctk.CTkFont(size=14), text_color=COLORS["text_muted"])
        self.loading_label.pack(pady=50)
        
        def fetch():
            presets = list_community_presets(sort_by=self.sort_by)
            self.after(0, lambda: self._display_presets(presets))
        
        threading.Thread(target=fetch, daemon=True).start()
    
    def _display_presets(self, presets: list):
        """Display presets in the UI"""
        # Clear existing
        for widget in self.presets_frame.winfo_children():
            widget.destroy()
        
        self.presets = presets
        
        if not presets:
            ctk.CTkLabel(self.presets_frame, 
                        text="No community presets available yet.\n\nBe the first to submit one!",
                        font=ctk.CTkFont(size=14), text_color=COLORS["text_muted"]).pack(pady=50)
            self.result_count.configure(text="")
            return
        
        self.result_count.configure(text=f"{len(presets)} presets")
        
        for preset in presets:
            card = CommunityPresetCard(self.presets_frame, preset, self._install_preset, self._vote_preset)
            card.pack(fill="x", pady=5)
    
    def _on_search(self, event=None):
        """Filter presets by search query"""
        query = self.search_entry.get().strip()
        
        if not query:
            self._refresh_presets(force=False)
            return
        
        def search():
            filtered = search_community_presets(query)
            self.after(0, lambda: self._display_presets(filtered))
        
        threading.Thread(target=search, daemon=True).start()
    
    def _install_preset(self, preset_id: str):
        """Install a community preset"""
        if not self.app.deadlock_path:
            self.app.sidebar.set_status("No game found", COLORS["accent_warning"])
            return
        
        self.app.sidebar.set_status("Installing...", COLORS["accent_warning"])
        
        def install():
            success = install_community_preset(preset_id, self.app.deadlock_path)
            
            if success:
                self.after(0, lambda: self.app.sidebar.set_status("Preset installed!", COLORS["accent_success"]))
                self.after(0, self.app.dashboard.refresh)
            else:
                self.after(0, lambda: self.app.sidebar.set_status("Install failed", COLORS["accent_danger"]))
        
        threading.Thread(target=install, daemon=True).start()
    
    def _vote_preset(self, preset_id: str, vote_type: int):
        """Vote on a community preset"""
        def do_vote():
            success = vote_preset(preset_id, vote_type)
            if success:
                # Refresh to show updated counts
                self.after(500, lambda: self._refresh_presets(force=True))
        
        threading.Thread(target=do_vote, daemon=True).start()
    
    def _submit_preset(self):
        """Open dialog to submit a preset"""
        SubmitPresetDialog(self.app, self.app.deadlock_path, on_submit=self._on_preset_submitted)
    
    def _on_preset_submitted(self):
        """Called after a preset is submitted"""
        self.app.sidebar.set_status("Preset submitted for review!", COLORS["accent_success"])


class SubmitPresetDialog(ctk.CTkToplevel):
    """Dialog for submitting a preset to the community via Supabase"""
    
    def __init__(self, parent, deadlock_path: Path, on_submit=None):
        super().__init__(parent)
        
        self.deadlock_path = deadlock_path
        self.on_submit = on_submit
        
        self.title("Submit to Community")
        self.geometry("450x600")
        self.resizable(False, False)
        self.configure(fg_color=COLORS["bg_dark"])
        
        self.transient(parent)
        self.grab_set()
        
        self._build_ui()
    
    def _build_ui(self):
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=30, pady=25)
        
        ctk.CTkLabel(content, text="📤 Submit Your Preset",
                    font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(content, text="Share your config with the community!",
                    font=ctk.CTkFont(size=12), text_color=COLORS["text_muted"]).pack(anchor="w", pady=(5, 20))
        
        # Name
        ctk.CTkLabel(content, text="Preset Name *", font=ctk.CTkFont(size=12)).pack(anchor="w")
        self.name_entry = ctk.CTkEntry(content, width=390, height=40,
                                       placeholder_text="My Awesome Config")
        self.name_entry.pack(anchor="w", pady=(5, 15))
        
        # Author
        ctk.CTkLabel(content, text="Your Name *", font=ctk.CTkFont(size=12)).pack(anchor="w")
        self.author_entry = ctk.CTkEntry(content, width=390, height=40,
                                         placeholder_text="YourUsername")
        self.author_entry.pack(anchor="w", pady=(5, 15))
        
        # Description
        ctk.CTkLabel(content, text="Description", font=ctk.CTkFont(size=12)).pack(anchor="w")
        self.desc_entry = ctk.CTkEntry(content, width=390, height=40,
                                       placeholder_text="What makes this config special?")
        self.desc_entry.pack(anchor="w", pady=(5, 15))
        
        # Tags
        ctk.CTkLabel(content, text="Tags (comma separated)", font=ctk.CTkFont(size=12)).pack(anchor="w")
        self.tags_entry = ctk.CTkEntry(content, width=390, height=40,
                                       placeholder_text="competitive, fps, potato")
        self.tags_entry.pack(anchor="w", pady=(5, 15))
        
        # Info
        ctk.CTkLabel(content, text="Your preset will be reviewed before appearing publicly.",
                    font=ctk.CTkFont(size=10), text_color=COLORS["text_muted"]).pack(anchor="w")
        
        # Status label
        self.status_label = ctk.CTkLabel(content, text="",
                                         font=ctk.CTkFont(size=11), text_color=COLORS["accent_warning"])
        self.status_label.pack(anchor="w", pady=(5, 0))
        
        # Buttons
        btn_frame = ctk.CTkFrame(content, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(15, 0))
        
        GradientButton(btn_frame, text="Cancel", style="secondary", width=100,
                      command=self.destroy).pack(side="left")
        self.submit_btn = GradientButton(btn_frame, text="Submit →", style="success", width=130,
                                         command=self._submit)
        self.submit_btn.pack(side="right")
    
    def _submit(self):
        name = self.name_entry.get().strip()
        author = self.author_entry.get().strip()
        desc = self.desc_entry.get().strip()
        tags_raw = self.tags_entry.get().strip()
        
        if not name:
            self.status_label.configure(text="Please enter a preset name", text_color=COLORS["accent_danger"])
            return
        
        if not author:
            self.status_label.configure(text="Please enter your name", text_color=COLORS["accent_danger"])
            return
        
        # Parse tags
        tags = [t.strip() for t in tags_raw.split(",") if t.strip()] if tags_raw else []
        
        # Get current convars from the game
        if self.deadlock_path:
            convars = read_convars(self.deadlock_path)
        else:
            self.status_label.configure(text="No game detected - can't read config", text_color=COLORS["accent_danger"])
            return
        
        if not convars:
            self.status_label.configure(text="No config changes to submit", text_color=COLORS["accent_danger"])
            return
        
        # Disable button and show submitting
        self.submit_btn.configure(state="disabled", text="Submitting...")
        self.status_label.configure(text="Submitting...", text_color=COLORS["accent_warning"])
        
        def do_submit():
            result = submit_preset(name, author, desc, convars, tags)
            
            if result:
                self.after(0, self._on_success)
            else:
                self.after(0, self._on_failure)
        
        threading.Thread(target=do_submit, daemon=True).start()
    
    def _on_success(self):
        self.status_label.configure(text="✓ Submitted! Pending review.", text_color=COLORS["accent_success"])
        if self.on_submit:
            self.on_submit()
        self.after(1500, self.destroy)
    
    def _on_failure(self):
        self.submit_btn.configure(state="normal", text="Submit →")
        self.status_label.configure(text="Failed to submit. Try again.", text_color=COLORS["accent_danger"])


# ============================================================================
# SETTINGS TAB
# ============================================================================

class SettingsTab(ctk.CTkFrame):
    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.app = app
        self._build_ui()
    
    def _build_ui(self):
        ctk.CTkLabel(self, text="Settings", font=ctk.CTkFont(family="Segoe UI", size=28, weight="bold")).pack(anchor="w", pady=(0, 20))
        
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True)
        
        # Game path
        path_section = ctk.CTkFrame(scroll, fg_color=COLORS["bg_card"], corner_radius=10)
        path_section.pack(fill="x", pady=(0, 15))
        
        path_content = ctk.CTkFrame(path_section, fg_color="transparent")
        path_content.pack(fill="x", padx=25, pady=20)
        
        ctk.CTkLabel(path_content, text="🎮 Game Location", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w")
        self.path_label = ctk.CTkLabel(path_content, text="Not detected", font=ctk.CTkFont(size=13), text_color=COLORS["text_secondary"])
        self.path_label.pack(anchor="w", pady=(8, 12))
        GradientButton(path_content, text="Browse", style="secondary", width=120, height=36, command=self.app._browse_path).pack(anchor="w")
        
        # Accent Color
        color_section = ctk.CTkFrame(scroll, fg_color=COLORS["bg_card"], corner_radius=10)
        color_section.pack(fill="x", pady=(0, 15))
        
        color_content = ctk.CTkFrame(color_section, fg_color="transparent")
        color_content.pack(fill="x", padx=25, pady=20)
        
        ctk.CTkLabel(color_content, text="🎨 Accent Color", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(color_content, text="Choose your theme color", font=ctk.CTkFont(size=12), text_color=COLORS["text_muted"]).pack(anchor="w", pady=(5, 12))
        
        colors_frame = ctk.CTkFrame(color_content, fg_color="transparent")
        colors_frame.pack(anchor="w")
        
        current_accent = get_setting("accent_color", "purple")
        for color_name, color_info in ACCENT_COLORS.items():
            btn = ctk.CTkButton(
                colors_frame, text="", width=40, height=40, corner_radius=20,
                fg_color=color_info["primary"], hover_color=color_info["hover"],
                border_width=3 if color_name == current_accent else 0,
                border_color=COLORS["text_primary"],
                command=lambda c=color_name: self._set_accent(c)
            )
            btn.pack(side="left", padx=5)
        
        # System Tray
        if TRAY_AVAILABLE:
            tray_section = ctk.CTkFrame(scroll, fg_color=COLORS["bg_card"], corner_radius=10)
            tray_section.pack(fill="x", pady=(0, 15))
            
            tray_content = ctk.CTkFrame(tray_section, fg_color="transparent")
            tray_content.pack(fill="x", padx=25, pady=20)
            
            ctk.CTkLabel(tray_content, text="🔲 System Tray", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w")
            
            self.tray_var = ctk.BooleanVar(value=get_setting("minimize_to_tray", True))
            ctk.CTkSwitch(tray_content, text="Minimize to system tray", variable=self.tray_var,
                         command=lambda: set_setting("minimize_to_tray", self.tray_var.get())).pack(anchor="w", pady=(10, 0))
        
        # Notifications
        if NOTIFICATIONS_AVAILABLE:
            notif_section = ctk.CTkFrame(scroll, fg_color=COLORS["bg_card"], corner_radius=10)
            notif_section.pack(fill="x", pady=(0, 15))
            
            notif_content = ctk.CTkFrame(notif_section, fg_color="transparent")
            notif_content.pack(fill="x", padx=25, pady=20)
            
            ctk.CTkLabel(notif_content, text="🔔 Notifications", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w")
            
            self.notif_var = ctk.BooleanVar(value=get_setting("show_notifications", True))
            ctk.CTkSwitch(notif_content, text="Show toast notifications", variable=self.notif_var,
                         command=lambda: set_setting("show_notifications", self.notif_var.get())).pack(anchor="w", pady=(10, 0))
        
        # Startup & Auto-Apply
        startup_section = ctk.CTkFrame(scroll, fg_color=COLORS["bg_card"], corner_radius=10)
        startup_section.pack(fill="x", pady=(0, 15))
        
        startup_content = ctk.CTkFrame(startup_section, fg_color="transparent")
        startup_content.pack(fill="x", padx=25, pady=20)
        
        ctk.CTkLabel(startup_content, text="🚀 Startup & Automation", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w")
        
        self.startup_var = ctk.BooleanVar(value=is_startup_enabled())
        ctk.CTkSwitch(startup_content, text="Launch on Windows startup", variable=self.startup_var,
                     command=self._toggle_startup).pack(anchor="w", pady=(10, 0))
        
        self.auto_apply_var = ctk.BooleanVar(value=get_setting("auto_apply_on_launch", False))
        ctk.CTkSwitch(startup_content, text="Auto-apply preset when game launches", variable=self.auto_apply_var,
                     command=lambda: set_setting("auto_apply_on_launch", self.auto_apply_var.get())).pack(anchor="w", pady=(8, 0))
        
        self.warn_running_var = ctk.BooleanVar(value=get_setting("warn_game_running", True))
        ctk.CTkSwitch(startup_content, text="Warn before applying if game is running", variable=self.warn_running_var,
                     command=lambda: set_setting("warn_game_running", self.warn_running_var.get())).pack(anchor="w", pady=(8, 0))
        
        # Hotkeys
        hotkey_section = ctk.CTkFrame(scroll, fg_color=COLORS["bg_card"], corner_radius=10)
        hotkey_section.pack(fill="x", pady=(0, 15))
        
        hotkey_content = ctk.CTkFrame(hotkey_section, fg_color="transparent")
        hotkey_content.pack(fill="x", padx=25, pady=20)
        
        ctk.CTkLabel(hotkey_content, text="⌨️ Global Hotkeys", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(hotkey_content, text="Switch presets with keyboard shortcuts", font=ctk.CTkFont(size=12), 
                    text_color=COLORS["text_muted"]).pack(anchor="w", pady=(5, 12))
        GradientButton(hotkey_content, text="Configure Hotkeys", style="secondary", width=160, height=36,
                      command=self._show_hotkey_dialog).pack(anchor="w")
        
        # Updates
        update_section = ctk.CTkFrame(scroll, fg_color=COLORS["bg_card"], corner_radius=10)
        update_section.pack(fill="x", pady=(0, 15))
        
        update_content = ctk.CTkFrame(update_section, fg_color="transparent")
        update_content.pack(fill="x", padx=25, pady=20)
        
        ctk.CTkLabel(update_content, text="🔄 Updates", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(update_content, text=f"Current version: {__version__}", font=ctk.CTkFont(size=13), text_color=COLORS["text_secondary"]).pack(anchor="w", pady=(8, 12))
        GradientButton(update_content, text="Check for Updates", style="secondary", width=160, height=36, command=self.app._check_updates).pack(anchor="w")
        
        # Links
        links_section = ctk.CTkFrame(scroll, fg_color=COLORS["bg_card"], corner_radius=10)
        links_section.pack(fill="x", pady=(0, 15))
        
        links_content = ctk.CTkFrame(links_section, fg_color="transparent")
        links_content.pack(fill="x", padx=25, pady=20)
        
        ctk.CTkLabel(links_content, text="🔗 Links", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", pady=(0, 12))
        GradientButton(links_content, text="GitHub", style="secondary", width=120, height=36,
                      command=lambda: webbrowser.open("https://github.com/BradyM37/Config-Manager")).pack(anchor="w")
    
    def _show_hotkey_dialog(self):
        HotkeyDialog(self.app, on_save=self.app._setup_hotkeys)
    
    def _set_accent(self, color_name: str):
        global COLORS
        set_setting("accent_color", color_name)
        COLORS = get_colors(color_name)
        
        # Would need to rebuild UI for full effect - show message
        self.app.sidebar.set_status("Restart to apply", COLORS["accent_warning"])
    
    def _toggle_startup(self):
        enabled = self.startup_var.get()
        if set_startup_enabled(enabled):
            self.app.sidebar.set_status("Startup " + ("enabled" if enabled else "disabled"), COLORS["accent_success"])
        else:
            self.startup_var.set(not enabled)
            self.app.sidebar.set_status("Failed to update", COLORS["accent_danger"])
    
    def refresh(self):
        if self.app.deadlock_path:
            self.path_label.configure(text=str(self.app.deadlock_path))


# ============================================================================
# MAIN APPLICATION
# ============================================================================

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Load settings first
        settings = load_settings()
        global COLORS
        COLORS = get_colors(settings.get("accent_color", "purple"))
        
        self.title(APP_NAME)
        self.geometry("1100x750")
        self.minsize(950, 650)
        self.configure(fg_color=COLORS["bg_dark"])
        
        self.deadlock_path: Optional[Path] = None
        self.selected_preset: Optional[str] = None
        self.tabs = {}
        self._minimized_to_tray = False
        
        # Handle close/minimize
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<Unmap>", self._on_minimize)
        
        self._build_ui()
        self._init_tray()
        self.after(100, self._detect_deadlock)
        
        # Check for --minimized arg
        if "--minimized" in sys.argv:
            self.after(500, self._minimize_to_tray)
    
    def _build_ui(self):
        self.sidebar = Sidebar(self, self._navigate)
        self.sidebar.pack(side="left", fill="y")
        
        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.pack(side="right", fill="both", expand=True, padx=25, pady=25)
        
        self.dashboard = DashboardTab(self.content, self)
        self.presets_tab = PresetsTab(self.content, self)
        self.community_tab = CommunityTab(self.content, self)
        self.advanced_tab = AdvancedTab(self.content, self)
        self.backups_tab = BackupsTab(self.content, self)
        self.settings_tab = SettingsTab(self.content, self)
        
        self.tabs = {
            "dashboard": self.dashboard,
            "presets": self.presets_tab,
            "community": self.community_tab,
            "advanced": self.advanced_tab,
            "backups": self.backups_tab,
            "settings": self.settings_tab,
        }
        
        self._navigate("dashboard")
    
    def _init_tray(self):
        """Initialize system tray"""
        if TRAY_AVAILABLE and get_setting("minimize_to_tray", True):
            icon_path = Path(__file__).parent.parent.parent / "assets" / "icon.ico"
            init_tray(
                on_show=self._show_from_tray,
                on_quit=self._quit,
                on_preset=self._tray_apply_preset,
                icon_path=icon_path if icon_path.exists() else None
            )
    
    def _on_close(self):
        """Handle window close"""
        if TRAY_AVAILABLE and get_setting("minimize_to_tray", True):
            self._minimize_to_tray()
        else:
            self._quit()
    
    def _on_minimize(self, event=None):
        """Handle window minimize"""
        if TRAY_AVAILABLE and get_setting("minimize_to_tray", True) and self.state() == "iconic":
            self.after(100, self._minimize_to_tray)
    
    def _minimize_to_tray(self):
        """Minimize to system tray"""
        self._minimized_to_tray = True
        self.withdraw()
    
    def _show_from_tray(self):
        """Show window from tray"""
        self._minimized_to_tray = False
        self.deiconify()
        self.lift()
        self.focus_force()
    
    def _tray_apply_preset(self, preset_name: str):
        """Apply preset from tray menu"""
        if self.deadlock_path:
            self._apply_preset(preset_name)
    
    def _quit(self):
        """Actually quit the app"""
        stop_tray()
        self.destroy()
    
    def _navigate(self, tab_id):
        for tab in self.tabs.values():
            tab.pack_forget()
        
        if tab_id in self.tabs:
            self.tabs[tab_id].pack(fill="both", expand=True)
            self.sidebar.set_active(tab_id)
            if hasattr(self.tabs[tab_id], 'refresh'):
                self.tabs[tab_id].refresh()
    
    def _detect_deadlock(self):
        self.sidebar.set_status("Searching...", COLORS["text_muted"])
        
        def detect():
            path = find_deadlock()
            self.after(0, lambda: self._on_detection_complete(path))
        
        threading.Thread(target=detect, daemon=True).start()
    
    def _on_detection_complete(self, path: Optional[Path]):
        self.deadlock_path = path
        if path:
            self.sidebar.set_status("Ready", COLORS["accent_success"])
            ensure_vanilla_backup(path)
            self.settings_tab.refresh()
            self.dashboard.refresh()
        else:
            self.sidebar.set_status("Game not found", COLORS["accent_warning"])
    
    def _browse_path(self):
        path = ctk.filedialog.askdirectory(title="Select Deadlock Installation")
        if path:
            path = Path(path)
            if validate_deadlock_path(path):
                self.deadlock_path = path
                self.sidebar.set_status("Ready", COLORS["accent_success"])
                ensure_vanilla_backup(path)
                self.settings_tab.refresh()
                self.dashboard.refresh()
            else:
                self.sidebar.set_status("Invalid path", COLORS["accent_danger"])
    
    def _apply_preset(self, preset_name, force: bool = False):
        if not self.deadlock_path:
            self.sidebar.set_status("No game found", COLORS["accent_warning"])
            return
        
        # Check if game is running (unless forced)
        if not force and get_setting("warn_game_running", True) and is_deadlock_running():
            GameRunningWarningDialog(
                self,
                on_continue=lambda: self._apply_preset(preset_name, force=True)
            )
            return
        
        self.sidebar.set_status("Applying...", COLORS["accent_warning"])
        
        # Check built-in presets first
        presets = list_presets()
        preset = next((p for p in presets if p["name"] == preset_name), None)
        
        # Check custom presets if not found
        if not preset:
            custom = list_custom_presets()
            preset = next((p for p in custom if p["name"] == preset_name), None)
        
        if preset and apply_preset(self.deadlock_path, preset["path"]):
            self.sidebar.set_status(f"Applied {preset_name}", COLORS["accent_success"])
            set_setting("last_preset", preset_name)
            
            # Show notification
            if get_setting("show_notifications", True):
                notify_preset_applied(preset_name)
            
            self.dashboard.refresh()
        else:
            self.sidebar.set_status("Failed", COLORS["accent_danger"])
    
    def _check_updates(self):
        self.sidebar.set_status("Checking...", COLORS["accent_warning"])
        
        def check():
            update = check_for_updates()
            self.after(0, lambda: self._on_update_check(update))
        
        threading.Thread(target=check, daemon=True).start()
    
    def _on_update_check(self, update):
        if update:
            self.sidebar.set_status(f"Downloading v{update['version']}...", COLORS["accent_warning"])
            
            # Download and apply update automatically
            def do_update():
                download_url = update.get("download_url")
                if not download_url:
                    self.after(0, lambda: self.sidebar.set_status("No download available", COLORS["accent_danger"]))
                    return
                
                # Download the update
                update_path = download_update(download_url)
                
                if update_path:
                    self.after(0, lambda: self.sidebar.set_status("Installing...", COLORS["accent_warning"]))
                    
                    # Apply update (will restart app)
                    if apply_update(update_path):
                        self.after(0, self._quit)
                    else:
                        # Fall back to opening browser if auto-update fails
                        self.after(0, lambda: self.sidebar.set_status("Manual update required", COLORS["accent_warning"]))
                        if update.get("html_url"):
                            webbrowser.open(update["html_url"])
                else:
                    self.after(0, lambda: self.sidebar.set_status("Download failed", COLORS["accent_danger"]))
            
            threading.Thread(target=do_update, daemon=True).start()
        else:
            self.sidebar.set_status("Up to date", COLORS["accent_success"])
    
    def _setup_hotkeys(self):
        """Setup global hotkeys for preset switching"""
        try:
            hotkey_presets = get_hotkey_presets()
            
            for hotkey, preset_name in hotkey_presets.items():
                register_hotkey(hotkey, lambda pn=preset_name: self.after(0, lambda: self._apply_preset(pn, force=True)))
            
            if hotkey_presets:
                start_hotkey_listener()
                self.sidebar.set_status("Hotkeys active", COLORS["accent_success"])
        except Exception as e:
            print(f"Failed to setup hotkeys: {e}")
    
    def _setup_game_watcher(self):
        """Setup game launch detection for auto-apply"""
        if not get_setting("auto_apply_on_launch", False):
            return
        
        last_preset = get_setting("last_preset")
        if not last_preset:
            return
        
        def on_game_launch():
            # Auto-apply last preset when game launches
            if self.deadlock_path and last_preset:
                self.after(0, lambda: self._apply_preset(last_preset, force=True))
        
        self.game_watcher = GameLaunchWatcher(on_launch=on_game_launch)
        self.game_watcher.start()


def main():
    app = App()
    
    # Setup hotkeys and game watcher after init
    app.after(1000, app._setup_hotkeys)
    app.after(1500, app._setup_game_watcher)
    
    app.mainloop()


if __name__ == "__main__":
    main()
