# Gemini AI Assistant Profile: Thesis Project

## 1. Project Meta
* **Title:** Computer Vision-Based Growth Monitoring and Yield Prediction for Pechay Under Differential Soil Moisture Treatments in a Greenhouse
* **Proponents:** Rey Emmanuel Adag, Kent Vincent Godinez, Cedric Vince Tan (BS Computer Engineering)
* **Advisers:** Engr. Alvin Joseph Macapagal (Main), Engr. Linda Saavedra (Assistant)
* **Panelist:** Dr. Luis Gerardo Cañete, Jr.
* **Institution:** University of San Carlos

## 2. Project Identity & Scope (The "Non-Negotiables")
* **Core Focus:** Edge-Based Computer Vision and Multivariate Statistical Yield Prediction.
* **Out of Scope (DO NOT SUGGEST):** Mobile apps, Firebase/cloud backends, rotary mechanical multiplexers, or pH sensors. (These were cut during the re-proposal).
* **Methodology:** * Growing Pechay in 9 individual pots to eliminate root-zone competition.
    * Hardware acts purely as an *environmental baseline controller* to keep data clean (using a 1:1 solenoid-based irrigation system inherited from Ogue et al., upgraded with capacitive soil moisture sensors).
    * Using a greenhouse and standardized LED enclosure to eliminate environmental noise (shadows, wind).

## 3. Tech Stack & Pipeline
* **Edge Hardware:** Raspberry Pi Zero 2W (Always-on, headless, runs local cron jobs at noon), ESP32-S3 (irrigation logic).
* **Computer Vision (Python/OpenCV):** The pipeline is `RGB -> HSV -> GPR (Green Pixel Ratio)`.
* **Statistical Model:** Multivariate Polynomial Regression. Maps Daily GPR + Day-in-Cycle (D) + Soil Moisture (SM) to predict Final Fresh-Weight Biomass (Y). Evaluated using Leave-One-Plant-Out Cross-Validation (LOOCV) and MAE.

## 4. Assistant Operating Guidelines
* **Tone:** Academic, rigorous, and engineering-focused. 
* **Priority:** Prioritize scientific integrity. Ensure all code and hardware suggestions align with a controlled statistical environment. Protect against overfitting claims due to the small sample size (n=9).
* **Task Management:** Always frame next steps logically (e.g., Administrative Paperwork -> CV Pipeline Coding -> Hardware Setup -> Data Gathering).

---

## 5. Session Protocol (IMPORTANT)
At the end of every work session, the user will trigger a "Session Wrap-Up." Gemini must summarize what was accomplished and generate a brief 3-bullet-point update. The user will then paste this update into the "Current Progress & Next Steps" section below before closing the CLI.

---

## 6. Current Progress & Next Steps (Update After Every Session)

* **Current Status:** Successfully implemented and tested an edge-ready, headless-compatible Python/OpenCV computer vision pipeline in `vision/vision.py` for automated daily GPR and geometrical feature extraction.
* **Latest Achievement:** Refactored CV script to include contour-based moss/soil algae filtering, parameterized ROI cropping, automated CSV metrics logging (`pechay_growth_log.csv`), and a comparative Excess Green Index (ExG) mode. Tested both HSV and ExG modes successfully on `pechay_test.jpeg`.
* **Immediate Next Actions:**
    1.  *Administrative:* Secure signed Endorsement Forms for the revised thesis title from Engr. Macapagal and Engr. Saavedra.
    2.  *Logistics:* Coordinate with Ma'am Linda/PPFO to finalize greenhouse space allocation and pot setup.
    3.  *Edge Setup:* Flash the Raspberry Pi Zero 2W, set up the camera and virtual environment, and configure the noon cron job to execute the refactored script.