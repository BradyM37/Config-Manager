"""
Build Script
Compiles the application to a standalone .exe using PyInstaller
"""

import subprocess
import sys
import shutil
from pathlib import Path

def build():
    print("🔨 Building OptiLock Config Manager...")
    
    # Ensure PyInstaller is available
    try:
        import PyInstaller
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
    
    # Build command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=OptiLockManager",
        "--onefile",
        "--windowed",
        "--icon=assets/icon.ico" if Path("assets/icon.ico").exists() else "",
        "--add-data=src/data;src/data",
        "--hidden-import=customtkinter",
        "--hidden-import=packaging",
        "--collect-all=customtkinter",
        "src/main.py"
    ]
    
    # Filter out empty strings
    cmd = [c for c in cmd if c]
    
    print(f"Running: {' '.join(cmd)}")
    
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        print("\n✅ Build successful!")
        print("📁 Output: dist/OptiLockManager.exe")
        
        # Copy presets to dist if they exist
        presets_src = Path("src/data/presets")
        presets_dst = Path("dist/presets")
        if presets_src.exists() and list(presets_src.glob("*.gi")):
            shutil.copytree(presets_src, presets_dst, dirs_exist_ok=True)
            print("📦 Copied preset configs to dist/presets/")
    else:
        print("\n❌ Build failed!")
        sys.exit(1)


if __name__ == "__main__":
    build()
