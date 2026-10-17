"""PowerModule: build PowerModule.kicad_pcb from the schematic netlist and place every part.

    kicad-cli sch export netlist -o pm.net kicad/PowerModule/PowerModule.kicad_sch
    python kicad/tools/pm_build.py pm.net

The power module only (report: ECE 533 Team MeGaNism, SolidWorks layout pp. 20-25):
  * left to right, as in the report: J4 control connector, isolators AT1/AT2 (+ PS1), a column of
    four 1EDN7550B drivers, the 2 x 2 EPC2304 block, the coupled inductor, then bulk caps and the
    REDCUBE terminals;
  * FETs and the input ceramics on the bottom (heatsink side), everything else on the top;
  * phase 1 above, phase 2 below, both at the inductor switch-node pads (y = 19.1 / 34.9 mm);
  * per phase: HS left, LS right, strips vertical, gate pads on the driver side.
ID-1 outline, 4 x 2 oz; copper planes per the report: L1 = 1st Cu plane, L2/L3 = interstitial
shield, L4 = 2nd Cu plane (MOSFET side). Coordinates: board mm from the top-left corner, top view.
"""
import json
import os
import sys

import pcbnew

import build_pcb as bp

HERE = os.path.dirname(os.path.abspath(__file__))
PRJ = os.path.normpath(os.path.join(HERE, '..', 'PowerModule'))
PCB = os.path.join(PRJ, 'PowerModule.kicad_pcb')
W, H = bp.W, bp.H
BAR = (16.3, 19.7)                          # isolation barrier band (J4 side | power side)
HS_X = (19.0, 79.0)                         # Z60-12.7B on the bottom, 60 x 60, 3 mm overhang top/bottom
HOLES = ((21.5, 4.0), (21.5, 50.0), (69.6, 18.0), (69.6, 36.0))
PH_Y = {1: 19.1, 2: 34.9}
HS_XC, LS_XC = 33.0, 39.6                   # FET centres
L1_C = (50.0, 30.95)
LV_REFS = {'J4', 'C11', 'C12'}
BARRIER_REFS = {'AT1', 'AT2', 'PS1'}
HV_SW = ('Net-(J1-Pin_1)', '/Gate_Drive/KS1', '/Gate_Drive/KS2')
LV_NETS = ('GND', '+5V', 'Net-(AT1-A1)', 'Net-(AT1-A2)', 'Net-(AT2-A1)', 'Net-(AT2-A2)')

DRV_X = 27.15
CELLS = [dict(u='U2', y=11.6, src='R13', snk='R14', inp='R5', inm='R6', c='C8', rv='R10'),
         dict(u='U1', y=17.0, src='R15', snk='R16', inp='R1', inm='R2', c='C7', rv='R9'),
         dict(u='U4', y=31.4, src='R19', snk='R20', inp='R3', inm='R4', c='C10', rv='R12'),
         dict(u='U3', y=38.6, src='R17', snk='R18', inp='R7', inm='R8', c='C9', rv='R11')]
PHASES = {1: dict(hs='Q3', ls='Q4', drv_h='U1', drv_l='U2', caps=('C1', 'C2')),
          2: dict(hs='Q6', ls='Q5', drv_h='U3', drv_l='U4', caps=('C3', 'C4'))}


def mechanics(board):
    dw, bf = pcbnew.Dwgs_User, pcbnew.B_Fab
    bp.rect_shape(board, HS_X[0], -3.0, HS_X[1], H + 3.0, dw)
    bp.text(board, 'Z60-12.7B heatsink (bottom), fins along x', (HS_X[0] + HS_X[1]) / 2, -1.6, dw, 1.0)
    bp.rect_shape(board, HS_XC - 3.2, PH_Y[1] - 2.6, LS_XC + 3.2, PH_Y[2] + 2.6, bf, 0.1)
    bp.text(board, 'pedestal 3.0 mm + insulating TIM', (HS_XC + LS_XC) / 2, 27.0, bf, 0.7, mirror=True)
    bp.rect_shape(board, HS_X[1], 3.0, HS_X[1] + 22.0, H - 3.0, dw)
    bp.text(board, 'fan duct / 9GA0405P6H001', HS_X[1] + 11.0, H / 2, dw, 1.0)
    bp.rect_shape(board, BAR[0], 0.0, BAR[1], H, pcbnew.Cmts_User, 0.1)
    bp.text(board, 'ISOLATION', (BAR[0] + BAR[1]) / 2, -1.5, pcbnew.Cmts_User, 0.8)


