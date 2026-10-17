"""Stage 3: build ECE533_Guide.kicad_pcb from the schematic netlist and place the parts.

Usage (KiCad's Python):
    kicad-cli sch export netlist -o build.net kicad/ECE533_Guide/ECE533_Guide.kicad_sch
    python kicad/tools/build_pcb.py build.net

What it does
  * creates every footprint with its nets, fields, DNP flag and schematic link (KIID path), so
    "Update PCB from Schematic" in KiCad keeps working afterwards;
  * 4-layer board, ID-1 outline (85.60 x 53.98 mm, R3.18), JLCPCB constraints, layer names;
  * places the floor-plan-critical parts at fixed positions (power stage, inductor, barrier parts,
    connectors, bulk capacitors, heatsink holes) and every other part next to the pads it connects
    to, on the right side of the isolation barrier, without courtyard overlaps;
  * draws the heatsink, pedestal and fan-duct outlines (User.Drawings / B.Fab) and the isolation
    barrier keep-out (rule area on all copper layers).

Coordinates below are board mm from the top-left corner, seen from the top (x right, y down).
After Stage 3 the placement is edited in KiCad; this script is the record of the first pass.
"""
import collections
import math
import os
import sys

import pcbnew

from check_footprints import lib_path
from sexp import child, find, parse

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.normpath(os.path.join(HERE, '..', 'ECE533_Guide', 'ECE533_Guide.kicad_pcb'))

X0, Y0 = 100.0, 100.0                       # board origin on the KiCad page
W, H, RC = 85.60, 53.98, 3.18               # ID-1 card
BAR = (25.45, 28.05)                        # isolation barrier band (2.6 mm), all layers
HS_X = (25.6, 85.6)                         # Z60-12.7B heatsink on the bottom (60 x 60 mm)
L1_C = (42.15, 30.95)                       # coupled inductor centre
PH_Y = {1: 19.1, 2: 34.9}                   # phase centres = L1 switch-node pads
FET_X = 37.0                                # half-bridge column
DRV_X = 26.75                               # barrier column (driver / isolator centres)

LV_NETS = {'GND_ISO', '+5V_ISO'}
HV_NETS = {'PGND', '+5V_PWR', 'VBUS', '+24V'}
BARRIER = {  # ref: (HV pins, LV pins)
    'U1': (range(9, 17), range(1, 9)), 'U2': (range(9, 17), range(1, 9)),
    'U6': (range(1, 9), range(9, 17)), 'U7': (range(1, 9), range(9, 17)),
    'U8': (range(1, 9), range(9, 17)),
    'AT1': (range(1, 5), range(5, 9)), 'AT2': (range(1, 5), range(5, 9)),
    'PS1': (range(1, 3), range(3, 5)),
}
LV_SHEETS = ('/Controller (LV)/',)
# parts allowed on the bottom under the heatsink (<= 3 mm with the 3 mm pedestal)
LOW = ('R_0603', 'R_0805', 'R_1206', 'C_0603', 'C_0805', 'C_1206', 'C_1210', 'L_0603', 'LED_0603',
       'D_SOD', 'SOT-23', 'SOT-323', 'VSSOP', 'MSOP', 'SOIC-8', 'SOIC-16', 'HSOP', 'SSOP', 'USON',
       'D_SMB', 'D_SMC', 'NetTie', 'R_2512', 'EPC2304', 'PG-HSOF', 'SOP-4')
TOP_ONLY_PREFIX = ('TP', 'D8', 'D9')        # test points and LEDs must be visible / probeable


def mm(v):
    return pcbnew.FromMM(v)


def V(x, y):
    return pcbnew.VECTOR2I(mm(X0 + x), mm(Y0 + y))


