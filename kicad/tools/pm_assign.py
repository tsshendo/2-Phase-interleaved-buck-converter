"""PowerModule: give the base-schematic symbols their footprints, BOM values and part numbers.

The circuit is the ECE 533 report power module as drawn in the base schematic (commit 57d8ca5);
this script only fills the Value, Footprint, MPN, Manufacturer and LCSC fields so the schematic
matches the BOM (0603 minimum, catalog values). Re-runnable.
    python kicad/tools/pm_assign.py
"""
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
PRJ = os.path.normpath(os.path.join(HERE, '..', 'PowerModule'))
SHEETS = ['PowerModule.kicad_sch', 'gate_drive.kicad_sch']

R0603, C0603, C0805 = ('Resistor_SMD:R_0603_1608Metric', 'Capacitor_SMD:C_0603_1608Metric',
                       'Capacitor_SMD:C_0805_2012Metric')


def rng(prefix, *nums):
    return [f'{prefix}{i}' for i in nums]


# ref list -> (value, footprint, MPN, manufacturer, LCSC)
PARTS = [
    (rng('C', 1, 2, 3, 4), ('2.2u/100V', C0805, 'GRM21BD72A225KE01L', 'Murata', 'C2981733')),
    (rng('C', 5, 6, 15, 16), ('62u/160V', 'Capacitor_THT:CP_Radial_D10.0mm_P5.00mm', 'EGXF161ELL620MJ25S',
                              'Chemi-Con', '')),     # each bulk cap = 2 x half value (user)
    (rng('C', 7, 8, 9, 10, 11, 13), ('100n/50V', C0603, 'GRM188R71H104KA93D', 'Murata', 'C77055')),
    (rng('C', 12, 14), ('10u/10V', C0805, 'GRM21BR71A106KE51L', 'Murata', 'C86038')),
    (rng('R', *range(1, 9)), ('51k', R0603, 'RC0603FR-0751KL', 'YAGEO', '')),
    (rng('R', 9, 10, 11, 12), ('4.7', R0603, 'RC0603FR-074R7L', 'YAGEO', '')),
    (rng('R', 13, 14, 19, 20), ('5.6', R0603, 'RC0603FR-075R6L', 'YAGEO', '')),
    (rng('R', 15, 16, 17, 18), ('2', R0603, 'RC0603FR-072RL', 'YAGEO', '')),
    (rng('D', 1, 2, 3, 4), ('SS110HL', 'Diode_SMD:D_SOD-123F', 'SS110HL-TP', 'MCC', 'C19996385')),
    (rng('U', 1, 2, 3, 4), ('1EDN7550B', 'Package_TO_SOT_SMD:SOT-23-6', '1EDN7550BXTSA1', 'Infineon', '')),
    (rng('AT', 1, 2), ('SI86S620BC-IS', 'Package_SO:SOIC-8_3.9x4.9mm_P1.27mm', 'SI86S620BC-IS',
                       'Skyworks', 'C7363570')),
    (['PS1'], ('NME1S0505SC', 'ECE533_Vendor:Murata_NME1S_SIP-4', 'NME1S0505SC', 'Murata',
               'C39128444')),
    (['J4'], ('105313-1206', 'Connector_Molex:Molex_Nano-Fit_105313-xx06_1x06_P2.50mm_Horizontal',
              '105313-1206', 'Molex', 'C17656275')),
    (['L1'], ('ERUC23-3R2K', 'ECE533_Mods:TDK_ERUC23', 'ERUC23-3R2K', 'TDK', '')),
    (rng('Q', 3, 4, 5, 6), ('EPC2304', 'ECE533_Mods:EPC2304_QFN-7_3x5mm_15pin', 'EPC2304', 'EPC',
                            'C6549215')),
    (['J1'], ('DC+', 'ECE533_Vendor:Wurth_REDCUBE_74650194', '74650194R', 'Wurth Elektronik', '')),
    (['J2'], ('Power_out', 'ECE533_Vendor:Wurth_REDCUBE_74650194', '74650194R', 'Wurth Elektronik', '')),
    (['J3'], ('DC-', 'ECE533_Vendor:Wurth_REDCUBE_74650194', '74650194R', 'Wurth Elektronik', '')),
]
TABLE = {r: v for refs, v in PARTS for r in refs}


def hidden(name, value, at):
    return (f'\t\t(property "{name}" "{value}"\n\t\t\t(at {at} 0)\n\t\t\t(show_name no)\n'
            f'\t\t\t(do_not_autoplace no)\n\t\t\t(hide yes)\n\t\t\t(effects\n\t\t\t\t(font\n'
            f'\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n')


def set_prop(block, name, value):
    pat = re.compile(r'(\n\t\t\(property "' + re.escape(name) + r'" ")([^"]*)(")')
    if pat.search(block):
        return pat.sub(lambda m: m.group(1) + value + m.group(3), block, count=1)
    at = re.search(r'\n\t\t\(at ([-\d.]+ [-\d.]+)', block).group(1)
    i = block.index('\n\t\t(pin ') if '\n\t\t(pin ' in block else block.index('\n\t\t(instances')
    return block[:i + 1] + hidden(name, value, at) + block[i + 1:]


def process(path):
    t = open(path, encoding='utf-8').read()
    out, pos, seen = [], 0, []
    for m in re.finditer(r'\n\t\(symbol\n\t\t\(lib_id ', t):
        start = m.start() + 1
        end = t.index('\n\t)\n', start) + 3
        block = t[start:end]
        ref = re.search(r'\(property "Reference" "([^"]*)"', block).group(1)
        if ref in TABLE:
            val, fp, mpn, mfr, lcsc = TABLE[ref]
            for k, v in (('Value', val), ('Footprint', fp), ('MPN', mpn), ('Manufacturer', mfr),
                         ('LCSC', lcsc)):
                block = set_prop(block, k, v)
            seen.append(ref)
        out.append(t[pos:start] + block)
        pos = end
    out.append(t[pos:])
    open(path, 'w', encoding='utf-8', newline='\n').write(''.join(out))
    return seen


if __name__ == '__main__':
    done = []
    for s in SHEETS:
        done += process(os.path.join(PRJ, s))
    missing = sorted(set(TABLE) - set(done))
    print(f'assigned {len(done)} symbols; not found: {missing}')
