# Irrigation Firmware — Team Briefing (rev 2)

**Project:** Computer Vision-Based Growth Monitoring and Yield Prediction for Pechay Under Differential Soil Moisture Treatments in a Greenhouse
**Checked against:** the manuscript endorsed 01 July 2026 (`Group-B_Revisions.pdf`)
**Cross-referenced with:** Aala et al. (2022) and Zamora et al. (2025) full manuscripts
**For:** Cedric Tan (Systems & Firmware), Rey Adag (Agronomy & Infrastructure)

> This revision exists because the first draft of this briefing was written against an earlier copy of our manuscript. Several claims in it were wrong or out of date. Corrections are marked below.

---

## 1. Files in this package

| File | What it is | Runs on |
|---|---|---|
| `irrigation_controller.ino` | Irrigation firmware (Arduino framework, C++) | ESP32-S3 |
| `pi_link.py` | Serial bridge + CSV logger | Raspberry Pi Zero 2W |
| `wiring_schematic.svg` | Pin-level wiring diagram | figure for Appendix B |

---

## 2. Does the manuscript say we are remaking Zamora's setup?

Not in those words, and the distinction matters. Here is what it actually says:

- **Abstract:** the system *"builds upon the validated solenoid-based automated irrigation approach from prior institutional work (Zamora et al., 2025), which serves as a controlled baseline."*
- **Section I.C:** *"Rather than introducing new irrigation hardware, this study reuses the validated solenoid-based automated irrigation approach demonstrated by Zamora et al. (2025) to enforce three distinct soil moisture treatment groups."*
- **Section I.F:** *"By building directly upon the irrigation hardware already validated by Zamora et al. (2025), this study avoids duplicating prior hardware contributions."*
- **Section II.F:** *"inheriting and redeploying the validated automated irrigation approach."*
- **Section III.A.3:** *"The inherited 1:1 solenoid-based micro-irrigation system [6] is configured to maintain three independent soil moisture treatment groups."*

So the claim is that we inherit the **approach and architecture**, not their physical rig. And the manuscript is explicit about several intentional departures:

| Zamora et al. (2025) | Our manuscript | Where stated |
|---|---|---|
| Shared 0.4 × 1.0 m crop plot, grid cells | Nine isolated 3.0 L container pots | I.C, II.F, III.B |
| Jumper-wire interconnects | Custom PCB routing interface | III.C |
| Uncoated sensors | Industrial conformal coating | III.C |
| One optimal moisture band | Three differential VWC bands | I.E, III.A.3 |
| Weather API, cloud DB, mobile app, pH sensing | All excluded | I.G |

That's a defensible position, and the wording is careful. **But there is one departure the manuscript does not disclose**, and it is a real one — see the next section.

---

## 3. Finding: we added a pump; Zamora did not have one

Zamora et al. Section 3.2: *"A 5-gallon water container served as the water source for the system. Due to the small scale of the land, a **gravity-based water flow system was chosen over a water pump**."* Aala et al. did the same (their Section II.B).

Our Appendix D lists a **12 V Diaphragm Water Pump**, and Figs. 6 and 7 both show it. So our irrigation hardware is not a pure inheritance — we have replaced their hydraulic source.

