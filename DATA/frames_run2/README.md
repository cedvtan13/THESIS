# Raw camera frames, run 2 (sown Oct 29, 2026)

**Copied:** Nov 18, 2026, from Kent's Pi pull `pi_pulls/2026-11-17_1606` (`~/agrisentry_data/frames/` on the Pi). Files are byte-for-byte copies: the SHA-256 of every file here matched the pull when copied. Nothing was edited, resized or renamed.

**Why the checksums:** anyone can recompute them (`sha256sum file`, or `Get-FileHash file` in PowerShell) and confirm the image is the one the Pi captured.

| Folder | Contents |
|---|---|
| `main/` | one noon frame per day as kept on the Pi, D1 and D4 to D20 (D2, D3 lost to the Oct 30 to 31 power outage) |
| `replaced/` | frames replaced by a retake (D11 12:30, D12 12:00), with their overlays |
| `setaside/` | the D20 09:36 catch-up frame, not used for the data |
| `overlay/` | the mask drawn on each day's frame by the capture code (derived, for viewing). For D12 and D20 this is the later capture of the day |

Frame names are `Dxx_date_HHMM.png`. Camera: Raspberry Pi Camera Module 3, top view, saved as PNG (lossless).

## Frames per day

"Used for data" means the rows in `Dual_Archi/growth_dataset.csv` for that day were measured from this frame.

| Day | Date | Time | File | Used for data | Note | SHA-256 |
|---|---|---|---|---|---|---|
| D01 | 2026-10-29 | 13:14 | `main/D01_2026-10-29_1314.png` | yes | sowing day; captured at 13:14 | `4b2100ff422550d39b5dbc76974d6fe88e894b8dbe7ecd8dc24e6411e1661173` |
| D04 | 2026-11-01 | 12:10 | `main/D04_2026-11-01_1210.png` | yes |  | `93968b132b4fced62e6c603782aceab5c0ec5f04bc1692a0368aeab999a742c2` |
| D05 | 2026-11-02 | 12:10 | `main/D05_2026-11-02_1210.png` | yes |  | `f400ed71b22c7e30825871b0215f2ed4b61b6c101704736a8cd91c86201e205e` |
| D06 | 2026-11-03 | 12:00 | `main/D06_2026-11-03_1200.png` | yes |  | `e21bf287c109cb0e98abc222379c0e3c7a00c27a58a34ee5a5eef69770e8511d` |
| D07 | 2026-11-04 | 12:00 | `main/D07_2026-11-04_1200.png` | yes |  | `435e466b7d74e3f1a624b49451c72beacfdb1331e2684f5778590e8777916924` |
| D08 | 2026-11-05 | 12:00 | `main/D08_2026-11-05_1200.png` | yes |  | `2ba0967e16e021dbfb27f7871d17f71b9f3deacfcab9f3742aa4020aa84aa260` |
| D09 | 2026-11-06 | 12:00 | `main/D09_2026-11-06_1200.png` | yes |  | `9a2f031a36800e8356806c9d8b6f22ccd536680e262f3c2bce84156bae3277b2` |
| D10 | 2026-11-07 | 12:24 | `main/D10_2026-11-07_1224.png` | yes | alignment shift of +141 px that day; overlay before the alignment fix also kept (overlay/D10_overlay_before_align.jpg) | `ac19cbe5edb019c6fbdaa63f350b15c73931968cce5aa8e29f0aaf895cee4937` |
| D11 | 2026-11-08 | 12:52 | `main/D11_2026-11-08_1252.png` | yes | retake at 12:52; the 12:30 frame had another group's device on P-01 (replaced/) | `f5f549da707da3f48a2bf8dc5eecad91d6683995c71175aa0474f593410f3ebc` |
| D12 | 2026-11-09 | 12:42 | `main/D12_2026-11-09_1242.png` | no (see note) | the D12 rows use the **12:00** frame (replaced/D12_2026-11-09_1200.png) for GPR, with the 12:42 soil readings (team decision, Nov 9 evening). The 12:42 frame here is the retake | `55b9258e9c821eb5d3b20306579bd3246c18111820e4717ee13ac3c98d9870af` |
| D13 | 2026-11-10 | 12:00 | `main/D13_2026-11-10_1200.png` | yes |  | `fd8b087d87e9da8ba952eb28cd6c9eaa50bb24dc4a639e397dc038de46c27342` |
| D14 | 2026-11-11 | 12:00 | `main/D14_2026-11-11_1200.png` | yes |  | `e3ccd1ed3cb6b57dd88afcd7974dc111c73e9ccb3bf5786370cb2db4286e1f42` |
| D15 | 2026-11-12 | 12:10 | `main/D15_2026-11-12_1210.png` | yes |  | `01748ad64b0ceb2b401d371561d8906d6026142abc4357cd5087d8d2405627bf` |
| D16 | 2026-11-13 | 12:00 | `main/D16_2026-11-13_1200.png` | yes |  | `4b28eae1c96724c4772ddafaf1073a0e4bef3cd1d3d87c2ca9fe283035551ec7` |
| D17 | 2026-11-14 | 12:00 | `main/D17_2026-11-14_1200.png` | yes |  | `ba78f718700c20cb785cdb2cfe4c315e9a79081ed850c2d8774176c90dcca23e` |
| D18 | 2026-11-15 | 12:00 | `main/D18_2026-11-15_1200.png` | yes | rows recovered on Nov 16 from this saved frame (recover_day.py) | `82b5a5e923a18f4776981a7b0d48d59d5fd588f721c7b459c53fb947f42da9c8` |
| D19 | 2026-11-16 | 12:47 | `main/D19_2026-11-16_1247.png` | yes | blue colour cast (blue/red 1.84), overcast; flagged | `9f12dd16dea9fa4be82d712fef066ff8ee564fc210acd655bc9e1d037840e613` |
| D20 | 2026-11-17 | 12:42 | `main/D20_2026-11-17_1242.png` | yes | blue colour cast (blue/red 1.57), dim; P-04 straightened before this manual retake; flagged R | `f85f92a723d9dd932dcf70809a9be4104395f5d8e65aae685cc19888d3e7c181` |

