"""PowerModule: power copper (report polygon pours), via arrays, then Freerouting for the signals.

    python kicad/tools/pm_route.py power                 # pours + vias on PowerModule.kicad_pcb
    python kicad/tools/pm_route.py signals <fr.exe> <dir> # Freerouting round trip for the rest
    python kicad/tools/pm_route.py finish                # refill, stitching check

Copper planes as in the report (pp. 7-9, 20-23): 2nd Cu plane = L4 (MOSFET side, patterned power
path), 1st Cu plane = L1 (inductor / drivers / isolators, VOUT and VBUS planes), interstitial
shield = L2 + L3 (continuous, SHIELD net = centre tap of the input decoupling caps, antipads at
every feedthrough). Per phase on L4: HS left, LS right, strips vertical; the switch-node comb runs
along the outer ends of the strips to the inductor pad, the VBUS (HS drain) and PGND (LS source)
combs along the inner ends, with the centre-tapped ceramics bridging them (lateral loop over the
L3 shield 0.1 mm away).
"""
import os
import sys

import pcbnew

import route_power as rp

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.normpath(os.path.join(HERE, '..', 'PowerModule', 'PowerModule.kicad_pcb'))
F, B, L2, L3 = pcbnew.F_Cu, pcbnew.B_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu
W, H = rp.W, rp.H
VBUS, VOUT, PGND, SHIELD, GND = 'Net-(J1-Pin_1)', 'Net-(J2-Pin_1)', 'GNDPWR', '/SHIELD', 'GND'
SW = {1: '/Gate_Drive/KS1', 2: '/Gate_Drive/KS2'}
HOLES = ((21.5, 4.0), (21.5, 50.0), (69.6, 18.0), (69.6, 36.0))
VIA_STD = rp.VIA_STD
VIA_PAD = (0.2, 0.5)            # via-in-pad, filled and capped (JLC: 0.2 drill, 0.15 ring)
LV_X = 16.1                     # barrier band 16.3-19.7
HV_X0 = 19.9


def circle_keepouts(board, r=3.4):
    import math
    for i, (x, y) in enumerate(HOLES, 1):
        z = pcbnew.ZONE(board)
        z.SetIsRuleArea(True)
        z.SetLayerSet(pcbnew.LSET.AllCuMask())
        z.SetDoNotAllowTracks(True)
        z.SetDoNotAllowVias(True)
        z.SetDoNotAllowZoneFills(True)
        z.SetDoNotAllowPads(False)
        z.SetDoNotAllowFootprints(False)
        z.SetZoneName(f'H{i}_keepout')
        o = z.Outline()
        o.NewOutline()
        for k in range(24):
            a = 2 * math.pi * k / 24
            o.Append(rp.mm(rp.X0 + x + r * math.cos(a)), rp.mm(rp.Y0 + y + r * math.sin(a)))
        board.Add(z)


