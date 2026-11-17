#!/bin/bash
sleep 120
TODAY=$(date +%Y-%m-%d)
if ! ls /home/crk/agrisentry_data/frames/D*_${TODAY}_*.png 1> /dev/null 2>&1; then
    /usr/bin/python3 /home/crk/THESIS/Dual_Archi/capture_gpr.py >> /home/crk/THESIS/Dual_Archi/cron.log 2>&1
fi
