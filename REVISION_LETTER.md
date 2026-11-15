# Revision Letter to the Thesis Panel

**November 12, 2026**

**Dr. Luis Gerardo S. Cañete, Jr.**  
**Engr. Andre Kimberly Trish D’Silva**  
**Engr. Kenneth Carl Labarosa**  
Department of Computer Engineering  
University of San Carlos – Technological Center  
Nasipit, Talamban, Cebu City  

**Dear Members of the Panel:**

We, the undersigned 4th-year Computer Engineering students and proponents of the research project entitled **"COMPUTER VISION-BASED GROWTH MONITORING AND YIELD PREDICTION FOR PECHAY UNDER DIFFERENTIAL SOIL MOISTURE TREATMENTS IN A GREENHOUSE"**, respectfully submit the following documented revisions and empirical refinements implemented in our research project and manuscript.

---

### 1. Soil Medium Composition and Pot Geometry (Sections 1.7, 3.1, and 3.2)
* **Effect on functionality:** None. The automated irrigation system, vision pipeline, and three differential moisture treatments operate identically. Only the substrate proportions and container dimensions are now explicitly quantified.
* **Change:** The proposal described the medium generically as Department of Agriculture (DA) soil "composed of loam, organic compost, and carbonized rice husk" without a fixed ratio, inside 200 mm pots. The medium is now batch-mixed by volume using a standardized **8:4:3 volumetric ratio**:
  * **8 parts** garden soil (53.3%)
  * **4 parts** carbonized rice hull / rice husk (26.7%)
  * **3 parts** vermicast (20.0%)
  
  Each specimen is grown in an identical truncated-cone polyethylene pot (**110 mm top diameter, 85 mm base diameter, 80 mm soil depth**), yielding a geometric soil volume of **$601\text{ cm}^3$ ($0.60\text{ L}$)** and holding **$388\text{ g}$ of oven-dried soil** and **$662\text{ g}$ when saturated** ($274\text{ mL}$ water capacity). Using this gravimetric baseline, the two-point relative soil moisture scale ($0\% = 2483\text{ ADC}$ oven-dried at $150\,^\circ\text{C}$ for 6 hours; $100\% = 1120\text{ ADC}$ saturated) maps directly to True Volumetric Water Content via $\text{True VWC} \approx \text{Relative SM} \times 0.456$.
* **Reason:** Quantifying the exact volumetric recipe and pot water-holding capacity ensures that all nine pots share an identical physical and chemical baseline, satisfying the substrate uniformity control required in Chapter 3 and grounding the sensor readings in physical volumetric water content.

---

### 2. Final Camera Module, Mounting Height, Pot Spacing, and ROI Partitioning (Sections 3.2, 3.4, and 3.5)
* **Effect on functionality:** None. The daily noon capture schedule, HSV color segmentation ($38 \le H \le 85$, $S \ge 100$, $V \ge 55$ in OpenCV units), and $3 \times 3$ morphological opening remain unchanged.
* **Change:**

| Parameter | Proposal Draft (v2.8) | Deployed Implementation (Revised) |
| :--- | :--- | :--- |
| **Camera Module** | Raspberry Pi Camera Module V2 (8 MP) | **Raspberry Pi Camera Module 3 (Sony IMX708, 12 MP)** capturing at $1296 \times 1296\text{ px}$ ($2\times$ binned), focus and white balance locked |
| **Camera Height** | ~1100 mm above pot rim plane | **1360 mm (136 cm)** from lens to the top of the pot/soil plane (**1440 mm** above the bench surface), yielding $1.34\text{ px/mm}$ resolution |
| **Pot Spacing** | 350 mm center-to-center (150 mm edge-to-edge) | **~260 mm center-to-center (~150 mm edge-to-edge)** across the $3 \times 3$ array |
| **ROIs & Canopy Metric** | Rectangular bounding boxes in `pot_rois.json` | **Circular pot ROIs of 154 px diameter ($r = 77\text{ px}$)** plus **non-overlapping Voronoi pot-area cells (`cell_gpr`, bounded at $r = 175\text{ px}$)** locked in `pot_rois.json` |

* **Reason:** Section 3.2 states that the final mounting height is empirically established and locked during pre-deployment calibration. Circular ROIs match the round pot rims, while the Voronoi pot-area cell (`cell_gpr`) ensures that seedlings leaning outward past their pot rim remain attributed to their own pot without overlapping neighboring pots.

