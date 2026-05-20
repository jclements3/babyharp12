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
import math, re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import svgwrite

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
BIG_CIRCLE_DIA_MM    = 9.0    # big-hole (TUNER) OD; used for mm scale.
                              # Bumped from 6 -> 9 to scale the whole harp 1.5x
                              # so the strings get realistic nylon lengths.
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
FRAME_SRC_PATH = Path(__file__).parent / "babyharp_frame.svg"  # immutable

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
    eyelet: tuple = (0.0, 0.0)           # soundbox attach (inner coords)
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

    # Iterate: eyelet spacing depends on string diameters, which depend on
    # string LENGTHS (which depend on eyelet positions). Converge.
    for s in specs: s.diameter_mm = 1.5
    for _ in range(5):
        # ---- Eyelets along soundboard ----
        # Bass eyelet at BASS_OFFSET_MM up the soundboard from column foot.
        # Each next eyelet steps up by (perp_air_gap + avg_string_r)/sin(rake)
        # so the perpendicular gap between adjacent string ODs is AIR_GAP.
        ce_first = add(INNER_COLUMN_FOOT,
                       mul(SB_DIR, BASS_OFFSET_MM * INNER_PER_MM))
        specs[0].eyelet = ce_first
        for i in range(1, NUM_STRINGS):
            perp_step_mm = (STRING_AIR_GAP_MM
                            + (specs[i-1].diameter_mm + specs[i].diameter_mm)/2)
            step_inner = (perp_step_mm / sin_rake) * INNER_PER_MM
            specs[i].eyelet = add(specs[i-1].eyelet, mul(SB_DIR, step_inner))

        # ---- Pin (string tip) END point: project original small-hole onto
        #      the parallel string line from the eyelet. ----
        for i, pin_orig in enumerate(SMALL_HOLES_INNER):
            v = sub(pin_orig, specs[i].eyelet)
            t = v[0]*str_dir[0] + v[1]*str_dir[1]
            tip = add(specs[i].eyelet, mul(str_dir, t))
            # Store tip in spec.pin TEMPORARILY; overwritten below with the
            # real pin-center offset.
            specs[i].pin = tip

        # ---- Vibrating length + required diameter ----
        for s in specs:
            s.length_mm = vibrating_length_mm(s.eyelet, s.pin)
            s.diameter_mm = diameter_for_freq_mm(s.length_mm, s.freq_hz,
                                                 s.tension_n,
                                                 STRING_DENSITY_KG_M3)

    # ---- Final eyelet center adjustment: shift eyelet center DOWN the
    # soundboard by (eyelet_r - string_r) so the string sits against the
    # upper inner edge of the eyelet hole under tension. ----
    eyelet_r_inner = (EYELET_ID_MM/2) * INNER_PER_MM
    for s in specs:
        string_r_inner = (s.diameter_mm/2) * INNER_PER_MM
        off = eyelet_r_inner - string_r_inner
        s.eyelet = (s.eyelet[0] - SB_DIR[0]*off, s.eyelet[1] - SB_DIR[1]*off)

    # ---- Final pin center: shift from the string tip perpendicular to the
    # string by (pin_r + string_r) so the pin OD is tangent to the string OD
    # on the RIGHT side of the string. ----
    pin_r_inner = (SMALL_CIRCLE_DIA_MM/2) * INNER_PER_MM
    str_up = (-str_dir[0], -str_dir[1])
    perpA = (-str_up[1],  str_up[0])
    perpB = ( str_up[1], -str_up[0])
    pin_perp = perpA if perpA[0] > perpB[0] else perpB
    for s in specs:
        tip = s.pin
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
    src_svg = FRAME_SRC_PATH.read_text()

    def frame_d(pid: str) -> str:
        m = re.search(r'd="([^"]+)"\s+style="[^"]*"\s+id="'+pid+r'"', src_svg)
        return m.group(1) if m else ""

    # Originals: neck arch, column-back curve, column-front curve, column-base,
    # joint, soundbox-left, soundbox-right.
    d_neck_arch  = frame_d("path20")
    d_col_back   = frame_d("path68")  # 859.996,3506.9  -> 1244,66.5
    d_col_front  = frame_d("path70")  # 1787,847.102    -> 859.996,3506.9
    d_col_base   = frame_d("path66")  # 1244,66.5       -> 1335.2,67.6992
    d_joint      = frame_d("path72")  # closed thin quad at neck-soundbox junction
    d_sb_left    = frame_d("path74")  # 2918,2807.3 -> 1339.4,71.3 -> 1337,67.7 -> 2541.2,67.7
    d_sb_right   = frame_d("path76")  # 2541.2,67.7 -> 3343.4,2608.1 -> 2918,2807.3

    def strip_leading_M(d: str) -> str:
        return re.sub(r'^[Mm]\s*-?\d+\.?\d*\s*,?\s*-?\d+\.?\d*\s*', '', d).strip()

    def chain(d: str) -> str:
        """Strip leading M/m and prepend a continuation command. If the tail
        already starts with a command letter, leave it; otherwise prepend 'l'
        so the implicit coord pairs are treated as relative linetos."""
        t = strip_leading_M(d)
        return ('l ' + t) if (t and t[0] not in 'MmLlHhVvCcSsQqTtAaZz') else t

    # Closed COMBINED paths for each region.
    d_neck     = f"{d_neck_arch} Z"
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
    p68_pts = parse_abs_pts(d_col_back)
    p70_pts = parse_abs_pts(d_col_front)

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
    p68_seq = [(859.996, 3506.9), p68_sharp, p68_left, p68_waist, p68_lower,
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

    p68_beziers = beziers_along(p68_seq, p68_pts)
    p70_beziers = beziers_along(p70_seq, p70_pts)

    def bez_str(b):
        c1, c2, p = b
        return (f"C {c1[0]:.2f} {c1[1]:.2f} {c2[0]:.2f} {c2[1]:.2f} "
                f"{p[0]:.2f} {p[1]:.2f}")
    d_column = " ".join([
        f"M {p70_seq[0][0]:.2f} {p70_seq[0][1]:.2f}",
        *[bez_str(b) for b in p70_beziers],
        *[bez_str(b) for b in p68_beziers],
        "L 1244 67.6992 L 1335.2 67.6992",
        "L 1337 67.6992 L 1339.4 71.3008 L 1787 847.102 Z",
    ])
    d_joint_z  = d_joint    # path72 is already closed

    # ---- svgwrite document ----
    dwg = svgwrite.Drawing(
        SVG_PATH.as_posix(),
        size=("708.88", "930.78"),
        viewBox="0 0 708.88 930.78",
        debug=False,
    )
    # Outer transforms mirror the original SVG: scale 2x then Y-flip, then 0.1x scale
    g_root = dwg.g(transform="matrix(2,0,0,-2,0,930.78)")
    dwg.add(g_root)
    g_inner = dwg.g(transform="scale(0.1)")
    g_root.add(g_inner)

    # FRAME GROUPS (one per harp part), each named
    g_neck = dwg.g(id="neck",
                   fill="#cc0000", fill_opacity=0.25,
                   stroke="#cc0000", stroke_width="7.2",
                   stroke_linecap="round", stroke_linejoin="round")
    g_neck.add(dwg.path(d=d_neck, id="neck_outline"))
    g_inner.add(g_neck)

    g_column = dwg.g(id="column",
                     fill="#00aa00", fill_opacity=0.25,
                     stroke="#00aa00", stroke_width="7.2",
                     stroke_linecap="round", stroke_linejoin="round")
    g_column.add(dwg.path(d=d_column, id="column_outline"))
    g_inner.add(g_column)

    g_soundbox = dwg.g(id="soundbox",
                       fill="#0080ff", fill_opacity=0.25,
                       stroke="#0080ff", stroke_width="7.2",
                       stroke_linecap="round", stroke_linejoin="round")
    g_soundbox.add(dwg.path(d=d_soundbox, id="soundbox_outline"))
    g_inner.add(g_soundbox)

    g_joint = dwg.g(id="joint",
                    fill="#8b4513", fill_opacity=0.6,
                    stroke="#8b4513", stroke_width="7.2",
                    stroke_linecap="round", stroke_linejoin="round")
    g_joint.add(dwg.path(d=d_joint_z, id="joint_outline"))
    g_inner.add(g_joint)

    # STRINGS — one path per note, going eyelet -> pin arc -> tuner arc.
    g_strings = dwg.g(id="strings", fill="none", stroke_linecap="round")
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
        d = (f"M {s.eyelet[0]:.2f} {s.eyelet[1]:.2f}"
             f" L {pin_entry[0]:.2f} {pin_entry[1]:.2f}"
             f" A {r_pin_c:.2f} {r_pin_c:.2f} 0 0 0 "
             f"{pin_exit_outer[0]:.2f} {pin_exit_outer[1]:.2f}"
             f" L {tuner_entry[0]:.2f} {tuner_entry[1]:.2f}"
             f" A {r_tnr_c:.2f} {r_tnr_c:.2f} 0 0 0 "
             f"{tuner_end[0]:.2f} {tuner_end[1]:.2f}")
        g_strings.add(dwg.path(d=d, id=f"string_{s.note}",
                               stroke=string_color(s.note),
                               stroke_width=f"{s.diameter_mm*INNER_PER_MM:.2f}"))
    g_inner.add(g_strings)

    # EYELETS
    g_eyelets = dwg.g(id="eyelets", fill="none",
                      stroke="#444444", stroke_width="3")
    for s in specs:
        g_eyelets.add(dwg.circle(center=s.eyelet, r=eyelet_r_inner,
                                 id=f"eyelet_{s.note}"))
    g_inner.add(g_eyelets)

    # PINS
    g_pins = dwg.g(id="pins", fill="#ff8800", fill_opacity=0.5,
                   stroke="#ff8800", stroke_width="3")
    for s in specs:
        g_pins.add(dwg.circle(center=s.pin, r=pin_r_inner,
                              id=f"pin_{s.note}"))
    g_inner.add(g_pins)

    # TUNERS
    g_tuners = dwg.g(id="tuners", fill="#9933cc", fill_opacity=0.4,
                     stroke="#9933cc", stroke_width="3")
    for s in specs:
        g_tuners.add(dwg.circle(center=s.tuner, r=tuner_r_inner,
                                id=f"tuner_{s.note}"))
    g_inner.add(g_tuners)

    # SOUNDBOX node labels (0..3) — blue, matching soundbox color.
    # The path has a tiny 5-unit jog (1339.4,71.3 -> 1337,67.7) at the bottom-
    # left; visually it's one point so we collapse it to one node.
    SOUNDBOX_NODES = [
        (2918.0,  2807.3),   # S0 top, meets neck/joint
        (1338.0,    69.5),   # S1 bottom-left (avg of the two near-coincident vertices)
        (2541.2,    67.6992),# S2 bottom-right at base
        (3343.4,  2608.1),   # S3 top-right
    ]
    # Helper to label each corner along its inward angle bisector. If the
    # bisector ends up pointing away from the polygon centroid, flip it.
    # `overrides` is {index: (dx, dy)} of explicit per-node offsets.
    LABEL_DIST = 75
    def add_corner_labels(nodes, group_id, color, overrides=None):
        overrides = overrides or {}
        cx = sum(p[0] for p in nodes) / len(nodes)
        cy = sum(p[1] for p in nodes) / len(nodes)
        g = dwg.g(id=group_id, fill=color,
                  font_family="sans-serif", font_size="80",
                  font_weight="bold")
        n = len(nodes)
        for i, v in enumerate(nodes):
            if i in overrides:
                ox, oy = overrides[i]
                lx, ly = v[0] + ox, v[1] + oy
            else:
                prev_v = nodes[(i - 1) % n]
                next_v = nodes[(i + 1) % n]
                bis = add(unit(sub(prev_v, v)), unit(sub(next_v, v)))
                if math.hypot(*bis) < 1e-6:
                    bis = unit((cx - v[0], cy - v[1]))
                else:
                    bis = unit(bis)
                    to_centroid = (cx - v[0], cy - v[1])
                    if bis[0]*to_centroid[0] + bis[1]*to_centroid[1] < 0:
                        bis = (-bis[0], -bis[1])
                lx = v[0] + bis[0] * LABEL_DIST
                ly = v[1] + bis[1] * LABEL_DIST
            g.add(dwg.text(
                str(i),
                insert=(0, 0),
                transform=f"translate({lx:.2f},{ly:.2f}) scale(1,-1)",
                text_anchor="middle",
            ))
        g_inner.add(g)

    add_corner_labels(SOUNDBOX_NODES, "soundbox_labels", "#0080ff")

    # Column nodes ordered CCW visually starting at the top of the column.
    # The path68/path70 parse and inflection-point detection was done earlier
    # (just after the frame paths were extracted) so it's available here AND
    # for the Bezier curve fit.
    COLUMN_NODES = [
        ( 859.996, 3506.9),   # C0 top (meets neck)
        p68_sharp,            # C1 top-left sharp corner
        p68_left,             # C2 outer curve UPPER leftmost bulge
        p68_waist,            # C3 outer curve waist (max-X)
        p68_lower,            # C4 outer curve LOWER leftmost bulge (between waist and base)
        (1244.0,    66.5),    # C5 base bottom-left
        (1335.2,    67.6992), # C6 base bottom-right
        (1787.0,    847.102), # C7 foot at soundbox diagonal
        p70_left,             # C8 inner curve leftmost bulge
    ]
    add_corner_labels(COLUMN_NODES, "column_labels", "#00aa00",
                      overrides={5: (-180, 60)})

    # Small green dots marking each column control node. Use a dark green
    # outline + lighter fill so dots are visible even on top of green strokes.
    g_col_dots = dwg.g(id="column_node_dots", fill="#ffffff",
                       stroke="#006400", stroke_width=6)
    for (x, y) in COLUMN_NODES:
        g_col_dots.add(dwg.circle(center=(x, y), r=22))
    g_inner.add(g_col_dots)

    # Real Bezier control-handle visualization. For each fitted Bezier
    # segment [p0, c1, c2, p3]: c1 is the forward handle at p0; c2 is the
    # backward handle at p3. Draw a solid line from node to handle endpoint.
    g_handles = dwg.g(id="column_handles", stroke="#00aa00",
                      stroke_width=4, stroke_dasharray="14,8", fill="none")

    # Combine the two sequences with their bezier control points.
    bezier_segs = []
    for seq, beziers in ((p70_seq, p70_beziers), (p68_seq, p68_beziers)):
        for k, (c1, c2, p3) in enumerate(beziers):
            p0 = seq[k]
            bezier_segs.append((p0, c1, c2, p3))

    for p0, c1, c2, p3 in bezier_segs:
        # Forward handle at p0 -> c1
        g_handles.add(dwg.line(start=p0, end=c1))
        g_handles.add(dwg.circle(center=c1, r=10, fill="#00aa00", stroke="none"))
        # Backward handle at p3 -> c2
        g_handles.add(dwg.line(start=p3, end=c2))
        g_handles.add(dwg.circle(center=c2, r=10, fill="#00aa00", stroke="none"))

    # Straight segments at the base (C5..C7) — show horizontal/vertical handles
    # for visual completeness (these are L commands, not C, so the "handle"
    # is just along the line direction).
    base_handles = [
        ((1244.0, 66.5),     (1244.0, 67.6992)),    # C5 up to v-h corner
        ((1244.0, 67.6992),  (1335.2, 67.6992)),    # v-h corner to C6
        ((1335.2, 67.6992),  (1337.0, 67.6992)),    # C6 tiny step
        ((1337.0, 67.6992),  (1339.4, 71.3008)),    # diagonal start
        ((1339.4, 71.3008),  (1787.0, 847.102)),    # closure diagonal
    ]
    for a, b in base_handles:
        g_handles.add(dwg.line(start=a, end=b, stroke_dasharray="4,4"))
    g_inner.add(g_handles)

    dwg.save()

if __name__ == "__main__":
    main()
