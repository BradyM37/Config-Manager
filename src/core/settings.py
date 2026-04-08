"""
Settings & State Management
Persistent app settings and user preferences
"""

import json
import winreg
import subprocess
from pathlib import Path
from typing import Optional, Any

from .backup import get_config_dir


# Deadlock Steam App ID
DEADLOCK_APP_ID = "1422450"

# Default accent colors
ACCENT_COLORS = {
    "purple": {"primary": "#8b5cf6", "hover": "#7c3aed", "name": "Purple"},
    "cyan": {"primary": "#06b6d4", "hover": "#0891b2", "name": "Cyan"},
    "red": {"primary": "#ef4444", "hover": "#dc2626", "name": "Red"},
    "green": {"primary": "#10b981", "hover": "#059669", "name": "Green"},
    "orange": {"primary": "#f59e0b", "hover": "#d97706", "name": "Orange"},
    "pink": {"primary": "#ec4899", "hover": "#db2777", "name": "Pink"},
    "blue": {"primary": "#3b82f6", "hover": "#2563eb", "name": "Blue"},
}

DEFAULT_SETTINGS = {
    "accent_color": "purple",
    "minimize_to_tray": True,
    "show_notifications": True,
    "launch_on_startup": False,
    "auto_apply_on_launch": False,
    "last_preset": None,
    "last_profile": "default",
    "custom_deadlock_path": None,
    "window_geometry": None,
}


def get_settings_path() -> Path:
    """Get settings file path"""
    return get_config_dir() / "settings.json"


def load_settings() -> dict:
    """Load settings from disk"""
    settings_path = get_settings_path()
    settings = DEFAULT_SETTINGS.copy()
    
    try:
        if settings_path.exists():
            with open(settings_path, 'r', encoding='utf-8') as f:
                saved = json.load(f)
                settings.update(saved)
    except Exception as e:
        print(f"Failed to load settings: {e}")
    
    return settings


def save_settings(settings: dict) -> bool:
    """Save settings to disk"""
    settings_path = get_settings_path()
    
    try:
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        with open(settings_path, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2)
        return True
    except Exception as e:
        print(f"Failed to save settings: {e}")
        return False


def get_setting(key: str, default: Any = None) -> Any:
    """Get a single setting"""
    settings = load_settings()
    return settings.get(key, default)


def set_setting(key: str, value: Any) -> bool:
    """Set a single setting"""
    settings = load_settings()
    settings[key] = value
    return save_settings(settings)


# ============================================================================
# PROFILES
# ============================================================================

def get_profiles_dir() -> Path:
    """Get profiles directory"""
    profiles_dir = get_config_dir() / "profiles"
    profiles_dir.mkdir(parents=True, exist_ok=True)
    return profiles_dir


def list_profiles() -> list[dict]:
    """List all user profiles"""
    profiles_dir = get_profiles_dir()
    profiles = []
    
    # Default profiles
    default_profiles = [
        {"name": "default", "display": "🎮 Default", "description": "Your everyday settings"},
        {"name": "streaming", "display": "📺 Streaming", "description": "Optimized for streaming/recording"},
        {"name": "ranked", "display": "🏆 Ranked", "description": "Competitive settings for ranked"},
        {"name": "casual", "display": "☕ Casual", "description": "Relaxed settings for fun"},
    ]
    
    for profile in default_profiles:
        profile_file = profiles_dir / f"{profile['name']}.json"
        profile["path"] = profile_file
        profile["exists"] = profile_file.exists()
        profiles.append(profile)
    
    # Custom profiles
    for file in profiles_dir.glob("*.json"):
        name = file.stem
        if name not in [p["name"] for p in profiles]:
            profiles.append({
                "name": name,
                "display": f"📦 {name.title()}",
                "description": "Custom profile",
                "path": file,
                "exists": True,
            })
    
    return profiles


def save_profile(name: str, preset_name: str, convars: dict) -> bool:
    """Save a profile (preset + custom convars)"""
    profiles_dir = get_profiles_dir()
    profile_path = profiles_dir / f"{name}.json"
    
    try:
        profile_data = {
            "preset": preset_name,
            "convars": convars,
        }
        with open(profile_path, 'w', encoding='utf-8') as f:
            json.dump(profile_data, f, indent=2)
        return True
    except Exception as e:
        print(f"Failed to save profile: {e}")
        return False


