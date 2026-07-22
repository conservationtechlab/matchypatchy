; MatchyPatchy NSIS installer - creates venv, pip installs requirements, and creates shortcuts.

; Version constant - update this for each release
!define APP_VERSION "0.1.4"

Name "MatchyPatchy"
OutFile "MatchyPatchy-v0.1.4-GPU-Setup.exe"
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
  AddSize 3015000;

  ; Create install folder
  CreateDirectory "$INSTDIR"
  SetOutPath "$INSTDIR"

  ; Include pip requirements
  File "installation\windows\win_py312_cpu_requirements.txt"
  File "installation\windows\win_py313_cpu_requirements.txt"
  File "installation\windows\win_cuda12_requirements.txt"
  File "installation\windows\launcher.vbs"
  File "ABOUT.md"
  File "README.md"
  File "LICENSE"

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
  File /r "installation\windows\wheels\*.*"

  ; Include python
  DetailPrint "Installing Python 3.13.."
  SetOutPath "$INSTDIR\python"
  CreateDirectory "$INSTDIR\python"
  File /r "installation\windows\python-portable\*.*"

  ; Include wheels
  DetailPrint "Copying dependencies..."
  SetOutPath "$INSTDIR\wheels"
  CreateDirectory "$INSTDIR\wheels"
  File /r "installation\windows\wheels\*.*"

  ; -------------------------------------------------------------
  ; Begin Install
  DetailPrint "Installing dependencies..."
  StrCpy $R5 "$INSTDIR\wheels"
  StrCpy $R6 "$INSTDIR\win_cpu_requirements.txt"
  ExecToLog "$INSTDIR\python\python.exe -m pip install --no-index --find-links "$R5" -r "$R6"'
  Pop $0
  IntCmp $0 0 install_onnxruntime_gpu pip_install_failed pip_install_failed

  install_onnxruntime_gpu:
    DetailPrint "Installing GPU requirements.."
    
    ; Uninstall CPU version
    DetailPrint "Uninstalling onnxruntime (CPU)..."
    nsExec::ExecToLog '"$INSTDIR\venv\Scripts\python.exe" -m pip uninstall -y onnxruntime'
    Pop $0
    ; Ignore errors
  
    ; Install GPU version
    DetailPrint "Installing onnxruntime-gpu..."
    nsExec::ExecToLog '"$INSTDIR\venv\Scripts\python.exe" -m pip install -r "$INSTDIR\win_cuda12_requirements.txt"'
    Pop $1
    IntCmp $1 0 install_mp pip_install_failed pip_install_failed

  pip_install_failed:
    MessageBox MB_OK|MB_ICONEXCLAMATION "Failed to install Python requirements online (exit code $1). Check the installer details for more information."
    Abort

  install_mp:
    ; continue with install of matchypatchy
    DetailPrint "Requirements installed successfully."
    DetailPrint "Installing packaged project from $INSTDIR\matchypatchy (log: $R0)..."

    ; Recommended for production: non-editable installation from directory (builds a wheel)
    nsExec::ExecToLog '"$INSTDIR\venv\Scripts\python.exe" -m pip install --no-deps -e "$INSTDIR\\matchypatchy"'
    Pop $0
    IntCmp $0 0 install_mp_ok install_mp_failed install_mp_failed

  install_mp_ok:
      DetailPrint "MatchyPatchy package installed successfully."
      Goto local_done

  install_mp_failed:
      MessageBox MB_OK|MB_ICONEXCLAMATION "Failed to install from $INSTDIR\\matchypatchy (see $R0 for pip output). The installer will abort."
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
  CreateShortCut "$DESKTOP\MatchyPatchy.lnk" \
    "$INSTDIR\launcher.vbs" \
    "" \
    "$INSTDIR\assets\graphics\desktop_icon.ico" \
    0 \
    SW_SHOWNORMAL \
    "" \
    "$INSTDIR"
SectionEnd

Section "Start Menu Shortcuts" SEC_STARTMENU
  CreateDirectory "$SMPROGRAMS\MatchyPatchy"
  CreateShortCut "$SMPROGRAMS\MatchyPatchy\MatchyPatchy.lnk" \
    "$INSTDIR\launcher.vbs" \
    "" \
    "$INSTDIR\assets\graphics\desktop_icon.ico" \
    0 \
    SW_SHOWNORMAL \
    "" \
    "$INSTDIR"
  
  CreateShortCut "$SMPROGRAMS\MatchyPatchy\Uninstall.lnk" "$INSTDIR\Uninstall.exe"
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
  Delete "$INSTDIR\win_py312_cu12_requirements.txt"
  Delete "$INSTDIR\win_py313_cu12_requirements.txt"
  Delete "$INSTDIR\matchypatchy.log"
  Delete "$INSTDIR\launcher.log"
  
  ; Remove directories
  RMDir /r "$INSTDIR\venv"
  RMDir /r "$INSTDIR\assets"
  RMDir /r "$INSTDIR\wheels"
  RMDir /r "$INSTDIR\matchypatchy"

  Delete "$INSTDIR\Uninstall.exe"
  RMDir "$INSTDIR"

  ; Remove registry keys
  DeleteRegKey HKCU "Software\MatchyPatchy"
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\MatchyPatchy"

SectionEnd