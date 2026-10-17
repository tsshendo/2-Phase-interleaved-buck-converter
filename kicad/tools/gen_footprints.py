"""Write the project footprints (Stage 3).

ECE533_Guide/ECE533_Mods.pretty  (committed) - drawn here from the manufacturer datasheets:
    EPC2304_QFN-7_3x5mm(_15pin)  EPC2304 datasheet: copper drawing, solder-mask-defined land
                                 pattern (mask openings) and stencil drawing (paste), pages 12-13
    TDK_ERUC23                   TDK ERUC23 datasheet "Recommended PCB layout"
    R_2512_Kelvin                Bourns CSS2H-2512 "Recommended Pad Layout" with sense strips,
                                 net-tie pad groups (1,2) and (3,4)
    Fuse_Littelfuse_NANO2_456    Littelfuse 456 datasheet, 20/25/30 A recommended pad layout
ECE533_Guide/ECE533_Mods.3dshapes  (committed) - placeholder STEP for the fuse (simple boxes)
lib/vendor/ECE533_Vendor.pretty  (git-ignored) - vendor footprints, only renamed / re-pointed:
    Wurth_REDCUBE_74650194       Wurth MP_Wurth_WP-THRBU_74650194R (KiCad_WP-THRBU_rev26b.zip)
    Murata_NME1S_SIP-4           SamacSys NME1S0505SC footprint, converted to the current format

3D models from vendors stay in lib/vendor (see lib/vendor/README.md) and are referenced through
${KIPRJMOD}/../lib/vendor/..., so the board never embeds them.
Run with KiCad's Python:  python kicad/tools/gen_footprints.py
"""
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
PRJ = os.path.normpath(os.path.join(HERE, '..', 'ECE533_Guide'))
MODS = os.path.join(PRJ, 'ECE533_Mods.pretty')
SHAPES = os.path.join(PRJ, 'ECE533_Mods.3dshapes')
VENDOR = os.path.normpath(os.path.join(HERE, '..', 'lib', 'vendor'))
VLIB = os.path.join(VENDOR, 'ECE533_Vendor.pretty')
VPATH = '${KIPRJMOD}/../lib/vendor'


def n(v):
    s = f'{v:.4f}'.rstrip('0').rstrip('.')
    return '0' if s in ('-0', '') else s


def font(size=1.0, th=0.15):
    return f'(effects (font (size {n(size)} {n(size)}) (thickness {n(th)})))'


