"""
Main Application Window
OptiLock Config Manager UI - Premium Edition with Tabs
"""

import customtkinter as ctk
from pathlib import Path
from typing import Optional
import threading
import webbrowser
import time

from src.core.detector import find_deadlock, get_current_config_info, validate_deadlock_path
from src.core.backup import create_backup, list_backups, restore_backup, ensure_vanilla_backup
from src.core.config import list_presets, apply_preset, get_presets_dir
from src.core.updater import check_for_updates
from src import __version__


# ============================================================================
# THEME CONFIGURATION
# ============================================================================

COLORS = {
    "bg_dark": "#0a0a0f",
    "bg_card": "#12121a", 
    "bg_card_hover": "#1a1a25",
    "bg_elevated": "#1e1e2e",
    "bg_sidebar": "#0d0d14",
    "border": "#2a2a3a",
    "border_glow": "#6366f1",
    "accent_primary": "#8b5cf6",
    "accent_secondary": "#06b6d4",
    "accent_success": "#10b981",
    "accent_warning": "#f59e0b",
    "accent_danger": "#ef4444",
    "text_primary": "#ffffff",
    "text_secondary": "#a1a1aa",
    "text_muted": "#71717a",
}

ctk.set_appearance_mode("dark")


# ============================================================================
# CUSTOM COMPONENTS
# ============================================================================

class GradientButton(ctk.CTkButton):
    """Styled button"""
    
    def __init__(self, parent, style="primary", **kwargs):
        styles = {
            "primary": {"fg_color": COLORS["accent_primary"], "hover_color": "#7c3aed"},
            "success": {"fg_color": COLORS["accent_success"], "hover_color": "#059669"},
            "secondary": {"fg_color": COLORS["bg_elevated"], "hover_color": COLORS["bg_card_hover"], "border_width": 1, "border_color": COLORS["border"]},
            "danger": {"fg_color": COLORS["accent_danger"], "hover_color": "#dc2626"},
        }
        style_config = styles.get(style, styles["primary"])
        if "font" not in kwargs:
            kwargs["font"] = ctk.CTkFont(family="Segoe UI", size=13, weight="bold")
        super().__init__(parent, corner_radius=8, **style_config, **kwargs)


class QuickPresetCard(ctk.CTkFrame):
    """Compact preset card for dashboard"""
    
    ICONS = {"potato": "🥔", "balanced": "⚖️", "quality": "💎", "competitive": "🎯"}
    COLORS_MAP = {"potato": "#f59e0b", "balanced": "#8b5cf6", "quality": "#06b6d4", "competitive": "#ef4444"}
    
    def __init__(self, parent, name: str, display: str, on_apply, **kwargs):
        super().__init__(parent, fg_color=COLORS["bg_card"], corner_radius=10, **kwargs)
        
        self.name = name
        self.on_apply = on_apply
        self.accent = self.COLORS_MAP.get(name.lower(), COLORS["accent_primary"])
        
        self.configure(border_width=2, border_color=COLORS["border"])
        self.bind("<Enter>", lambda e: self.configure(border_color=self.accent))
        self.bind("<Leave>", lambda e: self.configure(border_color=COLORS["border"]))
        self.bind("<Button-1>", lambda e: on_apply(name))
        
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=15, pady=12)
        
        icon = ctk.CTkLabel(content, text=self.ICONS.get(name.lower(), "📦"), font=ctk.CTkFont(size=28))
        icon.pack(side="left")
        icon.bind("<Button-1>", lambda e: on_apply(name))
        
        text_frame = ctk.CTkFrame(content, fg_color="transparent")
        text_frame.pack(side="left", padx=12, fill="y")
        
        title = ctk.CTkLabel(text_frame, text=display.replace(self.ICONS.get(name.lower(), ""), "").strip(), 
                            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"))
        title.pack(anchor="w")
        title.bind("<Button-1>", lambda e: on_apply(name))
        
        ctk.CTkLabel(text_frame, text="Click to apply", font=ctk.CTkFont(size=10), 
                    text_color=COLORS["text_muted"]).pack(anchor="w")


class StatCard(ctk.CTkFrame):
    """Stats display card"""
    
    def __init__(self, parent, title: str, value: str, icon: str, color: str, **kwargs):
        super().__init__(parent, fg_color=COLORS["bg_card"], corner_radius=10, **kwargs)
        
        self.configure(border_width=1, border_color=COLORS["border"])
        
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=15, pady=12)
        
        header = ctk.CTkFrame(content, fg_color="transparent")
        header.pack(fill="x")
        
        ctk.CTkLabel(header, text=icon, font=ctk.CTkFont(size=20)).pack(side="left")
        ctk.CTkLabel(header, text=title, font=ctk.CTkFont(size=11), 
                    text_color=COLORS["text_muted"]).pack(side="left", padx=8)
        
        self.value_label = ctk.CTkLabel(content, text=value, font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
                                        text_color=color)
        self.value_label.pack(anchor="w", pady=(8, 0))
    
    def set_value(self, value: str):
        self.value_label.configure(text=value)


