"""Generate the Stage 2 hierarchical schematic for the ECE533 credit-card buck.

Sheets (see docs/design/isolation_architecture.md):
  root                ECE533_Guide.kicad_sch   block diagram, mounting holes
  input_protection    fuse, TVS, reverse FET, hot-swap, 82 V OVP, bulk caps
  power_stage         coupled inductor, output caps/terminals, OTP, EMI
    power_phase (x2)  isolated driver, half-bridge, bootstrap, shunt, OCP, AMC3301
  aux_supply_fan      LM5012 5.2 V rail, fan switch and connector
  isolation           PS1, AT1/AT2 flags, AMC3330 VOUT sense
  controller          LTC3861, cycle-by-cycle latches, fault latch, OVP, LEDs, J4

Run with KiCad's Python:  python kicad/tools/gen_schematic.py
This is the initial Stage 2 generation; after review the sheets are edited in
KiCad directly, so treat this script as a record of how they were built.
"""
import os

import kisch
from kisch import Sheet, G
from parts import FP, cap, part, res

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'ECE533_Guide')
RED = (200, 0, 0)


def g(n):
    return round(n * G, 4)


# ---------------------------------------------------------------------------
# placement helpers (x, y = location of pin 1 on the 2.54 mm grid)
# ---------------------------------------------------------------------------
def rv(sh, lib, ref, val, x, y, n1, n2, fp=None, fields=None, span=3.81, **kw):
    """Vertical 2-pin part, pin 1 at top (x, y)."""
    return _two(sh, lib, ref, val, x, y + span, 0, n1, n2, fp, fields, **kw)


def rh(sh, lib, ref, val, x, y, n1, n2, fp=None, fields=None, span=3.81, **kw):
    """Horizontal 2-pin part, pin 1 at left (x, y)."""
    return _two(sh, lib, ref, val, x + span, y, 90, n1, n2, fp, fields, **kw)


def _two(sh, lib, ref, val, x, y, r, n1, n2, fp, fields, **kw):
    p = sh.add(lib, ref, val, x, y, r, footprint=fp, fields=dict(fields or {}), **kw)
    p.x, p.y = x, y            # keep exact (already on grid)
    if n1:
        sh.connect(p, '1', n1)
    if n2:
        sh.connect(p, '2', n2)
    return p


def R(sh, ref, val, x, y, n1, n2, horiz=False, size='0603', prec=False, **kw):
    text, fp, fields = res(val, size, prec)
    fn = rh if horiz else rv
    return fn(sh, 'Device:R', ref, text, x, y, n1, n2, fp, fields, **kw)


def C(sh, ref, val, volt, size, x, y, n1, n2, horiz=False, **kw):
    text, fp, fields = cap(val, volt, size)
    fn = rh if horiz else rv
    return fn(sh, 'Device:C', ref, text, x, y, n1, n2, fp, fields, **kw)


def div(sh, rtop, vtop, rbot, vbot, x, y, top, mid, bot, tap=-1, top_kw=None, bot_kw=None, bot_part=None):
    """Stacked two-element divider, top pin at (x, y); the middle node is tapped
    sideways (tap=+1 right, -1 left) to a label so it is shown once."""
    R(sh, rtop, vtop, x, y, top, None, **(top_kw or {}))
    if bot_part:
        bot_part(x, y + g(3))
    else:
        R(sh, rbot, vbot, x, y + g(3), None, bot, **(bot_kw or {}))
    ym = y + g(3)
    sh.junction(x, ym)
    sh.wire(x, ym, x + tap * g(2), ym)
    sh.label(mid, x + tap * g(2), ym, 0 if tap > 0 else 180)


def route(sh, a, b, lane):
    """Wire from point a to point b through a vertical lane at x = lane."""
    sh.wire_path([a, (lane, a[1]), (lane, b[1]), b])


def TP(sh, ref, net, x, y, label=None):
    """Test point pad; (x, y) is the connection point (body above, net label below)."""
    p = sh.add('Connector:TestPoint', ref, label or net, x, y, 0, footprint=FP['TP'],
               fields={'MPN': 'Test pad (bare copper)', 'Manufacturer': '-'}, in_bom=False)
    p.x, p.y = x, y
    if net:
        sh.connect(p, '1', net)
    return p


def barrier(sh, x, y0, y1, gaps=()):
    """Red dashed isolation barrier line, broken around symbols in `gaps` [(ya, yb)]."""
    ys = [y0]
    for a, b in gaps:
        ys += [a, b]
    ys.append(y1)
    for a, b in zip(ys[0::2], ys[1::2]):
        sh.line([(x, a), (x, b)], color=RED, width=0.6)


# ---------------------------------------------------------------------------
# Phase sheet (instantiated twice)
# ---------------------------------------------------------------------------
PH = {   # per-instance reference designators: (phase 1, phase 2)
    'U_DRV': ('U1', 'U2'), 'Q_HS': ('Q3', 'Q5'), 'Q_LS': ('Q4', 'Q6'),
    'R_GHS': ('R15', 'R16'), 'R_GLS': ('R13', 'R14'), 'R_PDH': ('R1', 'R3'), 'R_PDL': ('R2', 'R4'),
    'R_BST': ('R9', 'R10'), 'D_BST': ('D1', 'D2'), 'D_CLMP': ('D3', 'D4'), 'C_BST': ('C7', 'C9'),
    'C_VDDB': ('C8', 'C10'), 'C_VDDB2': ('C12', 'C14'), 'C_VDDI': ('C11', 'C13'),
    'R_DT': ('R21', 'R22'), 'C_DT': ('C30', 'C31'),
    'C_HF1': ('C1', 'C3'), 'C_HF2': ('C2', 'C4'), 'C_HF3': ('C15', 'C17'), 'C_HF4': ('C16', 'C18'),
    'C_CT1': ('C32', 'C34'), 'C_CT2': ('C33', 'C35'),
    'R_SNH': ('R23', 'R25'), 'C_SNH': ('C36', 'C38'), 'R_SNL': ('R24', 'R26'), 'C_SNL': ('C37', 'C39'),
    'D_TVH': ('D10', 'D12'), 'D_TVL': ('D11', 'D13'),
    'NT_HS': ('NT1', 'NT3'), 'NT_LS': ('NT2', 'NT4'),
    'RS': ('RS2', 'RS3'), 'U_OCP': ('U9', 'U10'), 'R_LIM': ('R27', 'R28'), 'C_OCP': ('C40', 'C41'),
    'R_ALRT': ('R29', 'R30'),
    'U_AMC': ('U6', 'U7'), 'R_AINP': ('R31', 'R33'), 'R_AINN': ('R32', 'R34'), 'C_AIN': ('C42', 'C51'),
    'C_AH1': ('C43', 'C52'), 'C_AH2': ('C44', 'C53'), 'C_AH3': ('C45', 'C54'),
    'C_AL1': ('C46', 'C55'), 'C_AL2': ('C47', 'C56'), 'C_AL3': ('C48', 'C57'), 'C_AL4': ('C49', 'C58'),
    'C_AH4': ('C50', 'C59'),
    'TP_SW': ('TP3', 'TP4'), 'TP_GH': ('TP5', 'TP7'), 'TP_GL': ('TP6', 'TP8'), 'TP_IMON': ('TP9', 'TP10'),
}


def refs(key):
    return list(PH[key])