# ------------------------------------------------------------------------------------------------
# netlist
# ------------------------------------------------------------------------------------------------
def read_netlist(path):
    tree = parse(open(path, encoding='utf-8').read())
    comps = collections.OrderedDict()
    for c in find(tree, 'comp'):
        ref = child(c, 'ref')[1]
        props = {}
        for p in c:
            if isinstance(p, list) and p and p[0] == 'property':
                val = child(p, 'value')
                props[child(p, 'name')[1]] = val[1] if val else ''
        fields = {}
        fl = child(c, 'fields')
        if fl:
            for f in fl[1:]:
                if isinstance(f, list) and f and f[0] == 'field':
                    nm = child(f, 'name')[1]
                    fields[nm] = f[2] if len(f) > 2 and isinstance(f[2], str) else ''
        sp = child(c, 'sheetpath')
        comps[ref] = dict(ref=ref, value=child(c, 'value')[1], fp=child(c, 'footprint')[1],
                          fields=fields, dnp='dnp' in props, nobom='exclude_from_bom' in props,
                          sheet=child(sp, 'names')[1],
                          path=child(sp, 'tstamps')[1] + child(c, 'tstamps')[1])
    nets = []
    for n in find(tree, 'net'):
        nodes = [(child(x, 'ref')[1], child(x, 'pin')[1]) for x in find(n, 'node')]
        nets.append((child(n, 'name')[1], nodes))
    return comps, nets


def domains(comps, nets):
    """'LV', 'HV' or 'B' (barrier part) for every component."""
    net_dom = {}
    for name, nodes in nets:
        d = set()
        if name in LV_NETS:
            d.add('LV')
        if name in HV_NETS:
            d.add('HV')
        for ref, pin in nodes:
            if ref in BARRIER:
                hv, lv = BARRIER[ref]
                d.add('HV' if int(pin) in hv else 'LV')
            elif comps[ref]['sheet'].startswith(LV_SHEETS):
                d.add('LV')
        net_dom[name] = d
    part_nets = collections.defaultdict(set)
    for name, nodes in nets:
        for ref, _ in nodes:
            part_nets[ref].add(name)
    dom = {}
    for ref, c in comps.items():
        if ref in BARRIER:
            dom[ref] = 'B'
            continue
        d = set()
        for n in part_nets[ref]:
            d |= net_dom[n]
        if not d:
            d = {'LV' if c['sheet'].startswith(LV_SHEETS) else 'HV'}
        if len(d) > 1:
            raise SystemExit(f'{ref} touches both domains: {sorted(part_nets[ref])}')
        dom[ref] = d.pop()
    lv_nets = sorted(n for n, d in net_dom.items() if d == {'LV'})
    return dom, lv_nets


# ------------------------------------------------------------------------------------------------
# board setup
# ------------------------------------------------------------------------------------------------
def setup_board(board):
    board.SetCopperLayerCount(4)
    for lid, name in ((pcbnew.F_Cu, 'L1_Top'), (pcbnew.In1_Cu, 'L2_PGND'), (pcbnew.In2_Cu, 'L3_Power'),
                      (pcbnew.B_Cu, 'L4_Bottom')):
        board.SetLayerName(lid, name)
    ds = board.GetDesignSettings()
    ds.m_MinClearance = mm(0.15)            # JLCPCB 2 oz outer: 0.15 / 0.15 mm
    ds.m_TrackMinWidth = mm(0.15)
    ds.m_ViasMinSize = mm(0.45)
    ds.m_MinThroughDrill = mm(0.2)
    ds.m_ViasMinAnnularWidth = mm(0.125)
    ds.m_HoleClearance = mm(0.25)
    ds.m_HoleToHoleMin = mm(0.25)
    ds.m_CopperEdgeClearance = mm(0.3)
    ds.m_SolderMaskMinWidth = mm(0.1)
    ds.m_SilkClearance = mm(0.1)
    ds.m_MinSilkTextHeight = mm(0.8)
    ds.m_MinSilkTextThickness = mm(0.15)
    board.GetDesignSettings().SetAuxOrigin(V(0, 0))
    board.GetDesignSettings().SetGridOrigin(V(0, 0))


def outline(board):
    def seg(a, b):
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(mm(0.1))
        s.SetStart(V(*a))
        s.SetEnd(V(*b))
        board.Add(s)

    def arc(c, start, end):
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_ARC)
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(mm(0.1))
        mid_ang = math.atan2((start[1] + end[1]) / 2 - c[1], (start[0] + end[0]) / 2 - c[0])
        mid = (c[0] + RC * math.cos(mid_ang), c[1] + RC * math.sin(mid_ang))
        s.SetArcGeometry(V(*start), V(*mid), V(*end))
        board.Add(s)

    seg((RC, 0), (W - RC, 0))
    arc((W - RC, RC), (W - RC, 0), (W, RC))
    seg((W, RC), (W, H - RC))
    arc((W - RC, H - RC), (W, H - RC), (W - RC, H))
    seg((W - RC, H), (RC, H))
    arc((RC, H - RC), (RC, H), (0, H - RC))
    seg((0, H - RC), (0, RC))
    arc((RC, RC), (0, RC), (RC, 0))


