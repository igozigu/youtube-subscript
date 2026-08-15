Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
strCurrentDir = fso.GetParentFolderName(WScript.ScriptFullName)

strPython = strCurrentDir & "\backend\venv\Scripts\pythonw.exe"
strApp = strCurrentDir & "\gui_app.py"

If fso.FileExists(strPython) Then
    WshShell.CurrentDirectory = strCurrentDir
    WshShell.Run """" & strPython & """ """ & strApp & """", 0, False
Else
    WshShell.CurrentDirectory = strCurrentDir
    WshShell.Run "cmd /c python -m venv backend\venv && backend\venv\Scripts\pip install -r backend\requirements.txt && backend\venv\Scripts\pythonw gui_app.py", 0, False
End If