def build_phase(sh):
    xb = g(50)                       # isolation barrier
    sh.text('LV CONTROL DOMAIN  (GND_ISO)', g(8), g(8), size=2.0, bold=True)
    sh.text('HV POWER DOMAIN  (PGND)', g(56), g(8), size=2.0, bold=True)
    sh.text('Isolation barrier: 2.5 mm keep-out on all layers. Only U_DRV (Si8274) and U_AMC (AMC3301) cross it.',
            g(8), g(11), size=1.27)

    # ---- isolated gate driver -------------------------------------------
    yd = g(40)
    drv = sh.add('ECE533:Si8274', refs('U_DRV'), 'Si8274GB1-IS1', xb, yd,
                 footprint=FP.get('SOIC16', 'Package_SO:SOIC-16_3.9x9.9mm_P1.27mm'),
                 fields={'MPN': 'Si8274GB1-IS1', 'Manufacturer': 'Skyworks', 'LCSC': 'C17368638'},
                 nets={'VDDI': '~+5V_ISO', 'PWM': '>PWM:input', 'EN': '>EN:input', 'DT': 'DT',
                       'GNDI': '~GND_ISO',
                       'VDDA': 'BOOT', 'VOA': 'HS_DRV', 'GNDA': 'SW_K',
                       'VDDB': '~+5V_PWR', 'VOB': 'LS_DRV', 'GNDB': 'PGND_K'})
    # LV-side support: VDDI decoupling, dead-time resistor (DT = 2.02*R + 7.77 ns -> 20 ns)
    C(sh, refs('C_VDDI'), '100n', '50V', '0603', g(36), g(33), '~+5V_ISO', '~GND_ISO')
    R(sh, refs('R_DT'), '6.04k', g(30), g(41), 'DT', '~GND_ISO')
    C(sh, refs('C_DT'), '100n', '50V', '0603', g(24), g(41), 'DT', '~GND_ISO')
    sh.text('Dead time ~20 ns:\nDT = 2.02 x R_DT[k] + 7.77 ns', g(18), g(48), size=1.0)
    sh.box(g(16), g(28), g(64), g(52), 'Isolated half-bridge driver')

    # ---- bootstrap (HV) -------------------------------------------------
    yb = g(22)
    R(sh, refs('R_BST'), '4.7', g(58), yb, '~+5V_PWR', None, horiz=True)
    d = sh.add('Device:D_Schottky', refs('D_BST'), 'SS110HL', g(63.5), yb, 180,
               footprint=FP['SOD123F'], fields={'MPN': 'SS110HL-TP', 'Manufacturer': 'MCC', 'LCSC': 'C19996385'})
    d.x, d.y = g(63.5), yb
    sh.wire(g(61), yb, g(62), yb)            # R pin2 -> D anode
    sh.wire(g(65), yb, g(68), yb)            # D cathode -> BOOT node
    sh.junction(g(68), yb)
    sh.wire(g(68), yb, g(71), yb)
    sh.label('BOOT', g(71), yb, 0)
    cb = C(sh, refs('C_BST'), '100n', '50V', '0603', g(68), yb, None, 'SW_K')
    z = sh.add('Device:D_Zener', refs('D_CLMP'), '5.1V', g(73), yb + 3.81, 270,
               footprint=FP['SOD123'], fields={'MPN': 'BZT52C5V1-TP', 'Manufacturer': 'MCC', 'LCSC': 'C78728'})
    z.x, z.y = g(73), yb + 3.81
    sh.wire(g(71), yb, g(73), yb)
    sh.connect(z, '2', 'SW_K')
    sh.text('Zener keeps HS VGS <= 6 V when SW rings\nbelow PGND during dead time', g(58), g(31), size=1.0)
    sh.box(g(55), g(17), g(80), g(34), 'Bootstrap (high side)')

    # VDDB decoupling (low-side driver supply, returns to Kelvin ground)
    C(sh, refs('C_VDDB'), '100n', '50V', '0603', g(70), g(40), '~+5V_PWR', 'PGND_K')
    C(sh, refs('C_VDDB2'), '10u', '10V', '0805', g(75), g(40), '~+5V_PWR', 'PGND_K')
    sh.text('VDDB decoupling at U_DRV pins 11/9', g(66), g(47.5), size=1.0)

    # ---- half bridge ----------------------------------------------------
    xq = g(100)
    yh, yl = g(30), g(52)
    fet_fp, fet_f = part('EPC2304', 'EPC', 'ECE533_Mods:EPC2304_QFN-7_3x5mm', 'C6549215')
    qh = sh.add('ECE533:EPC2304', refs('Q_HS'), 'EPC2304', xq, yh, footprint=fet_fp, fields=dict(fet_f))
    ql = sh.add('ECE533:EPC2304', refs('Q_LS'), 'EPC2304', xq, yl, footprint=fet_fp, fields=dict(fet_f))
    sh.connect(qh, 'D', '~VBUS')
    sh.connect(ql, 'S', '~PGND')
    (sx, sy), _ = qh.pin_at('S')
    (dx_, dy_), _ = ql.pin_at('D')
    sh.wire(sx, sy, dx_, dy_)
    ysw = g(41)
    sh.junction(xq, ysw)
    sh.wire(xq, ysw, g(106), ysw)
    sh.hlabel('SW', g(106), ysw, 0, 'output')
    TP(sh, refs('TP_SW'), 'SW', g(104), g(36), 'SW')

    def gate(q, rg_key, rg_val, pd_key, drv_net, k_net, tp_key):
        (gx_, gy), _ = q.pin_at('G')
        (kx, ky), _ = q.pin_at('SK')
        xr = gx_ - g(8)                       # R_g pin1
        R(sh, refs(rg_key), rg_val, xr, gy, drv_net, None, horiz=True)
        sh.wire(xr + g(3), gy, gx_, gy)       # R_g pin2 -> G
        xj = gx_ - g(2)
        sh.junction(xj, gy)
        R(sh, refs(pd_key), '51k', xj, gy + g(2), None, None)
        sh.wire(xj, gy, xj, gy + g(2))
        # SK (Kelvin source, pad 2) -> pull-down bottom -> Kelvin net label
        sh.wire(kx, ky, kx - g(1), ky)
        sh.wire(kx - g(1), ky, kx - g(1), gy + g(6))
        sh.wire(xj, gy + g(5), xj, gy + g(6))
        sh.wire(xj, gy + g(6), kx - g(1), gy + g(6))
        sh.junction(kx - g(1), gy + g(6))
        sh.wire(kx - g(1), gy + g(6), kx - g(1), gy + g(7))
        sh.label(k_net, kx - g(1), gy + g(7), 270)
        TP(sh, refs(tp_key), None, xj, gy - g(2), tp_key[3:] + ' gate')
        sh.wire(xj, gy - g(2), xj, gy)

    gate(qh, 'R_GHS', '2', 'R_PDH', 'HS_DRV', 'SW_K', 'TP_GH')
    gate(ql, 'R_GLS', '5.6', 'R_PDL', 'LS_DRV', 'PGND_K', 'TP_GL')
    sh.text('Gate loops: route each gate trace over its\nKelvin return (SK = EPC2304 pad 2)', g(81), g(58), size=1.0)

    # Kelvin net-ties at pad 2 of each FET
    nt_fp, nt_f = part('NetTie', '-', 'NETTIE')
    nh = sh.add('Device:NetTie_2', refs('NT_HS'), 'NetTie', g(107), g(48), footprint=nt_fp, fields=dict(nt_f), in_bom=False)
    nh.x, nh.y = g(107), g(48)
    sh.connect(nh, '1', 'SW_K')
    sh.connect(nh, '2', 'SW')
    nl = sh.add('Device:NetTie_2', refs('NT_LS'), 'NetTie', g(107), g(54), footprint=nt_fp, fields=dict(nt_f), in_bom=False)
    nl.x, nl.y = g(107), g(54)
    sh.connect(nl, '1', 'PGND_K')
    sh.connect(nl, '2', '~PGND')
    sh.text('Kelvin net-ties:\nplace at Q pad 2', g(103), g(58), size=1.0)
    sh.box(g(80), g(17), g(112), g(62), 'Half-bridge (bottom side)')

    # ---- snubbers / clamps (DNP) ----------------------------------------
    xs = g(116)
    sn_r = dict(dnp=True)
    R(sh, refs('R_SNH'), '2.2', xs, g(22), '~VBUS', None, size='1206', **sn_r)
    C(sh, refs('C_SNH'), '1n', '200V', '0805', xs, g(25), None, 'SW', **sn_r)
    R(sh, refs('R_SNL'), '2.2', xs, g(44), 'SW', None, size='1206', **sn_r)
    C(sh, refs('C_SNL'), '1n', '200V', '0805', xs, g(47), None, '~PGND', **sn_r)
    tvs_fp, tvs_f = part('SMBJ85A', 'Littelfuse', 'SMB')
    for key, y, a, b in (('D_TVH', g(23.5), '~VBUS', 'SW'), ('D_TVL', g(45.5), 'SW', '~PGND')):
        t = sh.add('Device:D_TVS', refs(key), 'SMBJ85A', g(122), y, 270, footprint=tvs_fp,
                   fields=dict(tvs_f), dnp=True)
        t.x, t.y = g(122), y
        sh.connect(t, '1', a)
        sh.connect(t, '2', b)
    sh.text('DNP: fit only if measured\nV_DS overshoot needs it', g(114), g(55), size=1.0)
    sh.box(g(113), g(17), g(128), g(60), 'D-S snubber / clamp (DNP)')

    # ---- HF input capacitors (at the FET pads, bottom side) -------------
    for i, key in enumerate(('C_HF1', 'C_HF2', 'C_HF3', 'C_HF4')):
        C(sh, refs(key), '2.2u', '100V', '0805', g(132 + 6 * i), g(22), '~VBUS', '~PGND')
    C(sh, refs('C_CT1'), '10n', '100V', '0603', g(134), g(36), '~VBUS', '>CT:passive')
    C(sh, refs('C_CT2'), '10n', '100V', '0603', g(140), g(36), '>CT:passive', '~PGND')
    sh.text('Commutation loop: caps tight against the half-bridge,\n'
            'return on L3 directly above (target 1.3-1.8 nH)', g(131), g(30), size=1.0)
    sh.text('Center-tap (EMI): shield / heatsink return via FB1', g(131), g(46), size=1.0)
    sh.box(g(130), g(17), g(156), g(50), 'HF input decoupling')

    # ---- current sense --------------------------------------------------
    ys0 = g(68)
    rs_fp, rs_f = part('CSS2H-2512R-L500F', 'Bourns', 'SHUNT2512', 'C2073667')
    rs = sh.add('Device:R_Shunt', refs('RS'), '0.5m', g(100), ys0 + g(2), footprint=rs_fp, fields=dict(rs_f))
    rs.x, rs.y = g(100), ys0 + g(2)
    sh.connect(rs, '1', '>LX:input')
    sh.connect(rs, '4', '~+24V')
    sh.connect(rs, '2', 'ISP')
    sh.connect(rs, '3', 'HGND_ISN')
    sh.text('Kelvin sense pads (pins 2/3)\nto U_OCP and U_AMC', g(103), g(76), size=1.0)

    u_ocp = sh.add('ECE533:INA301', refs('U_OCP'), 'INA301A3', g(124), g(80),
                   fields={'MPN': 'INA301A3IDGKR', 'Manufacturer': 'TI', 'LCSC': 'C2861552'},
                   nets={'IN+': 'ISP', 'IN-': 'HGND_ISN', 'VS': '~+5V_PWR', 'GND': '~PGND',
                         'RESET': '~PGND', 'LIMIT': 'OCP_LIM', 'OUT': 'IMON', '~{ALERT}': 'OCP_N'})
    C(sh, refs('C_OCP'), '100n', '50V', '0603', g(134), g(70), '~+5V_PWR', '~PGND')
    R(sh, refs('R_LIM'), '22.6k', g(112), g(84), 'OCP_LIM', '~PGND')
    R(sh, refs('R_ALRT'), '10k', g(140), g(74), '~+5V_PWR', '>OCP_N:output')
    TP(sh, refs('TP_IMON'), 'IMON', g(148), g(74), 'IMON')
    sh.text('Cycle-by-cycle limit 36 A peak: V_LIMIT = 80 uA x 22.6k = 1.81 V\n'
            '= 100 V/V x 0.5 mOhm x 36 A.  RESET low = transparent mode.', g(98), g(93), size=1.0)
    sh.box(g(96), g(64), g(156), g(97), 'Phase current sense / fast OCP (HV)')

    # ---- isolated current amplifier (crosses barrier) -------------------
    ya = g(84)
    amc = sh.add('ECE533:AMC3301', refs('U_AMC'), 'AMC3301', xb, ya, mirror=True,
                 footprint='Package_SO:SOIC-16W_7.5x10.3mm_P1.27mm',
                 fields={'MPN': 'AMC3301DWER', 'Manufacturer': 'TI', 'LCSC': 'C2869778'},
                 nets={'INP': 'AINP', 'INN': 'AINN', 'HGND': 'HGND_ISN', 'DCDC_HGND': 'HGND_ISN',
                       'DCDC_OUT': 'HDCDC', 'HLDO_IN': 'HDCDC', 'HLDO_OUT': 'HLDO',
                       'VDD': '~+5V_ISO', 'GND': '~GND_ISO', 'DCDC_GND': '~GND_ISO',
                       'DCDC_IN': 'LDCDC', 'LDO_OUT': 'LDCDC', 'DIAG': 'NC',
                       'OUTP': '>I_P:output', 'OUTN': '>I_N:output'})
    # HV-side input filter and supplies (right of barrier, referenced to HGND_ISN)
    R(sh, refs('R_AINP'), '10', g(76), g(87), 'ISP', 'AINP', horiz=True)
    R(sh, refs('R_AINN'), '10', g(76), g(93), 'HGND_ISN', 'AINN', horiz=True)
    C(sh, refs('C_AIN'), '1n', '50V', '0603', g(88), g(88), 'AINP', 'AINN')
    C(sh, refs('C_AH1'), '1u', '25V', '0603', g(66), g(68), 'HDCDC', 'HGND_ISN')
    C(sh, refs('C_AH4'), '100n', '50V', '0603', g(71), g(68), 'HDCDC', 'HGND_ISN')
    C(sh, refs('C_AH2'), '1u', '25V', '0603', g(76), g(68), 'HLDO', 'HGND_ISN')
    C(sh, refs('C_AH3'), '100n', '50V', '0603', g(81), g(68), 'HLDO', 'HGND_ISN')
    sh.text('High side floats at VOUT (HGND_ISN = shunt VOUT side), supplied by the AMC3301 internal isolated DC/DC.',
            g(52), g(98), size=1.0)
    # LV side
    C(sh, refs('C_AL1'), '1u', '25V', '0603', g(20), g(68), '~+5V_ISO', '~GND_ISO')
    C(sh, refs('C_AL2'), '100n', '50V', '0603', g(25), g(68), '~+5V_ISO', '~GND_ISO')
    C(sh, refs('C_AL3'), '1u', '25V', '0603', g(30), g(68), 'LDCDC', '~GND_ISO')
    C(sh, refs('C_AL4'), '100n', '50V', '0603', g(35), g(68), 'LDCDC', '~GND_ISO')
    sh.text('I_P - I_N = 8.2 x V_shunt = 4.1 mV/A to LTC3861 ISNS\n(attenuated on the controller sheet)',
            g(18), g(96), size=1.0)
    sh.box(g(16), g(64), g(94), g(100), 'Isolated phase-current amplifier (AMC3301)')

    barrier(sh, xb, g(14), g(102), gaps=[(g(35), g(46)), (g(76), g(92))])



