"""Tiny schematic builder for KiCad (writes KiCad 9 format, opened by KiCad 10).

Connections are made with short wire stubs ending in a net label, a
hierarchical label or a power symbol, so every connection is explicit and the
sheets stay readable. Coordinates are in mm, schematic Y grows downwards.
"""
import math
import os
import uuid as _uuid

from sexp import dump
from kilib import flatten, load_lib, std_lib_path, symbol_pins

G = 2.54
PROJECT = 'ECE533_Guide'
GROUNDS = {'PGND', 'GND_ISO', 'GND'}
RAIL_TAGS_ON_SIDE_PINS = True
HERE = os.path.dirname(os.path.abspath(__file__))
PROJ_LIB = os.path.join(HERE, '..', 'ECE533_Guide', 'ECE533.kicad_sym')

_ns = _uuid.UUID('6f1e2d1c-533a-4c0b-9a50-ece533000000')


def uid(*parts):
    """Deterministic UUID so regenerating doesn't churn the files."""
    return str(_uuid.uuid5(_ns, '/'.join(str(p) for p in parts)))


def q(s):
    return '"' + str(s).replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n') + '"'


def f(v):
    s = ('%.4f' % v).rstrip('0').rstrip('.')
    return '0' if s in ('-0', '') else s


def snap(v):
    return round(v / 1.27) * 1.27


# --------------------------------------------------------------------------
class SymbolDef:
    def __init__(self, lib_id):
        self.lib_id = lib_id
        lib, name = lib_id.split(':')
        path = PROJ_LIB if lib == 'ECE533' else std_lib_path(lib)
        syms = load_lib(path)
        node = flatten(syms, name)
        self.node = node
        self.pins = symbol_pins(node)
        self.is_power = any(isinstance(c, list) and c and c[0] == 'power' for c in node)

    def embedded(self):
        node = [x for x in self.node]
        node[1] = self.lib_id
        return dump(node, 2)

    def pin(self, key):
        """Find pin by number or by name (first visible match)."""
        for p in self.pins:
            if p['number'] == key and not p['hidden']:
                return p
        for p in self.pins:
            if p['name'] == key and not p['hidden']:
                return p
        for p in self.pins:
            if p['number'] == key:
                return p
        raise KeyError(f'{self.lib_id}: no pin {key!r}')


_defs = {}
_power_count = 0


def sdef(lib_id):
    if lib_id not in _defs:
        _defs[lib_id] = SymbolDef(lib_id)
    return _defs[lib_id]


def rot(x, y, r):
    a = math.radians(r)
    return x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)


