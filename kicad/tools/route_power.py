"""Stage 4 step 1: power copper (zones, via arrays) on ECE533_Guide.kicad_pcb.

    python kicad/tools/route_power.py power    # after build_pcb.py: power copper, planes, via-in-pad
    python kicad/tools/route_signals.py        # Freerouting for the remaining nets
    python kicad/tools/route_power.py finish   # outer-layer ground pours + stitching vias

Layer use (docs/design/routing_stage4.md):
  L1 top     SW / LX pours at L1, +24 V output pour, VBUS at the bulk caps, input terminal pours,
             PGND elsewhere on the HV side, GND_ISO on the LV side
  L2         solid PGND (HV side) / GND_ISO island (LV side), split along the barrier
  L3         PGND return plane under the half-bridges, VBUS feeder, D6-A1 input path, +24 V output,
             +5V_ISO plane (LV side)
  L4 bottom  per-phase VBUS / SW / PGND combs at the EPC2304 strips, input-protection path,
             PGND elsewhere (HV), GND_ISO (LV)
Via-in-pad (filled and capped, JLCPCB POFV): 0.25 / 0.45 mm in the EPC2304 SW and low-side PGND strips.
"""
import math
import os

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.normpath(os.path.join(HERE, '..', 'ECE533_Guide', 'ECE533_Guide.kicad_pcb'))
X0, Y0 = 100.0, 100.0
W, H, RC = 85.60, 53.98, 3.18
BAR = (25.45, 28.05)
F, B, L2, L3 = pcbnew.F_Cu, pcbnew.B_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu
SWN = {1: '/Power stage (2 phases)/SW1', 2: '/Power stage (2 phases)/SW2'}
LXN = {1: '/Power stage (2 phases)/LX1', 2: '/Power stage (2 phases)/LX2'}
PHASE = {1: dict(ls='Q4', hs='Q3', caps=('C1', 'C2', 'C15', 'C16'), lpad='4', rs='RS2', lx='1'),
         2: dict(ls='Q6', hs='Q5', caps=('C3', 'C4', 'C17', 'C18'), lpad='3', rs='RS3', lx='2')}
VIA_STD = (0.3, 0.6)          # drill, diameter
VIA_PAD = (0.25, 0.45)        # via-in-pad, filled and capped


def mm(v):
    return pcbnew.FromMM(v)


def P(x, y):
    return pcbnew.VECTOR2I(mm(X0 + x), mm(Y0 + y))