def power(R):
    b = R.b
    for lay in (L2, L3):                    # shield planes: not routed
        b.SetLayerType(lay, pcbnew.LT_POWER)
    circle_keepouts(b)
    # ---- L4: 2nd Cu plane (MOSFET side) ---------------------------------------------------------
    # switch nodes: outer strip ends of both FETs, out to the inductor pad (phase 2 also takes in
    # the HS SK pad, which sits on the inner side)
    # (the bands start right of the HS SK pad, so the SK pad only feeds the Kelvin island below)
    R.zone(SW[1], B, [(31.45, 14.4), (46.9, 14.4), (46.9, 21.2), (42.6, 21.2), (42.6, 18.4), (31.45, 18.4)],
           prio=6, name='SW1_L4')
    R.zone(SW[2], B, [(31.45, 35.6), (42.6, 35.6), (42.6, 32.8), (46.9, 32.8), (46.9, 40.4), (31.45, 40.4)],
           prio=6, name='SW2_L4')
    # Kelvin islands: HS SK pad -> island under the HS driver (its reference plane and the return
    # under its gate trace); joined to the switch node only inside the FET
    R.zone(SW[1], B, [(24.6, 15.1), (29.6, 15.1), (29.6, 17.4), (30.9, 17.4), (30.9, 19.4), (29.6, 19.4),
                      (29.6, 20.7), (24.6, 20.7)], prio=6, name='KS1_island_L4')
    R.zone(SW[2], B, [(24.6, 33.3), (30.9, 33.3), (30.9, 35.2), (29.6, 35.2), (29.6, 42.6), (24.6, 42.6)],
           prio=6, name='KS2_island_L4')
    # VBUS: HS drain combs (inner strip ends), bus column on the left, strip along the top edge to
    # the bulk capacitor and J1
    # (left edge kept off x 20.3-21.6: L4 channel for the isolator output cross-overs)
    R.zone(VBUS, B, [(25.2, 0.6), (82.4, 0.6), (85.2, 3.4), (85.2, 13.7), (24.3, 13.7), (24.3, 21.0),
                     (29.5, 21.0), (29.5, 21.3), (31.35, 21.3), (31.35, 20.0), (36.1, 20.0), (36.1, 33.9),
                     (31.35, 33.9), (31.35, 32.7), (22.6, 32.7), (22.6, 21.0), (21.7, 21.0), (21.7, 7.6),
                     (25.2, 7.6)], prio=5, name='VBUS_L4')
    # centre tap of the input ceramics (both phases) = shield return terminal
    R.rect(SHIELD, B, 35.4, 21.9, 38.25, 32.1, prio=6, name='SHIELD_tap_L4')
    # PGND: LS source combs (inner strip ends) and the return to J3, under the inductor
    R.zone(PGND, B, [(38.5, 20.0), (42.55, 20.0), (42.55, 21.6), (85.2, 21.6), (85.2, 50.6), (82.4, 53.4),
                     (38.5, 53.4)], prio=4, name='PGND_L4')
    R.rect(PGND, B, 36.5, 32.4, 38.6, 34.0, prio=3, name='PGND_Q5_SK')
    # PGND tongue through the VBUS strip to the input bulk capacitor's '-' pin (L1 and L4)
    R.rect(PGND, B, 62.4, 8.0, 65.6, 21.8, prio=6, name='PGND_C6_L4')
    R.rect(PGND, F, 62.4, 8.0, 65.6, 20.6, prio=6, name='PGND_C6_L1')
    # ---- L1: 1st Cu plane -----------------------------------------------------------------------
    R.rect(SW[1], F, 42.6, 14.4, 46.9, 21.2, prio=6, name='SW1_L1')
    R.rect(SW[2], F, 42.6, 32.8, 46.9, 39.6, prio=6, name='SW2_L1')
    R.zone(VOUT, F, [(52.9, 21.0), (85.2, 21.0), (85.2, 33.6), (72.4, 33.6), (72.4, 53.4), (52.9, 53.4)],
           prio=5, name='VOUT_L1')
    R.zone(VBUS, F, [(41.0, 0.6), (82.4, 0.6), (85.2, 3.4), (85.2, 13.7), (41.0, 13.7)], prio=5,
           name='VBUS_L1')
    R.zone(PGND, F, [(72.8, 34.2), (85.2, 34.2), (85.2, 50.6), (82.4, 53.4), (72.8, 53.4)], prio=4,
           name='PGND_J3_L1')
    # ---- L2 / L3: interstitial shield -----------------------------------------------------------
    for lay, nm in ((L2, 'SHIELD_L2'), (L3, 'SHIELD_L3')):
        R.zone(SHIELD, lay, [(HV_X0, 0.6), (82.4, 0.6), (85.2, 3.4), (85.2, 50.6), (82.4, 53.4),
                             (HV_X0, 53.4)], prio=0, solid=False, name=nm)
    vias(R)


def catch_all(R):
    """After routing: PGND fills the rest of L1 / L4 on the power side, GND on the J4 side."""
    R.zone(PGND, B, [(HV_X0, 0.6), (85.2, 0.6), (85.2, 53.4), (HV_X0, 53.4)], prio=1, min_w=0.3,
           name='PGND_L4_fill')
    R.zone(PGND, F, [(HV_X0, 0.6), (85.2, 0.6), (85.2, 53.4), (HV_X0, 53.4)], prio=0, min_w=0.3,
           name='PGND_L1_fill')
    for lay, nm in ((F, 'GND_L1'), (B, 'GND_L4')):
        R.zone(GND, lay, [(3.4, 0.6), (LV_X, 0.6), (LV_X, 53.4), (3.4, 53.4), (0.6, 50.6), (0.6, 3.4)],
               prio=0, min_w=0.3, name=nm)
    # stitching on a grid; vias that do not land in fill of their net on two layers are pruned
    R.vias = [v for v in R.vias]            # existing vias (load_existing) keep stitching 0.9 mm away
    near = lambda x, y: any(abs(v[0] - x) < 0.9 and abs(v[1] - y) < 0.9 for v in R.vias)
    for i in range(int((85.0 - HV_X0) / 1.6)):
        for j in range(33):
            x, y = HV_X0 + 0.6 + i * 1.6, 1.2 + j * 1.6
            if not near(x, y):
                R.via(PGND, x, y, stitch=True)
    for i in range(9):
        for j in range(33):
            x, y = 1.4 + i * 1.6, 1.2 + j * 1.6
            if not near(x, y):
                R.via(GND, x, y, stitch=True)


