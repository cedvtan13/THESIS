@echo off
rem check_pi.bat -- run the daily health check on the Pi and show the report here.
rem Usage: double-click, or  check_pi.bat 172.20.10.5
setlocal
set "PI_HOST=%~1"
if "%PI_HOST%"=="" call "%~dp0find_pi.bat" nopause
if "%PI_HOST%"=="" ( pause & exit /b 1 )
ssh -t crk@%PI_HOST% "python3 ~/fixkit/daily_check.py"
pause
