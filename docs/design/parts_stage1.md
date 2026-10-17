# Stage 1 — Proposed part list

> **Superseded in Stage 2** by `bom/PCB_BOM.xlsx` / `bom/PCB_BOM.csv`, which are generated from the
> schematic. Some reference designators changed when the schematic was drawn; see
> `schematic_stage2.md` §3. This file stays as the record of the Stage 1 selection and the rejected
> candidates.

Checked **2026-10-15**.
- **Digi-Key:** stock and Digi-Key PNs are handled by the user (Stage 1 review). Automatic checks
  were blocked by bot verification. Lifecycle status below comes from the manufacturer pages (TI,
  Skyworks, Würth) or the datasheet.
- **LCSC:** stock read from lcsc.com search results on the date above. "0" means LCSC lists the part
  but has none in stock (consign or buy from Digi-Key for JLC assembly).
- Passives (R/C values, 0603 minimum) are finalised in Stage 2. Only the critical ones are listed here.

## Power stage (HV, bottom unless noted)

| RefDes | Function | MPN | Mfr status | LCSC PN / stock | Notes |
|---|---|---|---|---|---|
| Q3–Q6 | 200 V eGaN FET | EPC2304ENGRT | Active (EPC) | C6549215 / 0 | Required part; source from Digi-Key |
| L1 (top) | Coupled inductor | TDK ERUC23-3R2K | Active | not found | Required part; Digi-Key. **Ripple/saturation issues**: `power_stage_calcs.md` §2, §7 |
| C1–C4 (+C15–C18 proposed) | HF input 2.2 µF 100 V X7T 0805 | Murata GRM21BD72A225KE01L | Active | C2981733 / 56,790 | 2 per half-bridge proposed (8 total) |
| C5 (×5) (top) | Bulk 110 µF 160 V | Chemi-Con EGXF161ELL111MK25S | Active | C1598290 / 0 | Count reconciled in Stage 2 |
| U1, U2 | Isolated half-bridge GaN driver, PWM in, dead time, 3 V UVLO, 2.5 kVrms | Skyworks **Si8274GB1-IS1** | Active (ordering guide, Jan 2026 datasheet) | C17368638 / 0; reel C17325150 / 9 | **Replaces 1EDN7550 ×4.** Bottom, next to FETs, straddling the barrier |
| D1, D2 | Bootstrap Schottky 100 V 1 A | MCC SS110HL-TP | Active (BOM) | C19996385 / 0 | Required part (2 of 4 kept) |
| D3, D4 | Bootstrap clamp Zener 5.1 V | MCC BZT52C5V1-TP (SOD-123) | Active | C78728 / 7,000 | Keeps HS VGS ≤ 6 V |
| R9, R10 | Bootstrap series 4.7 Ω (0603) | — | — | — | Required value |
| R15, R16 | HS gate 2 Ω | — | — | — | Required value |
| R13, R14 | LS gate 5.6 Ω | — | — | — | Required value |
| RS2, RS3 (top) | Phase shunt 0.5 mΩ 2512 6 W | Bourns CSS2H-2512R-L500F | Active | C2073667 / 0 | Kelvin pairs to U6/U7 and U9/U10 |
| C19–C24, C25–C26 (top) | Output 6 × 10 µF 50 V X7R 1210 + 2 × 100 µF 35 V polymer | Stage 2 | | | |

## Isolation and control (LV unless noted)

| RefDes | Function | MPN | Mfr status | LCSC PN / stock | Notes |
|---|---|---|---|---|---|
| U5 | 2-phase voltage-mode controller, PWM outputs | ADI **LTC3861IUHE#PBF** (QFN-36 5×6) | Production (ADI, via distributor data) | C686466 / 0 (LTC3861IUH-1#PBF QFN-32: C686464 / 10) | ADI site blocks automated access; datasheet checked from a distributor copy |
| U6, U7 | Isolated shunt amplifier ±250 mV, built-in isolated DC-DC | TI **AMC3301DWER** | Active (ti.com) | C2869778 / 3,166 | Reinforced 4.25 kVrms |
| U8 | Isolated voltage amplifier ±1 V, built-in isolated DC-DC | TI **AMC3330DWER** | Active (ti.com) | C2999368 / 4,333 | |
| U9, U10 (HV) | Fast OCP comparator / current-sense amp, 0–36 V CM | TI **INA301A3IDGKR** | Active (ti.com) | C2861552 / 59 | Gain 100 |
| AT1, AT2 | 2-ch digital isolator (HV → LV flags) | Skyworks SI86S620BC-IS | Active (BOM) | C7363570 / 0 | **Kept**, new role |
| PS1 | Isolated 5 V → 5 V, 1 W | Murata NME1S0505SC | Active | C39128444 / 66 | Kept (Stage 1 review). Fallback NXE2S0505MC-R7 (2 W) |
| U15 (LV), U14 (HV), U22 (HV) | Comparator + 1.242 V reference (output OVP 27 V; OTP 80 °C; input OVP 82 V) | TI TLV3012AIDBVR | Active | C62505 / 3 | U22 added at the Stage 1 review for a precise 82 V input OVP |
| U16, U17, U18 | D flip-flop (cycle latches ×2, fault latch) | TI SN74LVC1G74DCTR | Active | C840104 / 2,335 | |
| U19, U20 | 2-input AND (PWM gating) | TI SN74LVC1G08DBVR | Active | C7666 / 68,650 | |
| D8, D9 | PGOOD green / FAULT red LED 0603 | Stage 2 | | | |
| J4 | Isolated signal connector (EN, PGOOD, FAULT, GND_ISO, spare) | Molex Nano-Fit 105313-1206 (right angle) | Active (BOM) | C17656275 / 0 | Reused |

