"""Helpers to read KiCad symbol libraries and build simple box symbols.

Used by gen_symbols.py (project library) and gen_schematic.py (sheets).
"""
import copy
import os

from sexp import Sym, parse, find, child, dump

KICAD_SYM_DIR = os.environ.get(
    'KICAD_SYMBOL_DIR', r'C:\Program Files\KiCad\10.0\share\kicad\symbols')

_lib_cache = {}


def load_lib(path):
    if path not in _lib_cache:
        tree = parse(open(path, encoding='utf-8').read())[0]
        syms = {}
        for node in tree:
            if isinstance(node, list) and node and node[0] == 'symbol':
                syms[node[1]] = node
        _lib_cache[path] = syms
    return _lib_cache[path]


def std_lib_path(lib):
    return os.path.join(KICAD_SYM_DIR, lib + '.kicad_sym')


def rename_symbol(node, new):
    """Rename a symbol and its unit sub-symbols."""
    node = copy.deepcopy(node)
    old = node[1]
    node[1] = new
    for sub in node[2:]:
        if isinstance(sub, list) and sub and sub[0] == 'symbol':
            if sub[1].startswith(old + '_'):
                sub[1] = new + sub[1][len(old):]
    return node


def flatten(lib_syms, name):
    """Return a standalone copy of symbol `name`, resolving `extends`."""
    node = lib_syms[name]
    ext = child(node, 'extends')
    if not ext:
        return copy.deepcopy(node)
    parent = flatten(lib_syms, ext[1])
    out = rename_symbol(parent, name)
    # child properties override the parent's
    props = {c[1]: c for c in node if isinstance(c, list) and c and c[0] == 'property'}
    for i, c in enumerate(out):
        if isinstance(c, list) and c and c[0] == 'property' and c[1] in props:
            out[i] = copy.deepcopy(props.pop(c[1]))
    insert_at = max(i for i, c in enumerate(out)
                    if isinstance(c, list) and c and c[0] == 'property') + 1
    for p in props.values():
        out.insert(insert_at, copy.deepcopy(p))
        insert_at += 1
    return out


def set_property(node, key, value, hide=None):
    for c in node:
        if isinstance(c, list) and c and c[0] == 'property' and c[1] == key:
            c[2] = value
            if hide is not None:
                _set_hide(c, hide)
            return node
    prop = [Sym('property'), key, value, [Sym('at'), 0, 0, 0],
            [Sym('effects'), [Sym('font'), [Sym('size'), 1.27, 1.27]]]]
    if hide:
        prop.append([Sym('hide'), Sym('yes')])
    idx = max(i for i, c in enumerate(node)
              if isinstance(c, list) and c and c[0] == 'property') + 1
    node.insert(idx, prop)
    return node


def _set_hide(prop, hide):
    prop[:] = [c for c in prop if not (isinstance(c, list) and c and c[0] == 'hide')]
    if hide:
        prop.append([Sym('hide'), Sym('yes')])


def symbol_pins(node):
    """List of dicts: number, name, type, x, y, angle, length, hidden."""
    pins = []
    for p in find(node, 'pin'):
        if len(p) < 3 or not isinstance(p[1], str):
            continue
        at = child(p, 'at')
        ln = child(p, 'length')
        nm = child(p, 'name')
        num = child(p, 'number')
        if not (at and nm and num):
            continue
        hidden = any(isinstance(c, list) and c and c[0] == 'hide' for c in p) or 'hide' in p
        pins.append(dict(number=num[1], name=nm[1], type=str(p[1]),
                         x=float(at[1]), y=float(at[2]), angle=float(at[3]) if len(at) > 3 else 0.0,
                         length=float(ln[1]) if ln else 2.54, hidden=hidden))
    return pins


# --------------------------------------------------------------------------
# Box-symbol builder
# --------------------------------------------------------------------------
G = 2.54


def _font(size=1.27):
    return f'(effects (font (size {size} {size})))'


def _prop(key, val, x, y, hide=False, justify=None):
    j = f' (justify {justify})' if justify else ''
    h = ' (hide yes)' if hide else ''
    v = str(val).replace('\\', '\\\\').replace('"', '\\"')
    return (f'(property "{key}" "{v}" (at {x:g} {y:g} 0)'
            f' (effects (font (size 1.27 1.27)){j}){h})')


