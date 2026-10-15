# Stage 1 — Thermal and mechanical (heatsink, fan, NTC)

## 1. Heat into the heatsink

FET losses at full load, 72 V, 250 kHz (`power_stage_calcs.md` §5): HS ≈ 2.3 W ×2, LS ≈ 2.1 W ×2 →
**P_FET ≈ 8.8 W**, all extracted through the EPC2304 top-side cooling into the Z60-12.7B on the bottom.
The inductor (3.5 W), shunts and input path (≈ 2.9 W) are on the top side or spread in copper; they
cool by board conduction and convection, not through the heatsink.

## 2. Junction temperature

| Item | Value | Source |
|---|---|---|
| Rack inlet air | 35 °C | Spec |
| Heatsink to air, Z60-12.7B with the 9GA0405P6H001 fan (about 5 CFM, about 100 Pa) | 0.6–0.7 °C/W | CLAUDE.md §6 estimate |
| Heatsink rise: 8.8 W × 0.7 | 6.2 °C → **T_hs ≈ 41 °C** | (the CLAUDE.md 50 °C figure is conservative) |
| Rθ(j-c, top) EPC2304 | 0.2 °C/W | Report assumption |
| Pedestal (copper/aluminium spreader, §4) per FET share | about 0.3 °C/W | 2 mm Cu over the FET area |
| TIM, **electrically insulating** gap pad 0.25 mm, 5 W/mK, over 3 × 5 mm | 3.3 °C/W | t/(k·A) |
| **Tj (hottest, HS 2.3 W)** | 41 + 2.3 × (0.2 + 0.3 + 3.3) ≈ **50 °C** | ≤ 150 °C ✓ (100 °C margin) |

Insulating TIM is required because the HS FETs (SW-referenced) and LS FETs share one heatsink. Even
with a poor 1 mm pad (about 13 °C/W), Tj ≈ 73 °C.

**Fan failure:** natural convection on the Z60-12.7B is roughly 3–4 °C/W → T_hs ≈ 35 + 8.8 × 3.5
≈ 66 °C, still below the 80 °C OTP. OTP trips if airflow is also blocked or inlet air is hot. That's
the intended backstop.

## 3. NTC / over-temperature

- RT1: Murata NCP18XH103F03RB (0603, 10 kΩ, B = 3380 K), on the bottom between the two LS FETs, tied
  to PGND copper with vias so it tracks the FET/heatsink temperature (within a few °C at 8.8 W).
- R(80 °C) = 1.711 kΩ, R(70 °C) = 2.261 kΩ. With the TLV3012 internal 1.242 V reference and the NTC
  to PGND from +5V_PWR (5.2 V): R_top = 1.711 k × (5.2/1.242 − 1) = **5.45 kΩ (5.49 kΩ E96)**.
  Hysteresis about 10 °C via positive feedback (Stage 2), even though the LV latch holds the fault anyway.

## 4. Heatsink mounting and overhang (decision: keep Z60-12.7B, about 3 mm overhang)

- The 60 × 60 mm heatsink sits on the bottom over the power stage. It overhangs **3.0 mm per side**
  across the 53.98 mm width and covers 60 of the 85.6 mm length. Fins run **along the board's long
  axis** for crossflow.
- **Flat contact and part height:** EPC2304 (top-side cooled) are the lowest parts on the bottom.
  0603/0805 caps, SOIC-16 drivers (1.75 mm) and SMA diodes are taller, so a flat base would rest on
  them. Proposal: a **machined Al/Cu pedestal, about 2.5 mm, on the heatsink base** that touches only
  the four FETs (through the insulating TIM). That leaves ≥ 2.5 mm clearance for every other bottom
  part under the heatsink. Alternative: no pedestal, and only parts no taller than the FETs under the
  heatsink footprint, which isn't practical with the drivers and caps nearby.
- **Mounting:** 4 × M3 plated holes at the heatsink corners, inside the board outline (y = ±24 mm from
  the centreline). M3 × 0.5 tapped into the 3 mm base, with spring-loaded or shoulder screws so the TIM
  gets a controlled 20–40 psi. Keep-out rings of 7 mm on L1/L4 around each hole. Holes connect to
  nothing, or to the shield/center-tap node through the ferrite (`protection.md` §6).

## 5. Fan and shroud

- Sanyo Denki 9GA0405P6H001 (40 × 40 × 20 mm, 5 V, 0.35 A) blows **along the 60 mm fin length**.
- Shroud: a simple 3D-printed (PC/PA12) duct, 40 × 40 mm to the fin cross-section (60 mm wide ×
  about 9.7 mm fin height), length ≥ 15 mm for flow straightening. It clips onto the heatsink fins and
  fully closes the open fin side (bottom cover), so all air goes through the channels. Air exits at the
  far end of the board. The duct outline goes in the Stage 3 mechanical drawing.
- Duct pressure drop at about 5 CFM is about 100 Pa, within the fan's 191 Pa maximum static pressure.
