#!/usr/bin/env bash
# panel.sh -- one-screen summary of the running system, for the panel checking.
#   On the Pi:   ~/THESIS/system.sh panel     (or: bash ~/thesis/tools/panel.sh)
#   From Mac:    ./system.sh panel
# Read-only: it only reads the CSV files and service state.
DUAL="$HOME/THESIS/Dual_Archi"
DATA="$HOME/agrisentry_data"
B=$'\e[1m'; N=$'\e[0m'
rows() { [[ -f $1 ]] && echo $(( $(wc -l < "$1") - 1 )) || echo 0; }

echo "${B}Pechay Growth & Yield Monitoring -- system summary  $(date '+%Y-%m-%d %H:%M')${N}"
python3 - "$DUAL/sowing_date.txt" <<'EOF'
import sys, datetime as dt
s = open(sys.argv[1]).read().strip()
d = (dt.date.today() - dt.date.fromisoformat(s)).days + 1
print(f"Sown {s}  ->  today is D{d} of 30  (harvest D30 = {dt.date.fromisoformat(s) + dt.timedelta(days=29)})")
EOF
mode="GERMINATION (all pots kept at 50-60 %)"
grep -q "treatment bands ON" "$DUAL/field_log.csv" 2>/dev/null && mode="TREATMENTS (low 30-40 / optimal 50-60 / high 70-80 %)"
echo "Watering mode : $mode"
echo "Logger        : $(systemctl is-active pi-link)   Noon capture: $(crontab -l 2>/dev/null | grep -q '^[^#].*capture_gpr.py' && echo ON || echo OFF)   Light log: $(crontab -l 2>/dev/null | grep -q '^[^#].*light_log.py' && echo ON || echo OFF)"
echo "Clock synced  : $(timedatectl show -p NTPSynchronized --value)"

echo; echo "${B}1. Soil moisture (latest, logged every 30 min) and automatic watering${N}"
python3 - "$DATA/sm_log.csv" "$DATA/irrigation_log.csv" "$mode" <<'EOF'
import csv, sys, os
sm = list(csv.DictReader(open(sys.argv[1]))) if os.path.exists(sys.argv[1]) else []
irr = list(csv.DictReader(open(sys.argv[2]))) if os.path.exists(sys.argv[2]) else []
germ = sys.argv[3].startswith("GERM")
grp = {1: "Low", 2: "Low", 3: "Low", 4: "Optimal", 5: "Optimal", 6: "Optimal", 7: "High", 8: "High", 9: "High"}
bnd = {"Low": (30, 40), "Optimal": (50, 60), "High": (70, 80)}
if not sm:
    print("  no readings yet"); sys.exit()
r = sm[-1]
print(f"  reading at {r['wall_time'].replace('T', ' ')[:16]}")
print(f"  {'pot':5} {'group':8} {'moisture':>9}  {'target':>7}  {'status':16} {'doses':>5} {'mL':>6}")
for i in range(1, 10):
    p = f"P-0{i}"; lo, hi = (50, 60) if germ else bnd[grp[i]]
    v = r.get(p, "NaN")
    st = "no reading" if v in ("", "NaN") else ("below -> waters" if float(v) < lo else "above" if float(v) > hi else "in band")
    ev = [e for e in irr if e["pot_id"] == p and e.get("status", "DOSED") == "DOSED"]
    ml = sum(float(e["dose_ml"] or 0) for e in ev)
    print(f"  {p:5} {grp[i]:8} {v:>8}%  {lo:>3}-{hi:<3}  {st:16} {len(ev):>5} {ml:>6.0f}")
print(f"  moisture readings logged: {len(sm)}   automatic doses: {len(irr)}")
EOF

echo; echo "${B}2. Daily noon capture -- growth dataset${N}"
python3 - "$DUAL/growth_dataset.csv" "$DUAL/exposure_log.csv" <<'EOF'
import csv, sys, os
g = list(csv.DictReader(open(sys.argv[1]))) if os.path.exists(sys.argv[1]) else []
days = sorted({int(r["day"]) for r in g})
print(f"  days captured: {len(days)} ({', '.join('D'+str(d) for d in days) or 'none'})   rows: {len(g)}")
if g:
    last = max(days)
    rows = [r for r in g if int(r["day"]) == last]
    print(f"  latest D{last} at {rows[0]['timestamp']}:")
    print("    " + "  ".join(f"{r['pot_id']} {float(r.get('cell_gpr') or r['raw_gpr']):.2f}%" for r in rows))
    print("    (pot-area green pixel ratio; 0 % until the seedlings come up)")
if os.path.exists(sys.argv[2]):
    e = list(csv.DictReader(open(sys.argv[2])))
    if e:
        x = e[-1]
        print(f"  last exposure: {int(x['exposure_us'])/1000:.1f} ms, brightness {x['mean_v']} (target {x['target_v']}), light used: {x['light_used']}")
EOF
n=$(ls "$DATA"/frames/D*.png 2>/dev/null | wc -l)
echo "  raw frames saved: $n   check pictures: $(ls "$DATA"/frames/overlay/*.jpg 2>/dev/null | wc -l)  ($DATA/frames)"

echo; echo "${B}3. Light (hourly, camera used as a light meter)${N}"
if [[ $(rows "$DUAL/light_log.csv") -gt 0 ]]; then
  tail -n +2 "$DUAL/light_log.csv" | tail -n 4 | awk -F, '{printf "  %s  light index %s %s\n", $1, $6, $7}'
else echo "  no readings yet"; fi

echo; echo "${B}4. Faults and power${N}"
echo "  error log entries : $(rows "$DATA/error_log.csv")"
[[ $(rows "$DATA/error_log.csv") -gt 0 ]] && tail -n 3 "$DATA/error_log.csv" | sed 's/^/    /'
echo "  power events      : $(rows "$DATA/power_log.csv")"

echo; echo "${B}5. Deliverable files${N}"
for f in "$DUAL/growth_dataset.csv" "$DATA/sm_log.csv" "$DATA/irrigation_log.csv" "$DATA/error_log.csv" \
         "$DATA/power_log.csv" "$DUAL/light_log.csv" "$DUAL/exposure_log.csv" "$DUAL/field_log.csv" \
         "$DUAL/pot_rois.json" "$DUAL/harvest_weights.csv"; do
  if [[ $f == *.json && -f $f ]]; then printf "  %-50s %s\n" "$f" "present (9 pot circles)"
  elif [[ -f $f ]]; then printf "  %-50s %5s rows\n" "$f" "$(rows "$f")"
  else printf "  %-50s %s\n" "$f" "(not yet -- created at harvest)"; fi
done
echo; echo "Open a file as a table:  column -s, -t < FILE | less -S    (q to quit)"
