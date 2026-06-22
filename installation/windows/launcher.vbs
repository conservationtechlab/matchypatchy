Option Explicit
' launcher.vbs - robust launcher for venv/pythonw
' Sets CWD to the install folder and launches __main__.py with pythonw (or python/pyw fallback).
' Writes errors to launcher.log and shows a message box if launch fails.

Dim fso, wsh, scriptPath, scriptDir, pythonwPath, pythonPath, cmd, logPath
Set fso = CreateObject("Scripting.FileSystemObject")
Set wsh = CreateObject("WScript.Shell")

scriptPath = WScript.ScriptFullName
scriptDir = fso.GetParentFolderName(scriptPath)
logPath = scriptDir & "\launcher.log"

' Set working directory to install folder
wsh.CurrentDirectory = scriptDir

' Build candidate python executables
pythonwPath = scriptDir & "\venv\Scripts\pythonw.exe"
pythonPath  = scriptDir & "\venv\Scripts\python.exe"

' Prepare command to run __main__.py
If fso.FileExists(pythonwPath) Then
  cmd = """" & pythonwPath & """ -m matchypatchy"
ElseIf fso.FileExists(pythonPath) Then
  ' fallback to python (will show a console if used)
  cmd = """" & pythonPath & """ -m matchypatchy"
Else
  ' final fallback: try Python launcher on PATH
  cmd = "pyw -3 -m matchypatchy"
End If

' Attempt to run the command hidden (0 = hidden window). Do not wait for it to finish (False).
On Error Resume Next
wsh.Run cmd, 0, False
If Err.Number <> 0 Then
  Dim errMsg, tf
  errMsg = "Failed to launch application." & vbCrLf & _
           "Command: " & cmd & vbCrLf & _
           "Error: " & Err.Number & " - " & Err.Description & vbCrLf & _
           "Check that Python and the venv exist."

  ' Show error to user
  MsgBox errMsg, vbExclamation, "Launcher error"

  ' Append error to launcher.log for diagnostics
  On Error Resume Next
  Set tf = fso.OpenTextFile(logPath, 8, True) ' 8 = ForAppending
  If Err.Number = 0 Then
    tf.WriteLine Now & " - " & errMsg
    tf.Close
  End If

  WScript.Quit 1
End If

' Optionally write a small "launched" entry to the log
On Error Resume Next
Set tf = fso.OpenTextFile(logPath, 8, True)
If Err.Number = 0 Then
  tf.WriteLine Now & " - Launched: " & cmd
  tf.Close
End If