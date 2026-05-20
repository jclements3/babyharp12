#!/usr/bin/env python3
"""Generate babyharp12.scad — a 3D OpenSCAD assembly of the prototype.

Reads frame_data.py (Bezier curves + short raw d-strings), samples each
profile into a polygon, and writes a self-contained OpenSCAD file with
all the laminated Baltic-birch parts from BOM.md in their assembled
positions:

  2 neck cheeks + 3 neck-spacer layers + 2 column supports +
  3 column-body layers + 2 soundbox cheeks + 1 joint + 1 soundboard
  + 1 back panel with two oval sound holes.

Re-generate after editing the frame data:

    python3 tools/make_scad.py

Then open ../babyharp12.scad in OpenSCAD (F5 preview, F6 render).
"""
from __future__ import annotations
import re, sys, math
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
import frame_data

OUT_SCAD = REPO / "babyharp12.scad"

# --- Scale -------------------------------------------------------------------
# Must match babyharp.py: INNER_PER_MM = 66.6 / BIG_CIRCLE_DIA_MM
BIG_CIRCLE_DIA_MM = 7.0
INNER_PER_MM = 66.6 / BIG_CIRCLE_DIA_MM
MM_PER_INNER = 1.0 / INNER_PER_MM

# --- Bezier sampling ---------------------------------------------------------
def sample_bez(p0, c1, c2, p3, n=18):
    """Yield (n) points along a cubic Bezier from t=1/n .. t=1 (skips t=0)."""
    for i in range(1, n + 1):
        t = i / n
        u = 1 - t
        yield (u*u*u*p0[0] + 3*u*u*t*c1[0] + 3*u*t*t*c2[0] + t*t*t*p3[0],
               u*u*u*p0[1] + 3*u*u*t*c1[1] + 3*u*t*t*c2[1] + t*t*t*p3[1])

def bezpath_to_poly(seq, beziers, n=18):
    """Convert (start, [bez,...]) to a flat polygon in mm coords."""
    pts = [seq[0]]
    for i, b in enumerate(beziers):
        pts.extend(sample_bez(seq[i], b[0], b[1], b[2], n))
    # Convert inner -> mm
    return [(p[0] * MM_PER_INNER, p[1] * MM_PER_INNER) for p in pts]

# --- Parse short d-string paths ---------------------------------------------
_TOK = re.compile(r'[MmLlHhVvCcSsQqTtAaZz]|-?\d*\.?\d+(?:[eE][+-]?\d+)?')

def parse_d(d):
    """Parse a small SVG d-string into a list of (x,y) absolute points, mm."""
    toks = _TOK.findall(d)
    pts = []; i = 0; x = y = 0.0; cur = ''; first = True
    while i < len(toks):
        t = toks[i]
        if t in 'MmLlHhVvCcSsQqTtAaZz':
            cur = t; i += 1; continue
        abs_first = first
        if cur in 'Mm':
            cx, cy = float(t), float(toks[i+1])
            if cur == 'M' or abs_first: x, y = cx, cy
            else: x += cx; y += cy
            pts.append((x, y)); i += 2
            cur = 'L' if cur == 'M' else 'l'
            first = False
        elif cur in 'Ll':
            cx, cy = float(t), float(toks[i+1])
            if cur == 'L': x, y = cx, cy
            else: x += cx; y += cy
            pts.append((x, y)); i += 2
        elif cur in 'Hh':
            v = float(t)
            x = v if cur == 'H' else x + v
            pts.append((x, y)); i += 1
        elif cur in 'Vv':
            v = float(t)
            y = v if cur == 'V' else y + v
            pts.append((x, y)); i += 1
        elif cur in 'Cc':
            ex = float(toks[i+4]); ey = float(toks[i+5])
            if cur == 'C': x, y = ex, ey
            else: x += ex; y += ey
            pts.append((x, y)); i += 6
        else:
            i += 1
    return [(p[0] * MM_PER_INNER, p[1] * MM_PER_INNER) for p in pts]

# --- Build the polygons ------------------------------------------------------
neck_poly    = bezpath_to_poly(frame_data.P20_SEQ, frame_data.P20_BEZ)
col_back     = bezpath_to_poly(frame_data.P68_SEQ, frame_data.P68_BEZ)   # outer back of column
col_front    = bezpath_to_poly(frame_data.P70_SEQ, frame_data.P70_BEZ)   # inner front of column

# Column polygon: assembled from col_back + a short straight base + col_front
# This matches babyharp.py's d_column closure.
col_base    = parse_d(frame_data.PATH66_D)   # bass-end base (1244,66.5)->(1335.2,67.7)
col_poly    = col_back + col_base + col_front[::-1]

# Soundbox polygon = path74 + path76 (concatenated)
sb_left     = parse_d(frame_data.PATH74_D)
sb_right    = parse_d(frame_data.PATH76_D)
sbx_poly    = sb_left + sb_right[1:]

# Joint polygon
joint_poly  = parse_d(frame_data.PATH72_D)

