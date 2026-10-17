# Stage 1 — Control supply, isolated supply and fan

Two rails, both derived from the 72 V input (there is no auxiliary supply):

```
VIN (after Q2) ─► U11 LM5012 (100 V, 2.5 A buck) ─► +5V_PWR 5.2 V (PGND) ─┬─► fan (via U21 TPS2553)
                                                                          ├─► Si8274 output sides, bootstrap
                                                                          ├─► INA301, TLV3012 (OTP), AT1/AT2 side 1, VOM1271 LED
                                                                          └─► PS1 isolated 5 V ─► +5V_ISO (GND_ISO): LV domain
```

## 1. +5V_ISO budget (LV control domain, 5.0 V)

| Load | Typ (mA) | Max (mA) | Source |
|---|---|---|---|
| LTC3861 VCC | 30 | 30 | Datasheet, normal operation (to refine) |
| AMC3301 ×2, low side incl. built-in isolated DC-DC | 55 | 80 | Datasheet IDD 27.5 typ / 40 max each |
| AMC3330 | 28.5 | 41 | Datasheet IDD |
| Si8274 ×2 input side (VDDI) | 6 | 10 | Estimate |
| SI86S620BC ×2, side 2 | 4 | 6 | Estimate |
| Logic (74LVC ×5), TLV3012 (OVP), pull-ups | 2 | 3 | |
| PGOOD + FAULT LEDs (0603, 2 mA) | 4 | 4 | |
| J4 outputs (open-drain to host) | 0 | 2 | |
| **Total** | **≈ 130 mA (0.65 W)** | **≈ 176 mA (0.88 W)** | |

- **PS1 = NME1S0505SC (1 W, 200 mA, 1 kVDC) — kept (Stage 1 review).** Load is 65 % typical / 88 %
  worst case. It's unregulated, so in Stage 2: (a) check its output voltage at 130–176 mA against the
  AMC3330's 4.5 V minimum and the LTC3861's 5.5 V maximum, using the datasheet load-regulation curve;
  (b) keep LV loads lean (2 mA LEDs, no extra loads on +5V_ISO).
  Fallback if the margin is too thin: Murata NXE2S0505MC (2 W, 400 mA, 3 kVDC, SMD).
- Input power drawn from +5V_PWR: 0.88 W / 0.72 ≈ 1.2 W → **0.24 A at 5.2 V** (worst case).

## 2. +5V_PWR budget (HV domain, 5.2 V)

| Load | Run (A) | Start-up peak (A) |
|---|---|---|
| Fan 9GA0405P6H001 | 0.35 | 0.70 |
| PS1 input (§1, worst case) | 0.24 | 0.24 |
| Gate drive: 4 × Qg·f = 4 × 6.84 nC × 250 kHz | 0.007 | 0.007 |
| Si8274 output-side quiescent (4 channels) | 0.008 | 0.008 |
| INA301 ×2, TLV3012, AT1/AT2 side 1 | 0.008 | 0.008 |
| VOM1271 LED (reverse-FET gate drive) | 0.010 | 0.010 |
| **Total** | **≈ 0.62 A (3.3 W)** | **≈ 0.97 A** |

**U11 = TI LM5012** (6–100 V in, 2.5 A, COT non-synchronous, SOIC-8 PowerPAD; Active; pin-compatible
with LM5164 1 A synchronous). The LM5164 would run at 97 % of its rating during fan start, so it was
rejected. LM5012 has 2.6× margin at the 0.97 A peak. It needs a 100 V / 3 A Schottky and an inductor
of about 22–33 µH (Stage 2). Set VOUT to 5.2 V: the low-side gate gets 5.2 V and the high-side gets
5.2 V − V_F ≈ 4.8 V, both within EPC2304 limits (≤ 6 V). The fan, Si8274 (VDDx ≥ 4.2 V), INA301 and
PS1 (4.5–5.5 V) all accept 5.2 V.
Efficiency at 72 V → 5.2 V is about 82 % → input ≈ 4.0 W (included in the loss budget).

## 3. Fan output

- **U21 TI TPS2553DBVR** (2.5–6.5 V, adjustable limit 75 mA–1.7 A, 85 mΩ, constant-current limit with
  FAULT flag). Limit set at **≈ 1.0 A** (R_ILIM per the datasheet equation, Stage 2): above the 0.7 A
  start-up current, and low enough that a stalled or shorted fan can't pull +5V_PWR down. The LM5012
  still has 1.5 A of headroom. The `-1` latching variant is not used; the fan restarts on its own.
- Connector **J5: Molex Micro-Fit 3.0 43650-0400** (4 pins, right angle): 5 V, GND (PGND), TACH, PWM.
- **PWM pin:** left open (with a footprint for a pull-up to 5.2 V, DNP). Sanyo Denki's 9GA
  documentation says an open control terminal runs at 100 % duty (full speed). To confirm on the
  9GA0405P6H001 datasheet in Stage 2.
- **TACH:** open collector (Sanyo spec: 30 V, 5 mA max, 2 pulses/rev). 10 kΩ pull-up to 5.2 V →
  test point TP14 (HV side). It doesn't cross the barrier: AT2 channel B carries the hot-swap
  bus-good flag instead (Stage 2).
- **EN:** U21 EN is pulled up to +5V_PWR (R93), so the fan runs whenever +5V_PWR is up.
- **ESD:** TVS array on the fan pins (TI TPD4E05U06 class, Stage 2).
- Airflow and shroud: `thermal.md` §5.