# ---------------------------------------------------------------------------
# Power stage: two phase sub-sheets, coupled inductor, output, OTP, EMI
# A3 drawing area used: x g(8)..g(160), y g(8)..g(100)  (title block bottom-right)
# ---------------------------------------------------------------------------
def phase_pins(n):
    return [('L', 'PWM', 'input', f'>PWM{n}:input'), ('L', 'EN', 'input', f'>EN{n}:input'), None,
            ('L', 'I_P', 'output', f'>I{n}_P:output'), ('L', 'I_N', 'output', f'>I{n}_N:output'),
            ('R', 'SW', 'output', f'SW{n}'), ('R', 'LX', 'input', f'LX{n}'), None,
            ('R', 'CT', 'passive', 'CT'), ('R', 'OCP_N', 'output', f'>OCP{n}_N:output')]


def build_power_stage(sh, phase, root_path):
    sh.text('POWER STAGE (HV domain). Bottom side: FETs, drivers, HF caps.  Top side: L1, output caps, terminals.',
            g(8), g(8), size=1.778, bold=True)
    p1 = sh.sheet(phase, 'Phase 1', g(22), g(20), g(24), phase_pins(1), '4')
    p2 = sh.sheet(phase, 'Phase 2', g(22), g(46), g(24), phase_pins(2), '5')
    phase.inst_paths = [f'{root_path}/{p1.uuid}', f'{root_path}/{p2.uuid}']
    sh.text('Phase 1: U1, Q3 (HS), Q4 (LS), RS2, U6, U9\nPhase 2: U2, Q5 (HS), Q6 (LS), RS3, U7, U10\n'
            'Phases interleaved 180 deg (LTC3861 PHSMD = GND)', g(10), g(70), size=1.27)

    # coupled inductor: winding A = SW1 (pin 4) -> LX1 (pin 1), B = SW2 (pin 3) -> LX2 (pin 2)
    lfp, lf = part('ERUC23-3R2K', 'TDK', 'ECE533_Mods:TDK_ERUC23')
    sh.add('ECE533:ERUC23', 'L1', 'ERUC23-3R2K', g(72), g(30), footprint=lfp, fields=dict(lf),
           nets={'A in': 'SW1', 'B in': 'SW2', 'A out': 'LX1', 'B out': 'LX2'})
    sh.text('L1 (top side): 5.84 uH self, k = 0.714,\n1.84 mOhm per winding.\n'
            'SW copper <= 0.096 mOhm: short, wide,\n>= 50 vias to the L1 pads.', g(62), g(38), size=1.0)
    sh.box(g(58), g(18), g(88), g(48), 'Coupled inductor')

    # output capacitors and terminals
    for i in range(6):
        C(sh, f'C{60 + i}', '10u', '50V', '1210', g(96 + 4 * i), g(22), '~+24V', '~PGND')
    pfp, pf = part('EEH-ZA1V101P', 'Panasonic', 'CPOL_SMD')
    for i in range(2):
        rv(sh, 'Device:C_Polarized', f'C{66 + i}', '100u/35V', g(122 + 6 * i), g(22), '~+24V', '~PGND',
           pfp, dict(pf))
    sh.text('Output ripple << 1 %: 3.2 A p-p at 500 kHz (interleaved).', g(94), g(32), size=1.0)
    jfp, jf = part('74650194R', 'Wurth Elektronik', 'REDCUBE')
    j2 = sh.add('Connector_Generic:Conn_01x01', 'J2', 'VOUT+', g(144), g(22), footprint=jfp, fields=dict(jf))
    sh.connect(j2, '1', '~+24V')
    j6 = sh.add('Connector_Generic:Conn_01x01', 'J6', 'VOUT-', g(144), g(28), footprint=jfp, fields=dict(jf))
    sh.connect(j6, '1', '~PGND')
    sh.text('J2/J6: REDCUBE M4 blind-hole', g(136), g(32), size=1.0)
    sh.power('+24V', g(94), g(36))
    sh.wire(g(94), g(36), g(96), g(36))
    sh.flag(g(96), g(36))
    TP(sh, 'TP2', '~+24V', g(102), g(38), 'VOUT')
    sh.box(g(92), g(16), g(156), g(42), 'Output (24 V / 46 A)')

    # over-temperature sensor (HV side, near the LS FETs)
    nfp, nf = part('NCP18XH103F03RB', 'Murata', 'R0603', 'C13564')
    div(sh, 'R40', '5.49k', None, None, g(98), g(54), '~+5V_PWR', 'NTC', None,
        bot_part=lambda x, y: rv(sh, 'Device:Thermistor_NTC', 'RT1', '10k B3380', x, y, None, '~PGND',
                                 nfp, dict(nf)))
    sh.add('ECE533:TLV3012', 'U14', 'TLV3012', g(118), g(60),
           fields={'MPN': 'TLV3012AIDBVR', 'Manufacturer': 'TI', 'LCSC': 'C62505'},
           nets={'+': 'NTC', '-': 'OTP_REF', 'REF': 'OTP_REF', 'OUT': '>OTP_N:output',
                 'V+': '~+5V_PWR', 'V-': '~PGND'})
    R(sh, 'R41', '1M', g(106), g(51), 'NTC', 'OTP_N', horiz=True)
    C(sh, 'C68', '100n', '50V', '0603', g(130), g(52), '~+5V_PWR', '~PGND')
    sh.text('OTP 80 C: R_NTC(80 C) = 1.71k -> 1.242 V (= TLV3012 REF).\n'
            'OTP_N low when hot; latched on the LV side. R41: ~10 C hysteresis.\n'
            'RT1 on the bottom between Q4 and Q6, on PGND copper.', g(94), g(70), size=1.0)
    sh.box(g(92), g(46), g(156), g(78), 'Over-temperature (HV)')

    # center-tap EMI path: phase CT caps -> FB1 -> heatsink / shield
    ffp, ff = part('BLM18KG601SN1D', 'Murata', 'L0603')
    fb = sh.add('Device:FerriteBead_Small', 'FB1', '600R@100MHz', g(64), g(58), footprint=ffp, fields=dict(ff))
    fb.x, fb.y = g(64), g(58)
    sh.connect(fb, '1', 'CT')
    sh.connect(fb, '2', 'HS_SHIELD')
    R(sh, 'R42', '0', g(70), g(60), 'HS_SHIELD', '~PGND', dnp=True)
    mfp, mf = part('M3 plated hole', '-', 'MH_M3')
    for i in range(4):
        h = sh.add('Mechanical:MountingHole_Pad', f'H{i + 1}', 'M3', g(62 + 5 * i), g(70),
                   footprint=mfp, fields=dict(mf), in_bom=False)
        h.x, h.y = g(62 + 5 * i), g(70)
        sh.connect(h, '1', 'HS_SHIELD')
    sh.text('Heatsink Z60-12.7B (bottom) on H1-H4, insulating TIM on the FETs.\n'
            'CM path: shield / heatsink -> FB1 -> center-tap caps (169 / 596 MHz).\n'
            'R42 (DNP): option to tie the heatsink to PGND.', g(58), g(78), size=1.0)
    sh.box(g(56), g(52), g(88), g(86), 'EMI center-tap and heatsink')


