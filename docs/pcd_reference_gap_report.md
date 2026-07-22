# PCD Simulator Reference Fidelity Gap Report

Date: 2026-07-22

Scope: static review of the current PCD simulator repository, rendered PDF/image comparison, and code search for no-op/placeholder controls. Per request, this ignores the `PMD/DR>DEBUG` menu. It does not ignore normal status pages, HOTAS mapping pages, panel popups, display formats, or status-menu functions that are not debug-only.

Primary references:

- `AFTTP 3-3.F-35_NTTP 3-22.3-F35 _13 May 2025.pdf`, rendered under `tmp/pdfs/afttp_3_3_f35_2025/`
- `F-35 Battle Book - 1 Jan 17 - Final (Use this one for Desktop Reference).pdf`, rendered under `tmp/pdfs/f35_battle_book/`
- Attached HOTAS stick/throttle mapping table images provided during the 2026-07-22 update
- Current simulator screenshots under `docs/screenshots/`

Use the 2025 3-3 as the primary operational reference. Use the Battle Book as a display/reference companion where it provides screenshots, button maps, and troubleshooting examples. Keep this report local with the source PDFs.

## Priority Legend

- P0: high-impact 1:1 blocker. A visible simulator control or major referenced function is absent or misleading.
- P1: important fidelity gap. The simulator has an approximation, but not the referenced behavior.
- P2: polish, visual accuracy, or lower-risk missing linkage.

## Executive Summary

The simulator has a strong visual shell and several useful interactive systems, but it is not yet close to 1:1 with the 2025 3-3, Battle Book, and attached HOTAS mapping tables. The largest gaps are not layout; they are behavior/state gaps:

- HOTAS now has a first-pass short/long press model for the highest-priority mapped stick/throttle actions, including TMS, WMS, CMS, speed brake, CFFL, NWS, WPN REL MODE, MPO, APC, and pickle release. Remaining HOTAS gaps are exact aircraft state transitions, axis behavior, DMS/FOV/trim/mic/external-light details, and two-stage trigger behavior.
- Sensor formats are still mostly local. ASR, DAS, TFLIR/EOTS, SRCH, TWD, and TSD need a shared mission/sensor state model before they can produce reference-level troubleshooting and symbology outcomes.
- SMS/WPN-A have good inventory and bay-door UI foundations. EXCM ARM and CFFL program dispense now have first-pass state effects, but FRIU ownership, inventory mismatch, WPN-A errors, selective jettison, and full release logic remain incomplete.
- PHM/MSSTAT/CNI show the right kind of page. The obvious ICP GPA2B2/GPB label errors are fixed, but ICP associations, restart/recall actions, and network troubleshooting behaviors are incomplete.
- HUD/HMD combat/weapons symbology is much less complete than the AFTTP/Battle Book references.
- The provided 3-3 and Battle Book are enough to build several first-pass pages and visual states, but they are not a full current PMD/PCD interface specification. The sufficiency matrix below separates "buildable from provided PDFs" from "requires another source or a simulator design decision."

## Confirmed Gaps, No-Ops, And First-Pass Status

These are visible or configurable controls outside `PMD/DR>DEBUG` that either still do not perform the reference-level function or now have a documented first-pass approximation.

### P0 - HOTAS - TMS Directions

Finding: first-pass TMS short/long runtime behavior is now implemented. The mapping follows the attached table at a usable level: forward short designates NTS by current A/S or A/A context, forward long marks current steerpoint or single target track, aft short undesignates or selects DGFT in DAS context, aft long clears NTS/LST, left/right short step A/S or A/A NTS, and left long starts a TFLIR laser spot track. Remaining gaps are exact current-target selection, steerpoint promotion, ACM logic, sensor handoff, and display-specific cursor/NTS behavior.

Repo evidence: `scripts/cockpit_panel_state.py:118`, `scripts/cockpit_panel_state.py:363`, mapping UI at `main.py:6874`; first-pass runtime actions start at `main.py:22239`, with TMS handling around `main.py:23235`.

Reference: attached stick HOTAS table; Battle Book PDF p43/book 3-1 stick HOTAS; AFTTP A/S systems check references TMS actions around PDF pp217-221.

Sufficiency: Enough for first-pass representation using the attached mapping table. Partial for 1:1 behavior because the provided references do not expose the complete sensor-track state machine behind each TMS command.

Required to make accurate: exact TMS action table by master mode, DOI/POI, selected sensor, cursor/track state, NTS list contents, track quality, and expected display result.

### P0 - HOTAS - CMS Directions

Finding: the previous report incorrectly treated stick CMS as chaff/flare dispense. The attached stick table maps CMS to jam and EGL functions: forward puts a contact in the jam list/activates jam, left removes from the jam list, aft cases jamming, and z-axis places/removes the EGL donut. First-pass runtime state is now implemented and reflected on TWD, but it is not yet a real EW/jammer model. The simulator still uses the legacy internal action key `cms_right` for the visible `CMS Z` binding to preserve existing keybind compatibility.

