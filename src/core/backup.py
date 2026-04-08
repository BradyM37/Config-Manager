"""
Backup and Restore System
Manages gameinfo.gi backups with timestamps
"""

import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from .detector import get_gameinfo_path


def get_backup_dir() -> Path:
    """Get the backup directory path"""
    backup_dir = Path.home() / "AppData" / "Local" / "OptiLockManager" / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


def get_config_dir() -> Path:
    """Get the config directory for app settings"""
    config_dir = Path.home() / "AppData" / "Local" / "OptiLockManager"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def create_backup(deadlock_path: Path, label: str = "") -> Optional[Path]:
    """
    Create a backup of the current gameinfo.gi
    
    Args:
        deadlock_path: Path to Deadlock installation
        label: Optional label for the backup (e.g., 'pre-install', 'vanilla')
    
    Returns:
        Path to the backup file, or None if failed
    """
    gameinfo_path = get_gameinfo_path(deadlock_path)
    
    if not gameinfo_path.exists():
        return None
    
    backup_dir = get_backup_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if label:
        backup_name = f"gameinfo_{label}_{timestamp}.gi"
    else:
        backup_name = f"gameinfo_{timestamp}.gi"
    
    backup_path = backup_dir / backup_name
    
    try:
        shutil.copy2(gameinfo_path, backup_path)
        return backup_path
    except Exception as e:
        print(f"Backup failed: {e}")
        return None


def list_backups() -> list[dict]:
    """
    List all available backups
    
    Returns:
        List of backup info dicts with 'path', 'name', 'date', 'label'
    """
    backup_dir = get_backup_dir()
    backups = []
    
    for file in sorted(backup_dir.glob("gameinfo_*.gi"), reverse=True):
        # Parse filename: gameinfo_[label_]YYYYMMDD_HHMMSS.gi
        name = file.stem  # gameinfo_label_20260408_120000
        parts = name.split("_")
        
        try:
            # Extract timestamp (last two parts)
            time_str = f"{parts[-2]}_{parts[-1]}"
            date = datetime.strptime(time_str, "%Y%m%d_%H%M%S")
            
            # Extract label (everything between 'gameinfo' and timestamp)
            if len(parts) > 3:
                label = "_".join(parts[1:-2])
            else:
                label = ""
            
            backups.append({
                "path": file,
                "name": file.name,
                "date": date,
                "label": label,
                "display": f"{date.strftime('%Y-%m-%d %H:%M')} {f'({label})' if label else ''}"
            })
        except (ValueError, IndexError):
            # Malformed filename, skip
            continue
    
    return backups


def restore_backup(deadlock_path: Path, backup_path: Path) -> bool:
    """
    Restore a backup to gameinfo.gi
    
    Args:
        deadlock_path: Path to Deadlock installation
        backup_path: Path to the backup file to restore
    
    Returns:
        True if successful, False otherwise
    """
    if not backup_path.exists():
        return False
    
    gameinfo_path = get_gameinfo_path(deadlock_path)
    
    try:
        # Create a backup of current before restoring
        create_backup(deadlock_path, label="pre-restore")
        
        # Restore the backup
        shutil.copy2(backup_path, gameinfo_path)
        return True
    except Exception as e:
        print(f"Restore failed: {e}")
        return False


def delete_backup(backup_path: Path) -> bool:
    """Delete a backup file"""
    try:
        backup_path.unlink()
        return True
    except Exception:
        return False


def ensure_vanilla_backup(deadlock_path: Path) -> Optional[Path]:
    """
    Ensure we have a vanilla backup (first-time backup)
    
    Returns existing vanilla backup or creates one if none exists
    """
    backup_dir = get_backup_dir()
    vanilla_backups = list(backup_dir.glob("gameinfo_vanilla_*.gi"))
    
    if vanilla_backups:
        return vanilla_backups[0]
    
    # No vanilla backup exists, create one
    return create_backup(deadlock_path, label="vanilla")


if __name__ == "__main__":
    # Test backup system
    from .detector import find_deadlock
    
    path = find_deadlock()
    if path:
        print(f"Creating backup...")
        backup = create_backup(path, label="test")
        print(f"Backup created: {backup}")
        
        print(f"\nAll backups:")
        for b in list_backups():
            print(f"  {b['display']}")
