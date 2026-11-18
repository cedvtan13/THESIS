# Replant plan: backup batch, ready to swap in on D8 (written Nov 19, 2026)

*Claude with Cedric. This is a plan, not a team decision yet. Agree on it in the group chat first: rule 4 (no replanting) only changes after a written team decision.*

## The idea

Sow a backup batch now, in pots identical to the rig pots, kept off the rig.
- **If the panel asks for a redo on Nov 21:** end run 2, and swap the new pots into the rig on the new batch's D7, so its D8 (treatments on, first official capture) runs in the rig. D8 to D30 are then captured for the second checking.
- **If the panel accepts the current run:** keep run 2 going (Option 1, extend to D40). The new pots become a side-by-side comparison of growth in the old and new soil.

Either way the batch is useful. Neither choice touches the current pots before Nov 21.

## Dates (sowing Thu Nov 20 = new D1; if you sow today, Nov 19, move everything one day earlier)

| New day | Date | Milestone |
|---|---|---|
| D1 | Thu Nov 20 | sow |
| D2 | Sat Nov 21 | **first checking:** panel decides |
| D7 | Wed Nov 26 | swap the pots into the rig (only if replanting) |
| D8 | Thu Nov 27 | `bands-on`, first official noon capture |
| D18 to D24 | Dec 7 to 13 | **second checking** |
| D30 | Fri Dec 19 | harvest (after the second checking) |

**Ask Sir AJ now:** what must the second checking show?
- **Progress only:** this timeline works.
- **Harvest weights and the yield model:** harvest early, about D24 (Dec 13). Like the existing request for 30-day harvest sources, that needs a source showing pechay can be harvested around 25 days. Say it in the methods before the run starts.

**Write into the methods before sowing:**
- D1 to D7 = establishment, off the rig, not camera-captured; GPR is not measured.
- D8 to D30 = the official treatment series.
- Thin to 1 seedling per pot by D7.
- Training rows = 9 pots × 23 days (D8 to D30), minus any missed days.

---

## Things that must be fixed for the new run, or it will fail the same way

1. **Power: the top risk.**
   - So far this run: about 41 h off at D2 and D3, 13 restarts on Nov 3, and 3 full power losses on Nov 17 to 18.
   - Fix before the swap: a proper 5.1 V 3 A Pi supply with a short, thick cable; check the rig's main outlet and the UPS.
2. **Probe faults.**
   - Since Nov 17 16:32 every probe reads about 10 points low.
   - Since Nov 16, all probes jump 15 to 20 points together.
   - Check the probe supply, the connectors and moisture on the boards before the swap.
3. **The soil.** Measure the pH of the old mix and the new mix (see Day 1). Carbonized rice hull is alkaline, and there is a lot of it in the 8:4:3 mix.
4. **Sow depth.** Seeds were placed on the surface, and three pots never germinated. Sow 3 to 4 seeds per pot at a fixed shallow depth (follow the seed packet) and thin to 1.
5. **Waterlogging and the P-06 outlet.**
   - P-01's saucer held water. Make sure every pot drains.
   - P-06's tube outlet sits next to its probe. Put each tube outlet the same distance from each probe.
6. **Treatment vs position (Q10 in the checking plan).** Each group is one row, so position and treatment are mixed up. If the firmware is re-flashed anyway (step 4), consider randomising which pot gets which band, and record the map.

---

## Shopping and materials (buy everything at once, same stock)

- **Soil:** DA plain garden soil, vermicast, rice hull. Ask whether the rice hull is raw or carbonized, and write which in the methods.
  - **Recipe:** the team's choice. The Google suggestion is 3:1:1 plain soil : vermicast : rice hull by volume.
  - Mix **one batch** for every pot.
  - Amount: about 15 L of mixed soil for 9 rig pots, 3 to 6 spares, 4 to 6 comparison pots and the calibration samples. That is about 9 L soil, 3 L vermicast and 3 L rice hull. Check each pack's size and buy one extra of each.
  - **No chicken dung** (it can burn seedlings).
- **Pots:** 15 to 20 identical to the rig pots (110 mm top, 85 mm base, 80 mm deep), with drainage holes and saucers.
- **Seeds:** the same lot if possible. Note the brand, the lot and the packet date.
- **pH meter or kit** (the sensor expected Nov 19 to 20).
- **Kitchen scale:** for watering by weight (see Days 2 to 6). The 0.01 g pocket scale is for the harvest.
- **Also needed:** labels and a marker.

---

## Day by day

### Day 0: Wed Nov 19 (today)
- [ ] Agree on this plan in the group chat (it becomes the written team decision for the backup batch).
- [ ] Ask Sir AJ the second-checking question above.
- [ ] Pick the soil recipe. Confirm pots, seeds, pH meter and scale.
- [ ] Choose the spot for the new pots:
  - same greenhouse, as close as possible to the rig's light;
  - **out of the camera's view** (on D7 a green object in the frame was counted as P-03's GPR);
  - away from the rig's watering.

