Option Explicit
' launcher.vbs - runs the bundled Python hidden, logging all output to
' %LOCALAPPDATA%\MatchyPatchy\launcher.log

Dim fso, wsh, scriptDir, dataDir, logPath, pythonPath, cmd, rc, q
Set fso = CreateObject("Scripting.FileSystemObject")
Set wsh = CreateObject("WScript.Shell")
q = Chr(34)

scriptDir  = fso.GetParentFolderName(WScript.ScriptFullName)
pythonPath = scriptDir & "\python_env\python.exe"

' Per-user, writable location (the install dir is not writable)
dataDir = wsh.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\MatchyPatchy"
If Not fso.FolderExists(dataDir) Then fso.CreateFolder dataDir
logPath = dataDir & "\launcher.log"

' Simple rotation at 5 MB
If fso.FileExists(logPath) Then
    If fso.GetFile(logPath).Size > 5242880 Then
        If fso.FileExists(logPath & ".1") Then fso.DeleteFile logPath & ".1"
        fso.MoveFile logPath, logPath & ".1"
    End If
End If

Sub Log(msg)
    Dim tf
    On Error Resume Next
    Set tf = fso.OpenTextFile(logPath, 8, True)   ' 8 = ForAppending
    If Err.Number = 0 Then
        tf.WriteLine Now & " - " & msg
        tf.Close
    End If
    On Error GoTo 0
End Sub

If Not fso.FileExists(pythonPath) Then
    Log "ERROR: bundled Python not found: " & pythonPath
    MsgBox "MatchyPatchy's Python environment was not found in:" & vbCrLf & _
           scriptDir & "\python_env" & vbCrLf & vbCrLf & _
           "Please reinstall MatchyPatchy.", vbExclamation, "Launcher error"
    WScript.Quit 1
End If

' matchypatchy.log is written relative to the working directory
wsh.CurrentDirectory = dataDir
With wsh.Environment("Process")
    .Item("PYTHONNOUSERSITE")   = "1"
    .Item("PYTHONFAULTHANDLER") = "1"
    .Item("PYTHONUNBUFFERED")   = "1"
End With

Log "=== Launching (install dir: " & scriptDir & ") ==="

' cmd /c lets us redirect stdout+stderr; the doubled outer quotes are required
cmd = "cmd /c " & q & q & pythonPath & q & " -m matchypatchy >> " & q & logPath & q & " 2>&1" & q

rc = wsh.Run(cmd, 0, True)    ' 0 = hidden window, True = wait for exit
Log "Exited with code " & rc

If rc <> 0 Then
    MsgBox "MatchyPatchy exited unexpectedly (code " & rc & ")." & vbCrLf & vbCrLf & _
           "Details are in:" & vbCrLf & logPath, vbExclamation, "MatchyPatchy"
End If
WScript.Quit rc
