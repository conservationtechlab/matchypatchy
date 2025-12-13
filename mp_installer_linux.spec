# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_submodules, collect_data_files

datas= [("/home/kyra/matchypatchy/README.md", "."),
        ("/home/kyra/matchypatchy/LICENSE", "."),
        ("/home/kyra/matchypatchy/ABOUT.md", "."),
        ("/home/kyra/matchypatchy/assets/models.yml", "./assets"),
        ("/home/kyra/matchypatchy/assets/schema.txt", "./assets"),
        ("/home/kyra/matchypatchy/assets/graphics/logo.png", "./assets/graphics"),
        ("/home/kyra/matchypatchy/assets/graphics/fluent_pencil_icon.png", "./assets/graphics"),
        ("/home/kyra/matchypatchy/assets/graphics/thumbnail_notfound.png", "./assets/graphics"),
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
    [],
    exclude_binaries=True,
    name='MatchyPatchy',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    onefile=True,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='mp_installer',
)
