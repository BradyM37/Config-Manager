"""
Main Application Window
OptiLock Config Manager UI
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


# Theme configuration
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class StatusBar(ctk.CTkFrame):
    """Bottom status bar"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, height=30, **kwargs)
        
        self.version_label = ctk.CTkLabel(
            self,
            text=f"v{__version__}",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.version_label.pack(side="left", padx=10)
        
        self.status_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=11)
        )
        self.status_label.pack(side="left", padx=10)
        
        self.github_btn = ctk.CTkButton(
            self,
            text="GitHub",
            width=60,
            height=24,
            font=ctk.CTkFont(size=11),
            command=lambda: webbrowser.open("https://github.com/optilock/config-manager")
        )
        self.github_btn.pack(side="right", padx=10)
    
    def set_status(self, text: str, color: str = "white"):
        self.status_label.configure(text=text, text_color=color)


class DetectionFrame(ctk.CTkFrame):
    """Deadlock detection and status display"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        # Title
        self.title_label = ctk.CTkLabel(
            self,
            text="🎮 DEADLOCK STATUS",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.title_label.pack(pady=(10, 5))
        
        # Path display
        self.path_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.path_frame.pack(fill="x", padx=10, pady=5)
        
        self.path_label = ctk.CTkLabel(
            self.path_frame,
            text="Searching...",
            font=ctk.CTkFont(size=12),
            wraplength=400
        )
        self.path_label.pack(side="left", expand=True)
        
        self.browse_btn = ctk.CTkButton(
            self.path_frame,
            text="📁",
            width=30,
            command=self.browse_path
        )
        self.browse_btn.pack(side="right", padx=5)
        
        # Config status
        self.config_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.config_label.pack(pady=(0, 10))
        
        # Callback for path changes
        self.on_path_change = None
        self.deadlock_path = None
    
    def set_path(self, path: Optional[Path]):
        self.deadlock_path = path
        
        if path:
            self.path_label.configure(
                text=f"📁 {path}",
                text_color="white"
            )
            
            # Get config info
            info = get_current_config_info(path)
            if info["installed"]:
                version_str = f" v{info['version']}" if info['version'] else ""
                self.config_label.configure(
                    text=f"✅ {info['name']}{version_str} installed",
                    text_color="#4ade80"
                )
            else:
                self.config_label.configure(
                    text="⚠️ Vanilla config (no optimization)",
                    text_color="#fbbf24"
                )
        else:
            self.path_label.configure(
                text="❌ Deadlock not found",
                text_color="#f87171"
            )
            self.config_label.configure(text="")
        
        if self.on_path_change:
            self.on_path_change(path)
    
    def browse_path(self):
        path = ctk.filedialog.askdirectory(title="Select Deadlock Installation Folder")
        if path:
            path = Path(path)
            if validate_deadlock_path(path):
                self.set_path(path)
            else:
                ctk.CTkMessagebox = None  # Using simple approach
                self.config_label.configure(
                    text="❌ Invalid Deadlock path",
                    text_color="#f87171"
                )


class ActionButtons(ctk.CTkFrame):
    """Apply, Backup, Restore buttons"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        
        self.apply_btn = ctk.CTkButton(
            self,
            text="💾 Apply Config",
            width=140,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#22c55e",
            hover_color="#16a34a"
        )
        self.apply_btn.pack(side="left", padx=5)
        
        self.backup_btn = ctk.CTkButton(
            self,
            text="📂 Backup",
            width=100,
            height=40,
            font=ctk.CTkFont(size=13)
        )
        self.backup_btn.pack(side="left", padx=5)
        
        self.restore_btn = ctk.CTkButton(
            self,
            text="↩️ Restore",
            width=100,
            height=40,
            font=ctk.CTkFont(size=13)
        )
        self.restore_btn.pack(side="left", padx=5)
        
        self.update_btn = ctk.CTkButton(
            self,
            text="🔄 Check Update",
            width=120,
            height=40,
            font=ctk.CTkFont(size=13),
            fg_color="#6366f1",
            hover_color="#4f46e5"
        )
        self.update_btn.pack(side="left", padx=5)