class Router:
    def __init__(self, board):
        self.b = board
        self.nets = {}
        for name, ni in board.GetNetsByName().items():
            self.nets[str(name)] = ni
        self.vias = []
        self.tracks = []
        self.stitch = []

    def prune_stitching(self):
        """Remove stitching vias that do not land in filled copper of their net on two layers."""
        zones = [z for z in self.b.Zones() if not z.GetIsRuleArea()]
        n = 0
        for v in self.stitch:
            pos = v.GetPosition()
            hits = sum(1 for z in zones if z.GetNetCode() == v.GetNetCode()
                       and z.HitTestFilledArea(z.GetLayer(), pos))
            if hits < 2:
                self.b.Remove(v)
                n += 1
        return n

    def load_existing(self):
        for t in self.b.GetTracks():
            a, e = t.GetStart(), t.GetEnd()
            if t.GetClass() == 'PCB_VIA':
                self.vias.append((a.x / 1e6 - X0, a.y / 1e6 - Y0, t.GetWidth(pcbnew.F_Cu) / 2e6, t.GetNetname()))
            else:
                self.tracks.append((a.x / 1e6 - X0, a.y / 1e6 - Y0, e.x / 1e6 - X0, e.y / 1e6 - Y0,
                                    t.GetWidth() / 2e6, t.GetNetname()))

    def net(self, name):
        if name in self.nets:
            return self.nets[name]
        cands = [n for n in self.nets if n.endswith('/' + name) or n in (name, f'Net-({name})')]
        if len(cands) != 1:
            raise KeyError(f'net {name}: {cands}')
        return self.nets[cands[0]]

    def fp(self, ref):
        return self.b.FindFootprintByReference(ref)

    def pad(self, ref, num):
        """Bounding box of all copper of pad `num` (x0, y0, x1, y1) in board mm."""
        bb = None
        for p in self.fp(ref).Pads():
            if p.GetNumber() == str(num):
                r = p.GetBoundingBox()
                t = (r.GetLeft() / 1e6 - X0, r.GetTop() / 1e6 - Y0, r.GetRight() / 1e6 - X0,
                     r.GetBottom() / 1e6 - Y0)
                bb = t if bb is None else (min(bb[0], t[0]), min(bb[1], t[1]), max(bb[2], t[2]),
                                           max(bb[3], t[3]))
        if bb is None:
            raise KeyError(f'{ref}.{num}')
        return bb

    # -- copper --------------------------------------------------------------------------------
    def zone(self, net, layer, pts, prio=0, solid=True, min_w=0.2, name=''):
        z = pcbnew.ZONE(self.b)
        z.SetLayer(layer)
        z.SetNet(self.net(net))
        z.SetAssignedPriority(prio)
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL if solid else pcbnew.ZONE_CONNECTION_THERMAL)
        z.SetMinThickness(mm(min_w))
        z.SetThermalReliefGap(mm(0.3))
        z.SetThermalReliefSpokeWidth(mm(0.4))
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        if name:
            z.SetZoneName(name)
        o = z.Outline()
        o.NewOutline()
        for x, y in pts:
            o.Append(mm(X0 + x), mm(Y0 + y))
        self.b.Add(z)
        return z

    def rect(self, net, layer, x0, y0, x1, y1, prio=0, **kw):
        return self.zone(net, layer, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], prio, **kw)

    def via(self, net, x, y, size=VIA_STD, check=True, same_pad_ok=False, stitch=False):
        if check and not self.via_ok(net, x, y, size[1] / 2, same_pad_ok):
            return False
        v = pcbnew.PCB_VIA(self.b)
        if stitch:
            self.stitch.append(v)
        v.SetPosition(P(x, y))
        v.SetDrill(mm(size[0]))
        v.SetWidth(mm(size[1]))
        v.SetNet(self.net(net))
        self.b.Add(v)
        self.vias.append((x, y, size[1] / 2, net))
        return True

    def via_ok(self, net, x, y, r, same_pad_ok=False):
        """Clearance from every pad of another net (all layers, plus holes) and from other vias."""
        target = self.net(net).GetNetname()
        hv = target in ('VBUS', SWN[1], SWN[2])

        def box(p):
            bb = p.GetBoundingBox()
            return (bb.GetLeft() / 1e6 - X0, bb.GetTop() / 1e6 - Y0, bb.GetRight() / 1e6 - X0,
                    bb.GetBottom() / 1e6 - Y0)
        host = None                       # via-in-pad: the footprint whose same-net pad holds the via
        if same_pad_ok:
            for f in self.b.GetFootprints():
                for p in f.Pads():
                    x0, y0, x1, y1 = box(p)
                    if p.GetNetname() == target and x0 <= x <= x1 and y0 <= y <= y1:
                        host = f.GetReference()
        for f in self.b.GetFootprints():
            for p in f.Pads():
                x0, y0, x1, y1 = box(p)
                dx = max(x0 - x, 0, x - x1)
                dy = max(y0 - y, 0, y - y1)
                d = math.hypot(dx, dy)
                if p.HasHole() and d < r + 0.35:  # any drilled hole, plated or not (NPTH pegs)
                    return False
                if not p.IsOnCopperLayer():       # paste-only stencil apertures
                    continue
                same = p.GetNetname() == target and p.GetNetname() != ''
                cl = 0.0 if same else (0.3 if (hv or p.GetNetname() in ('VBUS', SWN[1], SWN[2])) else 0.22)
                if not same and f.GetReference() == host:
                    cl = 0.16             # pads of the same part: only the generic 0.15 mm rule applies
                if not same and d < r + cl:
                    return False
            for g in f.GraphicalItems():          # net-tie copper (Kelvin shunt strips), no net
                if g.IsOnCopperLayer():
                    bb = g.GetBoundingBox()
                    dx = max(bb.GetLeft() / 1e6 - X0 - x, 0, x - (bb.GetRight() / 1e6 - X0))
                    dy = max(bb.GetTop() / 1e6 - Y0 - y, 0, y - (bb.GetBottom() / 1e6 - Y0))
                    if math.hypot(dx, dy) < r + 0.25:
                        return False
        for (vx, vy, vr, vn) in self.vias:
            if math.hypot(vx - x, vy - y) < vr + r + (0.05 if vn == net else 0.25):
                return False
        for (xa, ya, xb, yb, hw, tn) in self.tracks:
            if tn == target:
                continue
            ux, uy = xb - xa, yb - ya
            L = ux * ux + uy * uy
            t = 0 if L == 0 else max(0, min(1, ((x - xa) * ux + (y - ya) * uy) / L))
            if math.hypot(x - (xa + t * ux), y - (ya + t * uy)) < r + hw + 0.25:
                return False
        if not (BAR[1] + 0.3 < x - r or x + r < BAR[0] - 0.3):
            return False
        return 0.6 < x < W - 0.6 and 0.6 < y < H - 0.6

    def track(self, net, layer, pts, w):
        for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
            t = pcbnew.PCB_TRACK(self.b)
            t.SetStart(P(xa, ya))
            t.SetEnd(P(xb, yb))
            t.SetWidth(mm(w))
            t.SetLayer(layer)
            t.SetNet(self.net(net))
            self.b.Add(t)