class FP:
    def __init__(self, name, descr, tags, attr='smd'):
        self.name, self.descr, self.tags, self.attr = name, descr, tags, attr
        self.items, self.pads, self.models, self.extra = [], [], [], []
        self.ref_y, self.val_y, self.datasheet = -3.0, 3.0, ''

    def line(self, x1, y1, x2, y2, layer, w):
        self.items.append(f'(fp_line (start {n(x1)} {n(y1)}) (end {n(x2)} {n(y2)}) '
                          f'(stroke (width {n(w)}) (type solid)) (layer "{layer}"))')

    def rect(self, x1, y1, x2, y2, layer, w=0.05, fill=False):
        self.items.append(f'(fp_rect (start {n(x1)} {n(y1)}) (end {n(x2)} {n(y2)}) '
                          f'(stroke (width {n(w)}) (type solid)) (fill {"yes" if fill else "no"}) '
                          f'(layer "{layer}"))')

    def poly(self, pts, layer):
        p = ' '.join(f'(xy {n(x)} {n(y)})' for x, y in pts)
        self.items.append(f'(fp_poly (pts {p}) (stroke (width 0) (type solid)) (fill yes) '
                          f'(layer "{layer}"))')

    def box(self, cx, cy, w, h, layer):
        """Filled rectangle given by centre and size (mask openings, copper strips)."""
        self.poly([(cx - w / 2, cy - h / 2), (cx + w / 2, cy - h / 2),
                   (cx + w / 2, cy + h / 2), (cx - w / 2, cy + h / 2)], layer)

    def circle(self, cx, cy, r, layer, w=0.12, fill=False):
        self.items.append(f'(fp_circle (center {n(cx)} {n(cy)}) (end {n(cx + r)} {n(cy)}) '
                          f'(stroke (width {n(w)}) (type solid)) (fill {"yes" if fill else "no"}) '
                          f'(layer "{layer}"))')

    def pad(self, num, x, y, w, h, layers, shape='roundrect', rr=None, kind='smd', drill=None,
            extra=''):
        lay = ' '.join(f'"{x_}"' for x_ in layers)
        s = f'(pad "{num}" {kind} {shape} (at {n(x)} {n(y)}) (size {n(w)} {n(h)})'
        if drill:
            s += f' (drill {n(drill)})'
        s += f' (layers {lay})'
        if shape == 'roundrect':
            s += f' (roundrect_rratio {n(rr if rr is not None else 0.25)})'
        self.pads.append(s + extra + ')')

    def paste(self, x, y, w, h, r=0.05):
        """Stencil aperture without copper (unnumbered paste-only pad)."""
        self.pad('', x, y, w, h, ['F.Paste'], rr=min(0.5, r / min(w, h)))

    def model(self, path, off=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1)):
        self.models.append(f'(model "{path}" (offset (xyz {" ".join(n(v) for v in off)})) '
                           f'(scale (xyz {" ".join(n(v) for v in scale)})) '
                           f'(rotate (xyz {" ".join(n(v) for v in rot)})))')

    def text(self):
        out = [f'(footprint "{self.name}"', '\t(version 20241229)',
               '\t(generator "ece533_gen_footprints")', '\t(generator_version "9.0")',
               '\t(layer "F.Cu")', f'\t(descr "{self.descr}")', f'\t(tags "{self.tags}")',
               f'\t(property "Reference" "REF**" (at 0 {n(self.ref_y)} 0) (layer "F.SilkS") {font()})',
               f'\t(property "Value" "{self.name}" (at 0 {n(self.val_y)} 0) (layer "F.Fab") {font()})',
               f'\t(property "Datasheet" "{self.datasheet}" (at 0 0 0) (layer "F.Fab") (hide yes) {font()})',
               f'\t(property "Description" "{self.descr}" (at 0 0 0) (layer "F.Fab") (hide yes) {font()})',
               f'\t(attr {self.attr})']
        out += ['\t' + e for e in self.extra]
        out += ['\t' + i for i in self.items]
        out.append(f'\t(fp_text user "${{REFERENCE}}" (at 0 0 0) (layer "F.Fab") {font(0.8, 0.12)})')
        out += ['\t' + p for p in self.pads]
        out += ['\t' + m for m in self.models]
        out.append(')')
        return '\n'.join(out) + '\n'

    def write(self, lib):
        os.makedirs(lib, exist_ok=True)
        with open(os.path.join(lib, self.name + '.kicad_mod'), 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(self.text())
        print('wrote', os.path.join(os.path.basename(lib), self.name + '.kicad_mod'))


# ---------------------------------------------------------------------------------------------
# EPC2304: datasheet top view, x along the 5 mm length, y up. KiCad y points down, so ky = -y.
# Pin 1 (gate) is top left. Copper per "Recommended copper drawing"; the solder mask openings are
# the "Recommended land pattern" (solder mask defined); paste per "Recommended stencil drawing".
# ---------------------------------------------------------------------------------------------
def epc2304():
    f = FP('EPC2304_QFN-7_3x5mm',
           'EPC2304 200 V eGaN FET, 3 x 5 mm QFN, solder-mask-defined land pattern, copper and stencil '
           'per EPC2304 datasheet pages 12-13',
           'EPC2304 eGaN GaN FET QFN')
    f.datasheet = 'https://epc-co.com/epc/Portals/0/epc/documents/datasheets/EPC2304_datasheet.pdf'
    f.ref_y, f.val_y = -2.9, 2.9
    rr = 0.05
    # copper (pads carry F.Cu only; mask and paste come from the shapes below)
    cu = ['F.Cu']
    f.pad('1', -2.414, -1.222, 1.028, 1.15, cu, rr=rr / 1.028)
    f.pad('2', -2.414, 0.658, 1.028, 2.29, cu, rr=rr / 1.028)
    for num, x in zip('3456', (-1.275, -0.425, 0.425, 1.275)):
        f.pad(num, x, 0, 0.45, 3.6, cu, rr=rr / 0.45)
    f.pad('7', 2.414, 0, 1.028, 3.6, cu, rr=rr / 1.028)
    # solder mask openings (land pattern)
    m = 'F.Mask'
    f.box(-2.175, -(0.714 + 1.700) / 2, 0.40, 0.986, m)           # gate strip 0.40 x 0.985
    f.box(-2.3375, -0.975, 0.725, 0.37, m)                         # gate tab
    f.box(-2.175, -(0.400 - 1.700) / 2, 0.40, 2.10, m)             # source strip 0.40 x 2.10
    for y in (0.225, -0.325, -0.975):                              # source tabs
        f.box(-2.3375, -y, 0.725, 0.37, m)
    for x in (-1.275, -0.425, 0.425, 1.275):                       # 0.30 x 3.40 strips
        f.box(x, 0, 0.30, 3.40, m)
    f.box(2.175, 0, 0.40, 3.40, m)                                 # drain strip 0.40 x 3.40
    for y in (0.975, 0.325, -0.325, -0.975):                       # drain tabs
        f.box(2.3375, -y, 0.725, 0.37, m)
    # stencil (100 um)
    f.paste(-2.090, -1.182, 0.54, 1.035, 0.1)
    for y in (-0.040, -1.213):
        f.paste(-2.090, -y, 0.535, 0.973, 0.1)
    for x in (-1.275, -0.425, 0.425, 1.275):
        for y in (0.9, -0.9):
            f.paste(x, y, 0.40, 1.60, 0.1)
    for y in (0.9, -0.9):
        f.paste(2.143, y, 0.435, 1.60, 0.109)
    for y in (0.975, 0.265, -0.365, -1.000):
        f.paste(-2.665, -y, 0.25, 0.45, 0.06)
    for y in (0.975, 0.325, -0.325, -0.975):
        f.paste(2.665, -y, 0.25, 0.45, 0.06)
    # body, silk, courtyard
    f.rect(-2.5, -1.5, 2.5, 1.5, 'F.Fab', 0.1)
    f.line(-2.5, -1.0, -2.0, -1.5, 'F.Fab', 0.1)
    f.line(-1.75, -1.95, 2.9, -1.95, 'F.SilkS', 0.12)
    f.line(-2.9, 1.95, 2.9, 1.95, 'F.SilkS', 0.12)
    f.circle(-3.25, -1.6, 0.15, 'F.SilkS', 0.12, fill=True)        # pin 1 (gate)
    f.rect(-3.2, -2.1, 3.2, 2.1, 'F.CrtYd', 0.05)
    f.model(f'{VPATH}/EPC2304/3D/EPC2304.stp', rot=(0, 0, 90))
    return f


# EPC2304 for the SamacSys 15-pin symbol used in the PowerModule base schematic (G_1/G_2, S_1-S_6,
# D_1-D_7). Same copper as EPC2304_QFN-7_3x5mm; pins 8-15 are stacked on the matching physical pad
# (same geometry, same net), so the base schematic stays unchanged.
EPC15 = {'1': ['12'], '2': ['15'], '3': ['8'], '4': ['13'], '5': ['9'], '6': ['14'], '7': ['10', '11']}


def epc2304_15pin():
    f = epc2304()
    f.name = 'EPC2304_QFN-7_3x5mm_15pin'
    f.descr += '; pins 8-15 of the SamacSys 15-pin symbol stacked on pads 1-7'
    for p in list(f.pads):
        num = p.split('"')[1]
        for extra in EPC15.get(num, []):
            f.pads.append(p.replace(f'(pad "{num}"', f'(pad "{extra}"', 1))
    return f


# ---------------------------------------------------------------------------------------------
# TDK ERUC23 coupled inductor, "Recommended PCB layout (top view)": 3.7 x 3.7 mm pads, columns
# 7.9 mm apart in the order 4, 1, 3, 2; pads 1/2 on the top row, 3/4 on the bottom row, 14 mm
# overall. Winding A = 4-1, winding B = 3-2.
# ---------------------------------------------------------------------------------------------
def eruc23():
    f = FP('TDK_ERUC23', 'TDK ERUC23 SMT flat-wire coupled inductor, 26.8 x 13.8 mm, TDK recommended '
           'PCB layout (windings 4-1 and 3-2)', 'TDK ERUC23 coupled inductor')
    f.datasheet = 'https://product.tdk.com/system/files/dam/doc/product/inductor/inductor/smd/data_sheet/eru_c23.pdf'
    f.ref_y, f.val_y = -8.3, 8.3
    lay = ['F.Cu', 'F.Paste', 'F.Mask']
    for num, x, y in (('4', -11.85, 5.15), ('1', -3.95, -5.15), ('3', 3.95, 5.15), ('2', 11.85, -5.15)):
        f.pad(num, x, y, 3.7, 3.7, lay, rr=0.05)
    f.rect(-13.4, -6.9, 13.4, 6.9, 'F.Fab', 0.1)
    f.line(-13.55, -7.25, 13.55, -7.25, 'F.SilkS', 0.12)
    f.line(-13.55, 7.25, 13.55, 7.25, 'F.SilkS', 0.12)
    f.circle(-1.6, -7.75, 0.2, 'F.SilkS', 0.12, fill=True)          # pin 1
    f.rect(-14.0, -7.6, 14.0, 7.6, 'F.CrtYd', 0.05)
    # TDK STEP: z is height with the terminals at +z, y is depth 0..13.9 mm -> flip about x
    f.model(f'{VPATH}/TDK_ERUC23/b82559sxm023_eruc23_14.0mm_max_public_tkd-pc.step',
            off=(0, 6.865, 7.2), rot=(180, 0, 0))
    return f


# ---------------------------------------------------------------------------------------------
# Bourns CSS2H-2512 shunt, "Recommended Pad Layout": solder pads 1.80 x 3.40 mm, 3.40 mm gap,
# sense strips rising from the inner bottom corner of each pad. Pads 1/4 = current, 2/3 = sense
# (KiCad Device:R_Shunt numbering). The sense strips are copper shapes inside the net-tie groups.
# ---------------------------------------------------------------------------------------------
def r2512_kelvin():
    f = FP('R_2512_Kelvin', 'Bourns CSS2H-2512 4-terminal (Kelvin) current-sense land pattern per '
           'datasheet, sense strips as net ties (1,2) and (3,4)', 'shunt kelvin 2512 CSS2H')
    f.datasheet = 'https://www.bourns.com/docs/product-datasheets/css2h-2512.pdf'
    f.ref_y, f.val_y = -3.2, 2.8
    f.extra.append('(net_tie_pad_groups "1, 2" "3, 4")')
    f.pad('1', -2.6, 0, 1.8, 3.4, ['F.Cu', 'F.Paste', 'F.Mask'], rr=0.05)
    f.pad('4', 2.6, 0, 1.8, 3.4, ['F.Cu', 'F.Paste', 'F.Mask'], rr=0.05)
    f.pad('2', -1.05, -1.95, 0.43, 0.6, ['F.Cu', 'F.Mask'], shape='rect')
    f.pad('3', 1.05, -1.95, 0.43, 0.6, ['F.Cu', 'F.Mask'], shape='rect')
    for s in (-1, 1):
        # strip: horizontal leg from the pad's inner edge, then up past the body edge
        f.poly([(s * 1.75, 1.2), (s * 0.835, 1.2), (s * 0.835, -1.95), (s * 1.265, -1.95),
                (s * 1.265, 0.8), (s * 1.75, 0.8)], 'F.Cu')
    f.rect(-3.175, -1.525, 3.175, 1.525, 'F.Fab', 0.1)
    f.line(-1.45, 1.95, 1.45, 1.95, 'F.SilkS', 0.12)
    f.line(-0.5, -1.95, 0.5, -1.95, 'F.SilkS', 0.12)
    f.rect(-3.75, -2.5, 3.75, 2.0, 'F.CrtYd', 0.05)
    f.model('${KICAD10_3DMODEL_DIR}/Resistor_SMD.3dshapes/R_2512_6332Metric.step')
    return f


def r2512_css2h():
    """Same Bourns solder pads without sense strips (CSS2H-2512C-000 0 ohm / 100 A link)."""
    f = FP('R_2512_CSS2H', 'Bourns CSS2H-2512 2-terminal land pattern per datasheet (1.80 x 3.40 mm pads, '
           '3.40 mm gap)', 'resistor jumper 2512 CSS2H')
    f.datasheet = 'https://www.bourns.com/docs/product-datasheets/css2h-2512.pdf'
    f.ref_y, f.val_y = -2.7, 2.7
    for num, x in (('1', -2.6), ('2', 2.6)):
        f.pad(num, x, 0, 1.8, 3.4, ['F.Cu', 'F.Paste', 'F.Mask'], rr=0.05)
    f.rect(-3.175, -1.525, 3.175, 1.525, 'F.Fab', 0.1)
    f.line(-1.45, -1.95, 1.45, -1.95, 'F.SilkS', 0.12)
    f.line(-1.45, 1.95, 1.45, 1.95, 'F.SilkS', 0.12)
    f.rect(-3.75, -2.0, 3.75, 2.0, 'F.CrtYd', 0.05)
    f.model('${KICAD10_3DMODEL_DIR}/Resistor_SMD.3dshapes/R_2512_6332Metric.step')
    return f


# ---------------------------------------------------------------------------------------------
# Littelfuse NANO2 456 (20/25/30 A), recommended pad layout: 3.25 x 3.43 mm pads, 6.10 mm gap,
# 12.60 mm overall. Body 10.08 x 3.05 x 3.05 mm, end caps 1.70 mm.
# ---------------------------------------------------------------------------------------------
def fuse456():
    f = FP('Fuse_Littelfuse_NANO2_456', 'Littelfuse NANO2 456 series SMD fuse 20/25/30 A, recommended '
           'pad layout per datasheet (placeholder 3D body)', 'fuse littelfuse 456 nano2')
    f.datasheet = 'https://www.littelfuse.com/assetdocs/littelfuse-fuse-456-datasheet'
    f.ref_y, f.val_y = -2.7, 2.7
    for num, x in (('1', -4.675), ('2', 4.675)):
        f.pad(num, x, 0, 3.25, 3.43, ['F.Cu', 'F.Paste', 'F.Mask'], rr=0.05)
    f.rect(-5.04, -1.525, 5.04, 1.525, 'F.Fab', 0.1)
    f.line(-3.34, -1.525, -3.34, 1.525, 'F.Fab', 0.1)
    f.line(3.34, -1.525, 3.34, 1.525, 'F.Fab', 0.1)
    f.line(-2.85, -1.95, 2.85, -1.95, 'F.SilkS', 0.12)
    f.line(-2.85, 1.95, 2.85, 1.95, 'F.SilkS', 0.12)
    f.rect(-6.55, -2.0, 6.55, 2.0, 'F.CrtYd', 0.05)
    f.model('${KIPRJMOD}/ECE533_Mods.3dshapes/Fuse_Littelfuse_NANO2_456.step')
    return f


# ---------------------------------------------------------------------------------------------
# Vendor footprints (git-ignored library)
# ---------------------------------------------------------------------------------------------
def redcube():
    src = os.path.join(VENDOR, 'Wurth_74650194', 'zip', 'footprints', 'REDCUBE_THT_Wurth.pretty',
                       'MP_Wurth_WP-THRBU_74650194R.kicad_mod')
    if not os.path.exists(src):
        print('skip REDCUBE: vendor file missing', src)
        return
    txt = open(src, encoding='utf-8').read()
    txt = txt.replace('(footprint "MP_Wurth_WP-THRBU_74650194R"', '(footprint "Wurth_REDCUBE_74650194"', 1)
    txt = re.sub(r'\(model "[^"]*"', f'(model "{VPATH}/Wurth_74650194/zip/3dmodels/'
                 'REDCUBE_THT_Wurth.3dshapes/MP_Wurth_WP-THRBU_74650194.step"', txt)
    os.makedirs(VLIB, exist_ok=True)
    with open(os.path.join(VLIB, 'Wurth_REDCUBE_74650194.kicad_mod'), 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(txt)
    print('wrote ECE533_Vendor.pretty/Wurth_REDCUBE_74650194.kicad_mod')


def nme1s():
    """SamacSys NME1S0505SC (legacy format) rewritten in the current format, same geometry."""
    src = os.path.join(VENDOR, 'NME1S0505SC', 'KiCad', 'NME1S0505SC.kicad_mod')
    if not os.path.exists(src):
        print('skip NME1S: vendor file missing', src)
        return
    f = FP('Murata_NME1S_SIP-4', 'Murata NME1S 1 W isolated DC-DC, SIP-4 2.54 mm (SamacSys footprint)',
           'NME1S0505SC SIP-4 isolated DC-DC', attr='through_hole')
    f.ref_y, f.val_y = -6.4, 2.6
    for i in range(4):
        f.pad(str(i + 1), i * 2.54, 0, 1.612, 1.612, ['*.Cu', '*.Mask'],
              shape='rect' if i == 0 else 'circle', kind='thru_hole', drill=1.075)
    f.rect(-2.19, -4.87, 9.31, 1.13, 'F.Fab', 0.1)
    for x1, y1, x2, y2 in ((-1.44, 1.13, -2.19, 1.13), (-2.19, 1.13, -2.19, -4.87),
                           (-2.19, -4.87, 9.31, -4.87), (9.31, -4.87, 9.31, 1.13), (9.31, 1.13, 8.56, 1.13)):
        f.line(x1, y1, x2, y2, 'F.SilkS', 0.2)
    f.circle(-2.75, 0, 0.05, 'F.SilkS', 0.1)
    f.rect(-3.19, -5.87, 10.31, 2.13, 'F.CrtYd', 0.05)
    # SamacSys model transform was in inches (legacy format): 0.3 in, -0.026 in
    f.model(f'{VPATH}/NME1S0505SC/3D/NME1S0505SC.stp', off=(7.62, 0, -0.66), rot=(-90, 0, -180))
    f.write(VLIB)


# ---------------------------------------------------------------------------------------------
# Minimal STEP writer: axis-aligned boxes with colours (placeholder 3D bodies)
# ---------------------------------------------------------------------------------------------
def step_boxes(path, name, boxes):
    """boxes: list of ((x0, y0, z0), (x1, y1, z1), (r, g, b))."""
    ents = []

    def e(s):
        ents.append(s)
        return len(ents)

    def pt(p):
        return e("CARTESIAN_POINT('',(%s));" % ','.join(f'{v:.6f}' for v in p))

    def dr(d):
        return e("DIRECTION('',(%s));" % ','.join(f'{v:.6f}' for v in d))

    ctx = e("APPLICATION_CONTEXT('automotive design');")
    e(f"APPLICATION_PROTOCOL_DEFINITION('international standard','automotive_design',2000,#{ctx});")
    pc = e(f"PRODUCT_CONTEXT('',#{ctx},'mechanical');")
    prod = e(f"PRODUCT('{name}','{name}','',(#{pc}));")
    e(f"PRODUCT_RELATED_PRODUCT_CATEGORY('part',$,(#{prod}));")
    pdf = e(f"PRODUCT_DEFINITION_FORMATION('','',#{prod});")
    pdc = e(f"PRODUCT_DEFINITION_CONTEXT('part definition',#{ctx},'design');")
    pd = e(f"PRODUCT_DEFINITION('design','',#{pdf},#{pdc});")
    pds = e(f"PRODUCT_DEFINITION_SHAPE('','',#{pd});")
    lu = e("(LENGTH_UNIT()NAMED_UNIT(*)SI_UNIT(.MILLI.,.METRE.));")
    au = e("(NAMED_UNIT(*)PLANE_ANGLE_UNIT()SI_UNIT($,.RADIAN.));")
    su = e("(NAMED_UNIT(*)SI_UNIT($,.STERADIAN.)SOLID_ANGLE_UNIT());")
    um = e(f"UNCERTAINTY_MEASURE_WITH_UNIT(LENGTH_MEASURE(1.E-07),#{lu},'distance_accuracy_value','confusion accuracy');")
    gc = e(f"(GEOMETRIC_REPRESENTATION_CONTEXT(3)GLOBAL_UNCERTAINTY_ASSIGNED_CONTEXT((#{um}))"
           f"GLOBAL_UNIT_ASSIGNED_CONTEXT((#{lu},#{au},#{su}))REPRESENTATION_CONTEXT('Context3D','3D Context'));")
    origin = e(f"AXIS2_PLACEMENT_3D('',#{pt((0, 0, 0))},#{dr((0, 0, 1))},#{dr((1, 0, 0))});")
    solids, styled = [], []
    for (lo, hi, rgb) in boxes:
        V = [(hi[0] if i & 1 else lo[0], hi[1] if i & 2 else lo[1], hi[2] if i & 4 else lo[2]) for i in range(8)]
        vp = [e(f"VERTEX_POINT('',#{pt(v)});") for v in V]
        edges = {}

        def edge(a, b):
            key = (min(a, b), max(a, b))
            if key not in edges:
                p0, p1 = V[key[0]], V[key[1]]
                d = [p1[k] - p0[k] for k in range(3)]
                ln = max(abs(c) for c in d)
                vec = e(f"VECTOR('',#{dr([c / ln for c in d])},{ln:.6f});")
                line = e(f"LINE('',#{pt(p0)},#{vec});")
                edges[key] = e(f"EDGE_CURVE('',#{vp[key[0]]},#{vp[key[1]]},#{line},.T.);")
            return e(f"ORIENTED_EDGE('',*,*,#{edges[key]},{'.T.' if a < b else '.F.'});")

        faces = []
        for axis in range(3):
            i, j = [k for k in range(3) if k != axis]
            for side in (0, 1):
                cyc = [(0, 0), (1, 0), (1, 1), (0, 1)]
                idx = [(side << axis) | (a << i) | (b << j) for a, b in cyc]
                p = [V[k] for k in idx]
                u = [p[1][k] - p[0][k] for k in range(3)]
                w = [p[2][k] - p[1][k] for k in range(3)]
                cr = [u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0]]
                normal = [0, 0, 0]
                normal[axis] = 1 if side else -1
                if sum(cr[k] * normal[k] for k in range(3)) < 0:
                    idx = idx[::-1]
                loop = e("EDGE_LOOP('',(%s));" % ','.join(f'#{edge(idx[k], idx[(k + 1) % 4])}' for k in range(4)))
                bound = e(f"FACE_OUTER_BOUND('',#{loop},.T.);")
                ref = [0, 0, 0]
                ref[i] = 1
                plc = e(f"AXIS2_PLACEMENT_3D('',#{pt(V[idx[0]])},#{dr(normal)},#{dr(ref)});")
                plane = e(f"PLANE('',#{plc});")
                faces.append(e(f"ADVANCED_FACE('',(#{bound}),#{plane},.T.);"))
        shell = e("CLOSED_SHELL('',(%s));" % ','.join(f'#{x}' for x in faces))
        solid = e(f"MANIFOLD_SOLID_BREP('',#{shell});")
        solids.append(solid)
        col = e("COLOUR_RGB('',%s);" % ','.join(f'{c:.3f}' for c in rgb))
        fac = e(f"FILL_AREA_STYLE_COLOUR('',#{col});")
        fas = e(f"FILL_AREA_STYLE('',(#{fac}));")
        ssf = e(f"SURFACE_STYLE_FILL_AREA(#{fas});")
        sss = e(f"SURFACE_SIDE_STYLE('',(#{ssf}));")
        ssu = e(f"SURFACE_STYLE_USAGE(.BOTH.,#{sss});")
        psa = e(f"PRESENTATION_STYLE_ASSIGNMENT((#{ssu}));")
        styled.append(e(f"STYLED_ITEM('color',(#{psa}),#{solid});"))
    rep = e("ADVANCED_BREP_SHAPE_REPRESENTATION('%s',(#%d,%s),#%d);"
            % (name, origin, ','.join(f'#{s}' for s in solids), gc))
    e(f"SHAPE_DEFINITION_REPRESENTATION(#{pds},#{rep});")
    e("MECHANICAL_DESIGN_GEOMETRIC_PRESENTATION_REPRESENTATION('',(%s),#%d);"
      % (','.join(f'#{s}' for s in styled), gc))
    head = ["ISO-10303-21;", "HEADER;", f"FILE_DESCRIPTION(('{name} placeholder body'),'2;1');",
            f"FILE_NAME('{name}.step','2026-10-16T00:00:00',('ECE533'),(''),'gen_footprints.py','','');",
            "FILE_SCHEMA(('AUTOMOTIVE_DESIGN { 1 0 10303 214 1 1 1 1 }'));", "ENDSEC;", "DATA;"]
    body = [f'#{k + 1}={s}' for k, s in enumerate(ents)]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='ascii', newline='\n') as fh:
        fh.write('\n'.join(head + body + ['ENDSEC;', 'END-ISO-10303-21;']) + '\n')
    print('wrote', os.path.relpath(path, PRJ))


def fuse_step():
    L, cap, W, Wb = 10.08, 1.70, 3.05, 2.85
    silver, ceramic = (0.80, 0.80, 0.78), (0.93, 0.92, 0.88)
    step_boxes(os.path.join(SHAPES, 'Fuse_Littelfuse_NANO2_456.step'), 'Fuse_Littelfuse_NANO2_456', [
        ((-L / 2, -W / 2, 0), (-L / 2 + cap, W / 2, W), silver),
        ((L / 2 - cap, -W / 2, 0), (L / 2, W / 2, W), silver),
        ((-L / 2 + cap, -Wb / 2, (W - Wb) / 2), (L / 2 - cap, Wb / 2, (W + Wb) / 2), ceramic),
    ])


if __name__ == '__main__':
    for fn in (epc2304, epc2304_15pin, eruc23, r2512_kelvin, r2512_css2h, fuse456):
        fn().write(MODS)
    fuse_step()
    redcube()
    nme1s()