---

### 3. 3D-Printed Enclosures for Actuators and Raspberry Pi / Camera Assembly (Section 3.8, Appendix 4)
* **Effect on functionality:** None. The electronic circuits and interconnections are unchanged; the enclosures house and protect them.
* **Change:** Custom 3D-printed **PLA enclosures** were designed in CAD and fabricated in-house:
  1. A **three-tier stacked actuator enclosure** housing the ESP32-S3 controller and relay banks on the top tier, the diaphragm pump and four solenoid valves on the middle tier, and the remaining five solenoid valves on the bottom tier.
  2. A **vented overhead camera and controller housing** with integrated cooling fans and pipe clips that clamps the Raspberry Pi Zero 2W and Camera Module 3 directly to the overhead roof structure.
* **Reason:** Raising the actuator assembly into a tiered enclosure protects the relays and PCB from ground splash and humidity. Clamping the combined Raspberry Pi and camera housing rigidly to the overhead frame keeps the nadir viewpoint constant across the 30-day cycle.

---

### 4. Pre-Deployment Trial Runs Before Final Data Collection (Section 3.5, Chapter 4)
* **Effect on functionality:** None. The trial runs were used strictly to commission, debug, and validate the hardware and vision pipeline; their records are archived separately from the final Run 2 dataset.
* **Change:** Two preliminary runs preceded the final grow-out:
  * **First Trial (September 2026 — prototype greenhouse of half-inch PVC pipes, UV plastic, and mesh):** Confirmed end-to-end sensing, irrigation, image capture, and logging, but revealed that the half-inch PVC frame flexed under roof load and admitted rainwater, motivating the timber rebuild in Item 5.
  * **Second Trial / Run 1 (sown October 6, 2026 — timber greenhouse at initial site):** Identified and resolved:
    1. Soil moisture probe channel rotation, corrected in firmware and verified via an interactive probe-mapping utility.
    2. Pot ROI circle offsets, re-fitted to the pot rims.
    3. Minor camera shifts between days, now corrected via phase-correlation image alignment against a locked reference frame (`align_ref.png`) and Voronoi cell attribution (`cell_gpr`).
    4. Midday power interruptions, mitigated via automatic cron retries every 10 minutes from 12:00 to 12:50 PM.
    5. Provided the noon frames (D12–D13) used to benchmark automatic GPR segmentation against independent manual leaf annotations (`Dual_Archi/tools/gpr_validate.py`). Because the initial site was overly shaded for normal vegetative growth, the run was concluded and the greenhouse was relocated (Item 8).
  * **Final Run / Run 2:** Sown on **October 29, 2026 ($D = 1$)** for the 30-day cycle concluding on **November 27, 2026 ($D = 30$)**.
* **Reason:** Operating the full system on live plants prior to the final dataset allowed hardware, wiring, and vision faults to be eliminated in accordance with Section 3.5.

---

### 5. Timber-Framed Greenhouse Rebuilt from Scratch (Sections 3.1 and 3.8)
* **Effect on functionality:** None. The cultivation layout and electronics remain unchanged; only the physical enclosure was upgraded.
* **Change:** The greenhouse was rebuilt using:
  * **1.5-inch nominal square wooden timber posts** for the structural frame
  * **Plywood platform** for the planar cultivation bench
  * **Pitched PVC roof frame** secured with custom 3D-printed PLA clip-ons and covered by a **$200 \times 200\text{ cm}$ UV-stabilized polyethylene sheet**
  * **Four $120 \times 60\text{ cm}$ fine insect mesh panels** enclosing the side walls
* **Reason:** The timber frame eliminates structural flexing under wind and roof load, holding the overhead camera at a fixed geometry above the 9-pot array.

---

### 6. BMP388 Temperature Sensor and Automated Cooling Fans for Electronics (Section 3.8, Appendix 4)
* **Effect on functionality:** None. Irrigation and vision pipelines operate as specified; these components protect the edge processors from thermal throttling.
* **Change:** A **BMP388 temperature and pressure sensor** was interfaced to the ESP32-S3, together with relay-actuated brushless cooling fans inside the electronics housings. The fans switch **ON at $35\,^\circ\text{C}$** and **OFF at $32\,^\circ\text{C}$** (hysteresis control).
* **Reason:** Because the Raspberry Pi Zero 2W runs continuously inside an enclosure and executes image capture at solar noon when ambient enclosure temperatures can exceed $40\,^\circ\text{C}$, active cooling prevents CPU thermal throttling and ensures reliable noon execution.

