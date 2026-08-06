# 📌 Thesis Project Context & System Prompt (`gemini.md`)

## 1. Project Identity & Metadata
* **Current Manuscript Title:** *Computer Vision-Based Plant Monitoring and Multivariate Yield Prediction for Pechay Under Differential Soil Moisture Conditions in a Controlled Greenhouse Environment*
* **Former Title:** *AgriSentry: An Edge-Vision IoT System for Automated Irrigation...*
* **Proponents:** Rey Emmanuel C. Adag, Kent Vincent S. Godinez, Cedric Vince M. Tan
* **Institution:** Department of Computer Engineering, University of San Carlos (USC)
* **Main Adviser:** M.Eng. Alvin Joseph S. Macapagal
* **Assistant Adviser / Panel:** Engr. Linda E. Saavedra, Dr. Luis Gerardo S. Cañete, Jr.

---

## 2. Strategic Scope Shift & Post-Hearing Revisions
Following feedback from Dr. Cañete and Engr. Saavedra during the proposal/re-proposal hearing:
* **Scope Cut (Dropped Components):** Commercial branding ("AgriSentry"), Mobile App, Web Dashboard UI, Firebase Cloud Backend, custom PCB highlight, custom rotary demultiplexer, and pH sentinel nodes.
* **Core Pivot:** The project is strictly defined as a **Computer Vision + Statistical Agronomic Yield Modeling** study.
* **Hardware Role:** Hardware operates strictly as an **Automated Baseline Environmental Controller** to maintain root-zone soil moisture stability, eliminating agronomic noise for the data model.
* **Baseline Lineage:** Inherits and adapts the 1:1 solenoid-based automated irrigation concept from prior USC institutional studies (*Aala et al., 2022; Zamora et al., 2025 / Ogue et al., 2024*).

---

## 3. Experimental & Agronomic Framework
* **Target Crop:** Pechay (*Brassica rapa*), 35-to-45-day growth cycle.
* **Environment:** Controlled greenhouse setup (USC campus) under uniform overhead LED illumination.
* **Container Grid:** 9 individual pots ($3 \times 3$ grid layout) to isolate root-zone variables.
* **Treatment Groups (Soil Moisture Bands):**
  1. Low Moisture Band (Near Permanent Wilting Point / PWP)
  2. Optimal Moisture Band (Field Capacity / FC)
  3. High Moisture Band (Near Saturation)
* **Variables & Metrics:**
  * **$X_1$ (Green Pixel Ratio - GPR):** Daily vegetative canopy coverage percentage extracted via overhead vision.
  * **$X_2$ (Soil Moisture - $SM$):** Volumetric Water Content percentage logged via capacitive sensors.
  * **$X_3$ (Day - $D$):** Phenological age within the 45-day cultivation cycle.
  * **$Y$ (Target / Ground Truth):** Final fresh-weight biomass (grams) measured on digital scales at Day 45 harvest.

---

## 4. Technical Architecture & System Pipeline

### A. Edge Vision Pipeline (`vision.py`)
* **Hardware:** Headless Raspberry Pi Zero 2W + Raspberry Pi Camera Module V2 mounted overhead ($950\text{ mm}$ height).
* **Operation:** Scheduled daily automated local cron job at noon (12:00 PM) operating headlessly without display GUI dependencies (`cv2.imshow` disabled/fallback).
* **CV Process:** RGB image capture $\rightarrow$ HSV color space conversion $\rightarrow$ Green color threshold masking $\rightarrow$ Contour extraction & GPR computation $\rightarrow$ Local CSV logging (`gpr_log.csv`).

### B. Baseline Microcontroller & Sensor Node
* **Microcontroller:** ESP32-S3 handling sensor polling, capacitive soil moisture sampling, and solenoid actuation.
* **Actuators:** Relay-controlled 12V Solenoid Valves (1 per pot).
* **Power Architecture:** 12V 10A PSU + Buck Converter (12V to 5V) + SLA battery UPS backup to prevent power cycle failures.

### C. Statistical Yield Prediction Model
* **Model Type:** Parsimonious Multivariate Polynomial Regression with interaction and quadratic terms:
  $$\tilde{Y} = \beta_0 + \beta_1 D + \beta_2 GPR + \beta_3 SM + \beta_4 D^2 + \beta_5 GPR^2 + \beta_6 (D \times GPR) + \beta_7 (GPR \times SM) + \epsilon$$
* **Validation Strategy:** Leave-One-Plant-Out Cross-Validation (LOOCV) across the 9 biological plants (405 daily data rows) to prevent spatial/temporal overfitting.
* **Defensive Justification:** Biological sigmoidal growth modeling, multi-variable cross-interaction tracking, and explicit acknowledgment of localized single-cycle coefficient scope in Section 1.7 (Scope and Limitations).

---

## 5. System Execution & AI Assistant Rules
When assisting with this project in CLI or chat sessions:
1. **Maintain Scope Discipline:** Do NOT re-introduce mobile apps, cloud servers, or complex hardware features that were cut by the panel.
2. **Code Standards:** Ensure Python scripts are headless-compatible (`cv2` without GUI locks) and suited for Raspberry Pi Zero 2W / ESP32-S3 deployment.
3. **Manuscript Compliance:** Align all updates with IEEE conference formatting standards in LaTeX.
4. **Defense Readiness:** Always frame mathematical and agronomic decisions around experimental integrity, statistical parsimony, and panel compliance.

---

## 6. Project Progress & Action Items Tracker
* [x] Re-proposal manuscript revisions and title update completed.
* [x] Statistical model formulation & LOOCV strategy documented.
* [x] Initial headless CV pipeline (`vision.py`) structured.
* [ ] Secure signed Title Page and Endorsement Forms from advisers (Engr. Macapagal & Engr. Saavedra).
* [ ] Complete Research Ethics Committee (REC) paperwork submission.
* [ ] Finalize greenhouse physical placement and BOM procurement (9 capacitive sensors, 9 solenoids, Pi Cam V2, SLA battery).
* [ ] Execute 45-day grow-out data collection log and harvest weighing.
* [ ] Train final multivariate polynomial regression model and evaluate $R^2$ / MAE scores.