def _pin(num, name, etype, x, y, ang, hidden=False, length=G):
    h = ' (hide yes)' if hidden else ''
    nm = name.replace('"', '\\"')
    return (f'(pin {etype} line (at {x:g} {y:g} {ang:g}) (length {length:g}){h}'
            f' (name "{nm}" {_font()}) (number "{num}" {_font()}))')


def box_symbol(name, ref, value, footprint='', datasheet='', description='',
               keywords='', left=(), right=(), top=(), bottom=(), width=None,
               extra_graphics=(), pin_names_offset=1.016):
    """Build a rectangular symbol.

    Each pin spec is (numbers, name, type) where numbers is a str or a list of
    str (stacked pins; extras are hidden), or None for a one-grid gap.
    """
    def norm(lst):
        return [None if p is None else (([p[0]] if isinstance(p[0], str) else list(p[0])), p[1], p[2])
                for p in lst]
    left, right, top, bottom = norm(left), norm(right), norm(top), norm(bottom)
    rows = max(len(left), len(right), 1)
    cols = max(len(top), len(bottom), 0)
    if width is None:
        ll = max([len(p[1]) for p in left if p] + [0])
        lr = max([len(p[1]) for p in right if p] + [0])
        width = (ll + lr) * 1.0 + 3.0
        width = max(width, (cols + 1) * G, 10.16)
    # body width is an even number of grid units so pins land on the 2.54 grid
    width = max(2, round(width / (2 * G))) * 2 * G
    half_w = width / 2
    pins = []

    def place_side(lst, x, ang, start_y):
        y = start_y
        for p in lst:
            if p is not None:
                nums, nm, typ = p
                for k, n in enumerate(nums):
                    t = typ if (k == 0 or typ == 'no_connect') else 'passive'
                    pins.append(_pin(n, nm, t, x, y, ang, hidden=k > 0))
            y -= G
    # keep pins on a 2.54 grid: first row at an integer multiple of G
    top_y = ((rows - 1) // 2) * G
    place_side(left, -half_w - G, 0, top_y)
    place_side(right, half_w + G, 180, top_y)
    ybot = -((rows - 1) - (rows - 1) // 2) * G

    def place_tb(lst, y, ang):
        n = len(lst)
        x = -((n - 1) // 2) * G
        for p in lst:
            if p is not None:
                nums, nm, typ = p
                for k, num in enumerate(nums):
                    pins.append(_pin(num, nm, typ if k == 0 else 'passive', x, y, ang, hidden=k > 0))
            x += G
    # leave a free row under/over top/bottom pins so their names don't hit side pins
    body_top = top_y + G + (G if top else 0)
    body_bot = ybot - G - (G if bottom else 0)
    place_tb(top, body_top + G, 270)
    place_tb(bottom, body_bot - G, 90)
    lines = [f'(symbol "{name}"',
             f'(pin_names (offset {pin_names_offset}))',
             '(exclude_from_sim no) (in_bom yes) (on_board yes)',
             _prop('Reference', ref, -half_w, body_top + 1.27 + (G if top else 0), justify='left'),
             _prop('Value', value, half_w, body_top + 1.27 + (G if top else 0), justify='right'),
             _prop('Footprint', footprint, 0, body_bot - 5.08, hide=True),
             _prop('Datasheet', datasheet, 0, body_bot - 7.62, hide=True),
             _prop('Description', description, 0, body_bot - 10.16, hide=True),
             _prop('ki_keywords', keywords, 0, 0, hide=True),
             f'(symbol "{name}_0_1" (rectangle (start {-half_w:g} {body_top:g}) (end {half_w:g} {body_bot:g})'
             ' (stroke (width 0.254) (type default)) (fill (type background)))'
             + ''.join(' ' + g for g in extra_graphics) + ')',
             f'(symbol "{name}_1_1" ' + ' '.join(pins) + ')',
             ')']
    return parse('\n'.join(lines))[0]


def lib_text(symbols):
    out = ['(kicad_symbol_lib', '\t(version 20241209)', '\t(generator "ece533_gen_symbols")',
           '\t(generator_version "9.0")']
    for s in symbols:
        out.append('\t' + dump(s, 1))
    out.append(')')
    return '\n'.join(out) + '\n'
