# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

project_root = Path(SPECPATH)
src_root = project_root / "src"

a = Analysis(
    [str(project_root / "run.py")],
    pathex=[str(src_root)],
    binaries=[],
    datas=[
        (str(project_root / "assets" / "vostok-vault.ico"), "assets"),
    ],
    hiddenimports=[
        "customtkinter",
        "PIL._tkinter_finder",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "pytest",
        "pytest_cov",
        "pyinstaller",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="VostokVault",
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
    icon=str(project_root / "assets" / "vostok-vault.ico"),
)
