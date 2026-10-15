# Vendor KiCad libraries (local only — not committed)

The symbols, footprints and 3D models for the parts below came from SamacSys /
Component Search Engine (the `LIB_*.zip` downloads). Their license allows
unrestricted use in board designs but **forbids redistributing the models as a PCB
library**, so this folder is git-ignored. The schematic and PCB embed copies of
the symbols and footprints they use, so the project still opens without this folder.
The folder is only needed to place new instances or update footprints.

## Setup on a new machine
1. Download each part's library (KiCad format) from componentsearchengine.com,
   or from the "ECAD Model" link on the Mouser/Digi-Key product page.
2. Extract so each part has its own folder:
   ```
   kicad/lib/vendor/<PART>/KiCad/*.kicad_sym, *.kicad_mod
   kicad/lib/vendor/<PART>/3D/*.stp
   ```
3. Point the project's `sym-lib-table` / `fp-lib-table` at these folders with
   `${KIPRJMOD}/../lib/vendor/...` paths (to be set up in Stage 2).

## Parts
| Part | Function | Footprint file in download |
|---|---|---|
| EPC2304 | 200 V eGaN FET | EPC2308.kicad_mod |
| ERUC23-3R2K | TDK coupled inductor | ERUC233R2K.kicad_mod |
| 1EDN7550UXTSA1 | Infineon gate driver | 1EDN7550UXTSA1.kicad_mod |
| SI86S620BC-IS / SI86S622BC-IS | Digital isolators (likely to be removed) | SOIC127P600X175-8N.kicad_mod |
| NME1S0505SC | Isolated 5 V module (likely to be removed) | NME1S0505SC.kicad_mod |
| 105313-1206 | Molex signal header | 1053131206.kicad_mod |

Footprints we draw ourselves (heatsink keep-out, REDCUBE terminals if needed,
etc.) go in `kicad/ECE533_Guide/ECE533_Mods.pretty/`, and those **are** committed.
