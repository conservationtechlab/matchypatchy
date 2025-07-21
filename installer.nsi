# Name of the installer
Outfile "MatchyPatchy.exe"

# Name to use in Start Menu and Program Files
InstallDir "$PROGRAMFILES\MatchyPatchy"

# Default installation directory
InstallDirRegKey HKLM "Software\MatchyPatchy" "InstallDir"

# Request admin privileges
RequestExecutionLevel admin

# Pages to show
Page directory
Page instfiles
UninstPage uninstConfirm
UninstPage instfiles

# Installer section
Section "Install"

  SetOutPath $INSTDIR

  # Save install path for uninstaller
  WriteRegStr HKLM "Software\MatchyPatchy" "InstallDir" "$INSTDIR"

  # Copy all files from dist folder
  File /r "dist\*.*"

  # Create a shortcut in Start Menu
  CreateDirectory "$SMPROGRAMS\MatchyPatchy"
  CreateShortCut "$SMPROGRAMS\MatchyPatchy\MatchyPatchy.lnk" "$INSTDIR\MatchyPatchy.exe"

  # Write uninstaller
  WriteUninstaller "$INSTDIR\Uninstall.exe"

SectionEnd

# Uninstaller section
Section "Uninstall"

  Delete "$SMPROGRAMS\MatchyPatchy\MatchyPatchy.lnk"
  RMDir /r "$SMPROGRAMS\MatchyPatchy"

  RMDir /r "$INSTDIR"

  DeleteRegKey HKLM "Software\MatchyPatchy"

SectionEnd
