; MatchyPatchy Windows installer (per-user, no admin rights needed).
;
; Ships a ready-made Python environment: the official embeddable Python with
; pip and all pinned requirements already installed at build time (in CI), so
; installing needs no internet connection.
;
; Build (from the folder holding the files listed below):
;   makensis /DVARIANT=cpu /DAPP_VERSION=X.Y.Z MatchyPatchy.nsi
;
; Files expected next to this script:
;   python_env\        embeddable Python with site-packages already populated
;                      (python312._pth in place, Scripts\ folder removed)
;   launcher.vbs
;   matchypatchy.ico

; Must come before any File instruction. Solid LZMA gives the best compression
; for the large Python environment and keeps the installer under the 2 GB limit.
; SetCompressor /SOLID lzma

!ifndef VARIANT
  !define VARIANT "cpu"
!endif
!ifndef APP_VERSION
  !define APP_VERSION "0.2.4"
!endif

!define UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\MatchyPatchy"

Unicode true
Name "MatchyPatchy"
OutFile "matchypatchy-v${APP_VERSION}-win-${VARIANT}-setup.exe"
InstallDir "$LOCALAPPDATA\MatchyPatchy"
; Per-user install. Stated explicitly so Windows doesn't guess (and show a UAC
; prompt) just because the file name contains "setup".
RequestExecutionLevel user

!include "MUI2.nsh"
!include "LogicLib.nsh"

!define MUI_ICON "matchypatchy.ico"
!define MUI_UNICON "matchypatchy.ico"

!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_INSTFILES
!define MUI_FINISHPAGE_RUN
!define MUI_FINISHPAGE_RUN_TEXT "Launch MatchyPatchy"
!define MUI_FINISHPAGE_RUN_FUNCTION LaunchApp
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

; -------------------------
; Helpers
; -------------------------
Function LaunchApp
  SetOutPath "$INSTDIR"
  ExecShell "open" "$INSTDIR\launcher.vbs"
FunctionEnd

; Report a failed step, remove the half-installed environment and stop the install
Function FailInstall
  Pop $1
  RMDir /r "$INSTDIR\python_env"
  MessageBox MB_OK|MB_ICONSTOP|MB_SETFOREGROUND \
    "$1$\n$\nThe installation files may be damaged or blocked by antivirus software.$\nTry downloading the installer again. The Details view shows the full error." \
    /SD IDOK
  Abort "Installation failed."
FunctionEnd

; -------------------------
; .onInit - detect an existing installation
; -------------------------
Function .onInit
  ReadRegStr $R0 HKCU "Software\MatchyPatchy" "Install_Dir"
  ReadRegStr $R1 HKCU "Software\MatchyPatchy" "Version"

  ${If} $R0 != ""
    ${If} $R1 != ""
      MessageBox MB_YESNO|MB_ICONQUESTION \
        "MatchyPatchy (version $R1) is already installed at:$\n$\n$R0$\n$\nDo you want to update to version ${APP_VERSION}?" \
        /SD IDYES IDYES use_existing
    ${Else}
      MessageBox MB_YESNO|MB_ICONQUESTION \
        "MatchyPatchy is already installed at:$\n$\n$R0$\n$\nDo you want to update/reinstall (version ${APP_VERSION})?" \
        /SD IDYES IDYES use_existing
    ${EndIf}
    Abort

    use_existing:
      StrCpy $INSTDIR $R0
  ${EndIf}
FunctionEnd