# ============================================================================
# SIDEBAR
# ============================================================================

class Sidebar(ctk.CTkFrame):
    """Navigation sidebar"""
    
    def __init__(self, parent, on_navigate, **kwargs):
        super().__init__(parent, fg_color=COLORS["bg_sidebar"], width=200, **kwargs)
        self.pack_propagate(False)
        
        self.on_navigate = on_navigate
        self.buttons = {}
        self.active_tab = None
        
        # Logo
        logo_frame = ctk.CTkFrame(self, fg_color="transparent")
        logo_frame.pack(fill="x", pady=20, padx=15)
        
        ctk.CTkLabel(logo_frame, text="⚡", font=ctk.CTkFont(size=32)).pack(side="left")
        
        title_frame = ctk.CTkFrame(logo_frame, fg_color="transparent")
        title_frame.pack(side="left", padx=10)
        ctk.CTkLabel(title_frame, text="OPTILOCK", font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(title_frame, text="Config Manager", font=ctk.CTkFont(size=10), 
                    text_color=COLORS["text_muted"]).pack(anchor="w")
        
        # Divider
        ctk.CTkFrame(self, height=1, fg_color=COLORS["border"]).pack(fill="x", padx=15)
        
        # Nav items
        nav_items = [
            ("dashboard", "🏠", "Dashboard"),
            ("presets", "📦", "Presets"),
            ("advanced", "🎛️", "Advanced"),
            ("backups", "💾", "Backups"),
            ("settings", "⚙️", "Settings"),
        ]
        
        nav_frame = ctk.CTkFrame(self, fg_color="transparent")
        nav_frame.pack(fill="x", pady=20)
        
        for tab_id, icon, label in nav_items:
            btn = ctk.CTkButton(
                nav_frame,
                text=f"  {icon}  {label}",
                font=ctk.CTkFont(family="Segoe UI", size=13),
                fg_color="transparent",
                hover_color=COLORS["bg_card"],
                anchor="w",
                height=40,
                corner_radius=8,
                command=lambda t=tab_id: self._on_click(t)
            )
            btn.pack(fill="x", padx=10, pady=2)
            self.buttons[tab_id] = btn
        
        # Bottom section - version
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(side="bottom", fill="x", pady=15, padx=15)
        
        ctk.CTkLabel(bottom, text=f"v{__version__}", font=ctk.CTkFont(size=10), 
                    text_color=COLORS["text_muted"]).pack(anchor="w")
        
        # Status
        self.status_label = ctk.CTkLabel(bottom, text="Ready", font=ctk.CTkFont(size=10),
                                         text_color=COLORS["accent_success"])
        self.status_label.pack(anchor="w")
    
    def _on_click(self, tab_id):
        self.set_active(tab_id)
        self.on_navigate(tab_id)
    
    def set_active(self, tab_id):
        for tid, btn in self.buttons.items():
            if tid == tab_id:
                btn.configure(fg_color=COLORS["accent_primary"])
            else:
                btn.configure(fg_color="transparent")
        self.active_tab = tab_id
    
    def set_status(self, text: str, color: str = None):
        self.status_label.configure(text=text, text_color=color or COLORS["accent_success"])


# ============================================================================
# DASHBOARD TAB
# ============================================================================

class DashboardTab(ctk.CTkFrame):
    """Main dashboard with quick actions"""
    
    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.app = app
        self._build_ui()
    
    def _build_ui(self):
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(header, text="Dashboard", font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold")).pack(side="left")
        
        # Status cards row
        stats_frame = ctk.CTkFrame(self, fg_color="transparent")
        stats_frame.pack(fill="x", pady=(0, 20))
        
        self.game_stat = StatCard(stats_frame, "Game Status", "Detected", "🎮", COLORS["accent_success"], width=180, height=90)
        self.game_stat.pack(side="left", padx=(0, 10))
        
        self.config_stat = StatCard(stats_frame, "Active Config", "OptiLock v1", "⚡", COLORS["accent_primary"], width=180, height=90)
        self.config_stat.pack(side="left", padx=(0, 10))
        
        self.backups_stat = StatCard(stats_frame, "Backups", "0", "💾", COLORS["accent_secondary"], width=180, height=90)
        self.backups_stat.pack(side="left", padx=(0, 10))
        
        # Quick presets section
        ctk.CTkLabel(self, text="⚡ Quick Apply", font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
                    text_color=COLORS["text_secondary"]).pack(anchor="w", pady=(10, 10))
        
        presets_grid = ctk.CTkFrame(self, fg_color="transparent")
        presets_grid.pack(fill="x")
        
        presets = [
            ("potato", "🥔 Potato"),
            ("balanced", "⚖️ Balanced"),
            ("quality", "💎 Quality"),
            ("competitive", "🎯 Competitive"),
        ]
        
        for i, (name, display) in enumerate(presets):
            card = QuickPresetCard(presets_grid, name, display, self._quick_apply, width=170, height=70)
            card.grid(row=0, column=i, padx=(0, 10), sticky="nsew")
        
        # Recent activity section
        ctk.CTkLabel(self, text="📋 Recent Activity", font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
                    text_color=COLORS["text_secondary"]).pack(anchor="w", pady=(30, 10))
        
        self.activity_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=10, height=150)
        self.activity_frame.pack(fill="x")
        self.activity_frame.pack_propagate(False)
        
        self.activity_list = ctk.CTkFrame(self.activity_frame, fg_color="transparent")
        self.activity_list.pack(fill="both", expand=True, padx=15, pady=10)
        
        ctk.CTkLabel(self.activity_list, text="No recent activity", font=ctk.CTkFont(size=12),
                    text_color=COLORS["text_muted"]).pack(pady=20)
    
    def _quick_apply(self, preset_name):
        if self.app.deadlock_path:
            self.app._apply_preset(preset_name)
    
    def refresh(self):
        """Refresh dashboard stats"""
        if self.app.deadlock_path:
            self.game_stat.set_value("Detected")
            info = get_current_config_info(self.app.deadlock_path)
            if info.get("installed"):
                self.config_stat.set_value(info.get("name", "Custom"))
            else:
                self.config_stat.set_value("Vanilla")
        else:
            self.game_stat.set_value("Not Found")
            self.config_stat.set_value("N/A")
        
        backups = list_backups()
        self.backups_stat.set_value(str(len(backups)))


# ============================================================================
# PRESETS TAB
# ============================================================================

class PresetCard(ctk.CTkFrame):
    """Full preset card with details"""
    
    ICONS = {"potato": "🥔", "balanced": "⚖️", "quality": "💎", "competitive": "🎯"}
    COLORS_MAP = {"potato": "#f59e0b", "balanced": "#8b5cf6", "quality": "#06b6d4", "competitive": "#ef4444"}
    
    def __init__(self, parent, preset: dict, on_select, selected=False, **kwargs):
        super().__init__(parent, fg_color=COLORS["bg_card"], corner_radius=12, **kwargs)
        
        self.preset = preset
        self.name = preset.get("name", "")
        self.on_select = on_select
        self.selected = selected
        self.accent = self.COLORS_MAP.get(self.name.lower(), COLORS["accent_primary"])
        
        self.configure(border_width=2, border_color=self.accent if selected else COLORS["border"])
        
        self.bind("<Button-1>", self._on_click)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        
        # Content
        icon = ctk.CTkLabel(self, text=self.ICONS.get(self.name.lower(), "📦"), font=ctk.CTkFont(size=40))
        icon.pack(pady=(20, 10))
        icon.bind("<Button-1>", self._on_click)
        
        self.title_label = ctk.CTkLabel(self, text=preset.get("display", self.name).replace(self.ICONS.get(self.name.lower(), ""), "").strip(),
                                        font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
                                        text_color=self.accent if selected else COLORS["text_primary"])
        self.title_label.pack()
        self.title_label.bind("<Button-1>", self._on_click)
        
        ctk.CTkLabel(self, text=preset.get("description", ""), font=ctk.CTkFont(size=11),
                    text_color=COLORS["text_muted"], wraplength=140).pack(pady=(5, 20), padx=10)
    
    def _on_click(self, e=None):
        self.on_select(self.name)
    
    def _on_enter(self, e=None):
        if not self.selected:
            self.configure(border_color=self.accent)
    
    def _on_leave(self, e=None):
        if not self.selected:
            self.configure(border_color=COLORS["border"])
    
    def set_selected(self, selected: bool):
        self.selected = selected
        self.configure(border_color=self.accent if selected else COLORS["border"],
                      border_width=3 if selected else 2)
        self.title_label.configure(text_color=self.accent if selected else COLORS["text_primary"])


class PresetsTab(ctk.CTkFrame):
    """Presets management tab"""
    
    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.app = app
        self.cards = {}
        self.selected = None
        self._build_ui()
    
    def _build_ui(self):
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(header, text="Config Presets", font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold")).pack(side="left")
        
        GradientButton(header, text="Apply Selected", style="success", width=140, height=36,
                      command=self._apply_selected).pack(side="right")
        
        # Presets grid
        grid = ctk.CTkFrame(self, fg_color="transparent")
        grid.pack(fill="x")
        
        presets = [
            {"name": "potato", "display": "🥔 Potato", "description": "Maximum FPS, minimum visuals. For low-end PCs."},
            {"name": "balanced", "display": "⚖️ Balanced", "description": "Best of both worlds. Recommended for most."},
            {"name": "quality", "display": "💎 Quality", "description": "Enhanced visuals while staying optimized."},
            {"name": "competitive", "display": "🎯 Competitive", "description": "Pro visibility settings for ranked play."},
        ]
        
        try:
            actual = list_presets()
            if actual:
                presets = actual
        except:
            pass
        
        for i, preset in enumerate(presets):
            card = PresetCard(grid, preset, self._on_select, width=180, height=160)
            card.grid(row=0, column=i, padx=10, pady=10, sticky="nsew")
            self.cards[preset["name"]] = card
        
        for i in range(len(presets)):
            grid.grid_columnconfigure(i, weight=1)
        
        # Info section
        info_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=10)
        info_frame.pack(fill="x", pady=20)
        
        info_content = ctk.CTkFrame(info_frame, fg_color="transparent")
        info_content.pack(fill="x", padx=20, pady=15)
        
        ctk.CTkLabel(info_content, text="ℹ️ About Presets", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(info_content, text="Presets modify your gameinfo.gi file to optimize Deadlock's performance and visuals. "
                    "A backup is automatically created before any changes.",
                    font=ctk.CTkFont(size=12), text_color=COLORS["text_secondary"], wraplength=600).pack(anchor="w", pady=(5, 0))
    
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


# ============================================================================
# ADVANCED TAB (ConVars)
# ============================================================================

class AdvancedTab(ctk.CTkScrollableFrame):
    """Advanced ConVar tweaks"""
    
    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.app = app
        self._build_ui()
    
    def _build_ui(self):
        # Header
        ctk.CTkLabel(self, text="Advanced Tweaks", font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold")).pack(anchor="w", pady=(0, 5))
        ctk.CTkLabel(self, text="Fine-tune individual settings for maximum control", 
                    font=ctk.CTkFont(size=12), text_color=COLORS["text_muted"]).pack(anchor="w", pady=(0, 20))
        
        # Import and use existing ConVarPanel
        from src.ui.convar_panel import ConVarPanel
        
        panel = ConVarPanel(self, fg_color=COLORS["bg_card"], corner_radius=12)
        panel.pack(fill="both", expand=True)


# ============================================================================
# BACKUPS TAB
# ============================================================================

class BackupsTab(ctk.CTkFrame):
    """Backup management"""
    
    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.app = app
        self._build_ui()
    
    def _build_ui(self):
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(header, text="Backups", font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold")).pack(side="left")
        
        GradientButton(header, text="Create Backup", style="primary", width=140, height=36,
                      command=self._create_backup).pack(side="right")
        
        # Backups list
        self.list_frame = ctk.CTkScrollableFrame(self, fg_color=COLORS["bg_card"], corner_radius=10, height=400)
        self.list_frame.pack(fill="both", expand=True)
        
        self.refresh()
    
    def refresh(self):
        # Clear existing
        for widget in self.list_frame.winfo_children():
            widget.destroy()
        
        backups = list_backups()
        
        if not backups:
            ctk.CTkLabel(self.list_frame, text="No backups yet", font=ctk.CTkFont(size=14),
                        text_color=COLORS["text_muted"]).pack(pady=30)
            return
        
        for backup in backups[:20]:
            row = ctk.CTkFrame(self.list_frame, fg_color="transparent")
            row.pack(fill="x", padx=10, pady=5)
            
            ctk.CTkLabel(row, text="💾", font=ctk.CTkFont(size=16)).pack(side="left", padx=(0, 10))
            ctk.CTkLabel(row, text=backup["display"], font=ctk.CTkFont(size=12)).pack(side="left")
            
            GradientButton(row, text="Restore", style="secondary", width=80, height=28,
                          command=lambda p=backup["path"]: self._restore(p)).pack(side="right")
    
    def _create_backup(self):
        if self.app.deadlock_path:
            if create_backup(self.app.deadlock_path, label="manual"):
                self.app.sidebar.set_status("Backup created", COLORS["accent_success"])
                self.refresh()
    
    def _restore(self, path):
        if self.app.deadlock_path:
            if restore_backup(self.app.deadlock_path, path):
                self.app.sidebar.set_status("Restored", COLORS["accent_success"])
                self.app.dashboard.refresh()


# ============================================================================
# SETTINGS TAB
# ============================================================================

class SettingsTab(ctk.CTkFrame):
    """App settings"""
    
    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.app = app
        self._build_ui()
    
    def _build_ui(self):
        # Header
        ctk.CTkLabel(self, text="Settings", font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold")).pack(anchor="w", pady=(0, 20))
        
        # Game path section
        path_section = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=10)
        path_section.pack(fill="x", pady=(0, 15))
        
        path_content = ctk.CTkFrame(path_section, fg_color="transparent")
        path_content.pack(fill="x", padx=20, pady=15)
        
        ctk.CTkLabel(path_content, text="🎮 Game Location", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w")
        
        self.path_label = ctk.CTkLabel(path_content, text="Not detected", font=ctk.CTkFont(size=12),
                                       text_color=COLORS["text_secondary"])
        self.path_label.pack(anchor="w", pady=(5, 10))
        
        GradientButton(path_content, text="Browse", style="secondary", width=100, height=32,
                      command=self.app._browse_path).pack(anchor="w")
        
        # Updates section
        update_section = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=10)
        update_section.pack(fill="x", pady=(0, 15))
        
        update_content = ctk.CTkFrame(update_section, fg_color="transparent")
        update_content.pack(fill="x", padx=20, pady=15)
        
        ctk.CTkLabel(update_content, text="🔄 Updates", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(update_content, text=f"Current version: {__version__}", font=ctk.CTkFont(size=12),
                    text_color=COLORS["text_secondary"]).pack(anchor="w", pady=(5, 10))
        
        GradientButton(update_content, text="Check for Updates", style="secondary", width=150, height=32,
                      command=self.app._check_updates).pack(anchor="w")
        
        # Links
        links_section = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=10)
        links_section.pack(fill="x")
        
        links_content = ctk.CTkFrame(links_section, fg_color="transparent")
        links_content.pack(fill="x", padx=20, pady=15)
        
        ctk.CTkLabel(links_content, text="🔗 Links", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", pady=(0, 10))
        
        links_row = ctk.CTkFrame(links_content, fg_color="transparent")
        links_row.pack(anchor="w")
        
        GradientButton(links_row, text="GitHub", style="secondary", width=100, height=32,
                      command=lambda: webbrowser.open("https://github.com/BradyM37/Config-Manager")).pack(side="left", padx=(0, 10))
    
    def refresh(self):
        if self.app.deadlock_path:
            self.path_label.configure(text=str(self.app.deadlock_path))


# ============================================================================
# MAIN APPLICATION
# ============================================================================

class App(ctk.CTk):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        
        self.title("OptiLock Config Manager")
        self.geometry("1000x700")
        self.minsize(900, 600)
        self.configure(fg_color=COLORS["bg_dark"])
        
        # State
        self.deadlock_path: Optional[Path] = None
        self.selected_preset: Optional[str] = None
        self.tabs = {}
        
        self._build_ui()
        self.after(100, self._detect_deadlock)
    
    def _build_ui(self):
        # Sidebar
        self.sidebar = Sidebar(self, self._navigate)
        self.sidebar.pack(side="left", fill="y")
        
        # Main content area
        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.pack(side="right", fill="both", expand=True, padx=20, pady=20)
        
        # Create tabs
        self.dashboard = DashboardTab(self.content, self)
        self.presets_tab = PresetsTab(self.content, self)
        self.advanced_tab = AdvancedTab(self.content, self)
        self.backups_tab = BackupsTab(self.content, self)
        self.settings_tab = SettingsTab(self.content, self)
        
        self.tabs = {
            "dashboard": self.dashboard,
            "presets": self.presets_tab,
            "advanced": self.advanced_tab,
            "backups": self.backups_tab,
            "settings": self.settings_tab,
        }
        
        # Show dashboard by default
        self._navigate("dashboard")
    
    def _navigate(self, tab_id):
        # Hide all tabs
        for tab in self.tabs.values():
            tab.pack_forget()
        
        # Show selected tab
        if tab_id in self.tabs:
            self.tabs[tab_id].pack(fill="both", expand=True)
            self.sidebar.set_active(tab_id)
            
            # Refresh tab if needed
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
    
    def _apply_preset(self, preset_name):
        if not self.deadlock_path:
            self.sidebar.set_status("No game found", COLORS["accent_warning"])
            return
        
        self.sidebar.set_status("Applying...", COLORS["accent_warning"])
        
        presets = list_presets()
        preset = next((p for p in presets if p["name"] == preset_name), None)
        
        if preset and apply_preset(self.deadlock_path, preset["path"]):
            self.sidebar.set_status(f"Applied {preset_name}", COLORS["accent_success"])
            self.dashboard.refresh()
        else:
            self.sidebar.set_status("Failed to apply", COLORS["accent_danger"])
    
    def _check_updates(self):
        self.sidebar.set_status("Checking...", COLORS["accent_warning"])
        
        def check():
            update = check_for_updates()
            self.after(0, lambda: self._on_update_check(update))
        
        threading.Thread(target=check, daemon=True).start()
    
    def _on_update_check(self, update):
        if update:
            self.sidebar.set_status(f"Update: v{update['version']}", COLORS["accent_success"])
            if update.get("html_url"):
                webbrowser.open(update["html_url"])
        else:
            self.sidebar.set_status("Up to date", COLORS["accent_success"])


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
