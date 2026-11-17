@echo off
rem run_mask_compare.bat -- run the read-only mask comparison on the Pi (2 to 5 min).
rem Usage: double-click, or  run_mask_compare.bat <ip>
setlocal
set "PI_HOST=%~1"
if "%PI_HOST%"=="" call "%~dp0find_pi.bat" nopause
if "%PI_HOST%"=="" ( pause & exit /b 1 )
ssh crk@%PI_HOST% "python3 ~/fixkit/mask_compare.py"
echo.
echo Done. The results come to the laptop with pull_from_pi.bat
pause
