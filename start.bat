@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"
title Vitals AGENT

echo ======================================================
echo   Vitals // 本机监测台
echo ======================================================
echo.

set "PY="

rem ---- 1. 同目录便携 runtime（零安装分发用）----
if exist "runtime\python.exe" set "PY=%CD%\runtime\python.exe"
if exist "runtime\Scripts\python.exe" set "PY=%CD%\runtime\Scripts\python.exe"

rem ---- 2. 本机安装的 Python ----
if not defined PY (
  for %%P in (python.exe) do set "_TMP=%%~$PATH:P"
  if defined _TMP (
    rem 排除 Microsoft Store 的占位 stub（它只会弹应用商店）
    for /f "delims=" %%V in ('python -c "import sys;print(sys.version_info[0])" 2^>nul') do (
      if "%%V"=="3" set "PY=python"
    )
  )
)

rem ---- 3. py launcher ----
if not defined PY (
  for /f "delims=" %%V in ('py -3 -c "print(1)" 2^>nul') do (
    if "%%V"=="1" set "PY=py -3"
  )
)

if not defined PY goto NOPYTHON

echo [1/3] Python ....... %PY%
"%PY%" -c "import sys;print('      version ...... '+sys.version.split()[0])" 2>nul
if errorlevel 1 (
  echo      [X] Python 无法执行。
  goto FAIL
)

echo [2/3] 检查 psutil ...
"%PY%" -c "import psutil" 2>nul
if errorlevel 1 (
  echo      未安装，尝试自动安装 ...
  "%PY%" -m pip install --quiet --disable-pip-version-check psutil 2>>"%~dp0install.log"
  "%PY%" -c "import psutil" 2>nul
  if errorlevel 1 (
    echo      [!] 自动安装失败（可能无网络/无 pip）。
    echo          将以 PowerShell 降级模式运行：无网络速率、无进程 CPU 榜。
    echo          手动修复： pip install psutil
  ) else (
    echo      [OK] psutil 安装完成。
  )
) else (
  echo      [OK] 已就绪。
)

echo [3/3] 启动采集服务 ...
echo.
echo   ------------------------------------------------
echo    浏览器会自动打开。关闭此窗口即停止监测。
echo   ------------------------------------------------
echo.

"%PY%" "%~dp0server.py"
goto END

:NOPYTHON
echo [X] 未检测到可用的 Python。
echo.
echo     方案 A（推荐，零安装）：
echo       把便携版 python.exe 放进本目录的 runtime\ 文件夹，
echo       再双击本文件即可。
echo.
echo     方案 B：到 https://www.python.org/downloads/ 安装 Python 3，
echo             安装时务必勾选 "Add python.exe to PATH"。
echo.
goto FAIL

:FAIL
echo.
echo 启动失败，按任意键关闭 ...
pause >nul
exit /b 1

:END
echo.
echo 采集已停止。
pause >nul
