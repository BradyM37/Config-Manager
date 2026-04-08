# Core modules
from .detector import find_deadlock, get_gameinfo_path, validate_deadlock_path, get_current_config_info
from .backup import create_backup, restore_backup, list_backups, ensure_vanilla_backup, get_config_dir
from .config import list_presets, apply_preset, get_presets_dir
from .settings import (
    load_settings, save_settings, get_setting, set_setting,
    ACCENT_COLORS, list_profiles, save_profile, load_profile,
    list_custom_presets, save_custom_preset, export_preset, import_preset,
    launch_deadlock, is_deadlock_running, is_startup_enabled, set_startup_enabled
)
from .tray import init_tray, stop_tray, get_tray, TRAY_AVAILABLE
from .notifications import NOTIFICATIONS_AVAILABLE, show_notification
