# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_submodules, collect_data_files
import sys

datas= [
    ("C:/Users/kyra/matchypatchy/README.md", "."),
    ("C:/Users/kyra/matchypatchy/LICENSE", "."),
    ("C:/Users/kyra/matchypatchy/assets/config.yml", "."),
    ("C:/Users/kyra/matchypatchy/assets/models.yml", "./assets"),
    ("C:/Users/kyra/matchypatchy/assets/schema.txt", "./assets"),
    ("C:/Users/kyra/matchypatchy/assets/logo.png", "./assets"),
    ("C:/Users/kyra/matchypatchy/assets/fluent_pencil_icon.png", "./assets"),
    ("C:/Users/kyra/matchypatchy/assets/thumbnail_notfound.png", "./assets"),
]

# Put MSVC runtime DLLs into binaries so they extract into the root of the bundle
binaries = [
    ('C:/Users/kyra/matchypatchy/assets/dll/msvcp140.dll', '.'),
    ('C:/Users/kyra/matchypatchy/assets/dll/msvcp140_1.dll', '.'),
    ('C:/Users/kyra/matchypatchy/assets/dll/vcruntime140.dll', '.')
]

hiddenimports = []

# Collect chromadb and onnxruntime packaged files
tmp_chroma = collect_all('chromadb')
datas += tmp_chroma[0]; binaries += tmp_chroma[1]; hiddenimports += tmp_chroma[2]
tmp_onnx = collect_all('onnxruntime')
datas += tmp_onnx[0]; binaries += tmp_onnx[1]; hiddenimports += tmp_onnx[2]

# ALSO: include python DLL from the Python used to run PyInstaller (if present)
# This ensures python312.dll (or whatever the interpreter DLL is named) is placed
# into the dist root so native extensions that depend on it can initialize.
python_dll_candidates = []
python_dir = os.path.dirname(sys.executable)
# Common name pattern for CPython on Windows: python<major><minor>.dll e.g. python312.dll
py_dll_name = f"python{sys.version_info.major}{sys.version_info.minor}.dll"
py_dll_path = os.path.join(python_dir, py_dll_name)
if os.path.exists(py_dll_path):
    python_dll_candidates.append(py_dll_path)
else:
    # fallback: some distributions name the dll differently or place it elsewhere
    # try sys.dllhandle (not always available) or the next-to-executable convention
    alt = os.path.join(python_dir, os.path.basename(sys.executable).replace('.exe', '.dll'))
    if os.path.exists(alt):
        python_dll_candidates.append(alt)

for p in python_dll_candidates:
    # place the python DLL into dist root (destination '.')
    binaries.append((p, '.'))

a = Analysis(
    ['mp_installer.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
   # runtime_hooks=['C:/Users/kyra/matchypatchy/hooks/runtime-hook-onnxruntime.py'],  # <- ensure runtime hook runs early
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
    upx=False,                        # disable UPX to avoid corrupting native DLLs
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
    upx=False,
    upx_exclude=['onnxruntime.dll', 'onnxruntime_pybind11_state.pyd', 'onnxruntime_providers_cuda.dll', 'vcruntime140.dll', 'msvcp140.dll', 'msvcp140_1.dll'],
    name='MatchyPatchy',
)