# ---------------------------------------------------------------------------
# Input protection: fuse, TVS, reverse FET, hot-swap, precise 82 V OVP, bulk
# ---------------------------------------------------------------------------
def build_input(sh):
    sh.text('INPUT PROTECTION (HV domain):  J1 -> F1 -> D6 -> Q2 (reverse) -> RS1 -> Q1 (hot-swap) -> VBUS',
            g(8), g(8), size=1.778, bold=True)
    y0 = g(32)
    jfp, jf = part('74650194R', 'Wurth Elektronik', 'REDCUBE')
    j1 = sh.add('Connector_Generic:Conn_01x01', 'J1', 'DC+ 72V', g(14), y0, mirror=True,
                ref_pos=(g(7), y0 - 1.27), val_pos=(g(7), y0 + 1.27),
                footprint=jfp, fields=dict(jf))
    j3 = sh.add('Connector_Generic:Conn_01x01', 'J3', 'DC- return', g(14), g(44), mirror=True,
                ref_pos=(g(7), g(44) - 1.27), val_pos=(g(7), g(44) + 1.27),
                footprint=jfp, fields=dict(jf))
    (j3x, j3y), _ = j3.pin_at('1')
    sh.wire(j3x, j3y, j3x + g(4), j3y)
    sh.power('PGND', j3x + g(4), j3y)      # PGND is driven by U8 DCDC_HGND (power out): no flag
    ffp, ff = part('0456025.ER', 'Littelfuse', 'FUSE456', 'C315877')
    (jx, jy), _ = j1.pin_at('1')
    rh(sh, 'Device:Fuse', 'F1', '25A', jx + g(1), y0, None, None, ffp, dict(ff))
    sh.wire(jx, jy, jx + g(1), y0)
    xn = jx + g(7)                           # VIN_FUSED node
    sh.wire(jx + g(4), y0, xn, y0)
    sh.junction(xn, y0)
    tfp, tf = part('SMDJ85CA', 'Littelfuse', 'SMC', 'C1978008')
    t = sh.add('Device:D_TVS', 'D6', 'SMDJ85CA', xn, y0 + 3.81 + g(1), 270, footprint=tfp, fields=dict(tf))
    t.x, t.y = xn, y0 + 3.81 + g(1)
    sh.wire(xn, y0, xn, y0 + g(1))
    sh.connect(t, '2', '~PGND')
    sh.text('D6 bidirectional: does not\nconduct on reverse polarity', jx - g(1), g(40), size=1.0)

    # reverse-polarity FET Q2 (S = input side) with photovoltaic gate drive
    qfp, qf = part('IPT015N10N5', 'Infineon', 'TOLL', 'C108964')
    q2 = sh.add('Transistor_FET:IPT015N10N5', 'Q2', 'IPT015N10N5', xn + g(4), y0 - g(1), 270,
                footprint=qfp, fields=dict(qf))
    (sx, sy), _ = q2.pin_at('S')
    (dx_, dy_), _ = q2.pin_at('D')
    (gx_, gy_), _ = q2.pin_at('G')
    sh.wire(xn, y0, sx, sy)
    vom = sh.add('ECE533:VOM1271', 'U13', 'VOM1271T', xn - g(4), g(20),
                 fields={'MPN': 'VOM1271T', 'Manufacturer': 'Vishay', 'LCSC': 'C146286'},
                 nets={'LED K': '~PGND'})
    (vx, vy), _ = vom.pin_at('VO+')
    (mx, my), _ = vom.pin_at('VO-')
    sh.wire_path([(vx, vy), (gx_, vy), (gx_, gy_)])
    sh.wire_path([(mx, my), (mx + g(1), my), (mx + g(1), y0)])
    sh.junction(mx + g(1), y0)
    R(sh, 'R43', '330', g(8), g(20), '~+5V_PWR', None, horiz=True)
    (ax, ay), _ = vom.pin_at('LED A')
    sh.wire(g(11), g(20), ax, ay)
    sh.text('U13 LED runs from +5V_PWR, which exists only with correct polarity:\n'
            'reversed input -> Q2 stays off, its body diode blocks (100 V).', g(8), g(13), size=1.0)
    sh.box(g(6), g(15), g(40), g(48), 'Fuse, TVS, reverse polarity')

    # VIN_PROT node
    yp = dy_
    xp = g(46)
    sh.wire(dx_, dy_, xp, yp)
    sh.junction(g(42), yp)
    sh.wire(g(42), yp, g(42), yp - g(3))
    sh.hlabel('VIN_PROT', g(42), yp - g(3), 90, 'output')
    sh.flag(g(44), yp)
    sh.junction(g(44), yp)
    C(sh, 'C70', '1u', '100V', '0805', g(44), yp + g(1), None, '~PGND')
    sh.wire(g(44), yp, g(44), yp + g(1))
    # RS1 horizontal, Kelvin taps on top
    sfp, sf = part('CSS2H-2512R-2L00F', 'Bourns', 'SHUNT2512')
    rs = sh.add('Device:R_Shunt', 'RS1', '2m', xp + g(2), yp, 90, footprint=sfp, fields=dict(sf))
    rs.x, rs.y = xp + g(2), yp
    (p1x, _), _ = rs.pin_at('1')
    sh.wire(xp, yp, p1x, yp)
    sh.connect(rs, '2', 'HSC_VIN')
    sh.connect(rs, '3', 'HSC_SENSE')
    (p4x, p4y), _ = rs.pin_at('4')
    # Q1 pass FET: D left, S right, G below
    q1 = sh.add('Transistor_FET:IPT015N10N5', 'Q1', 'IPT015N10N5', p4x + g(3), yp + g(1), 90,
                footprint=qfp, fields=dict(qf))
    (d1x, d1y), _ = q1.pin_at('D')
    (s1x, s1y), _ = q1.pin_at('S')
    (g1x, g1y), _ = q1.pin_at('G')
    sh.wire(p4x, p4y, d1x, d1y)
    sh.wire(s1x, s1y, s1x + g(4), s1y)
    sh.power('VBUS', s1x + g(4), s1y)
    sh.flag(s1x + g(4), s1y)
    R(sh, 'R44', '10', g1x, g1y + g(1), None, 'HSC_GATE')
    sh.wire(g1x, g1y, g1x, g1y + g(1))
    sh.text('Q1, Q2: 100 V 1.5 mOhm TOLL.  RS1 2 mOhm (Kelvin):\nI_limit 55 mV -> 27.5 A, breaker 105 mV -> 53 A',
            g(46), g(20), size=1.0)

    # LM5069-2 hot-swap controller
    hx, hy = g(62), g(56)
    sh.add('Power_Management:LM5069MM-2', 'U12', 'LM5069MM-2', hx, hy,
           footprint='Package_SO:MSOP-10_3x3mm_P0.5mm',
           fields={'MPN': 'LM5069MM-2/NOPB', 'Manufacturer': 'TI'},
           nets={'VIN': 'HSC_VIN', 'SENSE': 'HSC_SENSE', 'GATE': 'HSC_GATE', 'OUT': '~VBUS',
                 'UVLO': 'UVLO', 'OVLO': 'OVLO', 'GND': '~PGND',
                 'TIMER': 'TIMER', 'PWR': 'PWR', 'PGD': 'BUS_PG'})
    C(sh, 'C71', '1u', '100V', '0805', g(50), g(40), 'HSC_VIN', '~PGND')
    (cx, cy), _ = sh.parts[-1].pin_at('1')
    sh.flag(cx + g(2), cy - g(1))
    sh.wire(cx + g(2), cy - g(1), cx + g(4), cy - g(1))
    sh.label('HSC_VIN', cx + g(4), cy - g(1), 0)
    div(sh, 'R45', '95.3k', 'R46', '4.12k', g(44), g(46), 'VIN_PROT', 'UVLO', '~PGND', top_kw={'size': '1206'})
    C(sh, 'C72', '470n', '25V', '0603', g(78), g(54), 'TIMER', '~PGND')
    R(sh, 'R47', '13.0k', g(82), g(54), 'PWR', '~PGND')
    R(sh, 'R48', '10k', g(88), g(48), '~+5V_PWR', '>BUS_PG:output')
    sh.text('UVLO on 62.3 V / off 60.3 V: R45 = 2 V / 21 uA, R46 = 2.5 V x R45 / 57.5 V\n'
            'P_FET limit ~50 W: R_PWR = 1.3e5 x R_S x (P - 1.18 mV x V_DS) = 13.0k\n'
            'C72 470 nF: start ~12 ms, insertion delay ~0.34 s.  -2: auto-retry, 0.5 % duty',
            g(42), g(68), size=1.0)
    sh.box(g(40), g(15), g(96), g(76), 'Hot-swap / inrush (LM5069-2)')

    # precise 82 V OVP comparator -> LM5069 OVLO (separate divider from the unclamped input)
    div(sh, 'R49', '649k', 'R50', '10.0k', g(106), g(20), 'VIN_PROT', 'OVP_SNS', '~PGND',
        top_kw={'size': '1206', 'prec': True}, bot_kw={'prec': True})
    sh.add('ECE533:TLV3012', 'U22', 'TLV3012', g(122), g(28),
           fields={'MPN': 'TLV3012AIDBVR', 'Manufacturer': 'TI', 'LCSC': 'C62505'},
           nets={'+': 'OVP_SNS', '-': 'OVP_REF', 'REF': 'OVP_REF', 'OUT': 'OVP_CMP',
                 'V+': '~+5V_PWR', 'V-': '~PGND'})
    R(sh, 'R51', '1.69M', g(112), g(18), 'OVP_SNS', 'OVP_CMP', horiz=True)
    C(sh, 'C73', '100n', '50V', '0603', g(134), g(20), '~+5V_PWR', '~PGND')
    R(sh, 'R52', '10k', g(132), g(32), 'OVP_CMP', 'OVLO', horiz=True)
    R(sh, 'R53', '10k', g(142), g(34), 'OVLO', '~PGND')
    sh.text('Trip 81.9 V (1.242 V x 65.9), release ~80 V.\nTolerance ~80.7-83.1 V (> 79.2 V line max).\n'
            'R49: 1206 for voltage rating. Dividers 0.1 %.', g(102), g(40), size=1.0)
    sh.box(g(100), g(14), g(150), g(48), 'Input OVP 82 V (precise, drives LM5069 OVLO)')

    # bulk capacitors on VBUS
    efp, ef = part('EGXF161ELL111MK25S', 'Chemi-Con', 'CPOL_EGXF', 'C1598290')
    for i, ref in enumerate(('C5', 'C6')):
        rv(sh, 'Device:C_Polarized', ref, '110u/160V', g(106 + 7 * i), g(58), '~VBUS', '~PGND', efp, dict(ef))
    TP(sh, 'TP1', '~VBUS', g(126), g(60), 'VBUS')
    TP(sh, 'TP11', '~PGND', g(132), g(60), 'PGND')
    sh.text('Bulk (top side): ESR damps cable resonance.\nCharged through Q1 under the power limit.',
            g(102), g(68), size=1.0)
    sh.box(g(100), g(52), g(150), g(74), 'VBUS bulk')


