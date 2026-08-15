Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
strCurrentDir = fso.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = strCurrentDir

strPythonVenv = strCurrentDir & "\backend\venv\Scripts\pythonw.exe"
strApp = strCurrentDir & "\gui_app.py"

If fso.FileExists(strPythonVenv) Then
    WshShell.Run """" & strPythonVenv & """ """ & strApp & """", 0, False
    WScript.Quit
End If

Dim strPythonCmd
strPythonCmd = ""

On Error Resume Next
Dim retCode
retCode = WshShell.Run("cmd /c python --version", 0, True)
If retCode = 0 Then
    strPythonCmd = "python"
Else
    retCode = WshShell.Run("cmd /c py --version", 0, True)
    If retCode = 0 Then
        strPythonCmd = "py"
    End If
End If
On Error GoTo 0

If strPythonCmd = "" Then
    Dim ans
    ans = MsgBox("Python 3.10+ is required to run this application." & vbCrLf & vbCrLf & _
                 "Python was not found on this computer." & vbCrLf & vbCrLf & _
                 "Do you want to open python.org download page?", _
                 vbYesNo + vbExclamation, "Python Required")
    If ans = vbYes Then
        WshShell.Run "https://www.python.org/downloads/"
    End If
    WScript.Quit
End If

MsgBox "Setting up the environment for first-time use." & vbCrLf & _
       "Installing required dependencies (approx. 10~30 seconds)..." & vbCrLf & vbCrLf & _
       "The application will launch automatically once ready.", _
       vbInformation + vbOKOnly, "YouTube Transcript Extractor"

Dim cmdSetup
cmdSetup = "cmd /c " & strPythonCmd & " -m venv backend\venv && backend\venv\Scripts\pip install -r backend\requirements.txt && backend\venv\Scripts\pythonw gui_app.py"
WshShell.Run cmdSetup, 0, False
