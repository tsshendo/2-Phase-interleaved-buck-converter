# Stage 2 — Schematic (issue #2)

KiCad 10 project `kicad/ECE533_Guide/`. The schematic PDF is built by CI on every push (artifact
`kicad-reports`), or locally with
`kicad-cli sch export pdf -o ECE533_Guide-schematic.pdf kicad/ECE533_Guide/ECE533_Guide.kicad_sch`.

## 1. Sheet structure

| Page | Sheet | Contents |
|---|---|---|
| 1 | Overview (root) | Block diagram with wired sheet interfaces, domain, rail and protection summary |
| 2 | Input protection | J1/J3, F1, D6, reverse-polarity Q2 + U13, RS1 + Q1 + U12 (LM5069-2), precise 82 V OVP (U22), bulk C5/C6 |
| 3 | Power stage | Two instances of the phase sheet, L1, output caps and J2/J6, OTP (RT1 + U14), EMI center-tap FB1, heatsink holes H1–H4 |
| 4, 5 | Phase 1, Phase 2 (`power_phase.kicad_sch`, one file, two instances) | Si8274 driver, half-bridge, bootstrap, gate network, Kelvin net-ties, DNP snubbers, HF caps, shunt, INA301 fast OCP, AMC3301 current amplifier |
| 6 | Aux supply and fan | LM5012 → +5V_PWR, TPS2553 fan switch, J5, ESD |
| 7 | Isolation | PS1, AT1/AT2 flags, AMC3330 VOUT feedback; red barrier line |
| 8 | Controller (LV) | LTC3861, feedback and current scaling, compensation, cycle-by-cycle latches |
| 9 | Fault logic and rack I/O (nested under Controller) | Output OVP, fault latch, RUN_OK wired-AND, LEDs, J4 |

## 2. Conventions used
- **Signal flow** left to right on every sheet. Blocks are framed with dashed boxes and titled.
  Design values and the equations behind them are written next to each block.
- **Domains:** the phase and isolation sheets show the barrier as a red dashed line, HV on one side
  and LV on the other. Only the rated isolation parts sit on the line.
- **Rails** use named power symbols: `PGND`, `GND_ISO`, `+5V_PWR`, `+5V_ISO`, `VBUS`, `+24V`. On IC
  side pins, a rail tie is drawn as a global-label tag of the same name, so it can't collide with the
  next pin row (same global net; checked in the netlist).
- **Inter-sheet signals** are hierarchical labels. Each sheet pin shows its direction (input or
  output). On the root page the main paths are drawn as wires.
- **Kelvin connections** are explicit:
  - Each EPC2304 pad 2 ("SK", nearest the gate) is its own net (`SW_K` / `PGND_K`) for the driver
    return. It joins the power net only through a net-tie (NT1–NT4), placed at the pad in layout.
  - Shunts use 4-terminal symbols (R_Shunt), so sense pins 2/3 are separate nets. The custom
    footprint ties them to the power pads with net-tie pad groups (Stage 3).
- **Series chains** (R–D, R–C, R–LED) are wired directly and dividers are stacked, so each internal
  node is labelled at most once.
- **Footprint, MPN, manufacturer and LCSC** fields are on every BOM part. DNP parts are marked DNP
  (shown crossed out). Test pads, net-ties and mounting holes are excluded from the BOM.

## 3. Reference designators (changes from the Stage 1 note)
Phase sheet, phase 1 / phase 2: driver U1/U2; HS FET Q3/Q5; LS FET Q4/Q6; bootstrap R9/R10, D1/D2,
C7/C9, clamp Zeners D3/D4; HS gate R15/R16 (2 Ω); LS gate R13/R14 (5.6 Ω); gate pull-downs
R1–R4 (51 kΩ); VDDB C8/C10 + C12/C14; VDDI C11/C13; HF caps C1–C4 + C15–C18; shunts RS2/RS3;
INA301 U9/U10; AMC3301 U6/U7.

Not used (retired from the original BOM): U3, U4 (1EDN7550), R5–R8, R11, R12, R17–R20. Other parts
keep the numbers in `parts_stage1.md` with these additions:
- U25 (74LVC1G08, fault-set AND)
- D15/D16 (BAT54W, RUN_OK wired-AND)
- Q7/Q8 (2N7002, PGOOD LED and FAULT_N output)
- R93 (fan EN pull-up), R94/R95 (PWMEN pull-downs)
- C66/C67 output polymer caps
- H1–H4 heatsink holes, NT1–NT4 Kelvin net-ties, TP1–TP16 test pads

