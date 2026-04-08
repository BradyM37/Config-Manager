"""
Auto-Updater
Checks GitHub for updates and downloads new versions
"""

import json
import os
import tempfile
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional
from packaging import version

import requests

from src import __version__

# GitHub repository info
GITHUB_OWNER = "BradyM37"
GITHUB_REPO = "Config-Manager"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"

# Current version
CURRENT_VERSION = __version__


def check_for_updates() -> Optional[dict]:
    """
    Check GitHub for a newer version
    
    Returns:
        Dict with update info if available, None if up to date or error
        {
            'version': '1.1.0',
            'download_url': 'https://...',
            'release_notes': '...',
            'published_at': '2026-04-08T...'
        }
    """
    try:
        response = requests.get(
            GITHUB_API_URL,
            headers={"Accept": "application/vnd.github.v3+json"},
            timeout=10
        )
        
        if response.status_code == 404:
            # No releases yet
            return None
        
        response.raise_for_status()
        data = response.json()
        
        latest_version = data["tag_name"].lstrip("v")
        
        if version.parse(latest_version) > version.parse(CURRENT_VERSION):
            # Find the .exe asset
            download_url = None
            for asset in data.get("assets", []):
                if asset["name"].endswith(".exe"):
                    download_url = asset["browser_download_url"]
                    break
            
            # Fallback to zipball if no exe
            if not download_url:
                download_url = data.get("zipball_url")
            
            return {
                "version": latest_version,
                "download_url": download_url,
                "release_notes": data.get("body", ""),
                "published_at": data.get("published_at", ""),
                "html_url": data.get("html_url", "")
            }
        
        return None
    
    except requests.RequestException as e:
        print(f"Update check failed: {e}")
        return None
    except (KeyError, json.JSONDecodeError) as e:
        print(f"Failed to parse update response: {e}")
        return None


def download_update(download_url: str, progress_callback=None) -> Optional[Path]:
    """
    Download an update file
    
    Args:
        download_url: URL to download from
        progress_callback: Optional callback(bytes_downloaded, total_bytes)
    
    Returns:
        Path to downloaded file, or None if failed
    """
    try:
        response = requests.get(download_url, stream=True, timeout=60)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        
        # Create temp file
        temp_dir = Path(tempfile.gettempdir()) / "DeadlockConfigManager"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        filename = download_url.split("/")[-1]
        temp_path = temp_dir / filename
        
        downloaded = 0
        with open(temp_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback and total_size:
                        progress_callback(downloaded, total_size)
        
        return temp_path
    
    except Exception as e:
        print(f"Download failed: {e}")
        return None


def apply_update(update_path: Path) -> bool:
    """
    Apply a downloaded update (replace current exe and restart)
    
    Uses a batch file for maximum compatibility (PowerShell can have issues)
    
    Args:
        update_path: Path to the downloaded update file
    
    Returns:
        True if update process started, False if failed
    """
    if not update_path.exists():
        print(f"Update file not found: {update_path}")
        return False
    
    try:
        current_exe = Path(sys.executable)
        
        if not current_exe.name.endswith('.exe'):
            # Running from Python directly, can't auto-update
            print("Auto-update only works with compiled .exe")
            return False
        
        # Create a batch file that:
        # 1. Waits for the current process to exit (using tasklist polling)
        # 2. Replaces the exe with retries
        # 3. Starts the new exe
        # 4. Cleans up
        
        current_pid = os.getpid()
        bat_path = update_path.parent / "update.bat"
        
        # Use short paths to avoid issues with spaces
        update_path_str = str(update_path)
        current_exe_str = str(current_exe)
        
        bat_content = f'''@echo off
setlocal

:: Wait for the main process to exit
:waitloop
tasklist /FI "PID eq {current_pid}" 2>NUL | find /I "{current_pid}" >NUL
if not errorlevel 1 (
    timeout /t 1 /nobreak >NUL
    goto waitloop
)

:: Extra wait for file handles to release
timeout /t 2 /nobreak >NUL

:: Try to copy with retries
set retries=0
:copyloop
copy /Y "{update_path_str}" "{current_exe_str}" >NUL 2>&1
if errorlevel 1 (
    set /a retries+=1
    if %retries% lss 15 (
        timeout /t 1 /nobreak >NUL
        goto copyloop
    )
    echo Update failed after retries
    pause
    goto cleanup
)

:: Start the new exe
start "" "{current_exe_str}"

:cleanup
:: Clean up downloaded file
del /f /q "{update_path_str}" >NUL 2>&1

:: Self-delete this batch file
(goto) 2>NUL & del /f /q "%~f0"
'''
        
        with open(bat_path, 'w', encoding='utf-8') as f:
            f.write(bat_content)
        
        # Start batch file hidden and detached
        # Using cmd /c with start to fully detach
        subprocess.Popen(
            f'cmd /c start /min "" "{bat_path}"',
            shell=True,
            creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        return True
    
    except Exception as e:
        print(f"Failed to apply update: {e}")
        return False


def get_version_string() -> str:
    """Get current version string for display"""
    return f"v{CURRENT_VERSION}"


if __name__ == "__main__":
    print(f"Current version: {get_version_string()}")
    print("Checking for updates...")
    
    update = check_for_updates()
    if update:
        print(f"Update available: v{update['version']}")
        print(f"Download: {update['download_url']}")
        print(f"Notes: {update['release_notes'][:200]}...")
    else:
        print("You're up to date!")
