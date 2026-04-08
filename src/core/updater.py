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
        temp_dir = Path(tempfile.gettempdir()) / "OptiLockManager"
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
    
    Args:
        update_path: Path to the downloaded update file
    
    Returns:
        True if update process started, False if failed
    """
    if not update_path.exists():
        return False
    
    try:
        current_exe = Path(sys.executable)
        
        if not current_exe.name.endswith('.exe'):
            # Running from Python directly, can't auto-update
            print("Auto-update only works with compiled .exe")
            return False
        
        # Create a PowerShell script that:
        # 1. Waits for the current process to fully exit (by PID)
        # 2. Waits extra time for file handles to release
        # 3. Replaces the exe
        # 4. Starts the new exe
        # 5. Cleans up
        
        current_pid = os.getpid()
        ps_path = update_path.parent / "update.ps1"
        
        ps_content = f'''
$ErrorActionPreference = "SilentlyContinue"

# Wait for the main process to exit
$process = Get-Process -Id {current_pid} -ErrorAction SilentlyContinue
if ($process) {{
    $process.WaitForExit()
}}

# Extra wait for file handles to release
Start-Sleep -Seconds 3

# Try to copy with retries
$maxRetries = 10
$retryCount = 0
$success = $false

while (-not $success -and $retryCount -lt $maxRetries) {{
    try {{
        Copy-Item -Path "{update_path}" -Destination "{current_exe}" -Force
        $success = $true
    }} catch {{
        $retryCount++
        Start-Sleep -Seconds 1
    }}
}}

if ($success) {{
    # Start the new exe
    Start-Process -FilePath "{current_exe}"
}}

# Clean up
Remove-Item -Path "{update_path}" -Force -ErrorAction SilentlyContinue
Remove-Item -Path $MyInvocation.MyCommand.Path -Force -ErrorAction SilentlyContinue
'''
        
        with open(ps_path, 'w', encoding='utf-8') as f:
            f.write(ps_content)
        
        # Start PowerShell script hidden and detached
        subprocess.Popen(
            ['powershell', '-ExecutionPolicy', 'Bypass', '-WindowStyle', 'Hidden', '-File', str(ps_path)],
            creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
            start_new_session=True
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
