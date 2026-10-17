"""Connectivity checks on the exported KiCad netlist.

Usage:  kicad-cli sch export netlist -o build.net ECE533_Guide.kicad_sch
        python check_netlist.py build.net
Each check lists pins (REF.PIN) that must be on the same net, and optionally
pins that must NOT be on it. Exit code 1 if any check fails.
"""
import sys

from sexp import child, find, parse

CHECKS = [
    # name, same-net pins, must-not pins
    ('VIN_PROT', ['Q2.3', 'RS1.1', 'C70.1', 'R45.1', 'R49.1', 'U11.2', 'R54.1', 'C74.1'], ['VBUS:U12.9']),
    ('Hot-swap sense', ['RS1.2', 'U12.2', 'C71.1'], []),
    # 4-terminal Kelvin shunts: sense pins (2/3) are their own nets, tied to the
    # power pads (1/4) only inside the footprint (net-tie pad groups, Stage 3)
    ('Hot-swap sense load side', ['RS1.3', 'U12.1'], ['RS1.4']),
    ('Hot-swap load side', ['RS1.4', 'Q1.3'], []),
    ('VBUS', ['Q1.2', 'U12.9', 'C5.1', 'C6.1', 'Q3.3', 'Q5.3', 'C1.1', 'C3.1'], []),
    ('UVLO', ['R45.2', 'R46.1', 'U12.3'], []),
    ('OVLO', ['R52.2', 'R53.1', 'U12.4'], []),
    ('OVP sense', ['R49.2', 'R50.1', 'U22.3', 'R51.1'], []),
    ('Reverse FET gate', ['U13.4', 'Q2.1'], []),
    ('Reverse FET source', ['U13.3', 'Q2.2', 'F1.2', 'D6.1'], []),
    ('SW1', ['Q3.4', 'Q4.3', 'L1.4', 'NT1.2'], ['Q5.4']),
    ('SW2', ['Q5.4', 'Q6.3', 'L1.3', 'NT3.2'], []),
    ('LX1', ['L1.1', 'RS2.1'], []),
    ('LX2', ['L1.2', 'RS3.1'], []),
    ('+24V', ['RS2.4', 'RS3.4', 'J2.1', 'C60.1', 'R64.1'], []),
    ('HS1 Kelvin', ['Q3.2', 'U1.14', 'C7.2', 'D3.2', 'NT1.1', 'R1.2'], ['Q3.4']),
    ('LS1 Kelvin', ['Q4.2', 'U1.9', 'C8.2', 'C12.2', 'NT2.1', 'R2.2'], ['Q4.4']),
    ('HS2 Kelvin', ['Q5.2', 'U2.14', 'C9.2', 'D4.2', 'NT3.1', 'R3.2'], []),
    ('HS1 gate', ['R15.2', 'Q3.1', 'R1.1', 'TP5.1'], []),
    ('HS1 drive', ['U1.15', 'R15.1'], []),
    ('LS1 gate', ['R13.2', 'Q4.1', 'R2.1', 'TP6.1'], []),
    ('LS1 drive', ['U1.10', 'R13.1'], []),
    ('LS2 drive', ['U2.10', 'R14.1'], []),
    ('BOOT1', ['U1.16', 'C7.1', 'D1.1', 'D3.1'], []),
    ('Bootstrap R-D', ['R9.2', 'D1.2'], []),
    ('PWM1 to driver', ['U19.4', 'U1.1'], []),
    ('PWM2 to driver', ['U20.4', 'U2.1'], []),
    ('PWM1 raw', ['U5.29', 'U16.1', 'U19.1'], []),
    ('PWM2 raw', ['U5.18', 'U17.1', 'U20.1'], []),
    ('CBC1 latch', ['U16.5', 'U19.2'], []),
    ('EN1', ['U5.30', 'U1.5', 'R94.1'], []),
    ('EN2', ['U5.17', 'U2.5', 'R95.1'], []),
    ('OCP1 HV', ['U9.6', 'R29.2', 'AT1.2'], []),
    ('OCP2 HV', ['U10.6', 'R30.2', 'AT1.3'], []),
    ('OCP1 LV', ['AT1.7', 'U16.6'], []),
    ('OCP2 LV', ['AT1.6', 'U17.6'], []),
    ('OTP HV', ['U14.1', 'R41.2', 'AT2.2'], []),
    ('OTP LV', ['AT2.7', 'U25.1'], []),
    ('BUS_PG HV', ['U12.8', 'R48.2', 'AT2.3'], []),
    ('BUS_PG LV', ['AT2.6', 'D16.3'], []),
    ('RUN_OK', ['R87.2', 'D15.1', 'D16.1', 'R88.2', 'U5.28', 'U5.19', 'C118.1'], []),
    ('FAULT_N', ['U18.3', 'D15.3'], []),
    ('FAULT', ['U18.5', 'R89.1', 'Q8.1'], []),
    ('FLT_SET_N', ['U25.4', 'U18.7'], []),
    ('OVP_N', ['U15.1', 'U25.2'], []),
    ('VSOUT', ['U5.5', 'R81.1', 'R82.1', 'U15.4'], []),
    ('FB', ['U5.1', 'R81.2', 'C107.2', 'R83.1', 'C109.1'], []),
    ('COMP', ['U5.2', 'U5.9', 'C108.2', 'C109.2'], []),
    ('I1_P', ['U6.11', 'R73.1'], []),
    ('I1_N', ['U6.10', 'R75.1'], []),
    ('I2_P', ['U7.11', 'R77.1'], []),
    ('ISNS1P', ['R73.2', 'R74.1', 'U5.25', 'C105.1'], []),
    ('ISNS2N', ['R79.2', 'R80.1', 'U5.23', 'C106.2'], []),
    ('VFB_P', ['U8.11', 'R69.1'], []),
    ('VFB_N', ['U8.10', 'R71.1'], []),
    ('VSNSP1', ['R69.2', 'R70.1', 'U5.3'], []),
    ('VOUT divider', ['R64.2', 'R65.1', 'U8.6', 'C92.1'], []),
    ('Shunt1 Kelvin +', ['RS2.2', 'U9.8', 'R31.1'], []),
    ('Shunt1 Kelvin - / AMC HGND', ['RS2.3', 'U9.7', 'R32.1', 'U6.8', 'U6.2'], ['RS2.4']),
    ('AMC1 input', ['R31.2', 'U6.6', 'C42.1'], []),
    ('NTC', ['R40.2', 'RT1.1', 'U14.3', 'R41.1'], []),
    ('CT', ['C32.2', 'C33.1', 'C34.2', 'C35.1', 'FB1.1'], []),
    ('HS_SHIELD', ['FB1.2', 'H1.1', 'H4.1', 'R42.1'], []),
    ('PGOOD', ['U5.31', 'R91.2', 'Q7.1', 'R92.1'], []),
    ('J4 EN', ['J4.2', 'R88.1', 'D14.1'], []),
    ('J4 FAULT_N', ['J4.4', 'Q8.3', 'D14.4'], []),
    ('Fan 5V', ['U21.6', 'J5.1', 'C84.1', 'D7.1'], []),
    ('TACH', ['J5.3', 'R62.2', 'TP14.1', 'D7.2'], []),
    ('Buck SW', ['U11.8', 'D5.1', 'L2.1', 'C77.2', 'R59.1'], []),
    ('Buck FB', ['U11.5', 'R57.2', 'R58.1', 'C82.2'], []),
    ('+5V_PWR', ['L2.2', 'R57.1', 'PS1.2', 'U1.11', 'U2.11', 'U21.1', 'AT1.1', 'U9.1', 'R43.1'], []),
    ('+5V_ISO', ['PS1.4', 'U5.36', 'U5.34', 'U5.13', 'U5.10', 'AT1.8', 'U1.3', 'U6.12', 'U8.12'], []),
    ('PGND', ['J3.1', 'J6.1', 'Q4.4', 'Q6.4', 'U12.5', 'U11.1', 'PS1.1', 'AT1.4', 'U8.8', 'NT2.2'], []),
    ('GND_ISO', ['PS1.3', 'U5.21', 'U5.33', 'U5.15', 'AT1.5', 'U1.4', 'U6.9', 'J4.1'], []),
]

