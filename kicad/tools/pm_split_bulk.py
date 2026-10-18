"""PowerModule: split each bulk capacitor into two parallel parts of about half the value (user
request): C5 (output) + C15, C6 (input) + C16. The new parts are copies of C5 / C6 placed 7.62 mm to
the right, joined by labels (VOUT, VIN) on pin 1 and a GNDPWR power symbol on pin 2. Run once,
before pm_assign.py.
    python kicad/tools/pm_split_bulk.py
"""
import os
import re
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
SCH = os.path.normpath(os.path.join(HERE, '..', 'PowerModule', 'PowerModule.kicad_sch'))
DX = 7.62
PAIRS = (('C5', 'C15', 'VOUT'), ('C6', 'C16', 'VIN'))


def blocks(t):
    for m in re.finditer(r'\n\t\(symbol\n\t\t\(lib_id "([^"]+)"\)(.*?)\n\t\)\n', t, re.S):
        yield m


def find(t, pred):
    for m in re.finditer(r'\n(\t\(symbol\n\t\t\(lib_id "([^"]+)"\).*?\n\t\)\n)', t, re.S):
        if pred(m.group(1)):
            return m.group(1)
    raise KeyError


def shift(block, dx, dy=0.0):
    def mv(m):
        x, y = float(m.group(1)), float(m.group(2))
        return f'(at {round(x + dx, 4):g} {round(y + dy, 4):g}{m.group(3)}'
    return re.sub(r'\(at ([-\d.]+) ([-\d.]+)((?: [-\d.]+)?\))', mv, block)


def new_uuids(block):
    return re.sub(r'\(uuid "[^"]+"\)', lambda m: f'(uuid "{uuid.uuid4()}")', block)


def label(name, x, y):
    return (f'\t(label "{name}"\n\t\t(at {round(x, 4):g} {round(y, 4):g} 0)\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n'
            f'\t\t\t)\n\t\t\t(justify left bottom)\n\t\t)\n\t\t(uuid "{uuid.uuid4()}")\n\t)\n')


def main():
    t = open(SCH, encoding='utf-8').read()
    if '"Reference" "C15"' in t:
        raise SystemExit('already split')
    gnd = find(t, lambda b: '(lib_id "power:GNDPWR")' in b)
    gx, gy = map(float, re.search(r'\n\t\t\(at ([-\d.]+) ([-\d.]+)', gnd).groups())
    add = []
    for old, new, net in PAIRS:
        b = find(t, lambda s, old=old: f'"Reference" "{old}"' in s)
        x, y = map(float, re.search(r'\n\t\t\(at ([-\d.]+) ([-\d.]+)', b).groups())
        nb = new_uuids(shift(b, DX))
        nb = nb.replace(f'"Reference" "{old}"', f'"Reference" "{new}"').replace(
            f'(reference "{old}")', f'(reference "{new}")')
        add.append(nb)
        # C_Small pins: 1 at y - 2.54, 2 at y + 2.54
        add.append(label(net, x, y - 2.54))
        add.append(label(net, x + DX, y - 2.54))
        n = len(re.findall(r'"#PWR\d+"', t)) + 50 + len(add)
        g = new_uuids(shift(gnd, x + DX - gx, y + 2.54 - gy))
        g = re.sub(r'"#PWR\d+"', f'"#PWR{n:03d}"', g)
        add.append(g)
    t = t.replace('\n\t(sheet_instances', '\n' + ''.join(add).rstrip('\n') + '\n\t(sheet_instances', 1) \
        if '\n\t(sheet_instances' in t else t.rstrip().rstrip(')') + ''.join(add) + ')\n'
    open(SCH, 'w', encoding='utf-8', newline='\n').write(t)
    print('added C15, C16 with VOUT / VIN labels and GNDPWR symbols')


if __name__ == '__main__':
    main()
