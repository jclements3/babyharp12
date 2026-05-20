#!/usr/bin/env python3
"""Parameterize the BabyHarp SVG.

Run: python3 babyharp.py
Edits babyharp12.svg in place: scales using BIG_CIRCLE_DIA_MM as reference,
computes each string's vibrating length from the geometry, then back-solves
the string diameter required to vibrate at the target note (under TENSION_N).

String routing per string (soundboard end -> terminus):
  1. straight tangent from soundboard attachment to small circle (pin)
  2. clockwise arc along small circle
  3. straight common tangent to big circle
  4. arc around big circle (tuning pin terminus)
"""
from __future__ import annotations
import math, re, sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
sys.path.insert(0, str(Path(__file__).parent))
import frame_data

# ==================================================================
# PARAMETERS
# ==================================================================
# --- Geometry constraints --------------------------------------------------
RAKE_ANGLE_DEG       = 50.0   # (a) angle BETWEEN string and soundboard
BASS_OFFSET_MM       = 16.0   # bass string eyelet, distance from column foot
PIN_INSET_MM         = 13.0   # perpendicular distance from each small pin
                              # to the inside neck edge
TAKEOFF_ANGLE_DEG    = 30.0   # string angle leaving small circle toward big

# --- Physical sizes --------------------------------------------------------
STRING_AIR_GAP_MM    = 13.0   # gap between adjacent string ODs at the soundbox
EYELET_ID_MM         = 2.0    # inner diameter of each soundbox eyelet hole.
                              # CRAFTME Studio 2mm self-backing grommets.
                              # The string sits tangent to the eyelet's upper
                              # inner edge (the edge facing the neck) when in
                              # tension, so the eyelet center sits below the
                              # string center by (eyelet_r - string_r).
SMALL_CIRCLE_DIA_MM  = 3.0    # small-hole (string-guide PIN) OD
BIG_CIRCLE_DIA_MM    = 7.0    # big-hole (TUNER) OD; used for mm scale.
                              # Sized so the equally-spaced eyelets produce
                              # a perpendicular OD-to-OD air gap of ~13mm
                              # between adjacent strings.
NUM_STRINGS          = 12

# --- Pin -> tuner routing ----------------------------------------------------
# After the string wraps CW around the small pin it continues to the big tuner.
# The pin->tuner segment is at TUNER_TAKEOFF_DEG above the string trajectory.
# The distance from pin to tuner is a linear gradient bass -> treble.
TUNER_TAKEOFF_DEG    = 30.0   # angle of pin->tuner line off string direction
TUNER_DIST_BASS_MM   = 30.0   # pin->tuner distance for the lowest string
TUNER_DIST_TREBLE_MM = 15.0   # pin->tuner distance for the highest string

def tuner_dist_mm(i: int) -> float:
    return TUNER_DIST_BASS_MM + (TUNER_DIST_TREBLE_MM - TUNER_DIST_BASS_MM) * i / (NUM_STRINGS - 1)

# --- Tuning (lowest -> highest) -------------------------------------------
# 11 strings, diatonic from C4 upward: C4 D4 E4 F4 G4 A4 B4 C5 D5 E5 F5.
# Set TUNING_START to "C5" for an octave higher; or replace NOTES outright.
TUNING_START         = "C5"
TUNING_MODE          = "diatonic"   # "diatonic" or "chromatic"

def build_notes(start: str, n: int, mode: str) -> list[str]:
    chromatic = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]
    diatonic_steps = [2,2,1,2,2,2,1]   # whole/half pattern from C
    name, octv = start[:-1], int(start[-1])
    idx = chromatic.index(name)
    out, step_i = [], 0
    for k in range(n):
        out.append(f"{chromatic[idx]}{octv}")
        if mode == "chromatic":
            idx += 1
        else:
            idx += diatonic_steps[step_i % 7]; step_i += 1
        if idx >= 12: idx -= 12; octv += 1
    return out

NOTES = build_notes(TUNING_START, NUM_STRINGS, TUNING_MODE)

# --- String physics --------------------------------------------------------
# Nylon monofilament (most common for Paraguayan harps).
STRING_DENSITY_KG_M3 = 1140.0
# Per-string tension gradient (N). Bass strings under higher tension so the
# bass diameter comes out LARGER than the treble. Adjust to taste.
TENSION_BASS_N       = 100.0   # string 1
TENSION_TREBLE_N     = 8.0     # string N — much lower so treble diameter shrinks
def tension_for(i: int) -> float:
    return TENSION_BASS_N + (TENSION_TREBLE_N - TENSION_BASS_N) * i / (NUM_STRINGS - 1)

# --- Render --------------------------------------------------------------
STRING_COLOR_DEFAULT = "#888888"   # gray
STRING_COLOR_C       = "#cc0000"   # red for C notes
STRING_COLOR_F       = "#0066cc"   # blue for F notes

def string_color(note: str) -> str:
    n = note[:-1]
    if n == "C": return STRING_COLOR_C
    if n == "F": return STRING_COLOR_F
    return STRING_COLOR_DEFAULT

# ==================================================================
# Existing SVG references — DO NOT EDIT unless the SVG changes
# ==================================================================
SVG_PATH       = Path(__file__).parent / "babyharp12.svg"

SMALL_HOLES_INNER = [
    (870.797, 3663.8), (1040.0, 3615.8), (1230.8, 3521.0),
    (1448.0, 3357.8), (1667.0, 3191.6), (1847.0, 3115.4),
    (2010.8, 3091.4), (2159.6, 3098.0), (2299.4, 3128.0),
    (2430.8, 3180.2), (2552.0, 3249.2),
    (2664.0, 3334.0),   # extrapolated 12th pin (G5)
]
BIG_HOLES_INNER = [
    (966.797, 3985.4), (1122.8, 3875.0), (1300.4, 3722.0),
    (1502.6, 3504.2), (1724.0, 3338.0), (1905.2, 3266.6),
    (2067.2, 3245.6), (2218.4, 3254.6), (2357.0, 3290.6),
    (2487.2, 3335.6), (2613.2, 3401.6),
]
SOUNDBOARD_A = (1339.4, 71.3008)
SOUNDBOARD_B = (2918.0,  2807.3)
# Where the inner column (path70) meets the soundboard — bass string is
# BASS_OFFSET_MM up the soundboard from this point.
INNER_COLUMN_FOOT = (1787.0, 847.102)

INNER_BIG_DIA = 33.3 * 2
INNER_PER_MM  = INNER_BIG_DIA / BIG_CIRCLE_DIA_MM    # ~11.1 inner / mm
MM_PER_INNER  = 1.0 / INNER_PER_MM

# ==================================================================
# Math helpers
# ==================================================================
def unit(v):  n = math.hypot(*v); return (v[0]/n, v[1]/n)
def add(a,b): return (a[0]+b[0], a[1]+b[1])
def sub(a,b): return (a[0]-b[0], a[1]-b[1])
def mul(a,k): return (a[0]*k, a[1]*k)
def perp(v):  return (-v[1], v[0])
def dist(a,b):return math.hypot(a[0]-b[0], a[1]-b[1])

SB_DIR  = unit(sub(SOUNDBOARD_B, SOUNDBOARD_A))   # base -> neck-junction
# Soundboard line: y = m*x + b in inner coords
SB_M = (SOUNDBOARD_B[1] - SOUNDBOARD_A[1]) / (SOUNDBOARD_B[0] - SOUNDBOARD_A[0])
SB_B = SOUNDBOARD_A[1] - SB_M * SOUNDBOARD_A[0]

