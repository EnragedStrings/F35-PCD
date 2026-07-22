# PCD Reference Update - 2026-07-22

This file records the code and report changes made from the 2025 AFTTP 3-3, Battle Book, and attached HOTAS mapping table review. It is not a claim that the simulator is now 1:1; it documents the first-pass items that had enough information to implement a decent representation.

## Dist And Sensitive Data

- Removed source startup dependence on local distribution runtime/secrets by importing `scripts/dist_runtime_stub.py` directly.
- Removed the `DIST CONFIG>` status-menu entry so normal source execution does not expose hidden developer/distribution controls.
- Added `.gitignore` coverage for local caches, recordings, temp folders, generated builds, local settings, PDFs, environment files, key/cert material, user data folders, and any `dist_runtime.py` or `dist_secrets.py` files.
- Removed README language that implied private distribution secret material belongs in normal source context.

## HOTAS First-Pass Controls

- Added short/long press handling for mapped HOTAS buttons.
- Added first-pass TMS behavior from the attached stick table:
  - Forward short designates NTS based on A/S or A/A context.
  - Forward long marks current steerpoint or starts single target track.
  - Aft short undesignates or selects DGFT in DAS context.
  - Aft long clears NTS/LST state.
  - Left/right short step A/S or A/A NTS.
  - Left long starts TFLIR laser spot track.
- Corrected the CMS interpretation. Stick CMS is now treated as jam/EGL control, not chaff/flare dispense. The visible binding label is `CMS Z` for EGL, while the legacy internal action key remains `cms_right` for compatibility with existing keybind data.
- Added first-pass WMS behavior:
  - Forward/right short select A/A 1 or A/A 2 and second-actuate missile station cycling.
  - Left short selects A/S.
  - Left long cycles bomb type.
  - Aft selects DGFT.
  - Z plunger selects NAV.
- Added first-pass throttle CFFL behavior for chaff/flare programs 1/2/3, gated by EXCM ARM and decrementing local SMS inventory.
- Added first-pass NWS low/high gain cycling on the ground, speed-brake retract/extend, MPO hold, APC toggle, WPN REL MODE TFLIR/ASR slew-control flag, cage/uncage sensor state, speed-hold small/large increments, and pickle store release.

## Display And Sensor First-Pass Changes

- ASR now renders a RADAR FAIL condition with a Maltese-cross style symbol when RADAR/PHM status indicates fail/degraded/offline.
- ASR `SPNT/TGT` is now interactive and updates local SPNT/NTS state.
- TFLIR/EOTS `A-S`, `LASER`, `MTT`, `HT`, `SPNT/TGT`, and `CUE/OFF` now change local state and show status feedback.
- DAS `OPER`, `NORM`, and `VIEW A-S` now change local state and show status feedback.
- TWD now shows HOTAS-driven jam/EGL status.
- SMS `EXCM ARM` confirmation now changes state and shows armed/standby status.
- PHM/MSSTAT label fixes were applied for `GPA2B2` and ICP-B `GPB...` rows.

## Remaining Known Limitations

- HOTAS DMS, FOV, trim, mic, external-light, management-switch axis details, and real cursor slew axis behavior still need implementation.
- Trigger is still single-stage. The attached table requires half detent for TFLIR laser fire and second detent for gun fire.
- Weapon release is a local station decrement, not a reference-level release authorization model with LAR/DLZ, inhibit conditions, and post-release effects.
- ASR, DAS, TFLIR, TSD, TWD, SMS, and PHM still need a shared sensor/mission state model for 1:1 troubleshooting and symbology.
- TFLIR/DAS `CNTL>` pages, ASR MTT/search/track behavior, TWD alert/audio/degrade behavior, SMS/WPN-A jettison/error pages, and PHM/CNI network troubleshooting remain incomplete.

The merged gap report is updated in `docs/pcd_reference_gap_report.md`.
