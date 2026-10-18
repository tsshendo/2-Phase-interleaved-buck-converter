"""Stage 4 step 2: autoroute the remaining nets with Freerouting (Specctra DSN / SES round trip).

    python kicad/tools/route_signals.py <freerouting.exe> <work_dir> [passes]

The board must already hold the power copper from `route_power.py power` (the zones are exported as
planes, L2 is a power layer, the barrier rule area becomes a keep-out). Freerouting is run headless
with telemetry and analytics off; its user-data folder is kept in <work_dir>.
Freerouting: https://github.com/freerouting/freerouting (GPL-3.0), tested with v2.4.1.
"""
import os
import subprocess
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.normpath(os.path.join(HERE, '..', 'ECE533_Guide', 'ECE533_Guide.kicad_pcb'))


def disjoint_planes(board, gap=0.3):
    """KiCad resolves overlapping zones by priority, but the DSN only carries outlines. On the export
    copy, cut every zone by the higher-priority zones of other nets on the same layer."""
    zones = [z for z in board.Zones() if not z.GetIsRuleArea()]
    for z in zones:
        poly = z.Outline()
        for o in zones:
            if (o is z or o.GetLayer() != z.GetLayer() or o.GetNetCode() == z.GetNetCode()
                    or o.GetAssignedPriority() <= z.GetAssignedPriority()):
                continue
            cut = pcbnew.SHAPE_POLY_SET(o.Outline())
            cut.Inflate(pcbnew.FromMM(gap), pcbnew.CORNER_STRATEGY_CHAMFER_ALL_CORNERS, pcbnew.FromMM(0.05))
            poly.BooleanSubtract(cut)
        poly.Simplify()


def nettie_keepouts(board, margin=0.25):
    """Net-tie copper (Kelvin shunt sense strips, NT1-NT4) has no net, so the DSN does not carry it.
    On the export copy, cover it with track/via keep-outs on its layer."""
    for f in board.GetFootprints():
        for g in f.GraphicalItems():
            if not g.IsOnCopperLayer():
                continue
            bb = g.GetBoundingBox()
            m = pcbnew.FromMM(margin)
            z = pcbnew.ZONE(board)
            z.SetIsRuleArea(True)
            z.SetLayer(g.GetLayer())
            z.SetDoNotAllowTracks(True)
            z.SetDoNotAllowVias(True)
            z.SetDoNotAllowZoneFills(False)
            z.SetDoNotAllowPads(False)
            z.SetDoNotAllowFootprints(False)
            o = z.Outline()
            o.NewOutline()
            for x, y in ((bb.GetLeft() - m, bb.GetTop() - m), (bb.GetRight() + m, bb.GetTop() - m),
                         (bb.GetRight() + m, bb.GetBottom() + m), (bb.GetLeft() - m, bb.GetBottom() + m)):
                o.Append(int(x), int(y))
            board.Add(z)


def plane_keepouts(board, shrink=0.05):
    """Freerouting does not treat planes on signal layers as obstacles for other nets, so it would cut
    the power pours. On the export copy, cover each pour's filled copper with a track/via keep-out
    (the fill already leaves clearance around other-net pads, so those stay reachable)."""
    n = 0
    for z in [z for z in board.Zones() if not z.GetIsRuleArea()]:
        layer = z.GetLayer()
        if layer == pcbnew.In1_Cu:              # plane layer: not routed anyway
            continue
        fill = pcbnew.SHAPE_POLY_SET(z.GetFilledPolysList(layer))
        if fill.OutlineCount() == 0:
            continue
        fill.Inflate(-pcbnew.FromMM(shrink), pcbnew.CORNER_STRATEGY_CHAMFER_ALL_CORNERS, pcbnew.FromMM(0.05))
        fill.Simplify()
        for i in range(fill.OutlineCount()):
            k = pcbnew.ZONE(board)
            k.SetIsRuleArea(True)
            k.SetLayer(layer)
            k.SetDoNotAllowTracks(True)
            k.SetDoNotAllowVias(True)
            k.SetDoNotAllowZoneFills(False)
            k.SetDoNotAllowPads(False)
            k.SetDoNotAllowFootprints(False)
            o = k.Outline()                      # copy the points (SetOutline would take ownership)
            o.NewOutline()
            ch = fill.COutline(i)
            for j in range(ch.PointCount()):
                p = ch.CPoint(j)
                o.Append(p.x, p.y)
            board.Add(k)
            n += 1
    return n


def fix_widths(board, wmin=0.15):
    """Freerouting necks some tracks down to 0.12 mm at pads; JLC 2 oz needs 0.15 mm."""
    n = 0
    for t in board.GetTracks():
        if t.GetClass() != 'PCB_VIA' and t.GetWidth() < pcbnew.FromMM(wmin):
            t.SetWidth(pcbnew.FromMM(wmin))
            n += 1
    return n


def main(fr_exe, work, passes=40):
    os.makedirs(work, exist_ok=True)
    dsn, ses = os.path.join(work, 'board.dsn'), os.path.join(work, 'board.ses')
    export = pcbnew.LoadBoard(PCB)
    disjoint_planes(export)
    nettie_keepouts(export)
    print(f'{plane_keepouts(export)} pour keep-outs on the export copy')
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
    print(' '.join(cmd))
    with open(os.path.join(work, 'freerouting.log'), 'w', encoding='utf-8') as log:
        r = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT)
    if r.returncode != 0 or not os.path.exists(ses):
        raise SystemExit(f'Freerouting failed (exit {r.returncode}); see {work}/freerouting.log')
    if not pcbnew.ImportSpecctraSES(board, ses):
        raise SystemExit('SES import failed')
    print(f'widened {fix_widths(board)} narrow segments')
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(PCB, board)
    n = sum(1 for t in board.GetTracks() if t.GetClass() != 'PCB_VIA')
    print(f'imported {n} track segments -> {PCB}')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 40)