def barrier(board):
    """No copper in the barrier band on any layer; at PS1 it narrows to the gap between pins 2 and 3."""
    ps = board.FindFootprintByReference('PS1')
    p2 = [p for p in ps.Pads() if p.GetNumber() == '2'][0].GetBoundingBox()
    p3 = [p for p in ps.Pads() if p.GetNumber() == '3'][0].GetBoundingBox()
    gx0, gx1 = p2.GetRight() / 1e6 - bp.X0 + 0.05, p3.GetLeft() / 1e6 - bp.X0 - 0.05
    py = (p2.GetTop() / 1e6 - bp.Y0, p2.GetBottom() / 1e6 - bp.Y0)
    y0, y1 = py[0] - 1.6, py[1] + 1.6
    bp.keepout(board, BAR[0], -0.5, BAR[1], y0, 'ISOLATION_BARRIER_A')
    bp.keepout(board, gx0, y0, gx1, y1, 'ISOLATION_BARRIER_PS1')
    bp.keepout(board, BAR[0], y1, BAR[1], H + 0.5, 'ISOLATION_BARRIER_B')


def holes(board):
    for i, (x, y) in enumerate(HOLES, 1):
        f = bp.load_fp('MountingHole:MountingHole_3.2mm_M3')
        f.SetReference(f'H{i}')
        f.SetValue('M3 heatsink')
        f.SetBoardOnly(True)
        f.SetExcludedFromBOM(True)
        f.SetExcludedFromPosFiles(True)
        f.SetPosition(bp.V(x, y))
        f.Reference().SetVisible(False)
        f.Value().SetLayer(pcbnew.Cmts_User)
        board.Add(f)


def floor_plan(P):
    T, B = 'T', 'B'
    for ph, d in PHASES.items():
        y = PH_Y[ph]
        # FETs on the bottom, strips vertical, gate pad on the left (driver side), below the SK pad
        gate_left = lambda p, c: (p(1)[0] < c[0] - 2 and p(1)[1] > p(2)[1]
                                  and abs(p(3)[1] - p(5)[1]) < 0.01)
        P.fixed(d['hs'], B, HS_XC, y, cond=gate_left)
        P.fixed(d['ls'], B, LS_XC, y, cond=gate_left)
        # centre-tapped input ceramics in series, VBUS (HS) -> SHIELD -> PGND (LS), towards the
        # other phase; phase 1 below its FETs, phase 2 above
        cy = y + 3.9 if ph == 1 else y - 3.9
        left_first = lambda p, c: p(1)[0] < p(2)[0] - 1
        P.fixed(d['caps'][0], B, 35.0, cy, cond=left_first)
        P.fixed(d['caps'][1], B, 38.5, cy, cond=left_first)
    # coupled inductor (top): switch-node pads on the left over the FETs, pad 4 (SW1) on top
    P.fixed('L1', T, *L1_C, cond=lambda p, c: p(4)[0] < c[0] - 3 and p(4)[1] < p(3)[1])
    # REDCUBE terminals on the right edge: DC+ top, VOUT middle, DC- bottom
    for ref, y in (('J1', 9.0), ('J2', 27.0), ('J3', 45.0)):
        P.fixed(ref, T, 79.0, y)
    # bulk capacitors: input next to DC+, output next to the inductor output pads
    # (C6 '-' pin downwards, onto a PGND tongue cut through the VBUS strip)
    P.fixed('C6', T, 64.0, 4.6, cond=lambda p, c: abs(p(1)[0] - p(2)[0]) < 0.01 and p(2)[1] > p(1)[1] + 1)
    P.fixed('C5', T, 62.0, 46.6, cond=lambda p, c: p(1)[0] < p(2)[0] - 1)
    # control connector on the left edge, isolators and PS1 across the barrier
    P.fixed('PS1', T, 14.19, 27.0, cond=lambda p, c: p(1)[0] < p(4)[0] - 5 and abs(p(1)[1] - p(4)[1]) < 0.01)
    at_ok = lambda p, c: p(1)[0] < c[0] - 1 and p(1)[1] < p(4)[1]
    P.fixed('AT1', T, 18.0, 17.0, cond=at_ok)
    P.fixed('AT2', T, 18.0, 37.0, cond=at_ok)
    # gate drivers, one per FET, in a column left of the FET block (outputs face the FETs); the
    # high-side drivers sit level with their FET row, the low-side drivers on the outside
    out_right = lambda p, c: p(5)[0] > c[0] + 0.5 and p(6)[1] < p(4)[1]
    for d in CELLS:
        ux, uy = DRV_X, d['y']
        P.fixed(d['u'], T, ux, uy, cond=out_right)
        P.fixed(d['snk'], T, ux + 3.7, uy - 0.9, rot=180)      # pin 1 (gate) towards the FET
        P.fixed(d['src'], T, ux + 3.7, uy + 0.9, rot=180)
        P.fixed(d['inm'], T, ux - 3.85, uy - 0.9, rot=180)     # pin 1 (driver input) on the right
        P.fixed(d['inp'], T, ux - 3.85, uy + 0.9, rot=180)
        P.fixed(d['c'], T, ux + 1.6, uy + 2.65, rot=0)         # VDD | driver GND
        P.fixed(d['rv'], T, ux - 1.6, uy + 2.65, rot=0)        # D cathode | VDD
    # bootstrap / supply diodes and the PS1 output capacitors
    for ref, x, y in (('D2', DRV_X, 8.4), ('D1', 27.4, 22.4), ('D4', 27.4, 27.9), ('D3', DRV_X, 43.8)):
        P.fixed(ref, T, x, y, rot=0)
    P.fixed('C13', T, 26.3, 25.1, rot=0)
    P.fixed('C14', T, 29.7, 25.2, rot=0)


