' Vitals launcher
' 双击这个文件就能启动。它把 start.bat 藏在后台跑，
' 所以屏幕上只会出现仪表盘窗口，不会闪一个黑框。
'
' 这个启动器保证一件事：点它，一定能看到界面。
' 启动前它先清掉上一次没退干净的旧进程 —— 旧进程占着端口，
' 正是"第二次双击像没反应"的元凶。
'
' 它还能在桌面放一个快捷方式，下次直接点图标就行。
' 不过动手之前会先问你一句，答不答应你说了算。
Option Explicit

Dim fso, sh, here, bat, cln, lhm, rc
Dim desk, lnk, sc, mark, need, ans, tf

Set fso = CreateObject("Scripting.FileSystemObject")
Set sh  = CreateObject("WScript.Shell")

here = fso.GetParentFolderName(WScript.ScriptFullName)
bat  = fso.BuildPath(here, "start.bat")
cln  = fso.BuildPath(here, "tools\cleanup.bat")
mark = fso.BuildPath(here, ".nolink")

If Not fso.FileExists(bat) Then
    MsgBox "找不到 start.bat，请确认整个文件夹都完整解压出来了。", 16, "Vitals"
    WScript.Quit 1
End If

' --- 0. 桌面快捷方式：先问一句，再动手 ---------------------------------
' 只在"桌面还没有、或者它指向了别处"的时候才走到询问那一步，所以正常
' 情况下你只在第一次启动时被问一次。桌面路径用 SpecialFolders("Desktop")
' 取，它会自动跟随 OneDrive 重定向，这里没有任何写死的个人路径。
' 整段都是尽力而为：桌面写不进去，也绝不能挡住界面启动。
On Error Resume Next
desk = sh.SpecialFolders("Desktop")
If Len(desk) > 0 Then
    lnk = fso.BuildPath(desk, "Vitals.lnk")
    need = False
    Set sc = sh.CreateShortcut(lnk)
    ' 要一个还不存在的快捷方式，拿回来是空的 —— 正好，填上再存。
    ' 已经存在时，只在它指向别处才重写：这样整个文件夹挪了位置，
    ' 下次启动会把快捷方式修好，而不是留一个点不开的死链接。
    If sc.TargetPath <> WScript.ScriptFullName Then need = True
    ' 之前拒绝过就记着，不再问第二遍
    If need And Not fso.FileExists(mark) Then
        ans = MsgBox("是否创建快捷方式？", vbYesNo + vbQuestion, "Vitals")
        If ans = vbYes Then
            sc.TargetPath = WScript.ScriptFullName
            sc.WorkingDirectory = here
            sc.Description = "Vitals"
            sc.IconLocation = sh.ExpandEnvironmentStrings("%SystemRoot%") & "\System32\shell32.dll,13"
            sc.Save
        Else
            ' 记住这次拒绝，免得每次启动都来烦你
            Set tf = fso.CreateTextFile(mark, True)
            tf.WriteLine "no"
            tf.Close
            If fso.FileExists(mark) Then fso.GetFile(mark).Attributes = 2
        End If
    End If
End If
On Error GoTo 0

' --- 1. 清掉残留进程，保证这次一定拿得到端口 ---------------------------
' 还占着端口的，就是上一次没关干净的仪表盘。这段交给一个小批处理去杀
' （批处理里写这些命令，比在 VBS 里拼字符串可靠得多）。
If fso.FileExists(cln) Then
    On Error Resume Next
    sh.Run "cmd /c """ & cln & """", 0, True
    On Error GoTo 0
End If

' --- 2. LibreHardwareMonitor：提供 CPU / 显卡温度 ----------------------
' 它要有管理员权限才能读传感器，所以第一次会弹一个 UAC 授权框让人点一下。
' 之后 Windows 会记住这个选择，以后就安静启动了。
' 只在它没跑的时候才拉：开第二份只会跟第一份抢 8085 端口，白占资源。
lhm = fso.BuildPath(here, "tools\LibreHardwareMonitor\LibreHardwareMonitor.exe")
If fso.FileExists(lhm) Then
    rc = 9
    On Error Resume Next
    rc = sh.Run("cmd /c tasklist /FI ""IMAGENAME eq LibreHardwareMonitor.exe"" /NH | findstr /I LibreHardwareMonitor", 0, True)
    On Error GoTo 0
    ' rc = 0 说明 findstr 找到了，也就是它正在跑
    If rc <> 0 Then
        On Error Resume Next
        sh.CurrentDirectory = fso.GetParentFolderName(lhm)
        ' 1 = 正常窗口；LHM 会按自己的配置缩到托盘
        sh.Run """" & lhm & """", 1, False
        On Error GoTo 0
    End If
End If

' --- 3. 启动采集端（隐藏控制台）---------------------------------------
' 0 = 隐藏窗口，False = 不等它退出
sh.CurrentDirectory = here
sh.Run "cmd /c """ & bat & """", 0, False
