# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

# Project root
ROOT = Path(SPECPATH)

# Collect all src submodules
src_hiddenimports = collect_submodules('src')
ctk_hiddenimports = collect_submodules('customtkinter')

# Collect customtkinter data files
ctk_datas = collect_data_files('customtkinter')

a = Analysis(
    ['launcher.py'],
    pathex=[str(ROOT), str(ROOT / 'src')],
    binaries=[],
    datas=[
        ('src/data', 'src/data'),
        ('src', 'src'),
        ('community-presets', 'community-presets'),
    ] + ctk_datas,
    hiddenimports=[
        'PIL._tkinter_finder',
        'packaging.version',
        'packaging.requirements',
        'keyboard',
        'keyboard._winkeyboard',
    ] + src_hiddenimports + ctk_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='DeadlockConfigManager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico' if Path('assets/icon.ico').exists() else None,
)