Repo evidence: `scripts/cockpit_panel_state.py:130`, `scripts/cockpit_panel_state.py:375`, visible `CMS Z` label at `scripts/cockpit_panel_state.py:208`; mapping UI at `main.py:6893`; first-pass CMS action helper at `main.py:22902`; TWD HOTAS status display at `scripts/format_defs/twd.py:1260`.

Reference: attached stick HOTAS table; Battle Book PDF p43/book 3-1 stick HOTAS; Battle Book pp56-58/book 4-11 to 4-14 TWD/CM/EW context.

Sufficiency: Enough for first-pass jam/EGL state representation from the attached table. Partial for 1:1 behavior because exact EW target selection, jammer effectiveness, and TWD threat-state coupling are not specified in enough detail.

Required to make accurate: EW jam-list data model, selected-threat rules, jamming activation/deactivation logic, EGL placement/removal geometry, TWD feedback, audio/ICAWS effects, and degraded EW behavior.

### P0 - HOTAS - WPN REL MODE, NWS, MPO, CFFL, SPD BRK

Finding: first-pass runtime behavior is now implemented for these controls. WPN REL MODE z-plunge gives TFLIR/ASR slew control, NWS cycles ground low/high gain, MPO hold enables manual pitch override, CFFL forward/aft/z dispenses programs 1/2/3 when EXCM is armed, and speed brake forward/aft retracts/extends the modeled brake. Remaining gaps are speed-brake center hold semantics, exact APC PA-mode gating, external-light switch behavior, NWS ground-speed/weight-on-wheels rules, AIM-120 bore-launch cage/uncage behavior, and all DMS/FOV/trim/mic switch functions not yet modeled.

Repo evidence: `scripts/cockpit_panel_state.py:114`, `:117`, `:153`, `:156`, `:159`; mapping UI at `main.py:6870`, `:6873`, `:6897`, `:6900`, `:6903`; runtime helper/actions at `main.py:22779`, `main.py:22871`, `main.py:22948`, `main.py:23198`, and `main.py:23210`.

Reference: attached stick/throttle HOTAS tables; Battle Book PDF pp43-44/book 3-1 to 3-2 HOTAS maps; AFTTP taxi/NWS and speed-brake references in normal procedures.

Sufficiency: Enough for first-pass control response from the attached mapping tables. Partial for 1:1 behavior because the provided references do not define every valid/invalid aircraft state, inhibit, or indication.

Required to make accurate: exact per-control behavior by WOW/airborne state, PA mode, selected display/sensor, weapon state, switch detent/hold timing, cockpit/display indications, and failure/degraded interactions.

### P1 - HOTAS - Gun Trigger And Pickle

Finding: pickle now performs a first-pass release of one loaded station for the current A/A or A/S mode, using the local SMS/PMD station state. Gun trigger remains single-stage and still only decrements SMS gun count. The attached table requires half detent for TFLIR laser fire and second detent for gun fire, so the trigger model is still not reference-accurate. Release consent, LAR/DLZ, and inhibit logic are not modeled.

Repo evidence: gun fire handler at `main.py:20929`; release helper at `main.py:22834`; pickle action around `main.py:23262`; HOTAS trigger/pickle state around `main.py:23336`; gun loop call at `main.py:28481`.

Reference: attached stick HOTAS table; AFTTP pp193-198 A/A FEDS/AAGS and pp217-225 A/S LAR/DLZ/range references; Battle Book pp5-9, pp55-57.

Sufficiency: Enough for first-pass trigger/pickle mapping and visible store decrement. Partial for 1:1 weapon employment because the references do not provide release-computation algorithms or all inhibit conditions.

Required to make accurate: two-stage trigger input support, weapon release authorization model, LAR/DLZ calculations, trigger/pickle consent timing, station selection, inhibit conditions, and post-release store state.

### P1 - ASR - SPNT/TGT And Radar Modes

Finding: `SPNT/TGT` is now interactive and sets first-pass ASR NTS/SPNT state. ASR modes are still simplified to `NONE`, `SAR`, `WX`; no reference-level MTT/cue/re-cue/search/track behavior exists.

Repo evidence: mode options at `scripts/format_defs/asr1.py:1406`; SPNT/TGT button state around `scripts/format_defs/asr1.py:3049`; L3 action around `scripts/format_defs/asr1.py:3243`.

Reference: Battle Book PDF p61/book 4-21 radar/ASR, including SAR map and MTT concepts.

Sufficiency: Partial. The PDFs describe radar/ASR roles, but not exact ASR control-page logic.

Required to make accurate: ASR control-page layout, radar mode transition rules, MTT track symbology, search/cue behavior, SAR map products, and failure/degraded behavior.

### P0 - ASR - RADAR FAIL Maltese Cross

Finding: first-pass RADAR FAIL/Maltese Cross visual state is now implemented. The ASR page displays a RADAR FAIL condition with a Maltese-cross style symbol when PHM/RADAR status reports a fail/degraded/offline state. Exact symbol geometry, placement, and power-cycle timing remain approximate.

Repo evidence: ASR fail overlay helpers at `scripts/format_defs/asr1.py:87` and `scripts/format_defs/asr1.py:126`; PHM/RADAR state publication in `main.py`; active controls remain XMIT/BLANK/CAPTR/STOR/NORM/overlay/res.

