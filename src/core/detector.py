"""
Deadlock Installation Detector
Finds Deadlock install path across Steam libraries
"""

import os
import re
import winreg
from pathlib import Path
from typing import Optional


def get_steam_path() -> Optional[Path]:
    """Get Steam installation path from registry"""
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam")
        steam_path, _ = winreg.QueryValueEx(key, "InstallPath")
        winreg.CloseKey(key)
        return Path(steam_path)
    except (WindowsError, FileNotFoundError):
        pass
    
    # Fallback to common paths
    common_paths = [
        Path(r"C:\Program Files (x86)\Steam"),
        Path(r"C:\Program Files\Steam"),
        Path(r"D:\Steam"),
        Path(r"E:\Steam"),
    ]
    
    for path in common_paths:
        if path.exists():
            return path
    
    return None


def get_steam_libraries(steam_path: Path) -> list[Path]:
    """Parse libraryfolders.vdf to get all Steam library paths"""
    libraries = [steam_path]
    vdf_path = steam_path / "steamapps" / "libraryfolders.vdf"
    
    if not vdf_path.exists():
        return libraries
    
    try:
        with open(vdf_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse VDF format - look for "path" entries
        pattern = r'"path"\s+"([^"]+)"'
        matches = re.findall(pattern, content)
        
        for match in matches:
            lib_path = Path(match.replace("\\\\", "\\"))
            if lib_path.exists() and lib_path not in libraries:
                libraries.append(lib_path)
    
    except Exception:
        pass
    
    return libraries


def find_deadlock() -> Optional[Path]:
    """Find Deadlock installation directory"""
    steam_path = get_steam_path()
    
    if not steam_path:
        return None
    
    libraries = get_steam_libraries(steam_path)
    
    for library in libraries:
        deadlock_path = library / "steamapps" / "common" / "Deadlock"
        gameinfo_path = deadlock_path / "game" / "citadel" / "gameinfo.gi"
        
        if gameinfo_path.exists():
            return deadlock_path
    
    return None


def get_gameinfo_path(deadlock_path: Path) -> Path:
    """Get the gameinfo.gi path from Deadlock install"""
    return deadlock_path / "game" / "citadel" / "gameinfo.gi"


def validate_deadlock_path(path: Path) -> bool:
    """Validate that a path is a valid Deadlock installation"""
    if not path.exists():
        return False
    
    gameinfo = path / "game" / "citadel" / "gameinfo.gi"
    return gameinfo.exists()


def get_current_config_info(deadlock_path: Path) -> dict:
    """Parse current gameinfo.gi to get config info"""
    gameinfo_path = get_gameinfo_path(deadlock_path)
    
    info = {
        "installed": False,
        "name": "Vanilla/Unknown",
        "version": None
    }
    
    if not gameinfo_path.exists():
        return info
    
    try:
        with open(gameinfo_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Look for OptiLock/OptimizationLock signatures
        if "OptiLock" in content or "DYSON EDITION" in content:
            info["installed"] = True
            info["name"] = "OptiLock"
            
            # Try to extract version
            version_match = re.search(r'ver[.\s]*(\d+\.?\d*\.?\d*)', content, re.IGNORECASE)
            if version_match:
                info["version"] = version_match.group(1)
        
        elif "OptimizationLock" in content:
            info["installed"] = True
            info["name"] = "OptimizationLock"
            
            version_match = re.search(r'v(\d+\.?\d*\.?\d*)', content)
            if version_match:
                info["version"] = version_match.group(1)
    
    except Exception:
        pass
    
    return info


if __name__ == "__main__":
    # Test detection
    path = find_deadlock()
    if path:
        print(f"Found Deadlock at: {path}")
        info = get_current_config_info(path)
        print(f"Config info: {info}")
    else:
        print("Deadlock not found")