def vias(R):
    # switch node: via-in-pad (filled, capped) in the inductor pads, plain vias in the L4 band
    for ph, pad in ((1, '4'), (2, '3')):
        x0, y0, x1, y1 = R.pad('L1', pad)
        for i in range(5):
            for j in range(5):
                R.via(SW[ph], x0 + 0.45 + i * (x1 - x0 - 0.9) / 4, y0 + 0.45 + j * (y1 - y0 - 0.9) / 4,
                      VIA_PAD, same_pad_ok=True)
        ys = (14.95, 15.85) if ph == 1 else (37.95, 38.85)
        for y in ys:
            for i in range(4):
                R.via(SW[ph], 43.3 + i * 1.0, y)
    # gate and Kelvin feedthroughs (via-in-pad) to the drivers on L1
    for ph, (hs, ls) in ((1, ('Q3', 'Q4')), (2, ('Q6', 'Q5'))):
        for ref in (hs, ls):
            gx0, gy0, gx1, gy1 = R.pad(ref, 1)
            sx0, sy0, sx1, sy1 = R.pad(ref, 2)
            gate_net = R.fp(ref).Pads()[0].GetNetname()
            for p in R.fp(ref).Pads():
                if p.GetNumber() == '1':
                    gate_net = p.GetNetname()
                if p.GetNumber() == '2':
                    sk_net = p.GetNetname()
            R.via(gate_net, (gx0 + gx1) / 2, (gy0 + gy1) / 2, VIA_PAD, same_pad_ok=True)
            if ref == ls:                   # LS Kelvin up to L1; the HS SK pad feeds its island
                R.via(sk_net, (sx0 + sx1) / 2, sy1 - 0.5, VIA_PAD, same_pad_ok=True)
    # HS drivers: GND pin and VDD capacitor down to the Kelvin island
    for ph, drv, cap in ((1, 'U1', 'C7'), (2, 'U3', 'C9')):
        x0, y0, x1, y1 = R.pad(drv, 2)
        xv, yv = x0 - 0.45, (y0 + y1) / 2
        R.via(SW[ph], xv, yv, VIA_PAD)
        R.track(SW[ph], F, [((x0 + x1) / 2, yv), (xv, yv)], 0.3)
        x0, y0, x1, y1 = R.pad(cap, 2)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        for xv, yv in ((cx - 0.3, y1 + 0.5), (cx + 0.62, cy - 0.55), (cx - 0.3, y0 - 0.5)):
            if R.via(SW[ph], xv, yv, VIA_PAD):      # first spot clear of the HS gate pad / parts
                R.track(SW[ph], F, [(cx, cy), (xv, yv)], 0.3)
                break
    # isolator outputs: each B2 output feeds IN+ of one driver and IN- of the other, so it has to
    # cross B1 once; locked L4 hop beside the isolator
    hops = {'Net-(AT1-B2)': ('R1', 'R6', 21.2, 19.75, False), 'Net-(AT2-B2)': ('R7', 'R4', 20.54, 0.95, True)}
    for net, (near_r, far_r, xh, yv, under) in hops.items():
        x0, y0, x1, y1 = R.pad(near_r, 2)
        ax, ay = (x0 + x1) / 2, (y0 + y1) / 2
        x0, y0, x1, y1 = R.pad(far_r, 2)
        bx, by = (x0 + x1) / 2, (y0 + y1) / 2
        if under:       # via right under the near pad, the dog-leg on L4 (keeps AT2 pin 5 open on L1)
            v1 = (ax, ay + yv)
            segs = [(F, [(ax, ay), v1]), (B, [v1, (xh, v1[1]), (xh, by)]), (F, [(xh, by), (bx, by)])]
        else:
            v1 = (xh, yv)
            segs = [(F, [(ax, ay), (ax, yv), v1]), (B, [v1, (xh, by)]), (F, [(xh, by), (bx, by)])]
        for lay, pts in segs:
            R.track(net, lay, pts, 0.25)
        for v in (v1, (xh, by)):
            R.via(net, v[0], v[1], VIA_PAD, check=False)
    # +5V_iso from PS1 pin 4 (THT) to the isolator output supplies, on L4 beside the hops
    x0, y0, x1, y1 = R.pad('PS1', 4)
    px, py = (x0 + x1) / 2, (y0 + y1) / 2
    x0, y0, x1, y1 = R.pad('AT1', 8)
    ax, ay = (x0 + x1) / 2, (y0 + y1) / 2
    R.track('+5V_iso', B, [(px, py), (px, 21.3), (20.5, 20.0), (20.5, ay)], 0.3)
    R.via('+5V_iso', 20.5, ay, VIA_PAD, check=False)              # in AT1 pad 8 (filled)
    x0, y0, x1, y1 = R.pad('AT2', 8)
    bx, by = (x0 + x1) / 2, (y0 + y1) / 2
    R.track('+5V_iso', B, [(px, py), (px, by)], 0.3)
    R.via('+5V_iso', px, by, VIA_PAD, check=False)
    R.track('+5V_iso', F, [(px, by), (bx, by)], 0.3)
    for t in R.b.GetTracks():
        if t.GetNetname() in ('Net-(AT1-B2)', 'Net-(AT2-B2)', '+5V_iso'):
            t.SetLocked(True)
    # single-point Kelvin junction: island -> switch-node band, next to the HS FET
    R.track(SW[1], B, [(29.4, 16.0), (31.9, 16.0)], 0.4)
    R.track(SW[2], B, [(29.4, 40.0), (31.9, 40.0)], 0.4)
    # shield return: the centre-tap island to L2 / L3
    for y in (25.0, 27.0, 29.0):
        R.via(SHIELD, 36.8, y)
    # VBUS L1 / L4 strip stitching, PGND stitching (L1 fills to L4)
    for x in range(42, 84, 2):
        for y in (2.0, 4.0, 10.0, 12.2):
            R.via(VBUS, x + 0.0, y, stitch=True)
    for x in range(48, 72, 2):
        for y in (49.5, 51.5):
            R.via(PGND, x + 0.0, y, stitch=True)
    for x in range(74, 84, 2):
        for y in range(36, 52, 2):
            R.via(PGND, x + 0.5, y + 0.0, stitch=True)