def rect_shape(board, x0, y0, x1, y1, layer, width=0.15):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_RECT)
    s.SetLayer(layer)
    s.SetWidth(mm(width))
    s.SetStart(V(x0, y0))
    s.SetEnd(V(x1, y1))
    board.Add(s)


def text(board, msg, x, y, layer, size=1.0, mirror=False):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(msg)
    t.SetLayer(layer)
    t.SetPosition(V(x, y))
    t.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size)))
    t.SetTextThickness(mm(size * 0.15))
    if mirror:
        t.SetMirrored(True)
    board.Add(t)


def keepout(board, x0, y0, x1, y1, name):
    z = pcbnew.ZONE(board)
    z.SetIsRuleArea(True)
    z.SetLayerSet(pcbnew.LSET.AllCuMask())
    z.SetDoNotAllowTracks(True)
    z.SetDoNotAllowVias(True)
    z.SetDoNotAllowZoneFills(True)
    z.SetDoNotAllowPads(False)
    z.SetDoNotAllowFootprints(False)
    z.SetZoneName(name)
    o = z.Outline()
    o.NewOutline()
    for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        o.Append(mm(X0 + x), mm(Y0 + y))
    board.Add(z)


def mechanics(board):
    dw, bf = pcbnew.Dwgs_User, pcbnew.B_Fab
    rect_shape(board, HS_X[0], -3.0, HS_X[1], H + 3.0, dw)       # heatsink 60 x 60
    text(board, 'Z60-12.7B heatsink (bottom), fins along x', 55.6, -1.6, dw, 1.0)
    for ph, yp in PH_Y.items():                                  # pedestal pads over each FET pair
        rect_shape(board, FET_X - 2.7, yp - 3.75, FET_X + 2.7, yp + 3.75, bf, 0.1)
    text(board, 'pedestal 3.0 mm, insulating TIM', FET_X, 27.0, bf, 0.8, mirror=True)
    rect_shape(board, W, 3.0, W + 22.0, H - 3.0, dw)             # fan duct + 40 mm fan at the end
    text(board, 'fan duct / 9GA0405P6H001', W + 11.0, H / 2, dw, 1.0)
    rect_shape(board, BAR[0], 0.0, BAR[1], H, pcbnew.Cmts_User, 0.1)
    text(board, 'ISOLATION BARRIER', (BAR[0] + BAR[1]) / 2, -1.5, pcbnew.Cmts_User, 0.8)
    keepout(board, BAR[0], -0.5, BAR[1], H + 0.5, 'ISOLATION_BARRIER')


# ------------------------------------------------------------------------------------------------
# footprints
# ------------------------------------------------------------------------------------------------
_fp_cache = {}


def load_fp(fpid):
    lib, name = fpid.split(':', 1)
    f = pcbnew.FootprintLoad(lib_path(lib), name)
    if f is None:
        raise SystemExit(f'footprint not found: {fpid}')
    f.SetFPID(pcbnew.LIB_ID(lib, name))
    return f


def add_footprints(board, comps, nets):
    netinfo = {}
    for name, _ in nets:
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        netinfo[name] = ni
    pin_net = {}
    for name, nodes in nets:
        for ref, pin in nodes:
            pin_net[(ref, pin)] = netinfo[name]
    fps = {}
    for ref, c in comps.items():
        f = load_fp(c['fp'])
        f.SetReference(ref)
        f.SetValue(c['value'])
        f.SetPath(pcbnew.KIID_PATH(c['path']))
        for k, v in c['fields'].items():
            if k == 'Footprint':
                continue
            if k in ('Datasheet', 'Description'):
                f.GetField(k).SetText(v)
                continue
            f.SetField(k, v)
            fld = f.GetField(k)
            if fld:
                fld.SetVisible(False)
        if c['dnp']:
            f.SetDNP(True)
        if c['nobom']:
            f.SetExcludedFromBOM(True)
        for p in f.Pads():
            ni = pin_net.get((ref, p.GetNumber()))
            if ni:
                p.SetNet(ni)
        f.SetPosition(V(-30, -30))
        board.Add(f)
        fps[ref] = f
    return fps