Reference: Battle Book PDF p53/book 4-4 says RADAR FAIL troubleshooting depends on whether a Maltese Cross appears on ASR.

Sufficiency: Enough for first pass. The Battle Book provides the required procedural decision point and rough timing.

Required to make accurate: exact symbol geometry/placement and the simulator's failure-state trigger source if more than a procedural/visual approximation is desired.

### P0 - DAS - Remaining Page Fidelity Gaps

Finding: `OPER`, `NORM`, and `VIEW A-S` now have first-pass state effects and visual HOTAS/status feedback. `CNTL>` is still a placeholder, and the page does not model DAS AA IRST/SA IRST track generation or control subpages.

Repo evidence: buttons at `scripts/format_defs/das3d.py:400`, `:420`, `:439`, `:456`, `:475`, `:492`; HOTAS/status draw at `scripts/format_defs/das3d.py:544`; `on_osb` at `scripts/format_defs/das3d.py:596`; interactivity at `:612`.

Reference: Battle Book PDF pp58-60/book 4-15 to 4-19; AFTTP pp217-221 A/S systems checks and A2.6.1 avionics standards.

Sufficiency: Partial. The PDFs support visible page states and DAS/IRST concepts, but not exact OSB/page logic.

Required to make accurate: exact DAS OSB functions, page state transitions, camera/control page layout, IRST track generation, track symbology, and TWD fault arc mapping.

### P0 - TFLIR/EOTS - Remaining Page Fidelity Gaps

Finding: `A-S`, `LASER`, `MTT`, `HT`, `SPNT/TGT`, and `CUE/OFF` now have first-pass state effects and visible status feedback. `CNTL>` remains a placeholder. The page still lacks exact control subpages, laser inhibit logic, LST raster/timing, MTT behavior, and coordinate/range math.

Repo evidence: buttons at `scripts/format_defs/tflir3d.py:574`, `:593`, `:612`, `:631`, `:697`, `:716`, `:735`; HOTAS/status draw at `scripts/format_defs/tflir3d.py:790`; `on_osb` at `:802`; interactivity at `:846`.

Reference: Battle Book PDF pp59-60/book 4-16 to 4-19; AFTTP pp217-221.

Sufficiency: Partial. The PDFs provide strong visual/control references, but not complete EOTS/TFLIR state logic.

Required to make accurate: exact OSB behavior, control subpage layouts, laser inhibit logic, LST timing implementation details, track modes, range/coordinate math, and handoff rules.

### P0 - SMS/EXCM - EXCM ARM And CFFL First Pass

Finding: `EXCM ARM` confirmation now changes SMS state, and throttle CFFL program 1/2/3 first-pass dispense decrements local chaff/flare inventory when EXCM is armed. Exact program content, inventory-file semantics, expendable inhibits, and EXP JETT behavior remain approximate or absent.

Repo evidence: `scripts/format_defs/sms.py:2874`; EXCM arming state helper at `scripts/format_defs/sms.py:1343`; `L4`/confirmation handling at `scripts/format_defs/sms.py:3086`; CFFL dispense helper at `main.py:22871`.

Reference: Battle Book PDF p57/book 4-12 EXCM programming and EXP JETT behavior.

Sufficiency: Enough for first-pass page; partial for full behavior. The screenshot and high-level behavior are present, but not all program semantics.

Required to make accurate: exact EXCM program list semantics, loaded CM file schema, confirmation workflow, inventory decrement effects, and master-arm/inhibit edge cases.

### P1 - SMS - ET OPT And ET RUN

Finding: `ET OPT` and `ET RUN` render as status labels and are acknowledged only; no emergency/selected jettison sequence behavior.

Repo evidence: `scripts/format_defs/sms.py:2890`, `:2915`; `R3/R4` return true without behavior at `scripts/format_defs/sms.py:3086`.

Reference: Battle Book PDF p56/book 4-10 jettison sequence and WPN-A error info.

Sufficiency: Partial. The PDFs provide jettison context and sequence notes, not the full SMS command model.

Required to make accurate: selective/emergency jettison command mapping, valid station/state rules, timing, store inventory effects, and SMS/FRIU fault interactions.

### P0 - WPN-A - STEP And CNTL

Finding: `STEP` and `CNTL>` are clickable but no-op. WPN-A is a local selector page, not a weapon error/jettison page.

Repo evidence: `scripts/format_defs/wpn_a.py:222`, `:290`; `on_osb` no-op for L1/T5 at `scripts/format_defs/wpn_a.py:321`; interactivity at `:338`.

Reference: Battle Book PDF p56/book 4-10 WPN Page Error Info and Jettisoning.

Sufficiency: Partial. The PDFs provide WPN-A screenshots and error/jettison context, but not the full page tree.

Required to make accurate: full WPN-A page layout by weapon/status, selectable station behavior, all error mnemonics, jettison command mapping, and interaction with SMS/FRIU state.

### P1 - WPN-S - Profile Selection

Finding: `PROF 1` is rendered as a status label. `on_osb` returns true for T3, but `osb_is_interactive` excludes T3, so profile selection is effectively absent.

Repo evidence: `scripts/format_defs/wpn_s.py:198`, `:323`, `:338`, `:340`.

