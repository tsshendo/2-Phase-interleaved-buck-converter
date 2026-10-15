# Progress log

## Current stage
**Stage 0: Setup (done).** Next: **Stage 1: Architecture, controller choice and part list.**

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

## Open questions
- Remove AT1/AT2 isolators and PS1 (expected yes, since there's no isolation needed): confirm in Stage 1.
- Heatsink is 60 mm and the board is 53.98 mm wide: accept ~3 mm overhang per side, or a smaller heatsink?
- Controller IC selection (Stage 1).

## Known discrepancies to fix
- C1–C4 schematic value 2.5 µF → 2.2 µF (BOM part GRM21BD72A225KE01L).
- 0402 parts in BOM (e.g. ERJ-2GE, RC0402, GRM155) → 0603 equivalents.
- C6 shows 440 µF in the schematic vs. EGXF 110 µF ×5 in the BOM: reconcile.

## Session notes
### 2026-10-15: Setup
Repo restructured; KiCad project, BOM, reports and LTspice files imported from the local
`Final Project` folder. Vendor libraries, datasheets and SPICE models are local only (licenses).
