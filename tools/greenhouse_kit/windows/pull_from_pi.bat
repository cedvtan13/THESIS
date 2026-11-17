@echo off
rem pull_from_pi.bat -- copy ALL of the Pi's run data to this laptop.
rem   ~/thesis              growth_dataset, align/exposure/glare/light/field logs
rem   ~/agrisentry_data     sm, irrigation, error, power, band, throttle logs + frames
rem   ~/fixkit/reports and ~/fixkit/mask_compare   (if they exist)
rem into ThesisCoWork\pi_pulls\<date_time>\   Nothing on the Pi is changed.
rem Works on the hotspot without internet. Frames are ~3 MB per day.
rem Usage: double-click, or  pull_from_pi.bat 172.20.10.5
setlocal
set "PI_HOST=%~1"
if "%PI_HOST%"=="" call "%~dp0find_pi.bat" nopause
if "%PI_HOST%"=="" ( pause & exit /b 1 )
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd_HHmm"') do set "TS=%%i"
set "DEST=%~dp0..\..\..\..\pi_pulls\%TS%"
mkdir "%DEST%" 2>nul
echo Pulling into %DEST%   (type the Pi password when asked; 4 times)
scp -r crk@%PI_HOST%:thesis/ "%DEST%\thesis"
scp -r crk@%PI_HOST%:agrisentry_data/ "%DEST%\agrisentry_data"
mkdir "%DEST%\fixkit" 2>nul
scp -r crk@%PI_HOST%:fixkit/reports "%DEST%\fixkit\reports"
scp -r crk@%PI_HOST%:fixkit/mask_compare "%DEST%\fixkit\mask_compare"
echo.
echo Done: %DEST%
echo Next time you have internet, tell Claude: "I pulled the Pi data into pi_pulls\%TS%"
pause
