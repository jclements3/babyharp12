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
SVG_PATH = Path(__file__).parent / "babyharp12.svg"

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

    svg = SVG_PATH.read_text()

    # Remove ANY existing <g id="strings"> blocks (depth-aware so labels with
    # inner <g> from older runs are stripped too).
    def remove_g_blocks(svg, gid):
        while True:
            start = svg.find(f'<g id="{gid}"')
            if start < 0:
                return svg
            i = start; depth = 0
            while i < len(svg):
                if svg.startswith('<g', i) and i+2 < len(svg) and svg[i+2] in ' >\t\n':
                    depth += 1; i += 2
                elif svg.startswith('</g>', i):
                    depth -= 1
                    if depth == 0:
                        svg = svg[:start] + svg[i+4:]
                        break
                    i += 4
                else:
                    i += 1
            else:
                return svg
    svg = remove_g_blocks(svg, "strings")

    # Remove the original small-circle (pin) and big-circle (tuner) paths.
    # The script draws fresh ones at the computed positions.
    for pid in (# small (pins)
                "path22","path24","path26","path38","path40","path42",
                "path44","path46","path60","path62","path64",
                # big (tuners)
                "path28","path30","path32","path34","path36","path48",
                "path50","path52","path54","path56","path58"):
        svg = re.sub(
            r'<path[^/]*?id="' + pid + r'"\s*/>', '', svg, count=1)

    paths = []
    tuner_r_inner = (BIG_CIRCLE_DIA_MM/2) * INNER_PER_MM

    # Strings: eyelet -> tangent to pin LEFT -> CW arc on pin -> tangent line
    # to tuner LEFT -> CW arc on tuner.
    for i, s in enumerate(specs):
        sr = (s.diameter_mm/2) * INNER_PER_MM      # string outer radius

        # 1) string entry-tangent on the pin (perpendicular foot from pin
        #    center onto the line through eyelet in str_dir direction).
        v = sub(s.pin, s.eyelet)
        t_entry = v[0]*str_dir[0] + v[1]*str_dir[1]
        pin_entry = add(s.eyelet, mul(str_dir, t_entry))

        # 2) pin exit-tangent: along the takeoff direction, offset perpendicular
        #    by (pin_r + sr) on the same side as the entry.
        # The pin->tuner segment direction is `takeoff_dir`; the exit tangent
        # is perpendicular to takeoff_dir from pin center.
        perp_t = (-takeoff_dir[1], takeoff_dir[0])
        # pick perp that points toward the same side as the entry (away from tuner-side)
        ent_off = sub(pin_entry, s.pin)
        sign = 1 if (ent_off[0]*perp_t[0] + ent_off[1]*perp_t[1]) > 0 else -1
        pin_exit_outer = (s.pin[0] + sign*perp_t[0]*(pin_r_inner + sr),
                          s.pin[1] + sign*perp_t[1]*(pin_r_inner + sr))

        # 3) tuner entry-tangent: where the line from pin_exit_outer in takeoff_dir
        #    first touches the tuner OD on the LEFT side.
        perp_t2 = perp_t  # same perpendicular; use same side
        tuner_entry = (s.tuner[0] + sign*perp_t2[0]*(tuner_r_inner + sr),
                       s.tuner[1] + sign*perp_t2[1]*(tuner_r_inner + sr))

        # SVG arc sweep flag: with the SVG Y-flip transform, sweep=0 renders CW
        # visually. Both pin and tuner wraps are CW.
        sweep_pin = 0
        sweep_tuner = 0
        sw = s.diameter_mm * INNER_PER_MM
        col = string_color(s.note)
        r_pin_c = pin_r_inner + sr
        r_tnr_c = tuner_r_inner + sr
        tuner_end = (2*s.tuner[0] - tuner_entry[0],
                     2*s.tuner[1] - tuner_entry[1])
        d = (f"M {s.eyelet[0]:.2f} {s.eyelet[1]:.2f}"
             f" L {pin_entry[0]:.2f} {pin_entry[1]:.2f}"
             f" A {r_pin_c:.2f} {r_pin_c:.2f} 0 0 {sweep_pin} "
             f"{pin_exit_outer[0]:.2f} {pin_exit_outer[1]:.2f}"
             f" L {tuner_entry[0]:.2f} {tuner_entry[1]:.2f}"
             f" A {r_tnr_c:.2f} {r_tnr_c:.2f} 0 0 {sweep_tuner} "
             f"{tuner_end[0]:.2f} {tuner_end[1]:.2f}")
        paths.append(
            f'<path d="{d}" '
            f'style="fill:none;stroke:{col};stroke-width:{sw:.2f};stroke-linecap:round" />'
        )

    # Eyelets
    for s in specs:
        ex, ey = s.eyelet
        paths.append(
            f'<circle cx="{ex:.2f}" cy="{ey:.2f}" r="{eyelet_r_inner:.2f}" '
            f'style="fill:none;stroke:#444;stroke-width:3" />'
        )
    # Pins
    for s in specs:
        px, py = s.pin
        paths.append(
            f'<circle cx="{px:.2f}" cy="{py:.2f}" r="{pin_r_inner:.2f}" '
            f'style="fill:#ff8800;fill-opacity:0.5;stroke:#ff8800;stroke-width:3" />'
        )
    # Tuners
    for s in specs:
        tx, ty = s.tuner
        paths.append(
            f'<circle cx="{tx:.2f}" cy="{ty:.2f}" r="{tuner_r_inner:.2f}" '
            f'style="fill:#9933cc;fill-opacity:0.4;stroke:#9933cc;stroke-width:3" />'
        )

    # ----- Frame node labels -----
    # Label the structural vertices of NECK / COLUMN / SOUNDBOX in the matching
    # region color. Use transform directly on <text> (no wrapping <g>) so the
    # strings group stays flat and can be cleanly replaced on re-runs.
    def label(x, y, txt, color):
        return (f'<text transform="translate({x:.2f},{y:.2f}) scale(1,-1)" '
                f'font-size="60" font-family="sans-serif" '
                f'fill="{color}" font-weight="bold" text-anchor="middle">{txt}</text>')

    # Sample additional neck nodes by parsing path20 (the neck outer curve)
    def parse_abs_pts(d):
        toks = re.findall(r'[MmLlHhVvZz]|-?\d+\.?\d*', d.strip())
        i = 0; cx = cy = 0.0; pts = []; last = None
        while i < len(toks):
            t = toks[i]
            if t.isalpha(): cmd = t; i += 1
            else: cmd = 'L' if last=='M' else ('l' if last=='m' else last)
            last = cmd
            if cmd in ('M','m','L','l'):
                x,y = float(toks[i]), float(toks[i+1]); i += 2
                if cmd in ('m','l') and pts: cx+=x; cy+=y
                else: cx=x; cy=y
                pts.append((cx,cy))
        return pts
    m = re.search(r'd="([^"]+)"\s+style="[^"]*"\s+id="path20"', svg)
    neck_pts = parse_abs_pts(m.group(1)) if m else []
    if neck_pts:
        xs=[p[0] for p in neck_pts]; ys=[p[1] for p in neck_pts]
        NECK_NODES = [
            neck_pts[0],                       # N0 start
            neck_pts[xs.index(max(xs))],       # N1 rightmost (back top of head)
            neck_pts[ys.index(max(ys))],       # N2 topmost
            neck_pts[xs.index(min(xs))],       # N3 leftmost (back of head)
            neck_pts[ys.index(min(ys))],       # N4 lowest of curve
            neck_pts[-1],                      # N5 end
        ]
    else:
        NECK_NODES = [(3354.2, 2638.7), (2929.4, 2837.3)]
    COLUMN_NODES = [
        (1787.0,  847.102),  # C0 - foot at soundbox
        (859.996, 3506.9),   # C1 - top of column
        (1244.0,  66.5),     # C2 - bottom-left of column base
        (1335.2,  67.6992),  # C3 - bottom-right of column base
    ]
    SOUNDBOX_NODES = [
        (2918.0,  2807.3),   # S0 - top, meets neck/joint
        (1339.4,  71.3008),  # S1 - bottom-left of soundboard diagonal
        (2541.2,  67.6992),  # S2 - bottom-right at base
        (3343.4,  2608.1),   # S3 - top-right
    ]
    # Per-node offsets (inner units) to push each label OUTSIDE its region.
    # +X = right screen, +Y = UP screen (inner Y positive = up screen).
    OFF = 250
    for i, (x, y) in enumerate(NECK_NODES):
        paths.append(label(x + OFF, y + OFF, f"N{i}", "#cc0000"))
    col_offsets = [(+OFF, -OFF), (-OFF, +OFF), (-OFF, -OFF), (+OFF*2, -OFF)]
    for i, (x, y) in enumerate(COLUMN_NODES):
        ox, oy = col_offsets[i]
        paths.append(label(x + ox, y + oy, f"C{i}", "#00aa00"))
    sb_offsets = [(+OFF*2, +OFF), (-OFF, -OFF), (+OFF, -OFF), (+OFF*2, +OFF)]
    for i, (x, y) in enumerate(SOUNDBOX_NODES):
        ox, oy = sb_offsets[i]
        paths.append(label(x + ox, y + oy, f"S{i}", "#0080ff"))
    new_group = ('<g id="strings" style="fill:none;stroke-linecap:round">'
                 + "".join(paths) + "</g>")
    new = re.sub(r'<g id="strings"[^<]*(?:<[^/]+/>)+</g>', new_group, svg)
    if new == svg:
        new = svg.replace('id="path76" />', f'id="path76" />{new_group}')
    SVG_PATH.write_text(new)

if __name__ == "__main__":
    main()
