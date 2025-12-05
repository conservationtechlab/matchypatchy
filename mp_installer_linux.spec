# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_submodules, collect_data_files

datas= [("/home/kyra/matchypatchy/README.md", "."),
        ("/home/kyra/matchypatchy/LICENSE", "."),
        ("/home/kyra/matchypatchy/models.yml", "."),
        ("/home/kyra/matchypatchy/config.yml", "."),
        ("/home/kyra/matchypatchy/assets/schema.txt", "./assets"),
        ("/home/kyra/matchypatchy/assets/logo.png", "./assets"),
        ("/home/kyra/matchypatchy/assets/fluent_pencil_icon.png", "./assets"),
        ("/home/kyra/matchypatchy/assets/thumbnail_notfound.png", "./assets"),
        ]
binaries = []
hiddenimports = []

tmp_ret = collect_all('chromadb')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

a = Analysis(
    ['mp_installer.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='MatchyPatchy',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
