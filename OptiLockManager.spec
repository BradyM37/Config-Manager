# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

# Add the project root to the path
block_cipher = None

# Project root
ROOT = Path(SPECPATH)

a = Analysis(
    ['src/main.py'],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        ('src/data', 'src/data'),
    ],
    hiddenimports=[
        'customtkinter',
        'packaging',
        'packaging.version',
        'packaging.requirements',
        'PIL',
        'PIL._tkinter_finder',
        'src',
        'src.core',
        'src.core.config',
        'src.core.backup', 
        'src.core.detector',
        'src.core.updater',
        'src.ui',
        'src.ui.app',
        'src.ui.convar_panel',
        'src.ui.preset_cards',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
    collect_submodules=['customtkinter', 'src'],
    collect_data=['customtkinter'],
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='OptiLockManager',
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