# ------------------------------------------------------------------------------------------------
# placement engine
# ------------------------------------------------------------------------------------------------
class Placer:
    def __init__(self, board, fps, comps, nets, dom):
        self.board, self.fps, self.comps, self.dom = board, fps, comps, dom
        self.placed = {}                     # ref -> side ('T'/'B')
        self.unplaced = []
        self.obst = {'T': [], 'B': []}       # (x0, y0, x1, y1, ref)
        self.nets = nets
        self.part_nets = collections.defaultdict(list)
        for name, nodes in nets:
            for ref, pin in nodes:
                self.part_nets[ref].append((name, pin))
        self.net_nodes = {name: nodes for name, nodes in nets}

    # geometry --------------------------------------------------------------------------------
    def court(self, f):
        f.BuildCourtyardCaches()
        cy = f.GetCourtyard(pcbnew.B_CrtYd if f.IsFlipped() else pcbnew.F_CrtYd)
        bb = cy.BBox() if cy.OutlineCount() else f.GetBoundingBox(False)
        return (bb.GetLeft() / 1e6 - X0, bb.GetTop() / 1e6 - Y0, bb.GetRight() / 1e6 - X0,
                bb.GetBottom() / 1e6 - Y0)

    def set(self, f, side, rot, x, y):
        if (side == 'B') != f.IsFlipped():
            f.Flip(f.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        f.SetOrientationDegrees(rot)
        f.SetPosition(V(x, y))
        # reference designators live on the Fab layers (assembly drawing); silkscreen keeps outlines
        ref = f.Reference()
        ref.SetLayer(pcbnew.B_Fab if side == 'B' else pcbnew.F_Fab)
        ref.SetTextSize(pcbnew.VECTOR2I(mm(0.6), mm(0.6)))
        ref.SetTextThickness(mm(0.09))
        ref.SetFPRelativePosition(pcbnew.VECTOR2I(0, 0))

    def pad_xy(self, f, num):
        for p in f.Pads():
            if p.GetNumber() == str(num):
                q = p.GetPosition()
                return q.x / 1e6 - X0, q.y / 1e6 - Y0
        raise KeyError(num)

    def tht_pads(self, f):
        out = []
        for p in f.Pads():
            if p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH):
                bb = p.GetBoundingBox()
                out.append((bb.GetLeft() / 1e6 - X0 - 0.25, bb.GetTop() / 1e6 - Y0 - 0.25,
                            bb.GetRight() / 1e6 - X0 + 0.25, bb.GetBottom() / 1e6 - Y0 + 0.25))
        return out

    def commit(self, ref, side):
        f = self.fps[ref]
        c = self.court(f)
        self.obst[side].append(c + (ref,))
        other = 'B' if side == 'T' else 'T'
        for r in self.tht_pads(f):
            self.obst[other].append(r + (ref,))
        if str(f.GetFPID().GetLibItemName()).startswith('MountingHole'):
            self.obst[other].append(c + (ref,))
        self.placed[ref] = side

    # rules -------------------------------------------------------------------------------------
    def legal(self, ref, side, c):
        x0, y0, x1, y1 = c
        if x0 < 0.25 or y0 < 0.25 or x1 > W - 0.25 or y1 > H - 0.25:
            return False
        # rounded corners: the courtyard corner inside a corner square must stay inside the arc
        for cx, cy, fx, fy in ((RC, RC, x0, y0), (W - RC, RC, x1, y0), (RC, H - RC, x0, y1),
                               (W - RC, H - RC, x1, y1)):
            inside_sq = (fx < RC if cx == RC else fx > W - RC) and (fy < RC if cy == RC else fy > H - RC)
            if inside_sq and math.hypot(fx - cx, fy - cy) > RC - 0.3:
                return False
        d = self.dom[ref]
        if d == 'LV' and x1 > BAR[0]:
            return False
        if d == 'HV' and x0 < BAR[1]:
            return False
        for o in self.obst[side]:
            if x0 < o[2] - 0.01 and x1 > o[0] + 0.01 and y0 < o[3] - 0.01 and y1 > o[1] + 0.01:
                return False
        return True

    def can_bottom(self, ref):
        name = str(self.fps[ref].GetFPID().GetLibItemName())
        if ref.startswith(TOP_ONLY_PREFIX):
            return False
        return any(k in name for k in LOW)

    # placement ---------------------------------------------------------------------------------
    def fixed(self, ref, side, x, y, rot=0, cond=None, by_court=False):
        """Place at (x, y); cond(pads) picks the rotation; by_court: (x, y) is the courtyard centre."""
        f = self.fps[ref]
        rots = [rot] if cond is None else [0, 90, 180, 270]
        for r in rots:
            self.set(f, side, r, x, y)
            if by_court:
                c = self.court(f)
                self.set(f, side, r, x - ((c[0] + c[2]) / 2 - x), y - ((c[1] + c[3]) / 2 - y))
            if cond is None or cond(lambda n: self.pad_xy(f, n), (x, y)):
                break
        else:
            raise SystemExit(f'{ref}: no rotation satisfies the placement condition')
        c = self.court(f)
        for o in self.obst[side]:
            if c[0] < o[2] - 0.01 and c[2] > o[0] + 0.01 and c[1] < o[3] - 0.01 and c[3] > o[1] + 0.01:
                print(f'  note: fixed {ref} overlaps {o[4]}')
        self.commit(ref, side)

    def attract(self, ref):
        """Mean position of connected pads on placed parts (small nets only), preferred side."""
        pts, sides = [], collections.Counter()
        for name, pin in self.part_nets[ref]:
            nodes = self.net_nodes[name]
            if len(nodes) > 12:
                continue
            for r2, p2 in nodes:
                if r2 != ref and r2 in self.placed:
                    try:
                        pts.append(self.pad_xy(self.fps[r2], p2))
                    except KeyError:
                        continue
                    sides[self.placed[r2]] += 1
        if not pts:
            return None
        x = sum(p[0] for p in pts) / len(pts)
        y = sum(p[1] for p in pts) / len(pts)
        return x, y, sides.most_common(1)[0][0], len(pts)

    def auto(self, ref, x, y, side, radius=60.0, sides=None):
        """Nearest legal spot to (x, y); the other side costs 3 mm extra (LV parts: top, 12 mm)."""
        f = self.fps[ref]
        if sides is None:
            sides = [side, 'T' if side == 'B' else 'B']
            if self.dom[ref] == 'LV':
                sides = ['T', 'B']
            if not self.can_bottom(ref) or (self.dom[ref] == 'LV' and ref[0] in 'UQD'):
                sides = ['T']
        geo = {}
        for s in sides:
            for r in (0, 90):
                self.set(f, s, r, 0, 0)
                geo[(s, r)] = self.court(f)
        step = 0.25
        best = None
        rad = 0.0
        while rad <= radius:
            if best is not None and rad > best[0]:
                break
            n = max(1, int(2 * math.pi * rad / step))
            for s in sides:
                pen = 0.0 if s == sides[0] else (12.0 if self.dom[ref] == 'LV' else 3.0)
                if best is not None and rad + pen >= best[0]:
                    continue
                for k in range(n):
                    a = 2 * math.pi * k / n
                    px = round((x + rad * math.cos(a)) / step) * step
                    py = round((y + rad * math.sin(a)) / step) * step
                    for r in (0, 90):
                        c0 = geo[(s, r)]
                        if self.legal(ref, s, (c0[0] + px, c0[1] + py, c0[2] + px, c0[3] + py)):
                            cost = rad + pen
                            if best is None or cost < best[0]:
                                best = (cost, s, r, px, py)
            rad += step
        if best is None:
            print(f'  UNPLACED {ref}: no free spot near ({x:.1f}, {y:.1f}); parked off-board')
            self.set(f, 'T', 0, -10.0, 5.0 + 4.0 * len(self.unplaced))
            self.unplaced.append(ref)
            self.placed[ref] = 'T'
            return
        _, s, r, px, py = best
        self.set(f, s, r, px, py)
        self.commit(ref, s)

    def auto_all(self, fallback):
        todo = [r for r in self.fps if r not in self.placed]
        while todo:
            scored = []
            for r in todo:
                a = self.attract(r)
                scored.append(((a[3] if a else 0), r, a))
            scored.sort(key=lambda t: -t[0])
            n, ref, a = scored[0]
            if a is None:
                x, y, s = fallback(ref)
            else:
                x, y, s, _ = a
            self.auto(ref, x, y, s)
            todo.remove(ref)


