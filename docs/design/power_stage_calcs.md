# Stage 1 — Power stage calculations

Operating points: VOUT = 24 V, IOUT = 46 A (23 A/phase), **fsw = 250 kHz per phase** (raised from
200 kHz, the LTC3861 minimum), VIN = 64.8 / 72 / 79.2 V. Arithmetic was checked in PowerShell; formulas
are shown so they can be re-run.

## 1. Duty cycle

D = VOUT / VIN: **0.370 / 0.333 / 0.303**. D < 0.5 everywhere, so the two phases' on-times never overlap.

## 2. Coupled-inductor ripple (L1 = TDK ERUC23-3R2K)

Model values come from the TDK LTspice model `ERUC.sub` used in the report (kept local, not
committed): self inductance **L = 5.84 µH**, coupling **k = 0.714** (M = 4.17 µH), DCR
**1.84 mΩ** per winding. Leakage L − M = 1.67 µH; L + M = 10.0 µH. The phases are inversely coupled.

For phase 1 while Q3 is on and phase 2 freewheels (v1 = VIN − VOUT, v2 = −VOUT):

  di1/dt = (L·v1 − M·VOUT) / (L² − M²),  ΔI_ph = (di1/dt)·D·T

Total output ripple (both phases): ΔI_out = (VIN − 2·VOUT)/(L + M) · D·T

| VIN | ΔI per phase (p-p) | % of 23 A | I_peak / I_valley | ΔI output (p-p, at 500 kHz) | I_rms per phase |
|---|---|---|---|---|---|
| 64.8 V | 12.3 A | 53 % | 29.1 / 16.9 A | 2.5 A | 23.3 A |
| 72 V | 14.4 A | 63 % | 30.2 / 15.8 A | 3.2 A | 23.4 A |
| 79.2 V | 16.1 A | 70 % | 31.1 / 14.9 A | 3.8 A | 23.5 A |

**Finding: the < 40 % per-phase ripple spec isn't met with ERUC23-3R2K**, at 250 kHz or at the
report's 200 kHz (78 % at 72 V). Output ripple, about 7 % of 46 A, is small because of the interleaving.
Options (same model method):

| Inductor | 250 kHz | 300 kHz | 400 kHz |
|---|---|---|---|
| ERUC23-3R2K (5.84 µH, k 0.714) | 63–70 % | 52–58 % | **39–44 %** |
| ERUC23-4R1K (7.75 µH, k 0.728, DCR 1.87 mΩ) | 49–55 % | **40–45 %** | 30–34 % |

→ **Open decision for review.** Recommendation: keep ERUC23-3R2K at 250 kHz and relax the ripple spec
to "< 75 % per phase, < 10 % at the output", or move to ERUC23-4R1K at 300 kHz (check its saturation
rating against the 31 A peak). Everything below uses ERUC23-3R2K at 250 kHz.

## 3. Input capacitors

Input RMS ripple current (two non-overlapping 23 A pulses per period):

  I_Cin,rms = √(2D·I_ph² − (2D·I_ph)²) = **10.1 / 10.8 / 11.2 A**

Charge drawn from the HF ceramics during one high-side on-time at 72 V:
(23 − 16.1 A) × 1.33 µs ≈ 9.2 µC. C1–C4 (4 × GRM21BD72A225KE01L, 2.2 µF 100 V X7T 0805) keep about
40 % of their value at 72 V DC bias, roughly 3.5 µF together, giving about 2.6 V p-p on the HF caps.

Recommendation (an improvement over the report): **2 × 2.2 µF per half-bridge right at the FET pads**
(8 total, C1–C4 plus C15–C18). That halves the HF ripple and the current per capacitor (about 1.4 A rms
each), and lowers the loop inductance (parallel ESL). Bulk: Chemi-Con EGXF 160 V 110 µF; the BOM has
5, which is reconciled in Stage 2. They carry the low-frequency share and damp cable resonance with
their ESR.

## 4. Output capacitors and output ripple

ΔI_out = 3.2 A p-p at 500 kHz (2 × fsw). For ΔV < 1 % (240 mV): C > ΔI/(8·f·ΔV) = 3.3 µF and
ESR < 75 mΩ. Proposal: 6 × 10 µF 50 V X7R 1210 ceramics (≥ 25 µF effective at 24 V) plus
2 × 100 µF 35 V polymer for load steps. Expected ripple is well under 50 mV p-p. The report's 440 µF
(C6) gets reconciled in Stage 2.

## 5. Loss budget at full load (72 V)

