# Design notes

Stage 1 (architecture, issue #1). Read in this order:

1. [isolation_architecture.md](isolation_architecture.md): HV/LV domains, barrier, block diagram,
   crossing signals, fault logic, power-up
2. [power_stage_calcs.md](power_stage_calcs.md): duty, coupled-inductor ripple, capacitors, losses,
   loop inductance, delays
3. [stackup_ipc2152.md](stackup_ipc2152.md): JLCPCB stack-up, IPC-2152/2221 current capacity, vias
4. [thermal.md](thermal.md): Tj, heatsink pedestal and mounting, fan shroud, NTC
5. [control_supply_fan.md](control_supply_fan.md): +5V_PWR and +5V_ISO budgets, fan output
6. [protection.md](protection.md): thresholds, dividers, fault line, EMI items
7. [parts_stage1.md](parts_stage1.md): proposed parts with status/stock, removed parts, rejected candidates

## Stage 1 review outcome
- **Kept:** ERUC23-3R2K inductor and EPC2304 FETs, because the simulations depend on them. Per-phase
  ripple is accepted at about 53–70 % (output ripple < 10 %).
- **Input OVP:** precise 82 V with a TLV3012 comparator (U22).
- **Stack-up:** 4 × 2 oz, JLC04161H-3313, accepted.
- **Pass FET:** 100 V (IPT015N10N5).
- **Digi-Key stock:** handled by the user.

Still open:
- PS1: keep NME1S0505SC (1 W) or move to NXE2S0505MC (2 W).
- ERUC23-3R2K saturation definition per winding vs the 31 A peak (TDK datasheet, Stage 2 check).
- Fuse 0456025.ER DC voltage rating (Littelfuse datasheet, Stage 2 check).
