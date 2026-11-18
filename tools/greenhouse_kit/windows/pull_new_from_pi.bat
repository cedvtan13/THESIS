@echo off
rem pull_new_from_pi.bat -- QUICK daily pull (use this most days).
rem Copies only what changed:
rem   - every data and log file (csv, log, txt, json) from ~/thesis and ~/agrisentry_data
rem     (these are small, about 2 MB in total, and are always copied whole)
rem   - only the camera frames and overlays from the last 2 days (about 4 MB a day)
rem   - only the health-check reports from the last 2 days
rem into ThesisCoWork\pi_pulls\<date_time>_quick\   Nothing on the Pi is changed.
rem Asks for the Pi password ONCE. Works on the hotspot without internet.
rem
rem Usage: double-click
rem        pull_new_from_pi.bat 172.20.10.3       (Pi IP, if the name isn't found)
rem        pull_new_from_pi.bat 172.20.10.3 5     (frames from the last 5 days instead of 2)
rem
rem For a FULL copy of everything (all frames since D1), use pull_from_pi.bat about once a week.
setlocal
set "PI_HOST=%~1"
set "DAYS=%~2"
if "%DAYS%"=="" set "DAYS=2"
if "%PI_HOST%"=="" call "%~dp0find_pi.bat" nopause
if "%PI_HOST%"=="" ( pause & exit /b 1 )
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd_HHmm"') do set "TS=%%i"
set "DEST=%~dp0..\..\..\..\pi_pulls\%TS%_quick"
mkdir "%DEST%" 2>nul
echo Quick pull into %DEST%
echo Data files + frames from the last %DAYS% days. Type the Pi password ONCE when asked.
ssh crk@%PI_HOST% "cd ~ && F=$(find agrisentry_data/frames -maxdepth 2 -type f -mtime -%DAYS% \( -name 'D*.png' -o -name '*.jpg' \) 2>/dev/null); R=$(find fixkit/reports -type f -mtime -%DAYS% 2>/dev/null); tar --ignore-failed-read -czf - thesis/*.csv thesis/*.log thesis/*.txt agrisentry_data/*.csv agrisentry_data/*.log agrisentry_data/*.json $F $R" > "%DEST%\pull.tgz"
if errorlevel 1 (
  echo.
  echo PULL FAILED: wrong password, Pi not reachable, or the connection dropped.
  echo Nothing was changed. Try again, or use pull_from_pi.bat.
  pause & exit /b 1
)
tar -xzf "%DEST%\pull.tgz" -C "%DEST%"
if errorlevel 1 (
  echo Could not unpack pull.tgz. It is kept in %DEST% - send it to Kent as it is.
  pause & exit /b 1
)
del "%DEST%\pull.tgz"
echo.
echo ===== frames copied =====
dir /b /s "%DEST%\agrisentry_data\frames" 2>nul
echo.
echo ===== last 9 rows of growth_dataset.csv (today's photo, if it was taken) =====
powershell -NoProfile -Command "Get-Content '%DEST%\thesis\growth_dataset.csv' -Tail 9"
echo.
echo ===== latest soil readings (sm_log.csv: time, then P-01 to P-09) =====
powershell -NoProfile -Command "Get-Content '%DEST%\agrisentry_data\sm_log.csv' -Tail 4"
echo.
echo Done: %DEST%
echo Send this folder to Kent (Drive link or zip), or tell Claude: "quick pull in pi_pulls\%TS%_quick"
pause
