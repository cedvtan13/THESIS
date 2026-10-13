#!/usr/bin/env bash
# install_stability.sh -- one-time Pi settings for unattended running (safe to re-run).
#   * Wi-Fi: never give up auto-connecting (NetworkManager stops after 4 failures by
#     default -- the hotspot was then ignored until a reboot), Wi-Fi power saving off
#   * wifi-watchdog.timer: every 2 min, rescan + reconnect if not on Wi-Fi
#   * persistent journal (50 MB cap): logs survive reboots, so outages can be diagnosed
#   * fake-hwclock saved every 10 min instead of hourly: after a power loss the clock
#     restarts at most ~10 min + the outage behind, not up to an hour more
set -euo pipefail
TOOLS="$(cd "$(dirname "$0")" && pwd)"

for c in $(nmcli -t -f NAME,TYPE connection show | awk -F: '$2=="802-11-wireless"{print $1}'); do
  sudo nmcli connection modify "$c" connection.autoconnect-retries 0 802-11-wireless.powersave 2
done
printf "[connection]\nwifi.powersave = 2\n" | sudo tee /etc/NetworkManager/conf.d/wifi-powersave-off.conf >/dev/null

sudo install -m 755 "$TOOLS/wifi_watchdog.sh" /usr/local/bin/wifi_watchdog.sh
sudo tee /etc/systemd/system/wifi-watchdog.service >/dev/null <<'U'
[Unit]
Description=Reconnect Wi-Fi (hotspot) if disconnected
After=NetworkManager.service
[Service]
Type=oneshot
ExecStart=/usr/local/bin/wifi_watchdog.sh
U
sudo tee /etc/systemd/system/wifi-watchdog.timer >/dev/null <<'U'
[Unit]
Description=Check Wi-Fi every 2 minutes
[Timer]
OnBootSec=2min
OnUnitActiveSec=2min
[Install]
WantedBy=timers.target
U

sudo mkdir -p /etc/systemd/journald.conf.d /var/log/journal
printf "[Journal]\nStorage=persistent\nSystemMaxUse=50M\n" | sudo tee /etc/systemd/journald.conf.d/persist.conf >/dev/null

echo "*/10 * * * * root /usr/sbin/fake-hwclock save" | sudo tee /etc/cron.d/fake-hwclock-10min >/dev/null

sudo systemctl daemon-reload
sudo systemctl enable --now wifi-watchdog.timer
sudo systemctl restart systemd-journald
echo "stability settings installed"
