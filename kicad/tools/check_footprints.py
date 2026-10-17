"""Check that every symbol pin has a footprint pad and every footprint pad has a pin.

Usage (KiCad Python):  python check_footprints.py build.net
Footprints are loaded from the project fp-lib-table libraries and KiCad's standard libraries.
"""
import collections
import os
import sys

import pcbnew

from sexp import child, find, parse

HERE = os.path.dirname(os.path.abspath(__file__))
PRJ = os.path.normpath(os.path.join(HERE, '..', 'ECE533_Guide'))
STD = os.environ.get('KICAD10_FOOTPRINT_DIR', r'C:\Program Files\KiCad\10.0\share\kicad\footprints')
LIBS = {'ECE533_Mods': os.path.join(PRJ, 'ECE533_Mods.pretty'),
        'ECE533_Vendor': os.path.normpath(os.path.join(PRJ, '..', 'lib', 'vendor', 'ECE533_Vendor.pretty'))}


def lib_path(lib):
    return LIBS.get(lib, os.path.join(STD, lib + '.pretty'))


def main(net):
    tree = parse(open(net, encoding='utf-8').read())
    fps, pins = {}, collections.defaultdict(set)
    for comp in find(tree, 'comp'):
        ref = child(comp, 'ref')[1]
        fp = child(comp, 'footprint')
        fps[ref] = fp[1] if fp else ''
    for netn in find(tree, 'net'):
        for node in find(netn, 'node'):
            pins[child(node, 'ref')[1]].add(child(node, 'pin')[1])
    cache, bad, ok = {}, 0, 0
    for ref in sorted(fps):
        fpid = fps[ref]
        if not fpid:
            print(f'{ref}: no footprint')
            bad += 1
            continue
        if fpid not in cache:
            lib, name = fpid.split(':', 1)
            try:
                f = pcbnew.FootprintLoad(lib_path(lib), name)
            except Exception:
                f = None
            cache[fpid] = None if f is None else {p.GetNumber() for p in f.Pads() if p.GetNumber()}
        pads = cache[fpid]
        if pads is None:
            print(f'{ref}: footprint {fpid} not found')
            bad += 1
            continue
        missing = pins[ref] - pads
        unused = pads - pins[ref]
        if missing:
            print(f'{ref} ({fpid}): symbol pins without pad: {sorted(missing)}')
            bad += 1
        elif unused:
            print(f'{ref} ({fpid}): pads without symbol pin (check): {sorted(unused)}')
        else:
            ok += 1
    print(f'{ok} parts match, {bad} errors, {len(fps)} parts')
    return bad


if __name__ == '__main__':
    sys.exit(1 if main(sys.argv[1]) else 0)
