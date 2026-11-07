Option Explicit
Dim shell, fs, root, starter, command, code
Set shell = CreateObject("WScript.Shell")
Set fs = CreateObject("Scripting.FileSystemObject")
root = fs.GetParentFolderName(fs.GetParentFolderName(WScript.ScriptFullName))
starter = fs.BuildPath(root, "scripts\desktop_start.ps1")
If Not fs.FileExists(starter) Then
    MsgBox "AnimeVoiceTutor launcher is incomplete. Reinstall the Core files.", vbCritical, "AnimeVoiceTutor"
    WScript.Quit 2
End If
command = "powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File " & Chr(34) & starter & Chr(34)
code = shell.Run(command, 0, True)
If code = 2 Then
    MsgBox "AnimeVoiceTutor opened, but an ASR/TTS voice service is not ready." & vbCrLf & "Check the in-app status or data\logs\desktop_start.log.", vbExclamation, "AnimeVoiceTutor"
ElseIf code <> 0 Then
    MsgBox "AnimeVoiceTutor could not start (code " & code & ")." & vbCrLf & "Open data\logs\desktop_start.log for details.", vbCritical, "AnimeVoiceTutor"
End If
WScript.Quit code
