# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

Design materials for **BabyHarp 12** — a 12-string diatonic prototype of a custom electronic Paraguayan-style harp. Two coupled artifacts drive the design:

- **`babyharp.py`** — the parametric design script. Reads `babyharp_frame.svg` for the immutable frame paths (neck, column, joint, soundbox, original pins/tuners) and writes a fully-regenerated `babyharp12.svg` with computed strings, eyelets, pin/tuner positions, labeled control nodes, and Bezier-fit frame outlines.
- **`bezierfit.py`** — Python port of Philip J. Schneider's adaptive curve-fitting algorithm ("Graphics Gems"). Used by `babyharp.py` to fit smooth multi-Bezier curves to the original polyline frame paths.

Output: **`babyharp12.svg`** is regenerated each run; it's checked in for at-a-glance viewing.

Run: `python3 babyharp.py` (requires `numpy` and `svgwrite`).

## Key design facts

- **12 strings**, diatonic, tuned **C5 → G6** (`TUNING_START = "C5"`).
- **50° rake** between string axis and soundboard (`RAKE_ANGLE_DEG`).
- **13 mm perpendicular air gap** between adjacent string ODs (`STRING_AIR_GAP_MM`); equal eyelet spacing along the soundboard between the column foot and the soundbox top corner.
- **Nylon strings** (`STRING_DENSITY_KG_M3 = 1140`); diameters back-solved via the Mersenne formula `d = (1 / (L*f)) * sqrt(T / (π·ρ))` from a tension gradient (`TENSION_BASS_N = 100`, `TENSION_TREBLE_N = 8` — bass higher so bass diameter comes out larger).
- **2 mm CRAFTME self-backing grommet eyelets**.
- **Scale calibration**: `INNER_PER_MM = 66.6 / BIG_CIRCLE_DIA_MM` (the tuner OD anchors mm-to-inner-unit scale).

## SVG structure and coordinate system

- Output viewBox is `0 0 708.88 930.78`. The inner content is wrapped in nested transforms `matrix(2,0,0,-2,0,930.78)` (Y-flip + 2× scale) then `scale(0.1)`, so coordinates in `babyharp.py` are in an "inner" space where a 7mm tuner is 66.6 inner units. Net pixel-per-inner = 0.2.
- Labeled control-node groups (with prefix-letter color coding):
  - **C0–C9** (green) — column outline. C0–C3 sit on the shared neck/column boundary at the bass end; C4–C9 trace the rest of the column.
  - **N0–N5** (red) — neck outline. N4 = C3 (same point); the neck makes a sharp 90° corner here while the column outline is G1-smooth.
  - **S0–S3** (blue) — soundbox.
  - **J0–J3** (brown) — joint at the treble end.
- A **neck spacer** (brown) tucks into the treble end of the neck between the joint and a vertical line above the G6 (treble-most) eyelet — analogous to how the column tucks into the bass end.

## Working in this repo

- The script is **idempotent**: it always re-reads `babyharp_frame.svg` and fully rewrites `babyharp12.svg`. To experiment with frame geometry, edit `babyharp_frame.svg` (binary-ish — actually XML, but the paths were extracted from EPS and are hand-tuned).
- When changing C3/C4/N4 area handles, remember the Schneider fit can leave hooks at split points whose neighbors were dropped; check the rendered result, not just the bezier coordinates.
- Render check: `inkscape babyharp12.svg --export-type=png --export-filename=/tmp/p.png --export-width=900`. Read the PNG to verify geometry visually after non-trivial edits.