; -------------------------
; Main section (always installed)
; -------------------------
Section "MatchyPatchy ${APP_VERSION} (${VARIANT})" SEC_MAIN
  SectionIn RO

  CreateDirectory "$INSTDIR"
  SetOutPath "$INSTDIR"

  ; Update/reinstall starts clean: the whole environment is replaced
  RMDir /r "$INSTDIR\python_env"

  File "launcher.vbs"
  File "matchypatchy.ico"

  ; --- Python runtime with all packages already installed ---
  DetailPrint "Installing Python environment (this can take a minute)..."
  SetOutPath "$INSTDIR\python_env"
  File /r "python_env\*.*"
  SetOutPath "$INSTDIR"

  ; --- confirm the app itself is installed ---
  nsExec::ExecToLog `"$INSTDIR\python_env\python.exe" -c "import importlib.metadata as m; print('matchypatchy', m.version('matchypatchy'))"`
  Pop $0
  ${If} $0 != "0"
    Push "MatchyPatchy was not found in the installed Python environment."
    Call FailInstall
  ${EndIf}

  ; --- uninstaller and registry (written last, so a failed install isn't registered) ---
  WriteUninstaller "$INSTDIR\Uninstall.exe"

  WriteRegStr HKCU "Software\MatchyPatchy" "Version" "${APP_VERSION}"
  WriteRegStr HKCU "Software\MatchyPatchy" "Install_Dir" "$INSTDIR"

  WriteRegStr HKCU "${UNINST_KEY}" "DisplayName" "MatchyPatchy"
  WriteRegStr HKCU "${UNINST_KEY}" "DisplayVersion" "${APP_VERSION}"
  WriteRegStr HKCU "${UNINST_KEY}" "Publisher" "Conservation Technology Lab"
  WriteRegStr HKCU "${UNINST_KEY}" "DisplayIcon" "$INSTDIR\matchypatchy.ico"
  WriteRegStr HKCU "${UNINST_KEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "${UNINST_KEY}" "UninstallString" "$\"$INSTDIR\Uninstall.exe$\""
  WriteRegDWORD HKCU "${UNINST_KEY}" "NoModify" 1
  WriteRegDWORD HKCU "${UNINST_KEY}" "NoRepair" 1

  DetailPrint "Installation complete."
SectionEnd

; -------------------------
; Optional components
; -------------------------
Section "Desktop Shortcut" SEC_DESKTOP
  SetOutPath "$INSTDIR"
  CreateShortCut "$DESKTOP\MatchyPatchy.lnk" "$INSTDIR\launcher.vbs" "" \
    "$INSTDIR\matchypatchy.ico" 0 SW_SHOWNORMAL "" "MatchyPatchy"
SectionEnd

Section "Start Menu Shortcuts" SEC_STARTMENU
  SetOutPath "$INSTDIR"
  CreateDirectory "$SMPROGRAMS\MatchyPatchy"
  CreateShortCut "$SMPROGRAMS\MatchyPatchy\MatchyPatchy.lnk" "$INSTDIR\launcher.vbs" "" \
    "$INSTDIR\matchypatchy.ico" 0 SW_SHOWNORMAL "" "MatchyPatchy"
  CreateShortCut "$SMPROGRAMS\MatchyPatchy\Uninstall.lnk" "$INSTDIR\Uninstall.exe"
SectionEnd

!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_MAIN} "MatchyPatchy and its Python environment (required)."
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_DESKTOP} "Create a shortcut on the desktop"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_STARTMENU} "Create shortcuts in the Start Menu"
!insertmacro MUI_FUNCTION_DESCRIPTION_END

; -------------------------
; Uninstall
; -------------------------
Section "Uninstall"
  Delete "$DESKTOP\MatchyPatchy.lnk"
  Delete "$SMPROGRAMS\MatchyPatchy\MatchyPatchy.lnk"
  Delete "$SMPROGRAMS\MatchyPatchy\Uninstall.lnk"
  RMDir "$SMPROGRAMS\MatchyPatchy"

  ; The Python environment (including all installed packages)
  RMDir /r "$INSTDIR\python_env"

  Delete "$INSTDIR\launcher.vbs"
  Delete "$INSTDIR\matchypatchy.ico"
  Delete "$INSTDIR\launcher.log"
  Delete "$INSTDIR\matchypatchy.log*"
  Delete "$INSTDIR\Uninstall.exe"
  RMDir "$INSTDIR"

  DeleteRegKey HKCU "Software\MatchyPatchy"
  DeleteRegKey HKCU "${UNINST_KEY}"
SectionEnd
