@echo off
rem ============================================================
rem  Quietly clear leftovers from a previous run.
rem  Called by start.vbs BEFORE launching, so a stale agent can
rem  never block a fresh start. Silent: no window, no output.
rem
rem  Only the metric agent is killed. LibreHardwareMonitor is
rem  deliberately left alone: it is the temperature source, it
rem  runs elevated so a normal kill would be refused anyway, and
rem  the launcher only starts a new one when none is running.
rem ============================================================
setlocal EnableDelayedExpansion

for %%P in (8765 8766 8767 8768 8769) do (
  for /f "tokens=5" %%A in ('netstat -ano ^| findstr "LISTENING" ^| findstr ":%%P "') do (
    taskkill /F /PID %%A >nul 2>&1
  )
)

endlocal
exit /b 0