def hv_region():
    """HV side of the board (right of the barrier), corners chamfered like the R3.18 outline."""
    x0, x1, y0, y1, c = BAR[1] + 0.25, W - 0.35, 0.35, H - 0.35, 2.0
    return [(x0, y0), (x1 - c, y0), (x1, y0 + c), (x1, y1 - c), (x1 - c, y1), (x0, y1)]


def lv_region():
    x0, x1, y0, y1, c = 0.35, BAR[0] - 0.25, 0.35, H - 0.35, 2.0
    return [(x0 + c, y0), (x1, y0), (x1, y1), (x0 + c, y1), (x0, y1 - c), (x0, y0 + c)]


# ------------------------------------------------------------------------------------------------
def power_stage(R):
    for ph, d in PHASE.items():
        sw = SWN[ph]
        ls = {n: R.pad(d['ls'], n) for n in range(1, 8)}
        hs = {n: R.pad(d['hs'], n) for n in range(1, 8)}
        ls_y0, ls_y1 = min(v[1] for v in ls.values()), max(v[3] for v in ls.values())
        hs_y0, hs_y1 = min(v[1] for v in hs.values()), max(v[3] for v in hs.values())
        sx0 = min(v[0] for v in list(ls.values()) + list(hs.values()))
        sx1 = max(v[2] for v in list(ls.values()) + list(hs.values()))
        caps = [R.pad(c, 1) for c in d['caps']]
        capg = [R.pad(c, 2) for c in d['caps']]
        cx0, cx1 = min(c[0] for c in caps) - 0.25, max(c[2] for c in caps) + 0.25
        # L4: switch node across the LS/HS gap (SW strips line up), LS drain pad 7 included
        sw_cols = [ls[3], ls[5]]
        R.rect(sw, B, min(c[0] for c in sw_cols) - 0.05, ls_y1 - 0.5, ls[7][2], hs_y0 + 0.5, prio=6,
               name=f'SW{ph}_gap')
        # L4: VBUS comb from the HS drain strips to the input ceramics, extended for the feeder vias
        vb_y1 = max(c[3] for c in caps) + 0.05
        R.rect('VBUS', B, cx0, hs_y1 - 0.75, cx1 + 2.6, vb_y1, prio=6, name=f'VBUS{ph}_caps')
        # L4: PGND under the caps (return vias) and the PGND comb on the LS source strip tops
        g_y0, g_y1 = min(c[1] for c in capg) - 0.05, max(c[3] for c in capg) + 1.0
        R.rect('PGND', B, cx0, g_y0, cx1, g_y1, prio=5, name=f'PGND{ph}_caps')
        R.rect('PGND', B, ls[4][0] - 0.2, ls_y0 - 1.4, ls[6][2] + 0.2, ls_y0 + 0.45, prio=6,
               name=f'PGND{ph}_ls')
        # via-in-pad: SW strips (both FETs), LS drain pad 7, LS source strips; gap vias on SW columns
        lp = R.pad('L1', d['lpad'])
        for ref, nums, net in ((d['ls'], (3, 5, 7), sw), (d['hs'], (4, 6), sw), (d['ls'], (4, 6), 'PGND')):
            for n in nums:
                x0, y0, x1, y1 = R.pad(ref, n)
                xc = (x0 + x1) / 2
                k = int((y1 - y0 - 0.7) / 0.85) + 1
                for i in range(k):
                    y = y0 + 0.35 + (y1 - y0 - 0.7) * (i / max(k - 1, 1))
                    # through vias: a PGND via must not come up inside the inductor's SW pad on L1
                    if net == 'PGND' and y > lp[1] - 0.6:
                        continue
                    R.via(net, xc, y, VIA_PAD, same_pad_ok=True)
        for c in sw_cols:
            R.via(sw, (c[0] + c[2]) / 2, (ls_y1 + hs_y0) / 2, VIA_PAD, same_pad_ok=True)
        # PGND return vias: row above the LS source strips, row under the caps
        for i in range(6):
            R.via('PGND', ls[4][0] + 0.1 + i * 0.6, ls_y0 - 0.85)
        x = cx0 + 0.35
        while x < cx1 - 0.3:
            R.via('PGND', x, g_y1 - 0.4)
            x += 0.75
        # VBUS feeder vias (to the L3 VBUS strip) at the right end of the cap comb
        for i in range(3):
            for j in range(2):
                R.via('VBUS', cx1 + 0.6 + i * 0.8, vb_y1 - 0.45 - j * 0.8)
        # L1: switch-node pour around the inductor pad, covering the via-in-pad field
        R.rect(sw, F, lp[0] - 0.1, min(ls_y0, lp[1]) - 0.2, max(sx1, lp[2]) + 0.1,
               max(hs_y1, lp[3]) + 0.2, prio=6, name=f'SW{ph}_L1')
        # L1: LX pour from the inductor output pad to the shunt current pad
        lxp, rsp = R.pad('L1', d['lx']), R.pad(d['rs'], 1)
        # (two rectangles: the band joining the pads keeps clear of the shunt's sense pads)
        R.rect(LXN[ph], F, lxp[0] - 0.1, lxp[1] - 0.1, lxp[2] + 0.1, lxp[3] + 0.1, prio=6, name=f'LX{ph}')
        R.rect(LXN[ph], F, lxp[2] - 0.6, rsp[1] - 0.1, rsp[2] + 0.1, rsp[3] + 0.1, prio=5, name=f'LX{ph}b')


