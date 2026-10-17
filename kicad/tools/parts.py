"""Part catalogue: footprints, manufacturer part numbers and LCSC numbers.

Every placed part gets MPN / Manufacturer (and LCSC where known) fields so the
BOM can be exported straight from the schematic.
"""

FP = {
    'R0603': 'Resistor_SMD:R_0603_1608Metric',
    'R0805': 'Resistor_SMD:R_0805_2012Metric',
    'R1206': 'Resistor_SMD:R_1206_3216Metric',
    'C0603': 'Capacitor_SMD:C_0603_1608Metric',
    'C0805': 'Capacitor_SMD:C_0805_2012Metric',
    'C1206': 'Capacitor_SMD:C_1206_3216Metric',
    'C1210': 'Capacitor_SMD:C_1210_3225Metric',
    'L0603': 'Inductor_SMD:L_0603_1608Metric',
    'LED0603': 'LED_SMD:LED_0603_1608Metric',
    'SOD123': 'Diode_SMD:D_SOD-123',
    'SOD123F': 'Diode_SMD:D_SOD-123F',
    'SOD323': 'Diode_SMD:D_SOD-323',
    'SMB': 'Diode_SMD:D_SMB',
    'SMC': 'Diode_SMD:D_SMC',
    'SOT23': 'Package_TO_SOT_SMD:SOT-23',
    'SOT23-5': 'Package_TO_SOT_SMD:SOT-23-5',
    'TOLL': 'Package_TO_SOT_SMD:Infineon_PG-HSOF-8-1',
    'TP': 'TestPoint:TestPoint_Pad_D1.5mm',
    'NETTIE': 'NetTie:NetTie-2_SMD_Pad0.5mm',
    'SHUNT2512': 'ECE533_Mods:R_2512_Kelvin',
    'REDCUBE': 'ECE533_Mods:Wurth_REDCUBE_74650194',
    'FUSE456': 'ECE533_Mods:Fuse_Littelfuse_NANO2_456',
    'MH_M3': 'MountingHole:MountingHole_3.2mm_M3_Pad_Via',
    'USON10': 'Package_SON:USON-10_2.5x1.0mm_P0.5mm',
    'L7070': 'Inductor_SMD:L_Coilcraft_XAL7070-XXX',
    'CPOL_EGXF': 'Capacitor_THT:CP_Radial_D12.5mm_P5.00mm',
    'CPOL_SMD': 'Capacitor_SMD:CP_Elec_8x10.5',
    'J_MICROFIT4': 'Connector_Molex:Molex_Micro-Fit_3.0_43650-0400_1x04_P3.00mm_Horizontal',
    'J_NANOFIT6': 'Connector_Molex:Molex_Nano-Fit_105313-xx06_1x06_P2.50mm_Horizontal',
}


def _code(val):
    """'4.7' -> '4R7', '10k' -> '10K', '95.3k' -> '95K3', '1.69M' -> '1M69', '2' -> '2R'."""
    v = val.replace('Ω', '').strip()
    mult = 'R'
    if v[-1] in 'kKmM':
        mult = 'K' if v[-1] in 'kK' else 'M'
        v = v[:-1]
    if '.' in v:
        a, b = v.split('.')
        b = b.rstrip('0')
        return f'{a}{mult}{b}'
    return f'{v}{mult}' if mult == 'R' else f'{v}{mult}'


def _e96code(val):
    """Panasonic ERA 4-digit code: '10.0k' -> '1002', '649k' -> '6493'."""
    v = val.strip()
    mult = 1
    if v[-1] in 'kK':
        mult, v = 1e3, v[:-1]
    elif v[-1] in 'mM':
        mult, v = 1e6, v[:-1]
    ohms = float(v) * mult
    if ohms <= 0:
        raise ValueError('no precision code for 0 ohm')
    exp = 0
    while ohms >= 1000:
        ohms /= 10
        exp += 1
    while ohms < 100:
        ohms *= 10
        exp -= 1
    return f'{int(round(ohms)):03d}{exp}'


def res(val, size='0603', prec=False, power=None):
    """Return (value_text, footprint, fields)."""
    if prec:
        series = {'0603': 'ERA-3AEB', '0805': 'ERA-6AEB', '1206': 'ERA-8AEB'}[size]
        mpn = f'{series}{_e96code(val)}V'
        mfr = 'Panasonic'
        text = f'{val} 0.1%'
    else:
        mpn = f'RC{size}FR-07{_code(val)}L' if val != '0' else f'RC{size}JR-070RL'
        mfr = 'YAGEO'
        text = val
    return text, FP['R' + size], {'MPN': mpn, 'Manufacturer': mfr}


# LCSC numbers below were read from lcsc.com search results (2026-10-16); '' = not found / not checked
CAPS = {
    # (value, voltage, size): (MPN, LCSC, manufacturer)
    ('100n', '50V', '0603'): ('GRM188R71H104KA93D', 'C77055', 'Murata'),
    ('100n', '100V', '0603'): ('GRM188R72A104KA35D', 'C77058', 'Murata'),
    ('1u', '25V', '0603'): ('GRM188R71E105KA12D', 'C86020', 'Murata'),
    ('1u', '100V', '0805'): ('CC0805KKX7R0BB105', 'C5370002', 'YAGEO'),
    ('10u', '10V', '0805'): ('GRM21BR71A106KE51L', 'C86038', 'Murata'),
    ('10u', '50V', '1210'): ('GRM32ER71H106KA12L', 'C77102', 'Murata'),
    ('22u', '10V', '1206'): ('GRM31CR71A226KE15L', 'C91604', 'Murata'),
    ('2.2u', '100V', '0805'): ('GRM21BD72A225KE01L', 'C2981733', 'Murata'),
    ('10n', '100V', '0603'): ('GRM188R72A103KA01D', 'C162275', 'Murata'),
    ('1n', '200V', '0805'): ('C0805C102J2GAC7800', 'C2170811', 'KEMET'),
    ('1n', '50V', '0603'): ('GRM1885C1H102JA01D', 'C77026', 'Murata'),
    ('2.2n', '50V', '0603'): ('GRM188R71H222KA01D', 'C86023', 'Murata'),
    ('4.7n', '50V', '0603'): ('GRM188R71H472KA01D', 'C77057', 'Murata'),
    ('10n', '50V', '0603'): ('GRM188R71H103KA01D', 'C77053', 'Murata'),
    ('47n', '50V', '0603'): ('GRM188R71H473KA61D', 'C86027', 'Murata'),
    ('100p', '50V', '0603'): ('GRM1885C1H101JA01D', 'C71664', 'Murata'),
    ('470n', '25V', '0603'): ('GRM188R71E474KA12D', 'C77052', 'Murata'),
}

LCSC_BY_MPN = {
    'LTST-C191KGKT': 'C125098', 'LTST-C191KRKT': 'C125099', 'BAT54W-7-F': 'C134417',
    'BLM18KG601SN1D': 'C85833', '2N7002LT1G': 'C16338',
}


def cap(val, volt, size):
    mpn, lcsc, mfr = CAPS[(val, volt, size)]
    f = {'MPN': mpn, 'Manufacturer': mfr}
    if lcsc:
        f['LCSC'] = lcsc
    return f'{val}/{volt}', FP['C' + size], f


def part(mpn, mfr, fp_key_or_name, lcsc=None, **extra):
    fp = FP.get(fp_key_or_name, fp_key_or_name)
    f = {'MPN': mpn, 'Manufacturer': mfr}
    lcsc = lcsc or LCSC_BY_MPN.get(mpn)
    if lcsc:
        f['LCSC'] = lcsc
    f.update(extra)
    return fp, f