def place_j4(P):
    """Nano-Fit right-angle header on the left edge, mating face outwards, pins in a column."""
    f = P.fps['J4']
    for r in (0, 90, 180, 270):
        P.set(f, 'T', r, 0, 0)
        p1, p6 = P.pad_xy(f, 1), P.pad_xy(f, 6)
        c = P.court(f)
        if abs(p1[0] - p6[0]) < 0.01 and (c[0] + c[2]) / 2 < p1[0]:
            break
    c = P.court(f)
    P.set(f, 'T', r, 0.35 - c[0], 41.0 - (c[1] + c[3]) / 2)
    P.commit('J4', 'T')


def write_netclasses(pro):
    d = json.load(open(pro, encoding='utf-8'))
    ns = d.setdefault('net_settings', {})
    if not ns.get('classes'):
        ns['classes'] = [dict(name='Default', bus_width=12, clearance=0.15, diff_pair_gap=0.25,
                              diff_pair_via_gap=0.25, diff_pair_width=0.2, line_style=0,
                              microvia_diameter=0.3, microvia_drill=0.1, pcb_color='rgba(0, 0, 0, 0.000)',
                              priority=2147483647, schematic_color='rgba(0, 0, 0, 0.000)',
                              track_width=0.2, via_diameter=0.6, via_drill=0.3, wire_width=6)]
    base = dict(ns['classes'][0])
    classes = [c for c in ns['classes'] if c['name'] not in ('LV_ISO', 'HV_SW', 'GATE')]
    for name, extra in (('LV_ISO', dict(clearance=0.15, track_width=0.25)),
                        ('HV_SW', dict(clearance=0.25, track_width=0.5)),
                        ('GATE', dict(clearance=0.15, track_width=0.4))):
        c = dict(base)
        c.update(name=name, priority=len(classes), **extra)
        classes.append(c)
    ns['classes'] = classes
    pats = [dict(netclass='LV_ISO', pattern=n) for n in LV_NETS]
    pats += [dict(netclass='HV_SW', pattern=n) for n in HV_SW]
    pats += [dict(netclass='GATE', pattern=p) for p in ('/Gate_Drive/P??', 'Net-(U?-OUT_S*)')]
    ns['netclass_patterns'] = pats
    json.dump(d, open(pro, 'w', encoding='utf-8', newline='\n'), indent=2)


def main(net):
    bp.BAR = BAR
    comps, nets = bp.read_netlist(net)
    dom = {r: ('LV' if r in LV_REFS else 'B' if r in BARRIER_REFS else 'HV') for r in comps}
    with open(PCB, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('(kicad_pcb (version 20260206) (generator "pcbnew") (generator_version "10.0")\n)\n')
    board = pcbnew.LoadBoard(PCB)
    bp.setup_board(board)
    for lid, name in ((pcbnew.F_Cu, 'L1_Cu1'), (pcbnew.In1_Cu, 'L2_Shield'), (pcbnew.In2_Cu, 'L3_Shield'),
                      (pcbnew.B_Cu, 'L4_Cu2_FET')):
        board.SetLayerName(lid, name)
    bp.outline(board)
    mechanics(board)
    fps = bp.add_footprints(board, comps, nets)
    holes(board)
    P = bp.Placer(board, fps, comps, nets, dom)
    P.can_bottom = lambda ref: False        # only the FETs and the input ceramics go on the bottom
    for i, (x, y) in enumerate(HOLES, 1):   # screw heads (5.5 mm) on the top
        P.obst['T'].append((x - 2.9, y - 2.9, x + 2.9, y + 2.9, f'H{i}'))
    floor_plan(P)
    place_j4(P)
    P.auto_all(lambda ref: (8.0, 27.0, 'T') if dom[ref] == 'LV' else (28.0, 27.0, 'T'))
    barrier(board)
    board.BuildConnectivity()
    pcbnew.SaveBoard(PCB, board)
    bp.write_stackup(PCB)
    write_netclasses(os.path.join(PRJ, 'PowerModule.kicad_pro'))
    for ref in sorted(P.placed):
        f = fps[ref]
        q = f.GetPosition()
        print(f'{ref:5s} {P.placed[ref]} ({q.x / 1e6 - bp.X0:6.2f}, {q.y / 1e6 - bp.Y0:6.2f}) '
              f'rot {f.GetOrientationDegrees():5.1f}')
    if P.unplaced:
        print('UNPLACED:', P.unplaced)


if __name__ == '__main__':
    main(sys.argv[1])
