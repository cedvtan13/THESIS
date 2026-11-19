# Thesis Reference Library & Literature Verification Registry

**Project:** Computer Vision-Based Growth Monitoring and Yield Prediction for Pechay Under Differential Soil Moisture Treatments in a Greenhouse  
**Institution:** Department of Computer Engineering, University of San Carlos  
**BibTeX Source:** [`2026-11-11-GroupB-Manuscript-Draft1/References/references.bib`](file:///Users/moapilaw/Desktop/THESIS/2026-11-11-GroupB-Manuscript-Draft1/References/references.bib)  
**Last Verified:** November 19, 2026 (Audited against Crossref API, OpenAlex, and official Philippine institutional publications)

> **Integrity Rule:** Every entry below has been checked against Crossref/OpenAlex DOI registries, university repositories, or official Philippine government technical publications. Unverified or mistyped entries found during the November 19 audit of `references.bib` have been corrected and documented in **Section 6**.

---

## 1. Potting Media, Soil Mix Ratios (`3:1:1` & `8:4:3`), and Pechay Agronomy

### 1.1 `Gonzaga2023` — Carbonized Rice Hull (CRH) Integration in Pechay Growing Media *(New)*
* **Citation:** Gonzaga, N. R., Gonzaga, A. B., Silverio, B. G. S., Pabellon, J. M. L., Taylaran, R. D., & Montecalvo, L. L. C. (2023). "Ensuring household food security through enhanced production of pechay (*Brassica rapa* L.) as influenced by different levels of carbonized rice hull integration." *IOP Conference Series: Earth and Environmental Science*, **1208**(1), 012048.
* **DOI:** [10.1088/1755-1315/1208/1/012048](https://doi.org/10.1088/1755-1315/1208/1/012048)
* **Relevance to `3:1:1` / `8:4:3` Soil Mix:** Evaluated pechay (*Brassica rapa* L.) under specialized mixed growing media integrated with varying volumetric levels of CRH (`0%`, `5%`, `10%`, `15%`). Mixing specialized growing media with CRH yielded significantly higher dry matter than pure garden soil alone, with moderate CRH inclusion (`5%–15%`) optimizing fresh yield ($102.13\text{ kg}/100\text{ m}^2$ at `5%` CRH) and economic return. Supports keeping CRH moderate (~`20%` in `3:1:1`) rather than excessively high (`26.7%` in `8:4:3`).

### 1.2 `Lagon2022` — Potted Pechay Response to Vermicompost Amendments in the Philippines *(New)*
* **Citation:** Lagon, J. R. M., Abad, R. G., Bayogan, E. R. V., & Silvosa-Millado, C. S. C. (2022). "Growth and Yield of Screenhouse-grown potted Pechay (*Brassica rapa* L. ssp. *chinensis* cv. Black Behi) in selected Davao-produced Composts." *Mindanao Journal of Science and Technology*, **20**(2).
* **DOI:** [10.61310/mndjstea.0990.22](https://doi.org/10.61310/mndjstea.0990.22)
* **Relevance to `3:1:1` Soil Mix:** Evaluated potted *Black Behi* pechay under screenhouse conditions across organic compost formulations. Plants grown in potting mixes amended with **`20%` vermicompost** (Tacunan) achieved the highest mean plant height ($18.42\text{ cm}$), leaf length ($10.31\text{ cm}$), leaf width ($5.89\text{ cm}$), marketable fresh weight ($12.19\text{ g}$), and $94\text{--}100\%$ germination—validating the **`20%` (1-of-5 parts) vermicast proportion** shared by both the `3:1:1` and `8:4:3` recipes.

### 1.3 `BPI_Pechay` — DA-ATI & BPI Pechay Production and Container Potting Guidelines *(New)*
* **Citation:** Department of Agriculture – Bureau of Plant Industry (DA-BPI) & Agricultural Training Institute (DA-ATI). *Pechay Production Guide* & Philippine Urban Container Gardening Extension Manuals. Quezon City, Philippines.
* **Relevance to `3:1:1` Soil Mix & Schedule:** Establishes agronomic baselines for pechay (*Brassica rapa* L.): loose, well-drained sandy-to-clay loam soil rich in organic matter; optimal **soil pH of $5.5\text{ to }6.5$**; balanced container mixes combining pulverized garden soil with organic compost/vermicast and rice hull (`1:1:1` to `2:1:1`–`3:1:1` by volume in container gardening practice); direct seeding or transplanting at $10\text{--}14\text{ DAS}$; and a harvest window spanning **3 weeks (21 days) to 40 days** after sowing depending on cultivar and target size.

### 1.4 `PhilRiceCRH` — PhilRice Carbonized Rice Hull Technical Bulletin *(New)*
* **Citation:** Philippine Rice Research Institute (PhilRice). *Carbonized Rice Hull*, Rice Technology Bulletin No. 47. Science City of Muñoz, Nueva Ecija, Philippines (PinoyRice Knowledge Bank).
* **Relevance to Soil Amendments:** Documents the physical and chemical characteristics of carbonized rice hull (CRH / *inuling na ipa*): produced by incomplete combustion, lightweight, porous, water-retentive, permeable, sterile (free from weed seeds and pathogens), containing phosphorus, potassium, calcium, magnesium, and trace elements, and exhibiting an **alkaline reaction** that neutralizes acidic soils. Explains why Day 0 pH testing is critical when mixing CRH with garden loam.

### 1.5 `Camariosa2021` — Pechay Growth Window & Organic Cultivation
* **Citation:** Camariosa, C. M., & Gurrea, G. (2021). *The growth performance of pechay (Brassica rapa L. subsp. chinensis) as affected by different levels of organic foliar fertilizer*. Undergraduate Thesis, College of Arts and Sciences Education, University of Mindanao, Davao City, Philippines.
* **Used in:** Chapter 3 (`\cite{Camariosa2021}`) — establishes growth tracking methodology and 30–45 day cultivation benchmarks for Philippine *Brassica rapa* subsp. *chinensis*.

### 1.6 `Poorter2012` — Pot Size and Rooting Volume Constraints
* **Citation:** Poorter, H., Bühler, J., van Dusschoten, D., Climent, J., & Postma, J. A. (2012). "Pot size matters: a meta-analysis of the effects of rooting volume on plant growth." *Functional Plant Biology*, **39**(11), 839–850.
* **DOI:** [10.1071/FP12049](https://doi.org/10.1071/FP12049)
* **Used in:** Chapter 2 (`\cite{Poorter2012}`) — explains both why individual pot isolation eliminates inter-plant root competition and why finite pot volume ($601\text{ cm}^3$ in our rig) imposes a root-restriction growth ceiling that must be stated as a limitation.

---

## 2. Computer Vision, Canopy Segmentation (GPR / FGCC), and Yield Imaging

### 2.1 `Patrignani2015` — Fractional Green Canopy Cover (Canopeo)
* **Citation:** Patrignani, A., & Ochsner, T. E. (2015). "Canopeo: A Powerful New Tool for Measuring Fractional Green Canopy Cover." *Agronomy Journal*, **107**(6), 2312–2320.
* **DOI:** [10.2134/agronj15.0150](https://doi.org/10.2134/agronj15.0150)
* **Used in:** Chapters 1 & 2 (`\cite{Patrignani2015}`) — foundational justification for using top-down fractional green canopy cover / Green Pixel Ratio (GPR) as a non-destructive biomass proxy.

### 2.2 `Ge2016` — Temporal RGB Imaging for Water Use & Growth Dynamics
* **Citation:** Ge, Y., Bai, G., Stoerger, V., & Schnable, J. C. (2016). "Temporal dynamics of maize plant growth, water use, and leaf water content using automated high throughput RGB and hyperspectral imaging." *Computers and Electronics in Agriculture*, **127**, 625–632.
* **DOI:** [10.1016/j.compag.2016.07.028](https://doi.org/10.1016/j.compag.2016.07.028)
* **Used in:** Chapters 1 & 2 (`\cite{Ge2016}`) — demonstrates continuous non-destructive time-series phenotyping via top-down optical imaging vs. destructive sampling.

### 2.3 `Hamuda2016` — Survey of Plant Segmentation & HSV Color-Space Stability
* **Citation:** Hamuda, E., Glavin, M., & Jones, E. (2016). "A survey of image processing techniques for plant extraction and segmentation in the field." *Computers and Electronics in Agriculture*, **125**, 184–199.
* **DOI:** [10.1016/j.compag.2016.04.024](https://doi.org/10.1016/j.compag.2016.04.024)
* **Used in:** Chapters 1 & 2 (`\cite{Hamuda2016}`) — explains RGB illumination coupling failures and justifies transforming frames to HSV to decouple hue from brightness ($V$) under changing cloud cover.

### 2.4 `Slaughter2008` — Outdoor/Greenhouse Lighting Noise in Vegetation Segmentation
* **Citation:** Slaughter, D. C., Giles, D. K., & Downey, D. (2008). "Autonomous robotic weed control systems: A review." *Computers and Electronics in Agriculture*, **61**(1), 63–78.
* **DOI:** [10.1016/j.compag.2007.05.008](https://doi.org/10.1016/j.compag.2007.05.008)
* **Used in:** Chapter 2 (`\cite{Slaughter2008}`) — documents how ambient sunlight shifts, cloud cover, and specular shadows corrupt color-threshold canopy extraction.

### 2.5 `Kim2022` — Early Projected Canopy Size Predicts Final Biomass
* **Citation:** Kim, C., & van Iersel, M. W. (2022). "Morphological and Physiological Screening to Predict Lettuce Biomass Production in Controlled Environment Agriculture." *Remote Sensing*, **14**(2), 316.
* **DOI:** [10.3390/rs14020316](https://doi.org/10.3390/rs14020316)
* **Used in:** Chapter 2 (`\cite{Kim2022}`) — shows early projected canopy size (PCS at 13 DAG in green lettuce) correlates significantly with final shoot dry weight at 51 DAG ($R^2 = 0.74$).

### 2.6 `Lee2024` — Vegetation Fraction & Soil/Irrigation Modeling for *Brassica rapa*
* **Citation:** Lee, D.-H., & Park, J.-H. (2024). "Development of a UAS-Based Multi-Sensor Deep Learning Model for Predicting Napa Cabbage Fresh Weight and Determining Optimal Harvest Time." *Remote Sensing*, **16**(18), 3455.
* **DOI:** [10.3390/rs16183455](https://doi.org/10.3390/rs16183455)
* **Used in:** Chapter 2 (`\cite{Lee2024}`) — predicts *Brassica rapa* (Napa cabbage) fresh weight from RGB/multispectral vegetation fraction and water-stress indicators ($R^2 = 0.82$), capturing variability across soil types and drip irrigation regimes.

### 2.7 `Hosoda2024` — Early Time-Series Image Forward Projection of Fresh Weight
* **Citation:** Hosoda, Y., Tada, T., & Goto, H. (2024). "Lettuce Fresh Weight Prediction in a Plant Factory Using Plant Growth Models." *IEEE Access*, **12**, 97226–97234.
* **DOI:** [10.1109/access.2024.3423455](https://doi.org/10.1109/access.2024.3423455)
* **Used in:** Literature review (`MANUSCRIPT.md`) — demonstrates fitting geometric canopy features (projection area, edge length, skeleton length) from 10 days of early growth images to project lettuce fresh weight 10 days ahead ($R^2 = 0.885$, $\text{MAE} = 6.684\text{ g}$).

---

## 3. Crop Growth Curves, Statistical Regression, and Model Generalization

### 3.1 `Archontoulis2015` — Nonlinear Regression Models in Agricultural Research
* **Citation:** Archontoulis, S. V., & Miguez, F. E. (2015). "Nonlinear Regression Models and Applications in Agricultural Research." *Agronomy Journal*, **107**(2), 786–798.
* **DOI:** [10.2134/agronj2012.0506](https://doi.org/10.2134/agronj2012.0506)
* **Used in:** Chapters 2 & 3 (`\cite{Archontoulis2015}`) — validates nonlinear/curvilinear modeling over linear equations for plant biomass trajectories.

### 3.2 `Ding2022` — Sigmoidal Logistic Growth of Greenhouse Pak Choi
* **Citation:** Ding, X., Zhang, H., He, L., Jin, H., Zhou, Q., Yang, J., Zhu, W., Yu, J., & Qian, T. (2022). "Changes in Leaf and Growth of Pak Choi in a Semi-closed Greenhouse in Eastern China." *HortScience*, **57**(5), 643–651.
* **DOI:** [10.21273/hortsci16523-22](https://doi.org/10.21273/hortsci16523-22)
* **Used in:** Chapter 3 (`\cite{Ding2022}`) — demonstrates that leaf length/width accumulation and plant width in greenhouse *Brassica rapa* ssp. *chinensis* follow sigmoidal logistic growth curves ($R^2 > 0.98$ for leaf dimensions, $R^2 > 0.93$ for plant width).

### 3.3 `Cho2015` — Expolinear Growth Modeling of Pak-Choi
* **Citation:** Cho, Y. Y., Lee, J. H., Shin, J. H., & Son, J. E. (2015). "Development of an expolinear growth model for pak-choi using the radiation integral and planting density." *Horticulture, Environment, and Biotechnology*, **56**(3), 310–315.
* **DOI:** [10.1007/s13580-015-0140-z](https://doi.org/10.1007/s13580-015-0140-z)
* **Used in:** Literature review (`MANUSCRIPT.md`) — models pak-choi shoot dry and fresh weight using an expolinear equation driven by cumulative photosynthetically active radiation (PAR) and planting density.

### 3.4 `Harrell2015` — Regression Modeling Strategies & Predictor-to-Sample Ratio
* **Citation:** Harrell, Jr., F. E. (2015). *Regression Modeling Strategies: With Applications to Linear Models, Logistic and Ordinal Regression, and Survival Analysis* (2nd ed.). Springer, Cham, Switzerland.
* **DOI:** [10.1007/978-3-319-19425-7](https://doi.org/10.1007/978-3-319-19425-7)
* **Used in:** Overfitting & model parsimony defense (10–15 independent experimental units per predictor rule), motivating our simplification to univariate `weight ~ GPR` as the primary model when $N = 7\text{–}9$ plants and treating the 6-term polynomial as exploratory.

### 3.5 `Kamilaris2018` — Deep Learning Data Requirements in Agriculture
* **Citation:** Kamilaris, A., & Prenafeta-Boldú, F. X. (2018). "Deep learning in agriculture: A survey." *Computers and Electronics in Agriculture*, **147**, 70–90.
* **DOI:** [10.1016/j.compag.2018.02.016](https://doi.org/10.1016/j.compag.2018.02.016)
* **Used in:** Chapter 2 (`\cite{Kamilaris2018}`) — explains why data-hungry deep neural networks overfit small single-cycle cohorts, justifying transparent OLS regression at the edge.

---

## 4. Edge Computing, Automated Irrigation, Capacitive Sensing, and Hardware Reliability

### 4.1 `Shi2016` — Edge Computing Paradigm
* **Citation:** Shi, W., Cao, J., Zhang, Q., Li, Y., & Xu, L. (2016). "Edge Computing: Vision and Challenges." *IEEE Internet of Things Journal*, **3**(5), 637–646.
* **DOI:** [10.1109/JIOT.2016.2579198](https://doi.org/10.1109/JIOT.2016.2579198)
* **Used in:** Chapter 2 (`\cite{Shi2016}`) — justifies running OpenCV segmentation locally on the Raspberry Pi Zero 2 W rather than streaming images to cloud servers over unstable Wi-Fi.

### 4.2 `Zamora2019` — Smart Farming IoT Platform with Edge & Cloud Decoupling
* **Citation:** Zamora-Izquierdo, M. A., Santa, J., Martínez, J. A., Martínez, V., & Skarmeta, A. F. (2019). "Smart farming IoT platform based on edge and cloud computing." *Biosystems Engineering*, **177**, 4–17.
* **DOI:** [10.1016/j.biosystemseng.2018.10.014](https://doi.org/10.1016/j.biosystemseng.2018.10.014)
* **Used in:** Chapter 2 (`\cite{Zamora2019}`) — supports autonomous local edge nodes in greenhouse automation.

### 4.3 `Prathibha2017` — Microcontroller-Driven Smart Agriculture Monitoring
* **Citation:** Prathibha, S. R., Hongal, A., & Jyothi, M. P. (2017). "IOT Based Monitoring System in Smart Agriculture." *2017 International Conference on Recent Advances in Electronics and Communication Technology (ICRAECT)*, 81–84.
* **DOI:** [10.1109/ICRAECT.2017.52](https://doi.org/10.1109/ICRAECT.2017.52)
* **Used in:** Chapter 2 (`\cite{Prathibha2017}`) — baseline architecture for microcontroller-driven sensor polling and irrigation control.

### 4.4 `Kushwaha2024` — Smart Irrigation Wireless Sensor Water Management
* **Citation:** Kushwaha, Y. K., Joshi, A., Panigrahi, R. K., & Pandey, A. (2024). "Development of a smart irrigation monitoring system employing the wireless sensor network for agricultural water management." *Journal of Hydroinformatics*, **26**(12), 3224–3243.
* **DOI:** [10.2166/hydro.2024.241](https://doi.org/10.2166/hydro.2024.241)
* **Used in:** Chapter 2 (`\cite{Kushwaha2024}`) — establishes automated 1:1 sensor-driven irrigation loops as an engineering baseline.

### 4.5 `Nagahage2019` (Legacy BibTeX key `Younis2021`) — Low-Cost Capacitive Soil Moisture Sensor Calibration *(Audited Replacement)*
* **Citation:** Nagahage, E. A. A. D., Nagahage, I. S. P., & Fujino, T. (2019). "Calibration and Validation of a Low-Cost Capacitive Moisture Sensor to Integrate the Automated Soil Moisture Monitoring System." *Agriculture*, **9**(7), 141.
* **DOI:** [10.3390/agriculture9070141](https://doi.org/10.3390/agriculture9070141)
* **Used in:** Chapter 2 (`\cite{Younis2021}` / `\cite{Nagahage2019}`) & soil calibration justification — validates soil-specific two-point/gravimetric calibration for low-cost capacitive v1.2 sensors and documents signal stability sensitivities.

### 4.6 `Mane2024` — Dielectric Soil Moisture Sensor Calibration Review *(New)*
* **Citation:** Mane, S., Das, N., Singh, G., Cosh, M., & Dong, Y. (2024). "Advancements in dielectric soil moisture sensor Calibration: A comprehensive review of methods and techniques." *Computers and Electronics in Agriculture*, **218**, 108686.
* **DOI:** [10.1016/j.compag.2024.108686](https://doi.org/10.1016/j.compag.2024.108686)
* **Relevance to Hardware Defense:** Explains dielectric permittivity sensitivity in potting substrates containing organic matter and carbonized materials, justifying our pot-specific oven-dry (`2483 ADC`) to saturated (`1120 ADC`) gravimetric calibration and True VWC mapping ($\times 0.456$).

### 4.7 `Mantis2021` (Legacy BibTeX key `Sheng2019`) — Conformal Coating Reliability Under Condensing Humidity *(Audited Replacement)*
* **Citation:** Mantis, I., Li, F., Jellesen, M. S., & Ambat, R. (2021). "Effect of intrinsic PCB parameters on the performance of fluoropolymer coating under condensing humidity conditions." *Microelectronics Reliability*, **122**, 114158.
* **DOI:** [10.1016/j.microrel.2021.114158](https://doi.org/10.1016/j.microrel.2021.114158)
* **Used in:** Chapters 2 & 3 (`\cite{Sheng2019}` / `\cite{Mantis2021}`) — empirically demonstrates how conformal coatings behave under condensing humidity on PCBs to mitigate surface insulation resistance drops, corrosion, and electrochemical migration, while noting vulnerability at sharp edges/unsealed junctions.

---

## 5. Food Security Policy & USC Institutional Lineage

### 5.1 `UN2023` — Global Food Security Context
* **Citation:** FAO, IFAD, UNICEF, WFP, & WHO (2023). *The State of Food Security and Nutrition in the World 2023*. Rome, Italy.
* **DOI:** [10.4060/cc3017en](https://doi.org/10.4060/cc3017en)
* **Used in:** Chapter 1 (`\cite{UN2023}`).

### 5.2 `PSA2023` — Philippine Food Supply & Price Volatility
* **Citation:** Philippine Statistics Authority (2023). *Agricultural Indicators System: Agricultural Exports and Imports*, Report No. 2023-11. Quezon City, Philippines.
* **Used in:** Chapter 1 (`\cite{PSA2023}`).

### 5.3 `HB1337` — Integrated Urban Agriculture Legislation (Philippines)
* **Citation:** House of Representatives, 19th Congress of the Republic of the Philippines (2022). *House Bill No. 1337: An Act Promoting Integrated Urban Agriculture in Urban Areas Nationwide to Address Food Security*. Manila, Philippines.
* **Used in:** Chapter 1 (`\cite{HB1337}`).

### 5.4 `NUPAP2023` — National Urban & Peri-Urban Agriculture Program
* **Citation:** Department of Agriculture (2023). *National Urban and Peri-Urban Agriculture Program (NUPAP) Strategic Framework*. Department of Agriculture Official Publications, Quezon City, Philippines.
* **Used in:** Chapter 1 (`\cite{NUPAP2023}`).

### 5.5 `Aala2022` — USC Generation 1 Urban Farming Prototype
* **Citation:** Aala, N. L. S., Casas, J. M. G., & Ouano, E. M. (2022). *Farming System with Integrated Assistant Application*. B.S. Thesis, Department of Computer Engineering, University of San Carlos, Cebu City, Philippines.
* **Used in:** Chapters 1 & 2 (`\cite{Aala2022}`) — documented glass-bulb pH sensor drift and loose jumper-wire contact failures in humid conditions.

### 5.6 `ZamoraOgue2025` — USC Generation 2 Solenoid Baseline System
* **Citation:** Zamora, J. J., Ogue, D. N., & Manila, P. G. (2025). *Redevelopment and Evaluation of an IoT Urban Farming System Using ESP32 with Sensors, Cloud Database, and Mobile App Monitoring*. B.S. Thesis, Department of Computer Engineering, University of San Carlos, Cebu City, Philippines.
* **Used in:** Chapters 1, 2, & 3 (`\cite{ZamoraOgue2025}`) — established 1:1 capacitive sensor/solenoid irrigation (`+92.1%` fresh weight vs. manual watering) over a 37-day pechay cycle while performing plant health monitoring manually via ruler and IRRI Leaf Color Chart.

---

## 6. Citation Verification Audit Log (Nov 19, 2026)

During preparation for the November 21 Project Checking, every journal/conference DOI in [`references.bib`](file:///Users/moapilaw/Desktop/THESIS/2026-11-11-GroupB-Manuscript-Draft1/References/references.bib) was checked programmatically against the Crossref API and OpenAlex. The following errors from earlier drafts were identified and fixed so **zero hallucinated or broken references remain**:

| BibTeX Key | Issue Found in Pre-Audit `references.bib` | Verified Correction Applied |
| :--- | :--- | :--- |
| `Sheng2019` | Unverified proposal entry (`Sheng, J.` + `10.1109/TDMR.2019.2928301` returned HTTP 404). | Replaced metadata with Crossref-verified `Mantis et al. (2021)`, *Microelectronics Reliability* 122:114158 (`10.1016/j.microrel.2021.114158`); alias `@article{Mantis2021}` also added. |
| `Younis2021` | Unverified proposal entry (`Younis, A.` + `10.1016/j.aeue.2021.153690` returned HTTP 404). | Replaced metadata with Crossref-verified `Nagahage et al. (2019)`, *Agriculture* 9(7):141 (`10.3390/agriculture9070141`); alias `@article{Nagahage2019}` also added. |
| `Hamuda2016` | Wrong DOI (`10.1016/j.compag.2016.03.013` resolved to an unrelated 2016 soil-erosion paper by Spekken et al.). | Fixed DOI to **`10.1016/j.compag.2016.04.024`**. |
| `Archontoulis2015` | Typo in DOI (`agronj14.0506` returned HTTP 404). | Fixed DOI to **`10.2134/agronj2012.0506`**. |
| `Ding2022` | Wrong authors (`Wang, Li, Li`) and wrong DOI (`HORTSCI16518-22` returned 404) & paraphrased title. | Corrected to Ding, X. et al. (2022), *"Changes in Leaf and Growth of Pak Choi in a Semi-closed Greenhouse in Eastern China"*, DOI **`10.21273/hortsci16523-22`**. |
| `Cho2015` | Wrong co-authors (`Oh, Oh`) and wrong DOI (`10.1007/s13580-015-0120-x` returned 404). | Corrected to Cho, Y. Y., Lee, J. H., Shin, J. H., & Son, J. E. (2015), *"Development of an expolinear growth model for pak-choi using the radiation integral and planting density"*, DOI **`10.1007/s13580-015-0140-z`**. |
| `Hosoda2024` | Fake placeholder DOI (`3412345`) and paraphrased title/authors (`Matsuo, Takahashi`). | Corrected to Hosoda, Y., Tada, T., & Goto, H. (2024), *"Lettuce Fresh Weight Prediction in a Plant Factory Using Plant Growth Models"*, DOI **`10.1109/access.2024.3423455`**. |
| `Kim2022` & `Lee2024` | Paraphrased titles & missing first-name initials (`J. Kim` instead of `C. Kim`, `S. Lee` instead of `D.-H. Lee`). | Updated to exact published titles and author names from Crossref (`10.3390/rs14020316` & `10.3390/rs16183455`). |
| `Prathibha2017` & `Kushwaha2024` | Missing DOIs, page numbers, and truncated co-authors (`and others`). | Completed full Crossref author list, pages (`3224--3243`), and DOIs (`10.1109/ICRAECT.2017.52`, `10.2166/hydro.2024.241`). |
| *New Soil & Sensor Refs* | Needed formal academic backing for `3:1:1` / `8:4:3` potting mix, pH/CRH effects, and capacitive dielectric calibration. | Added Crossref-verified **`Gonzaga2023`**, **`Lagon2022`**, **`Mane2024`**, plus official **`BPI_Pechay`** and **`PhilRiceCRH`** guides. |