## Replaced and set-aside frames

| File | Used for data | Note | SHA-256 |
|---|---|---|---|
| `replaced/D11_2026-11-08_1230.png` | no | replaced by the 12:52 retake (other group's device on P-01, fault soil reading) | `ec4d0c4cdfa2694112d231c763a2d8595b6b16a3aa44492b2b3680aec26e5540` |
| `replaced/D12_2026-11-09_1200.png` | **yes, D12 GPR** | the D12 rows' GPR comes from this frame | `b881a745746dad53822945d4b72f7e83a1031a7804fe0de0918bb13364042433` |
| `setaside/D20_2026-11-17_0936.png` | no | catch-up capture after the 09:31 reboot, outside the noon window; its 9 rows moved to growth_dataset_setaside_D20_20261117_1657.csv on the Pi (Nov 17 16:57) | `72b0ca20ed75e9304170e6f3917cc97e4b9441b638777cee04095d6cd491d17e` |

## Overlays

| File | SHA-256 |
|---|---|
| `overlay/D01_overlay.jpg` | `17116f93c3112577bef66a46a20e2950faa63b7fad945081ea1fd246bcecd515` |
| `overlay/D04_overlay.jpg` | `244d7728b8d96a32296224df41729b797ae40a86c30588bc45e6fa48a241f4ff` |
| `overlay/D05_overlay.jpg` | `0990b0ca11758985e6bb238b148b852edf4675d9d031005c069ba6ddb866a20b` |
| `overlay/D06_overlay.jpg` | `37d51df204573e64bdaaff0c1fd4efe76e14aeaa3c425f80ec1136c7fb81a4d7` |
| `overlay/D07_overlay.jpg` | `719657b2e3528ebae038adc3cd3502640b1b842af02e8c26f523c574a483e53f` |
| `overlay/D08_overlay.jpg` | `9e98081772fe5492cf413ce42fc6fe0e66df7d882e4797791602cc31eb798e28` |
| `overlay/D09_overlay.jpg` | `d92c4f08fe89838519a39f57564874f55817ca2a0bd309e9a75d5d37c71015d2` |
| `overlay/D10_overlay.jpg` | `810b20984318a0021f1ffd3eee1ed5e7d16975178475de4b38288d51e8e15b9f` |
| `overlay/D10_overlay_before_align.jpg` | `bf3d74f2a50350a656a1fb733272f676a881d09e4ed63e7c4dfe819177f3d07a` |
| `overlay/D11_overlay.jpg` | `5bcb835e79b0836f09f752632c187c3f1216b43ab171b09274a513959275627a` |
| `overlay/D12_overlay.jpg` | `f43d4730d93c6262cc1af777d5ed39452c3df038158f8dc936cb30e95e466cb2` |
| `overlay/D13_overlay.jpg` | `184d27347d6754a7177e8f7fe3371d429500a351815a587e9e025ab9ce14d768` |
| `overlay/D14_overlay.jpg` | `bdd6fc81b266daa84c57416c00deebb775cf2efe49aba296721706f5c78521d5` |
| `overlay/D15_overlay.jpg` | `a8dc14b9d8c46a9ebde586b4e44f74a8c34c0b2d2775f45e0c15e8c1d9f2103c` |
| `overlay/D16_overlay.jpg` | `8b2ad1a38df68870bf8376dae53e6ece25c8c4696601dfdfa5bda8323c69d52f` |
| `overlay/D17_overlay.jpg` | `85290cb1c74b42699c89998a803bebbd03871668d8f31f17f05dbf4f9924c7bc` |
| `overlay/D18_overlay.jpg` | `8246a26426a2d64bd58c9689ab563d8ef776e14b6c7e209f484c6c97439d8a15` |
| `overlay/D19_overlay.jpg` | `16a6bee8575e0d3d0f106788f59d9dcb82a5eebb33d80622964de8cb53bd66bf` |
| `overlay/D20_overlay.jpg` | `55e1f907035f95d5c338e9c224ef44faa44fc9062bcc0f28cf2de7f467d2f148` |
| `replaced/D11_overlay_1230.jpg` | `788680a54ccf272e9ead9010565476d166715dc3fade97608017e6f37e18570e` |
| `replaced/D12_overlay_1200.jpg` | `d0d3616989059d9feb3a40becf7415dba356efba34610fdfcd5b276d3bb36001` |

## Not included

Camera and alignment tests from the same folder on the Pi: `time_test/` (13:00 and 14:00 test frames, D10 to D12), `roi_fit_*`, `roi_check_*`, `check_D08_*`. They stay in the Pi pulls on Kent's laptop.

## Adding new days

After each `pull_from_pi.bat`, the new day's frame and overlay are copied here and added to the tables above with their checksums.
