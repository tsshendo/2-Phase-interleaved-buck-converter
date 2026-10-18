"""PowerModule: 1 kOhm gate-to-Kelvin-source pull-downs on all four FETs (as in the report's LTspice
model; CLAUDE.md section 7). R21 P1H-KS1, R22 P1L-GNDPWR, R23 P2H-KS2, R24 P2L-GNDPWR, drawn at
the free right-hand side of the gate-drive sheet: copies of R15 (vertical), hierarchical labels on
pin 1 (gate) and on pin 2 (KS1 / KS2) or a GNDPWR symbol. Run once, before pm_assign.py.
    python kicad/tools/pm_pulldowns.py
"""
import os
import re
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
SCH = os.path.normpath(os.path.join(HERE, '..', 'PowerModule', 'gate_drive.kicad_sch'))
PARTS = (('R21', 'P1H', 'KS1', 248.92, 50.8), ('R22', 'P1L', None, 261.62, 50.8),
         ('R23', 'P2H', 'KS2', 248.92, 81.28), ('R24', 'P2L', None, 261.62, 81.28))


def g(v):
    return f'{round(v, 4):g}'


def symbol_block(t, pred):
    for m in re.finditer(r'\n(\t\(symbol\n\t\t\(lib_id "[^"]+"\).*?\n\t\)\n)', t, re.S):
        if pred(m.group(1)):
            return m.group(1)
    raise KeyError


def place(block, x, y, rot):
    """Move a symbol instance so its origin is at (x, y) with rotation rot; fields follow."""
    ox, oy = map(float, re.search(r'\n\t\t\(at ([-\d.]+) ([-\d.]+)', block).groups())

    def mv(m):
        return f'(at {g(float(m.group(1)) - ox + x)} {g(float(m.group(2)) - oy + y)}{m.group(3)}'
    block = re.sub(r'\(at ([-\d.]+) ([-\d.]+)((?: [-\d.]+)?\))', mv, block)
    block = re.sub(r'\n\t\t\(at ([-\d.]+) ([-\d.]+) [-\d.]+\)', f'\n\t\t(at {g(x)} {g(y)} {rot})', block, count=1)
    return re.sub(r'\(uuid "[^"]+"\)', lambda m: f'(uuid "{uuid.uuid4()}")', block)


def hlabel(t, name, x, y, angle):
    b = re.search(r'\n(\t\(hierarchical_label "' + name + r'".*?\n\t\)\n)', t, re.S).group(1)
    b = re.sub(r'\n\t\t\(at [^)]*\)', f'\n\t\t(at {g(x)} {g(y)} {angle})', b, count=1)
    b = b.replace('(justify left)', '(justify left)' if angle == 0 else '(justify right)')
    return re.sub(r'\(uuid "[^"]+"\)', lambda m: f'(uuid "{uuid.uuid4()}")', b)


def main():
    t = open(SCH, encoding='utf-8').read()
    if '"Reference" "R21"' in t:
        raise SystemExit('already added')
    r15 = symbol_block(t, lambda b: '"Reference" "R15"' in b)
    gnd = symbol_block(t, lambda b: '(lib_id "power:GNDPWR")' in b)
    n = 900
    add = []
    for ref, gate, src, x, y in PARTS:
        b = place(r15, x, y, 0)
        b = re.sub(r'"Reference" "R15"', f'"Reference" "{ref}"', b)
        b = b.replace('(reference "R15")', f'(reference "{ref}")')
        add.append(b)
        add.append(hlabel(t, gate, x, y - 2.54, 0))          # R_Small_US pin 1 on top
        if src:
            add.append(hlabel(t, src, x, y + 2.54, 0))
        else:
            n += 1
            gb = place(gnd, x, y + 2.54, 0)
            add.append(re.sub(r'"#PWR\d+"', f'"#PWR{n}"', gb))
    t = t.replace('\n\t(sheet_instances', '\n' + ''.join(add).rstrip('\n') + '\n\t(sheet_instances', 1) \
        if '\n\t(sheet_instances' in t else t.rstrip()[:-1] + ''.join(add) + ')\n'
    open(SCH, 'w', encoding='utf-8', newline='\n').write(t)
    print('added R21-R24 gate pull-downs')


if __name__ == '__main__':
    main()