# Treble-end neck spacer — for the 3D model we approximate it as a vertical
# strip between the joint and a vertical line above the G6 eyelet. The exact
# 2D shape comes from babyharp12.svg; here we mock the bounding box and let
# the user refine it later if desired.
nb_xs = [p[0] for p in neck_poly]
nb_ys = [p[1] for p in neck_poly]
sx0, sx1 = max(nb_xs) - 90, max(nb_xs)     # treble end ~90 mm wide
sy_lo, sy_hi = min(nb_ys) + 5, max(nb_ys) - 5
spacer_poly = [(sx0, sy_lo), (sx1, sy_lo), (sx1, sy_hi), (sx0, sy_hi)]

# --- Layer Z positions (BOM-driven) ------------------------------------------
PLY = 6.0                    # Baltic birch ply mm
NECK_T = 5 * PLY             # 2 cheeks + 3 spacers = 30 mm
Z_BACK_CHEEK = -NECK_T/2          # -15
Z_SPACER0    = -NECK_T/2 + PLY    # -9
Z_SPACER1    = -NECK_T/2 + 2*PLY  # -3
Z_SPACER2    = -NECK_T/2 + 3*PLY  # +3
Z_FRONT_CHEEK= -NECK_T/2 + 4*PLY  # +9

# Soundbox is wider than the neck (more interior volume). Use 2 cheeks of
# 6 mm spaced 60 mm apart with the back panel closing the rear.
SBX_T = 60.0
Z_SBX_BACK_CHEEK  = -SBX_T/2
Z_SBX_FRONT_CHEEK = +SBX_T/2 - PLY

# Soundboard thickness and Z-centering
SOUNDBOARD_T = 3.0

# Back panel
BACK_T = 3.0
Z_BACK_PANEL = -SBX_T/2 - BACK_T   # behind the back soundbox cheek

# --- Sound holes (per BOM) ---------------------------------------------------
# Two ovals on the back panel, long axis vertical (along soundboard direction).
# Placed roughly 1/3 and 2/3 along the soundboard span.
SH_OVAL_LONG_MM  = 40
SH_OVAL_SHORT_MM = 22

# Soundboard span = C8 -> S0 (column foot to soundbox top corner). In mm:
C8_MM = (1787.0 * MM_PER_INNER, 847.102 * MM_PER_INNER)
S0_MM = (2918.0 * MM_PER_INNER, 2807.3 * MM_PER_INNER)
SB_LEN = math.hypot(S0_MM[0]-C8_MM[0], S0_MM[1]-C8_MM[1])

# Sound holes positioned at 1/3 and 2/3 along the soundboard centerline
SH1 = ((C8_MM[0] + (S0_MM[0]-C8_MM[0]) * 1/3),
       (C8_MM[1] + (S0_MM[1]-C8_MM[1]) * 1/3))
SH2 = ((C8_MM[0] + (S0_MM[0]-C8_MM[0]) * 2/3),
       (C8_MM[1] + (S0_MM[1]-C8_MM[1]) * 2/3))

# --- SCAD emit ---------------------------------------------------------------
def scad_polygon(name, pts):
    pts_str = ', '.join(f'[{p[0]:.3f},{p[1]:.3f}]' for p in pts)
    return f'{name} = [{pts_str}];\n'

lines = []
lines.append('// babyharp12.scad - 3D assembly of the BabyHarp 12 prototype.')
lines.append('// Auto-generated by tools/make_scad.py from frame_data.py.')
lines.append('// Open in OpenSCAD (F5 preview / F6 render).')
lines.append('')
lines.append('$fn = 64;')
lines.append('')
lines.append('// ---------- Profile polygons (mm) ----------')
lines.append(scad_polygon('NECK_OUTLINE',     neck_poly))
lines.append(scad_polygon('COLUMN_OUTLINE',   col_poly))
lines.append(scad_polygon('SPACER_OUTLINE',   spacer_poly))
lines.append(scad_polygon('SOUNDBOX_OUTLINE', sbx_poly))
lines.append(scad_polygon('JOINT_OUTLINE',    joint_poly))

lines.append('')
lines.append('// ---------- Layer thicknesses ----------')
lines.append(f'PLY            = {PLY};')
lines.append(f'NECK_THICKNESS = {NECK_T};   // 2 cheeks + 3 spacers')
lines.append(f'SBX_INTERIOR   = {SBX_T - 2*PLY};')
lines.append(f'SBX_WIDTH      = {SBX_T};   // soundbox cheek-to-cheek')
lines.append(f'SOUNDBOARD_T   = {SOUNDBOARD_T};')
lines.append(f'BACK_T         = {BACK_T};')
lines.append('')

# Layer Z positions
lines.append('// ---------- Z positions ----------')
for name, val in [('Z_BACK_CHEEK', Z_BACK_CHEEK),
                  ('Z_SPACER0', Z_SPACER0),
                  ('Z_SPACER1', Z_SPACER1),
                  ('Z_SPACER2', Z_SPACER2),
                  ('Z_FRONT_CHEEK', Z_FRONT_CHEEK),
                  ('Z_SBX_BACK_CHEEK', Z_SBX_BACK_CHEEK),
                  ('Z_SBX_FRONT_CHEEK', Z_SBX_FRONT_CHEEK),
                  ('Z_BACK_PANEL', Z_BACK_PANEL)]:
    lines.append(f'{name} = {val:.3f};')