# ------------------------------------------------------------------------------------------------
# the floor plan
# ------------------------------------------------------------------------------------------------
def floor_plan(P):
    T, B = 'T', 'B'
    lx, ly = L1_C
    # coupled inductor: switch-node pads (3, 4) face the power stage on the left, pad 4 on top
    P.fixed('L1', T, lx, ly, cond=lambda p, c: p(4)[0] < p(1)[0] - 5 and p(4)[1] < p(3)[1])
    # heatsink screws (plated, HS_SHIELD) clear of the barrier column and the bulk capacitors
    for ref, (x, y) in zip(('H1', 'H2', 'H3', 'H4'), ((36.8, 3.7), (36.8, 50.28), (68.7, 20.0), (68.7, 34.0))):
        P.fixed(ref, T, x, y)
    # power terminals on the right edge: DC+ / DC- (input) on top, VOUT- / VOUT+ below
    jx = W - 6.4 - 0.5
    for ref, y in (('J1', 6.75), ('J3', 19.3), ('J6', 34.7), ('J2', 47.25)):
        P.fixed(ref, T, jx, y, by_court=True)
    # input bulk capacitors (top, THT) next to the half-bridges' VBUS rows
    P.fixed('C5', T, 47.6, 8.0, by_court=True)
    P.fixed('C6', T, 61.0, 8.0, rot=0, by_court=True)
    P.fixed('F1', T, 69.9, 8.0, rot=90, by_court=True)          # optional fuse (DNP), R96 below it
    # barrier column, top: PS1, U8 (VOUT), U6 (I1), U7 (I2); HV pins on the right
    P.fixed('PS1', T, 26.4, 4.4, by_court=True,
            cond=lambda p, c: p(1)[0] > p(4)[0] + 5 and abs(p(1)[1] - p(4)[1]) < 0.1)
    # HV pins (1-8) in a vertical row on the right, LV pins (9-16) on the left
    hv_right = lambda p, c: p(1)[0] > c[0] + 3 and abs(p(1)[0] - p(8)[0]) < 0.01
    for ref, y in (('U8', 14.3), ('U6', 25.4), ('U7', 36.5)):
        P.fixed(ref, T, DRV_X, y, cond=hv_right)
    # barrier column, bottom: AT1, U1, U2, AT2 (HV pins 1-4 on the right)
    at_ok = lambda p, c: p(1)[0] > c[0] + 1 and abs(p(1)[0] - p(4)[0]) < 0.01
    P.fixed('AT1', B, DRV_X, 9.6, cond=at_ok)
    P.fixed('AT2', B, DRV_X, 44.6, cond=at_ok)
    # half-bridges (bottom), both phases identical (translated by the L1 pad pitch).
    # A bottom-side Si8274 has channel B (VOB, low side) at the top of its output row and channel A
    # (VOA, high side) at the bottom, so each stack is low side on top, high side below, with the
    # input ceramics under the high side. The low-side gate faces the driver (short gate loop);
    # the high-side gate is at the far end of the pair (columns aligned so SW stays on L4).
    parts = {1: dict(drv='U1', hs='Q3', ls='Q4', caps=('C1', 'C2', 'C15', 'C16'), rg_h='R15', rpd_h='R1',
                     rg_l='R13', rpd_l='R2', cboot='C7', cvdd='C8', nt_h='NT1', nt_l='NT2'),
             2: dict(drv='U2', hs='Q5', ls='Q6', caps=('C3', 'C4', 'C17', 'C18'), rg_h='R16', rpd_h='R3',
                     rg_l='R14', rpd_l='R4', cboot='C9', cvdd='C10', nt_h='NT3', nt_l='NT4')}
    for ph, yp in PH_Y.items():
        d = parts[ph]
        P.fixed(d['drv'], B, DRV_X, yp,
                cond=lambda p, c: p(10)[0] > c[0] + 1 and p(10)[1] < c[1] and p(15)[1] > c[1])
        # low side on top, gate pad on the left (driver side)
        P.fixed(d['ls'], B, FET_X, yp - 2.15,
                cond=lambda p, c: p(1)[0] < c[0] and abs(p(3)[1] - p(5)[1]) < 0.01)
        ls = P.fps[d['ls']]
        ls_d = sorted(round(P.pad_xy(ls, n)[0], 3) for n in (3, 5))

        def hs_ok(p, c, ls_d=ls_d):    # high-side source strips line up with low-side drain strips
            return sorted(round(p(n)[0], 3) for n in (4, 6)) == ls_d
        P.fixed(d['hs'], B, FET_X, yp + 2.15, cond=hs_ok)
        # input ceramics in a row under the high side, VBUS pad towards the FET
        for k, ref in enumerate(d['caps']):
            P.fixed(ref, B, FET_X - 3.15 + 2.1 * k, yp + 6.1, cond=lambda p, c: p(1)[1] < p(2)[1] - 0.5)
        # VDDB / boot capacitors at the driver pins
        P.fixed(d['cvdd'], B, 31.3, yp - 6.0, rot=90)
        P.fixed(d['cboot'], B, 31.3, yp + 3.55, rot=90)
        # gate resistor in line with the gate pad, pull-down and Kelvin net tie towards the SK pad
        for fet, rg, rpd, nt, dx in (('ls', 'rg_l', 'rpd_l', 'nt_l', None), ('hs', 'rg_h', 'rpd_h', 'nt_h', 3.4)):
            f = P.fps[d[fet]]
            g, sk = P.pad_xy(f, 1), P.pad_xy(f, 2)
            sgn = 1 if sk[1] > g[1] else -1
            x = 32.13 if dx is None else g[0] + dx
            P.fixed(d[rg], B, x, g[1], cond=lambda p, c, gx=g[0]: abs(p(2)[0] - gx) < abs(p(1)[0] - gx))
            P.fixed(d[rpd], B, x, g[1] + sgn * 1.6, rot=0)
            P.fixed(d[nt], B, x, g[1] + sgn * 3.0, rot=0)
    # FET temperature sensor between the phases, under the heatsink
    P.fixed('RT1', B, FET_X, 28.8, rot=0)
    # output: shunts at the inductor output pads, output capacitors, VOUT terminals
    lx1 = P.pad_xy(P.fps['L1'], 1)
    lx2 = P.pad_xy(P.fps['L1'], 2)
    # shunts vertical beside L1, sense strips towards L1 / the barrier
    vert = lambda p, c: abs(p(1)[0] - p(4)[0]) < 0.01 and p(2)[0] < c[0]
    P.fixed('RS2', T, 52.4, lx1[1] - 1.0, cond=vert)
    P.fixed('RS3', T, 52.4, lx2[1] - 1.0, cond=vert)
    P.fixed('C66', T, 59.0, 23.3, rot=90, by_court=True)
    P.fixed('C67', T, 59.0, 36.2, rot=90, by_court=True)
    P.fixed('L2', T, 44.6, 49.45, rot=0)                       # aux buck inductor (7 mm tall)
    P.fixed('J5', T, 63.9, 48.3, rot=180, by_court=True)       # fan header, opening to the bottom edge
    # input protection on the bottom right (under the heatsink, <= 3 mm): J1 -> R96 -> Q2 -> RS1 -> Q1
    P.fixed('R96', B, 69.9, 8.0, rot=90, by_court=True)
    P.auto('Q2', 62.0, 19.0, B, sides=[B])
    P.auto('Q1', 50.5, 19.0, B, sides=[B])
    # rack I/O connector on the left edge (opening to the left), controller in the LV area
    P.fixed('J4', T, 9.0, 45.0, rot=270, by_court=True)
    P.fixed('U5', T, 13.0, 25.0, rot=0)


