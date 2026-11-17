@echo off
rem tomorrow_fixes.bat -- Nov 17 fixes, in one go (about 4 passwords):
rem   1. send the updated kit (new daily_check, protect_data, add_field_notes, apply_cast_guard)
rem   2. protect_data.sh: git can no longer overwrite live data; hourly camera job off;
rem      sowing date checked
rem   3. add_field_notes.py: your Nov 16 observations + the D18 cause + D19 colour cast
rem   4. run the health check
rem Usage: double-click, or  tomorrow_fixes.bat <ip>
setlocal
set "PI_HOST=%~1"
if "%PI_HOST%"=="" call "%~dp0find_pi.bat" nopause
if "%PI_HOST%"=="" ( pause & exit /b 1 )
set "KIT=%~dp0..\pi"
echo.
echo === 1. sending the updated kit
scp "%KIT%\daily_check.py" "%KIT%\recover_day.py" "%KIT%\add_field_notes.py" "%KIT%\mask_compare.py" "%KIT%\backup.sh" "%KIT%\install_cron.sh" "%KIT%\protect_data.sh" "%KIT%\apply_cast_guard.py" crk@%PI_HOST%:fixkit/
echo.
echo === 2-4. protect data, add field notes, health check
ssh -t crk@%PI_HOST% "sed -i 's/\r$//' ~/fixkit/*.sh ~/fixkit/*.py; bash ~/fixkit/protect_data.sh; echo; python3 ~/fixkit/add_field_notes.py; echo; python3 ~/fixkit/daily_check.py"
echo.
echo Done. Read the SUMMARY above.
pause
