# Project: 72 V → 24 V, 1.1 kW, 2-Phase Interleaved Coupled-Inductor GaN Buck — Credit-Card PCB

> Start every session by reading `PROGRESS.md` (current stage, decisions, open questions).
> Repo-specific working rules are in §9–§10 at the bottom.

## 1. Goal
Turn the ECE 533 final-project design (Team MeGaNism, `docs/ECE533_Final_Report.pdf`) into a complete,
manufacturable PCB designed in **KiCad 10.0**. The board is credit-card size and shape and holds the
power stage, gate drive, a standalone analog controller, a minimal control supply, a board-powered
cooling fan output and full protection.
Use case: a **plug-in step-down module in a data-center server rack**. The 72 V input is the only power
source; no auxiliary or bias supply will be provided. The output feeds rack loads with **no back-feed**.
No firmware or programming: all behavior is set by resistors and capacitors.
Treat the report, the LTspice/Q3D results (`sim/ltspice/`) and the SolidWorks physical layout as the
reference design. Copy their topology and current paths, then improve them where the report found weak spots.

## 2. Electrical specification (do not change without asking)
| Parameter | Value |
|---|---|
| Input voltage | 72 V nominal, ±10 % worst case → **64.8–79.2 V**; the line never exceeds 80 V. Single input |
| Output | 24 V, 46 A (23 A per phase), 1.1 kW; rack load, no back-feed |
| Topology | 2-phase interleaved synchronous buck, phases 180° apart, one coupled inductor |
| Switching frequency | 200 kHz per phase |
| Inductor current ripple | < 40 % p-p |
| Output voltage ripple | < 1 % p-p |
| Efficiency target | ≥ 95 % at full load |
| Max junction temperature | 150 °C |
| Freewheel path resistance | Interconnect ≤ 3 % of the FET RDS(on) |
| Fan output | 5 V from the board to the cooling fan (§6) |

## 3. Board outline, stack-up, placement, mechanics
- Outline: ISO/IEC 7810 ID-1, **85.60 × 53.98 mm with 3.18 mm corner radii**, on Edge.Cuts. Thickness is
  **1.6 mm**. Component height is not limited.
- Reference size: the original power module is **1 in × 2 in (25.4 × 50.8 mm)**. Keep the power stage in
  about that footprint, arranged like the simulated layout. Control, protection, the control supply and
  connectors use the rest of the board.
- Fab: **JLCPCB, 4-layer, standard 1.6 mm**. Stay within JLCPCB's current 4-layer capabilities (check
  their present copper-weight options, trace/space, via and stack-up rules). Heavier copper is allowed and
  encouraged if the current or thermal calculation needs it; state the chosen stack-up. Layers:
  L1 = top (controls/inductor side), L2 = solid power-ground plane, L3 = power/signal, L4 = bottom
  (power-stage side). The plane next to the bottom switching loop acts as the return plane/shield from the
  report. Document the IPC-2152 temperature rise for 46 A out and 23 A per phase.