## 4. Changes made while drawing the schematic
| Change | Reason |
|---|---|
| AT2 channel B carries **BUS_PG** (LM5069 PGD) instead of fan tach | The controller must not start switching while VBUS is still charging through Q1. Tach stays on TP14 |
| Si8274 ENABLE driven by **LTC3861 PWMEN** (not directly by RUN_OK) | RUN_OK → RUN low → PWM three-state → PWMEN low gives the same result with no extra logic. PWMEN needs a pull-down per the datasheet (R94/R95) |
| LM5069 VIN: **no series resistor**, C71 bypass only | 1.3 mA × 10 Ω would shift the 55 mV current-limit threshold by 13 mV |
| PGOOD LED driven by Q7, FAULT_N output by Q8 | LTC3861 PGOOD is open drain (an LED on it would light when power is *bad*); J4 outputs are open drain for the host |
| C5/C6 bulk = 2 × EGXF 110 µF | CLAUDE.md lists C5/C6. The 5-piece BOM line is reconciled to 2 (≈220 µF): enough for damping; the hot-swap limits inrush |
| 1 µF/100 V caps → Yageo CC0805KKX7R0BB105; 1 nF/200 V snubber cap → KEMET C0805C102J2GAC7800 | The Murata numbers first chosen could not be confirmed to exist |

## 5. Verification
- **ERC** (KiCad 10.0.1, all severities): **0 errors, 11 warnings.** Every warning is
  `footprint_link_issues` for the custom footprints drawn in Stage 3:
  - `ECE533_Mods:EPC2304_QFN-7_3x5mm` (Q3–Q6)
  - `TDK_ERUC23` (L1)
  - `Wurth_REDCUBE_74650194` (J1, J2, J3, J6)
  - `Fuse_Littelfuse_NANO2_456` (F1)
  - `Murata_NME1S_SIP-4` (PS1)
  - `R_2512_Kelvin` (RS1–RS3; needs net-tie pad groups)
- **CI:** a blocking "ERC errors" step was added; warnings are reported but don't block. The workflow
  now installs KiCad's default library tables in the container. Without them, CI reported 428
  "library not included" warnings that don't occur on a normal install. DRC still reports the empty
  board outline (Stage 3).
- **Netlist checks:** `kicad/tools/check_netlist.py` runs 74 checks, and all pass:
  - every signal path through the hierarchy (PWM, EN, current sense, VOUT feedback, all fault flags,
    RUN_OK, BUS_PG)
  - the Kelvin nets
  - the hot-swap and Kelvin shunt connections
  - fan and rack I/O
  - all six rails
  - PGND ≠ GND_ISO
  - unique reference designators (this check caught a duplicate C114, now fixed)
- **Readability:** every page was rendered and reviewed. Clashing labels, fields and symbol rows were
  fixed.

## 6. BOM
`bom/PCB_BOM.xlsx` (sheet "BOM"; the previous report BOM is kept as "Original (report BOM)") and
`bom/PCB_BOM.csv`, generated by `kicad/tools/make_bom.py` from the netlist: 94 lines, 248 parts,
14 of them DNP.
- **Digi-Key PNs and prices** are carried over where the MPN is unchanged. The rest is left for the
  user to fill (agreed in Stage 1).
- **LCSC PNs** were verified on lcsc.com for 47 lines (date in `parts.py`). Lines without one are
  Digi-Key-only parts (TDK, Würth, Coilcraft, LM5069, Panasonic ZA, Vishay 30BQ100, Bourns 2 mΩ) or
  standard 1 % 0603 resistors, which JLC can take from its basic library.
- **Zero or very low LCSC stock on the check date:** EPC2304, LTC3861IUHE, Si8274GB1-IS1 (9 on reel),
  SI86S620BC, EGXF, SS110HL, 0.5 mΩ shunt, Molex 105313-1206, BAT54W-7-F, 4.7 nF and 47 nF Murata. Source these from Digi-Key or
  consign them to JLC.

## 7. Open items carried to Stage 3 / bring-up
1. Draw the custom footprints listed in §5 (EPC2304 land pattern from the datasheet; REDCUBE, NANO2
   456, NME1S, ERUC23 from the vendor drawings). The shunt footprint needs net-tie pad groups (1–2,
   3–4).
2. **Starting values to confirm in SPICE or on the bench:**
   - LTC3861 type-III compensation (R81–R83, C107–C109)
   - LM5012 ripple injection (R59/C81/C82)
   - Si8274 dead time (R21/R22 → 20 ns)
   - LM5069 power limit and timer (R47, C72) against the IPT015N10N5 SOA
3. LTC3861 VSNSP1/VSNSN1 input bias: check the differential-amplifier input current against the
   10 k / 5.97 k scaling dividers. The datasheet lists ±100 nA, which is negligible; confirm the
   common-mode range at ~0.54 V.
4. PS1 output voltage at 130–176 mA vs the AMC3330 4.5 V minimum.
5. ERUC23-3R2K saturation rating per winding vs the 31 A peak; fuse 0456025.ER DC rating.
6. EPC2304 RDS(on) is 3.5 mΩ typ / 5 mΩ max per the datasheet (Stage 1 used 3.2 mΩ). Conduction loss
   rises about 10–55 %; efficiency stays above 97 %.
