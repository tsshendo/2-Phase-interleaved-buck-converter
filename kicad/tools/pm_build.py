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
LS_DRV_X = 35.4
CELLS = [dict(u='U1', y=17.0, src='R15', snk='R16', inp='R1', inm='R2', c='C7', rv='R9'),
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
    # high-side drivers in the column left of the FET block, level with their FET row (outputs face
    # the FETs)
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
    # low-side drivers on the top between the two phases, right at the LS gate pads: outputs face
    # the gate via (U2 up to phase 1, U4 down to phase 2), gate resistors vertical, VDD cap at VDD
    pin1_top = lambda p, c: p(1)[1] < p(2)[1] - 1
    pin1_bot = lambda p, c: p(1)[1] > p(2)[1] + 1
    pin1_right = lambda p, c: p(1)[0] > p(2)[0] + 1
    pin1_left = lambda p, c: p(1)[0] < p(2)[0] - 1
    P.fixed('U2', T, LS_DRV_X, 25.3, cond=lambda p, c: p(5)[1] < c[1] - 0.5 and p(6)[0] < p(4)[0])
    P.fixed('R14', T, LS_DRV_X - 0.8, 21.6, cond=pin1_top)
    P.fixed('R13', T, LS_DRV_X + 0.8, 21.6, cond=pin1_top)
    P.fixed('C8', T, LS_DRV_X + 3.3, 24.4, cond=pin1_left)
    P.fixed('R10', T, LS_DRV_X + 3.3, 26.1, cond=lambda p, c: p(2)[0] < p(1)[0] - 1)
    P.fixed('R6', T, LS_DRV_X - 3.3, 25.6, cond=pin1_right)
    P.fixed('R5', T, LS_DRV_X - 3.3, 27.2, cond=pin1_right)
    P.fixed('U4', T, LS_DRV_X, 31.2, cond=lambda p, c: p(5)[1] > c[1] + 0.5 and p(6)[0] > p(4)[0])
    P.fixed('R20', T, LS_DRV_X + 0.8, 34.85, cond=pin1_bot)
    P.fixed('R19', T, LS_DRV_X - 0.8, 34.85, cond=pin1_bot)
    P.fixed('C10', T, LS_DRV_X - 3.2, 34.6, cond=pin1_right)
    P.fixed('R12', T, LS_DRV_X - 0.4, 37.3, cond=lambda p, c: p(2)[0] < p(1)[0] - 1)
    P.fixed('R3', T, LS_DRV_X - 3.3, 29.6, cond=pin1_right)     # B1 above B2, as at the AT2 pins
    P.fixed('R4', T, LS_DRV_X - 3.3, 31.2, cond=pin1_right)
    # supply diodes: low side next to their drivers' R10 / R12, high side in the column
    P.fixed('D2', T, LS_DRV_X + 4.3, 28.3, rot=0)
    P.fixed('D4', T, LS_DRV_X, 39.4, rot=0)
    P.fixed('D1', T, 27.4, 22.4, rot=0)
    P.fixed('D3', T, DRV_X, 43.8, rot=0)


NAME_BLOCK = ('Tanishq Shendokar', 'MS Electrical Engineering', 'NC State University',
              'tsshendo@ncsu.edu', '+1 (336) 405-3942')


def _bb(item):
    r = item.GetBoundingBox()
    return (r.GetLeft() / 1e6 - bp.X0, r.GetTop() / 1e6 - bp.Y0, r.GetRight() / 1e6 - bp.X0,
            r.GetBottom() / 1e6 - bp.Y0)


def _hit(a, b, m=0.0):
    return a[0] < b[2] + m and a[2] > b[0] - m and a[1] < b[3] + m and a[3] > b[1] - m


def silk_labels(board):
    """Every reference designator on the silkscreen (0.8 mm, JLC minimum), on the side of its part,
    at the first spot around the courtyard that clears pads, other labels and the board edge."""
    side_pads = {'T': [], 'B': []}
    courts = {'T': [], 'B': []}
    for f in board.GetFootprints():
        s = 'B' if f.IsFlipped() else 'T'
        f.BuildCourtyardCaches()
        cy = f.GetCourtyard(pcbnew.B_CrtYd if s == 'B' else pcbnew.F_CrtYd)
        if cy.OutlineCount():
            bb = cy.BBox()
            courts[s].append((bb.GetLeft() / 1e6 - bp.X0, bb.GetTop() / 1e6 - bp.Y0,
                              bb.GetRight() / 1e6 - bp.X0, bb.GetBottom() / 1e6 - bp.Y0, f.GetReference()))
        for p in f.Pads():
            if p.HasHole() or p.IsOnLayer(pcbnew.B_Cu if s == 'B' else pcbnew.F_Cu):
                for ss in ('T', 'B') if p.HasHole() else (s,):
                    side_pads[ss].append(_bb(p))
    for x, y in HOLES:
        for s in ('T', 'B'):
            side_pads[s].append((x - 3.0, y - 3.0, x + 3.0, y + 3.0))
    for f in board.GetFootprints():          # other parts' silkscreen outlines
        for g in f.GraphicalItems():
            if g.GetLayer() in (pcbnew.F_SilkS, pcbnew.B_SilkS) and g.GetClass() != 'PCB_FIELD':
                side_pads['B' if g.GetLayer() == pcbnew.B_SilkS else 'T'].append(_bb(g))
    placed = {'T': [], 'B': []}
    fps = sorted([f for f in board.GetFootprints() if not f.GetReference().startswith('H')],
                 key=lambda f: -f.GetArea())
    missing = []
    for f in fps:
        s = 'B' if f.IsFlipped() else 'T'
        ref = f.Reference()
        ref.SetLayer(pcbnew.B_SilkS if s == 'B' else pcbnew.F_SilkS)
        ref.SetTextSize(pcbnew.VECTOR2I(bp.mm(0.8), bp.mm(0.8)))
        ref.SetTextThickness(bp.mm(0.15))
        ref.SetVisible(True)
        c = [cc for cc in courts[s] if cc[4] == f.GetReference()]
        x0, y0, x1, y1 = c[0][:4] if c else _bb(f)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        done = False
        for strict in (True, False):
            for ang in (0, 90):
                ref.SetTextAngleDegrees(ang)
                ref.SetPosition(bp.V(cx, cy))
                tb = _bb(ref)
                tw, th = tb[2] - tb[0], tb[3] - tb[1]
                cands = []
                for g in (0.15, 0.7, 1.4):
                    cands += [(cx, y0 - th / 2 - g), (cx, y1 + th / 2 + g), (x0 - tw / 2 - g, cy),
                              (x1 + tw / 2 + g, cy), (x0 + tw / 2, y0 - th / 2 - g),
                              (x1 - tw / 2, y0 - th / 2 - g), (x0 + tw / 2, y1 + th / 2 + g),
                              (x1 - tw / 2, y1 + th / 2 + g)]
                for px, py in cands:
                    box = (px - tw / 2, py - th / 2, px + tw / 2, py + th / 2)
                    if box[0] < 0.6 or box[1] < 0.6 or box[2] > W - 0.6 or box[3] > H - 0.6:
                        continue
                    if any(_hit(box, q, 0.15) for q in side_pads[s] + placed[s]):
                        continue
                    if strict and any(_hit(box, q[:4], -0.05) for q in courts[s] if q[4] != f.GetReference()):
                        continue
                    ref.SetPosition(bp.V(px, py))
                    placed[s].append(box)
                    done = True
                    break
                if done:
                    break
            if done:
                break
        if not done:                        # nearest free spot within 4 mm (dense driver area)
            best = None
            for ang in (0, 90):
                ref.SetTextAngleDegrees(ang)
                ref.SetPosition(bp.V(cx, cy))
                tb = _bb(ref)
                tw, th = tb[2] - tb[0], tb[3] - tb[1]
                for i in range(-24, 25):
                    for j in range(-24, 25):
                        px, py = cx + i * 0.25, cy + j * 0.25
                        d = (i * i + j * j) ** 0.5 * 0.25
                        if best and d >= best[0]:
                            continue
                        box = (px - tw / 2, py - th / 2, px + tw / 2, py + th / 2)
                        if box[0] < 0.6 or box[1] < 0.6 or box[2] > W - 0.6 or box[3] > H - 0.6:
                            continue
                        if any(_hit(box, q, 0.15) for q in side_pads[s] + placed[s]):
                            continue
                        best = (d, ang, px, py, box)
            if best:
                ref.SetTextAngleDegrees(best[1])
                ref.SetPosition(bp.V(best[2], best[3]))
                placed[s].append(best[4])
                done = True
        if not done:
            missing.append(f.GetReference())
            ref.SetTextAngleDegrees(0)
            ref.SetPosition(bp.V(cx, cy))
    return missing


def name_block(board):
    """Owner text on the bottom silkscreen (credit-card name size, about 2.5 mm), in the free band
    between the FET block and the terminals, reading along the long side when the board is turned."""
    t = pcbnew.PCB_TEXT(board)
    t.SetText('\n'.join(NAME_BLOCK))
    t.SetLayer(pcbnew.B_SilkS)
    t.SetTextSize(pcbnew.VECTOR2I(bp.mm(1.6), bp.mm(2.3)))
    t.SetTextThickness(bp.mm(0.3))
    t.SetMirrored(True)
    t.SetTextAngleDegrees(90)
    t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER)
    t.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_CENTER)
    t.SetPosition(bp.V(56.7, 27.5))
    board.Add(t)
    return _bb(t)


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
    print('labels not placed:', silk_labels(board))
    print('name block bbox:', [round(v, 2) for v in name_block(board)])
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