# ---------------------------------------------------------------------------
def build_aux(sh):
    sh.text('AUX SUPPLY + FAN (HV domain): LM5012 makes +5V_PWR (5.2 V) from VIN_PROT',
            g(8), g(8), size=1.778, bold=True)
    hx, hy = g(44), g(28)
    buck = sh.add('ECE533:LM5012', 'U11', 'LM5012DDAR', hx, hy,
                  fields={'MPN': 'LM5012DDAR', 'Manufacturer': 'TI', 'LCSC': 'C6079494'},
                  nets={'EN/UVLO': 'BUCK_EN', 'RON': 'BUCK_RON', 'BST': 'BUCK_BST', 'SW': 'BUCK_SW',
                        'FB': 'BUCK_FB', 'PGOOD': 'NC', 'GND': '~PGND'})
    (vx, vy), _ = buck.pin_at('VIN')
    sh.hlabel('VIN_PROT', g(12), vy, 180, 'input')
    sh.wire(g(12), vy, vx, vy)
    for i, (ref, val, volt, size) in enumerate((('C74', '2.2u', '100V', '0805'), ('C75', '2.2u', '100V', '0805'),
                                                ('C76', '100n', '100V', '0603'))):
        x = g(18 + 5 * i)
        sh.junction(x, vy)
        C(sh, ref, val, volt, size, x, vy, None, '~PGND')
    div(sh, 'R54', '200k', 'R55', '10k', g(14), g(33), 'VIN_PROT', 'BUCK_EN', '~PGND', top_kw={'size': '1206'})
    R(sh, 'R56', '32.4k', g(30), g(36), 'BUCK_RON', '~PGND')
    C(sh, 'C77', '2.2n', '50V', '0603', g(56), g(18), 'BUCK_BST', 'BUCK_SW')
    dfp, df = part('VS-30BQ100TRPBF', 'Vishay', 'SMC')
    d5 = sh.add('Device:D_Schottky', 'D5', '30BQ100', g(62), g(32.5), 270, footprint=dfp, fields=dict(df))
    d5.x, d5.y = g(62), g(32.5)
    sh.connect(d5, '1', 'BUCK_SW')
    sh.connect(d5, '2', '~PGND')
    lfp, lf = part('XAL7070-333MEB', 'Coilcraft', 'L7070')
    rh(sh, 'Device:L', 'L2', '33uH', g(66), g(26), 'BUCK_SW', None, lfp, dict(lf))
    sh.wire(g(69), g(26), g(98), g(26))
    sh.power('+5V_PWR', g(74), g(24))
    sh.wire(g(74), g(24), g(74), g(26))
    sh.junction(g(74), g(26))
    sh.flag(g(76), g(24))
    sh.wire(g(74), g(24), g(76), g(24))
    for i, (ref, val, volt, size) in enumerate((('C78', '22u', '10V', '1206'), ('C79', '22u', '10V', '1206'),
                                                ('C80', '100n', '50V', '0603'))):
        x = g(80 + 4 * i)
        sh.junction(x, g(26))
        C(sh, ref, val, volt, size, x, g(26), None, '~PGND')
    div(sh, 'R57', '33.2k', 'R58', '10k', g(98), g(26), None, 'BUCK_FB', '~PGND', tap=-1)
    R(sh, 'R59', '100k', g(66), g(38), 'BUCK_SW', 'BUCK_RI', horiz=True)
    C(sh, 'C81', '4.7n', '50V', '0603', g(76), g(38), 'BUCK_RI', '~+5V_PWR')
    C(sh, 'C82', '47n', '50V', '0603', g(84), g(38), 'BUCK_RI', 'BUCK_FB')
    TP(sh, 'TP12', '~+5V_PWR', g(104), g(26), '+5V_PWR')
    sh.text('VOUT = 1.2 V x (1 + 33.2k / 10k) = 5.18 V.   f_sw ~400 kHz: R_RON = VOUT x 2500 / f[kHz] = 32.4k\n'
            'EN/UVLO starts at ~31.5 V (1.5 V x 21).   R59/C81/C82: type-3 ripple injection (verify per datasheet).\n'
            'Budget: 0.62 A running, 0.97 A at fan start (2.5 A part).', g(10), g(48), size=1.0)
    sh.box(g(8), g(14), g(110), g(54), '+5V_PWR buck (LM5012, 100 V input)')

    # fan switch and connector
    yf = g(74)
    sh.add('ECE533:TPS2553', 'U21', 'TPS2553DBVR', g(30), yf,
           fields={'MPN': 'TPS2553DBVR', 'Manufacturer': 'TI', 'LCSC': 'C55266'},
           nets={'IN': '~+5V_PWR', 'EN': 'FAN_EN', 'ILIM': 'FAN_ILIM', 'OUT': 'FAN_5V',
                 '~{FAULT}': 'FAN_FLT_N', 'GND': '~PGND'})
    R(sh, 'R93', '10k', g(16), g(64), '~+5V_PWR', 'FAN_EN')
    C(sh, 'C83', '1u', '25V', '0603', g(10), g(64), '~+5V_PWR', '~PGND')
    R(sh, 'R60', '25.5k', g(16), g(78), 'FAN_ILIM', '~PGND')
    R(sh, 'R61', '10k', g(42), g(64), '~+5V_PWR', 'FAN_FLT_N')
    TP(sh, 'TP13', 'FAN_FLT_N', g(46), g(68), 'FAN_FLT')
    C(sh, 'C84', '10u', '10V', '0805', g(52), g(74), 'FAN_5V', '~PGND')
    jfp, jf = part('43650-0400', 'Molex', 'J_MICROFIT4', 'C277684')
    sh.add('Connector_Generic:Conn_01x04', 'J5', 'FAN Micro-Fit', g(80), g(76), footprint=jfp, fields=dict(jf),
           nets={'1': 'FAN_5V', '2': '~PGND', '3': 'TACH', '4': 'FAN_PWM'})
    R(sh, 'R62', '10k', g(60), g(64), '~+5V_PWR', 'TACH')
    R(sh, 'R63', '10k', g(64), g(64), 'FAN_5V', 'FAN_PWM', dnp=True)
    TP(sh, 'TP14', 'TACH', g(68), g(68), 'TACH')
    efp, ef = part('TPD4E05U06DQAR', 'TI', 'USON10', 'C138714')
    sh.add('Power_Protection:TPD4E05U06DQA', 'D7', 'TPD4E05U06', g(100), g(76), footprint=efp, fields=dict(ef),
           nets={'D1+': 'FAN_5V', 'D1-': 'TACH', 'D2+': 'FAN_PWM', 'D2-': 'NC', '3': '~PGND', '8': '~PGND',
                 '6': 'NC', '7': 'NC', '9': 'NC', '10': 'NC'})
    sh.text('Limit 1.0 A typ (0.94-1.09 A): I_OS = 23950 / R_ILIM^0.977 (R in k).  Fan: 0.7 A start, 0.35 A run.\n'
            'PWM pin open = full speed (Sanyo 9GA); R63 DNP.   J5: 1 +5V, 2 GND, 3 TACH (open collector), 4 PWM.',
            g(10), g(90), size=1.0)
    sh.box(g(8), g(58), g(112), g(96), 'Fan output (separately current-limited)')


