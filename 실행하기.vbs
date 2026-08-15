Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
strCurrentDir = fso.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = strCurrentDir

strPythonVenv = strCurrentDir & "\backend\venv\Scripts\pythonw.exe"
strApp = strCurrentDir & "\gui_app.py"

' 1. 이미 가상환경이 정상 구성되어 있는 경우 -> 즉시 완전 무음 실행
If fso.FileExists(strPythonVenv) Then
    WshShell.Run """" & strPythonVenv & """ """ & strApp & """", 0, False
    WScript.Quit
End If

' 2. 최초 1회 실행: 시스템에 파이썬이 설치되어 있는지 확인
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

' 파이썬이 없는 경우 안내 메시지
If strPythonCmd = "" Then
    Dim ans
    ans = MsgBox("이 프로그램을 실행하려면 Python(3.10 이상)이 필요합니다." & vbCrLf & vbCrLf & _
                 "Python이 아직 설치되어 있지 않거나 환경변수(PATH)에 등록되지 않았습니다." & vbCrLf & vbCrLf & _
                 "Python 공식 다운로드 페이지(python.org)를 여시겠습니까?" & vbCrLf & _
                 "(※ 설치 시 'Add python.exe to PATH' 체크박스를 꼭 선택해주세요!)", _
                 vbYesNo + vbExclamation, "Python 설치 필요")
    If ans = vbYes Then
        WshShell.Run "https://www.python.org/downloads/"
    End If
    WScript.Quit
End If

' 최초 환경 구성 안내 알림
MsgBox "최초 1회 실행을 위한 환경을 자동으로 구성합니다." & vbCrLf & _
       "필요한 라이브러리를 설치 중이오니 잠시만 기다려주세요 (약 10~30초 소요)." & vbCrLf & vbCrLf & _
       "설치가 완료되면 프로그램이 자동으로 시작됩니다.", _
       vbInformation + vbOKOnly, "YouTube 대본 추출기 초기 설정"

' 가상환경 생성 및 패키지 설치 후 프로그램 시작
Dim cmdSetup
cmdSetup = "cmd /c " & strPythonCmd & " -m venv backend\venv && backend\venv\Scripts\pip install -r backend\requirements.txt && backend\venv\Scripts\pythonw gui_app.py"
WshShell.Run cmdSetup, 0, False