### Day 1: Thu Nov 20 (new D1)
- [ ] Buy the soil and amendments.
- [ ] Measure the pH of the old 8:4:3 mix (leftover, or remade from the same materials) and of the new mix. Log both.
- [ ] Mix the new soil in one batch.
- [ ] **Set aside calibration samples:**
  - one portion to oven-dry at 150 °C for 6 h, as the old calibration was done;
  - one portion to saturate.
  - Weigh each pot's worth dry and saturated, as was done for the old mix (388 g dry and 662 g saturated per pot).
- [ ] Fill every pot to the **same mass** of soil. Write the mass down.
- [ ] Sow 3 to 4 seeds per pot at a fixed depth.
  - Label the pots: rig candidates N-01 to N-09, spares N-S1 and up.
  - Also sow 4 to 6 **comparison pots: half old mix, half new mix**, side by side.
- [ ] Water them all to the same target.
- [ ] Log everything in `field_log.csv`: time, recipe, products, pH, pot mass, seeds per pot, depth, location, and who did it.

### Days 2 to 6: Fri Nov 21 to Tue Nov 25
- [ ] **Water by weight.** The pots have no probes yet, so keep each one at the germination target (50 to 60 % of the dry-to-saturated range). Weigh it, and add water to the target mass.
  - Example with the old mix: dry 388 g, saturated 662 g, so 50 to 60 % is a soil mass of 525 to 552 g, plus the empty pot's own mass.
  - Use the new mix's own dry and saturated masses.
  - Log each watering in `field_log.csv`.
- [ ] Count emergence daily per pot. Take phone photos, labelled as supplementary only.
- [ ] **Sat Nov 21: checking.** Write the panel's decision into `field_log.csv` and the event log the same day.
- **If replanting:**
  - [ ] Fix the power supply.
  - [ ] Check the probe wiring.
  - [ ] Fix the saucers and the P-06 outlet.
  - [ ] Prepare the firmware calibration change (step 4).
- **If not replanting:** keep everything as it is. Keep growing the new pots as the comparison, and stop here.

### Day 7: Wed Nov 26, swap day (only if replanting)
Work in daylight. Unplug the pump before touching any probe: a probe in air reads 0 to 6 % and triggers a dose.

1. **End run 2 properly.**
   - Take a last noon capture if the timing allows.
   - Harvest the current plants: fresh weight on the 0.01 g scale with `record_harvest.py`, and photos.
   - Don't throw them away without weighing; this is run 2's final data.
2. **Pull a copy of the Pi's data to the laptop** (`pull_from_pi.bat`), then push it from the laptop.
3. **Calibrate the probes on the new soil.** Use the oven-dried and saturated samples, and read each probe's ADC (the web page at 192.168.4.1 or `GET_RAW`). That gives new `dryADC` and `wetADC` per probe.
4. **Firmware:** put the new `dryADC`/`wetADC` values (and the band map, if randomising) in `main.cpp`, flash, and confirm that the readings in air and in saturated soil look right. Log the commit.
5. **Thin each pot to 1 seedling.** Choose the 9 most uniform for the rig and log which ones.
6. **Move the pots in:** the same positions, probes at the same depth and the same distance from the tube outlets. Don't move the camera.
7. **Camera:**
   - Re-fit the pot circles on a daylight frame, by hand or with a per-pot rim fit, not `make_rois.py`.
   - Back up the old `pot_rois.json` and add a line to `_comment`.
   - Make a new `align_ref.png` reference photo.
   - Check with `tools/roi_view.py`, subtracting 70 from any y value.
8. **Start the run:** `agrisentry.sh new-run 2026-11-20` (the **sowing** date, so D1 = Nov 20; it archives run 2 and turns on germination mode).
   - Check `sowing_date.txt`.
   - Dry-run the capture with `--test-image` and `--no-write`.
   - Don't run `agrisentry.sh start` (it turns the hourly camera job back on, and that job crashes the Pi).
9. **Log every step** in `field_log.csv` and the event log.

### Day 8: Thu Nov 27
- [ ] Before noon: `agrisentry.sh bands-on`.
- [ ] After 12:55: check that D8's 9 rows are in `growth_dataset.csv`, look at the overlay, and run `check_pi.bat`.

---

## Things we don't know yet (answer before Day 1)

- Do you have, or can you get, 15 to 20 pots identical to the rig pots?
- Is there a spare soil probe for calibration? If not, the calibration waits for swap day, when the rig probes come free.
- Is the old 8:4:3 mix still available for the comparison pots?
- When does the pH sensor arrive?
- What does the second checking require (see above)?
