# LTspice vendor models (local only — not committed)

`ECE533_IL_Buck_parasitics (2).asc` uses two vendor models that are copyrighted by
their manufacturers, so they aren't committed. Download them and put them in this folder
(or next to the `.asc`):

| File | Source |
|---|---|
| `EPCGaNLibrary.lib`, `EPCGaN.asy` | EPC GaN LTspice device library, epc-co.com → Design Support → Device Models |
| `ERUC.sub`, `ERUC.asy` | TDK ERUC23 coupled-inductor SPICE model, TDK product page for ERUC23-3R2K |

Transient `.raw` result files are git-ignored (the full-load run is about 1.6 GB);
re-run the simulation to regenerate them. Small `.op.raw` operating-point files are kept.
