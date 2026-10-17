# Stage 1 — Protection thresholds and parts

All values are nominal; tolerances are shown where they matter. Final resistor values are set in
Stage 2 and simulated.

## 1. Input chain (HV domain)

`J1 DC+ → F1 → D6 (TVS to DC−) → Q2 (reverse) → U11 tap → RS1 → Q1 (LM5069 pass) → VIN bus`

| Function | Part | Setting |
|---|---|---|
| Fuse | **F1 Littelfuse 0456025.ER** (NANO2, 25 A, SMD; LCSC lists 125 VDC, 500 A interrupt) | Steady input 16.1 A (72 V) / 17.9 A (64.8 V) = 64–72 % of rating. **To confirm:** DC rating and derating on the Littelfuse datasheet. One distributor lists the 456 series 30 A as 65 VDC. If 25 A isn't rated ≥ 80 VDC, pick another series. |
| Surge TVS | **D6 SMDJ85CA** (bidirectional, Littelfuse; 3000 W) | Standoff 85 V > 79.2 V. V_BR 94.4 V min; V_C 137 V at full I_PP. **Bidirectional** so it doesn't short a reversed supply. |
| Reverse polarity | **Q2 Infineon IPT015N10N5** (100 V, 1.5 mΩ, TOLL) + **U13 Vishay VOM1271** photovoltaic gate driver | The LED is powered from +5V_PWR, which only exists with correct polarity. Reversed, Q2 stays off and its body diode blocks up to 100 V. No IC sees a negative voltage. (LTC4364 and TPS4811 were rejected because their pins are rated only −40 V / −30 V.) |
| Hot-swap / inrush | **U12 TI LM5069MM-2** (9–80 V, 100 V abs, power limiting, auto-retry) + **Q1 IPT015N10N5** | See below |
| Current sense | **RS1 2 mΩ** (Bourns CSS2H-2512R-2L00F, or 2 × 1 mΩ CSS2H-2512R-1L00F in series) | 0.52 W at 16.1 A |

### LM5069 settings
- **UVLO** (R1 top / R2 bottom, 21 µA hysteresis current):
  R1 = ΔV/21 µA = 2 V/21 µA → **95.3 kΩ**; R2 = 2.5·R1/(V_UVL − 2.5) → **4.12 kΩ**.
  Result: **on 62.3 V / off 60.3 V** (threshold 2.45–2.55 V, hysteresis 12–30 µA → on 61.5–63.2 V).
- **OVLO: precise 82 V comparator (decided at the Stage 1 review).** The LM5069's own OVLO threshold
  (2.4–2.6 V) would give a band of 78.4–84.9 V around a nominal 82 V, which could trip at the 79.2 V
  maximum line. Instead, **U22 TLV3012** (HV side, 1.242 V internal reference, push-pull output) senses
  a separate divider from the unclamped bus and drives the LM5069 OVLO pin through 10 kΩ, with
  10 kΩ to PGND so OVLO defaults low.
  - Divider: R_top **649 kΩ** (0.1 %) / R_bot **10.0 kΩ** (0.1 %) → trip = 1.242 × (1 + 64.9) =
    **81.9 V**.
  - Hysteresis about 2 V: positive feedback R_f ≈ R_top × 5.2 V / 2 V ≈ **1.69 MΩ** → release about
    80 V (exact values set in Stage 2).
  - Tolerance (about ±1.5 % from the reference and 0.1 % resistors): **≈ 80.7–83.1 V**, above the
    79.2 V maximum line.
  - Fallback: the LM5069 divider alone (R3 = 95.3 kΩ, R4 = 2.94 kΩ → 83.5 V typ, 80.2–86.9 V).
- **Current limit** V_CL = 55 mV (48.5–61.5) / 2 mΩ → **27.5 A** (24.3–30.8 A), above the 17.9 A
  maximum load current. **Circuit breaker** V_CB = 105 mV → **53 A** (fast gate pull-down): covers a
  power-stage short or shoot-through.
- **Power limit and timer:** R_PWR and C_TIMER are sized in Stage 2 against the IPT015N10N5 SOA. The
  inrush charges C_bus (550 µF bulk + ceramics) to 72 V in about 20–40 ms. The -2 version restarts at
  0.5 % duty.
- **VIN pin:** C71 1 µF/100 V bypass at the pin, taken from the RS1 Kelvin tap. *Changed in Stage 2:*
  no series resistor, because the LM5069 supply current (1.3 mA) through 10 Ω would add a 13 mV error
  to the 55 mV current-limit sense. Spikes above the 100 V pin rating are an open coordination item
  (TVS clamp, see below). The earlier plan read: 10 Ω + 1 µF RC, so TVS clamp spikes above 100 V are
  filtered before they reach the pin.