# --------------------------------------------------------------------------
class Part:
    def __init__(self, sheet, lib_id, refs, value, x, y, r=0, fields=None,
                 footprint=None, dnp=False, in_bom=True, ref_pos=None, val_pos=None,
                 hide_value=False, mirror=False):
        self.sheet, self.d = sheet, sdef(lib_id)
        self.lib_id, self.refs, self.value = lib_id, refs, value
        self.x, self.y, self.r = x, y, r
        self.mirror = mirror
        self.fields = fields or {}
        self.footprint = footprint
        self.dnp, self.in_bom = dnp, in_bom
        self.ref_pos, self.val_pos = ref_pos, val_pos
        self.hide_value = hide_value
        self.uuid = uid(sheet.file, 'sym', refs if isinstance(refs, str) else refs[0], lib_id, x, y)

    # pin connection point in sheet coordinates + outward direction (dx, dy)
    def pin_at(self, key):
        p = self.d.pin(key)
        sx, sa = p['x'], p['angle']
        if self.mirror:          # KiCad "(mirror y)": flip left/right before rotating
            sx, sa = -sx, (180 - sa) % 360
        px, py = rot(sx, p['y'], self.r)
        ang = (sa + self.r) % 360
        # pin 'angle' points from the connection point into the body
        out = (ang + 180) % 360
        dx, dy = round(math.cos(math.radians(out))), -round(math.sin(math.radians(out)))
        return (round(self.x + px, 4), round(self.y - py, 4)), (dx, dy)

    def text(self, inst_paths):
        d = self.d
        L = ['\t(symbol', f'\t\t(lib_id {q(self.lib_id)})',
             f'\t\t(at {f(self.x)} {f(self.y)} {f(self.r)})'] + \
            (['\t\t(mirror y)'] if self.mirror else []) + ['\t\t(unit 1)',
             '\t\t(exclude_from_sim no)',
             f'\t\t(in_bom {"yes" if self.in_bom and not d.is_power else "no"})',
             '\t\t(on_board yes)', f'\t\t(dnp {"yes" if self.dnp else "no"})',
             f'\t\t(uuid {q(self.uuid)})']
        ref0 = self.refs if isinstance(self.refs, str) else self.refs[0]
        rp = self.ref_pos or self._default_field_pos(0)
        vp = self.val_pos or self._default_field_pos(1)
        L.append(self._prop('Reference', ref0, rp, hide=d.is_power))
        L.append(self._prop('Value', self.value, vp, hide=self.hide_value))
        fp = self.footprint if self.footprint is not None else _sym_prop(d.node, 'Footprint')
        L.append(self._prop('Footprint', fp, (self.x, self.y), hide=True))
        L.append(self._prop('Datasheet', self.fields.pop('Datasheet', _sym_prop(d.node, 'Datasheet')),
                            (self.x, self.y), hide=True))
        L.append(self._prop('Description', _sym_prop(d.node, 'Description'), (self.x, self.y), hide=True))
        for k, v in self.fields.items():
            L.append(self._prop(k, v, (self.x, self.y), hide=True))
        for p in d.pins:
            L.append(f'\t\t(pin {q(p["number"])} (uuid {q(uid(self.uuid, "pin", p["number"]))}))')
        L.append(f'\t\t(instances (project {q(PROJECT)}')
        refs = [self.refs] * len(inst_paths) if isinstance(self.refs, str) else self.refs
        for path, ref in zip(inst_paths, refs):
            L.append(f'\t\t\t(path {q(path)} (reference {q(ref)}) (unit 1))')
        L.append('\t\t))')
        L.append('\t)')
        return '\n'.join(L)

    def _default_field_pos(self, which):
        vis = [p for p in self.d.pins if not p['hidden']]
        pts = [self.pin_at(p['number']) for p in vis]
        xs = [pt[0][0] for pt in pts] or [self.x]
        ys = [pt[0][1] for pt in pts] or [self.y]
        if not self.d.is_power and len(vis) <= 2 or self.lib_id in ('Device:R_Shunt', 'Device:NetTie_2'):
            if (max(ys) - min(ys)) >= (max(xs) - min(xs)):      # vertical 2-pin part
                cy = (max(ys) + min(ys)) / 2
                return (self.x + 2.54, cy - 1.27 + which * 2.54)
            cx = (max(xs) + min(xs)) / 2                       # horizontal 2-pin part
            return (cx - 2.54, self.y - 2.54 if which == 0 else self.y + 3.81)
        if not self.d.is_power and self.lib_id.startswith('ECE533:') or len(vis) > 4:
            # boxes: ref above the top-left corner, value under the bottom-left corner,
            # clear of any pins (and their power symbols) on the top / bottom edges
            top_pins = [pt for pt in pts if pt[1] == (0, -1)]
            bot_pins = [pt for pt in pts if pt[1] == (0, 1)]
            left = min(xs) + 2.54
            top = min(ys) - (6.35 if top_pins else 1.27) - (0 if top_pins else 2.54)
            bot = max(ys) + (6.35 if bot_pins else 2.54)
            if top_pins:
                top = min(pt[0][1] for pt in top_pins) - 6.35
            if bot_pins:
                bot = max(pt[0][1] for pt in bot_pins) + 6.35
            return (left, top) if which == 0 else (left, bot)
        if self.d.is_power:
            # use the library's own field position (above supplies, below grounds)
            key = 'Value' if which else 'Reference'
            for c in self.d.node:
                if isinstance(c, list) and c and c[0] == 'property' and c[1] == key:
                    at = [x for x in c if isinstance(x, list) and x and x[0] == 'at'][0]
                    ox, oy = rot(float(at[1]), float(at[2]), self.r)
                    return (self.x + ox, self.y - oy)
            return (self.x, self.y)
        if len([p for p in self.d.pins if not p['hidden']]) <= 4 and (max(ys) - min(ys)) >= (max(xs) - min(xs)):
            return (self.x + 2.54, self.y - 1.27 + which * 2.54)
        if len([p for p in self.d.pins if not p['hidden']]) <= 4:
            return (self.x, min(ys) - 3.81 + which * 2.0 - 2.0)
        return (min(xs) + 2.54 + which * 0, min(ys) - 3.81 - (0 if which else 2.54))

    def _prop(self, key, val, pos, hide=False):
        x, y = pos
        just = ''
        if key in ('Reference', 'Value') and not hide:
            just = ' (justify left)'
        if self.d.is_power and key == 'Value':
            just = ''
        # KiCad turns field text with the symbol; counter-rotate so text reads horizontally
        ang = 90 if self.r % 180 == 90 else 0
        h = ' (hide yes)' if hide else ''
        return (f'\t\t(property {q(key)} {q(val)} (at {f(x)} {f(y)} {ang}){h}'
                f' (effects (font (size 1.27 1.27)){just}))')