def input_path(R):
    j1 = R.pad('J1', 1)
    r96a, r96b = R.pad('R96', 1), R.pad('R96', 2)
    q2s, q2d = R.pad('Q2', 2), R.pad('Q2', 3)
    q1s, q1d = R.pad('Q1', 2), R.pad('Q1', 3)
    rs1a, rs1b = R.pad('RS1', 1), R.pad('RS1', 4)
    d6 = R.pad('D6', 1)
    f1a, f1b = R.pad('F1', 1), R.pad('F1', 2)
    jx0 = j1[0] - 0.3
    # J1 terminal: top and bottom pours reaching F1 pad 1 (top) and R96 pad 1 (bottom)
    R.zone('J1-Pin_1', F, [(f1a[0] - 0.3, f1a[1] - 0.3), (jx0, f1a[1] - 0.3), (jx0, 0.35), (W - 2.4, 0.35),
                           (W - 0.35, 2.4), (W - 0.35, j1[3] + 0.15), (jx0, j1[3] + 0.15),
                           (jx0, f1a[3] + 0.3), (f1a[0] - 0.3, f1a[3] + 0.3)], prio=4, name='J1_top')
    R.zone('J1-Pin_1', B, [(r96a[0] - 0.3, r96a[1] - 0.5), (jx0, r96a[1] - 0.5), (jx0, 0.35), (W - 2.4, 0.35),
                           (W - 0.35, 2.4), (W - 0.35, j1[3] + 0.15), (r96a[0] - 0.3, j1[3] + 0.15)],
           prio=4, name='J1_bot')
    # D6-A1: R96 pad 2 / F1 pad 2 -> Q2 source pins, TVS D6, VOM1271 (bottom pour + top pad pour)
    R.zone('D6-A1', B, [(d6[0] - 0.3, q2s[1] - 0.6), (d6[0] - 0.3, d6[3] + 0.3), (d6[2] + 0.4, d6[3] + 0.3),
                        (d6[2] + 0.4, q2s[3] + 0.3), (q2s[2] + 0.5, q2s[3] + 0.3), (q2s[2] + 0.5, r96b[3] + 0.6),
                        (r96b[2] + 0.3, r96b[3] + 0.6), (r96b[2] + 0.3, 1.0), (r96b[0] - 4.0, 1.0),
                        (r96b[0] - 4.0, q2s[1] - 0.6)], prio=4, name='D6A1_bot')
    R.rect('D6-A1', F, f1b[0] - 0.3, f1b[1] - 0.3, f1b[2] + 0.3, f1b[3] + 0.3, prio=4, name='D6A1_top')
    for i in range(3):
        for j in range(2):
            R.via('D6-A1', f1b[0] + 0.6 + i * 1.1, f1b[1] + 0.8 + j * 1.6)
            R.via('J1-Pin_1', f1a[0] + 0.6 + i * 1.1, f1a[1] + 0.8 + j * 1.4)
    # VIN_PROT: Q2 drain tab -> RS1 pad 1
    R.rect('VIN_PROT', B, q2d[0] - 0.2, q2d[1] - 0.2, q2d[2] + 0.2, q2d[3] + 0.2, prio=4, name='VIN_PROT')
    R.rect('VIN_PROT', B, rs1a[0] - 0.2, q2d[3] - 0.5, rs1a[2] + 0.2, rs1a[3] + 0.2, prio=3, name='VIN_PROTb')
    # Q1 drain: RS1 pad 4 -> Q1 tab
    R.rect('Q1-D', B, q1d[0] - 0.2, q1d[1] - 0.2, q1d[2] + 0.2, q1d[3] + 0.2, prio=4, name='Q1_D')
    R.rect('Q1-D', B, q1d[2] - 0.5, rs1b[1] - 0.2, rs1b[2] + 0.2, rs1b[3] + 0.2, prio=3, name='Q1_Db')
    # VBUS out of Q1 source pins, with vias into the L3 feeder
    R.rect('VBUS', B, q1s[0] - 0.4, q1s[1] - 0.3, q1s[2] + 0.3, q1s[3] + 0.2, prio=4, name='VBUS_Q1')
    for i in range(3):
        for j in range(5):
            R.via('VBUS', q1s[0] - 0.05 + i * 1.3, q1s[1] + 0.6 + j * 1.7)