# ==================================================================
# String direction: at RAKE_ANGLE_DEG (interpretation a) from soundboard,
# pointing FROM pin TOWARD soundboard (i.e., downward on screen).
# ==================================================================
def string_direction():
    """Unit vector from pin toward soundboard, at RAKE_ANGLE from sb line."""
    sb_down = (-SB_DIR[0], -SB_DIR[1])
    a = math.radians(RAKE_ANGLE_DEG)
    c, s = math.cos(a), math.sin(a)
    # Rotate sb_down +RAKE (CCW in inner) — choose the rotation that puts X>0
    cand1 = (sb_down[0]*c - sb_down[1]*s, sb_down[0]*s + sb_down[1]*c)
    cand2 = (sb_down[0]*c + sb_down[1]*s, -sb_down[0]*s + sb_down[1]*c)
    return cand1 if cand1[0] > cand2[0] else cand2

# ==================================================================
# Frequency / diameter relation
# ==================================================================
def note_freq_hz(note: str) -> float:
    """Equal-tempered, A4 = 440 Hz."""
    semitone_from_A = {"C":-9,"C#":-8,"D":-7,"D#":-6,"E":-5,"F":-4,
                       "F#":-3,"G":-2,"G#":-1,"A":0,"A#":1,"B":2}
    n, o = note[:-1], int(note[-1])
    semis = semitone_from_A[n] + (o-4)*12
    return 440.0 * 2.0**(semis/12.0)

def diameter_for_freq_mm(length_mm: float, freq_hz: float,
                         tension_N: float, density: float) -> float:
    """f = (1/2L) sqrt(T / (rho * pi * (d/2)^2))
       => d = (1/(L f)) * sqrt(T / (pi rho))
       L in meters, returns d in mm."""
    L = length_mm / 1000.0
    d_m = (1.0/(L*freq_hz)) * math.sqrt(tension_N / (math.pi*density))
    return d_m * 1000.0

# ==================================================================
# Per-string geometry: left-tangent point on small circle + soundboard end
# ==================================================================
def small_radius_inner():
    return (SMALL_CIRCLE_DIA_MM / 2) * INNER_PER_MM

def left_tangent_point(pin_c, str_dir_u):
    """Tangent point on the LEFT side of the pin (negative-X perpendicular)
    relative to the string direction. Returns inner-coord point."""
    # Two perpendiculars: rotate str_dir +/- 90°
    p1 = (-str_dir_u[1], str_dir_u[0])     # CCW 90°
    p2 = ( str_dir_u[1], -str_dir_u[0])    # CW 90°
    n = p1 if p1[0] < p2[0] else p2        # pick the one with smaller X
    r = small_radius_inner()
    return (pin_c[0] + n[0]*r, pin_c[1] + n[1]*r)

def soundboard_hit(start_pt, str_dir_u):
    """Where a ray from start_pt in str_dir_u hits the soundboard line."""
    # start_y + t*dy = SB_M*(start_x + t*dx) + SB_B
    # t*(dy - SB_M*dx) = SB_M*start_x + SB_B - start_y
    denom = str_dir_u[1] - SB_M*str_dir_u[0]
    t = (SB_M*start_pt[0] + SB_B - start_pt[1]) / denom
    return (start_pt[0] + t*str_dir_u[0], start_pt[1] + t*str_dir_u[1])

def vibrating_length_mm(start_pt, end_pt):
    return dist(start_pt, end_pt) * MM_PER_INNER

def build_string_path(start_pt, end_pt):
    return f"M {start_pt[0]:.2f} {start_pt[1]:.2f} L {end_pt[0]:.2f} {end_pt[1]:.2f}"

# ==================================================================
# StringSpec: all the named per-string state in one place.
# After main() runs, STRINGS["C5"].eyelet (alias: c5e), .pin (c5p), .tuner (c5t)
# hold the inner-coord points. .length_mm, .diameter_mm, .tension_n, .freq_hz
# hold the physics. Iterate STRINGS.values() to walk every string.
# ==================================================================
@dataclass
class StringSpec:
    note: str                            # e.g. "C5"
    freq_hz: float
    tension_n: float
    eyelet: tuple = (0.0, 0.0)           # string CENTERLINE start (where the path begins)
    eyelet_hole: tuple = (0.0, 0.0)      # eyelet CIRCLE center (shifted below s.eyelet)
    pin: tuple = (0.0, 0.0)              # small-circle (string-guide) center
    tuner: Optional[tuple] = None        # big-circle (tuning peg) — TBD
    length_mm: float = 0.0
    diameter_mm: float = 0.0

# Flat name -> StringSpec dict, populated by main()
STRINGS: dict[str, StringSpec] = {}

def _alias(name: str, spec: StringSpec):
    """Expose c5e/c5p/c5t style module globals for quick inspection."""
    k = name.lower()
    globals()[f"{k}e"] = spec.eyelet
    globals()[f"{k}p"] = spec.pin
    globals()[f"{k}t"] = spec.tuner