lines.append('')
lines.append('// ---------- Colors ----------')
lines.append('PLY_COLOR    = [0.82, 0.71, 0.55];     // Baltic birch')
lines.append('TONEWOOD     = [0.93, 0.84, 0.70];     // Sitka spruce')
lines.append('BACK_COLOR   = [0.65, 0.50, 0.35];     // back panel (birch stained)')
lines.append('STRING_COLOR = [0.20, 0.20, 0.20];')
lines.append('')

# Soundboard placement: between C8 and S0, at 65 degrees from horizontal,
# 3 mm thick, spanning the soundbox width.
lines.append(f'// ---------- Soundboard endpoints (mm) ----------')
lines.append(f'C8 = [{C8_MM[0]:.3f}, {C8_MM[1]:.3f}];')
lines.append(f'S0 = [{S0_MM[0]:.3f}, {S0_MM[1]:.3f}];')
lines.append(f'SB_LEN = {SB_LEN:.3f};')
lines.append('')
lines.append('// ---------- Sound hole positions ----------')
lines.append(f'SH1 = [{SH1[0]:.3f}, {SH1[1]:.3f}];')
lines.append(f'SH2 = [{SH2[0]:.3f}, {SH2[1]:.3f}];')
lines.append(f'SH_LONG  = {SH_OVAL_LONG_MM};')
lines.append(f'SH_SHORT = {SH_OVAL_SHORT_MM};')
lines.append('')

# --- Modules ---
lines.append("""// ---------- Modules ----------

module ply_layer(profile, z) {
    color(PLY_COLOR)
        translate([0, 0, z])
            linear_extrude(height = PLY)
                polygon(profile);
}

module neck_back()    { ply_layer(NECK_OUTLINE, Z_BACK_CHEEK); }
module neck_front()   { ply_layer(NECK_OUTLINE, Z_FRONT_CHEEK); }
module neck_spacer(z) { ply_layer(SPACER_OUTLINE, z); }

module column_body(z) { ply_layer(COLUMN_OUTLINE, z); }
// Column supports = same column shape but only the top portion overlapping
// the neck-attach area. Approximated by intersecting with a "top region" box.
module column_support(z) {
    intersection() {
        ply_layer(COLUMN_OUTLINE, z);
        // Top region: rough bounding box from neck outline overlap
        translate([0, 200, z - 1])
            cube([1000, 800, PLY + 2]);
    }
}

module soundbox_cheek(z) { ply_layer(SOUNDBOX_OUTLINE, z); }
module joint(z)          { ply_layer(JOINT_OUTLINE, z); }

// Soundboard: a flat strip extruded along the soundboard line (C8 -> S0),
// rotated so the long axis lies between them, set 3 mm thick along its
// surface normal. Placed between the soundbox cheeks (Z centered on 0).
module soundboard() {
    sb_angle_rad = atan2(S0[1] - C8[1], S0[0] - C8[0]);
    sb_angle_deg = sb_angle_rad;
    color(TONEWOOD)
        translate([C8[0], C8[1], -SBX_INTERIOR/2])
            rotate([0, 0, sb_angle_deg])
                translate([0, -25, 0])   // strip width 50 mm
                    cube([SB_LEN, 50, SOUNDBOARD_T]);
}

// Back panel with sound holes. Lies in the X-Y plane at Z = Z_BACK_PANEL.
module back_panel() {
    color(BACK_COLOR)
        translate([0, 0, Z_BACK_PANEL])
            linear_extrude(BACK_T)
                difference() {
                    polygon(SOUNDBOX_OUTLINE);
                    translate(SH1) scale([SH_SHORT/SH_LONG, 1, 1]) circle(d = SH_LONG);
                    translate(SH2) scale([SH_SHORT/SH_LONG, 1, 1]) circle(d = SH_LONG);
                }
}

// ---------- Assembly ----------
module babyharp() {
    // Neck stack (right cheek back, 3 spacer layers, left cheek front)
    neck_back();
    neck_spacer(Z_SPACER0);
    neck_spacer(Z_SPACER1);
    neck_spacer(Z_SPACER2);
    neck_front();

    // Column stack (3-layer body matches the spacer Zs; 2 supports flank it)
    column_body(Z_SPACER0);
    column_body(Z_SPACER1);
    column_body(Z_SPACER2);
    column_support(Z_BACK_CHEEK);
    column_support(Z_FRONT_CHEEK);

    // Joint piece — single 6 mm layer between the cheeks
    joint(Z_SPACER1);

    // Soundbox
    soundbox_cheek(Z_SBX_BACK_CHEEK);
    soundbox_cheek(Z_SBX_FRONT_CHEEK);
    back_panel();
    soundboard();
}

babyharp();
""")

OUT_SCAD.write_text('\n'.join(lines))
print(f"Wrote {OUT_SCAD} ({OUT_SCAD.stat().st_size} bytes)")
