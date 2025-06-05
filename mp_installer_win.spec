# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_submodules, collect_data_files

datas= [("C:/Users/tswanson/matchypatchy/README.md", "."),
        ("C:/Users/tswanson/matchypatchy/LICENSE", "."),
        ("C:/Users/tswanson/matchypatchy/models.yml", "."),
        ("C:/Users/tswanson/matchypatchy/config.yml", "."),
        ("C:/Users/tswanson/matchypatchy/assets/schema.txt", "./assets"),
        ("C:/Users/tswanson/matchypatchy/assets/logo.png", "./assets"),
        ("C:/Users/tswanson/matchypatchy/assets/fluent_pencil_icon.png", "./assets"),
        ("C:/Users/tswanson/matchypatchy/assets/thumbnail_notfound.png", "./assets"),
        ("C:/Users/tswanson/anaconda3/envs/mp_installer/lib/python3.12/site-packages/ultralytics/cfg/default.yaml", "./ultralytics/cfg"),
        ("C:/Users/tswanson/anaconda3/envs/mp_installer/lib/python3.12/site-packages/ultralytics/cfg/solutions/default.yaml", "./ultralytics/cfg/solutions"),
        ]
binaries = []
hiddenimports = ['torch._C',
                'torch._C._cuda',
                'torch.backends.cudnn',
                'torch.backends.cuda',
                'torchvision',
                'torchvision.io.image',]

tmp_ret = collect_all('chromadb')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

datas += collect_data_files('torch', include_py_files=True)
hiddenimports += collect_submodules('torch')



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
    name='mp_installer',
)
