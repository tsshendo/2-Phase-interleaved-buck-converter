"""Generate the project symbol library kicad/ECE533_Guide/ECE533.kicad_sym.

Pinouts are taken from the manufacturer datasheets (noted per symbol).
Run with KiCad's bundled Python:  python kicad/tools/gen_symbols.py
"""
import os

from kilib import (box_symbol, flatten, lib_text, load_lib, rename_symbol,
                   set_property, std_lib_path)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'ECE533_Guide', 'ECE533.kicad_sym')

I, O, P, PI, PO, OC, NC, TS = ('input', 'output', 'passive', 'power_in', 'power_out',
                               'open_collector', 'no_connect', 'tri_state')


def power_sym(src_lib, src_name, new_name, desc):
    s = rename_symbol(flatten(load_lib(std_lib_path(src_lib)), src_name), new_name)
    set_property(s, 'Value', new_name)
    set_property(s, 'Description', desc)
    # the power pin's name must equal the net name
    for node in s:
        if isinstance(node, list) and node and node[0] == 'symbol':
            for p in node:
                if isinstance(p, list) and p and p[0] == 'pin':
                    for q in p:
                        if isinstance(q, list) and q and q[0] == 'name':
                            q[1] = new_name
    return s


def build():
    syms = []

    # ---------------- power / net symbols ----------------
    syms.append(power_sym('power', 'GNDPWR', 'PGND',
                          'Power ground: VIN-, VOUT-, power stage return (HV domain)'))
    syms.append(power_sym('power', 'GNDA', 'GND_ISO',
                          'Isolated control ground (LV domain)'))
    syms.append(power_sym('power', '+5V', '+5V_PWR',
                          '5.2 V HV-domain rail from LM5012 (gate drive, fan, PS1 input)'))
    syms.append(power_sym('power', '+5V', '+5V_ISO',
                          '5 V isolated LV-domain rail from PS1'))
    syms.append(power_sym('power', '+12V', 'VBUS',
                          '72 V input bus after hot-swap (HV domain)'))
    syms.append(power_sym('power', '+24V', '+24V',
                          '24 V / 46 A output (HV domain)'))

    # ---------------- ICs ----------------
    # ADI LTC3861 (UHE QFN-36 5x6), datasheet Rev B pin functions
    syms.append(box_symbol(
        'LTC3861', 'U', 'LTC3861',
        footprint='Package_DFN_QFN:QFN-36-1EP_5x6mm_P0.5mm_EP3.6x4.1mm',
        datasheet='https://www.analog.com/media/en/technical-documentation/data-sheets/38611fb.pdf',
        description='Dual multiphase voltage-mode step-down controller with current sharing, PWM outputs',
        keywords='buck controller multiphase PWM DrMOS',
        width=33.02,
        left=[('34', 'VINSNS', I), ('33', 'CONFIG', I), ('12', 'FREQ', P), ('13', 'CLKIN', I),
              ('15', 'PHSMD', I), None, ('28', 'RUN1', I), ('19', 'RUN2', I),
              ('35', 'TRACK/SS1', P), ('11', 'TRACK/SS2', P), None,
              ('3', 'VSNSP1', I), ('4', 'VSNSN1', I), ('8', 'VSNSP2', I), ('7', 'VSNSN2', I), None,
              ('25', 'ISNS1P', I), ('24', 'ISNS1N', I), ('22', 'ISNS2P', I), ('23', 'ISNS2N', I),
              ('27', 'ILIM1', P), ('20', 'ILIM2', P)],
        right=[('29', 'PWM1', TS), ('30', 'PWMEN1', O), ('18', 'PWM2', TS), ('17', 'PWMEN2', O),
               None, ('31', 'PGOOD1', OC), ('16', 'PGOOD2', OC), ('14', 'CLKOUT', O), None,
               ('5', 'VSNSOUT1', O), ('1', 'FB1', I), ('2', 'COMP1', P), None,
               ('6', 'VSNSOUT2', O), ('10', 'FB2', I), None, ('9', 'COMP2', P),
               ('32', 'IAVG', P)],
        top=[('36', 'VCC', PI)],
        bottom=[(['21', '26', '37'], 'SGND', PI)]))

    # Skyworks Si8274GB1-IS1 SOIC-16 NB (datasheet Table 3). VOA = high side (A).
    syms.append(box_symbol(
        'Si8274', 'U', 'Si8274GB1-IS1',
        footprint='Package_SO:SOIC-16_3.9x9.9mm_P1.27mm',
        datasheet='https://www.skyworksinc.com/-/media/SkyWorks/SL/documents/public/data-sheets/si827x.pdf',
        description='Isolated high-side/low-side gate driver, PWM input, programmable dead time, 2.5 kVrms',
        keywords='isolated gate driver half bridge GaN',
        width=20.32,
        left=[(['3', '8'], 'VDDI', PI), ('1', 'PWM', I), ('5', 'EN', I), ('6', 'DT', P), None, None,
              ('4', 'GNDI', PI), (['2', '7', '12', '13'], 'NC', NC)],
        right=[('16', 'VDDA', P), ('15', 'VOA', O), ('14', 'GNDA', P), None,
               ('11', 'VDDB', PI), ('10', 'VOB', O), ('9', 'GNDB', P)]))   # GNDB on Kelvin net

    # TI AMC3301DWE: same pinout as AMC3330 (SBAS917C Table 4-1)
    amc = rename_symbol(flatten(load_lib(std_lib_path('Isolator_Analog')), 'AMC3330'), 'AMC3301')
    set_property(amc, 'Value', 'AMC3301')
    set_property(amc, 'Description',
                 'Reinforced isolated amplifier, +-250 mV input, gain 8.2, integrated isolated DC/DC')
    set_property(amc, 'Datasheet', 'https://www.ti.com/lit/ds/symlink/amc3301.pdf')
    syms.append(amc)

    # TI INA301 VSSOP-8 (SBOS713A pin functions)
    syms.append(box_symbol(
        'INA301', 'U', 'INA301A3',
        footprint='Package_SO:VSSOP-8_3x3mm_P0.65mm',
        datasheet='https://www.ti.com/lit/ds/symlink/ina301.pdf',
        description='Current-sense amplifier with integrated overcurrent comparator, 0-36 V CM',
        keywords='current sense comparator alert',
        width=15.24,
        left=[('8', 'IN+', I), ('7', 'IN-', I), None, ('3', 'LIMIT', P), ('5', 'RESET', I)],
        right=[('2', 'OUT', O), None, None, ('6', '~{ALERT}', OC)],
        top=[('1', 'VS', PI)], bottom=[('4', 'GND', PI)]))

    # TI LM5012 DDA (SNVSCA9 Table 6-1); EP = pad 9 (GND)
    syms.append(box_symbol(
        'LM5012', 'U', 'LM5012DDAR',
        footprint='Package_SO:HSOP-8-1EP_3.9x4.9mm_P1.27mm_EP2.41x3.1mm',
        datasheet='https://www.ti.com/lit/ds/symlink/lm5012.pdf',
        description='100 V, 2.5 A non-synchronous COT buck converter',
        keywords='buck regulator 100V COT',
        width=15.24,
        left=[('2', 'VIN', PI), None, ('3', 'EN/UVLO', I), ('4', 'RON', P)],
        right=[('7', 'BST', P), ('8', 'SW', PO), ('5', 'FB', I), ('6', 'PGOOD', OC)],
        bottom=[(['1', '9'], 'GND', PI)]))

    # TI TPS2553 SOT-23-6 (SLVS841F pin functions)
    syms.append(box_symbol(
        'TPS2553', 'U', 'TPS2553DBVR',
        footprint='Package_TO_SOT_SMD:SOT-23-6',
        datasheet='https://www.ti.com/lit/ds/symlink/tps2553.pdf',
        description='Current-limited power-distribution switch, adjustable 75 mA-1.7 A, active-high EN',
        keywords='load switch current limit fan',
        width=15.24,
        left=[('1', 'IN', PI), ('3', 'EN', I), ('5', 'ILIM', P)],
        right=[('6', 'OUT', PO), None, ('4', '~{FAULT}', OC)],
        bottom=[('2', 'GND', PI)]))

    # TI TLV3012 SOT-23-6 (SBOS300C Table 5-1)
    syms.append(box_symbol(
        'TLV3012', 'U', 'TLV3012AIDBVR',
        footprint='Package_TO_SOT_SMD:SOT-23-6',
        datasheet='https://www.ti.com/lit/ds/symlink/tlv3012.pdf',
        description='Nanopower push-pull comparator with integrated 1.242 V reference',
        keywords='comparator reference',
        width=10.16,
        left=[('3', '+', I), ('4', '-', I)],
        right=[('1', 'OUT', O), ('5', 'REF', O)],
        top=[('6', 'V+', PI)], bottom=[('2', 'V-', PI)]))

    # Vishay VOM1271 SOP-4: 1 LED anode, 2 LED cathode, 4 output +, 3 output -
    syms.append(box_symbol(
        'VOM1271', 'U', 'VOM1271T',
        footprint='Package_SO:SOP-4_3.8x4.1mm_P2.54mm',
        datasheet='https://www.vishay.com/docs/83469/vom1271.pdf',
        description='Photovoltaic MOSFET driver with integrated fast turn-off, 4.5 kVrms',
        keywords='photovoltaic gate driver optocoupler',
        width=15.24,
        left=[('1', 'LED A', P), ('2', 'LED K', P)],
        right=[('4', 'VO+', P), ('3', 'VO-', P)]))

    # TI SN74LVC1G74 DCT/DCU (SCES431 pin functions)
    syms.append(box_symbol(
        '74LVC1G74', 'U', 'SN74LVC1G74DCTR',
        footprint='Package_SO:SSOP-8_2.95x2.8mm_P0.65mm',
        datasheet='https://www.ti.com/lit/ds/symlink/sn74lvc1g74.pdf',
        description='Single D-type flip-flop with preset and clear',
        keywords='flip flop latch',
        width=15.24,
        left=[('2', 'D', I), None, ('1', 'CLK', I), None, ('7', '~{PRE}', I), ('6', '~{CLR}', I)],
        right=[('5', 'Q', O), None, None, None, None, ('3', '~{Q}', O)],
        top=[('8', 'VCC', PI)], bottom=[('4', 'GND', PI)]))

    # Skyworks SI86S620BC-IS SOIC-8: side 1 = A inputs, side 2 = B outputs
    syms.append(box_symbol(
        'SI86S620', 'AT', 'SI86S620BC-IS',
        footprint='Package_SO:SOIC-8_3.9x4.9mm_P1.27mm',
        datasheet='https://www.skyworksinc.com/-/media/SkyWorks/SL/documents/public/data-sheets/si86xx-datasheet.pdf',
        description='2-channel digital isolator, 2 forward / 0 reverse',
        keywords='digital isolator',
        width=17.78,
        left=[('1', 'VDD1', PI), ('2', 'A1', I), ('3', 'A2', I), ('4', 'GND1', PI)],
        right=[('8', 'VDD2', PI), ('7', 'B1', O), ('6', 'B2', O), ('5', 'GND2', PI)]))

    # Murata NME1S0505SC SIP-4
    syms.append(box_symbol(
        'NME1S0505SC', 'PS', 'NME1S0505SC',
        footprint='ECE533_Vendor:Murata_NME1S_SIP-4',
        datasheet='https://www.murata.com/products/productdata/8822286319646/KDC-NME1.pdf',
        description='1 W isolated DC/DC module, 5 V in, 5 V out, 1 kVDC',
        keywords='isolated dc-dc module',
        width=15.24,
        left=[('2', '+VIN', PI), ('1', '-VIN', PI)],
        right=[('4', '+VOUT', PO), ('3', '-VOUT', PO)]))

    # EPC2304 (datasheet pin description): 1 G, 2 S (Kelvin, nearest the gate), 3/5/7 D, 4/6 S
    syms.append(box_symbol(
        'EPC2304', 'Q', 'EPC2304',
        footprint='ECE533_Mods:EPC2304_QFN-7_3x5mm',
        datasheet='https://epc-co.com/epc/documents/datasheets/EPC2304_datasheet.pdf',
        description='200 V, 3.5 mOhm eGaN FET, top-side cooled QFN 3x5',
        keywords='GaN FET eGaN',
        width=10.16,
        left=[('1', 'G', I), ('2', 'SK', P)],
        top=[(['3', '5', '7'], 'D', P)],
        bottom=[(['4', '6'], 'S', P)]))

    # TDK ERUC23-3R2K coupled inductor: winding A = 4 -> 1, winding B = 3 -> 2
    syms.append(box_symbol(
        'ERUC23', 'L', 'ERUC23-3R2K',
        footprint='ECE533_Mods:TDK_ERUC23',
        datasheet='https://product.tdk.com/en/search/inductor/inductor/smd/info?part_no=ERUC23-3R2K',
        description='Two-phase coupled inductor, L 5.84 uH, k 0.714, DCR 1.84 mOhm per winding',
        keywords='coupled inductor interleaved',
        width=15.24,
        left=[('4', 'A in', P), ('3', 'B in', P)],
        right=[('1', 'A out', P), ('2', 'B out', P)]))
    return syms


def main():
    syms = build()
    with open(OUT, 'w', encoding='utf-8', newline='\n') as f:
        f.write(lib_text(syms))
    print('wrote', os.path.normpath(OUT), len(syms), 'symbols')


if __name__ == '__main__':
    main()
