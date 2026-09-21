' ya_seen_start.vbs
' YAseen ERP - تشغيل الخادم في الخلفية (بدون أي نافذة أوامر) ثم فتح التطبيق تلقائياً
Option Explicit

Dim shell, fso, root, pythonCmd, serverCmd, appExe, serverProc, http
Dim healthUrl, attempts, alive
Dim wmi, procs, proc

Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' جذر المشروع (نفس مجلد هذا الملف)
root = fso.GetParentFolderName(WScript.ScriptFullName)

pythonCmd = "python"
serverCmd = """" & root & "\run.py"""
appExe = root & "\frontend\build\windows\x64\runner\Release\ya_seen_erp_flutter.exe"

' 1) تشغيل الخادم في الخلفية بدون نافذة (window style 0 = hidden)
On Error Resume Next
serverProc = shell.Run(pythonCmd & " " & serverCmd, 0, False)
If Err.Number <> 0 Then
    MsgBox "تعذر تشغيل بايثون. تأكد من تثبيت بايثون وإضافته إلى PATH.", 48, "YAseen ERP"
    WScript.Quit
End If
On Error GoTo 0

' 2) انتظار جاهزية الخادم (حتى 30 ثانية)
healthUrl = "http://127.0.0.1:8000/api/health"
attempts = 0
alive = False
Do While attempts < 60 And Not alive
    Set http = CreateObject("MSXML2.ServerXMLHTTP.6.0")
    On Error Resume Next
    http.open "GET", healthUrl, False
    http.send
    If Err.Number = 0 And http.status = 200 Then
        alive = True
    End If
    Err.Clear
    On Error GoTo 0
    If Not alive Then
        WScript.Sleep 500
        attempts = attempts + 1
    End If
Loop

' 3) فتح التطبيق
If fso.FileExists(appExe) Then
    ' افتح التطبيق (عرض نافذة التطبيق — وليس نافذة أوامر!)
    shell.Run """" & appExe & """", 1, False

    ' 4) مراقبة التطبيق: انتظر حتى يغلقه المستخدم ثم أوقف الخادم تلقائياً
Dim wmi, procs, proc
Set wmi = GetObject("winmgmts:\\.\root\cimv2")
Do
    WScript.Sleep 2000
    Set procs = wmi.ExecQuery("SELECT ProcessId FROM Win32_Process WHERE Name='ya_seen_erp_flutter.exe'")
Loop While procs.Count > 0

' 5) المستخدم أغلق التطبيق: أوقف خادم run.py فقط (وليس كل بايثون على الجهاز)
Set procs = wmi.ExecQuery("SELECT ProcessId FROM Win32_Process WHERE Name='python.exe' AND CommandLine LIKE '%run.py%'")
For Each proc In procs
    shell.Run "taskkill /F /T /PID " & proc.ProcessId, 0, True
Next
Else
    If alive Then
        MsgBox "تم تشغيل الخادم، لكن لم يُعثر على ملف التطبيق النهائي:" & vbCrLf & vbCrLf & appExe, 48, "YAseen ERP"
    Else
        MsgBox "لم يستجب الخادم خلال 30 ثانية. تحقق من قاعدة البيانات/الإعدادات ثم أعد المحاولة.", 48, "YAseen ERP"
    End If
End If
