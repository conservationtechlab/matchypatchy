# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas= [("/home/kyra/matchypatchy/models.yml", "."),
        ("/home/kyra/matchypatchy/config.yml", "."),
        ("/home/kyra/matchypatchy/assets/schema.txt", "./assets"),
        ("/home/kyra/matchypatchy/assets/logo.png", "./assets"),
        ("/home/kyra/matchypatchy/assets/fluent_pencil_icon.png", "./assets"),
        ("/home/kyra/matchypatchy/assets/thumbnail_notfound.png", "./assets"),
        ("/home/kyra/anaconda3/envs/mp/lib/python3.12/site-packages/ultralytics/cfg/default.yaml", "./ultralytics/cfg"),
        ("/home/kyra/anaconda3/envs/mp/lib/python3.12/site-packages/ultralytics/cfg/solutions/default.yaml", "./ultralytics/cfg/solutions")]
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
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='MatchyPatchy',
)
