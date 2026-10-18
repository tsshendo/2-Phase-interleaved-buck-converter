"""Project copy of KiCad's Molex_Nano-Fit_105313-xx06_1x06_P2.50mm_Horizontal (J4 on the power
module): points at the right-angle model from gen_footprints.nanofit_ra_step() and drops the
silkscreen past x = 8.4 (beyond the board edge when the body overhangs it). Called by
gen_footprints.py."""
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
MODS = os.path.normpath(os.path.join(HERE, '..', 'ECE533_Guide', 'ECE533_Mods.pretty'))
KICAD_FP = os.environ.get('KICAD10_FOOTPRINT_DIR', r'C:\Program Files\KiCad\10.0\share\kicad\footprints')
NAME = 'Molex_Nano-Fit_105313-1206_RA'


def nanofit_ra_fp():
    src = os.path.join(KICAD_FP, 'Connector_Molex.pretty',
                       'Molex_Nano-Fit_105313-xx06_1x06_P2.50mm_Horizontal.kicad_mod')
    t = open(src, encoding='utf-8').read()
    t = t.replace('(footprint "Molex_Nano-Fit_105313-xx06_1x06_P2.50mm_Horizontal"', f'(footprint "{NAME}"', 1)
    out, i = [], 0
    for m in re.finditer(r'\n\t\(fp_(?:line|rect|poly|arc|circle)\b.*?\n\t\)', t, re.S):
        blk = m.group(0)
        xs = [float(x) for x in re.findall(r'\((?:start|end|xy|mid|center) ([-\d.]+) [-\d.]+\)', blk)]
        if '"F.SilkS"' in blk and xs and max(xs) > 8.4:
            out.append(t[i:m.start()])
            i = m.end()
    out.append(t[i:])
    t = ''.join(out)
    t = re.sub(r'\(model "[^"]*"', f'(model "${{KIPRJMOD}}/../ECE533_Guide/ECE533_Mods.3dshapes/{NAME}.step"', t)
    with open(os.path.join(MODS, NAME + '.kicad_mod'), 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(t)
    print('wrote', os.path.join('ECE533_Mods.pretty', NAME + '.kicad_mod'))
