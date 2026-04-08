"""
Toast Notifications
Windows toast notifications for app events
"""

from pathlib import Path
from typing import Optional

try:
    from winotify import Notification, audio
    NOTIFICATIONS_AVAILABLE = True
except ImportError:
    NOTIFICATIONS_AVAILABLE = False
    Notification = None


APP_ID = "Deadlock Config Manager"


def show_notification(
    title: str,
    message: str,
    icon_path: Optional[Path] = None,
    sound: bool = True
) -> bool:
    """
    Show a Windows toast notification
    
    Args:
        title: Notification title
        message: Notification body
        icon_path: Optional path to icon
        sound: Whether to play a sound
    
    Returns:
        True if notification was shown
    """
    if not NOTIFICATIONS_AVAILABLE:
        print(f"[Notification] {title}: {message}")
        return False
    
    try:
        toast = Notification(
            app_id=APP_ID,
            title=title,
            msg=message,
        )
        
        if icon_path and icon_path.exists():
            toast.set_audio(audio.Default if sound else audio.Silent, loop=False)
            toast.icon = str(icon_path)
        elif sound:
            toast.set_audio(audio.Default, loop=False)
        else:
            toast.set_audio(audio.Silent, loop=False)
        
        toast.show()
        return True
    except Exception as e:
        print(f"Failed to show notification: {e}")
        return False


def notify_preset_applied(preset_name: str, icon_path: Optional[Path] = None):
    """Notify that a preset was applied"""
    icons = {
        "potato": "🥔",
        "balanced": "⚖️",
        "quality": "💎",
        "competitive": "🎯",
    }
    icon = icons.get(preset_name.lower(), "✅")
    
    show_notification(
        f"{icon} Preset Applied",
        f"{preset_name.title()} config has been applied to Deadlock.",
        icon_path
    )


def notify_backup_created(icon_path: Optional[Path] = None):
    """Notify that a backup was created"""
    show_notification(
        "💾 Backup Created",
        "Your config has been backed up successfully.",
        icon_path
    )


def notify_game_detected(icon_path: Optional[Path] = None):
    """Notify that Deadlock was detected"""
    show_notification(
        "🎮 Deadlock Detected",
        "Found Deadlock installation. Ready to apply configs!",
        icon_path
    )


def notify_game_launched(icon_path: Optional[Path] = None):
    """Notify that Deadlock is launching"""
    show_notification(
        "🚀 Launching Deadlock",
        "Starting Deadlock via Steam...",
        icon_path,
        sound=False
    )


def notify_update_available(version: str, icon_path: Optional[Path] = None):
    """Notify that an update is available"""
    show_notification(
        "🔄 Update Available",
        f"Version {version} is available. Click to download.",
        icon_path
    )


def notify_custom_preset_saved(name: str, icon_path: Optional[Path] = None):
    """Notify that a custom preset was saved"""
    show_notification(
        "⭐ Preset Saved",
        f'Your preset "{name}" has been saved.',
        icon_path
    )


def notify_profile_switched(profile_name: str, icon_path: Optional[Path] = None):
    """Notify that profile was switched"""
    show_notification(
        "🔄 Profile Switched",
        f"Switched to {profile_name} profile.",
        icon_path,
        sound=False
    )
