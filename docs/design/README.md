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

## Decisions needed at the Stage 1 review
- Per-phase ripple: the < 40 % spec isn't met with ERUC23-3R2K (63–70 % at 250 kHz). Relax the spec,
  or change to ERUC23-4R1K at 300 kHz (`power_stage_calcs.md` §2).
- ERUC23-3R2K saturation rating per winding vs the 31 A peak (§7).
- Input OVP: 83.5 V typical with LM5069 tolerance, or a precision 82 V comparator (+1 part).
- PS1: keep NME1S0505SC (1 W) or move to NXE2S0505MC (2 W).
- Stack-up: 2 oz on all four layers with 3313 prepreg (confirm with JLC) vs a 7628 fallback.
- Pass FET 100 V (lower loss) vs 150 V (more surge margin).
- Fuse DC rating confirmation; Digi-Key stock for every part (bot verification blocked automatic checks).