Reference: AFTTP pp217-225 A/S weapon setup, LAR/DLZ, range box; Battle Book pp7-8 A/S weapon symbology.

Sufficiency: Partial. The PDFs show A/S employment context, not the exact WPN-S profile implementation.

Required to make accurate: exact WPN-S profile page set, parameter validation ranges by weapon, profile selection behavior, and release-computation linkage.

### P1 - TWD - STBY, CNTL, DCLT

Finding: `STBY`, `CNTL>`, and `DCLT` are visible but do not open real control/declutter pages. `SEP` only separates overlapping icons.

Repo evidence: buttons at `scripts/format_defs/twd.py:1265`, `:1280`, `:1293`, `:1306`, `:1321`; `on_osb` at `:1506`.

Reference: Battle Book PDF pp57-58/book 4-13 to 4-14 TWD description/control/failure display.

Sufficiency: Partial. The PDFs show TWD controls and behavior concepts, but not the complete control-page layout.

Required to make accurate: exact TWD control-page layout, declutter behavior, threat-priority rules, launch indication inputs, and degraded/fail state inputs.

### P0 - TWD - Threat Alert Behavior

Finding: threat alert behavior is incomplete: no new-threat breathing animation, no threat audio, no launch flashing/tone sequence, and no degrade/fail arcs for EW/DAS.

Repo evidence: threat draw is generic icon placement at `scripts/format_defs/twd.py:971`, `:1435`; no code hits for the Battle Book audio/launch wording in TWD module.

Reference: Battle Book PDF pp57-58/book 4-13 to 4-14.

Sufficiency: Partial to enough for first pass. The PDFs provide alert descriptions and failure-arc examples, but not every threat-priority and audio edge case.

Required to make accurate: all threat prioritization rules, audio file/cue timing, launch indication inputs, and complete EW/DAS degradation taxonomy.

### P1 - TSD - MAP, ASGN, DEP

Finding: `MAP` is visibly disabled; `ASGN>` and `DEP` are rendered non-interactive.

Repo evidence: `MAP currently disabled` at `scripts/format_defs/tsd.py:5016` and `:5536`; button states at `scripts/format_defs/tsd.py:5050`, `:5096`; `osb_is_interactive` disables L4/R2/R4 at `scripts/format_defs/tsd.py:5851`.

Reference: Battle Book PDF p62/book 4-22 TSD controls; AFTTP pp193-198 and pp217-225.

Sufficiency: Partial. The PDFs provide many TSD visuals and examples, but not the complete TSD control tree.

Required to make accurate: MAP source/display rules, ASGN/DLINK page layouts, DEP behavior, EDW field definitions, symbol truth tables, track confidence rules, and message workflows.

### P1 - CNI - Recall, Reset, AUTON Restart

Finding: CNI recall/reset and AUTON restart paths contain explicit placeholder/no-op comments.

Repo evidence: `scripts/format_defs/cni.py:324`, `:331`, `:332`; `on_osb` T4/T5 confirm at `scripts/format_defs/cni.py:782`.

Reference: Battle Book PDF pp49-50/book 3-12 to 3-14 CNI/COMM/HQ/TOD; p53/book 4-4 troubleshooting; AFTTP A2.8.4 data link setup.

Sufficiency: Not enough for exact behavior. The PDFs show examples and context, but not the actual CNI CNTL state machine.

Required to make accurate: exact CNI CNTL actions, AUTON/CNTD/BASIC behavior, recall/reset effects, selected-row restart behavior, and page state diagrams.

### P1 - Status DATA LINK - MADL, LINK16, VMF

Finding: `MADL>`, `LINK16>`, and `VMF>` only set a status string; they do not open protocol pages or model message capabilities.

Repo evidence: buttons at `main.py:4880` to `main.py:4882`; handlers at `main.py:29869` to `main.py:29874`.

Reference: Battle Book PDF pp67-68/book 4-32 to 4-34; AFTTP p358/A2.8.4 data link setup.

Sufficiency: Partial. The PDFs identify functions and message examples, but not full page layouts or schemas.

Required to make accurate: missing page layouts, menu hierarchy, required fields, validation, transmit/receive workflow, and failure/inhibit states.

### P1 - INS/GPS - FIX, NAV FILTR, GPS

Finding: `FIX>`, `NAV FILTR>`, and `GPS>` are drawn as GOL buttons but their top-level handlers are pass-through/no-op.

Repo evidence: draw at `main.py:5951` to `main.py:5968`; no-op at `main.py:30727`.

Reference: AFTTP normal procedures and navigation accuracy references; Battle Book PDF p48/book 3-11 NAV accuracy/antennas.

Sufficiency: Not enough for exact behavior. The PDFs provide navigation context, but not the INS/GPS page spec.

Required to make accurate: INS/GPS page specification, GOL option effects, alignment/filter algorithms, GPS aiding states, failure modes, and display indications.

### P1 - HMD - ALIGN

Finding: `ALIGN>` is drawn but no-op.

Repo evidence: draw at `main.py:5348` to `main.py:5349`; no-op at `main.py:30737`.

