@echo off
rem send_kit_to_pi.bat -- copy the fix kit (the "pi" folder) to ~/fixkit on the Pi
rem and install the twice-daily backup. Run once. Works on the hotspot, no internet.
rem Usage: double-click, or  send_kit_to_pi.bat 172.20.10.5
setlocal
set "PI_HOST=%~1"
if "%PI_HOST%"=="" call "%~dp0find_pi.bat" nopause
if "%PI_HOST%"=="" ( pause & exit /b 1 )
set "KIT=%~dp0..\pi"
echo.
echo Copying the kit to crk@%PI_HOST%:~/fixkit  (type the Pi password when asked)
ssh crk@%PI_HOST% "mkdir -p ~/fixkit/reports"
scp "%KIT%\daily_check.py" "%KIT%\recover_day.py" "%KIT%\add_field_notes.py" "%KIT%\mask_compare.py" "%KIT%\backup.sh" "%KIT%\install_cron.sh" crk@%PI_HOST%:fixkit/
echo.
echo Installing the backup schedule and making the first backup...
ssh crk@%PI_HOST% "sed -i 's/\r$//' ~/fixkit/*.sh ~/fixkit/*.py; bash ~/fixkit/install_cron.sh && bash ~/fixkit/backup.sh"
echo.
echo Done. Next: run check_pi.bat
pause