STACKUP = """		(stackup
			(layer "F.SilkS" (type "Top Silk Screen"))
			(layer "F.Paste" (type "Top Solder Paste"))
			(layer "F.Mask" (type "Top Solder Mask") (thickness 0.01))
			(layer "F.Cu" (type "copper") (thickness 0.07))
			(layer "dielectric 1" (type "prepreg") (color "FR4 natural") (thickness 0.0994) (material "FR4 3313") (epsilon_r 4.1) (loss_tangent 0.02))
			(layer "In1.Cu" (type "copper") (thickness 0.07))
			(layer "dielectric 2" (type "core") (color "FR4 natural") (thickness 1.1012) (material "FR4") (epsilon_r 4.6) (loss_tangent 0.02))
			(layer "In2.Cu" (type "copper") (thickness 0.07))
			(layer "dielectric 3" (type "prepreg") (color "FR4 natural") (thickness 0.0994) (material "FR4 3313") (epsilon_r 4.1) (loss_tangent 0.02))
			(layer "B.Cu" (type "copper") (thickness 0.07))
			(layer "B.Mask" (type "Bottom Solder Mask") (thickness 0.01))
			(layer "B.Paste" (type "Bottom Solder Paste"))
			(layer "B.SilkS" (type "Bottom Silk Screen"))
			(copper_finish "ENIG")
			(dielectric_constraints no)
		)
"""


