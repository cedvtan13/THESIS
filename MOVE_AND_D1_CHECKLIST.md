# Greenhouse move (Oct 28 night) and run 2, D1 (Oct 29)

The panel checks the system from D1 (sowing) to D30, so everything has to be logging before the seeds go in.
- **D1 = Oct 29, D30 = Nov 27.**
- 1st checking (1st week of November) ≈ D5–D10.
- 2nd checking (Nov 23–28) ≈ D26–D30.

---

## A. Before you unplug anything (tonight, at the old spot)

- [ ] **Label everything with its pot number:** each pot, probe cable, valve tube and relay wire. Masking tape is fine. In run 1, the probes ended up rotated 180°, so every pot read another pot's moisture until Oct 16.
- [ ] **Photograph the wiring:** the ESP32 board, the relay board, the MUX and the valve manifold.
- [ ] **Photograph the pot layout from above.** Row by row, the top row is P-03 P-02 P-01 (right to left). Keep the same layout at the new spot; the software assumes it.
- [ ] **Shut the Pi down properly** before you unplug it (`sudo shutdown -h now`, wait for the green light to stop). Pulling the plug can corrupt the SD card.

## B. The new spot

- [ ] **At least 6 hours of direct sun**, ideally 9 am to 3 pm. Look for walls, trees and roofs that will shade the pots in the morning or afternoon, not only at the moment you look.
- [ ] **Heat:** more sun makes it hotter under the cover. Pechay does best at about 18–30 °C, and above about 35 °C it wilts or bolts. Keep the sides able to open for air, and check the temperature at noon tomorrow (phone weather or a thermometer at pot level).
- [ ] **Level ground**, so water doesn't run to one side of each pot.
- [ ] **No shade from the rig itself:** at noon the sun is almost overhead, so the camera pole and arm must not throw a shadow over any pot.
- [ ] **Electronics in the shade and dry:** keep the Pi, ESP32, relays and power supply out of direct sun and rain. A Pi in a box in full sun overheats.

## C. Rebuild

- [ ] **Power:** use a rain-safe extension cord and tape the Pi's cable down so nobody trips on it or pulls it (most of run 1's 17 power cuts came from that).
- [ ] **Camera:** rigid mount, lens pointing straight down, **136 cm from the lens to the soil** (same as run 1, so the size scale stays the same). Tighten everything; in run 1 the camera drifted 15 px in a week.
- [ ] **Pots:** same layout, roughly the same spacing. All 9 must be fully in view with some margin.
- [ ] **Soil:** reuse it, but mix it all together first so every pot starts the same. Fill each pot with the **same weight** of soil (weigh it) and write down the number.
- [ ] **Moisture:** the soil should be **moist, not soaked**. In run 1 the soil started saturated and the low group took 10+ days to dry down. Empty all saucers.
- [ ] **Probes:** each in its own labelled pot, at the same depth and distance from the edge, pushed straight in with no air gap.

## D. Start the software (on the hotspot, from the Mac)

Run these in the THESIS folder:

1. Check that everything came back up:
   ```bash
   ./system.sh status
   ```
2. Start the new run. This moves all of run 1's data (CSVs, logs, photos, field log) into `~/archive/` on the Pi (nothing is deleted), sets D1 = Oct 29, and puts the ESP32 in germination mode (all pots kept at 50–60%):
   ```bash
   ./system.sh new-run 2026-10-29
   ```
3. Test that every valve opens for the pot it's labelled with:
   ```bash
   ./actuator_test.sh
   ```
4. **Probe-mapping test:** run `python3 ~/thesis/tools/map_probes.py` on the Pi. When it says READY, pull the probes out into the air one at a time, in order from P-01 to P-09, and check that each one shows up as the right channel. Push them back in the same spot. This catches swapped cables (the run-1 problem). The tool pauses the logger, so restart it afterwards with `sudo systemctl restart pi-link`.
5. **Leak test:** leave the pump off and the valves closed for 1 hour, then check that no saucer has water in it (this was the P-06 problem).
6. **Re-fit the pot circles.** The camera moved, so the old circles are wrong. Take one frame and send it to Claude; it fits the circles. This **must be done before 12:00 on Oct 29**, or D1's capture will measure the wrong spots.

## E. Sowing morning (Oct 29, D1)

- [ ] Sow **3–4 seeds per pot**, in the centre, at the same depth. Write the seed count in the field log.
- [ ] Sow a **backup tray** (10–20 seeds) beside the pots, for replacements.
- [ ] Take a photo of the pots at sowing time (for the panel).
- [ ] After 12:50, check that D1 was captured:
  ```bash
  ./system.sh status
  ```
  It should show `growth_dataset=9`.
- [ ] Look at the check picture the Pi saved: `~/agrisentry_data/frames/overlay/D01_overlay.jpg`. Each pot should sit inside its own yellow outline.

## F. During the run

- **D7–D10, thin:** keep the single best seedling per pot. Choose so the 9 kept are as similar as possible, and log which pots were thinned.
- **Starting the treatments:** after thinning, switch from germination mode to the three moisture bands, then log the day:
  ```bash
  ./system.sh bands-on
  ```
  Ask the panel or sir AJ which day they want the treatments to start (D8 is our proposal).
- **New, automatic:**
  - Every noon capture now records **pot-area GPR** (`cell_gpr`), so leaning plants are no longer lost.
  - A **check picture** is saved every day.
  - An **hourly light reading** is logged from the camera to `light_log.csv` (6:30 am to 6:30 pm, skipping 12:xx).
- **Every day:** run `./system.sh status`, glance at the check picture, and add anything unusual to the field log (rain, shade, pests, knocks, power cuts).
- **Don't** leave `live_feed` running near 12:00; the camera can only be used by one program at a time.

## G. Reliability tests to fit in (for the panel)

- In the first week, run the sensor check 3 times, do the cup test for dose accuracy (3× per valve), and the oven-dry soil sample next to one probe.
- **Camera repeatability:** take 5 frames in a row, compare their GPR, and photograph a green card of known size.
- **Scale check:** weigh a known mass 3× before harvest.
