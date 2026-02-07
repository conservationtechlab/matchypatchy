; MatchyPatchy NSIS installer - creates venv, pip installs requirements, and creates shortcuts.
Name "MatchyPatchy"
OutFile "MatchyPatchy-Setup.exe"
; Per-user install (no admin required). Change to RequestExecutionLevel admin + SetShellVarContext all if you want system-wide install.
InstallDir "$LOCALAPPDATA\MatchyPatchy"

!include "MUI2.nsh"
!include "LogicLib.nsh"

Page directory
Page instfiles

Var PYLAUNCHER
Var PYVER_STR
Var HAS_NVIDIA_GPU

; -------------------------
; .onInit - optional checks
; -------------------------
Function .onInit
  ; Refresh environment variables to pick up PATH changes
  ReadRegStr $0 HKCU "Environment" "Path"
  ReadRegStr $1 HKLM "SYSTEM\CurrentControlSet\Control\Session Manager\Environment" "Path"
  System::Call 'kernel32::SetEnvironmentVariable(t "PATH", t "$0;$1")'
FunctionEnd

; -------------------------
; Install section
; -------------------------
Section "Install"

  ; Create install folder
  CreateDirectory "$INSTDIR"
  SetOutPath "$INSTDIR"

  ; Include pip requirements
  File "requirements.txt"
  ; Include launcher
  File "launcher.vbs"

  ; Recursively include and extract the 'matchypatchy' package directory
  DetailPrint "Installing matchypatchy files..."
  SetOutPath "$INSTDIR\matchypatchy"
  CreateDirectory "$INSTDIR\matchypatchy"
  File /r "matchypatchy\*.*"

  ; Recursively include and extract the 'assets' directory
  DetailPrint "Installing assets..."
  SetOutPath "$INSTDIR\assets"
  CreateDirectory "$INSTDIR\assets"
  File /r "assets\*.*"

  ; -------------------------------------------------------------

  ; --- Check for NVIDIA GPU ---
  DetailPrint "Checking for NVIDIA GPU..."
  StrCpy $HAS_NVIDIA_GPU "0"
  
  ; Check if nvidia-smi exists (indicates NVIDIA drivers are installed)
  nsExec::ExecToStack 'nvidia-smi --query-gpu=name --format=csv,noheader'
  Pop $0  ; exit code
  Pop $1  ; output
  
  IntCmp $0 0 0 no_nvidia_gpu no_nvidia_gpu
    ; nvidia-smi succeeded, check if output contains something
    StrLen $R0 $1
    IntCmp $R0 0 no_nvidia_gpu has_nvidia_gpu has_nvidia_gpu
  
  has_nvidia_gpu:
    StrCpy $HAS_NVIDIA_GPU "1"
    DetailPrint "NVIDIA GPU detected: $1"
    Goto gpu_check_done
  
  no_nvidia_gpu:
    DetailPrint "No NVIDIA GPU detected. Will install CPU version of dependencies."
  
  gpu_check_done:

  ; --- Require Python >= 3.12 check ---
  ; $R0 = installer log (path)
  ; $R1 = temp file for numeric version
  StrCpy $R0 "$INSTDIR\install-log.txt"
  StrCpy $R1 "$INSTDIR\py-version.txt"
  Delete "$R0"
  Delete "$R1"

  DetailPrint "Locating Python 3.12+ ..."
  
  ; Try direct path first - check if Python 3.14 exists in common location
  IfFileExists "$LOCALAPPDATA\Programs\Python\Python314\python.exe" 0 try_python313
    DetailPrint "Found Python 3.14 in LocalAppData"
    StrCpy $PYLAUNCHER "$LOCALAPPDATA\Programs\Python\Python314\python.exe"
    Goto test_python
  
  try_python313:
    IfFileExists "$LOCALAPPDATA\Programs\Python\Python313\python.exe" 0 try_python312
      DetailPrint "Found Python 3.13 in LocalAppData"
      StrCpy $PYLAUNCHER "$LOCALAPPDATA\Programs\Python\Python313\python.exe"
      Goto test_python
  
  try_python312:
    IfFileExists "$LOCALAPPDATA\Programs\Python\Python312\python.exe" 0 try_programfiles
      DetailPrint "Found Python 3.12 in LocalAppData"
      StrCpy $PYLAUNCHER "$LOCALAPPDATA\Programs\Python\Python312\python.exe"
      Goto test_python
  
  try_programfiles:
    ; Check Program Files locations
    IfFileExists "$PROGRAMFILES\Python314\python.exe" 0 try_pf_313
      DetailPrint "Found Python 3.14 in Program Files"
      StrCpy $PYLAUNCHER "$PROGRAMFILES\Python314\python.exe"
      Goto test_python
  
  try_pf_313:
    IfFileExists "$PROGRAMFILES\Python313\python.exe" 0 try_pf_312
      DetailPrint "Found Python 3.13 in Program Files"
      StrCpy $PYLAUNCHER "$PROGRAMFILES\Python313\python.exe"
      Goto test_python
  
  try_pf_312:
    IfFileExists "$PROGRAMFILES\Python312\python.exe" 0 python_not_found
      DetailPrint "Found Python 3.12 in Program Files"
      StrCpy $PYLAUNCHER "$PROGRAMFILES\Python312\python.exe"
      Goto test_python

  test_python:
    ; Test if the python.exe at the direct path works and get version
    DetailPrint "Testing Python at: $PYLAUNCHER"
    nsExec::ExecToStack '$PYLAUNCHER -c "import sys; print(sys.version_info[0]*10000 + sys.version_info[1]*100 + sys.version_info[2])"'
    Pop $0  ; exit code
    Pop $PYVER_STR  ; output
    IntCmp $0 0 parse_version python_not_found python_not_found

  python_not_found:
    MessageBox MB_OK|MB_ICONEXCLAMATION "Python 3.12 or newer was not found.$\n$\nPlease install Python 3.12+ from python.org.$\n$\nMake sure to install for all users or current user."
    Abort

  parse_version:
    ; Trim loop - remove all trailing whitespace
    trim_loop:
      StrCpy $R4 "$PYVER_STR" 1 -1  ; get last char
      StrCmp $R4 "$\r" 0 +3
        StrCpy $PYVER_STR "$PYVER_STR" -1
        Goto trim_loop
      StrCmp $R4 "$\n" 0 +3
        StrCpy $PYVER_STR "$PYVER_STR" -1
        Goto trim_loop
      StrCmp $R4 " " 0 +3
        StrCpy $PYVER_STR "$PYVER_STR" -1
        Goto trim_loop
    
    StrLen $R3 $PYVER_STR
    IntCmp $R3 0 py_version_missing 0 0
    
    ; convert $PYVER_STR to integer and compare to 3.12.0 => 31200
    IntOp $R3 $PYVER_STR + 0
    IntCmp 31200 $PYVER_STR py_version_ok py_version_ok py_version_lt

  py_version_ok:
    DetailPrint "Found Python >= 3.12 (version code: $PYVER_STR) at $PYLAUNCHER"
    Goto create_venv

  py_version_lt:
    MessageBox MB_OK|MB_ICONEXCLAMATION "Python 3 found but is older than 3.12 (detected version code: $PYVER_STR). Please install Python 3.12 or newer."
    Abort

  py_version_missing:
    MessageBox MB_OK|MB_ICONEXCLAMATION "Failed to detect Python version. Please ensure Python 3.12+ is installed correctly."
    Abort

  create_venv:
    DetailPrint "Creating virtual environment using: $PYLAUNCHER"
    ; Use the chosen launcher to create the venv
    nsExec::ExecToLog '$PYLAUNCHER -m venv "$INSTDIR\venv"'
    Pop $0
    IntCmp $0 0 venv_ok venv_failed venv_failed

  venv_ok:
    DetailPrint "Virtual environment created successfully."
    Goto venv_done

  venv_failed:
    ; Try ensurepip then retry venv creation (common on some constrained installs)
    DetailPrint "venv creation failed (exit $0). Attempting ensurepip and retry..."
    nsExec::ExecToLog '$PYLAUNCHER -m ensurepip --default-pip'
    Pop $1
    IntCmp $1 0 retry_venv venv_final_failed venv_final_failed
    
  retry_venv:
    ; ensurepip succeeded (exit 0) -> retry venv
    nsExec::ExecToLog '$PYLAUNCHER -m venv "$INSTDIR\venv"'
    Pop $0
    IntCmp $0 0 venv_ok venv_final_failed venv_final_failed

  venv_final_failed:
    MessageBox MB_OK|MB_ICONEXCLAMATION "Failed to create a Python virtual environment. Check the installer details for more information."
    Abort

  venv_done:
    ; Upgrade pip/setuptools/wheel in the venv (recommended)
    DetailPrint "Upgrading pip/setuptools/wheel inside venv..."
    nsExec::ExecToLog '"$INSTDIR\venv\Scripts\python.exe" -m pip install --upgrade pip setuptools wheel'
    Pop $0
    IntCmp $0 0 pip_ok pip_upgrade_failed pip_upgrade_failed

  pip_ok:
    DetailPrint "pip upgrade succeeded."
    Goto install_requirements

  pip_upgrade_failed:
    ; If $0 != 0 we still continue to attempt installing requirements but warn the user
    DetailPrint "Warning: pip upgrade returned exit code $0. Continuing..."

  install_requirements:
    ; Install requirements based on GPU availability
    StrCmp $HAS_NVIDIA_GPU "1" install_gpu_requirements install_cpu_requirements
  
  install_gpu_requirements:
    DetailPrint "Installing package requirements with GPU support..."
    ; First install base requirements
    nsExec::ExecToLog '"$INSTDIR\venv\Scripts\python.exe" -m pip install --no-deps chromadb>=1.3.4'
    nsExec::ExecToLog '"$INSTDIR\venv\Scripts\python.exe" -m pip install -r "$INSTDIR\requirements.txt"'
    Pop $1
    IntCmp $1 0 0 pip_install_failed pip_install_failed
    
    ; Then install CUDA dependencies
    DetailPrint "Installing NVIDIA CUDA runtime libraries..."
    nsExec::ExecToLog '"$INSTDIR\venv\Scripts\python.exe" -m pip install nvidia-cuda-runtime-cu12 nvidia-cudnn-cu12'
    Pop $1
    IntCmp $1 0 pip_success pip_install_failed pip_install_failed
  
  install_cpu_requirements:
    DetailPrint "Installing package requirements (CPU version)..."
    ; Install requirements, replacing any GPU packages with CPU versions
    nsExec::ExecToLog '"$INSTDIR\venv\Scripts\python.exe" -m pip install --no-deps chromadb>=1.3.4'
    nsExec::ExecToLog '"$INSTDIR\venv\Scripts\python.exe" -m pip install -r "$INSTDIR\requirements.txt"'
    Pop $1
    IntCmp $1 0 0 pip_install_failed pip_install_failed
    
    ; If requirements.txt has onnxruntime-gpu, replace it with CPU version
    DetailPrint "Ensuring CPU-only versions of dependencies..."
    nsExec::ExecToLog '"$INSTDIR\venv\Scripts\python.exe" -m pip uninstall -y onnxruntime-gpu'
    nsExec::ExecToLog '"$INSTDIR\venv\Scripts\python.exe" -m pip install --force-reinstall onnxruntime'
    Pop $1
    IntCmp $1 0 pip_success pip_install_failed pip_install_failed

  pip_success:
    DetailPrint "Requirements installed successfully."
    Goto PipDone

  pip_install_failed:
    MessageBox MB_OK|MB_ICONEXCLAMATION "Failed to install Python requirements (exit code $1). Check the installer details for more information."
    Abort

  PipDone:
    ; continue with install of matchypatchy
    DetailPrint "Installing packaged project from $INSTDIR\matchypatchy (log: $R0)..."

    ; Recommended for production: non-editable installation from directory (builds a wheel)
    nsExec::ExecToLog '"$INSTDIR\venv\Scripts\python.exe" -m pip install --no-deps -e "$INSTDIR\\matchypatchy"'
    Pop $0
    IntCmp $0 0 install_local_ok install_local_failed install_local_failed

    install_local_ok:
      DetailPrint "Local package installed successfully."
      Goto local_done

    install_local_failed:
      ; Optionally try an editable install (useful during development)
      DetailPrint "Install from directory failed (exit $0). Attempting editable install (-e) as fallback..."
      nsExec::ExecToLog '"$INSTDIR\venv\Scripts\python.exe" -m pip install --no-deps -e "$INSTDIR\\matchypatchy"'
      Pop $1
      IntCmp $1 0 install_local_ok install_local_final_failed install_local_final_failed

    install_local_final_failed:
      MessageBox MB_OK|MB_ICONEXCLAMATION "Failed to install the packaged project from $INSTDIR\\matchypatchy (see $R0 for pip output). The installer will abort."
      Abort

    local_done:
      ; (continue)
      StrCpy $R2 "" ; clear helper var

    ; Write uninstaller
    WriteUninstaller "$INSTDIR\Uninstall.exe"

    ; Start Menu shortcut
    CreateDirectory "$SMPROGRAMS\MatchyPatchy"
    ; create shortcut that points directly at the .vbs file (no explicit wscript.exe)
      CreateShortCut "$DESKTOP\MatchyPatchy.lnk" "$INSTDIR\launcher.vbs" "" "$INSTDIR\assets\graphics\desktop_icon.png" 0
      CreateShortCut "$SMPROGRAMS\MatchyPatchy\MatchyPatchy.lnk" "$INSTDIR\launcher.vbs" "" "$INSTDIR\assets\graphics\desktop_icon.png" 0

    DetailPrint "Installation complete."

SectionEnd

; -------------------------
; Uninstall section
; -------------------------
Section "Uninstall"

  ; Remove shortcuts and start menu folder
  Delete "$DESKTOP\MatchyPatchy.lnk"
  Delete "$SMPROGRAMS\MatchyPatchy\MatchyPatchy.lnk"
  RMDir "$SMPROGRAMS\MatchyPatchy"

  ; Remove files - adjust if you embed more files
  Delete "$INSTDIR\runner.vbs"
  Delete "$INSTDIR\main.py"
  Delete "$INSTDIR\requirements.txt"
  RMDir /r "$INSTDIR\venv"
  ; If you included an assets folder, remove it as well
  RMDir /r "$INSTDIR\assets"
  RMDir /r "$INSTDIR\matchypatchy"

  Delete "$INSTDIR\Uninstall.exe"
  RMDir /r "$INSTDIR"

SectionEnd

; -------------------------
; Optional: show installation log (useful for debugging)
; -------------------------
!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
!insertmacro MUI_FUNCTION_DESCRIPTION_END