### TVS clamp vs 100 V parts (open issue)
"Clamp below 100 V" holds only at low surge currents: the SMDJ85CA is about 95–100 V near 1 A and
137 V at its full rated I_PP. Downstream, 100 V items are C1–C4/C15–C18 (100 V X7T MLCC), the
LM5069 pin (RC-filtered), Q1/Q2 (100 V, avalanche-rated) and the LM5012 (100 V). Mitigations: bulk electrolytic ESR damping (C5, 160 V),
the TVS at the connector, and the spec statement that the line never exceeds 80 V. **Decided at the
Stage 1 review: keep the 100 V pass FET (IPT015N10N5).** The 150 V option (IPT059N15N3, +1.3 W loss)
was not needed.

## 2. Converter protections

| Function | Where | Implementation | Value |
|---|---|---|---|
| Input UVLO | HV | LM5069 UVLO | On 62.3 V / off 60.3 V |
| Input OVP | HV | U22 TLV3012 → LM5069 OVLO | 81.9 V trip / about 80 V release (see above) |
| **Cycle-by-cycle OCP, per phase** | HV → LV | INA301A3 on RS2/RS3 (0.5 mΩ, gain 100, 0–36 V CM, < 1 µs) → AT1 → cycle latch + AND | **36 A instantaneous**, about 28 A average plus half the 14–16 A ripple. A 28 A peak threshold would trip at full load (peak 31 A). INA301 output at 36 A = 1.80 V; R_LIMIT per the datasheet (Stage 2) |
| Average OCP + hiccup | LV | LTC3861 ISNS (AMC3301 out, attenuated ×0.261 → 30 mV at 28 A), 128-cycle counter → three-state, 32 768-cycle wait | **28 A per phase (≈ 56 A total, about 120 %)**, R_ILIM = (18.5 × 30 mV + 0.5 V)/20 µA = **52.3 kΩ**; hiccup off-time 131 ms, auto-retry |
| Output OVP (latch) | LV | LTC3861 VSNSOUT (0.6 V at 24 V) → TLV3012 → fault latch | **27.0 V** (VSNSOUT = 0.675 V) |
| OTP (latch) | HV → LV | NTC RT1 + TLV3012 (U14) → AT2 → fault latch | **80 °C**, about 10 °C hysteresis (`thermal.md` §3) |
| Shoot-through | HV | Si8274 overlap protection + 20 ns dead time; LM5069 53 A breaker; F1 | — |
| Gate protection | HV | 10 kΩ gate-source pull-downs at each EPC2304; LS gate 5.2 V; HS bootstrap clamped by a **5.1 V Zener** (BZT52C5V1, D3/D4) after a 4.7 Ω series resistor | VGS ≤ 6 V (EPC2304). The Zener stops bootstrap over-charge when SW goes negative during dead time (GaN V_SD about 2–3 V) |
| Switch-node clamp | HV | DNP footprints per FET: RC snubber (0805/1206) and an SMBJ85A D-S TVS option | Fit only if measured overshoot calls for it |

Notes:
- The LTC3861 also has its own output OV (VFB > 645 mV ≈ 25.8 V) and UV (540 mV) PGOOD window
  (±10 %). Its OV acts before the 27 V latch. That's harmless; the latch is the backstop.
- **Latched faults clear only when input power is cycled.** The fault latch is a 74LVC1G74 with an RC
  power-on reset on +5V_ISO, and +5V_ISO collapses with VIN.

## 3. Common fault/disable line

`RUN_OK` (LV domain, diode wired-AND, 100 kΩ pull-up to +5V_ISO) is pulled low by the fault latch
(OVP, OTP) through D15, by the hot-swap bus-not-good flag (AT2 B2) through D16, and by J4 EN low
(host) through R88. `RUN_OK` drives LTC3861 RUN1/RUN2. RUN low three-states the PWM outputs and
drops PWMEN1/2, which drive the Si8274 ENABLE pins, so both FETs of each phase turn off. The
cycle-by-cycle OCP acts per cycle and doesn't pull `RUN_OK`. Sustained OCP goes to the LTC3861 hiccup.

## 4. Indicators and test points

- LEDs (LV domain, 0603): **PGOOD** (green, LTC3861 PGOOD1) and **FAULT** (red, fault latch Q).
- Test points: VIN, VOUT, SW1, SW2, the 4 gates (with Kelvin source pads), +5V_PWR, +5V_ISO, TACH,
  PGND, GND_ISO. HV and LV test points are grouped on opposite sides of the barrier and labelled.

## 5. EMI items (from the report's 169 MHz / 595.6 MHz CM resonances)

The report's shield/return plane ties to the **center tap of the input decoupling network** (a
capacitor pair from VIN to CT and from CT to PGND). Proposal:
- Center-tap pair: 2 × 1 nF + 2 × 10 nF, 100 V C0G/X7R 0603, at each half-bridge.
- **FB1 ferrite bead** (Murata BLM18KG601SN1 class, 0603) in the shield/heatsink-to-center-tap link,
  sized for its impedance near 169 MHz and 600 MHz. It carries only displacement current, so no high-current bead is needed.
- Heatsink: connected to the center-tap node through FB1 (DNP 0 Ω option to PGND), or left floating.
  Decide during bring-up.