---

### 7. Removal of Supplemental Overhead LED Array in Favor of Exposure Normalization (Sections 1.5, 2.5, 3.4, 3.5, Appendix 7)
* **Effect on functionality:** None. Images are still captured daily at solar noon and segmented via HSV thresholding.
* **Change:** The overhead LED array was removed. Illumination consistency across daily captures is maintained by:
  * Locking camera focus, analogue gain ($1.0$), and white balance gains ($1.8, 1.6$)
  * Running an automatic exposure-convergence loop prior to each capture so that mean frame brightness matches a standardized target luminance (**$V = 73$**), logged daily in `exposure_log.csv`
  * Placing a matte dark background cloth beneath the pots for uniform high-contrast soil/background separation
  * Running an automated per-pot glare diagnostic (`glare_check.py` $\rightarrow$ `glare_log.csv`) on every noon frame
  * Restricting capture to solar noon (12:00 PM, with retries up to 12:50 PM)
* **Reason:** In bench testing, switching the LED array caused transient current drops that reset the Raspberry Pi, while contributing negligible irradiance compared to midday tropical daylight. Normalizing camera exposure to a locked target luminance ($V = 73$) with fixed white balance directly stabilizes HSV values across varying cloud cover without risking brownouts.

---

### 8. Greenhouse Siting for Optimal Direct Sunlight (Section 3.1)
* **Effect on functionality:** None. The experimental design and hardware are unchanged; only the physical siting of the enclosure was moved.
* **Change:** Prior to sowing Run 2 on October 29, 2026, the greenhouse was relocated to an open sunlit cultivation site receiving approximately **4 to 6 hours of direct morning-to-midday sunlight daily** (from ~7:30 AM until ~12:00 noon), with partial afternoon shade preventing extreme thermal stress.
* **Reason:** The shaded site used during Trial 2 caused etiolation (stem stretching) and slow leaf expansion. The relocated site provides sufficient photosynthetic photon flux for healthy vegetative development while avoiding afternoon heat stress.

---

### 9. Grow-Out Period Refined from 35 Days to 30 Days (Sections 1.4, 1.7, 3.1, 3.6, Table 1.1, Appendices 6 and 8)
* **Effect on functionality:** None. The 9-pot differential treatment design, the parsimonious 6-term polynomial regression model, and the Leave-One-Plant-Out Cross-Validation (LOOCV) protocol are unchanged. The full 30-day cycle yields up to **9 plants $\times$ 30 days = 270 rows** (with D2–D3 power outage days transparently recorded as missed captures), and physical harvest occurs on **$D = 30$ (November 27, 2026)** immediately following the final noon capture.
* **Change:** The grow-out cycle duration was adjusted from 35 days to **30 days after sowing ($1 \le D \le 30$)**.
* **Reason:** Thirty days falls squarely within the established 30- to 45-day harvest window for Pechay (*Brassica rapa* subsp. *chinensis*) documented in agronomic literature (Camariosa & Gurrea, 2021; Ding et al., 2022) and institutional precedent (Zamora et al., 2025). Because LOOCV generalizes across the 9 independent plant units (training on 8 plants, testing on the held-out 9th plant across 9 folds), the effective sample size of independent biological replicates ($N = 9$) is unchanged, while allowing the complete Run 2 grow-out and harvest analysis to conclude within the academic term.

---

We are happy to meet with the Panel at your convenience to discuss or demonstrate any of the revisions enumerated above.

Respectfully yours,

**Rey Emmanuel C. Adag**  
Researcher 1  

**Kent Vincent S. Godinez**  
Researcher 2  

**Cedric Vince M. Tan**  
Researcher 3  

---

**Noted by:**

**Engr. Alvin Joseph S. Macapagal**  
Main Adviser  

**Engr. Linda E. Saavedra**  
Assistant Adviser  

---

**Approved by:**

**Dr. Luis Gerardo S. Cañete, Jr.**  
Panel Chair  

**Engr. Andre Kimberly Trish D’Silva**  
Panel Member  

**Engr. Kenneth Carl Labarosa**  
Panel Member  
