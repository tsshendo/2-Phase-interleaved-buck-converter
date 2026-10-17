"""PowerModule BOM (CSV) from the schematic netlist.

    kicad-cli sch export netlist -o pm.net kicad/PowerModule/PowerModule.kicad_sch
    python kicad/tools/pm_bom.py pm.net bom/PowerModule_BOM.csv

Digi-Key numbers are the ones already checked for the main board BOM (bom/PCB_BOM.csv); parts that
only the power module uses are marked for confirmation.
"""
import collections
import csv
import re
import sys

import build_pcb as bp

DIGIKEY = {'SI86S620BC-IS': '863-SI86S620BC-IS-ND', 'GRM21BD72A225KE01L': '490-GRM21BD72A225KE01LCT-ND',
           'EGXF161ELL111MK25S': '565-EGXF161ELL111MK25S-ND', 'SS110HL-TP': '353-SS110HL-TPCT-ND',
           '105313-1206': 'WM14975-ND', 'ERUC23-3R2K': '495-ERUC23-3R2KCT-ND',
           'NME1S0505SC': '811-NME1S0505SC-ND', 'EPC2304': '917-EPC2304CT-ND'}
MAIN_BOM = {'GRM188R71H104KA93D', 'GRM21BR71A106KE51L', 'RC0603FR-0751KL', 'RC0603FR-074R7L',
            'RC0603FR-075R6L', 'RC0603FR-072RL', '74650194R'}


def natural(ref):
    m = re.match(r'([A-Z]+)(\d+)', ref)
    return (m.group(1), int(m.group(2))) if m else (ref, 0)


def main(net, out):
    comps, _ = bp.read_netlist(net)
    groups = collections.OrderedDict()
    for ref in sorted(comps, key=natural):
        c = comps[ref]
        f = c['fields']
        key = (c['value'], f.get('MPN', ''), c['fp'])
        groups.setdefault(key, []).append(ref)
    with open(out, 'w', encoding='utf-8', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['Item', 'Qty', 'Reference designators', 'Value', 'Manufacturer part number',
                    'Manufacturer', 'Digi-Key PN', 'LCSC PN', 'Footprint', 'Side', 'Notes'])
        for i, ((val, mpn, fp), refs) in enumerate(groups.items(), 1):
            f = comps[refs[0]]['fields']
            side = 'Bottom' if refs[0][0] == 'Q' or refs[0] in ('C1', 'C2', 'C3', 'C4') else 'Top'
            note = 'Report part (base schematic)'
            if mpn in MAIN_BOM:
                note = 'Same part as the main board BOM'
            if mpn == 'EGXF161ELL620MJ25S':
                note = 'Bulk split into 2 x half value per position (GXF 160 V, 10 x 25 mm); Digi-Key PN and stock to confirm'
            if mpn == '1EDN7550BXTSA1':
                note = 'Report driver (base schematic); Digi-Key PN and stock to confirm'
            w.writerow([i, len(refs), ','.join(refs), val, mpn, f.get('Manufacturer', ''),
                        DIGIKEY.get(mpn, ''), f.get('LCSC', ''), fp.split(':')[-1], side, note])
        w.writerow([len(groups) + 1, 1, '(mechanical)', 'Z60-12.7B heatsink', 'Z60-12.7B', 'Alpha Novatech',
                    '', '', '4 x M3 holes H1-H4', 'Bottom', 'Pedestal 3.0 mm over the FET block, insulating TIM'])
    print(f'{len(groups)} lines, {len(comps)} parts -> {out}')


if __name__ == '__main__':
    main(*sys.argv[1:])