# ==================================================================
# Main
# ==================================================================
def main():
    str_dir = string_direction()
    sin_rake = math.sin(math.radians(RAKE_ANGLE_DEG))

    # Seed: every string spec, in tuning order. Eyelet/pin/length/diameter
    # are filled in below by the iterative geometry solve.
    specs: list[StringSpec] = [
        StringSpec(note=n,
                   freq_hz=note_freq_hz(n),
                   tension_n=tension_for(i))
        for i, n in enumerate(NOTES)
    ]

    # ---- Eyelets along the soundboard between column foot (C8) and
    # soundbox top corner (S0). The center-to-center spacing of adjacent
    # strings (along SB_DIR) is chosen so the PERPENDICULAR air gap between
    # adjacent string ODs is exactly STRING_AIR_GAP_MM:
    #     perp_gap = SB_step * sin(rake_angle) - avg_diameter
    #     => SB_step = (STRING_AIR_GAP_MM + avg_d) / sin(rake)
    # Because diameter depends on vibrating length (which depends on eyelet
    # position) and vice versa, we iterate until diameters stabilize. The
    # BASS-side boundary gap (C8 → C5 eyelet, along the soundboard) is fixed
    # by BASS_BOUNDARY_MM; the treble-side gap floats and absorbs whatever
    # leftover length remains on the soundboard up to S0.
    BASS_BOUNDARY_MM = 16.0
    SOUNDBOX_TOP_CORNER = (2918.0, 2807.3)         # = S0
    total_inner = math.hypot(SOUNDBOX_TOP_CORNER[0] - INNER_COLUMN_FOOT[0],
                             SOUNDBOX_TOP_CORNER[1] - INNER_COLUMN_FOOT[1])
    sin_rake = math.sin(math.radians(RAKE_ANGLE_DEG))
    bass_boundary_inner = BASS_BOUNDARY_MM * INNER_PER_MM

    # Initial diameter guess: place eyelets equally spaced for the first pass.
    step_inner = total_inner / (NUM_STRINGS + 1)
    for i in range(NUM_STRINGS):
        specs[i].eyelet = add(INNER_COLUMN_FOOT,
                              mul(SB_DIR, (i + 1) * step_inner))
    for i, pin_orig in enumerate(SMALL_HOLES_INNER):
        v = sub(pin_orig, specs[i].eyelet)
        t = v[0]*str_dir[0] + v[1]*str_dir[1]
        specs[i].pin = add(specs[i].eyelet, mul(str_dir, t))
    for s in specs:
        s.length_mm = vibrating_length_mm(s.eyelet, s.pin)
        s.diameter_mm = diameter_for_freq_mm(s.length_mm, s.freq_hz,
                                             s.tension_n,
                                             STRING_DENSITY_KG_M3)

    # Iterate variable spacing until diameters converge.
    for _iter in range(15):
        sb_steps = [
            (STRING_AIR_GAP_MM + 0.5*(specs[i].diameter_mm
                                      + specs[i+1].diameter_mm))
            * INNER_PER_MM / sin_rake
            for i in range(NUM_STRINGS - 1)
        ]
        # Anchor C5 at BASS_BOUNDARY_MM from C8 along the soundboard.
        specs[0].eyelet = add(INNER_COLUMN_FOOT,
                              mul(SB_DIR, bass_boundary_inner))
        for i in range(1, NUM_STRINGS):
            specs[i].eyelet = add(specs[i-1].eyelet,
                                  mul(SB_DIR, sb_steps[i-1]))
        # Recompute pins (project original small-hole onto each string line)
        for i, pin_orig in enumerate(SMALL_HOLES_INNER):
            v = sub(pin_orig, specs[i].eyelet)
            t = v[0]*str_dir[0] + v[1]*str_dir[1]
            specs[i].pin = add(specs[i].eyelet, mul(str_dir, t))
        # Recompute lengths + diameters
        max_dd = 0.0
        for s in specs:
            prev_d = s.diameter_mm
            s.length_mm = vibrating_length_mm(s.eyelet, s.pin)
            s.diameter_mm = diameter_for_freq_mm(s.length_mm, s.freq_hz,
                                                 s.tension_n,
                                                 STRING_DENSITY_KG_M3)
            max_dd = max(max_dd, abs(s.diameter_mm - prev_d))
        if max_dd < 1e-5:
            break

    # ---- Eyelet HOLE position (for drawing the circle) sits BELOW the
    # string centerline by (eyelet_r - string_r), so the string OD touches
    # the upper inner rim of the hole when in tension. s.eyelet remains the
    # string-centerline position (where the string PATH starts).
    eyelet_r_inner = (EYELET_ID_MM/2) * INNER_PER_MM
    for s in specs:
        string_r_inner = (s.diameter_mm/2) * INNER_PER_MM
        off = eyelet_r_inner - string_r_inner
        s.eyelet_hole = (s.eyelet[0] - SB_DIR[0]*off,
                         s.eyelet[1] - SB_DIR[1]*off)

    # ---- Final pin center: shift from the string tip perpendicular to the
    # string by (pin_r + string_r) so the pin OD is tangent to the string OD.
    # IMPORTANT: recompute the tip from the FINAL (adjusted) eyelet position,
    # so the perpendicular offset is measured from the actual string line.
    pin_r_inner = (SMALL_CIRCLE_DIA_MM/2) * INNER_PER_MM
    str_up = (-str_dir[0], -str_dir[1])
    perpA = (-str_up[1],  str_up[0])
    perpB = ( str_up[1], -str_up[0])
    pin_perp = perpA if perpA[0] > perpB[0] else perpB
    for i, s in enumerate(specs):
        pin_orig = SMALL_HOLES_INNER[i]
        v = sub(pin_orig, s.eyelet)
        t = v[0]*str_dir[0] + v[1]*str_dir[1]
        tip = add(s.eyelet, mul(str_dir, t))
        string_r_inner = (s.diameter_mm/2) * INNER_PER_MM
        off = pin_r_inner + string_r_inner
        s.pin = (tip[0] + pin_perp[0]*off, tip[1] + pin_perp[1]*off)

    # ---- Tuner positions: pin + tuner_distance * rotated(str_up, +takeoff) ----
    # The pin-to-tuner ray sits at TUNER_TAKEOFF_DEG above the string trajectory,
    # rotated the same way the CW pin-wrap throws the string (toward the same
    # side as the pin offset, so the string exits the pin and continues outward).
    # The pin->tuner segment is at TUNER_TAKEOFF_DEG off the string trajectory
    # (so the bend at the pin is small, only ~15°). Rotate str_up by -15° in
    # inner coords; with the SVG Y-flip this lands the tuner just up-and-
    # slightly-right of the pin in the rendered view, on the side the CW
    # wrap around the pin pushes the string toward.
    str_up = (-str_dir[0], -str_dir[1])
    a = math.radians(TUNER_TAKEOFF_DEG)
    c, sin_a = math.cos(a), math.sin(a)
    takeoff_dir = (str_up[0]*c + str_up[1]*sin_a,
                   -str_up[0]*sin_a + str_up[1]*c)
    for i, s in enumerate(specs):
        d_inner = tuner_dist_mm(i) * INNER_PER_MM
        s.tuner = (s.pin[0] + takeoff_dir[0]*d_inner,
                   s.pin[1] + takeoff_dir[1]*d_inner)

    # ---- Publish to module globals: STRINGS["C5"], aliases c5e, c5p, c5t ----
    STRINGS.clear()
    for s in specs:
        STRINGS[s.note] = s
        _alias(s.note, s)

    print(f"string direction (inner) = ({str_dir[0]:+.3f}, {str_dir[1]:+.3f})")
    print(f"{'#':>3} {'Note':>4} {'Hz':>8} {'L(mm)':>8} {'T(N)':>6} {'d(mm)':>7}")
    for i, s in enumerate(specs):
        print(f"{i+1:3d} {s.note:>4} {s.freq_hz:8.2f} "
              f"{s.length_mm:8.1f} {s.tension_n:6.1f} {s.diameter_mm:7.3f}")
    print(f"pin count = {len(specs)}  ({specs[0].note}..{specs[-1].note})")

    # ==============================================================
    # Build the output SVG with svgwrite using named groups.
    # Frame path d-attributes are extracted from the existing SVG (they
    # come from the original EPS conversion and aren't algorithmic).
    # ==============================================================
    tuner_r_inner = (BIG_CIRCLE_DIA_MM/2) * INNER_PER_MM

    # Frame data (polylines + Schneider Bezier fits + short raw d-strings) is
    # imported from frame_data.py, which is generated offline by
    # tools/extract_frame_data.py. No runtime dependency on bezierfit.py.
    d_col_base   = frame_data.PATH66_D  # 1244,66.5 -> 1335.2,67.6992
    d_joint      = frame_data.PATH72_D  # closed thin quad at neck/soundbox junction
    d_sb_left    = frame_data.PATH74_D  # 2918,2807.3 -> 1339.4,71.3 -> 1337,67.7 -> 2541.2,67.7
    d_sb_right   = frame_data.PATH76_D  # 2541.2,67.7 -> 3343.4,2608.1 -> 2918,2807.3

    def strip_leading_M(d: str) -> str:
        return re.sub(r'^[Mm]\s*-?\d+\.?\d*\s*,?\s*-?\d+\.?\d*\s*', '', d).strip()

    def chain(d: str) -> str:
        """Strip leading M/m and prepend a continuation command. If the tail
        already starts with a command letter, leave it; otherwise prepend 'l'
        so the implicit coord pairs are treated as relative linetos."""
        t = strip_leading_M(d)
        return ('l ' + t) if (t and t[0] not in 'MmLlHhVvCcSsQqTtAaZz') else t

    # Closed COMBINED paths for each region (d_neck built below from Bezier
    # fit so it can use the parsed nodes).
    d_soundbox = f"{d_sb_left} L {strip_leading_M(d_sb_right)} Z"

    # ---- Parse the column polylines to find their control nodes -----------
    def parse_abs_pts(d):
        toks = re.findall(r'[MmLlHhVv]|-?\d+\.?\d*', d.strip())
        i = 0; cx = cy = 0.0; pts = []; last = None
        while i < len(toks):
            t = toks[i]
            if t.isalpha(): cmd = t; i += 1
            else: cmd = 'L' if last=='M' else ('l' if last=='m' else last)
            last = cmd
            if cmd in ('M','L'):
                cx, cy = float(toks[i]), float(toks[i+1]); i += 2; pts.append((cx, cy))
            elif cmd in ('m','l'):
                dx, dy = float(toks[i]), float(toks[i+1]); i += 2
                if cmd=='m' and not pts: cx,cy = dx,dy
                else: cx,cy = cx+dx, cy+dy
                pts.append((cx, cy))
            elif cmd in ('H','V','h','v'):
                v = float(toks[i]); i += 1
                if cmd=='H': cx = v
                elif cmd=='h': cx += v
                elif cmd=='V': cy = v
                elif cmd=='v': cy += v
                pts.append((cx, cy))
            else: i += 1
        return pts
    p68_pts = frame_data.P68_PTS
    p70_pts = frame_data.P70_PTS
    p20_pts = frame_data.P20_PTS

    def extreme_x_inflection(pts):
        interior = pts[1:-1] if len(pts) > 2 else pts
        return min(interior, key=lambda p: p[0])
    def extreme_x_max(pts):
        interior = pts[1:-1] if len(pts) > 2 else pts
        return max(interior, key=lambda p: p[0])
    def find_sharp_corner(pts, threshold_deg=30):
        worst = None; worst_ang = threshold_deg
        for j in range(1, len(pts)-1):
            v1 = (pts[j][0]-pts[j-1][0], pts[j][1]-pts[j-1][1])
            v2 = (pts[j+1][0]-pts[j][0], pts[j+1][1]-pts[j][1])
            m1 = math.hypot(*v1); m2 = math.hypot(*v2)
            if m1 < 1e-3 or m2 < 1e-3: continue
            dot = max(-1, min(1, (v1[0]*v2[0] + v1[1]*v2[1]) / (m1*m2)))
            ang = math.degrees(math.acos(dot))
            if ang > worst_ang:
                worst_ang = ang; worst = pts[j]
        return worst

    p68_sharp = find_sharp_corner(p68_pts)
    p68_left  = extreme_x_inflection(p68_pts)
    p68_waist = extreme_x_max(p68_pts)
    p70_left  = extreme_x_inflection(p70_pts)
    i_waist_idx = max(range(len(p68_pts)), key=lambda j: p68_pts[j][0])
    p68_lower = min(p68_pts[i_waist_idx+1:-1], key=lambda p: p[0])

    # Neck control nodes (path20 outer arch). Walking the polyline forward:
    # start (right joint corner) -> rightmost -> topmost -> leftmost ->
    # sharp 90° corner -> end (left joint corner).
    xs20 = [p[0] for p in p20_pts]; ys20 = [p[1] for p in p20_pts]
    n20_max_x = p20_pts[xs20.index(max(xs20))]
    n20_max_y = p20_pts[ys20.index(max(ys20))]
    n20_min_x = p20_pts[xs20.index(min(xs20))]
    n20_sharp = find_sharp_corner(p20_pts)

    # ---- Curve-fit the column polylines into Bezier segments ---------------
    # The original SVG has path68 and path70 as polylines of hundreds of tiny
    # straight segments. Replace them with cubic Beziers fitted (least-squares)
    # to the polyline points between each pair of consecutive column nodes.
    def fit_bezier(pts, p0, p3):
        if len(pts) < 3:
            return (p0[0]+(p3[0]-p0[0])/3, p0[1]+(p3[1]-p0[1])/3), \
                   (p0[0]+2*(p3[0]-p0[0])/3, p0[1]+2*(p3[1]-p0[1])/3)
        cumlen = [0.0]
        for k in range(1, len(pts)):
            cumlen.append(cumlen[-1] + math.hypot(
                pts[k][0]-pts[k-1][0], pts[k][1]-pts[k-1][1]))
        total = cumlen[-1] or 1.0
        ts = [c/total for c in cumlen]
        s11=s12=s22=bx1=bx2=by1=by2=0.0
        for t, p in zip(ts, pts):
            w1 = 3*(1-t)**2 * t
            w2 = 3*(1-t)   * t**2
            kx = (1-t)**3 * p0[0] + t**3 * p3[0]
            ky = (1-t)**3 * p0[1] + t**3 * p3[1]
            rx = p[0]-kx; ry = p[1]-ky
            s11 += w1*w1; s12 += w1*w2; s22 += w2*w2
            bx1 += w1*rx; bx2 += w2*rx
            by1 += w1*ry; by2 += w2*ry
        det = s11*s22 - s12*s12
        if abs(det) < 1e-9:
            return p0, p3
        cx1 = ( s22*bx1 - s12*bx2)/det
        cx2 = (-s12*bx1 + s11*bx2)/det
        cy1 = ( s22*by1 - s12*by2)/det
        cy2 = (-s12*by1 + s11*by2)/det
        return (cx1, cy1), (cx2, cy2)

    def find_idx(target, pts, tol=0.5):
        for i, p in enumerate(pts):
            if abs(p[0]-target[0]) < tol and abs(p[1]-target[1]) < tol:
                return i
        return None

    # Stash the fit handles so we can label/visualize them later.
    # path68 segment node order, top -> base-left:
    p68_seq = [(859.996, 3506.9), n20_sharp, p68_left, p68_waist, p68_lower,
               (1244.0, 66.5)]
    p70_seq = [(1787.0, 847.102), p70_left, (859.996, 3506.9)]

    def beziers_along(seq, all_pts):
        idxs = [find_idx(n, all_pts) for n in seq]
        out = []
        for k in range(len(seq)-1):
            i0, i1 = idxs[k], idxs[k+1]
            slice_pts = all_pts[i0:i1+1]
            c1, c2 = fit_bezier(slice_pts, seq[k], seq[k+1])
            out.append((c1, c2, seq[k+1]))
        return out

    # Schneider Bezier fits are precomputed offline (tools/extract_frame_data.py)
    # and imported as constants. We copy into local lists so post-fit handle
    # tweaks below (sharp corners, vertical C0, merged C3->next, etc.) don't
    # mutate the frame_data globals.
    p68_seq      = list(frame_data.P68_SEQ)
    p68_beziers  = list(frame_data.P68_BEZ)
    p70_seq      = list(frame_data.P70_SEQ)
    p70_beziers  = list(frame_data.P70_BEZ)

    # User adjustment: move C0 (top of column, where path68/path70 meet) and
    # C8 (inner-curve leftmost bulge) LEFT by 6mm. Move their adjacent Bezier
    # control handles by the same amount so curve shape at those nodes is
    # preserved.
    def shift_seq_node(seq, beziers, target, dx, dy, tol=20):
        """Find the seq entry closest to `target` and shift it + adjacent
        Bezier handles by (dx, dy). Mutates `seq` and `beziers` in place."""
        idx = min(range(len(seq)),
                  key=lambda i: (seq[i][0]-target[0])**2 + (seq[i][1]-target[1])**2)
        if math.hypot(seq[idx][0]-target[0], seq[idx][1]-target[1]) > tol:
            return  # no nearby node, skip
        seq[idx] = (seq[idx][0]+dx, seq[idx][1]+dy)
        # Bezier ending AT this node: index = idx - 1 (if exists)
        if idx > 0:
            c1, c2, p3 = beziers[idx-1]
            beziers[idx-1] = (c1, (c2[0]+dx, c2[1]+dy),
                              (p3[0]+dx, p3[1]+dy))
        # Bezier starting FROM this node: index = idx (if exists)
        if idx < len(beziers):
            c1, c2, p3 = beziers[idx]
            beziers[idx] = ((c1[0]+dx, c1[1]+dy), c2, p3)

    shift_mm = -6.0
    dx_shift = shift_mm * INNER_PER_MM
    # Only C8 (inner curve bulge) gets the manual -6mm shift; C0 (column top)
    # is REPOSITIONED to where the C8->C0 arc trajectory intersects the neck
    # outline (path20), so the column top tucks into the neck contour.
    shift_seq_node(p70_seq, p70_beziers, p70_left, dx_shift, 0)

    # Compute intersection of the (C8->C0 arc tangent at C0) with path20.
    last_p70 = p70_beziers[-1]               # (c1, c2, p3) ending at OLD C0
    c2_at_c0 = last_p70[1]
    old_c0   = last_p70[2]
    tangent  = unit(sub(old_c0, c2_at_c0))

    def ray_polyline_intersect(O, d, pts):
        best_t = None; best_pt = None; best_i = -1
        for i in range(len(pts) - 1):
            A, B = pts[i], pts[i+1]
            sx, sy = B[0]-A[0], B[1]-A[1]
            det = -d[0]*sy + d[1]*sx
            if abs(det) < 1e-9: continue
            t = (-(A[0]-O[0])*sy + (A[1]-O[1])*sx) / det
            s = (d[0]*(A[1]-O[1]) - d[1]*(A[0]-O[0])) / det
            if t > 1e-6 and 0 <= s <= 1:
                if best_t is None or t < best_t:
                    best_t = t
                    best_pt = (O[0] + t*d[0], O[1] + t*d[1])
                    best_i = i
        return best_pt, best_i

    # NEW C0 = the point on path20 directly above C8 (same X, highest Y
    # near that X), then slide 6mm DOWN the curve toward the RIGHT (toward
    # smaller path20 indices = back toward N2/N1/N0 = right joint).
    c8_x = p70_left[0] + dx_shift
    near_x = [(i, p) for i, p in enumerate(p20_pts) if abs(p[0] - c8_x) < 60]
    if near_x:
        c0_neck_idx, new_c0 = max(near_x, key=lambda ip: ip[1][1])
    else:
        new_c0, c0_neck_idx = ray_polyline_intersect(old_c0, tangent, p20_pts)
        if new_c0 is None: new_c0 = old_c0; c0_neck_idx = 0

    SLIDE_C0_MM = 12.0
    slide_inner = SLIDE_C0_MM * INNER_PER_MM
    walked = 0.0
    j = c0_neck_idx
    while j > 0 and walked < slide_inner:
        seg = math.hypot(p20_pts[j][0]-p20_pts[j-1][0],
                         p20_pts[j][1]-p20_pts[j-1][1])
        walked += seg
        j -= 1
    c0_neck_idx = j
    new_c0 = p20_pts[c0_neck_idx]

    # Extend the last p70 Bezier so its endpoint is the new C0 (preserve
    # the relative position of c2 so the tangent direction is preserved).
    extra_dx = new_c0[0] - old_c0[0]
    extra_dy = new_c0[1] - old_c0[1]
    shift_seq_node(p70_seq, p70_beziers, old_c0, extra_dx, extra_dy)

    # N4 = sharp corner on path20 at index 546 (same point as path68 sharp).
    N4_NECK_IDX = 546

    # Neck Schneider fit precomputed in frame_data.py.
    p20_beziers = list(frame_data.P20_BEZ)
    p20_seq     = list(frame_data.P20_SEQ)

    # Force a SHARP corner at N4. Schneider's smooth fit leaves the in/out
    # tangents at N4 nearly parallel (45°ish on both sides), producing a
    # rounded transition with a visible ripple. Override cp2 of the bezier
    # ending at N4 and cp1 of the bezier starting at N4 so the tangents
    # align with the actual polyline directions (N4 - prev_pt) and
    # (next_pt - N4) — preserving the original handle magnitudes.
    n4_bez_idx = min(range(len(p20_beziers)),
                     key=lambda i: (p20_beziers[i][2][0]-n20_sharp[0])**2
                                 + (p20_beziers[i][2][1]-n20_sharp[1])**2)
    incoming_dir = unit(sub(n20_sharp, p20_pts[N4_NECK_IDX-1]))
    outgoing_dir = unit(sub(p20_pts[N4_NECK_IDX+1], n20_sharp))
    # bezier ENDING at N4: replace cp2 so end-tangent (end - cp2) = incoming_dir
    c1_in, c2_in, p3_in = p20_beziers[n4_bez_idx]
    mag_in = math.hypot(c2_in[0]-p3_in[0], c2_in[1]-p3_in[1])
    new_c2_in = (p3_in[0] - mag_in * incoming_dir[0],
                 p3_in[1] - mag_in * incoming_dir[1])
    p20_beziers[n4_bez_idx] = (c1_in, new_c2_in, p3_in)
    # bezier STARTING at N4: replace cp1 so start-tangent (cp1 - start) = outgoing_dir
    if n4_bez_idx + 1 < len(p20_beziers):
        c1_out, c2_out, p3_out = p20_beziers[n4_bez_idx + 1]
        start_out = n20_sharp
        mag_out = math.hypot(c1_out[0]-start_out[0], c1_out[1]-start_out[1])
        new_c1_out = (start_out[0] + mag_out * outgoing_dir[0],
                      start_out[1] + mag_out * outgoing_dir[1])
        p20_beziers[n4_bez_idx + 1] = (new_c1_out, c2_out, p3_out)

    def bez_str(b):
        c1, c2, p = b
        return (f"C {c1[0]:.2f} {c1[1]:.2f} {c2[0]:.2f} {c2[1]:.2f} "
                f"{p[0]:.2f} {p[1]:.2f}")
    # Column path: trace the EXACT neck beziers (so the shared boundary
    # matches pixel-for-pixel), then path68 beziers, base, path70 beziers.
    # Split the neck bezier that contains new_c0 at the closest-t (de Casteljau)
    # to introduce an exact bezier endpoint there.
    def bez_eval(P0, P1, P2, P3, t):
        u = 1 - t
        return (u*u*u*P0[0] + 3*u*u*t*P1[0] + 3*u*t*t*P2[0] + t*t*t*P3[0],
                u*u*u*P0[1] + 3*u*u*t*P1[1] + 3*u*t*t*P2[1] + t*t*t*P3[1])
    def bez_split(P0, P1, P2, P3, t):
        # de Casteljau split at t; returns (first_bez, second_bez) each as
        # (c1, c2, p3) with implicit start = P0 / split_pt respectively.
        Q0 = (P0[0]+t*(P1[0]-P0[0]), P0[1]+t*(P1[1]-P0[1]))
        Q1 = (P1[0]+t*(P2[0]-P1[0]), P1[1]+t*(P2[1]-P1[1]))
        Q2 = (P2[0]+t*(P3[0]-P2[0]), P2[1]+t*(P3[1]-P2[1]))
        R0 = (Q0[0]+t*(Q1[0]-Q0[0]), Q0[1]+t*(Q1[1]-Q0[1]))
        R1 = (Q1[0]+t*(Q2[0]-Q1[0]), Q1[1]+t*(Q2[1]-Q1[1]))
        S  = (R0[0]+t*(R1[0]-R0[0]), R0[1]+t*(R1[1]-R0[1]))
        return (Q0, R0, S), (R1, Q2, P3), S
    # find which p20_beziers segment contains the closest point to new_c0
    best = None
    for bi, (c1, c2, p3) in enumerate(p20_beziers):
        p0 = p20_seq[bi]
        for ti in range(1, 200):
            t = ti / 200.0
            x, y = bez_eval(p0, c1, c2, p3, t)
            d2 = (x-new_c0[0])**2 + (y-new_c0[1])**2
            if best is None or d2 < best[0]:
                best = (d2, bi, t, p0, c1, c2, p3)
    _, split_bi, split_t, P0, P1, P2, P3 = best
    _, second_half, split_pt = bez_split(P0, P1, P2, P3, split_t)
    # Snap new_c0 to the exact split point so column & neck share the boundary.
    new_c0 = split_pt
    # Find bezier index ending at n20_sharp.
    n4_bi = min(range(len(p20_beziers)),
                key=lambda i: (p20_beziers[i][2][0]-n20_sharp[0])**2
                            + (p20_beziers[i][2][1]-n20_sharp[1])**2)
    # Re-extend the last p70 Bezier so its endpoint = updated new_c0, AND
    # force the column inner curve to APPROACH C0 vertically by placing cp2
    # directly below the endpoint (same X, lower Y). The original handle
    # magnitude is preserved so the curve keeps roughly the same scale of
    # curvature into C0; only the direction is overridden.
    p70_last = p70_beziers[-1]
    _old_cp2 = p70_last[1]
    _old_end = p70_last[2]
    cp2_mag = math.hypot(_old_cp2[0]-_old_end[0], _old_cp2[1]-_old_end[1])
    new_cp2 = (new_c0[0], new_c0[1] - cp2_mag)
    p70_beziers[-1] = (p70_last[0], new_cp2, new_c0)
    p70_seq[-1] = new_c0

    # C3 -> next bezier endpoint: collapse the C3->C4 and C4->next pair into
    # a single sweeping bezier (C4 removed as a node). C3's exit handle is
    # extended to roughly the magnitude C4's old exit handle had, so the
    # curve sweeps smoothly from the sharp corner down to where the column
    # back starts curving right toward the waist — without the localized
    # bulge that the forced X-minimum at C4 produced.
    first_p68  = p68_beziers[1]
    second_p68 = p68_beziers[2]
    _c1_old, _c2_old, _c4_old = first_p68
    c1_next, c2_next, p3_next = second_p68
    # C3 exit handle: align with the VISUAL trajectory of the bezier entering
    # N4/C3 (i.e., the chord from that bezier's cp1 to its endpoint), not with
    # `incoming_dir` (which is the very-last-point tangent — only valid for the
    # tiny mag_in distance). This makes the column flow smoothly past C3
    # without a visible kink.  Keep the length short so the original Schneider-
    # shaped wide column sweep below dominates and the outer column path
    # stays essentially unchanged.
    in_bez = p20_beziers[n4_bez_idx]
    in_cp1, _, in_end = in_bez
    chord_v = (in_end[0] - in_cp1[0], in_end[1] - in_cp1[1])
    chord_mag = math.hypot(*chord_v)
    c3_exit_dir = (chord_v[0]/chord_mag, chord_v[1]/chord_mag)
    C3_EXIT_HANDLE_LEN = 1065.0  # inner units; ~70% of the previous 1522 long-sweep length
    mag_c3_out_extended = C3_EXIT_HANDLE_LEN
    extended_cp1_c3 = (n20_sharp[0] + mag_c3_out_extended * c3_exit_dir[0],
                       n20_sharp[1] + mag_c3_out_extended * c3_exit_dir[1])
    merged_c3_to_next = (extended_cp1_c3, c2_next, p3_next)

    d_column = " ".join([
        f"M {new_c0[0]:.2f} {new_c0[1]:.2f}",
        bez_str(second_half),
        *[bez_str(b) for b in p20_beziers[split_bi+1 : n4_bi+1]],
        bez_str(merged_c3_to_next),
        *[bez_str(b) for b in p68_beziers[3:]],
        "L 1244 67.6992 L 1335.2 67.6992",
        "L 1337 67.6992 L 1339.4 71.3008 L 1787 847.102",
        *[bez_str(b) for b in p70_beziers],
        "Z",
    ])
    d_neck = " ".join([
        f"M {p20_seq[0][0]:.2f} {p20_seq[0][1]:.2f}",
        *[bez_str(b) for b in p20_beziers],
        "Z",
    ])
    d_joint_z  = d_joint    # path72 is already closed

    # ===== Compute NECK SPACER outline =====
    # Slab of neck material between the joint (right edge of path20 = the
    # implicit N5->N0 closing line) and the vertical above the treble-most
    # (G6) eyelet. Top and bottom edges use the EXACT neck beziers (de
    # Casteljau-split at the target X), so it tucks into the neck the same
    # way the column tucks into the bass end.
    target_x = specs[-1].eyelet[0]
    crossings = []
    for bi, (c1, c2, p3) in enumerate(p20_beziers):
        p0 = p20_seq[bi]
        prev_x = p0[0]; prev_t = 0.0
        for ti in range(1, 401):
            t = ti / 400.0
            u = 1 - t
            x = u*u*u*p0[0] + 3*u*u*t*c1[0] + 3*u*t*t*c2[0] + t*t*t*p3[0]
            if (prev_x - target_x) * (x - target_x) <= 0 and prev_x != x:
                f = (target_x - prev_x) / (x - prev_x)
                t_cross = prev_t + f * (t - prev_t)
                y_cross = bez_eval(p0, c1, c2, p3, t_cross)[1]
                crossings.append((bi, t_cross, target_x, y_cross))
            prev_x = x; prev_t = t

    d_spacer = None
    if len(crossings) >= 2:
        up = max(crossings, key=lambda c: c[3])
        lo = min(crossings, key=lambda c: c[3])
        up_bi, up_t, _, _ = up
        lo_bi, lo_t, _, _ = lo
        P0u = p20_seq[up_bi]
        c1u, c2u, p3u = p20_beziers[up_bi]
        first_up, _, split_up = bez_split(P0u, c1u, c2u, p3u, up_t)
        P0l = p20_seq[lo_bi]
        c1l, c2l, p3l = p20_beziers[lo_bi]
        _, second_lo, split_lo = bez_split(P0l, c1l, c2l, p3l, lo_t)
        def rev_bez(P0, P1, P2, P3):
            return (P3, P2, P1, P0)
        _, rev_second_lo_c1, rev_second_lo_c2, rev_second_lo_p3 = \
            rev_bez(split_lo, second_lo[0], second_lo[1], second_lo[2])
        _, rev_first_up_c1, rev_first_up_c2, rev_first_up_p3 = \
            rev_bez(P0u, first_up[0], first_up[1], first_up[2])
        N0_pt = p20_seq[0]
        N5_pt = p20_seq[-1]
        d_spacer = " ".join([
            f"M {N0_pt[0]:.2f} {N0_pt[1]:.2f}",
            f"L {N5_pt[0]:.2f} {N5_pt[1]:.2f}",
            bez_str((rev_second_lo_c1, rev_second_lo_c2, rev_second_lo_p3)),
            f"L {split_up[0]:.2f} {split_up[1]:.2f}",
            bez_str((rev_first_up_c1, rev_first_up_c2, rev_first_up_p3)),
            "Z",
        ])

    # ===== Compute string paths =====
    string_paths = []
    for s in specs:
        sr = (s.diameter_mm/2) * INNER_PER_MM
        v = sub(s.pin, s.eyelet)
        t_entry = v[0]*str_dir[0] + v[1]*str_dir[1]
        pin_entry = add(s.eyelet, mul(str_dir, t_entry))
        perp_t = (-takeoff_dir[1], takeoff_dir[0])
        ent_off = sub(pin_entry, s.pin)
        sign = 1 if (ent_off[0]*perp_t[0] + ent_off[1]*perp_t[1]) > 0 else -1
        pin_exit_outer = (s.pin[0] + sign*perp_t[0]*(pin_r_inner + sr),
                          s.pin[1] + sign*perp_t[1]*(pin_r_inner + sr))
        tuner_entry = (s.tuner[0] + sign*perp_t[0]*(tuner_r_inner + sr),
                       s.tuner[1] + sign*perp_t[1]*(tuner_r_inner + sr))
        tuner_end = (2*s.tuner[0] - tuner_entry[0],
                     2*s.tuner[1] - tuner_entry[1])
        r_pin_c = pin_r_inner + sr
        r_tnr_c = tuner_r_inner + sr
        d_s = (f"M {s.eyelet[0]:.2f} {s.eyelet[1]:.2f}"
               f" L {pin_entry[0]:.2f} {pin_entry[1]:.2f}"
               f" A {r_pin_c:.2f} {r_pin_c:.2f} 0 0 0 "
               f"{pin_exit_outer[0]:.2f} {pin_exit_outer[1]:.2f}"
               f" L {tuner_entry[0]:.2f} {tuner_entry[1]:.2f}"
               f" A {r_tnr_c:.2f} {r_tnr_c:.2f} 0 0 0 "
               f"{tuner_end[0]:.2f} {tuner_end[1]:.2f}")
        string_paths.append((s, d_s))

    # ===== Node lists for labels =====
    SOUNDBOX_NODES = [
        (2918.0,  2807.3),   # S0 top, meets neck/joint
        (1338.0,    69.5),   # S1 bottom-left (avg of two near-coincident vertices)
        (2541.2,    67.6992),# S2 bottom-right at base
        (3343.4,  2608.1),   # S3 top-right
    ]
    COLUMN_NODES = [
        new_c0,                                  # C0  on neck contour
        n20_max_y,                               # C1 = neck N2 (topmost arch)
        n20_min_x,                               # C2 = neck N3 (leftmost)
        n20_sharp,                               # C3 = neck N4 (sharp corner, identical pt)
        p68_waist,                               # C4  outer waist (max-X)
        p68_lower,                               # C5  outer LOWER bulge
        (1244.0,    66.5),                       # C6  base bottom-left
        (1335.2,    67.6992),                    # C7  base bottom-right
        (1787.0,    847.102),                    # C8  foot at soundbox diagonal
        (p70_left[0] + dx_shift, p70_left[1]),   # C9  inner curve bulge (-6mm)
    ]
    NECK_NODES = [
        p20_pts[0],   # N0 start (right corner of joint)
        n20_max_x,    # N1 rightmost edge of neck
        n20_max_y,    # N2 topmost of arch
        n20_min_x,    # N3 leftmost (back of neck)
        n20_sharp,    # N4 sharp 90° corner where neck meets column back
        p20_pts[-1],  # N5 end (left corner of joint)
    ]

    LABEL_DIST = 75
    def label_positions(nodes, overrides=None):
        overrides = overrides or {}
        cx_c = sum(p[0] for p in nodes) / len(nodes)
        cy_c = sum(p[1] for p in nodes) / len(nodes)
        n = len(nodes); out = []
        for i, v in enumerate(nodes):
            if i in overrides:
                ox, oy = overrides[i]
                out.append((v[0] + ox, v[1] + oy)); continue
            prev_v = nodes[(i - 1) % n]
            next_v = nodes[(i + 1) % n]
            bis = add(unit(sub(prev_v, v)), unit(sub(next_v, v)))
            if math.hypot(*bis) < 1e-6:
                bis = unit((cx_c - v[0], cy_c - v[1]))
            else:
                bis = unit(bis)
                to_centroid = (cx_c - v[0], cy_c - v[1])
                if bis[0]*to_centroid[0] + bis[1]*to_centroid[1] < 0:
                    bis = (-bis[0], -bis[1])
            out.append((v[0] + bis[0]*LABEL_DIST, v[1] + bis[1]*LABEL_DIST))
        return out

    # ==================================================================
    # SVG EMIT — hand-formatted, one logical element per line, no nested
    # transforms (the inner-coord matrix(2,0,0,-2,0,930.78)·scale(0.1) is
    # baked into each coordinate so the file is directly readable).
    # ==================================================================
    def ux(v): return 0.2 * v                # inner X -> user X
    def uy(v): return 930.78 - 0.2 * v       # inner Y -> user Y (with flip)
    SW_USER = 1.44                            # stroke-width: inner 7.2 * 0.2
    THIN_SW = 0.6                             # eyelet/pin/tuner outline
    FONT_SIZE = 16                            # inner 80 * 0.2
    _NUM_RE = re.compile(r'[MmLlHhVvCcSsQqTtAaZz]|-?\d*\.?\d+(?:[eE][+-]?\d+)?')

    def tx_d(d):
        """Transform an SVG path d-string from inner to user coordinates.
        Handles M/L/H/V/C/A in both absolute and relative forms. Arc sweep
        flag is flipped (negative-determinant transform). Per SVG spec, the
        VERY FIRST coordinate pair of the path is always absolute even when
        the moveto command is lowercase (subsequent implicit pairs then
        follow the original case)."""
        toks = _NUM_RE.findall(d)
        out = []; i = 0; cur = ''; x = y = 0.0
        first_pair_pending = True
        fmt = lambda v: f'{v:.2f}'
        while i < len(toks):
            t = toks[i]
            if t in 'MmLlHhVvCcSsQqTtAaZz':
                cur = t; out.append(t); i += 1; continue
            is_abs = cur.isupper() or first_pair_pending
            if cur in 'Mm':
                cx, cy = float(t), float(toks[i+1])
                if is_abs: x, y = cx, cy; out += [fmt(ux(cx)), fmt(uy(cy))]
                else:      x += cx; y += cy; out += [fmt(0.2*cx), fmt(-0.2*cy)]
                i += 2; cur = 'L' if cur.isupper() else 'l'
                first_pair_pending = False
            elif cur in 'Ll':
                cx, cy = float(t), float(toks[i+1])
                if is_abs: x, y = cx, cy; out += [fmt(ux(cx)), fmt(uy(cy))]
                else:      x += cx; y += cy; out += [fmt(0.2*cx), fmt(-0.2*cy)]
                i += 2
            elif cur in 'Hh':
                cx = float(t)
                if is_abs: x = cx; out.append(fmt(ux(cx)))
                else:      x += cx; out.append(fmt(0.2*cx))
                i += 1
            elif cur in 'Vv':
                cy = float(t)
                if is_abs: y = cy; out.append(fmt(uy(cy)))
                else:      y += cy; out.append(fmt(-0.2*cy))
                i += 1
            elif cur in 'Cc':
                vals = [float(toks[i+k]) for k in range(6)]
                if is_abs:
                    x, y = vals[4], vals[5]
                    for k in (0, 2, 4): out += [fmt(ux(vals[k])), fmt(uy(vals[k+1]))]
                else:
                    x += vals[4]; y += vals[5]
                    for k in (0, 2, 4): out += [fmt(0.2*vals[k]), fmt(-0.2*vals[k+1])]
                i += 6
            elif cur in 'Aa':
                rx, ry = float(toks[i]), float(toks[i+1])
                rot, large, sweep = toks[i+2], toks[i+3], toks[i+4]
                ex, ey = float(toks[i+5]), float(toks[i+6])
                out += [fmt(0.2*rx), fmt(0.2*ry), rot, large,
                        '1' if sweep == '0' else '0']
                if is_abs: x, y = ex, ey; out += [fmt(ux(ex)), fmt(uy(ey))]
                else:      x += ex; y += ey; out += [fmt(0.2*ex), fmt(-0.2*ey)]
                i += 7
            else:
                i += 1
        return ' '.join(out)

    out_lines = ['<?xml version="1.0" encoding="utf-8"?>',
                 '<svg viewBox="0 0 708.88 930.78" xmlns="http://www.w3.org/2000/svg">']

    def grp(id_, **attrs):
        attr_str = ' '.join(f'{k.replace("_","-")}="{v}"' for k, v in attrs.items())
        out_lines.append(f'  <g id="{id_}" {attr_str}>')
    def close(): out_lines.append('  </g>')
    def path(id_, d, **attrs):
        attr_str = ' '.join(f'{k.replace("_","-")}="{v}"' for k, v in attrs.items())
        sep = ' ' if attrs else ''
        out_lines.append(f'    <path id="{id_}"{sep}{attr_str} d="{tx_d(d)}"/>')
    def circle(id_, cx_, cy_, r_):
        out_lines.append(
            f'    <circle id="{id_}" cx="{ux(cx_):.2f}" cy="{uy(cy_):.2f}" r="{0.2*r_:.2f}"/>')
    def text(content, lx, ly):
        out_lines.append(
            f'    <text x="{ux(lx):.2f}" y="{uy(ly):.2f}">{content}</text>')

    # ----- NECK BACK (right cheek, drawn first = behind everything) -----
    NECK_STYLE = dict(fill="#cc0000", fill_opacity="0.25", stroke="#cc0000",
                      stroke_width=str(SW_USER), stroke_linecap="round",
                      stroke_linejoin="round")
    grp("neck_back", **NECK_STYLE)
    path("neck_back_outline", d_neck)
    close()

    # ----- NECK SPACER -----
    if d_spacer:
        grp("neck_spacer", fill="#aa6600", fill_opacity="0.45", stroke="#aa6600",
            stroke_width=str(SW_USER), stroke_linecap="round", stroke_linejoin="round")
        path("neck_spacer_outline", d_spacer)
        close()

    # ----- COLUMN -----
    grp("column", fill="#00aa00", fill_opacity="0.25", stroke="#00aa00",
        stroke_width=str(SW_USER), stroke_linecap="round", stroke_linejoin="round")
    path("column_outline", d_column)
    close()

    # ----- SOUNDBOX -----
    grp("soundbox", fill="#0080ff", fill_opacity="0.25", stroke="#0080ff",
        stroke_width=str(SW_USER), stroke_linecap="round", stroke_linejoin="round")
    path("soundbox_outline", d_soundbox)
    close()

    # ----- JOINT -----
    grp("joint", fill="#8b4513", fill_opacity="0.6", stroke="#8b4513",
        stroke_width=str(SW_USER), stroke_linecap="round", stroke_linejoin="round")
    path("joint_outline", d_joint_z)
    close()

    # ----- STRINGS -----
    grp("strings", fill="none", stroke_linecap="round", stroke_linejoin="round")
    for s, d_s in string_paths:
        sw = s.diameter_mm * INNER_PER_MM * 0.2
        path(f"string_{s.note}", d_s,
             stroke=string_color(s.note), stroke_width=f"{sw:.2f}")
    close()

    # ----- EYELETS / PINS / TUNERS -----
    grp("eyelets", fill="none", stroke="#444444", stroke_width=str(THIN_SW))
    for s in specs: circle(f"eyelet_{s.note}", s.eyelet_hole[0], s.eyelet_hole[1], eyelet_r_inner)
    close()

    # Pins/tuners alternate between the two neck cheeks: ODD-numbered
    # (strings 1, 3, 5, …) go on the LEFT (front) cheek and are drawn AFTER
    # neck_front so they sit on top. EVEN-numbered (strings 2, 4, 6, …) go on
    # the RIGHT (back) cheek and are drawn BEFORE neck_front, which leaves
    # them slightly muted under the translucent front cheek — matching what
    # a side-on viewer would actually see.
    odd_specs  = [s for i, s in enumerate(specs) if (i + 1) % 2 == 1]
    even_specs = [s for i, s in enumerate(specs) if (i + 1) % 2 == 0]

    # Even (right cheek): cool colors. Odd (left cheek): warm colors.
    grp("pins_right", fill="#0088ff", fill_opacity="0.5", stroke="#0088ff",
        stroke_width=str(THIN_SW))
    for s in even_specs: circle(f"pin_{s.note}", s.pin[0], s.pin[1], pin_r_inner)
    close()

    grp("tuners_right", fill="#229922", fill_opacity="0.4", stroke="#229922",
        stroke_width=str(THIN_SW))
    for s in even_specs: circle(f"tuner_{s.note}", s.tuner[0], s.tuner[1], tuner_r_inner)
    close()

    # ----- NECK FRONT (left cheek, drawn after middle pieces = on top) -----
    grp("neck_front", **NECK_STYLE)
    path("neck_front_outline", d_neck)
    close()

    grp("pins_left", fill="#ff8800", fill_opacity="0.5", stroke="#ff8800",
        stroke_width=str(THIN_SW))
    for s in odd_specs: circle(f"pin_{s.note}", s.pin[0], s.pin[1], pin_r_inner)
    close()

    grp("tuners_left", fill="#9933cc", fill_opacity="0.4", stroke="#9933cc",
        stroke_width=str(THIN_SW))
    for s in odd_specs: circle(f"tuner_{s.note}", s.tuner[0], s.tuner[1], tuner_r_inner)
    close()

    # ----- LABELS (drawn last so they're always on top) -----
    LABEL_STYLE = dict(font_family="sans-serif", font_size=str(FONT_SIZE),
                       font_weight="bold", text_anchor="middle",
                       dominant_baseline="central")
    for nodes, gid, color, overrides in [
        (SOUNDBOX_NODES, "soundbox_labels", "#0080ff", None),
        (COLUMN_NODES,   "column_labels",   "#00aa00", {6: (-180, 60)}),
        (NECK_NODES,     "neck_labels",     "#cc0000", None),
    ]:
        positions = label_positions(nodes, overrides)
        grp(gid, fill=color, **LABEL_STYLE)
        for i, (lx, ly) in enumerate(positions):
            text(str(i), lx, ly)
        close()

    # ----- DEBUG: C3 / N4 control handles at the shared sharp corner -----
    # C3 (column-outline view of the shared point):
    #   IN  = cp2 of the neck bezier ending at C3 (sharp-corner-fix output)
    #         — points UP from C3, magnitude = mag_in (preserved Schneider value)
    #   OUT = cp1 of the merged C3->next column bezier
    #         — points DOWN along incoming_dir, magnitude = C3_EXIT_HANDLE_FACTOR
    #           x (original Schneider next-segment cp1 length)
    # N4 (neck-outline view of the same point):
    #   IN  = SAME handle as C3 IN (literally same cp2 of the same bezier)
    #   OUT = cp1 of the neck bezier starting at N4 (sharp-corner-fix output)
    #         — points RIGHT along outgoing_dir toward N5
    c3_in   = p20_beziers[n4_bez_idx][1]
    c3_out  = extended_cp1_c3
    n4_out  = p20_beziers[n4_bez_idx + 1][0]   # cp1 of bez starting at N4
    C3_COLOR = "#ff00ff"   # magenta — column-outline handles
    N4_COLOR = "#ff8800"   # orange  — neck-outline handles (IN coincident w/ C3)

    out_lines.append(f'  <g id="c3_handles" stroke="{C3_COLOR}" stroke-width="0.8" fill="{C3_COLOR}">')
    out_lines.append(
        f'    <line id="c3_handle_in_line" x1="{ux(n20_sharp[0]):.2f}" y1="{uy(n20_sharp[1]):.2f}" '
        f'x2="{ux(c3_in[0]):.2f}" y2="{uy(c3_in[1]):.2f}"/>')
    out_lines.append(
        f'    <line id="c3_handle_out_line" x1="{ux(n20_sharp[0]):.2f}" y1="{uy(n20_sharp[1]):.2f}" '
        f'x2="{ux(c3_out[0]):.2f}" y2="{uy(c3_out[1]):.2f}"/>')
    out_lines.append(
        f'    <circle id="c3_handle_in_dot" cx="{ux(c3_in[0]):.2f}" cy="{uy(c3_in[1]):.2f}" r="2.5"/>')
    out_lines.append(
        f'    <circle id="c3_handle_out_dot" cx="{ux(c3_out[0]):.2f}" cy="{uy(c3_out[1]):.2f}" r="2.5"/>')
    out_lines.append(
        f'    <circle id="c3_node" cx="{ux(n20_sharp[0]):.2f}" cy="{uy(n20_sharp[1]):.2f}" '
        f'r="4" fill="none" stroke="{C3_COLOR}" stroke-width="0.8"/>')
    out_lines.append('  </g>')

    out_lines.append(f'  <g id="n4_handles" stroke="{N4_COLOR}" stroke-width="0.8" fill="{N4_COLOR}">')
    out_lines.append(
        f'    <line id="n4_handle_in_line" x1="{ux(n20_sharp[0]):.2f}" y1="{uy(n20_sharp[1]):.2f}" '
        f'x2="{ux(c3_in[0]):.2f}" y2="{uy(c3_in[1]):.2f}"/>')
    out_lines.append(
        f'    <line id="n4_handle_out_line" x1="{ux(n20_sharp[0]):.2f}" y1="{uy(n20_sharp[1]):.2f}" '
        f'x2="{ux(n4_out[0]):.2f}" y2="{uy(n4_out[1]):.2f}"/>')
    out_lines.append(
        f'    <circle id="n4_handle_in_dot" cx="{ux(c3_in[0]):.2f}" cy="{uy(c3_in[1]):.2f}" r="2.5"/>')
    out_lines.append(
        f'    <circle id="n4_handle_out_dot" cx="{ux(n4_out[0]):.2f}" cy="{uy(n4_out[1]):.2f}" r="2.5"/>')
    out_lines.append('  </g>')

    out_lines.append('</svg>')
    SVG_PATH.write_text('\n'.join(out_lines) + '\n')

if __name__ == "__main__":
    main()