def load_profile(name: str) -> Optional[dict]:
    """Load a profile"""
    profiles_dir = get_profiles_dir()
    profile_path = profiles_dir / f"{name}.json"
    
    try:
        if profile_path.exists():
            with open(profile_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Failed to load profile: {e}")
    
    return None


# ============================================================================
# CUSTOM PRESETS
# ============================================================================

def get_custom_presets_dir() -> Path:
    """Get custom presets directory"""
    presets_dir = get_config_dir() / "custom_presets"
    presets_dir.mkdir(parents=True, exist_ok=True)
    return presets_dir


def save_custom_preset(name: str, source_path: Path, description: str = "") -> Optional[Path]:
    """Save current config as a custom preset"""
    import shutil
    
    presets_dir = get_custom_presets_dir()
    safe_name = "".join(c for c in name if c.isalnum() or c in " _-").strip()
    preset_path = presets_dir / f"{safe_name}.gi"
    meta_path = presets_dir / f"{safe_name}.meta.json"
    
    try:
        # Copy the config file
        shutil.copy2(source_path, preset_path)
        
        # Save metadata
        meta = {
            "name": name,
            "description": description,
            "created": str(Path(source_path).stat().st_mtime),
        }
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(meta, f, indent=2)
        
        return preset_path
    except Exception as e:
        print(f"Failed to save custom preset: {e}")
        return None


def list_custom_presets() -> list[dict]:
    """List all custom presets"""
    presets_dir = get_custom_presets_dir()
    presets = []
    
    for file in presets_dir.glob("*.gi"):
        name = file.stem
        meta_path = presets_dir / f"{name}.meta.json"
        
        meta = {"name": name, "description": "Custom preset"}
        try:
            if meta_path.exists():
                with open(meta_path, 'r', encoding='utf-8') as f:
                    meta.update(json.load(f))
        except:
            pass
        
        presets.append({
            "name": name,
            "display": f"⭐ {meta.get('name', name)}",
            "description": meta.get("description", "Custom preset"),
            "path": file,
            "custom": True,
        })
    
    return presets


def export_preset(preset_path: Path, export_path: Path) -> bool:
    """Export a preset to a file"""
    import shutil
    try:
        shutil.copy2(preset_path, export_path)
        return True
    except Exception as e:
        print(f"Failed to export preset: {e}")
        return False


def import_preset(import_path: Path, name: str = None) -> Optional[Path]:
    """Import a preset from a file"""
    import shutil
    
    presets_dir = get_custom_presets_dir()
    name = name or import_path.stem
    safe_name = "".join(c for c in name if c.isalnum() or c in " _-").strip()
    preset_path = presets_dir / f"{safe_name}.gi"
    
    try:
        shutil.copy2(import_path, preset_path)
        return preset_path
    except Exception as e:
        print(f"Failed to import preset: {e}")
        return None


# ============================================================================
# STARTUP
# ============================================================================

APP_NAME = "DeadlockConfigManager"
STARTUP_REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def get_exe_path() -> Optional[Path]:
    """Get the path to the current executable"""
    import sys
    
    # If running as frozen exe
    if getattr(sys, 'frozen', False):
        return Path(sys.executable)
    
    # Running as script - return None (can't add to startup)
    return None


def is_startup_enabled() -> bool:
    """Check if app is set to run on startup"""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_REG_KEY, 0, winreg.KEY_READ)
        try:
            winreg.QueryValueEx(key, APP_NAME)
            winreg.CloseKey(key)
            return True
        except WindowsError:
            winreg.CloseKey(key)
            return False
    except WindowsError:
        return False


def set_startup_enabled(enabled: bool) -> bool:
    """Enable or disable startup"""
    exe_path = get_exe_path()
    
    if not exe_path and enabled:
        print("Cannot enable startup when running as script")
        return False
    
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_REG_KEY, 0, winreg.KEY_SET_VALUE)
        
        if enabled:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, f'"{exe_path}" --minimized')
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except WindowsError:
                pass  # Key doesn't exist, that's fine
        
        winreg.CloseKey(key)
        return True
    except WindowsError as e:
        print(f"Failed to modify startup: {e}")
        return False


# ============================================================================
# GAME LAUNCH
# ============================================================================

def launch_deadlock() -> bool:
    """Launch Deadlock via Steam"""
    try:
        # Use Steam URL protocol
        subprocess.Popen(
            f'start steam://rungameid/{DEADLOCK_APP_ID}',
            shell=True
        )
        return True
    except Exception as e:
        print(f"Failed to launch Deadlock: {e}")
        return False


def is_deadlock_running() -> bool:
    """Check if Deadlock is currently running"""
    try:
        result = subprocess.run(
            ['tasklist', '/FI', 'IMAGENAME eq project8.exe'],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        return 'project8.exe' in result.stdout.lower()
    except:
        # Also try deadlock.exe as backup
        try:
            result = subprocess.run(
                ['tasklist', '/FI', 'IMAGENAME eq deadlock.exe'],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            return 'deadlock.exe' in result.stdout.lower()
        except:
            return False