- **Double-sided placement:**
  - **Bottom:** EPC2304 FETs, 1EDN7550 gate drivers, bootstrap parts, gate resistors, and the high-frequency
    input ceramics (same side as the FETs to keep the commutation loop small). The heatsink mounts here.
  - **Top:** TDK coupled inductor, controller, control supply, protection circuitry, bulk capacitors,
    connectors, LEDs.
  - **Minimum package size is 0603** (don't use 0402); change existing 0402 BOM parts to 0603 equivalents.
- **Heatsink:** Alpha Novatech **Z60-12.7B** (60 × 60 mm, 12.7 mm tall, 3 mm base, A6063 black anodized)
  on the bottom over the EPC2304 top-side cooling pads, with a TIM. It is wider than the 53.98 mm board:
  either allow about 3 mm of overhang per side, or propose a smaller heatsink with a revised thermal check.
  Add mounting holes and keep the bottom contact area flat and clear of taller parts.
- Connectors:
  - **High current (DC+, DC−, VOUT+, VOUT−):** bolt-down screw terminals such as Würth REDCUBE. Size for
    46 A out and the input current with margin.
  - **Low current (fan, enable/PGOOD/fault if used):** Molex Micro-Fit, Nano-Fit or Pico/Micro-Lock
    family. The existing J4 (Molex 105313-1206) can be reused or replaced.

## 4. Parts policy and required components
- **Every part must be off-the-shelf, Active (not NRND or obsolete) and in stock on Digi-Key** when it is
  chosen. Also check JLCPCB/LCSC availability for assembly. Use the real values that are sold (e.g. C1–C4
  are 2.2 µF in the BOM because that's the catalog part; update the schematic to match the BOM). Record
  the MPN, Digi-Key PN, LCSC PN (if any), reference designator and stock status for every part. If a
  part is no longer active/in stock, flag it and propose a drop-in replacement. If Digi-Key can't be
  checked automatically (bot verification), say so and ask me to confirm.
- Required parts (BOM: `bom/PCB_BOM.xlsx`; vendor footprints: `kicad/lib/vendor/`, local only):
  - Q3–Q6: EPC2304 eGaN FETs (200 V), two per phase
  - L1: TDK ERUC23-3R2K coupled inductor
  - U1–U4: Infineon 1EDN7550 gate drivers (high side uses bootstrap)
  - D1–D4: SS110HL Schottky (bootstrap)
  - Gate resistors: 2 Ω HS turn-on (R15–R18), 5.6 Ω LS (R13, R14, R19, R20), 4.7 Ω (R9–R12), 51 kΩ (R1–R8)
  - Input decoupling: 4× 2.2 µF 100 V X7T 0805 (C1–C4). Bulk: Chemi-Con EGXF 160 V 110 µF (C5/C6)
  - Gate-drive decoupling: 100 nF (C7–C11, C13), 10 µF (C12, C14)
  - Heatsink: Alpha Novatech Z60-12.7B
  - Fan: Sanyo Denki San Ace 40 9GA0405P6H001 (§6). In stock on Digi-Key, confirmed 2026-10-15
- **Probably removed (confirm with me first):** AT1/AT2 SI86S620BC isolators and the PS1 NME1S0505SC
  isolated module. With an on-board non-isolated controller they don't do anything.
- Reference only: UCC27611 datasheet, FAN3122 app note (links in `docs/datasheets/README.md`).

## 5. Layout requirements (keep the simulated physical design, but improve it)
1. Keep the placement and current-flow logic of the SolidWorks/Q3D layout: input ceramics tight against
   each half-bridge, drivers next to their FETs, the two phases mirror-symmetric.
2. **Commutation loop:** Q3D found 10.8 nH and SPICE showed about 160 V low-side V_DS overshoot, against a
   200 V rating. Target 2–3 nH, with the ceramics right at the FET pads on the bottom and a vertical loop
   over the adjacent return plane. Target overshoot is < 100 V.
3. **Gate loops:** use Kelvin source returns, keep driver-to-gate distance as short as possible, route each
   gate trace over its own return, and give each driver local VDD decoupling.
4. Keep SW1/SW2 small. Keep them away from the controller and its feedback/sense network. Don't put
   sensitive top-side analog parts directly above the switch nodes.
5. Analog ground for the controller connects to power ground at one defined point. Route current-sense
   traces as Kelvin pairs.
6. EMI: the report found CM resonances at 169 MHz and 595.6 MHz. Add a ferrite bead in the return
   center-tap path and extra center-tap decoupling.
7. Use thermal vias under the FET and driver pads and spread copper toward the bottom heatsink.

## 6. Controller, control supply and fan (72 V input only, no programming)
- **Controller:** a standalone analog 2-phase (180° interleaved) synchronous buck controller IC,
  configured only with resistors and capacitors (frequency, soft-start, current limit, compensation,
  UVLO). It provides PWM for both phases (or GaN-suitable gate-drive outputs) with GaN-appropriate dead
  time. Required features: per-phase current sensing (shunt or DCR), current balancing, enable,
  power-good. No MCU, no telemetry; use the fewest parts that work.
- **Controller VIN rating:** the input can reach 79.2 V, so **prefer VIN abs max ≥ 100 V**. An 80 V-rated
  controller is allowed only if its supply pin is **clamped to stay ≤ 75 V in all conditions**,
  including hot-plug ringing. Do this with a series element plus a Zener/TVS on the controller's own
  supply node (about 68–70 V), never a TVS across the whole bus. In that case, input OVP/UVLO sensing
  uses a separate divider from the unclamped bus.
- **Control supply:** one minimal converter is allowed and required (the fan rules out a linear-only
  supply). Use a small, low-part-count buck with **≥ 100 V input** running from 72 V that makes **5 V,
  rated ≥ 1 A**, only for: controller bias (if needed), 1EDN7550 VDD/bootstrap, protection comparators,
  LEDs and the fan. Write out the current budget. The low-side drivers are referenced to power ground;
  the high-side drivers use the bootstrap.
- **Cooling fan:** Sanyo Denki San Ace 40 **9GA0405P6H001**: 40 × 40 × 20 mm, 5 V, 0.35 A (1.75 W),
  11.7 CFM max, 191 Pa max static pressure, 4 wire leads (+, −, tach, PWM). Chosen to push about 5 CFM,
  about 4–4.5 m/s, through the Z60-12.7B fins at about 100 Pa, estimated 0.6–0.7 °C/W. This meets or
  exceeds the report's h ≈ 50 W/m²K assumption. (The report's 6 m/s figure was a flat-plate assumption;
  a true 6 m/s through this heatsink needs ~200 Pa, which isn't practical for a small 5 V fan.)
  - If it ever stops being Active/in stock, substitute a 5 V fan or blower delivering ≥ 5 CFM at ≥ 100 Pa.
  - Fan connector: Molex header with 5 V, GND, tach (to a test point), PWM (tied per the datasheet for
    full speed; confirm the open-pin behavior). Budget 0.35 A running and about 0.7 A at startup.
    Fuse or current-limit the fan output separately so a fan fault can't take down the control rail.
  - Provide a mounting/shroud plan that ducts air through the heatsink fins (crossflow along the 60 mm
    length).

## 7. Protection and safety (required)
| Function | Requirement |
|---|---|
| Hot-plug / inrush | Inrush limiting on plug-in (hot-swap controller rated ≥ 100 V, or pre-charge); damp cable-inductance ringing |
| Reverse polarity | Protection on the 72 V input |
| Input surge | TVS across the input bus: standoff above 79.2 V, clamp below 100 V (ceramic rating); plus fuse or eFuse |
| Controller supply clamp | Only if an 80 V controller is used: ≤ 75 V on its supply pin (§6) |
| Input OVP | Trip at about **82 V** with hysteresis |
| Input UVLO | Turn on about 62 V, turn off about 60 V |
| Overcurrent | Cycle-by-cycle per phase at about 28 A; total output about 55 A (~120 %); **hiccup** auto-retry; covers shoot-through |
| Output OVP | Trip at about 27 V; **latch off** |
| Over-temperature | NTC at the FETs/heatsink; trip at **80 °C** with hysteresis; **latch off** (expected heatsink temperature is ~50 °C with 35 °C rack inlet air) |
| Switch-node clamp | Low-inductance D-S TVS/RC snubber placement option (80–85 V standoff) at each EPC2304 |
| Gate protection | Gate pull-downs; gate voltage held within EPC2304 limits (≤ 6 V) |
| Fan output | Separate fuse or current limit; ESD protection on the connector pins |
| Indicators/test | Power-good and fault LEDs; test points for VIN, VOUT, SW1, SW2, gates, 5 V rail, fan tach, GND |
All protections drive one common fault/disable line. Latched faults clear when input power is cycled.

## 8. Existing KiCad project (starting point)
- Location: `kicad/ECE533_Guide/`. Files: `ECE533_Guide.kicad_pro`, `ECE533_Guide.kicad_sch` (power stage),
  `gate_drive.kicad_sch`, `connectors.kicad_sch`; custom footprints in `ECE533_Mods.pretty/` (currently empty).
- The schematic can be changed or reorganized. Suggested sheets: power stage, gate drive, controller,
  control supply + fan, protection, connectors.
- `ECE533_Guide.kicad_pcb` is currently **empty**. Layout starts from scratch.
- Existing nets: +5V, GND, +5V_iso, GNDPWR, SW1, SW2, PWM_HS1/LS1/HS2/LS2. Simplify and merge the ground
  and 5 V nets when the isolation is removed.

## 9. How to work on this project
- All files must stay compatible with **KiCad 10.0**. Don't edit while `.lck` files show the project is
  open in KiCad; ask me to close it. Git is the backup; don't make timestamped copies in the repo.
- Edit the KiCad files directly (S-expression text). For PCB placement/routing, prefer KiCad's scripting
  API or `kicad-cli` over hand-editing `.kicad_pcb` text. Run ERC/DRC with KiCad 10 after each major step,
  using JLCPCB 4-layer rules (store them as `kicad/ECE533_Guide/ECE533_Guide.kicad_dru`). Fix all errors and
  explain any warnings left in place.
- Before picking a part, check its datasheet (ratings, package ≥ 0603) and confirm it is Active and in
  stock on Digi-Key, plus LCSC where possible.
- Ask before decisions that are hard to undo: removing the isolators, controller IC, control-supply IC,
  stack-up/copper weight, heatsink overhang or replacement, connector part numbers.
- Work in stages and check in after each one: (1) architecture, controller choice and part list,
  (2) schematic + ERC, (3) placement (top/bottom), which I review, (4) routing + DRC, (5) outputs.
- Final deliverables: schematic PDF, routed PCB, updated BOM (.xlsx), JLCPCB-ready Gerbers + drill +
  CPL/BOM for both sides, 3D render, and a short design note covering current/thermal calculations,
  loop-inductance reasoning, protection thresholds, control-supply and fan budget, and open issues.

## 10. Repository and git workflow
- Layout:
  - `kicad/ECE533_Guide/`: the KiCad project
  - `kicad/lib/vendor/`: SamacSys libraries, **git-ignored**, license forbids redistribution
  - `bom/`: BOM (.xlsx, plus a CSV export for diffs)
  - `docs/`: reports, `docs/design/` design notes and calculations, `docs/datasheets/` (links only)
  - `sim/ltspice/`: simulations (vendor models and transient `.raw` are git-ignored)
  - `fab/`: JLCPCB outputs (Stage 5)
- **Never commit** vendor library models, vendor datasheets, vendor SPICE models, the instructor's
  assignment PDF, or `.raw` transient results.
- One branch per stage (`stage-1-architecture`, `stage-2-schematic`, …). Commit after every completed
  step with a clear message, push, and open a PR into `main` at the end of the stage for my review.
  Don't push directly to `main`.
- CI (`.github/workflows/kicad-checks.yml`) runs KiCad 10 ERC/DRC and exports a schematic PDF on every
  push/PR. Check its result before asking for review.
- Update `PROGRESS.md` at the end of every session: stage, what was done, decisions made, open questions.
  Record each significant decision (with the reason) in its Decisions log.
- GitHub issues #1–#5 track the five stages; reference them in commits/PRs (e.g. "Closes #1").
