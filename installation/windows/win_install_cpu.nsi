; MatchyPatchy NSIS installer - creates venv, pip installs requirements, and creates shortcuts.

; Version constant - update this for each release
!define APP_VERSION "0.1.1"

Name "MatchyPatchy"
OutFile "MatchyPatchy-Setup.exe"
; Per-user install (no admin required). Change to RequestExecutionLevel admin + SetShellVarContext all if you want system-wide install.
InstallDir "$LOCALAPPDATA\MatchyPatchy"

!include "MUI2.nsh"
!include "LogicLib.nsh"

Page directory
Page components
Page instfiles

Var PYLAUNCHER
Var PYVER_STR

; -------------------------
; .onInit - optional checks
; -------------------------
Function .onInit
  ; Refresh environment variables to pick up PATH changes
  ReadRegStr $0 HKCU "Environment" "Path"
  ReadRegStr $1 HKLM "SYSTEM\CurrentControlSet\Control\Session Manager\Environment" "Path"
  System::Call 'kernel32::SetEnvironmentVariable(t "PATH", t "$0;$1")'

    ; Check for existing installation
  ReadRegStr $R0 HKCU "Software\MatchyPatchy" "Install_Dir"
  ReadRegStr $R1 HKCU "Software\MatchyPatchy" "Version"
  
  ${If} $R0 != ""
    ; Installation exists, show update prompt
    ${If} $R1 != ""
      MessageBox MB_YESNO|MB_ICONQUESTION "MatchyPatchy (version $R1) is already installed at:$\n$\n$R0$\n$\nDo you want to update to version ${APP_VERSION}?" IDNO abort_install
    ${Else}
      MessageBox MB_YESNO|MB_ICONQUESTION "MatchyPatchy is already installed at:$\n$\n$R0$\n$\nDo you want to update/reinstall (version ${APP_VERSION})?" IDNO abort_install
    ${EndIf}
    
    ; User clicked YES, use existing installation directory
    StrCpy $INSTDIR $R0
    Goto end_version_check
    
    abort_install:
      ; User clicked NO, abort installation
      Abort
    
    end_version_check:
  ${EndIf}
FunctionEnd