| Loss | Basis | W |
|---|---|---|
| HS conduction ×2 | D·I_rms²·RDS(on,hot); EPC2304 3.2 mΩ × 1.4 | 1.64 |
| LS conduction ×2 | (1−D)·I_rms²·RDS(on,hot) | 3.26 |
| HS switching ×2 | ½·V·I·t: turn-on at the valley (15.8 A, 3 ns), turn-off at the peak (30.2 A, 2 ns) | 1.94 |
| Coss/Qoss ×2 | Estimate, about 2 µJ/cycle at 72 V, to confirm in SPICE | 1.0 |
| Dead-time reverse conduction ×2 | 2 V × 23 A × 20 ns × 2 edges × f | 0.92 |
| Inductor DCR | 2 × 23.4² × 1.84 mΩ | 2.0 |
| Inductor core | Estimate (not in the model) | 1.5 |
| Phase shunts | 2 × 23.4² × 0.5 mΩ | 0.55 |
| Input path | RS1 2 mΩ, Q1 + Q2 (IPT015N10N5, hot), F1, at 16.1 A | 2.3 |
| PCB copper | `stackup_ipc2152.md` | 0.6 |
| Control supply incl. fan | `control_supply_fan.md` | 4.1 |
| **Total** | | **≈ 19.8 W** |

η ≈ 1100 / (1100 + 19.8) = **98.2 %** (≥ 95 % target; the margin covers the estimated terms).
Per-FET: HS about 2.3 W, LS about 2.1 W. The report had HS 2.0 W and LS 3.4 W at 200 kHz with a
100 ns dead time. The LS drops because the **dead time is set to about 20 ns** with the Si8274 R_DT
(DT = 2.02·R_DT[kΩ] + 7.77 ns → R_DT ≈ 6.04 kΩ), to be checked against Miller turn-on margin in SPICE
(Stage 2).

## 6. Commutation loop inductance and overshoot

Baseline (report): Q3D loop 10.8 nH; SPICE showed the LS V_DS peaking at about 160 V (≈ 88 V over a
72 V bus), against a 200 V rating.

Proposed loop: HF caps on the **bottom**, at the FET pads (same side as the FETs). The return runs on
**L3 directly above, 0.1 mm away** (JLC04161H-3313 prepreg, `stackup_ipc2152.md`), and the loop is
closed by a row of vias under each cap.

| Contribution (per half-bridge) | Estimate |
|---|---|
| Lateral loop over L3: μ0·h·ℓ/w with h ≈ 0.17 mm (prepreg + copper), ℓ ≈ 4 mm, w ≈ 5 mm | 0.17 nH |
| Vias, 6–8 in parallel, 0.17 mm span | 0.1 nH |
| 2 × 0805 caps in parallel (≈ 0.45 nH each) | 0.23 nH |
| 2 × EPC2304 package | about 0.3 nH |
| Margin for spreading and the cap-to-FET gap | 0.5–1 nH |
| **Total** | **≈ 1.3–1.8 nH** (target 2–3 nH ✓) |

Overshoot scales roughly with L_loop at the same di/dt: 88 V × (1.8/10.8) ≈ **15 V** → LS peak about
90–95 V at 79.2 V input. That meets the < 100 V overshoot target with margin and leaves 105 V under the
200 V rating. A D-S RC snubber footprint (DNP) at each FET stays as a tuning option.

## 7. Delays through the barrier (budget)

| Path | Delay | Effect |
|---|---|---|
| PWM → gate (Si8274) | ≤ 60 ns + dead time | Equal on both phases; doesn't matter at 4 µs period |
| I1/I2 → LTC3861 (AMC3301) | 334 kHz BW, a few µs group delay | Used for current sharing and the 128-cycle average OC only |
| VOUT → LTC3861 (AMC3330) | Same | Limits the loop crossover to about 10–15 kHz (fsw/20 or lower); fine for a rack bus. Phase margin at crossover is checked in Stage 2 |
| INA301 → AT1 → latch → PWM | < 1 µs + about 30 ns | At 13.3 A/µs (79.2 V) the current overshoots the 36 A threshold by about 13 A → about 49 A worst case, within the EPC2304 pulse rating. **Check ERUC23-3R2K saturation per winding**: distributors list 57.5 A with windings in parallel and 28.75 A in series. Normal operation already peaks at 31 A per winding, so the TDK datasheet definition must be confirmed in Stage 2. If 28.75 A is a per-winding limit, the threshold and the inductor choice change. |
| CMTI | Si8274 200 kV/µs, AMC 85 kV/µs | SW dv/dt is about 72 V/3 ns = 24 kV/µs |
