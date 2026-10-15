# Stage 1 — Stack-up, copper and current capacity

## 1. JLCPCB 4-layer capability (checked 2026-10-15, jlcpcb.com capabilities and impedance pages)

- Outer copper 1 or 2 oz; inner copper 0.5 / 1 / 2 oz; 1.6 mm standard thickness.
- 2 oz outer: min trace/space 0.15/0.15 mm; 1 oz outer: 0.09/0.09 mm.
- Vias: min 0.15 mm drill / 0.25 mm pad; preferred 0.2 mm or larger. PTH annular ring 0.254 mm or more
  at 2 oz. Inner via-to-copper 0.2 mm, inner PTH-to-copper 0.3 mm. Via-in-pad (epoxy-filled and
  capped) available for 0.15–0.55 mm vias at extra cost on 4-layer boards.
- Board edge to copper 0.2 mm (routed).
- 4-layer 1.6 mm stack-ups listed: JLC04161H-7628 (prepreg 0.2104 mm, core 1.065 mm) and
  **JLC04161H-3313 (prepreg 0.0994 mm, core 1.265 mm)**, among others. The impedance page lists layer
  thicknesses for 1 oz outer / 0.5 oz inner; JLC adjusts the build when heavier copper is ordered.

## 2. Proposed stack-up (decision for review)

| Layer | Copper | Use |
|---|---|---|
| L1 top | **2 oz (70 µm)** | Coupled inductor, controller/LV domain, bulk caps, terminals, VOUT and VIN pours |
| Prepreg 3313 ≈ 0.1 mm | | |
| L2 | **2 oz** | Solid `PGND` plane under the power stage; `GND_ISO` island under the controls, split along the barrier |
| Core ≈ 1.2 mm (adjusted by JLC so the total is 1.6 mm) | | |
| L3 | **2 oz** | Power layer: `VIN` / `PGND` pours directly above the bottom commutation loops (the return plane / shield from the report); SW and VOUT current sharing; a few signals |
| Prepreg 3313 ≈ 0.1 mm | | |
| L4 bottom | **2 oz** | EPC2304, Si8274 drivers, bootstrap, gate resistors, HF input ceramics; heatsink side |

Why: the **thin outer prepreg** puts the bottom loop's return (L3) about 0.1 mm above the loop, which
gives about 0.17 nH lateral loop inductance (`power_stage_calcs.md` §6). 2 oz on every layer handles
46 A on a credit-card board. **To confirm when ordering:** that JLC builds 2 oz inner copper with 3313
prepreg. If not, the fallback is JLC04161H-7628 (0.21 mm prepreg, about +0.2 nH loop) or 1 oz inner
with wider pours.

## 3. Current capacity (IPC-2221B / IPC-2152)

IPC-2221B external-trace formula, I = 0.048·ΔT^0.44·A^0.725 (A in mil²). This is close to the IPC-2152
baseline chart (1.6 mm FR-4, still air, no plane) and conservative here, because IPC-2152 credits
adjacent copper planes and the heatsink airflow with a lower temperature rise.

| Path | Current | Copper | ΔT (estimate) |
|---|---|---|---|
| Single 2 oz trace for 23 A at ΔT 20 °C | 23 A | 7.5 mm wide (808 mil²) | 20 °C (reference) |
| Single 2 oz trace for 46 A at ΔT 20 °C | 46 A | 19.4 mm wide | 20 °C (reference) |
| **Phase path** (SW → inductor, inductor → shunt): ≥ 10 mm on 2 layers | 23 A (11.5 A/layer) | 2 × 10 mm × 2 oz | **≈ 2.5 °C** |
| **VOUT bus** to the J2 terminals: ≥ 20 mm on L1 + L4 (+ L3) | 46 A | 2–3 × 20 mm × 2 oz | **≈ 3.9 °C** (2 layers) / 1.6 °C (3 layers) |
| **VIN bus**: ≥ 8 mm on 2 layers | 17.9 A max | 2 × 8 mm × 2 oz | ≈ 2.1 °C |

All are far below the usual 10–20 °C allowance. Width is set by resistance and loop inductance, not
by heating.

### Resistance and copper loss
Sheet resistance of 2 oz copper: **0.246 mΩ/sq** (25 °C).
- VOUT path, about 30 mm × 20 mm on 2 layers: 0.185 mΩ → 0.39 W at 46 A.
- VIN path, about 30 mm × 10 mm on 2 layers: 0.37 mΩ → 0.10 W at 16 A.
- Phase paths: about 0.1 W.
- Total PCB copper ≈ 0.6 W.

### Freewheel path ≤ 3 % of RDS(on)
3 % × 3.2 mΩ = **0.096 mΩ**. Example: SW copper about 6 mm long × 10 mm wide on L3 + L4 in parallel
is 0.074 mΩ. Adding 30 vias to the top-side inductor (0.05 mΩ) gives **0.124 mΩ, which misses the
limit**. Meeting it takes SW copper ≤ 4 mm long and **≥ 50 vias** (filled or via-in-pad under the
inductor pad, or a dense ring around it): 0.049 + 0.03 ≈ 0.08 mΩ. It's a placement constraint for
Stage 3.

### Via arrays
0.3 mm drill, about 20 µm plating: 1.46 mΩ per via (1.6 mm). Rated about 0.8 A per via at ΔT 10 °C
(internal-trace rule, conservative).
- SW → top-side inductor pad, per phase: **≥ 50 vias**. Current needs ≥ 30 (23 A / 0.8 A); the
  3 % resistance limit needs about 50.
- VOUT and VIN transitions: ≥ 30 and ≥ 24 vias.
- Thermal vias under each EPC2304 and driver: as many as the pads allow, tied to L3/L2 copper.