Reference: AFTTP p44 ground HMD alignment and pp193-198 combat symbology; Battle Book pp5-9 and p53 HMD troubleshooting.

Sufficiency: Partial. The PDFs provide alignment context and combat symbology examples, but not the HMD alignment page workflow.

Required to make accurate: HMD alignment workflow, HMD/PCD HUD symbol rules by master mode, FEDS/AAGS algorithms, DLZ/LAR computations, and declutter interactions.

### P2 - ECS - OBOGS RESET

Finding: `OBOGS RESET` is explicitly disabled/non-interactive.

Repo evidence: `main.py:5144` to `main.py:5146`; disabled-zone filtering at `main.py:29462`.

Reference: Battle Book PDF p46/book 3-6 oxygen/BOS/OBOGS reference.

Sufficiency: Not enough for exact behavior. The PDFs give oxygen/OBOGS context, not ECS page reset behavior.

Required to make accurate: ECS page function spec, OBOGS reset effect, POST/fail state transitions, BOS interactions, ICAWS/HRC ties, and timing.

### P2 - FUEL - R1

Finding: FUEL `R1` prints to console but has no display or aircraft effect.

Repo evidence: `scripts/format_defs/fuel.py:1197` to `scripts/format_defs/fuel.py:1198`.

Reference: Battle Book PDF p45/book 3-5 fuel display examples.

Sufficiency: Not enough for exact behavior. The PDFs show fuel displays, but not the R1 OSB definition.

Required to make accurate: fuel page OSB map, R1 function definition, fuel transfer/refuel/emergency-refuel logic, and fault/inhibit behavior.

### P1 - CKLST - Missing Subpages

Finding: checklist page buttons flash/return true but all content is `Use paper checklist`; no actual EMER/SPECL/LIMITS/NORM/TACT pages.

Repo evidence: labels at `scripts/format_defs/cklst.py:85` to `:89`; text at `:105`; `on_osb` at `:109`.

Reference: AFTTP normal/abnormal procedure context; Battle Book quick-reference pages.

Sufficiency: Not enough from these PDFs alone. They provide procedures/checklists as reference material, not the aircraft checklist page hierarchy.

Required to make accurate: actual aircraft checklist page hierarchy, checklist item lists, completion/selection behavior, emergency/special/limits/normal/tactical page contents, and update authority.

## Reference Fidelity Gaps By Format

### ASR / Radar

Current ASR implementation is a useful synthetic SAR/WX visual format, but not a 1:1 radar/ASR model. It supports XMIT acquisition/processing, blank map, capture/store, overlay toggles, range, a basic none/SAR/WX mode set, first-pass SPNT/TGT state, and a first-pass RADAR FAIL/Maltese Cross overlay. It does not model:

- ASR failure/recovery timings tied to ICP-A/RADAR power cycles.
- MTT search/track techniques from the radar reference.
- Sensor cue/re-cue or LOS/helmet boresight radar modes.
- A reference-level ASR system check state matching AFTTP A/S checks.

Repo anchors: `scripts/format_defs/asr1.py:87`, `:126`, `:1025`, `:1406`, `:2831`, `:3049`, `:3243`.

References: Battle Book PDF p53/book 4-4, p61/book 4-21; AFTTP PDF pp217-225 and A2.6.1.

Reference sufficiency: enough for a first-pass Maltese Cross/RADAR FAIL visual and procedure state; partial for ASR MTT/cue/re-cue/radar modes.

Required to make accurate: exact ASR control pages, radar mode transition rules, MTT/search/track symbology, SAR product behavior, failure triggers, and timing/state sources.

### DAS

The DAS page is visually active and has six camera selections, 3D rendering, WHOT/BHOT toggling, and first-pass `OPER`, `NORM`, and `VIEW A-S` state. Missing reference behavior:

- Real `CNTL>` page behavior.
- DAS AA IRST track model and SA IRST GTL point model.
- FOV sector graphic and 2D angular track limitations.
- Tie-in to TWD DAS quadrant degrade/fail arcs and camera up/down labels.
- DAS/NVC station keeping and night/battle-damage check workflows.

Repo anchors: `scripts/format_defs/das3d.py:400`, `:420`, `:439`, `:456`, `:475`, `:492`, `:544`, `:596`, `:612`.

References: Battle Book PDF p58/book 4-15; AFTTP pp217-221, p355/A2.7.24.

Reference sufficiency: partial. The PDFs support visible DAS/FOV/IRST concepts, but not exact DAS OSB behavior or page transitions.

Required to make accurate: DAS control-page layout, per-camera controls, AA/SA IRST track generation and symbology, DAS/NVC station keeping behavior, and TWD fault arc mapping.

### TFLIR / EOTS / IRST / Laser

The TFLIR/EOTS page has a strong 3D video foundation and now has first-pass state for `A-S`, `LASER`, `MTT`, `HT`, `SPNT/TGT`, `CUE/OFF`, TMS laser spot track, and TFLIR/ASR slew control. It is still not the EOTS control model from the reference. Missing:

- LASER ARM/prevented-fire states and exact firing conditions.
- LST continuous/delayed/stop timing and scan pattern.
- IRST field-of-regard behavior.
- Reference-level MTT, point/area track, SPNT/TGT, and CUE/OFF behavior.
- EOTS coordinate generation and laser-ranging accuracy states.
- Reference FOV/zoom values and crosshair dimensions.

Repo anchors: `scripts/format_defs/tflir3d.py:574`, `:593`, `:612`, `:631`, `:697`, `:716`, `:735`, `:790`, `:802`, `:846`; HOTAS TMS/LST handling in `main.py:23235`.

References: Battle Book PDF pp59-60/book 4-16 to 4-19; AFTTP pp217-221 and A2.6.1.

Reference sufficiency: partial. The PDFs are strong for visuals and high-level laser/LST/IRST behavior, but not enough for an exact EOTS/TFLIR state machine.

Required to make accurate: full OSB map, control subpages, laser inhibit logic, LST timing and raster implementation, MTT/track mode behavior, coordinate/range calculations, and handoff rules.

### TWD / CM / EW

TWD renders rings and threat icons from contact data, with RWR SS options and a separator hold. It does not yet match the threat warning behavior:

- No new-emitter breathing animation.
- No threat audio or launch audio sequence.
- No middle-ring tone logic.
- No launch-associated flashing until launch indication clears.
- No degraded/failed EW and DAS arcs.
- No CM/TWD inventory linkage for chaff/flare/IRCM/RFCM status.

Repo anchors: `scripts/format_defs/twd.py:5`, `:971`, `:1265`, `:1280`, `:1293`, `:1306`, `:1321`, `:1506`.

References: Battle Book PDF pp56-58/book 4-11 to 4-14; AFTTP p347/A2.6.1 and pp121-122.

Reference sufficiency: partial to enough for first pass. The PDFs support rings, visible alert behavior, and degrade/fail arc examples; exact threat logic still needs more detail.

Required to make accurate: threat prioritization rules, launch indication inputs, audio cue timing/assets, CM inventory linkage, TWD control pages, and complete EW/DAS degradation taxonomy.

### SMS / WPN-A / WPN-S / Stores

SMS has the best internal foundation among the combat formats. It has station inventory programming, weapon icons, train/live behavior tied to master arm, bay-door animation, chaff/flare counts, first-pass EXCM ARM state, and first-pass CFFL program inventory decrement. Reference gaps:

- No automatic `INV MISMATCH` status rendering when actual and loaded inventory differ; `SMS LOAD INVALID` exists only as an ICAWS catalog entry.
- FRIU ownership and failed-store behavior are not tied into station employment/jettison state.
- Exact EXCM program semantics and inhibit/degraded behavior are not modeled.
- `ET OPT` and `ET RUN` are status-only/no-op.
- WPN-A does not show referenced weapon error/jettison pages and does not drive selective jettison.
- WPN-S profiles/data entries are standalone and not tied to actual release, DLZ, LAR, or weapon employment.
- Console-left `JETT` panel updates selector/counter state only; no store state change was found.

Repo anchors: `scripts/format_defs/sms.py:2874`, `:2890`, `:2915`, `:3086`, `:3216`; CFFL helper at `main.py:22871`; `scripts/format_defs/hrcs_catalog.py:803`; `scripts/format_defs/wpn_a.py:222`, `:290`, `:321`; `scripts/format_defs/wpn_s.py:198`, `:323`, `:338`, `:340`; `scripts/cockpit_panel_state.py:1567` to `:1593`.

References: Battle Book PDF pp54-57/book 4-7 to 4-12; AFTTP pp217-225 and A2.7.6.

Reference sufficiency: enough for first-pass inventory mismatch, SMS LOAD INVALID, FRIU ownership, and EXCM/WPN-A visual pages; partial for exact full behavior.

Required to make accurate: full SMS/FRIU state model, all store failure mnemonics, selective/emergency jettison rules, EXCM program semantics, loaded CM file schema, weapon-specific WPN-S profiles, and release-computation linkage.

### TSD / EDW / Fusion / Data Link

TSD is visually close in broad layout and has useful live/sim/Link-16 contact rendering, DCLT options, range controls, cursor/TOI logic, and HSD/VSD views. Remaining gaps:

- `MAP` is intentionally disabled, conflicting with reference TSD setup.
- `ASGN>` and `DEP` are visible but non-interactive.
- EDW taxonomy is partial compared with IFF, radar, AA/AS ESM, L16 PPLI/surveillance, EOB, and fighter EDW examples.
- TSD symbols are approximate and based on local icon assets; the Battle Book shows a larger trusted/untrusted/mixed taxonomy, radar dish, missile/weapon, Link-16, HMD threat, and fusion-specific symbology.
- Link-16/MADL/VMF behaviors are modeled as local UDP/net payloads rather than message-type workflows such as waypoint transmit, assignment, J12/J3.5 display, breathing, and data-audio differences.
- DCLT has several controls, but they act as local display filters rather than complete aircraft display-management behavior.

Repo anchors: `scripts/format_defs/tsd.py:1198` to `:1221`, `:4179`, `:4625`, `:5016`, `:5024`, `:5050`, `:5096`, `:5536`, `:5757`, `:5851`; icons under `icons/TSD/`.