def write_stackup(path):
    """4 x 2 oz, JLC04161H-3313 prepreg (0.0994 mm), core set so the board is 1.60 mm, ENIG."""
    txt = open(path, encoding='utf-8').read()
    if '(stackup' not in txt:
        txt = txt.replace('\t(setup\n', '\t(setup\n' + STACKUP, 1)
        open(path, 'w', encoding='utf-8', newline='\n').write(txt)


def write_netclasses(pro, lv_nets):
    """LV_ISO net class (every net on the control side of the barrier) for the 2.5 mm DRC rule,
    HV_SW for the 72 V bus and switch nodes."""
    import json
    d = json.load(open(pro, encoding='utf-8'))
    ns = d.setdefault('net_settings', {})
    base = dict(ns['classes'][0])
    classes = [c for c in ns['classes'] if c['name'] not in ('LV_ISO', 'HV_SW')]
    for name, extra in (('LV_ISO', dict(clearance=0.15, track_width=0.2)),
                        ('HV_SW', dict(clearance=0.25, track_width=0.5))):
        c = dict(base)
        c.update(name=name, priority=len(classes), **extra)
        classes.append(c)
    ns['classes'] = classes
    pats = [dict(netclass='LV_ISO', pattern=n) for n in lv_nets]
    pats += [dict(netclass='HV_SW', pattern=n) for n in
             ('VBUS', '/Power stage (2 phases)/SW1', '/Power stage (2 phases)/SW2')]
    ns['netclass_patterns'] = pats
    json.dump(d, open(pro, 'w', encoding='utf-8', newline='\n'), indent=2)