## Input protection and supplies (HV)

| RefDes | Function | MPN | Mfr status | LCSC PN / stock | Notes |
|---|---|---|---|---|---|
| F1 | Fuse 25 A, SMD | Littelfuse 0456025.ER | Active | C315877 / 2,563 | **Confirm DC voltage rating ≥ 80 V** (LCSC: 125 VDC) |
| D6 | Input TVS, bidirectional, 85 V standoff | Littelfuse SMDJ85CA | Active | C1978008 / 158 | |
| Q2 | Reverse-polarity FET 100 V 1.5 mΩ TOLL | Infineon IPT015N10N5 | Active | C108964 / 40,000 | |
| U13 | Photovoltaic MOSFET driver | Vishay VOM1271T | Active | C146286 / 3,610 | Q2 gate |
| U12 | Hot-swap controller 9–80 V, auto-retry | TI **LM5069MM-2/NOPB** | Active (ti.com) | not found | Digi-Key |
| Q1 | Hot-swap pass FET 100 V | Infineon IPT015N10N5 | Active | C108964 / 40,000 | 100 V kept (Stage 1 review) |
| RS1 | 2 mΩ shunt | Bourns CSS2H-2512R-2L00F (or 2 × CSS2H-2512R-1L00F) | Active | 1 mΩ: C4175647 / 1,380 | |
| U11 | 5.2 V buck 6–100 V, 2.5 A | TI **LM5012DDAR** | Active (ti.com) | C6079494 / 1,414 | + 100 V 3 A Schottky + 22–33 µH inductor (Stage 2) |
| U21 | Fan current-limit switch | TI TPS2553DBVR | Active (ti.com) | C55266 / 52,811 | Limit ≈ 1.0 A |
| D7 | Fan-pin ESD array | TI TPD4E05U06DQAR | Active | C138714 / 236,560 | |
| J5 | Fan connector, 4 pin | Molex Micro-Fit 3.0 43650-0400 | Active | C277684 / 634 | |
| RT1 | NTC 10 kΩ B3380 0603 | Murata NCP18XH103F03RB | Active | C13564 / 169,520 | |
| FB1 | Ferrite (center-tap/shield link) | Murata BLM18KG601SN1 class | — | Stage 2 | |

## Connectors and mechanics

| RefDes | Function | MPN | Status | Notes |
|---|---|---|---|---|
| J1, J3 | DC+, DC− | Würth REDCUBE **74650194R** (THR, M4 blind-hole, 9 pins, 10 × 7 mm) | Active (Würth catalog: "Production is active") | Family rated 50–85 A. Blind hole, so the screw doesn't reach the bottom/heatsink side. Not on LCSC: Digi-Key |
| J2a, J2b | VOUT+, VOUT− | Würth REDCUBE 74650194R | Active | 46 A < 85 A class rating |
| HS1 | Heatsink | Alpha Novatech Z60-12.7B | Required | + 2.5 mm pedestal, insulating TIM (`thermal.md`) |
| FAN1 | Fan | Sanyo Denki 9GA0405P6H001 | Active, in stock on Digi-Key (confirmed 2026-10-15 per CLAUDE.md) | |
| H1–H4 | M3 mounting holes | — | — | Heatsink corners |

## Removed / changed vs the original BOM

| Old | New | Reason |
|---|---|---|
| U1–U4 1EDN7550 | U1, U2 Si8274GB1-IS1 | Isolated drivers with dead time; the 1EDN static CMR is marginal for high-side use at 79 V |
| D1–D4 SS110HL (4) | D1, D2 (2) + D3, D4 Zeners | Only the high sides need bootstrap; GaN over-charge clamp |
| R11, R12 4.7 Ω | — | Only 2 bootstrap resistors needed |
| AT1/AT2, PS1 | Kept, new roles | Isolation of the LV control domain |
| +5V_iso / GNDPWR nets | `+5V_ISO` / `GND_ISO` (LV), `+5V_PWR` / `PGND` (HV) | Two real domains now |
| 0402 parts (ERJ-2GE, RC0402, GRM155) | 0603 equivalents | Package rule (Stage 2) |
| C1–C4 "2.5 µF" | 2.2 µF GRM21BD72A225KE01L | Match the BOM |

## Candidates rejected

| Part | Why |
|---|---|
| ADI LTC7890 | Drivers and sense are on power ground, so the controller can't be isolated |
| TI TPS40090 | Peak-current mode needs a fast current signal across the barrier |
| ADI LTC3860 | Datasheet minimum frequency unconfirmed (ADI site blocked); LTC3861 chosen |
| TI UCC21222 | 8 V output UVLO, too high for 5 V GaN gate drive |
| Si8274AB1 (5 V UVLO) | UVLO+ 4.9–6.3 V, too close to the 5.2 V rail |
| ADI LTC4364 | VCC reverse rating −40 V < −79 V |
| TI TPS4811-Q1 | Reverse rating −30 V |
| TI LM5164 | 1 A, 97 % loaded at fan start |
