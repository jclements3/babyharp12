# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

Design materials for a custom electronic Paraguayan-style pedal harp ("BabyHarp"). Two distinct artifacts live here:

- **`harp.md`** — canonical text spec for the **full 47-string** instrument, written as ASCII-art views (side, front pillar, front soundboard, rear neck). Source of truth for everything described in text. Diagrams are positional and column-sensitive — preserve fixed-width alignment exactly when editing.
- **`babyharp.py`** + **`babyharp12.svg`** — a **12-string** prototype rendering. The script back-solves string geometry and physics from a handful of parameters and rewrites the SVG in place. Run with `python3 babyharp.py` (no deps beyond stdlib). The two artifacts are coupled: the SVG provides hardcoded anchor coordinates the script reads, and the script regenerates the `<g id="strings">` group + pin/tuner/eyelet circles every run.

**Don't conflate the two scopes** — `harp.md` is the full 47-string design (C1→G7, three Teensys, 7 pedals); `babyharp.py` is a 12-string diatonic prototype defaulting to C5→G6. When the user asks about "the harp," clarify which they mean if it's not obvious from context.

## Running and modifying `babyharp.py`

**The script is currently broken** — running it does not produce useful output. Long history of attempted fixes; don't run it speculatively to "see what happens" and don't claim a change works just because the script exits cleanly. Reason through the math/geometry first and ask the user before invoking it.

- *Intended* behavior: `python3 babyharp.py` rewrites `babyharp12.svg` in place and prints a per-string table (note, Hz, vibrating length mm, tension N, computed diameter mm).
- *Intended* idempotency: strips any prior `<g id="strings">` block (depth-aware) and a known list of original pin/tuner path IDs (`path22`, `path24`, … `path64` for pins; `path28`–`path58` for tuners) before re-emitting them. If you add new structural paths to the SVG, they will not be touched.
- Tweakable knobs cluster at the top of the file under `PARAMETERS`:
  - **Geometry**: `RAKE_ANGLE_DEG`, `BASS_OFFSET_MM`, `PIN_INSET_MM`, `TAKEOFF_ANGLE_DEG`, `TUNER_TAKEOFF_DEG`, `TUNER_DIST_BASS_MM`, `TUNER_DIST_TREBLE_MM`, `STRING_AIR_GAP_MM`, `EYELET_ID_MM`, `SMALL_CIRCLE_DIA_MM` (pin), `BIG_CIRCLE_DIA_MM` (tuner — also the mm-scale reference for the whole drawing).
  - **Tuning**: `NUM_STRINGS`, `TUNING_START` (e.g. `"C5"`), `TUNING_MODE` (`"diatonic"` or `"chromatic"`).
  - **Physics**: `STRING_DENSITY_KG_M3` (nylon = 1140), `TENSION_BASS_N`, `TENSION_TREBLE_N` (linear gradient; bass higher so bass diameter comes out larger).
- After `main()` runs, every string is exposed as `STRINGS["C5"]` (a `StringSpec` with `eyelet`/`pin`/`tuner`/`length_mm`/`diameter_mm`/`tension_n`/`freq_hz`) plus convenience module globals `c5e`/`c5p`/`c5t`. Built for REPL inspection — keep that surface if you refactor.
- The diameter solve is **iterative** (5 passes): eyelet spacing depends on string diameters, which depend on vibrating lengths, which depend on eyelet positions. Don't try to make this single-pass.

## SVG coordinate system (when touching `babyharp12.svg` or its anchors)

- The SVG uses an **"inner" coordinate space** at roughly `INNER_PER_MM ≈ 11.1` (derived from `INNER_BIG_DIA = 66.6 / BIG_CIRCLE_DIA_MM = 9.0`). All hardcoded anchors in `babyharp.py` are in inner coords.
- The drawing applies a Y-flip transform downstream, so text labels are emitted with `transform="scale(1,-1)"` to read right-side-up. Keep that wrapper if you add labels.
- The script reads these baked-in anchors from the original SVG layout — **if the SVG geometry changes, these must be re-extracted**:
  - `SMALL_HOLES_INNER` — 12 string-guide pin centers
  - `BIG_HOLES_INNER` — 11 tuner centers (12th was extrapolated by hand)
  - `SOUNDBOARD_A`, `SOUNDBOARD_B` — endpoints of the soundboard line
  - `INNER_COLUMN_FOOT` — where the inner column meets the soundboard; bass string anchors `BASS_OFFSET_MM` up the soundboard from here

## Instrument design facts (from `harp.md`)

The full 47-string design, separate from the 12-string prototype scope above:

- **47 strings**, range **C1 → G7**, numbered 1 (lowest, C1) to 47 (highest, G7).
- **Soundboard** mounted at **65° from horizontal**.
- **Piezo pickups** along the soundboard at **~33 mm intervals**, one per string.
- **Tuning pins** alternate sides of the neck: `◑` = +Z side (left), `◐` = -Z side (right) in the side view.
- **Three Teensy microcontrollers** split the range; only Teensy 1 has Bluetooth:
  - Teensy 1: **C1 – E3** (with Bluetooth)
  - Teensy 2: **F3 – A5**
  - Teensy 3: **B5 – G7**
- **Pedals**: 7 pedals in the order `d c b | e f g a` (bass-side `d c b`, treble-side `e f g a`; bar is the player's centerline). Each is a 3-position toggle: **up = flat, middle = natural, down = sharp** (standard pedal-harp convention).
- **Z=0** is the centerline of the pillar, soundboard, and neck — Z runs across the instrument, left/right of center.