def fallback(dom):
    def f(ref):
        if dom[ref] == 'LV':
            return 12.0, 27.0, 'T'
        return 60.0, 27.0, 'T'
    return f


def main(net):
    comps, nets = read_netlist(net)
    dom, lv_nets = domains(comps, nets)
    with open(PCB, 'w', encoding='utf-8', newline='\n') as fh:      # start from an empty board
        fh.write('(kicad_pcb (version 20260206) (generator "pcbnew") (generator_version "10.0")\n)\n')
    board = pcbnew.LoadBoard(PCB)
    setup_board(board)
    outline(board)
    mechanics(board)
    fps = add_footprints(board, comps, nets)
    P = Placer(board, fps, comps, nets, dom)
    floor_plan(P)
    P.obst['T'].append((W - 14.2, 0.0, W, H, 'lug zone'))      # ring lugs on the REDCUBE terminals
    P.auto_all(fallback(dom))
    board.BuildConnectivity()
    pcbnew.SaveBoard(PCB, board)
    write_stackup(PCB)
    write_netclasses(PCB.replace('.kicad_pcb', '.kicad_pro'), lv_nets)
    n_b = sum(1 for s in P.placed.values() if s == 'B')
    print(f'placed {len(P.placed)} footprints ({n_b} bottom) -> {PCB}')


if __name__ == '__main__':
    main(sys.argv[1])