def signals(fr_exe, work, passes=60):
    """Freerouting on L1 / L4 only (L2 / L3 are shield planes); see route_signals.py."""
    import subprocess
    import route_signals as rs
    os.makedirs(work, exist_ok=True)
    dsn, ses = os.path.join(work, 'pm.dsn'), os.path.join(work, 'pm.ses')
    export = pcbnew.LoadBoard(PCB)
    rs.disjoint_planes(export)
    print(f'{rs.plane_keepouts(export)} pour keep-outs on the export copy')
    if not pcbnew.ExportSpecctraDSN(export, dsn):
        raise SystemExit('DSN export failed')
    board = pcbnew.LoadBoard(PCB)
    if os.path.exists(ses):
        os.remove(ses)
    cmd = [fr_exe, '-de', dsn, '-do', ses, '-mp', str(passes), '-l', 'en',
           '--gui.enabled=false', '--router.optimizer.enabled=false',
           '--profile.allow_telemetry=false', '--profile.allow_contact=false',
           '--usage_and_diagnostic_data.disable_analytics=true',
           f'--user_data_path={os.path.join(work, "fr_user")}']
    with open(os.path.join(work, 'freerouting.log'), 'w', encoding='utf-8') as log:
        r = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT)
    if r.returncode != 0 or not os.path.exists(ses):
        raise SystemExit(f'Freerouting failed (exit {r.returncode}); see {work}/freerouting.log')
    if not pcbnew.ImportSpecctraSES(board, ses):
        raise SystemExit('SES import failed')
    print(f'widened {rs.fix_widths(board)} narrow segments')
    fill(board)
    pcbnew.SaveBoard(PCB, board)
    print(f'imported {sum(1 for t in board.GetTracks() if t.GetClass() != "PCB_VIA")} segments')


def fill(board):
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())


def main(stage, *args):
    if stage == 'signals':
        signals(*args)
        return
    board = pcbnew.LoadBoard(PCB)
    rp.PCB = PCB
    rp.BAR = (16.3, 19.7)
    rp.SWN = SW
    R = rp.Router(board)
    if stage == 'power':
        power(R)
        fill(board)
        print(f'stitching vias removed: {R.prune_stitching()}')
        fill(board)
    elif stage == 'finish':
        R.load_existing()
        catch_all(R)
        fill(board)
        print(f'stitching vias removed: {R.prune_stitching()}')
        fill(board)
    pcbnew.SaveBoard(PCB, board)
    print(f'{len(R.vias)} vias placed -> {PCB}')


if __name__ == '__main__':
    main(*sys.argv[1:])
