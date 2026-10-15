# 2-Phase Interleaved Coupled-Inductor GaN Buck Converter — 72 V → 24 V, 1.1 kW

A two-phase interleaved synchronous buck converter using EPC2304 eGaN FETs and a TDK ERUC23
coupled inductor at 200 kHz. It started as the ECE 533 (Power Electronics Packaging, NC State,
Spring 2026) final project by Team MeGaNism and is being turned into a credit-card-size
(85.6 × 54 mm) PCB with an on-board analog controller and full protection, designed in KiCad 10.

| | |
|---|---|
| Input | 72 V nominal (64.8–79.2 V) |
| Output | 24 V, 46 A, 1.1 kW |
| Switching | 2 phases × 200 kHz, 180° interleaved |
| Target efficiency | ≥ 95 % |
| Board | 85.6 × 53.98 mm, 4-layer, 1.6 mm, JLCPCB |

## Status
See [`PROGRESS.md`](PROGRESS.md) for the current stage and decisions. The full design requirements are in
[`CLAUDE.md`](CLAUDE.md).

## Repository layout
```
kicad/ECE533_Guide/   KiCad 10 project (schematic, PCB, project-local footprints)
kicad/lib/vendor/     Vendor symbols/footprints: local only, see README inside
bom/                  Bill of materials
docs/                 Final report (PDF + DOCX), earlier report, design notes, datasheet links
sim/ltspice/          LTspice simulations (vendor models local only, see README inside)
fab/                  Fabrication outputs (added in Stage 5)
.github/workflows/    CI: KiCad ERC/DRC + schematic PDF on every push
```

## Getting started (local)
1. Clone the repo and install KiCad 10.0.
2. Download the vendor libraries into `kicad/lib/vendor/` (see its README). The project opens without them.
3. Open `kicad/ECE533_Guide/ECE533_Guide.kicad_pro`.

## Background
The original design, analysis (Q3D parasitics, ANSYS thermal/mechanical) and simulations are documented in
[`docs/ECE533_Final_Report.pdf`](docs/ECE533_Final_Report.pdf).
