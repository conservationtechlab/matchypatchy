!include LogicLib.nsh
!include MUI2.nsh

!define APP_NAME "MatchyPatchy"
!define APP_FOLDER_NAME "MatchyPatchy"         ; must match folder name next to installer
!define EXE_NAME "MatchyPatchy.exe"               ; entry-point executable
!define INSTALL_DIR "$PROGRAMFILES\${APP_NAME}"

Name "${APP_NAME}"
OutFile "${APP_NAME}_Installer.exe"
InstallDir "${INSTALL_DIR}"
RequestExecutionLevel admin


Page directory
Page components
Page instfiles
UninstPage uninstConfirm
UninstPage instfiles

Var result
Var output

Section "Install"
    ; Set install destination
    SetOutPath "$INSTDIR"
    
    DetailPrint "Copying application files..."
    nsExec::ExecToLog 'cmd.exe /C "xcopy /E /I /Y  $EXEDIR\${APP_FOLDER_NAME}\* $INSTDIR"'

    ; Save install location to registry
    WriteRegStr HKLM "Software\${APP_NAME}" "Install_Dir" "$INSTDIR"

    ; Write uninstaller
    WriteUninstaller "$INSTDIR\Uninstall.exe"
SectionEnd

Section "Create Desktop Shortcut" SecDesktop
    SectionIn 1
    DetailPrint "Creating desktop shortcut..."
    CreateShortCut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\${EXE_NAME}"
SectionEnd

Section "Create Start Menu Shortcuts" SecStartMenu
    SectionIn 1
    DetailPrint "Creating start menu shortcuts..."
    CreateDirectory "$SMPROGRAMS\${APP_NAME}"
    CreateShortCut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" "$INSTDIR\${EXE_NAME}"
    CreateShortCut "$SMPROGRAMS\${APP_NAME}\Uninstall.lnk" "$INSTDIR\Uninstall.exe"
SectionEnd

; Section descriptions
!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
    !insertmacro MUI_DESCRIPTION_TEXT ${SecDesktop} "Create a shortcut on the desktop"
    !insertmacro MUI_DESCRIPTION_TEXT ${SecStartMenu} "Create shortcuts in the Start Menu"
!insertmacro MUI_FUNCTION_DESCRIPTION_END

Section "Uninstall"
    Delete "$INSTDIR\${EXE_NAME}"
    Delete "$INSTDIR\Uninstall.exe"
    RMDir /r "$INSTDIR"

    ; Delete desktop shortcut if it exists
    IfFileExists "$DESKTOP\${APP_NAME}.lnk" 0 +2
        Delete "$DESKTOP\${APP_NAME}.lnk"
    
    ; Delete start menu shortcuts if they exist
    IfFileExists "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" 0 +2
        Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"
    IfFileExists "$SMPROGRAMS\${APP_NAME}\Uninstall.lnk" 0 +2
        Delete "$SMPROGRAMS\${APP_NAME}\Uninstall.lnk"
    RMDir "$SMPROGRAMS\${APP_NAME}"

    DeleteRegKey HKLM "Software\${APP_NAME}"
SectionEnd
