# Vendor KiCad libraries and 3D models (local only, not committed)

The 3D models and the two vendor footprints below come from SamacSys / Component Search Engine,
TDK and Würth Elektronik. Their licenses allow use in board designs but not redistribution as a
library, so this folder is git-ignored (only this README is committed).

The board stores copies of its footprints, so the project opens and passes DRC without this
folder. What you lose without it: the 3D models in the 3D viewer and renders, and the
`ECE533_Vendor` footprint library (ERC on a fresh clone reports it as missing; CI does the same).

## Setup on a new machine
1. Download the files in the table and extract them to the paths shown (relative to this folder).
2. Run `python kicad/tools/gen_footprints.py` with KiCad's Python. It writes
   `ECE533_Vendor.pretty/` here (the vendor footprints, renamed, with model paths pointing into
   this folder) and regenerates the committed `ECE533_Guide/ECE533_Mods.pretty/`.

| Part | Source | Path here | Used for |
|---|---|---|---|
| EPC2304 | SamacSys ("ECAD model" on Mouser/Digi-Key) | `EPC2304/3D/EPC2304.stp` | 3D model only. The SamacSys footprint (`EPC2308.kicad_mod`, 15 pads) does not match the EPC land pattern; `ECE533_Mods:EPC2304_QFN-7_3x5mm` is drawn from the EPC datasheet instead |
| ERUC23-3R2K | TDK product page, "3D model (STEP)" | `TDK_ERUC23/b82559sxm023_eruc23_14.0mm_max_public_tkd-pc.step` | 3D model only. The SamacSys pads do not match TDK's recommended layout; `ECE533_Mods:TDK_ERUC23` follows TDK |
| NME1S0505SC | SamacSys | `NME1S0505SC/KiCad/NME1S0505SC.kicad_mod`, `NME1S0505SC/3D/NME1S0505SC.stp` | `ECE533_Vendor:Murata_NME1S_SIP-4` + 3D |
| 74650194R REDCUBE | we-online.com, `KiCad_WP-THRBU_rev26b.zip` (CC BY-SA 4.0 with design exception) | `Wurth_74650194/zip/` (zip extracted as-is) | `ECE533_Vendor:Wurth_REDCUBE_74650194` + 3D |

Würth blocks scripted downloads; save the zip from a browser.

## Model alignment (checked by rendering, 2026-10-16)
- EPC2304 STEP: rotate z +90°. Strips, tabs and the gate/source notch land on the EPC pads; the
  model's pin-1 dot sits over the gate.
- TDK STEP: built with z as height (terminals at +z) and y as depth from 0 to 13.9 mm, so it
  needs rotate x 180° and offset (0, 6.865, 7.2) mm. Its feet land on pads 4/1/3/2.
- NME1S0505SC: SamacSys transform (legacy inch units converted: offset 7.62, 0, −0.66 mm,
  rotate −90, 0, −180). Body matches the outline, pin 1 dot on the square pad.
- REDCUBE: Würth's own transform, unchanged.