# ---------------------------------------------------------------------------
def build_isolation(sh):
    xb = g(80)
    sh.text('HV POWER DOMAIN (PGND)', g(12), g(8), size=2.0, bold=True)
    sh.text('LV CONTROL DOMAIN (GND_ISO)', g(84), g(8), size=2.0, bold=True)
    sh.text('All barrier crossings except the per-phase Si8274 drivers and AMC3301 amplifiers (phase sheets).',
            g(12), g(11), size=1.27)

    sh.add('ECE533:NME1S0505SC', 'PS1', 'NME1S0505SC', xb, g(22),
           fields={'MPN': 'NME1S0505SC', 'Manufacturer': 'Murata', 'LCSC': 'C39128444'},
           nets={'+VIN': '~+5V_PWR', '-VIN': '~PGND', '+VOUT': '~+5V_ISO', '-VOUT': '~GND_ISO'})
    C(sh, 'C85', '1u', '25V', '0603', g(64), g(18), '~+5V_PWR', '~PGND')
    C(sh, 'C86', '10u', '10V', '0805', g(94), g(18), '~+5V_ISO', '~GND_ISO')
    C(sh, 'C87', '100n', '50V', '0603', g(98), g(18), '~+5V_ISO', '~GND_ISO')
    TP(sh, 'TP15', '~+5V_ISO', g(104), g(20), '+5V_ISO')
    TP(sh, 'TP16', '~GND_ISO', g(108), g(20), 'GND_ISO')
    sh.text('1 W, 1 kVDC. LV load 130 mA typ / 176 mA max.\nUnregulated: check VOUT at load in bring-up.',
            g(84), g(28), size=1.0)
    sh.box(g(58), g(14), g(114), g(32), 'PS1 - isolated control supply')

    def iso(ref, y, a1, a2, b1, b2, c1, c2):
        sh.add('ECE533:SI86S620', ref, 'SI86S620BC-IS', xb, y,
               fields={'MPN': 'SI86S620BC-IS', 'Manufacturer': 'Skyworks', 'LCSC': 'C7363570'},
               nets={'VDD1': '~+5V_PWR', 'GND1': '~PGND', 'A1': a1, 'A2': a2,
                     'VDD2': '~+5V_ISO', 'GND2': '~GND_ISO', 'B1': b1, 'B2': b2})
        C(sh, c1, '100n', '50V', '0603', g(62), y - g(3), '~+5V_PWR', '~PGND')
        C(sh, c2, '100n', '50V', '0603', g(98), y - g(3), '~+5V_ISO', '~GND_ISO')
    iso('AT1', g(40), '>OCP1_N:input', '>OCP2_N:input', '>OCP1_ISO_N:output', '>OCP2_ISO_N:output', 'C88', 'C89')
    iso('AT2', g(53), '>OTP_N:input', '>BUS_PG:input', '>OTP_ISO_N:output', '>BUS_PG_ISO:output', 'C90', 'C91')
    sh.text('AT1: per-phase cycle-by-cycle OCP flags (INA301 ALERT, active low).\n'
            'AT2: OTP flag (latched on LV side) and hot-swap bus-good (LM5069 PGD).', g(58), g(59), size=1.0)
    sh.box(g(56), g(34), g(114), g(63), 'HV -> LV flags (SI86S620BC: 2 forward / 0 reverse)')

    ya = g(82)
    sh.add('Isolator_Analog:AMC3330', 'U8', 'AMC3330', xb, ya,
           footprint='Package_SO:SOIC-16W_7.5x10.3mm_P1.27mm',
           fields={'MPN': 'AMC3330DWER', 'Manufacturer': 'TI', 'LCSC': 'C2999368'},
           nets={'INP': 'VS_DIV', 'INN': '~PGND', 'HGND': '~PGND', 'DCDC_HGND': '~PGND',
                 'DCDC_OUT': 'V_HDCDC', 'HLDO_IN': 'V_HDCDC', 'HLDO_OUT': 'V_HLDO',
                 'VDD': '~+5V_ISO', 'GND': '~GND_ISO', 'DCDC_GND': '~GND_ISO',
                 'DCDC_IN': 'V_LDCDC', 'LDO_OUT': 'V_LDCDC', 'DIAG': 'NC',
                 'OUTP': '>VFB_P:output', 'OUTN': '>VFB_N:output'})
    div(sh, 'R64', '290k', 'R65', '10.0k', g(40), g(74), '~+24V', 'VS_DIV', '~PGND',
        top_kw={'prec': True}, bot_kw={'prec': True})
    C(sh, 'C92', '100p', '50V', '0603', g(48), g(77), 'VS_DIV', '~PGND')
    for i, (ref, val, n) in enumerate((('C93', '1u', 'V_HDCDC'), ('C94', '100n', 'V_HDCDC'),
                                       ('C95', '1u', 'V_HLDO'), ('C96', '100n', 'V_HLDO'))):
        C(sh, ref, val, '25V' if val == '1u' else '50V', '0603', g(14 + 5 * i), g(70), n, '~PGND')
    for i, (ref, val, n) in enumerate((('C97', '1u', '~+5V_ISO'), ('C98', '100n', '~+5V_ISO'),
                                       ('C99', '1u', 'V_LDCDC'), ('C100', '100n', 'V_LDCDC'))):
        C(sh, ref, val, '25V' if val == '1u' else '50V', '0603', g(98 + 5 * i), g(70), n, '~GND_ISO')
    sh.text('VOUT x 10/300 = 0.8 V at 24 V (0.9 V at 27 V; +-1 V range).\n'
            'VFB_P - VFB_N = 2 x V_in = 1.6 V at 24 V -> LTC3861 VSNSP1/N1.', g(14), g(91), size=1.0)
    sh.box(g(12), g(66), g(120), g(97), 'Output voltage feedback (AMC3330, isolated)')

    barrier(sh, xb, g(14), g(99), gaps=[(g(18), g(27)), (g(36), g(45)), (g(49), g(58)), (g(73), g(91))])


# ---------------------------------------------------------------------------
def build_controller(sh, fault, root_path):
    sh.text('CONTROLLER (LV domain, GND_ISO): LTC3861, 2-phase voltage mode, 250 kHz/phase, 180 deg',
            g(8), g(8), size=1.778, bold=True)
    xu, yu = g(60), g(56)
    sh.add('ECE533:LTC3861', 'U5', 'LTC3861IUHE#PBF', xu, yu,
           fields={'MPN': 'LTC3861IUHE#PBF', 'Manufacturer': 'Analog Devices', 'LCSC': 'C686466'},
           nets={'VINSNS': '~+5V_ISO', 'CONFIG': '~GND_ISO', 'FREQ': 'FREQ', 'CLKIN': '~+5V_ISO',
                 'PHSMD': '~GND_ISO', 'RUN1': 'RUN_OK', 'RUN2': 'RUN_OK',
                 'TRACK/SS1': 'SS', 'TRACK/SS2': 'SS',
                 'VSNSP1': 'VSP', 'VSNSN1': 'VSN', 'VSNSP2': '~GND_ISO', 'VSNSN2': '~GND_ISO',
                 'ISNS1P': 'IS1P', 'ISNS1N': 'IS1N', 'ISNS2P': 'IS2P', 'ISNS2N': 'IS2N',
                 'ILIM1': 'ILIM1', 'ILIM2': 'ILIM2',
                 'PWM1': 'PWM1_RAW', 'PWMEN1': '>EN1:output', 'PWM2': 'PWM2_RAW', 'PWMEN2': '>EN2:output',
                 'PGOOD1': 'PGOOD', 'PGOOD2': 'NC', 'CLKOUT': 'NC',
                 'VSNSOUT1': 'VSOUT', 'FB1': 'FB', 'COMP1': 'COMP',
                 'VSNSOUT2': 'NC', 'FB2': '~+5V_ISO', 'COMP2': 'COMP', 'IAVG': 'IAVG',
                 'VCC': '~+5V_ISO', 'SGND': '~GND_ISO'})
    C(sh, 'C101', '1u', '25V', '0603', g(70), g(30), '~+5V_ISO', '~GND_ISO')
    C(sh, 'C102', '100n', '50V', '0603', g(74), g(30), '~+5V_ISO', '~GND_ISO')
    # PWMEN pins have an internal pull-up only; datasheet requires a resistor to SGND
    R(sh, 'R94', '10k', g(78), g(30), 'EN1', '~GND_ISO')
    R(sh, 'R95', '10k', g(82), g(30), 'EN2', '~GND_ISO')

    # set-up parts
    R(sh, 'R66', '26.1k', g(12), g(18), 'FREQ', '~GND_ISO')
    C(sh, 'C103', '100n', '50V', '0603', g(17), g(18), 'SS', '~GND_ISO')
    R(sh, 'R67', '52.3k', g(22), g(18), 'ILIM1', '~GND_ISO')
    R(sh, 'R68', '52.3k', g(27), g(18), 'ILIM2', '~GND_ISO')
    C(sh, 'C104', '100p', '50V', '0603', g(32), g(18), 'IAVG', '~GND_ISO')
    sh.text('R66: f ~255 kHz (250 kHz minimum clamp).   C103: soft-start 0.1u x 0.6 V / 2.5 uA = 24 ms.\n'
            'R67/R68: ILIM = (18.5 x 30 mV + 0.5 V) / 20 uA -> 28 A/phase.   FB2 = VCC: channel 2 is slave.',
            g(10), g(27), size=1.0)
    sh.box(g(8), g(14), g(46), g(30), 'Frequency, soft-start, current limit')

    # VOUT feedback scaling from AMC3330 (k = 5.97/(10+5.97) = 0.374)
    R(sh, 'R69', '10.0k', g(10), g(38), '>VFB_P:input', 'VSP', horiz=True, prec=True)
    R(sh, 'R70', '5.97k', g(20), g(40), 'VSP', '~GND_ISO', prec=True)
    R(sh, 'R71', '10.0k', g(10), g(46), '>VFB_N:input', 'VSN', horiz=True, prec=True)
    R(sh, 'R72', '5.97k', g(28), g(48), 'VSN', '~GND_ISO', prec=True)
    sh.text('VSNSP1 - VSNSN1 = 0.374 x 1.6 V = 0.598 V\n-> VOUT = 24.1 V', g(10), g(54), size=1.0)
    sh.box(g(8), g(33), g(38), g(58), 'VOUT sense scaling')

    # current-sense attenuators (AMC3301 outputs, 4.1 mV/A -> 1.07 mV/A)
    def isns(n, y):
        b = 4 * (n - 1)
        R(sh, f'R{73 + b}', '7.50k', g(10), y, f'>I{n}_P:input', f'IS{n}P', horiz=True, prec=True)
        R(sh, f'R{74 + b}', '2.67k', g(20), y + g(2), f'IS{n}P', '~GND_ISO', prec=True)
        R(sh, f'R{75 + b}', '7.50k', g(10), y + g(9), f'>I{n}_N:input', f'IS{n}N', horiz=True, prec=True)
        R(sh, f'R{76 + b}', '2.67k', g(28), y + g(11), f'IS{n}N', '~GND_ISO', prec=True)
        C(sh, f'C{104 + n}', '1n', '50V', '0603', g(34), y + g(2), f'IS{n}P', f'IS{n}N')
    isns(1, g(64))
    isns(2, g(84))
    sh.text('k = 2.67 / (7.5 + 2.67) = 0.263: 28 A -> 30 mV at ISNS', g(10), g(102), size=1.0)
    sh.box(g(8), g(60), g(40), g(104), 'Phase-current scaling (from AMC3301)')

    # type-III compensation (starting values)
    # series R-C pairs touch pin-to-pin, so each internal node needs no label
    R(sh, 'R81', '10k', g(88), g(46), 'VSOUT', 'FB', horiz=True)
    R(sh, 'R82', '1k', g(88), g(50), 'VSOUT', None, horiz=True)
    C(sh, 'C107', '2.2n', '50V', '0603', g(94), g(50), None, 'FB', horiz=True)
    sh.wire(g(91), g(50), g(94), g(50))
    R(sh, 'R83', '20k', g(88), g(56), 'FB', None, horiz=True)
    C(sh, 'C108', '4.7n', '50V', '0603', g(94), g(56), None, 'COMP', horiz=True)
    sh.wire(g(91), g(56), g(94), g(56))
    C(sh, 'C109', '100p', '50V', '0603', g(89.5), g(60), 'FB', 'COMP', horiz=True)
    sh.text('Type III, starting values only. Crossover target\n10-15 kHz (AMC3330 delay). VINSNS = +5V_ISO\n'
            '(no line feed-forward; gain +-10 % over VIN).', g(86), g(64), size=1.0)
    sh.box(g(84), g(40), g(110), g(72), 'Voltage loop compensation')

    # cycle-by-cycle latches + PWM gating
    def cbc(n, y):
        sh.add('ECE533:74LVC1G74', f'U{15 + n}', 'SN74LVC1G74', g(124), y,
               fields={'MPN': 'SN74LVC1G74DCTR', 'Manufacturer': 'TI', 'LCSC': 'C840104'},
               nets={'D': '~+5V_ISO', 'CLK': f'PWM{n}_RAW', '~{PRE}': '~+5V_ISO',
                     '~{CLR}': f'>OCP{n}_ISO_N:input', 'Q': f'CBC{n}', '~{Q}': 'NC',
                     'VCC': '~+5V_ISO', 'GND': '~GND_ISO'})
        sh.add('74xGxx:74LVC1G08', f'U{18 + n}', '74LVC1G08', g(148), y,
               footprint=FP['SOT23-5'], fields={'MPN': 'SN74LVC1G08DBVR', 'Manufacturer': 'TI', 'LCSC': 'C7666'},
               nets={'1': f'PWM{n}_RAW', '2': f'CBC{n}', '4': f'>PWM{n}:output',
                     'VCC': '~+5V_ISO', 'GND': '~GND_ISO'})
        C(sh, f'C{109 + 2 * n}', '100n', '50V', '0603', g(114), y - g(8), '~+5V_ISO', '~GND_ISO')
        C(sh, f'C{110 + 2 * n}', '100n', '50V', '0603', g(138), y - g(8), '~+5V_ISO', '~GND_ISO')
    cbc(1, g(28))
    cbc(2, g(52))
    sh.text('PWM rising edge sets the latch; the isolated INA301 alert clears it,\n'
            'forcing PWM low (HS off, LS on) for the rest of that cycle.', g(114), g(64), size=1.0)
    sh.box(g(112), g(14), g(162), g(68), 'Cycle-by-cycle current limit (per phase)')

    # nested sheet: fault latch, OVP, common fault line, LEDs, rack I/O
    s = sh.sheet(fault, 'Fault logic and rack I/O', g(124), g(76), g(30),
                 [('L', 'VSOUT', 'input', 'VSOUT'), ('L', 'PGOOD', 'input', 'PGOOD'),
                  ('L', 'OTP_ISO_N', 'input', '>OTP_ISO_N:input'),
                  ('L', 'BUS_PG_ISO', 'input', '>BUS_PG_ISO:input'),
                  ('R', 'RUN_OK', 'output', 'RUN_OK')], '9')
    fault.inst_paths = [f'{root_path}/{s.uuid}']
    R(sh, 'R91', '10k', g(116), g(74), '~+5V_ISO', 'PGOOD')