def planes(R):
    hv, lv = hv_region(), lv_region()
    # L2: solid PGND / GND_ISO
    R.zone('PGND', L2, hv, prio=0, name='L2_PGND')
    R.zone('GND_ISO', L2, lv, prio=0, name='L2_GND_ISO')
    # L3: PGND default, VBUS feeder (bulk caps -> half-bridge cap combs, Q1 source), +24 V output
    # L3 return plane directly under each commutation loop (LS source vias -> stack -> cap PGND
    # vias); the L3 catch-all PGND / +5V_ISO pours are added after the signal routing
    for ph, d in PHASE.items():
        ls_top = min(R.pad(d['ls'], n)[1] for n in range(1, 8))
        capg = max(R.pad(c, 2)[3] for c in d['caps'])
        x0 = min(R.pad(c, 1)[0] for c in d['caps']) - 0.4
        R.rect('PGND', L3, x0, ls_top - 1.8, 41.3, capg + 1.2, prio=1, name=f'L3_PGND_loop{ph}')
    c5, c6 = R.pad('C5', 1), R.pad('C6', 1)
    q1s = R.pad('Q1', 2)
    R.zone('VBUS', L3, [(41.3, 2.5), (c6[2] + 1.5, 2.5), (c6[2] + 1.5, 12.0), (47.5, 12.0),
                        (max(47.5, q1s[2] + 0.5), 26.5), (max(47.5, q1s[2] + 0.5), 42.5), (41.3, 42.5)],
           prio=2, name='L3_VBUS')
    R.zone('+24V', L3, [(49.8, 21.5), (W - 0.35, 21.5), (W - 0.35, H - 2.4), (W - 2.4, H - 0.35),
                        (49.8, H - 0.35)], prio=1, name='L3_24V')
    # L3: D6-A1 input path is on L4; keep L3 PGND there
    # L1 (top): +24 V output, PGND at the return terminals, VBUS at the bulk caps, defaults
    R.zone('+24V', F, [(49.8, 21.0), (W - 14.3, 21.0), (W - 14.3, 41.05), (W - 0.35, 41.05),
                       (W - 0.35, H - 2.4), (W - 2.4, H - 0.35), (49.8, H - 0.35)], prio=3, name='L1_24V')
    R.rect('PGND', F, W - 13.2, 12.95, W - 0.35, 40.95, prio=3, name='L1_PGND_terminals')


