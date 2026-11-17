@echo off
rem apply_cast_guard.bat -- OPTIONAL capture change: retry blue (overcast) frames.
rem Shows the change and the D19 test first; patches only if you type y.
rem Undo any time:  ssh crk@groupb.local "python3 ~/fixkit/apply_cast_guard.py --undo"
setlocal
set "PI_HOST=%~1"
if "%PI_HOST%"=="" call "%~dp0find_pi.bat" nopause
if "%PI_HOST%"=="" ( pause & exit /b 1 )
echo === preview (nothing changes yet)
ssh crk@%PI_HOST% "python3 ~/fixkit/apply_cast_guard.py"
echo.
echo The guard only delays the noon write by 10 minutes when the frame is blue;
echo the 12:50 retry always writes, so no day can be lost to it.
set /p ANS=Apply it to capture_gpr.py on the Pi? Type y to apply: 
if /i not "%ANS%"=="y" ( echo Not applied. & pause & exit /b 0 )
ssh crk@%PI_HOST% "python3 ~/fixkit/apply_cast_guard.py --apply && cd ~/THESIS/Dual_Archi && python3 capture_gpr.py --test-image ~/agrisentry_data/frames/D19_2026-11-16_1247.png --no-write --no-sm --allow-any-day 2>&1 | grep -i -e cast -e error -e Traceback"
echo.
echo Expect a line "colour cast blue/red = 1.84". If you see "Traceback", run the undo above.
pause
