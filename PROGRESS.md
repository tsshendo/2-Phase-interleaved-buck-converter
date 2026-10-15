# Progress log

## Current stage
**Stage 1: Architecture (proposal written, awaiting review)** on branch `stage-1-architecture`.
Next: Stage 1 review, then Stage 2 (schematic + ERC).

## Stage checklist
- [x] 0. Repo set up (structure, CLAUDE.md, CI, issues)
- [ ] 1. Architecture: controller IC, control-supply IC, protection parts, stack-up, calculations
- [ ] 2. Schematic + ERC, BOM updated
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
| 2026-10-15 | Proposed: LM5012 (5.2 V buck), LM5069-2 hot-swap + IPT015N10N5 + VOM1271 reverse FET, AMC3301/AMC3330, INA301A3 OCP | See `docs/design/` (pending review) |
| 2026-10-15 | Stack-up: 4 × 2 oz, JLC04161H-3313 | Thin prepreg for a low loop inductance; 46 A capacity (accepted at review) |
| 2026-10-15 | Keep ERUC23-3R2K and EPC2304; accept about 53–70 % per-phase ripple (output < 10 %) | Existing simulations are built on these parts (Stage 1 review) |
| 2026-10-15 | Input OVP: precise 82 V via a TLV3012 (U22) driving LM5069 OVLO | User prefers 82 V over 83.5 V; LM5069 tolerance alone could trip at 79.2 V |
| 2026-10-15 | Hot-swap pass FET 100 V (IPT015N10N5) | Lower loss; 100 V accepted at review |
| 2026-10-15 | Digi-Key stock handled by the user | User choice |

| 2026-10-15 | PS1 stays NME1S0505SC (1 W) | User choice; 65–88 % load, output voltage to be checked in Stage 2 |

## Open questions
- PS1 output voltage at 130–176 mA vs AMC3330 4.5 V min / LTC3861 5.5 V max (Stage 2).
- ERUC23-3R2K saturation definition per winding vs the 31 A peak (TDK datasheet, Stage 2 check).
- Fuse 0456025.ER DC voltage rating (Littelfuse datasheet, Stage 2 check).

## Known discrepancies to fix
- C1–C4 schematic value 2.5 µF → 2.2 µF (BOM part GRM21BD72A225KE01L).
- 0402 parts in BOM (e.g. ERJ-2GE, RC0402, GRM155) → 0603 equivalents.
- C6 shows 440 µF in the schematic vs. EGXF 110 µF ×5 in the BOM: reconcile.

## Session notes
### 2026-10-15: Setup
Repo restructured; KiCad project, BOM, reports and LTspice files imported from the local
`Final Project` folder. Vendor libraries, datasheets and SPICE models are local only (licenses).

### 2026-10-15: Stage 1 architecture
Wrote `docs/design/` (architecture/isolation, power-stage calcs, stack-up/IPC, thermal, control
supply/fan, protection, parts list). Parts were checked against manufacturer pages and datasheets.
LCSC stock was read from lcsc.com. Digi-Key was blocked by bot verification, so the user must confirm
it. The ERUC23-3R2K parameters came from the local TDK LTspice model (not committed). Found that the
coupled-inductor ripple spec isn't met (open question). No KiCad files were changed.