; -------------------------
; Install section (MAIN - always runs)
; -------------------------
Section "Install MatchyPatchy ${APP_VERSION}" SEC_MAIN
  SectionIn RO  ; This section is required (read-only, can't be unchecked)
  AddSize 1450000

  ; Create install folder
  CreateDirectory "$INSTDIR"
  SetOutPath "$INSTDIR"

  ; Include pip requirements and launcher
  File "installation\windows\win_py312_cu12_requirements.txt"
  File "installation\windows\win_py313_cu12_requirements.txt"
  File "installation\windows\launcher.vbs"

  ; Recursively include and extract the 'matchypatchy' package directory
  DetailPrint "Installing matchypatchy files..."
  SetOutPath "$INSTDIR\matchypatchy"
  CreateDirectory "$INSTDIR\matchypatchy"
  File /r "matchypatchy_package\*.*"

  ; Recursively include and extract the 'assets' directory
  DetailPrint "Installing assets..."
  SetOutPath "$INSTDIR\assets"
  CreateDirectory "$INSTDIR\assets"
  File /r "assets\*.*"

  ; Include wheels
  DetailPrint "Installing Python 3.12 wheels..."
  SetOutPath "$INSTDIR\wheels"
  CreateDirectory "$INSTDIR\wheels"
  File /r "installation\windows\wheels\default\*.*"

  ; -------------------------------------------------------------
  ; --- Require Python >= 3.12 check ---
  ; $R0 = installer log (path)
  ; $R1 = temp file for numeric version
  StrCpy $R0 "$INSTDIR\install-log.txt"
  StrCpy $R1 "$INSTDIR\py-version.txt"
  Delete "$R0"
  Delete "$R1"

  DetailPrint "Locating Python 3.12+ ..."
  
  ; Try direct path first - check if Python 3.13 exists in common location
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
    Goto select_wheels

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

  select_wheels:
    ; Determine which wheels to use based on detected Python version
    ${If} $PYVER_STR >= 31300
      DetailPrint "Using Python 3.13 wheels..."
      StrCpy $R5 "$INSTDIR\wheels"
      ; StrCpy $R6 "$INSTDIR\win_py13_cpu_requirements.txt"
    ${Else}
      DetailPrint "Using Python 3.12 wheels..."
      StrCpy $R5 "$INSTDIR\wheels"
      StrCpy $R6 "$INSTDIR\win_py12_cpu_requirements.txt"
    ${EndIf}
  Goto install_requirements

  install_requirements:
    DetailPrint "Installing package requirements (CPU version)..."
    ; Install requirements without
    nsExec::ExecToLog '"$INSTDIR\venv\Scripts\python.exe" -m pip install -r "$INSTDIR\requirements.txt"'
    Pop $1
    IntCmp $1 0 PipDone pip_install_failed pip_install_failed

  pip_install_failed:
    MessageBox MB_OK|MB_ICONEXCLAMATION "Failed to install Python requirements (exit code $1). Check the installer details for more information."
    Abort

  PipDone:
    ; continue with install of matchypatchy
    DetailPrint "Requirements installed successfully."
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

    ; Write registry keys for version tracking and Add/Remove Programs
    WriteRegStr HKCU "Software\MatchyPatchy" "Version" "${APP_VERSION}"
    WriteRegStr HKCU "Software\MatchyPatchy" "Install_Dir" "$INSTDIR"

    ; Register in Add/Remove Programs
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\MatchyPatchy" "DisplayName" "MatchyPatchy"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\MatchyPatchy" "DisplayVersion" "${APP_VERSION}"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\MatchyPatchy" "Publisher" "Conservation Technology Lab"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\MatchyPatchy" "UninstallString" "$INSTDIR\Uninstall.exe"
    WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\MatchyPatchy" "NoModify" 1
    WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\MatchyPatchy" "NoRepair" 1
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\MatchyPatchy" "DisplayIcon" "$INSTDIR\assets\graphics\desktop_icon.ico"

    DetailPrint "Installation complete."

SectionEnd

; -------------------------
; Optional Components
; -------------------------
Section "Desktop Shortcut" SEC_DESKTOP
  CreateShortCut "$DESKTOP\MatchyPatchy.lnk" "$INSTDIR\launcher.vbs" "" "$INSTDIR\assets\graphics\desktop_icon.ico" 0
SectionEnd

Section "Start Menu Shortcuts" SEC_STARTMENU
  CreateDirectory "$SMPROGRAMS\MatchyPatchy"
  CreateShortCut "$SMPROGRAMS\MatchyPatchy\MatchyPatchy.lnk" "$INSTDIR\launcher.vbs" "" "$INSTDIR\assets\graphics\desktop_icon.ico" 0
  CreateShortCut "$SMPROGRAMS\MatchyPatchy\Uninstall.lnk" "$INSTDIR\Uninstall.exe" "" "$INSTDIR\Uninstall.exe" 0
SectionEnd

; Section descriptions (shown in component selection page)
!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_MAIN} "MatchyPatchy application files (required)"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_DESKTOP} "Create a shortcut on the desktop"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_STARTMENU} "Create shortcuts in the Start Menu"
!insertmacro MUI_FUNCTION_DESCRIPTION_END

; -------------------------
; Uninstall section
; -------------------------
Section "Uninstall"

  ; Remove shortcuts and start menu folder
  Delete "$DESKTOP\MatchyPatchy.lnk"
  Delete "$SMPROGRAMS\MatchyPatchy\MatchyPatchy.lnk"
  Delete "$SMPROGRAMS\MatchyPatchy\Uninstall.lnk"
  RMDir "$SMPROGRAMS\MatchyPatchy"

  ; Remove files
  Delete "$INSTDIR\launcher.vbs"
  Delete "$INSTDIR\requirements.txt"
  Delete "$INSTDIR\LICENSE"
  Delete "$INSTDIR\README.md"
  Delete "$INSTDIR\ABOUT.md"
  Delete "$INSTDIR\install-log.txt"
  Delete "$INSTDIR\py-version.txt"
  Delete "$INSTDIR\installer-path.txt"
  Delete "$INSTDIR\where-nvidia.txt"
  Delete "$INSTDIR\launcher.log"
  
  ; Remove directories
  RMDir /r "$INSTDIR\venv"
  RMDir /r "$INSTDIR\assets"
  RMDir /r "$INSTDIR\matchypatchy"

  Delete "$INSTDIR\Uninstall.exe"
  RMDir "$INSTDIR"

  ; Remove registry keys
  DeleteRegKey HKCU "Software\MatchyPatchy"
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\MatchyPatchy"

SectionEnd