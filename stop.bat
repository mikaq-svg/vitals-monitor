@echo off
setlocal EnableDelayedExpansion
title Vitals stop

echo.
echo   Stopping Vitals ...
echo.

set "KILLED=0"
for %%P in (8765 8766 8767 8768 8769) do (
  for /f "tokens=5" %%A in ('netstat -ano ^| findstr "LISTENING" ^| findstr ":%%P "') do (
    taskkill /F /PID %%A >nul 2>&1
    if not errorlevel 1 (
      echo   stopped port %%P  PID %%A
      set "KILLED=1"
    )
  )
)

if "!KILLED!"=="0" (
  echo   Vitals is not running.
) else (
  echo.
  echo   Done.
)

rem ---- 顺带收掉 LibreHardwareMonitor（读温度用的托盘程序）----
set "LHM=0"
for /f "tokens=2" %%A in ('tasklist /FI "IMAGENAME eq LibreHardwareMonitor.exe" /NH ^| findstr /I "LibreHardwareMonitor"') do (
  taskkill /F /PID %%A >nul 2>&1
  if not errorlevel 1 (
    echo   stopped LibreHardwareMonitor  PID %%A
    set "LHM=1"
  )
)
if "!LHM!"=="0" (
  rem 它以管理员权限运行时普通权限杀不掉，这很正常，给个提示就好
  tasklist /FI "IMAGENAME eq LibreHardwareMonitor.exe" /NH 2>nul | findstr /I "LibreHardwareMonitor" >nul && (
    echo   [i] LibreHardwareMonitor 需要管理员权限才能关闭，
    echo       可在系统托盘右键退出，或不管它（不影响使用）。
  )
)

echo.
"%SystemRoot%\System32\timeout.exe" /t 3 >nul 2>&1