def _sym_prop(node, key):
    for c in node:
        if isinstance(c, list) and c and c[0] == 'property' and c[1] == key:
            return c[2]
    return ''


# --------------------------------------------------------------------------
class Sheet:
    def __init__(self, title, file, paper='A3', comment=''):
        self.title, self.file, self.paper, self.comment = title, file, paper, comment
        self.uuid = uid('sheetfile', file)
        self.parts, self.items = [], []
        self.children = []          # (SheetRef)
        self.inst_paths = []        # instance paths this sheet's symbols get
        self.power_count = 0

    # ---- placement ----
    def add(self, lib_id, refs, value, x, y, r=0, nets=None, **kw):
        p = Part(self, lib_id, refs, value, snap(x), snap(y), r, **kw)
        self.parts.append(p)
        for key, spec in (nets or {}).items():
            self.connect(p, key, spec)
        return p

    def connect(self, part, key, spec, stub=None):
        """spec: 'NET' (local label), '~PGND' (power symbol), '>NAME:in' (hier label),
        'NC' (no-connect), or ('wire', (x, y)) / ('to', part, pin)."""
        (x, y), (dx, dy) = part.pin_at(key)
        if spec == 'NC':
            self.items.append(f'\t(no_connect (at {f(x)} {f(y)}) (uuid {q(uid(self.file, "nc", x, y))}))')
            return
        if isinstance(spec, tuple) and spec[0] == 'to':
            (x2, y2), _ = spec[1].pin_at(spec[2])
            pts = [(x, y), (x2, y), (x2, y2)] if len(spec) < 4 or spec[3] == 'hv' else \
                [(x, y), (x, y2), (x2, y2)]
            self.wire_path(pts)
            return
        if isinstance(spec, tuple) and spec[0] == 'wire':
            pts = [(x, y)] + list(spec[1:])
            self.wire_path(pts)
            return
        if spec.startswith('~') and dx != 0 and stub is None and RAIL_TAGS_ON_SIDE_PINS:
            # rail tie on a side pin: a global-label tag reads better than a power
            # symbol hanging into the next pin row (same global net as the power symbol)
            spec = '^' + spec[1:]
        if spec.startswith('^'):
            L = G if stub is None else stub
            ex, ey = x + dx * L, y + dy * L
            self.wire(x, y, ex, ey)
            ang = {(1, 0): 0, (-1, 0): 180, (0, -1): 90, (0, 1): 270}[(dx, dy)]
            self.glabel(spec[1:], ex, ey, ang)
            return
        if spec.startswith('~'):
            name = spec[1:]
            ground = name in GROUNDS
            # power symbols sit directly on vertical pins that face "their" way;
            # otherwise use a stub and turn the symbol to face the wire
            facing = (dy == 1 and ground) or (dy == -1 and not ground)
            L = (0 if facing else G) if stub is None else stub
            ex, ey = x + dx * L, y + dy * L
            if L:
                self.wire(x, y, ex, ey)
            r = 180 if ((dy == 1 and not ground) or (dy == -1 and ground)) else 0
            self.power(name, ex, ey, r)
            return
        L = G if stub is None else stub
        ex, ey = x + dx * L, y + dy * L
        if L:
            self.wire(x, y, ex, ey)
        ang = {(1, 0): 0, (-1, 0): 180, (0, -1): 90, (0, 1): 270}[(dx, dy)]
        if spec.startswith('>'):
            name, _, shape = spec[1:].partition(':')
            self.hlabel(name, ex, ey, ang, shape or 'passive')
        else:
            self.label(spec, ex, ey, ang)

    def power(self, name, x, y, r=0):
        global _power_count
        _power_count += 1
        self.power_count += 1
        lib_id = 'power:PWR_FLAG' if name == 'PWR_FLAG' else f'ECE533:{name}'
        pre = '#FLG' if name == 'PWR_FLAG' else '#PWR'
        n = max(1, len(self.inst_paths))
        refs = [f'{pre}{_power_count + 1000 * k:04d}' for k in range(n)]
        p = Part(self, lib_id, refs if n > 1 else refs[0], name, snap(x), snap(y), r,
                 hide_value=(name == 'PWR_FLAG'))
        p.uuid = uid(self.file, 'pwr', self.power_count)
        self.parts.append(p)
        return p

    def flag(self, x, y):
        """PWR_FLAG at a point (draw a short wire to it yourself if needed)."""
        return self.power('PWR_FLAG', x, y)

    # ---- graphics ----
    def wire(self, x1, y1, x2, y2):
        if (x1, y1) == (x2, y2):
            return
        self.items.append(f'\t(wire (pts (xy {f(x1)} {f(y1)}) (xy {f(x2)} {f(y2)}))'
                          f' (stroke (width 0) (type default)) (uuid {q(uid(self.file, "w", x1, y1, x2, y2))}))')

    def wire_path(self, pts):
        for a, b in zip(pts, pts[1:]):
            self.wire(a[0], a[1], b[0], b[1])

    def junction(self, x, y):
        self.items.append(f'\t(junction (at {f(x)} {f(y)}) (diameter 0) (color 0 0 0 0)'
                          f' (uuid {q(uid(self.file, "j", x, y))}))')

    def label(self, name, x, y, ang=0):
        just = 'left bottom' if ang in (0, 90) else 'right bottom'
        self.items.append(f'\t(label {q(name)} (at {f(x)} {f(y)} {ang})'
                          f' (effects (font (size 1.27 1.27)) (justify {just}))'
                          f' (uuid {q(uid(self.file, "l", name, x, y))}))')

    def glabel(self, name, x, y, ang, shape='passive'):
        just = 'left' if ang in (0, 90) else 'right'
        self.items.append(f'\t(global_label {q(name)} (shape {shape}) (at {f(x)} {f(y)} {ang})'
                          f' (fields_autoplaced yes) (effects (font (size 1.27 1.27)) (justify {just}))'
                          f' (uuid {q(uid(self.file, "g", name, x, y))})'
                          f' (property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at {f(x)} {f(y)} 0)'
                          f' (effects (font (size 1.27 1.27)) (hide yes))))')

    def hlabel(self, name, x, y, ang, shape='passive'):
        just = 'left' if ang in (0, 90) else 'right'
        self.items.append(f'\t(hierarchical_label {q(name)} (shape {shape}) (at {f(x)} {f(y)} {ang})'
                          f' (effects (font (size 1.27 1.27)) (justify {just}))'
                          f' (uuid {q(uid(self.file, "h", name, x, y))}))')

    def text(self, s, x, y, size=1.27, bold=False, ang=0):
        b = ' (bold yes)' if bold else ''
        self.items.append(f'\t(text {q(s)} (exclude_from_sim no) (at {f(x)} {f(y)} {ang})'
                          f' (effects (font (size {size} {size}){b}) (justify left top))'
                          f' (uuid {q(uid(self.file, "t", s[:40], x, y))}))')

    def box(self, x1, y1, x2, y2, title=None, color=None, dash=True, width=0.254):
        c = f' (color {color[0]} {color[1]} {color[2]} 1)' if color else ''
        t = 'dash' if dash else 'solid'
        self.items.append(f'\t(rectangle (start {f(x1)} {f(y1)}) (end {f(x2)} {f(y2)})'
                          f' (stroke (width {width}) (type {t}){c}) (fill (type none))'
                          f' (uuid {q(uid(self.file, "r", x1, y1, x2, y2))}))')
        if title:
            self.text(title, x1 + 1.27, y1 + 1.27, size=1.778, bold=True)

    def line(self, pts, color=(200, 0, 0), width=0.5, dash=True):
        xy = ' '.join(f'(xy {f(x)} {f(y)})' for x, y in pts)
        t = 'dash' if dash else 'solid'
        self.items.append(f'\t(polyline (pts {xy}) (stroke (width {width}) (type {t})'
                          f' (color {color[0]} {color[1]} {color[2]} 1))'
                          f' (uuid {q(uid(self.file, "pl", pts[0], pts[-1]))}))')

    # ---- hierarchy ----
    def sheet(self, child, name, x, y, w, pins, page):
        """Place a sheet symbol. pins: list of (side, name, shape, net) with side 'L'/'R'.
        Pins are spaced 2.54 mm from the top; each pin gets a stub + label/power."""
        ref = SheetRef(self, child, name, snap(x), snap(y), w, pins, page)
        self.children.append(ref)
        return ref

    # ---- output ----
    def write(self, path, root_uuid=None, sheet_instances=None):
        lib_ids = sorted({p.lib_id for p in self.parts})
        L = ['(kicad_sch', '\t(version 20250114)', '\t(generator "eeschema")',
             '\t(generator_version "9.0")', f'\t(uuid {q(self.uuid)})', f'\t(paper {q(self.paper)})',
             '\t(title_block', f'\t\t(title {q(self.title)})', '\t\t(date "2026-10-16")',
             '\t\t(rev "A")', '\t\t(company "ECE533 MeGaNism - 72 V to 24 V 1.1 kW 2-phase GaN buck")']
        if self.comment:
            L.append(f'\t\t(comment 1 {q(self.comment)})')
        L.append('\t)')
        L.append('\t(lib_symbols')
        for lid in lib_ids:
            L.append('\t\t' + sdef(lid).embedded())
        L.append('\t)')
        L.extend(self.items)
        for ch in self.children:
            L.append(ch.text())
        for p in self.parts:
            L.append(p.text(self.inst_paths))
        if sheet_instances is not None:
            L.append('\t(sheet_instances')
            L.append('\t\t(path "/" (page "1"))')
            L.append('\t)')
        L.append('\t(embedded_fonts no)')
        L.append(')')
        with open(path, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write('\n'.join(L) + '\n')


class SheetRef:
    def __init__(self, parent, child, name, x, y, w, pins, page):
        self.parent, self.child, self.name = parent, child, name
        self.x, self.y, self.w, self.pins, self.page = x, y, w, pins, page
        nl = sum(1 for p in pins if p and p[0] == 'L')
        nr = sum(1 for p in pins if p and p[0] == 'R')
        self.h = (max(nl, nr) + 1) * G
        self.uuid = uid(parent.file, 'sheet', name)
        self.pin_pos = {}
        yl = yr = y + G
        for p in pins:
            if p is None:
                yl += G
                yr += G
                continue
            side, pname, shape, net = p
            if side == 'L':
                self.pin_pos[pname] = (x, yl, 180, shape)
                yl += G
            else:
                self.pin_pos[pname] = (x + w, yr, 0, shape)
                yr += G
        self.h = max(yl, yr) - y
        for p in pins:
            if p is None:
                continue
            side, pname, shape, net = p
            px, py, ang, _ = self.pin_pos[pname]
            if net is None:
                continue
            dx = -1 if side == 'L' else 1
            ex = px + dx * G
            parent.wire(px, py, ex, py)
            if net.startswith('~'):
                parent.power(net[1:], ex, py)
            elif net.startswith('>'):
                nm, _, sh = net[1:].partition(':')
                parent.hlabel(nm, ex, py, 180 if side == 'L' else 0, sh or shape)
            else:
                parent.label(net, ex, py, 180 if side == 'L' else 0)

    def text(self):
        L = ['\t(sheet', f'\t\t(at {f(self.x)} {f(self.y)})', f'\t\t(size {f(self.w)} {f(self.h)})',
             '\t\t(exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no)',
             '\t\t(fields_autoplaced yes)',
             '\t\t(stroke (width 0.1524) (type solid))', '\t\t(fill (color 255 255 225 1))',
             f'\t\t(uuid {q(self.uuid)})',
             f'\t\t(property "Sheetname" {q(self.name)} (at {f(self.x)} {f(self.y - 0.7)} 0)'
             ' (effects (font (size 1.524 1.524) (bold yes)) (justify left bottom)))',
             f'\t\t(property "Sheetfile" {q(self.child.file)} (at {f(self.x)} {f(self.y + self.h + 0.6)} 0)'
             ' (effects (font (size 1.27 1.27)) (justify left top)))']
        for pname, (px, py, ang, shape) in self.pin_pos.items():
            just = 'left' if ang == 180 else 'right'
            L.append(f'\t\t(pin {q(pname)} {shape} (at {f(px)} {f(py)} {ang})'
                     f' (uuid {q(uid(self.uuid, "pin", pname))})'
                     f' (effects (font (size 1.27 1.27)) (justify {just})))')
        L.append(f'\t\t(instances (project {q(PROJECT)}')
        for path in self.parent.inst_paths:
            L.append(f'\t\t\t(path {q(path)} (page {q(self.page)}))')
        L.append('\t\t))')
        L.append('\t)')
        return '\n'.join(L)
