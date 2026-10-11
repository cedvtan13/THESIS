# Sourced by the Mac-side scripts. Sets PI (user@host) and SSH (ssh command).
# groupb.local works on the hotspot; on home Wi-Fi mDNS can fail, so fall back
# to the ARP table. HostKeyAlias pins the Pi's known host key either way.
# Override with:  PI_HOST=192.168.1.16 ./script.sh
if [[ -z "${PI_HOST:-}" ]]; then
  if ssh -o BatchMode=yes -o ConnectTimeout=4 crk@groupb.local true 2>/dev/null; then
    PI_HOST=groupb.local
  else
    PI_HOST=$(arp -a | awk '/^groupb[ .]/ {gsub(/[()]/, "", $2); print $2; exit}')
  fi
fi
[[ -n "${PI_HOST:-}" ]] || { echo "Pi not found on the network (try: PI_HOST=<ip> $0 ...)"; exit 1; }
PI="crk@$PI_HOST"
SSH="ssh -o HostKeyAlias=groupb.local"