This is probably the right engineering call: nine separated pots on a 3 × 3 bench need consistent delivery pressure to each outlet, and gravity head varies as the reservoir drains (Aala's own Appendix Q documents exactly that — flow rate drops measurably between a full and half-full container). But because Section I.C claims we are *"not introducing new irrigation hardware,"* the pump reads as an undisclosed contradiction. **Add one or two sentences to Section III acknowledging the change and justifying it.**

**Practical consequence for the firmware:** Zamora's measured flow of roughly 1 mL/s (their Table 3.1) is a *gravity-fed* figure and does not transfer. A small diaphragm pump will be one to two orders of magnitude faster. The firmware placeholder has been changed accordingly, but this must be measured.

---

## 4. Re-evaluation of every claim I made earlier

| # | Earlier claim | Verdict | Correction |
|---|---|---|---|
| 1 | The Pi does not control the solenoid valves | **Holds.** Figs. 6 and 7 both route sensors and valves through the ESP32-S3 only | — |
| 2 | Zamora's GitHub repo contains no ESP32 firmware | **Holds.** Repo is Flutter app + one Firebase Cloud Function; zero `.ino`/`.cpp`/`.h` files | — |
| 3 | No SD card module in our BOM | **Holds.** Appendix D unchanged | — |
| 4 | No RTC in our BOM | **Holds** | — |
| 5 | Sensor and valve quantities are 4, design needs 9 | **Holds.** Appendix D still says 4 and 4 | — |
| 6 | No microSD listed for the Pi | **Holds** | — |
| 7 | UPS still "model TBD" | **Holds**, and see finding 5.6 below | — |
| 8 | "No relay or MOSFET driver board is listed" | **Partly wrong** | Appendix B, Fig. 7 *does* show a "Relay Board / Solenoid Driver" block. The **concept is in the manuscript**; only the BOM line item is missing. My first version overstated this, and my second version still did not credit Fig. 7 |
| 9 | Zamora used discrete transistors, not a relay board | **Holds.** Their Appendix E lists 2N2222 transistors, 1N4007 diodes, capacitors, a 7805 and heatsink | — |
| 10 | Our manuscript specifies a 2-hour stabilization window | **Wrong** | That was in an earlier draft. The current revision contains no stabilization window anywhere. It needs to be added |
| 11 | Polling interval is 2–4 hours | **Wrong** | The current revision states no interval. Appendix C only says "24/7" |
| 12 | Camera at 950 mm | **Out of date** | Section III.B now specifies ~1100 mm nadir, 350 mm pot pitch, 900 × 900 mm array footprint. The schematic has been updated |
| 13 | `PUMP_FLOW_ML_PER_S ≈ 1.0` citing Zamora | **Wrong** | That was their *gravity* flow. Placeholder changed to 20 mL/s for a diaphragm pump |
| 14 | `ML_PER_PERCENT ≈ 25` | **Refined to 10** | Scaled from Zamora's 23.92 mL/1 % for an 8000 g container down to our 3.0 L pot. Still a placeholder |
| 15 | The manuscript has no ESP32 → Pi data path | **Holds, and is worse than I said** | Appendix C step 7 *draws* the SM handoff and Appendix G line 14 *assumes* it, but Appendix A Fig. 6 shows **no link at all** between the two layers, and no section names a medium |

---

## 5. Gaps and inconsistencies found in the current manuscript

### 5.1 Fig. 7 still says "Duty-Cycled Vision" and "Edge AI Device"

Appendix B labels the Raspberry Pi branch **"Duty-Cycled Vision"** and the Pi itself **"(Edge AI Device)."** Both contradict the current text:

- Section III.D.1 and I.G specify an **always-on** Pi, precisely to avoid boot-cycle failures.
- Appendix C explicitly states *"Continuous operation — all controllers remain powered 24/7."*
- There is no machine learning anywhere in the study. Sir Luis questioned the "edge vision" framing directly at the reproposal, and the title now avoids it — but the figures did not follow.

These are remnants of the earlier duty-cycled design. Fig. 7 needs relabelling, and "Edge-Vision Processing Layer" in Fig. 6 is worth reconsidering too.

### 5.2 Section III.G still describes deep sleep

*"the ESP32-S3 demanding approximately 80mA during deep-sleep polling states."* Two problems: the architecture is always-on, so there is no deep sleep; and 80 mA is not a deep-sleep figure by several orders of magnitude (the S3 deep-sleep spec is single-digit microamps). Another remnant.

The same sentence attributes a **240 mA peak "during localized solenoid valve actuation" to the 3.3 V logic rail.** The solenoid draws its current from the **12 V rail through the driver stage**, not from the microcontroller. The power table should separate the two rails.

### 5.3 Fig. 6 shows no link between the controllers

Appendix A draws the telemetry layer and the vision layer as two boxes joined only by "Wall Outlet + UPS." But Appendix C step 7 shows *"Latest volumetric water content (SM) from baseline log"* passing from the ESP32 to the Pi, and Appendix G line 14 depends on it.

Without that link the regression has no SM column, and the model in Equation 1 collapses from three variables to two. Fig. 6 must be updated, and Section III must state the medium. `pi_link.py` implements it over UART because that adds no BOM item and no network dependency.

### 5.4 The driver stage is in the figure but not the BOM

Fig. 7 shows it; Appendix D does not itemise it. We need roughly 10 switching channels (9 valves + pump), each with a flyback diode. Two routes:

- **Discrete, the way Zamora did it** — transistors plus 1N4007 flyback diodes on our custom PCB, which we already budget ₱800 for. Cheapest, matches the lineage, and the PCB is itself an improvement over their jumper wiring.
- **A pre-made 16-channel relay board** — simpler, more robust, but an extra line item.

Either way, **the flyback diodes are not optional.** Cutting current to a coil produces a reverse voltage spike that will destroy the switching device.

*Caution:* Aala et al. spec the solenoid at 540 mA (their Appendix F). A 2N2222 in TO-92 is rated around 600 mA — workable at one valve at a time, but with little margin. A logic-level MOSFET such as an IRLZ44N handles it comfortably. Measure the actual coil resistance before committing.

### 5.5 Germination-window risk is acknowledged but not mitigated

Section I.G now correctly notes that the probes sit *"at a depth substantially below the placement depth of the sown seed"* and that emergence differences cannot be attributed to the reported VWC band.

The unaddressed risk: for **Group A (30–40 %)** the root-zone band may leave the surface layer too dry for the seed to germinate at all during D = 1 to 7. If Group A fails to emerge, we lose three of nine plants and one entire treatment level — which is one third of the variance the SM term depends on.

Worth discussing with Rey. Options include a uniform surface-wetting protocol until emergence (logged as a documented deviation), or starting the differential treatments only from emergence onward with the day index adjusted accordingly.

### 5.6 UPS runtime has no shown calculation — and do not copy Aala's

Section III.G.1 claims *"approximately 4 hours of continuous runtime."* No working is shown.

**Do not reproduce Aala et al.'s Appendix F method.** Their calculation takes a daily energy figure of 1.596 Wh, divides by 12 V to get "0.133 A," then divides 7 Ah by that to claim 52.63 hours of runtime. That is dimensionally invalid — a per-day energy total is being used as an instantaneous current. Copying it will not survive a panel question.

A defensible version: state the continuous load (Pi ≈ 0.75 W, ESP32 ≈ 0.3 W, plus supply-module and inverter losses, which for a 650 VA class unit dominate at this tiny load), state usable battery energy (12 V × 7 Ah × depth-of-discharge × inverter efficiency), and divide. Our 4-hour figure is in a plausible range; it just needs the arithmetic shown.

### 5.7 Two small deliverable-table mismatches

Sir Luis said explicitly he would check our results **item by item against Table I**, so these are worth tidying:

- **Deliverable 2** asks for a *"Day 0 pH measurement table,"* and Section III.A.1 says the pH spot-check happens *"at Day 0."* But the new Cultivation Timeline paragraph defines **D = 1** as the sowing date. Day 0 is now undefined. Pick one index.
- **Deliverable 3** asks for *"Nine 35-day GPR time-series CSV files,"* but Appendices G and H describe a **single** `growth_dataset.csv` with a Pot ID column. Nine files or one — decide and make both places agree.

### 5.8 Firmware provenance is not stated anywhere

The manuscript never says where the ESP32 firmware comes from. Since Zamora's was never archived, ours is reimplemented from the pattern published in Aala et al., Appendix R. One sentence in Section III would close this, and it also protects us from an "is this really inherited?" question.

---

## 6. What the firmware does

1. Polls all nine sensors every 15 minutes, taking a median of nine samples each.
2. Enforces the three treatment bands of Section III.A.3.
3. When a pot falls below its band, computes a dose in millilitres, opens that pot's valve, runs the pump for the corresponding time, closes up, and locks that pot out for two hours.
4. Reports a full SM snapshot every 30 minutes, and on demand when the Pi asks at noon.
5. Detects sensor faults and quarantines a pot after three consecutive faults, so a broken probe cannot cause runaway watering → Deliverable 7.
6. Stores per-pot irrigation state in non-volatile memory so a brownout cannot cause double-watering → Section III.G.1.

Only one valve is ever open at a time, since there is one shared pump. The valve opens before the pump starts and closes after it stops, so the pump never runs against a closed line.

### Serial protocol

ESP32 → Pi:

```
SM,<epoch>,P-01…P-09                     → SM column, Deliverable 5
EVT,<epoch>,pot,group,vwc,target,mL,ms   → Deliverable 1
ERR,<epoch>,code,detail                  → Deliverable 7
```

Pi → ESP32: `TIME,<unix_epoch>` · `GET_SM` · `PING` · `STATUS`

---

## 7. Pin map

| Function | GPIO | Direction |
|---|---|---|
| P-01 … P-09 moisture sensors | 1, 2, 3, 4, 5, 6, 7, 8, 9 | Analog in (ADC1) |
| P-01 … P-09 solenoid driver channels | 11, 12, 13, 14, 15, 16, 21, 38, 39 | Digital out |
| Pump driver channel | 40 | Digital out |
| UART1 → Pi RXD (physical pin 8) | 17 | TX |
| UART1 ← Pi TXD (physical pin 10) | 18 | RX |
| Spare | 10, 41, 42, 47 | — |

Sensors must sit on **ADC1 (GPIO 1–10)** — ADC2 is shared with the radio, which is the same limitation Section III cites for choosing the S3.

Avoided: GPIO 0, 3, 45, 46 (strapping); 19, 20 (USB D−/D+); 26–32 (flash); 33–37 (octal PSRAM); 43, 44 (UART0 console); 48 (onboard RGB LED).

Both boards are 3.3 V logic, so no level shifter — but **they must share a common ground.**

---

## 8. Constants that must be measured

**8.1 `dryADC[]` / `wetADC[]`** — two-point calibration per sensor per Section III.E.1. Nine pairs.

**8.2 `ML_PER_PERCENT`** — millilitres to raise one pot by one sensor-percent. Because calibration sets bone-dry = 0 and saturated = 100, our "%" is a **relative saturation index, not true volumetric water content**, so it cannot be derived from pot geometry (1 % of 3.0 L is *not* 30 mL). Placeholder is 10 mL, scaled from Zamora's measured 23.92 mL/1 % for an 8000 g container. Replicate their drying-and-weighing procedure on one of our own pots.

*This nuance deserves a sentence in Section III* — a panel member could reasonably ask what our percentages physically represent.

**8.3 `PUMP_FLOW_ML_PER_S`** — measured into a beaker through one open solenoid and our actual tubing. Placeholder is 20 mL/s. **Do not use Zamora's 1 mL/s** (gravity-fed, no pump).

Also confirm with a multimeter whether the driver board is active-HIGH or active-LOW before connecting anything to water — there is a `RELAY_ACTIVE_LOW` flag at the top of the firmware.

---

## 9. Testing plan

Six stages, cheapest and safest first. **No water anywhere near the system until Stage 5.**

**Stage 1 — Compile.** *(~10 min, no hardware)* Arduino IDE → Preferences → add the Espressif ESP32 boards URL → Boards Manager → install "esp32". Board: ESP32S3 Dev Module. Press Verify. The firmware uses only `Preferences.h`, which ships with the core, so nothing to install.

**Stage 2 — Logic check.** *(ESP32 alone, nothing wired)* Serial Monitor at 115200, line ending "Newline". Commands are accepted over USB as well as over the Pi link, specifically so this works with no Pi attached.
- `PING` → `PONG,...`
- `STATUS` → nine `STAT` lines; check P-01…P-03 read `A_Low,30,40`, P-04…P-06 `B_Optimal,50,60`, P-07…P-09 `C_High,70,80`
- `TIME,1767225600` → `ACK,TIME,...`

With no sensors attached the pins float, so `SENSOR_RANGE` errors and pot quarantines are **expected and correct** — that is fault detection working.

**Stage 3 — Sensor check.** *(sensors wired, no driver board, no water)* One sensor on GPIO 1, held in air then in a glass of water, `GET_SM` after each. The value should swing sharply. If it barely moves or moves the wrong way, swap `dryADC`/`wetADC`. Repeat for all nine before the real soil calibration.

**Stage 4 — Valve check.** *(driver board wired, tubes DRY, reservoir empty)* Temporarily set `podConfig[0].lowerBound = 99.0f` so pot 1 always looks dry, send `TIME,...`, and listen. Expected order: valve 1 on, pump on, pump off, valve 1 off. Confirm it is **channel 1 and not channel 3**. Repeat per pot, then restore the real values.

**Stage 5 — Hydraulic calibration.** *(water, beaker)* Run the outlet into a beaker. Time an event and measure the volume → `PUMP_FLOW_ML_PER_S`. Then the drying-and-weighing test on one filled pot → `ML_PER_PERCENT`. Update both, re-upload, tighten `MAX_PULSE_MS`.

**Stage 6 — 72-hour soak.** Already promised in Section III.E.2. Run the whole system with `pi_link.py` going. Afterwards check that `sm_log.csv` has roughly one row per 30 minutes with no gaps and that `error_log.csv` is empty or fully explainable.

### Pi setup for the serial link

```
sudo raspi-config
    Interface Options → Serial Port
        login shell over serial?       → NO
        serial port hardware enabled?  → YES
    reboot
sudo apt install python3-serial
```

Then `python3 pi_link.py --ping` to confirm the link, `python3 pi_link.py` to run the logger. For Stage 6 it needs a `systemd` service so it survives reboots — Cedric's area.

---

## 10. Open decisions

**10.1 — Fail-safe vs fail-open on clock sync.** The firmware refuses to irrigate until the Pi sends `TIME`, because the two-hour lockout is stored as an absolute timestamp so a brownout cannot cause double-watering. The trade-off is that if the Pi never boots, nothing gets watered.

This is now **more defensible than when I first raised it**, because Section I.G has since gained the Manual Intervention Constraints clause and its deviation log. If the Pi is down, we water by hand and record the timestamp, pot, nature and justification. Over-watering, by contrast, silently destroys the separation between treatment groups — which is the whole experimental design. My recommendation is to keep the fail-safe. Rey's call carries weight since it is an agronomic risk too.

**10.2 — Polling interval and stabilization window.** The firmware samples every 15 min, reports every 30 min, and locks a pot out for 2 h after watering. **None of these numbers appear in the manuscript.** The 2 h figure traces to Aala et al.'s finding that soil moisture needs roughly two hours to redistribute, which Zamora carried forward — so it is citable. Either write these into Section III or change the code to match what we write.

**10.3 — Germination protocol for Group A.** See 5.5.

**10.4 — Backup setups.** Sir AJ advised that if we run backups we should run **three**, not two, so a disagreement can be broken by majority rather than by picking the result we prefer. He also said the backups may stay undocumented. Still unsettled.

---

## 11. Action items

| # | Item | Owner |
|---|---|---|
| 1 | Ask Sir AJ / Sir Ogue whether the second-iteration ESP32 sketch exists outside the GitHub repo, and whether their driver circuit was ever drawn | Kent |
| 2 | Itemise the driver stage in Appendix D: ~10 switching devices, 10 flyback diodes, base/gate resistors; measure valve coil resistance to pick the part | Rey + Cedric |
| 3 | Correct BOM quantities: 9 sensors, 9 solenoid valves | Rey |
| 4 | Add microSD card for the Pi to the BOM | Rey |
| 5 | Name a specific UPS model and **show the runtime arithmetic** — do not reuse Aala's Appendix F method | Rey |
| 6 | Run Stages 1–4 of the testing plan | Cedric |
| 7 | Write the `systemd` service for `pi_link.py` | Cedric |
| 8 | Bench-measure `ML_PER_PERCENT` and `PUMP_FLOW_ML_PER_S` | Cedric + Rey |
| 9 | Two-point calibrate all nine sensors and keep the log (Deliverable 1) | Rey |
| 10 | Decide fail-safe vs fail-open (10.1) and the Group A germination protocol (10.3) | All three |
| 11 | Relabel Fig. 7: remove "Duty-Cycled Vision" and "Edge AI Device" | Kent |
| 12 | Fix Section III.G: remove "deep-sleep", separate the 3.3 V and 12 V rails in the power figures | Kent |
| 13 | Add the ESP32 → Pi data path to Fig. 6 and name the medium in Section III | Kent |
| 14 | Add the polling interval and stabilization window to Section III, cited to Aala et al. | Kent |
| 15 | Disclose and justify the gravity → pump change | Kent |
| 16 | Add a sentence clarifying that "% VWC" is a relative saturation index | Kent |
| 17 | Add a sentence on firmware provenance (reimplemented from Aala et al., Appendix R) | Kent |
| 18 | Reconcile Day 0 vs D = 1, and nine CSVs vs one CSV, in Table I | Kent |
| 19 | Add the pin-level schematic to Appendix B alongside or in place of Fig. 7 | Kent |

---

## 12. Why the documentation items matter

At the reproposal Sir Luis said he could not accept the document as it stood, that our architecture needed clarifying, and — most importantly — that he would check our results **item by item against our goals, objectives and deliverables**:

> *"checkan na namo, na achieved bana niya nga deliverable kani og kani, which means kani siya nga goal na achieved. If any of those deliverables wala, wana ninyo na achieve inyo goal, mahagbong mo."*

Table I is now much stronger than it was. The remaining risk is not the table itself but the places where the **figures and the text disagree** — a duty-cycled Pi in Fig. 7 next to an always-on Pi in Section III.D, a deep-sleep ESP32 in Section III.G next to 24/7 operation in Appendix C, and a missing data link in Fig. 6 that Appendices C and G both rely on. Those are exactly the kind of thing a panel finds in five minutes.

Items 11 through 19 are all one-paragraph or one-figure fixes. None of them require new experimental work.
