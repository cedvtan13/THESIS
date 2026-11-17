@echo off
rem fix_d18.bat -- preview, then (if you say y) add the missing D18 rows on the Pi,
rem update the field log, and add the D15 P-09 note. Usage: double-click, or fix_d18.bat <ip>
setlocal
set "PI_HOST=%~1"
if "%PI_HOST%"=="" call "%~dp0find_pi.bat" nopause
if "%PI_HOST%"=="" ( pause & exit /b 1 )
echo.
echo === PREVIEW (nothing is written yet) ===
ssh crk@%PI_HOST% "python3 ~/fixkit/recover_day.py --day 18"
echo.
echo Check the preview above:
echo   1. "applied=True" on the alignment line
echo   2. "soil moisture from sm_log at ... (N min from the frame)" with N small
echo   3. nine pots listed with numbers
set /p ANS=Do all three look right? Type y to write, anything else to stop: 
if /i not "%ANS%"=="y" ( echo Stopped. Nothing was written. & pause & exit /b 0 )
ssh crk@%PI_HOST% "python3 ~/fixkit/recover_day.py --day 18 --write && python3 ~/fixkit/add_field_notes.py"
echo.
echo Done. Run check_pi.bat again: D18 should no longer be listed as missing.
pause