class App(ctk.CTk):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        
        # Window setup
        self.title("OptiLock Config Manager")
        self.geometry("700x750")
        self.minsize(600, 600)
        
        # State
        self.deadlock_path: Optional[Path] = None
        self.selected_preset: Optional[str] = None
        
        # Build UI
        self._build_ui()
        
        # Auto-detect Deadlock
        self.after(100, self._detect_deadlock)
    
    def _build_ui(self):
        # Main container
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Title
        title = ctk.CTkLabel(
            self.main_frame,
            text="⚙️ OPTILOCK CONFIG MANAGER",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.pack(pady=(10, 5))
        
        # Detection frame
        self.detection_frame = DetectionFrame(self.main_frame)
        self.detection_frame.pack(fill="x", padx=10, pady=10)
        self.detection_frame.on_path_change = self._on_path_change
        
        # Presets section
        presets_label = ctk.CTkLabel(
            self.main_frame,
            text="📦 CONFIG PRESETS",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        presets_label.pack(pady=(10, 5))
        
        self.presets_frame = PresetCardsFrame(
            self.main_frame,
            on_select=self._on_preset_select
        )
        self.presets_frame.pack(fill="x", padx=10, pady=5)
        
        # ConVar tweaks section
        convars_label = ctk.CTkLabel(
            self.main_frame,
            text="🎛️ CONVAR TWEAKS",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        convars_label.pack(pady=(15, 5))
        
        self.convar_panel = ConVarPanel(self.main_frame)
        self.convar_panel.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Action buttons
        self.actions = ActionButtons(self.main_frame)
        self.actions.pack(pady=15)
        
        # Connect button actions
        self.actions.apply_btn.configure(command=self._apply_config)
        self.actions.backup_btn.configure(command=self._create_backup)
        self.actions.restore_btn.configure(command=self._show_restore_dialog)
        self.actions.update_btn.configure(command=self._check_updates)
        
        # Status bar
        self.status_bar = StatusBar(self)
        self.status_bar.pack(fill="x", side="bottom")
    
    def _detect_deadlock(self):
        """Auto-detect Deadlock installation"""
        self.status_bar.set_status("Searching for Deadlock...", "gray")
        
        def detect():
            path = find_deadlock()
            self.after(0, lambda: self._on_detection_complete(path))
        
        threading.Thread(target=detect, daemon=True).start()
    
    def _on_detection_complete(self, path: Optional[Path]):
        self.detection_frame.set_path(path)
        
        if path:
            self.status_bar.set_status("Ready", "#4ade80")
            # Ensure vanilla backup exists
            ensure_vanilla_backup(path)
        else:
            self.status_bar.set_status("Please locate Deadlock manually", "#fbbf24")
    
    def _on_path_change(self, path: Optional[Path]):
        self.deadlock_path = path
        
        # Enable/disable controls based on path
        state = "normal" if path else "disabled"
        self.actions.apply_btn.configure(state=state)
        self.actions.backup_btn.configure(state=state)
        self.actions.restore_btn.configure(state=state)
    
    def _on_preset_select(self, preset_name: str):
        self.selected_preset = preset_name
        self.status_bar.set_status(f"Selected: {preset_name}", "white")
    
    def _apply_config(self):
        if not self.deadlock_path:
            return
        
        if self.selected_preset:
            # Apply preset
            presets = list_presets()
            preset = next((p for p in presets if p["name"] == self.selected_preset), None)
            
            if preset:
                self.status_bar.set_status("Applying preset...", "#fbbf24")
                
                if apply_preset(self.deadlock_path, preset["path"]):
                    self.status_bar.set_status(f"✅ Applied {preset['display']}", "#4ade80")
                    # Refresh detection
                    self.detection_frame.set_path(self.deadlock_path)
                else:
                    self.status_bar.set_status("❌ Failed to apply preset", "#f87171")
        else:
            self.status_bar.set_status("Please select a preset first", "#fbbf24")
    
    def _create_backup(self):
        if not self.deadlock_path:
            return
        
        self.status_bar.set_status("Creating backup...", "#fbbf24")
        
        backup_path = create_backup(self.deadlock_path, label="manual")
        
        if backup_path:
            self.status_bar.set_status(f"✅ Backup created", "#4ade80")
        else:
            self.status_bar.set_status("❌ Backup failed", "#f87171")
    
    def _show_restore_dialog(self):
        if not self.deadlock_path:
            return
        
        backups = list_backups()
        
        if not backups:
            self.status_bar.set_status("No backups available", "#fbbf24")
            return
        
        # Create restore dialog
        dialog = ctk.CTkToplevel(self)
        dialog.title("Restore Backup")
        dialog.geometry("400x300")
        dialog.transient(self)
        dialog.grab_set()
        
        label = ctk.CTkLabel(dialog, text="Select backup to restore:", font=ctk.CTkFont(size=14))
        label.pack(pady=10)
        
        # Backup list
        listbox_frame = ctk.CTkScrollableFrame(dialog, height=180)
        listbox_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        selected_backup = ctk.StringVar()
        
        for backup in backups[:20]:  # Limit to 20 most recent
            btn = ctk.CTkRadioButton(
                listbox_frame,
                text=backup["display"],
                variable=selected_backup,
                value=str(backup["path"])
            )
            btn.pack(anchor="w", pady=2)
        
        def do_restore():
            path = selected_backup.get()
            if path:
                if restore_backup(self.deadlock_path, Path(path)):
                    self.status_bar.set_status("✅ Backup restored", "#4ade80")
                    self.detection_frame.set_path(self.deadlock_path)
                else:
                    self.status_bar.set_status("❌ Restore failed", "#f87171")
                dialog.destroy()
        
        restore_btn = ctk.CTkButton(dialog, text="Restore", command=do_restore)
        restore_btn.pack(pady=10)
    
    def _check_updates(self):
        self.status_bar.set_status("Checking for updates...", "#fbbf24")
        
        def check():
            update = check_for_updates()
            self.after(0, lambda: self._on_update_check(update))
        
        threading.Thread(target=check, daemon=True).start()
    
    def _on_update_check(self, update: Optional[dict]):
        if update:
            self.status_bar.set_status(f"Update available: v{update['version']}", "#22c55e")
            
            # Ask to open download page
            if update.get("html_url"):
                webbrowser.open(update["html_url"])
        else:
            self.status_bar.set_status("✅ You're up to date!", "#4ade80")


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
