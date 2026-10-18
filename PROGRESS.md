# Progress log

## Current stage
**Stage 3: Footprints + placement (done, awaiting review)** on branch `stage-3-placement`.
Next: placement review (`docs/design/placement_stage3.md`), then Stage 4 (routing + DRC).

## Stage checklist
- [x] 0. Repo set up (structure, CLAUDE.md, CI, issues)
- [x] 1. Architecture: controller IC, control-supply IC, protection parts, stack-up, calculations (PR #7)
- [x] 2. Schematic + ERC, BOM updated (PR #8)
- [x] 3. Placement (bottom: power stage; top: inductor + controls), awaiting review
- [ ] 4. Routing + DRC (JLCPCB 4-layer rules)
- [ ] 5. Outputs: Gerbers, drill, CPL/BOM, 3D render, design note

## Decisions log
| Date | Decision | Reason |
|---|---|---|
| 2026-10-15 | Input range 64.8–79.2 V (72 V ±10 %); never above 80 V | Upstream supply spec |
| 2026-10-15 | Standalone analog controller, no MCU/telemetry, R/C configured | Minimum parts, no programming |
| 2026-10-15 | One minimal ≥ 100 V-input buck allowed for 5 V control/fan rail | Plug-in device, 72 V is the only input; fan load rules out linear-only |
| 2026-10-15 | Controller VIN ≥ 100 V preferred; 80 V part only with ≤ 75 V supply clamp | 79.2 V max input leaves no margin at 80 V |
| 2026-10-15 | Protection: OCP hiccup; OVP/OTP latch; OTP 80 °C; input OVP ~82 V; UVLO ~62/60 V | User choices |
| 2026-10-15 | Rack step-down use, no back-feed | Use case |
| 2026-10-15 | JLCPCB, 4-layer, 1.6 mm, ≥ 0603, double-sided (power stage bottom, inductor/controls top) | Fab and assembly plan |
| 2026-10-15 | Heavier copper allowed if needed | User OK |
| 2026-10-15 | High-current: Würth REDCUBE-style bolt-down terminals; low-current: Molex Micro/Nano-Fit family | User choice |
| 2026-10-15 | Fan: Sanyo Denki 9GA0405P6H001 (5 V, 0.35 A, 191 Pa); in stock on Digi-Key | Pushes ~5 CFM / 4–4.5 m/s through Z60-12.7B |
| 2026-10-15 | Heatsink: Alpha Novatech Z60-12.7B (from report) | Reference design |
| 2026-10-15 | KiCad 10.0 | User's version |
| 2026-10-15 | All LV control electronics and signals isolated from the HV power path; the control-side supply is isolated | User requirement (Stage 1) |
| 2026-10-15 | AT1/AT2 SI86S620BC and PS1 kept (new roles: HV→LV fault flags, isolated LV supply) | Follows from the isolation requirement |
| 2026-10-15 | LTC7890 rejected; controller = ADI LTC3861 (voltage mode, PWM outputs) on the LV side | LTC7890 drivers/sense sit on power ground, so it can't be isolated |
| 2026-10-15 | Switching frequency 200 → **250 kHz** per phase | LTC3861 minimum is 250 kHz; voltage mode suits slow isolated feedback (user approved) |
| 2026-10-15 | 1EDN7550 ×4 → Si8274GB1-IS1 ×2 isolated half-bridge drivers | Isolation + dead time; 1EDN static CMR marginal at 79 V high side |
| 2026-10-15 | Heatsink Z60-12.7B kept, ~3 mm overhang per side | User choice |
| 2026-10-15 | LM5012 (5.2 V buck), LM5069-2 hot-swap + IPT015N10N5 + VOM1271 reverse FET, AMC3301/AMC3330, INA301A3 OCP | Stage 1 review |
| 2026-10-15 | Stack-up: 4 × 2 oz, JLC04161H-3313 | Thin prepreg for a low loop inductance; 46 A capacity (accepted at review) |
| 2026-10-15 | Keep ERUC23-3R2K and EPC2304; accept about 53–70 % per-phase ripple (output < 10 %) | Existing simulations are built on these parts (Stage 1 review) |
| 2026-10-15 | Input OVP: precise 82 V via a TLV3012 (U22) driving LM5069 OVLO | User prefers 82 V over 83.5 V; LM5069 tolerance alone could trip at 79.2 V |
| 2026-10-15 | Hot-swap pass FET 100 V (IPT015N10N5) | Lower loss; 100 V accepted at review |
| 2026-10-15 | Digi-Key stock handled by the user | User choice |
| 2026-10-15 | PS1 stays NME1S0505SC (1 W) | User choice; 65–88 % load, output voltage to be checked |
| 2026-10-16 | Schematic: 9 pages; one phase sheet instantiated twice; fault logic/rack I/O nested under the controller | Readability, no duplicated circuitry |
| 2026-10-16 | AT2 ch B = hot-swap bus-good (LM5069 PGD) instead of fan tach | Don't start switching while VBUS is still charging; tach stays on a test pad |
| 2026-10-16 | Si8274 ENABLE from LTC3861 PWMEN; RUN_OK (diode wired-AND) drives RUN1/RUN2 | Same protection with less logic; PWMEN pull-downs required by the datasheet |
| 2026-10-16 | EPC2304 pad 2 = Kelvin source net, joined to SW/PGND through net-ties NT1–NT4 | Enforces the Kelvin gate return in layout |
| 2026-10-16 | Bulk C5/C6 = 2 × EGXF 110 µF | Matches CLAUDE.md C5/C6; resolves the "×5" BOM discrepancy |
| 2026-10-16 | LM5069 VIN without series resistor | Series R would offset the 55 mV current-limit sense |
| 2026-10-16 | BOM generated from the schematic (`kicad/tools/make_bom.py`); previous BOM kept as a sheet | One source of truth |
| 2026-10-16 | Own footprints for EPC2304, ERUC23, CSS2H shunts, NANO2 fuse drawn from datasheets; vendor STEP models (and Würth/SamacSys footprints) kept local in `kicad/lib/vendor` | SamacSys EPC2304/ERUC23 footprints wrong; licenses forbid redistribution |
| 2026-10-16 | F1 not fitted (option); R96 CSS2H-2512C-000 link; LM5069 breaker = eFuse | 0456025.ER only 72 VDC; no ≥ 25 A / ≥ 100 VDC SMD fuse found (user decision) |
| 2026-10-16 | D15/D16 footprint SOT-323 (was SOD-323) | BAT54W is SOT-323; pin 3 had no pad |
| 2026-10-17 | Test points 1.0 mm pads, all on top | Bottom is under the heatsink; 1.5 mm pads did not fit |
| 2026-10-17 | Half-bridge: LS above HS, strips aligned (SW on L4 only), LS gate at the driver, HS gate at the far end | Smallest commutation loop and SW area; bottom-mounted Si8274 is mirrored |
| 2026-10-17 | Heatsink pedestal 3.0 mm (was ~2.5); hot-swap stage on the bottom under the heatsink | Fits SOIC-16W/SMC/TOLL under the heatsink; top side full |
| 2026-10-17 | Heatsink screws at (36.8, 3.7/50.3) and (68.7, 20/34) | Corners hold the barrier column and terminals |
| 2026-10-17 | Stack-up written to the board (4 × 70 µm, 3313, 1.60 mm, ENIG); JLC rules + 2.5 mm LV_ISO barrier rule in `ECE533_Guide.kicad_dru` | Stage 1 stack-up; isolation enforced by DRC |

## Open questions
- PS1 output voltage at 130–176 mA vs AMC3330 4.5 V min / LTC3861 5.5 V max (bench check).
- ERUC23-3R2K saturation definition per winding vs the 31 A peak (TDK datasheet).
- Starting values to confirm in SPICE/bench: compensation, LM5012 ripple injection, dead time,
  LM5069 power limit vs Q1 SOA (`docs/design/schematic_stage2.md` §7).
- PS1 SIP-4 pin 2–3 spacing (0.92 mm) across the barrier: accept, slot, or other module (placement note §7).
- High-side gate path at the far end of each FET pair (placement note §3).

## Known discrepancies (resolved in Stage 2)
- C1–C4 value is 2.2 µF (GRM21BD72A225KE01L). Done.
- All parts 0603 or larger. Done.
- Bulk C5/C6: 2 × EGXF 110 µF; output caps are a separate group (C60–C67). Done.

## Session notes
### 2026-10-15: Setup
Repo restructured; KiCad project, BOM, reports and LTspice files imported from the local
`Final Project` folder. Vendor libraries, datasheets and SPICE models are local only (licenses).

### 2026-10-15: Stage 1 architecture
Wrote `docs/design/` (architecture/isolation, power-stage calcs, stack-up/IPC, thermal, control
supply/fan, protection, parts list). Review decisions recorded above. PR #7 merged.

### 2026-10-16: Stage 2 schematic
- Built the project symbol library from datasheet pinouts (`kicad/tools/gen_symbols.py`) and the
  9-page hierarchical schematic (`gen_schematic.py`).
- Every page was rendered and reviewed for readability.
- ERC: 0 errors, 11 warnings (custom footprints, Stage 3). Netlist connectivity: 74/74 checks pass
  (`check_netlist.py`).
- CI now installs KiCad's default library tables and blocks on ERC errors.
- BOM regenerated from the schematic: 94 lines / 248 parts, 47 LCSC numbers verified.
- Notes: `docs/design/schematic_stage2.md`.

### 2026-10-16/17: Stage 3 footprints and placement
- Footprints: EPC2304, TDK ERUC23, Bourns CSS2H (Kelvin + 2-terminal), NANO2 456 drawn from the
  datasheets (`kicad/tools/gen_footprints.py`); Würth REDCUBE and Murata NME1S from the vendor
  libraries (local `ECE533_Vendor`). Every 3D model aligned and checked by rendering (from below
  through a board cut-out for the EPC2304 and ERUC23).
- `check_footprints.py`: 273/273 symbol pins match their pads (found the D15/D16 SOT-323 error).
- F1 fuse decision (DNP option + R96 link), test points 1.0 mm.
- Board built from the netlist with `kicad/tools/build_pcb.py`: outline, stack-up, layer names, net
  classes, JLC rules + isolation rule (`ECE533_Guide.kicad_dru`), heatsink/pedestal/duct outlines,
  barrier rule area, placement of all 273 footprints (134 on the bottom).
- DRC with schematic parity: 0 errors, 0 parity issues, 1 silkscreen warning, 499 unrouted (Stage 4).
  ERC: 0 violations.
- Notes and renders: `docs/design/placement_stage3.md`.

## Power module (separate project, branch `power-module`)
A power-stage-only board, `kicad/PowerModule`, made at the user's request (2026-10-17). It uses the
report's base schematic and parts and the report's SolidWorks/Q3D layout. Gate commands come in
through J4. Note: `docs/design/power_module.md`.

| Date | Decision | Reason |
|---|---|---|
| 2026-10-17 | Board: credit card 85.6 × 53.98 mm; REDCUBE terminals; Z60-12.7B with 4 × M3 holes | User answers |
| 2026-10-17 | "Two-layer like report": L1 = 1st Cu plane, L4 = 2nd Cu plane (FETs), L2 + L3 = interstitial shield (SHIELD = centre tap of C1/C2, C3/C4) | User answer; L3 used as a second shield layer next to the switch nodes (can be deleted) |
| 2026-10-17 | Base schematic kept; only added footprints/values/MPNs, a SHIELD label joining the centre taps, PWR_FLAGs; orphan `connectors.kicad_sch` dropped | "Schematic ready as given" |
| 2026-10-17 | EPC2304 15-pin footprint variant (pins 8–15 stacked on pads 1–7) | Base SamacSys symbol has 15 pins |
| 2026-10-17 | Kelvin island under each HS driver on L4, tied to the switch node once at the FET | Gate return under the gate trace; SK pad kept off the power path |
| 2026-10-17 | LS drivers moved between the phases next to the LS FETs (driver→gate 4.8 mm, was 11–14 mm) | User: gate traces too long |
| 2026-10-17 | Bulk caps split: C5+C15, C6+C16 = 2 × EGXF 62 µF / 160 V each | User: half values for lower ESR; GXF 160 V has no 55 µF, 62 µF keeps ≥ 110 µF per position |
| 2026-10-17 | J4 centred on the left edge, PS1 moved to the bottom left, H2 screw to (28.4, 50.6) | User: centred connector, shorter control traces |
| 2026-10-17 | All reference designators on silkscreen; owner block on the bottom silkscreen (2.0 mm) | User request |
| 2026-10-17 | Bulk caps mirror-symmetric: C6/C16 top edge, C5/C15 bottom edge, x 37.5 / 64.6 | User: symmetric, 2 per edge; inductor body offset forces one pair each side of it |
| 2026-10-17 | PS1 on J4's centreline; J4 right angle, overhanging the edge 2.2 mm, project footprint + model | User request; KiCad has no Nano-Fit model |

Status: ERC 0 errors (6 off-grid warnings from the base drawing); DRC with schematic parity 0 / 0 / 0.
Open items: VOUT copper on one layer and the 2.6 mm VBUS neck (thermal); loop inductance not
extracted; 1EDN7550B high-side common-mode margin; PS1 pitch; confirm the 1EDN7550BXTSA1 Digi-Key PN
and stock (`power_module.md` §7).
