@echo off
rem find_pi.bat -- finds the Pi on the current hotspot / Wi-Fi.
rem Double-click it to see the result (the window stays open).
rem The other .bat files call it with "nopause" so it does not stop them.
set "PI_HOST="
set "PI_MAC=88-a2-9e-51-89-a0"
echo Looking for the Pi (groupb)...

rem 1. by name
ping -4 -n 1 -w 1500 groupb.local >nul 2>&1 && set "PI_HOST=groupb.local"

rem 2. already in the address table?
if not defined PI_HOST for /f "tokens=1" %%a in ('arp -a ^| findstr /i "%PI_MAC%"') do set "PI_HOST=%%a"

rem 3. ping every address on this network once (about 5 seconds), then look again
if not defined PI_HOST (
  echo Not found by name. Scanning this network, please wait...
  powershell -NoProfile -Command "$ip=(Get-NetIPConfiguration | Where-Object {$_.IPv4DefaultGateway} | Select-Object -First 1).IPv4Address.IPAddress; if($ip){$p=$ip.Substring(0,$ip.LastIndexOf('.')); $t=1..254 | ForEach-Object {(New-Object System.Net.NetworkInformation.Ping).SendPingAsync(\"$p.$_\",400)}; try{[System.Threading.Tasks.Task]::WaitAll($t)}catch{}; Write-Host ('Scanned ' + $p + '.1-254')} else {Write-Host 'This laptop is not connected to any network.'}"
  for /f "tokens=1" %%a in ('arp -a ^| findstr /i "%PI_MAC%"') do set "PI_HOST=%%a"
)

echo.
if defined PI_HOST (
  echo   Pi found at %PI_HOST%
) else (
  echo   Pi NOT found.
  echo   - Is the laptop connected to the SAME hotspot as the Pi?
  echo   - Is the Pi powered on? Wait 1-2 minutes after the hotspot turns on.
  echo   - On the phone: hotspot settings, connected devices, look for "groupb"
  echo     and note its IP. Then run the other files with that IP, for example:
  echo        check_pi.bat 172.20.10.5
)
echo.
if /i not "%~1"=="nopause" pause
