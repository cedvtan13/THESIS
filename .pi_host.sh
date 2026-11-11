# Sourced by the Mac-side scripts. Sets PI (user@host) and SSH (ssh command).
# groupb.local works on the hotspot; on home Wi-Fi mDNS can fail, so fall back
# to the ARP table. HostKeyAlias pins the Pi's known host key either way.
# Override with:  PI_HOST=192.168.1.16 ./script.sh
if [[ -z "${PI_HOST:-}" ]]; then
  if ssh -o BatchMode=yes -o ConnectTimeout=2 crk@groupb.local true 2>/dev/null; then
    PI_HOST=groupb.local
  else
    # Search ARP by Pi Zero 2W Wi-Fi MAC (88:a2:9e:51:89:a0) - works on hotspot where mDNS fails
    PI_HOST=$(arp -an 2>/dev/null | grep -i "88:a2:9e:51:89:a0" | awk '{print $2}' | tr -d '()' | head -n 1)
    if [[ -z "$PI_HOST" ]]; then
      PI_HOST=$(arp -a 2>/dev/null | awk '/^groupb[ .]/ {gsub(/[()]/, "", $2); print $2; exit}')
    fi
  fi
fi
if [[ -z "${PI_HOST:-}" ]]; then
  echo "Pi not found on the network (MAC: 88:a2:9e:51:89:a0, host: groupb.local)."
  echo "Make sure hotspot is ON and the Pi is connected, or run: PI_HOST=<ip> $0"
  return 1 2>/dev/null || exit 1
fi
PI="crk@$PI_HOST"
SSH="ssh -o HostKeyAlias=groupb.local"