References: Battle Book PDF pp62-68/book 4-22 to 4-34; AFTTP pp193-198, pp217-225, p358/A2.8.4.

Reference sufficiency: partial. The PDFs provide many visuals, EDW examples, and message examples, but not the complete TSD/DLINK/ASGN control tree.

Required to make accurate: MAP source/display rules, ASGN/DLINK page layouts, EDW field definitions, symbol truth tables, track confidence rules, participant/message schemas, and display/audio cue workflows.

### PHM / MSSTAT / ICP / Network

PHM/MSSTAT shows systems, networks, and ICP rows. The first-pass GPA2B2 and GPB label fixes are applied, but several items still need correction for reference fidelity:

- ICP associations are not displayed or modeled; rows are just statuses.
- Network rows are hard-coded and not tied to the Battle Book troubleshooting outcomes.
- GPIO/FRIU BIT troubleshooting and ICP switch-cycle effects are not modeled as state transitions.
- PHM visible controls such as DL/VHF, HIST, and XMIT REPORT appear disabled/non-interactive.

Repo anchors: `scripts/format_defs/phm.py:1069` to `:1089`, `main.py:20603` to `main.py:20607`; PHM interactivity around `scripts/format_defs/phm.py:1375` and `:1499`.

References: Battle Book PDF pp51-54/book 4-1 to 4-7.

Reference sufficiency: enough for first-pass ICP name/association correction; partial for live network/ICP/GPIO troubleshooting behavior.

Required to make accurate: exact row ordering/status color rules, ICP A/B and network state machines, GPIO/FRIU BIT effects, sensor power-cycle timers, and ICAWS/HRC assert/clear rules.

### CNI / COMM / Data Link Status Pages

CNI/COMM has a good interactive local radio setup, audio/guard/secure toggles, and a data-link net page. Gaps:

- CNI recall/reset/AUTON restart are explicit placeholders.
- Data-link `MADL>`, `LINK16>`, and `VMF>` buttons do not open real pages.
- Link-16/MADL message capability matrix, waypoint transmit/receive, assignment flow, and display breathing/audio differences are not represented.
- AFTTP A2.8.4 data-link callsign standard is not enforced beyond editable text fields.

Repo anchors: `scripts/format_defs/cni.py:22`, `:23`, `:324`, `:331`, `:332`, `:782`; `main.py:4880`, `:4881`, `:4882`, `:29869` to `:29874`.

References: Battle Book PDF pp49-50/book 3-12 to 3-14 and pp67-68/book 4-32 to 4-34; AFTTP p358/A2.8.4.

Reference sufficiency: partial for COMM/DATA LINK visuals and examples; not enough for exact CNI recall/reset/AUTON behavior.

Required to make accurate: CNI CNTL action spec, AUTON/CNTD/BASIC page behavior, recall/reset state effects, data-link page layouts, message schemas, validation rules, transmit/receive flows, and failure modes.

### HUD / HMD / Combat Symbology

HUD currently renders a flight/ADI-style overlay with airspeed, altitude, heading, pitch ladder, roll cue, and a small status block. It does not implement combat/weapons HUD/HMD symbology:

- No AAGS/FEDS assessment.
- No A/A gun funnel/snap/gun cues.
- No AIM-120/AIM-9 DLZ or shoot cues.
- No A/S weapon DLZ/LAR/range-box reference.
- No weapon-mode-specific HMD overlays beyond status-menu declutter toggles.
- HMD `ALIGN>` is a no-op.

Repo anchors: `scripts/format_defs/hud.py:4` to `:269`; HMD status page draw at `main.py:5348`; no-op at `main.py:30737`.

References: AFTTP pp193-198 and pp217-225; Battle Book PDF pp5-9 and pp47-48.

Reference sufficiency: partial. The PDFs provide combat symbology examples and HMD alignment context, but not enough for exact algorithms or page workflows.

Required to make accurate: HMD alignment workflow, HUD/HMD symbol rules by master mode, FEDS/AAGS algorithms, A/A and A/S DLZ/LAR calculations, shoot-cue logic, and declutter interactions.

### CKLST / Status Utilities

CKLST is currently a placeholder. For a 1:1 simulator, it should either become an actual checklist hierarchy or be clearly marked as an unavailable paper-reference shortcut. ECS OBOGS reset, INS/GPS FIX/NAV FILTR/GPS, and some status arrows also need cleanup.

Repo anchors: `scripts/format_defs/cklst.py:85` to `:113`; `main.py:5144`, `:5951` to `:5968`, `:30727`.

References: AFTTP normal procedures and service standards; Battle Book PDF pp46-48 and mission reference pages.

Reference sufficiency: not enough for exact CKLST/ECS/INS-GPS/FUEL utility behavior. The PDFs provide procedure and system context, not the cockpit page specs.

Required to make accurate: checklist page hierarchy and item lists, ECS OBOGS reset behavior, INS/GPS GOL option effects, fuel page OSB definitions, and related fault/ICAWS/HRC state transitions.

## Visual/Image Comparison Notes

Reviewed current screenshots:

