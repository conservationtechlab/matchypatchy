import os
import glob
import ctypes
import sys
import tempfile
import traceback
import importlib

def find_cudart_on_path():
    """Search PATH for cudart64_*.dll. Returns full path or None."""
    paths = os.environ.get("PATH", "").split(os.pathsep)
    for p in paths:
        try:
            for f in glob.glob(os.path.join(p, "cudart64_*.dll")):
                return os.path.abspath(f)
        except Exception:
            continue
    return None

def query_cuda_runtime_version(cudart_path):
    """
    Load cudart DLL and call cudaRuntimeGetVersion to get runtime version.
    Returns (major, minor) tuple, e.g. (11, 8).
    Raises Exception on failure.
    """
    # Use WinDLL so the stdcall calling convention is used as needed
    lib = ctypes.WinDLL(cudart_path)
    # int cudaRuntimeGetVersion(int *runtimeVersion)
    try:
        func = lib.cudaRuntimeGetVersion
    except AttributeError:
        raise RuntimeError("cudart does not export cudaRuntimeGetVersion")
    func.argtypes = [ctypes.POINTER(ctypes.c_int)]
    func.restype = ctypes.c_int
    v = ctypes.c_int(0)
    rc = func(ctypes.byref(v))
    if rc != 0:
        raise RuntimeError(f"cudaRuntimeGetVersion returned error {rc}")
    # CUDA runtime version returned as integer like 11080 (for 11.8.0)
    ver = v.value
    major = ver // 1000
    minor = (ver % 1000) // 10
    return major, minor

def has_cuda_gpu(cudart_path):
    """
    Returns (device_count) using cudaGetDeviceCount if available,
    or None if check could not be performed.
    """
    try:
        lib = ctypes.WinDLL(cudart_path)
        func = lib.cudaGetDeviceCount
        func.argtypes = [ctypes.POINTER(ctypes.c_int)]
        func.restype = ctypes.c_int
        cnt = ctypes.c_int(0)
        rc = func(ctypes.byref(cnt))
        if rc != 0:
            return 0
        return cnt.value
    except Exception:
        return None

def check_cuda(required_major=None, required_minor=None, require_gpu=True):
    """
    Checks for a cudart DLL and optionally for a minimum version and GPU.
    Returns (ok:bool, msg:str, details:dict).
    """
    cudart = find_cudart_on_path()
    if not cudart:
        return False, "CUDA runtime (cudart64_*.dll) not found on PATH.", {"cudart_path": None}
    try:
        major, minor = query_cuda_runtime_version(cudart)
    except Exception as e:
        return False, f"Failed to query CUDA runtime from '{cudart}': {e}", {"cudart_path": cudart}
    if required_major is not None:
        if (major, minor) < (required_major, required_minor or 0):
            return False, f"CUDA runtime {major}.{minor} found at '{cudart}' — required >= {required_major}.{required_minor}", {"cudart_path": cudart, "version": f"{major}.{minor}"}
    devcount = None
    if require_gpu:
        devcount = has_cuda_gpu(cudart)
        if devcount is None:
            # Could not call cudaGetDeviceCount (non-fatal — still might work)
            return False, f"Could not query CUDA devices using '{cudart}'.", {"cudart_path": cudart, "version": f"{major}.{minor}"}
        if devcount == 0:
            return False, f"No CUDA-capable devices found (cudaDriver/runtime present at '{cudart}').", {"cudart_path": cudart, "version": f"{major}.{minor}"}
    return True, f"CUDA runtime {major}.{minor} found at '{cudart}' with {devcount if devcount is not None else 'unknown'} devices.", {"cudart_path": cudart, "version": f"{major}.{minor}", "devices": devcount}

def user_message_box(title, text):
    """Show a Windows message box (useful for GUI installers)."""
    try:
        ctypes.windll.user32.MessageBoxW(None, str(text), str(title), 0x40)  # MB_ICONINFORMATION
    except Exception:
        print(f"{title}: {text}")

def show_and_exit(msg, code=2, gui=True):
    # Use message box in GUI mode; otherwise print to console then exit
    if gui:
        try:
            user_message_box("MatchyPatchy: CUDA check failed", msg)
        except Exception:
            print(msg, file=sys.stderr)
    else:
        print(msg, file=sys.stderr)
    sys.exit(code)


def add_dir_for_dlls(path):
    try:
        if hasattr(os, "add_dll_directory"):
            handle = os.add_dll_directory(path)
            if not hasattr(sys, "_dll_dir_handles"):
                sys._dll_dir_handles = []
            sys._dll_dir_handles.append(handle)
    except Exception:
        pass
    os.environ["PATH"] = os.pathsep.join([path, os.environ.get("PATH", "")])


# If running frozen, register MEIPASS and onnxruntime dirs immediately:
if getattr(sys, "frozen", False):
    base = getattr(sys, "_MEIPASS", None)
    if base:
        # Register as early as possible
        for d in (base, os.path.join(base, "onnxruntime"), os.path.join(base, "onnxruntime", "capi")):
            if os.path.isdir(d):
                add_dir_for_dlls(d)
        # Also search for CUDA dlls under extracted tree and register their dirs:
        for root, dirs, files in os.walk(base):
            for f in files:
                if f.lower().startswith("cudart64_") or f.lower().startswith("cublas64_") or f.lower().startswith("cudnn"):
                    add_dir_for_dlls(root)
                    break

logpath = os.path.join(tempfile.gettempdir(), "onnx_fwd_import_log.txt")

def _log(s):
    try:
        with open(logpath, "a", encoding="utf-8") as f:
            f.write(s + "\n")
    except Exception:
        pass

# Try forcing onnxruntime import immediately after DLL dirs registered
try:
    _log("Attempting to import onnxruntime early...")
    importlib.import_module("onnxruntime")
    _log("onnxruntime imported OK")
except Exception:
    _log("onnxruntime import FAILED")
    _log(traceback.format_exc())

# Now import the rest of your app (or the package that depends on onnxruntime)
try:
    # Example: import the package that earlier failed when it imported onnxruntime
    import matchypatchy  # or import the module that triggers the indirect import
    # or import mp_installer (your real application)
    # import mp_installer as app
    # if hasattr(app, 'main'): app.main()
except Exception:
    _log("Importing main app failed")
    _log(traceback.format_exc())
    raise