def build_fault(sh):
    sh.text('FAULT LOGIC AND RACK I/O (LV domain, GND_ISO)', g(8), g(8), size=1.778, bold=True)
    yl = g(30)
    sh.hlabel('VSOUT', g(10), g(36), 180, 'input')
    sh.wire(g(10), g(36), g(14), g(36))
    sh.label('VSOUT', g(14), g(36), 0)
    sh.add('ECE533:TLV3012', 'U15', 'TLV3012', g(34), yl,
           fields={'MPN': 'TLV3012AIDBVR', 'Manufacturer': 'TI', 'LCSC': 'C62505'},
           nets={'+': 'OVP_REF', '-': 'VSOUT', 'REF': 'OVP_REFOUT', 'OUT': 'OVP_N',
                 'V+': '~+5V_ISO', 'V-': '~GND_ISO'})
    div(sh, 'R84', '10k', 'R85', '11.8k', g(20), g(17), 'OVP_REFOUT', 'OVP_REF', '~GND_ISO')
    C(sh, 'C119', '100n', '50V', '0603', g(44), g(18), '~+5V_ISO', '~GND_ISO')
    sh.add('74xGxx:74LVC1G08', 'U25', '74LVC1G08', g(62), yl,
           footprint=FP['SOT23-5'], fields={'MPN': 'SN74LVC1G08DBVR', 'Manufacturer': 'TI', 'LCSC': 'C7666'},
           nets={'1': '>OTP_ISO_N:input', '2': 'OVP_N', '4': 'FLT_SET_N', 'VCC': '~+5V_ISO', 'GND': '~GND_ISO'})
    sh.add('ECE533:74LVC1G74', 'U18', 'SN74LVC1G74', g(90), yl,
           fields={'MPN': 'SN74LVC1G74DCTR', 'Manufacturer': 'TI', 'LCSC': 'C840104'},
           nets={'D': '~GND_ISO', 'CLK': '~GND_ISO', '~{PRE}': 'FLT_SET_N', '~{CLR}': 'POR_N',
                 'Q': 'FAULT', '~{Q}': 'FAULT_N', 'VCC': '~+5V_ISO', 'GND': '~GND_ISO'})
    div(sh, 'R86', '100k', None, None, g(76), g(36), '~+5V_ISO', 'POR_N', None,
        bot_part=lambda x, y: C(sh, 'C115', '1u', '25V', '0603', x, y, None, '~GND_ISO'))
    C(sh, 'C116', '100n', '50V', '0603', g(100), g(18), '~+5V_ISO', '~GND_ISO')
    C(sh, 'C117', '100n', '50V', '0603', g(72), g(18), '~+5V_ISO', '~GND_ISO')
    sh.text('Output OVP 27 V: VSOUT = 0.675 V; ref = 1.242 V x 11.8 / 21.8 = 0.672 V.\n'
            'Fault latch set by OVP or OTP (U25 ANDs the active-low flags);\n'
            'cleared only at power-up (POR RC ~0.1 s). Input power cycle = reset.', g(10), g(50), size=1.0)
    sh.box(g(8), g(13), g(110), g(56), 'Latched faults: output OVP 27 V, OTP 80 C')

    # RUN_OK common fault line
    bfp, bf = part('BAT54W-7-F', 'Diodes Inc', 'SOT323')
    R(sh, 'R87', '100k', g(122), g(16), '~+5V_ISO', 'RUN_OK')
    C(sh, 'C118', '10n', '50V', '0603', g(128), g(24), 'RUN_OK', '~GND_ISO')
    sh.hlabel('RUN_OK', g(150), g(24), 0, 'output')
    sh.wire(g(140), g(24), g(150), g(24))
    sh.label('RUN_OK', g(140), g(24), 180)
    for i, (ref, k) in enumerate((('D15', 'FAULT_N'), ('D16', '>BUS_PG_ISO:input'))):
        d = sh.add('Diode:BAT54W', ref, 'BAT54W', g(126), g(32 + 5 * i), footprint=bfp, fields=dict(bf))
        d.x, d.y = g(126), g(32 + 5 * i)
        sh.connect(d, 'A', 'RUN_OK')
        sh.connect(d, 'K', k)
    R(sh, 'R88', '1k', g(118), g(46), 'EN_IN', 'RUN_OK', horiz=True)
    sh.text('RUN_OK (LTC3861 RUN1/RUN2) is pulled low by the fault latch (D15),\n'
            'hot-swap bus not good (D16) or J4 EN low (R88).\n'
            'RUN low -> PWM three-state -> PWMEN low -> both Si8274 drivers off.', g(114), g(50), size=1.0)
    sh.box(g(112), g(12), g(160), g(56), 'Common fault / enable line')

    # indicators and rack interface
    lfp = FP['LED0603']
    R(sh, 'R89', '1.5k', g(12), g(68), 'FAULT', None, horiz=True)
    led = sh.add('Device:LED', 'D9', 'RED FAULT', g(15) + 3.81, g(68), 180, footprint=lfp,
                 ref_pos=(g(15), g(68) - 5.08), val_pos=(g(15), g(68) - 2.79),
                 fields={'MPN': 'LTST-C191KRKT', 'Manufacturer': 'Lite-On'})
    led.x, led.y = g(15) + 3.81, g(68)        # anode touches R89 pin 2
    sh.connect(led, 'K', '~GND_ISO')
    R(sh, 'R90', '1.5k', g(12), g(78), '~+5V_ISO', None, horiz=True)
    led2 = sh.add('Device:LED', 'D8', 'GREEN PGOOD', g(15) + 3.81, g(78), 180, footprint=lfp,
                  ref_pos=(g(15), g(78) - 5.08), val_pos=(g(15), g(78) - 2.79),
                  fields={'MPN': 'LTST-C191KGKT', 'Manufacturer': 'Lite-On'})
    led2.x, led2.y = g(15) + 3.81, g(78)
    sh.connect(led2, 'K', 'LED_PK')
    nfp, nf = part('2N7002LT1G', 'onsemi', 'SOT23')
    sh.add('Transistor_FET:2N7002', 'Q7', '2N7002', g(40), g(86), footprint=nfp, fields=dict(nf),
           nets={'G': 'PGOOD', 'S': '~GND_ISO', 'D': 'LED_PK'})
    sh.hlabel('PGOOD', g(10), g(96), 180, 'input')
    sh.wire(g(10), g(96), g(14), g(96))
    sh.label('PGOOD', g(14), g(96), 0)
    sh.add('Transistor_FET:2N7002', 'Q8', '2N7002', g(64), g(86), footprint=nfp, fields=dict(nf),
           nets={'G': 'FAULT', 'S': '~GND_ISO', 'D': 'FAULT_OUT_N'})
    R(sh, 'R92', '100', g(48), g(70), 'PGOOD', 'PGOOD_OUT', horiz=True)
    sh.text('LEDs 0603, ~2 mA. Q7 lights PGOOD when the LTC3861 PGOOD1 is high.', g(10), g(102), size=1.0)
    sh.box(g(8), g(60), g(76), g(106), 'Indicators')
    jfp, jf = part('105313-1206', 'Molex', 'J_NANOFIT6', 'C17656275')
    sh.add('Connector_Generic:Conn_01x06', 'J4', 'RACK I/O Nano-Fit', g(136), g(76), footprint=jfp, fields=dict(jf),
           nets={'1': '~GND_ISO', '2': 'EN_IN', '3': 'PGOOD_OUT', '4': 'FAULT_OUT_N', '5': '~GND_ISO', '6': 'NC'})
    efp, ef = part('TPD4E05U06DQAR', 'TI', 'USON10', 'C138714')
    sh.add('Power_Protection:TPD4E05U06DQA', 'D14', 'TPD4E05U06', g(104), g(80), footprint=efp, fields=dict(ef),
           nets={'D1+': 'EN_IN', 'D1-': 'PGOOD_OUT', 'D2+': 'FAULT_OUT_N', 'D2-': 'NC', '3': '~GND_ISO',
                 '8': '~GND_ISO', '6': 'NC', '7': 'NC', '9': 'NC', '10': 'NC'})
    sh.text('J4 (isolated): 1 GND_ISO, 2 EN (open/high = run), 3 PGOOD (open drain via 100R),\n'
            '4 FAULT_N (open drain, low = latched fault), 5 GND_ISO, 6 spare.', g(82), g(92), size=1.0)
    sh.box(g(80), g(60), g(150), g(97), 'Rack interface J4 (isolated)')


