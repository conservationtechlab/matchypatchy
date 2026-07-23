; MatchyPatchy NSIS installer - creates venv, pip installs requirements, and creates shortcuts.

; Version constant - update this for each release
!define APP_VERSION "0.1.4"

Name "MatchyPatchy"
OutFile "MatchyPatchy-v0.1.4-GPU-Setup.exe"
; Per-user install (no admin required)
InstallDir "$LOCALAPPDATA\MatchyPatchy"

!include "MUI2.nsh"
!include "LogicLib.nsh"

Page directory
Page components
Page instfiles

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

  ; Create install folder
  CreateDirectory "$INSTDIR"
  SetOutPath "$INSTDIR"

  ; Include pip requirements and launcher
  File "installation\windows\launcher.vbs"

  ; Include python
  DetailPrint "Installing Python 3.13.."
  SetOutPath "$INSTDIR\python_env"
  CreateDirectory "$INSTDIR\python_env"
  File /r "installation\windows\python_env_gpu\*.*"

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
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\MatchyPatchy" "DisplayIcon" "$INSTDIR\Lib\site_packages\matchypatchy\assets\graphics\desktop_icon.ico"

  DetailPrint "Installation complete."

SectionEnd

; -------------------------
; Optional Components
; -------------------------
Section "Desktop Shortcut" SEC_DESKTOP
  CreateShortCut "$DESKTOP\MatchyPatchy.lnk" \
    "$INSTDIR\launcher.vbs" \
    "" \
    "$INSTDIR\python_env\Lib\site_packages\matchypatchy\assets\graphics\desktop_icon.ico" \
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
    "$INSTDIR\Lib\site_packages\matchypatchy\assets\graphics\desktop_icon.ico" \
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
  Delete "$INSTDIR\matchypatchy.log"
  Delete "$INSTDIR\launcher.log"
  RMDir /r "$INSTDIR\python_env"

  Delete "$INSTDIR\Uninstall.exe"
  RMDir "$INSTDIR"

  ; Remove registry keys
  DeleteRegKey HKCU "Software\MatchyPatchy"
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\MatchyPatchy"

SectionEnd