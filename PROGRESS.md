# Progress log

## Current stage
**Stage 2: Schematic + ERC (done, awaiting review)** on branch `stage-2-schematic`.
Next: Stage 2 review, then Stage 3 (custom footprints + placement).

## Stage checklist
- [x] 0. Repo set up (structure, CLAUDE.md, CI, issues)
- [x] 1. Architecture: controller IC, control-supply IC, protection parts, stack-up, calculations (PR #7)
- [x] 2. Schematic + ERC, BOM updated (awaiting review)
- [ ] 3. Placement (bottom: power stage; top: inductor + controls), reviewed
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

## Open questions
- PS1 output voltage at 130–176 mA vs AMC3330 4.5 V min / LTC3861 5.5 V max (bench check).
- ERUC23-3R2K saturation definition per winding vs the 31 A peak (TDK datasheet).
- Fuse 0456025.ER DC voltage rating (Littelfuse datasheet).
- Starting values to confirm in SPICE/bench: compensation, LM5012 ripple injection, dead time,
  LM5069 power limit vs Q1 SOA (`docs/design/schematic_stage2.md` §7).
- Vendor footprints for EPC2304/ERUC23 aren't on this machine (`kicad/lib/vendor/` is empty):
  Stage 3 will draw them from the datasheets in `ECE533_Mods.pretty`.

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