- `docs/screenshots/full-pcd-layout.png`
- `docs/screenshots/tsd-format.png`
- `docs/screenshots/cockpit-panels.png`
- `docs/screenshots/das-format.png`
- `docs/screenshots/tflir-format.png`
- `docs/screenshots/sms-format.png`

Reviewed rendered Battle Book sheets:

- `tmp/pdfs/f35_battle_book/sheets/sheet_05_pages_037-045.png`
- `tmp/pdfs/f35_battle_book/sheets/sheet_06_pages_046-054.png`
- `tmp/pdfs/f35_battle_book/sheets/sheet_07_pages_055-063.png`
- `tmp/pdfs/f35_battle_book/sheets/sheet_08_pages_064-072.png`

Reviewed attached HOTAS mapping tables:

- Stick mappings for DMS, FOV, CMS, NWS, paddle, trim, WPN REL MODE, TMS, trigger, and pickle.
- Throttle mappings for mic, speed brake, CFFL, cursor slew, management switch, speed hold, polarity, WMS, APC, external lights, MPO, and cage/uncage.

Visual mismatches to prioritize:

- TSD: current TSD resembles the HSD page, but Battle Book pp62-64 show more specific EDW, TSD option, and symbol taxonomies than the current icon set and enabled buttons.
- TWD: current rings and contacts are present, but Battle Book pp57-58 include specific alert animation, threat audio, launch, and degrade/fail arc depictions.
- DAS: current 3D camera view does not match the Battle Book DAS FOV diagrams and AA/SA IRST track examples.
- TFLIR/EOTS: current video page lacks the Battle Book FOV/zoom chart, laser/LST scan, coordinate-generation overlay, IRST FOR, and referenced crosshair dimensions.
- SMS: current SMS aircraft/station view is close enough to build on, but it does not show the exact inventory mismatch, degraded/failed store, FRIU, and WPN-A error states from Battle Book pp55-56.
- MSSTAT/ICP: current PHM/MSSTAT page now has the obvious GPA2B2/GPB label fixes, but still needs exact ICP association descriptions from Battle Book p52/book 4-2.
- HUD/HMD: current HUD is a flight display, not the combat employment symbology shown in Battle Book pp5-9 and AFTTP pp193-198.
- Text encoding: two UI strings are mojibake and should be fixed before any visual polish pass: `main.py:4908`, `main.py:4911`, and `main.py:5138`.

## Reference Sufficiency Guidance

- Build directly from the provided PDFs and attached HOTAS tables first where sufficiency is "Enough for first pass": HOTAS control response, ASR Maltese Cross, PHM/MSSTAT naming/associations, SMS mismatch/FRIU basics, and EXCM/WPN-A first-pass visuals.
- For "Partial" items, implement page scaffolds and visible states from the PDFs, but keep behavior behind explicit simulator assumptions until a better source is available.
- For "Not enough" items, avoid inventing exact aircraft behavior. Either gray the control out, label it unsupported in a developer-only audit, or implement a documented simulator approximation.

## Suggested Implementation Order

1. HOTAS fidelity pass 2: add DMS/FOV/trim/mic/external-light behavior, real cursor slew axes, speed-brake center hold semantics, and two-stage trigger support.
2. Shared sensor state: create one source of truth for sensor availability, scan schedules, target/TOI/SPI, laser/LST/IRST, and degradation. Use it from ASR, DAS, TFLIR, SRCH, TWD, TSD, SMS, and PHM.
3. ASR/radar failure pass 2: add ICP-A/radar cycle timing, ASR modes beyond SAR/WX/NONE, and reference-level MTT/search/track behavior.
4. SMS/WPN-A/CM model: implement inventory mismatch, FRIU ownership, selective/emergency jettison effects, EXCM programming/jettison, and WPN-A error displays.
5. TFLIR/DAS/EOTS: wire visible OSBs into laser/LST/IRST/track/FOV behavior and display the reference graphics/states.
6. TWD: add threat breathing, launch flashing/audio state, middle-ring tone state, and EW/DAS degrade/fail arcs.
7. TSD/EDW/data link: re-enable/reference-match map behavior, implement ASGN/DLINK pages, expand EDW and symbol taxonomy, then connect Link-16/MADL/VMF message flows.
8. PHM/CNI/MSSTAT: add association text and make network/ICP/GPIO troubleshooting affect mission systems.
9. HUD/HMD combat symbology: add FEDS/AAGS, DLZ/LAR, shoot cues, A/S range-box cues, and HMD alignment behavior.
10. Cleanup pass: fix mojibake arrows, replace console-print-only controls with visible feedback, and either implement or gray out all placeholder buttons.

## Quick Fix List

- Replace mojibake arrows in `main.py:4908`, `main.py:4911`, and `main.py:5138`.
- Remove or gray out `ASGN>`, `DEP`, `TWD CNTL>`, `TWD DCLT`, `DAS CNTL>`, `TFLIR CNTL>`, WPN-A `CNTL>`, and CKLST subpages until they open real pages.
- Add an audit/debug overlay or automated test that lists every rendered `ButtonState` whose click handler returns true without changing state.
- Add regression tests for HOTAS action coverage: every `HOTAS_ACTION_ORDER` entry should either have a handler, be an axis-only action, or be explicitly marked unsupported.