ISOLATED = ('GND_ISO', 'PGND')


def load(path):
    tree = parse(open(path, encoding='utf-8').read())
    pin2net, nets = {}, {}
    for net in find(tree, 'net'):
        name = child(net, 'name')
        if not name:
            continue
        nodes = []
        for n in find(net, 'node'):
            k = f"{child(n, 'ref')[1]}.{child(n, 'pin')[1]}"
            pin2net[k] = name[1]
            nodes.append(k)
        nets[name[1]] = nodes
    return pin2net, nets


def main(path):
    pin2net, nets = load(path)
    fails = 0
    for name, same, notpins in CHECKS:
        missing = [p for p in same if p not in pin2net]
        if missing:
            print(f'FAIL {name}: pins not in netlist {missing}')
            fails += 1
            continue
        found = {pin2net[p] for p in same}
        if len(found) != 1:
            groups = {}
            for p in same:
                groups.setdefault(pin2net[p], []).append(p)
            print(f'FAIL {name}: split across nets {groups}')
            fails += 1
            continue
        net = found.pop()
        bad = []
        for p in notpins:
            p = p.split(':')[-1]
            if pin2net.get(p) == net:
                bad.append(p)
        if bad:
            print(f'FAIL {name}: {bad} must not be on {net}')
            fails += 1
        else:
            print(f'ok   {name:<28} {net}')
    # the two grounds must never merge
    if pin2net.get('PS1.1') == pin2net.get('PS1.3'):
        print('FAIL: PGND and GND_ISO are the same net!')
        fails += 1
    # no single-pin nets except deliberate test points / NC
    singles = [n for n, nodes in nets.items() if len(nodes) == 1 and not n.startswith('unconnected')]
    for n in singles:
        print(f'note single-pin net {n}: {nets[n]}')
    print(f'\n{len(CHECKS) - fails}/{len(CHECKS)} checks passed')
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1]))
