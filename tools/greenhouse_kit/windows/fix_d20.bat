@echo off
rem fix_d20.bat -- (1) limit the after-reboot catch-up capture to 12:00-12:55,
rem               (2) resolve D20's duplicate rows (09:36 and 12:42 captures).
rem Shows everything first; changes D20 only after you type the time to keep.
setlocal
set "PI_HOST=%~1"
if "%PI_HOST%"=="" call "%~dp0find_pi.bat" nopause
if "%PI_HOST%"=="" ( pause & exit /b 1 )
set "KIT=%~dp0..\pi"
echo === sending the two scripts
scp "%KIT%\fix_duplicate_day.py" "%KIT%\fix_catch_up.sh" crk@%PI_HOST%:fixkit/
echo.
echo === 1. catch-up capture limited to the noon window
ssh crk@%PI_HOST% "sed -i 's/\r$//' ~/fixkit/fix_catch_up.sh ~/fixkit/fix_duplicate_day.py; bash ~/fixkit/fix_catch_up.sh"
echo.
echo === 2. D20 has two sets of rows (nothing changes yet)
ssh crk@%PI_HOST% "python3 ~/fixkit/fix_duplicate_day.py --day 20"
echo.
echo Type the time of the set to KEEP exactly as shown (agreed choice: 12:42),
set /p KEEP=or just press Enter to change nothing: 
if "%KEEP%"=="" ( echo D20 left unchanged. & pause & exit /b 0 )
ssh crk@%PI_HOST% "python3 ~/fixkit/fix_duplicate_day.py --day 20 --keep %KEEP% --write"
echo.
echo Done. Then run check_pi.bat and pull_from_pi.bat.
pause
