Option Explicit
' runner.vbs - robust launcher for venv/pythonw
' Sets CWD to the install folder and launches main.py with pythonw (or python/pyw fallback).
' Writes errors to runner.log and shows a message box if launch fails.

Dim fso, wsh, scriptPath, scriptDir, pythonwPath, pythonPath, cmd, logPath
Set fso = CreateObject("Scripting.FileSystemObject")
Set wsh = CreateObject("WScript.Shell")

scriptPath = WScript.ScriptFullName
scriptDir = fso.GetParentFolderName(scriptPath)
logPath = scriptDir & "\runner.log"

' Build candidate python executables
pythonwPath = scriptDir & "\venv\Scripts\pythonw.exe"
pythonPath  = scriptDir & "\venv\Scripts\python.exe"

' Prepare command to run main.py
If fso.FileExists(pythonwPath) Then
  cmd = """" & pythonwPath & """ """ & scriptDir & "\matchypatchy\src\matchypatchy\main.py" & """"
ElseIf fso.FileExists(pythonPath) Then
  ' fallback to python (will show a console if used)
  cmd = """" & pythonPath & """ """ & scriptDir & "\matchypatchy\src\matchypatchy\main.py" & """"
Else
  ' final fallback: try Python launcher on PATH (pyw for GUI, py if you want console)
  cmd = "pyw -3 """ & scriptDir & "\matchypatchy\src\matchypatchy\main.py" & """"
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

  ' Append error to runner.log for diagnostics
  On Error Resume Next
  Set tf = fso.OpenTextFile(logPath, 8, True) ' 8 = ForAppending
  If Err.Number = 0 Then
    tf.WriteLine Now & " - " & errMsg
    tf.Close
  End If

  WScript.Quit 1
End If

' Optionally write a small "launched" entry to the log so you can confirm run attempts
On Error Resume Next
Set tf = fso.OpenTextFile(logPath, 8, True)
If Err.Number = 0 Then
  tf.WriteLine Now & " - Launched: " & cmd
  tf.Close
End If