def finish(R):
    """After the signal routing: outer-layer ground pours and stitching vias around the traces."""
    hv, lv = hv_region(), lv_region()
    R.zone('PGND', F, hv, prio=0, name='L1_PGND')
    R.zone('GND_ISO', F, lv, prio=0, name='L1_GND_ISO')
    R.zone('PGND', B, hv, prio=0, name='L4_PGND')
    R.zone('GND_ISO', B, lv, prio=0, name='L4_GND_ISO')
    R.zone('PGND', L3, hv, prio=0, name='L3_PGND')
    R.zone('+5V_ISO', L3, lv, prio=0, name='L3_5V_ISO')
    for x in [55.0 + 2.5 * i for i in range(7)]:          # +24 V top <-> L3 in the output area
        for y in [22.5 + 2.5 * j for j in range(12)]:
            R.via('+24V', x, y, stitch=True)
    for x in [29.2 + 1.3 * i for i in range(44)]:
        for y in [1.2 + 1.3 * j for j in range(41)]:
            R.via('PGND', x, y, stitch=True)
    for x in [1.4 + 1.3 * i for i in range(18)]:
        for y in [1.4 + 1.3 * j for j in range(40)]:
            R.via('GND_ISO', x, y, stitch=True)


def main(stage):
    board = pcbnew.LoadBoard(PCB)
    R = Router(board)
    if stage == 'power':
        old = [z for z in board.Zones() if not z.GetIsRuleArea()] + list(board.GetTracks())
        for item in old:                  # start from the placed board without copper
            board.Remove(item)
        board.SetLayerType(L2, pcbnew.LT_POWER)          # L2 is a plane (autorouter: no traces)
        power_stage(R)
        input_path(R)
        planes(R)
    else:
        R.load_existing()
        finish(R)
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    if stage != 'power':
        print(f'pruned {R.prune_stitching()} unconnected stitching vias')
        filler.Fill(board.Zones())
    pcbnew.SaveBoard(PCB, board)
    print(f'{len(R.vias)} vias, {len(list(board.Zones()))} zones -> {PCB}')


if __name__ == '__main__':
    import sys
    main(sys.argv[1] if len(sys.argv) > 1 else 'power')
