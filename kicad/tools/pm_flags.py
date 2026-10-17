"""PowerModule: add PWR_FLAG markers to the gate-drive supply nets that ERC cannot see as driven
(the driver supplies come from J4 / PS1 / the bootstrap diodes and resistors). Each flag sits on the
pin location ERC reported. Re-runnable (skips if flags exist).
    python kicad/tools/pm_flags.py
"""
import os
import re
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
SCH = os.path.normpath(os.path.join(HERE, '..', 'PowerModule', 'gate_drive.kicad_sch'))
POWER_LIB = r'C:\Program Files\KiCad\10.0\share\kicad\symbols\power.kicad_sym'
PATH = '/09d3e748-966b-486a-bab2-fcfca6077673/e50bb7ab-2c50-48fd-b7e3-eb36d7af3b30'
# ERC "power_pin_not_driven" locations (one per net): U1 VDD, KS1, U2 VDD, GNDPWR, #PWR01, U3 VDD,
# KS2, #PWR06, U4 VDD, #PWR07
PINS = [(123.19, 31.75), (123.19, 52.07), (123.19, 77.47), (123.19, 97.79), (165.10, 21.59),
        (124.46, 124.46), (124.46, 144.78), (205.74, 26.67), (124.46, 166.37), (205.74, 38.10)]


def lib_symbol():
    t = open(POWER_LIB, encoding='utf-8').read()
    i = t.index('\t(symbol "PWR_FLAG"')
    depth, j = 0, i
    while True:
        c = t[j]
        depth += c == '('
        depth -= c == ')'
        j += 1
        if depth == 0 and c == ')':
            break
    s = t[i:j].replace('(symbol "PWR_FLAG"', '(symbol "power:PWR_FLAG"', 1)
    return '\n'.join('\t' + ln for ln in s.split('\n'))


def instance(n, x, y):
    return f'''	(symbol
		(lib_id "power:PWR_FLAG")
		(at {x} {y} 0)
		(unit 1)
		(exclude_from_sim no)
		(in_bom no)
		(on_board yes)
		(dnp no)
		(uuid "{uuid.uuid4()}")
		(property "Reference" "#FLG{n:02d}"
			(at {x} {y - 1.905} 0)
			(hide yes)
			(effects
				(font
					(size 1.27 1.27)
				)
			)
		)
		(property "Value" "PWR_FLAG"
			(at {x + 1.27} {y - 3.81} 0)
			(effects
				(font
					(size 1.0 1.0)
				)
				(justify left)
			)
		)
		(property "Footprint" ""
			(at {x} {y} 0)
			(hide yes)
			(effects
				(font
					(size 1.27 1.27)
				)
			)
		)
		(property "Datasheet" ""
			(at {x} {y} 0)
			(hide yes)
			(effects
				(font
					(size 1.27 1.27)
				)
			)
		)
		(pin "1"
			(uuid "{uuid.uuid4()}")
		)
		(instances
			(project "PowerModule"
				(path "{PATH}"
					(reference "#FLG{n:02d}")
					(unit 1)
				)
			)
		)
	)
'''


if __name__ == '__main__':
    t = open(SCH, encoding='utf-8').read()
    if 'power:PWR_FLAG' in t:
        raise SystemExit('flags already present')
    t = t.replace('\t(lib_symbols\n', '\t(lib_symbols\n' + lib_symbol() + '\n', 1)
    flags = ''.join(instance(i + 1, x, y) for i, (x, y) in enumerate(PINS))
    t = t.replace('\n\t(symbol\n\t\t(lib_id', '\n' + flags.rstrip('\n') + '\n\t(symbol\n\t\t(lib_id', 1)
    open(SCH, 'w', encoding='utf-8', newline='\n').write(t)
    print(f'added {len(PINS)} PWR_FLAGs')