# ---------------------------------------------------------------------------
def build_root(sh, kids):
    sh.text('ECE533 MeGaNism - 72 V -> 24 V, 46 A, 1.1 kW, 2-phase interleaved coupled-inductor GaN buck',
            g(8), g(7), size=2.5, bold=True)
    sh.text('Credit-card PCB (85.6 x 54 mm, 4 layers). Stage 2 schematic. Design notes: docs/design/.',
            g(8), g(10.5), size=1.5)
    inp, ps, aux, iso, ctl = kids
    # sheet pins with net None are wired explicitly below (block-diagram style)
    s_in = sh.sheet(inp, 'Input protection', g(8), g(18), g(26),
                    [('R', 'VIN_PROT', 'output', None), ('R', 'BUS_PG', 'output', 'BUS_PG')], '2')
    s_aux = sh.sheet(aux, 'Aux supply and fan', g(8), g(26), g(26),
                     [('R', 'VIN_PROT', 'input', None)], '6')
    ps_l = ['PWM1', 'EN1', 'PWM2', 'EN2', None, 'I1_P', 'I1_N', 'I2_P', 'I2_N']
    s_ps = sh.sheet(ps, 'Power stage (2 phases)', g(62), g(18), g(28),
                    [None if n is None else ('L', n, 'output' if n.startswith('I') else 'input', None) for n in ps_l]
                    + [('R', 'OCP1_N', 'output', None), ('R', 'OCP2_N', 'output', None),
                       ('R', 'OTP_N', 'output', None)], '3')
    iso_l = ['OCP1_N', 'OCP2_N', 'OTP_N', 'BUS_PG', None,
             'OCP1_ISO_N', 'OCP2_ISO_N', 'OTP_ISO_N', 'BUS_PG_ISO', 'VFB_P', 'VFB_N']
    s_iso = sh.sheet(iso, 'Isolation barrier', g(100), g(41), g(28),
                     [None if n is None else ('L', n, 'output' if ('ISO' in n or 'VFB' in n) else 'input',
                                              'BUS_PG' if n == 'BUS_PG' else None) for n in iso_l], '7')
    ctl_r = ['PWM1', 'EN1', 'PWM2', 'EN2', None, 'I1_P', 'I1_N', 'I2_P', 'I2_N', None,
             'OCP1_ISO_N', 'OCP2_ISO_N', 'OTP_ISO_N', 'BUS_PG_ISO', 'VFB_P', 'VFB_N']
    s_ctl = sh.sheet(ctl, 'Controller (LV)', g(18), g(36), g(26),
                     [None if n is None else ('R', n, 'input' if (n.startswith('I') or 'ISO' in n or 'VFB' in n)
                                              else 'output', None) for n in ctl_r], '8')

    def pin(ref, name):
        x, y, _, _ = ref.pin_pos[name]
        return (x, y)

    # input protection -> aux supply
    a, b = pin(s_in, 'VIN_PROT'), pin(s_aux, 'VIN_PROT')
    route(sh, a, b, a[0] + g(3))
    sh.label('VIN_PROT', a[0] + g(1), a[1], 0)
    # controller <-> power stage: one lane per signal, lanes step right
    for i, n in enumerate([x for x in ps_l if x]):
        route(sh, pin(s_ctl, n), pin(s_ps, n), g(46 + 2 * i))
        sh.label(n, pin(s_ps, n)[0] - g(1), pin(s_ps, n)[1], 180)
    # power stage HV flags -> isolation (outer lane for the top signal)
    for i, n in enumerate(['OCP1_N', 'OCP2_N', 'OTP_N']):
        route(sh, pin(s_ps, n), pin(s_iso, n), g(96 - 2 * i))
        sh.label(n, pin(s_ps, n)[0] + g(1), pin(s_ps, n)[1], 0)
    # isolation LV outputs -> controller (rows line up: straight wires)
    for n in ['OCP1_ISO_N', 'OCP2_ISO_N', 'OTP_ISO_N', 'BUS_PG_ISO', 'VFB_P', 'VFB_N']:
        sh.wire_path([pin(s_iso, n), pin(s_ctl, n)])
        sh.label(n, pin(s_ctl, n)[0] + g(1), pin(s_ctl, n)[1], 0)

    sh.text('HV power domain (PGND)', g(62), g(15.5), size=1.5, bold=True)
    sh.text('LV control domain (GND_ISO)', g(18), g(56.5), size=1.5, bold=True)
    sh.text('DOMAINS\n'
            '  HV power (PGND): input protection, power stage, aux supply + fan, HV side of isolation parts.\n'
            '  LV control (GND_ISO): controller, fault logic, LEDs, J4 rack I/O, LV side of isolation parts.\n'
            '  Barrier crossings: Si8274 x2, AMC3301 x2 (phase sheets); AMC3330, AT1, AT2, PS1 (isolation sheet).\n\n'
            'RAILS\n'
            '  VBUS 72 V (64.8-79.2 V) after hot-swap      +24V  24 V / 46 A output\n'
            '  +5V_PWR 5.2 V (LM5012): drivers, fan, PS1    +5V_ISO 5 V isolated (PS1): controller, logic\n\n'
            'PROTECTION\n'
            '  UVLO 62.3 / 60.3 V and OVP 81.9 V (LM5069 + U22); reverse polarity (Q2 + U13); TVS D6; F1 25 A.\n'
            '  OCP: 36 A peak cycle-by-cycle per phase (INA301), 28 A/phase average with hiccup (LTC3861).\n'
            '  Latched: output OVP 27 V, OTP 80 C. All faults -> RUN_OK. Latches clear on input power cycle.\n\n'
            'SHEETS: 2 Input protection | 3 Power stage (4, 5 = Phase 1, Phase 2) | 6 Aux supply + fan |\n'
            '        7 Isolation | 8 Controller (9 = Fault logic and rack I/O)',
            g(8), g(62), size=1.27)
    return [s_in, s_ps, s_aux, s_iso, s_ctl]


def main():
    root = Sheet('Overview and block diagram', 'ECE533_Guide.kicad_sch')
    inp = Sheet('Input protection and hot-swap', 'input_protection.kicad_sch')
    ps = Sheet('Power stage', 'power_stage.kicad_sch')
    phase = Sheet('Power phase (one instance per phase)', 'power_phase.kicad_sch')
    aux = Sheet('Aux supply (+5V_PWR) and fan', 'aux_supply_fan.kicad_sch')
    iso = Sheet('Isolation barrier crossings', 'isolation.kicad_sch')
    ctl = Sheet('Controller (LV)', 'controller.kicad_sch')
    flt = Sheet('Fault logic and rack I/O (LV)', 'fault_io.kicad_sch')
    root.inst_paths = ['/' + root.uuid]
    sheet_refs = build_root(root, [inp, ps, aux, iso, ctl])
    for sh, sref in zip([inp, ps, aux, iso, ctl], sheet_refs):
        sh.inst_paths = [f'/{root.uuid}/{sref.uuid}']
    build_input(inp)
    build_power_stage(ps, phase, ps.inst_paths[0])
    build_phase(phase)
    build_aux(aux)
    build_isolation(iso)
    build_controller(ctl, flt, ctl.inst_paths[0])
    build_fault(flt)
    for sh in (inp, ps, phase, aux, iso, ctl, flt):
        sh.write(os.path.join(OUT, sh.file))
    root.write(os.path.join(OUT, root.file), sheet_instances=True)
    print('ok')


if __name__ == '__main__':
    main()
