# kicad/tools

Scripts used to build and check the Stage 2 schematic. Run them with KiCad's bundled Python
(`C:\Program Files\KiCad\10.0\bin\python.exe` on Windows).

| Script | What it does |
|---|---|
| `gen_symbols.py` | Writes the project symbol library `ECE533_Guide/ECE533.kicad_sym`: custom IC symbols drawn from the manufacturer datasheets (LTC3861, Si8274, AMC3301, INA301, LM5012, TPS2553, TLV3012, VOM1271, 74LVC1G74, SI86S620, NME1S0505SC, EPC2304, ERUC23) and the named power symbols (PGND, GND_ISO, +5V_PWR, +5V_ISO, VBUS, +24V). |
| `gen_schematic.py` | Generated the initial hierarchical sheets (root, input protection, power stage, 2 × power phase, aux supply/fan, isolation, controller, fault logic/rack I/O). |
| `check_netlist.py` | Connectivity checks on an exported netlist (74 checks: every signal path through the hierarchy, Kelvin returns, the two ground domains kept apart). |
| `kisch.py`, `kilib.py`, `sexp.py`, `parts.py` | Helpers: schematic writer, symbol builder, S-expression reader, part catalogue (footprints, MPNs). |

**After Stage 2, edit the schematic in KiCad.** Re-running `gen_schematic.py` overwrites the
sheets, so it is a record of how they were built, not the master copy. `check_netlist.py` stays
useful after manual edits:

```
kicad-cli sch export netlist -o build.net kicad/ECE533_Guide/ECE533_Guide.kicad_sch
python kicad/tools/check_netlist.py build.net
```
