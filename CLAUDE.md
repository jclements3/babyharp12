# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

Not a software project. This directory holds design materials for a custom electronic Paraguayan-style pedal harp ("BabyHarp"). There is no build, lint, or test step — work here is editing the spec, reasoning about the instrument's mechanics/electronics, and discussing/modifying the PDF and EPS design artifacts.

Contents:
- `harp.md` — the canonical design spec, written as ASCII-art views (side, front pillar, front soundboard, rear neck). Treat this as the source of truth for dimensions and layout described in text.
- `BabyHarp.pdf`, `BabyHarp 1.pdf` … `BabyHarp 7.pdf`, `page1.pdf` — design drawings/schematics.
- `babyharp12.eps` — vector drawing (EPS Level 2). Use `gs` / Inkscape / similar if rendering is needed; do not assume the user wants it converted unless they ask.

## Instrument design facts worth knowing before answering questions

From `harp.md` — keep these in mind so you don't have to re-derive them:

- **47 strings**, range **C1 → G7**, numbered 1 (lowest, C1) to 47 (highest, G7).
- **Soundboard** mounted at **65° from horizontal**.
- **Piezo pickups** mounted along the soundboard at **~33 mm intervals**, one per string.
- **Tuning pins** alternate sides of the neck: `◑` = +Z side (left), `◐` = -Z side (right).
- **Three Teensy microcontrollers** split the range; only Teensy 1 has Bluetooth:
  - Teensy 1: **C1 – E3** (with Bluetooth)
  - Teensy 2: **F3 – A5**
  - Teensy 3: **B5 – G7**
- **Pedals**: 7 pedals in the order `d c b | e f g a` (bass-side `d c b`, treble-side `e f g a` — the bar is the player's centerline). Each is a 3-position toggle: **up = flat, middle = natural, down = sharp** (standard pedal-harp convention).
- Coordinate convention used in the views: `Z=0` is marked at the centerline of the pillar, soundboard, and neck — Z runs across the instrument, left/right of center.

## Working in this repo

- When editing `harp.md`, preserve the ASCII-art alignment exactly — the diagrams are positional and column-sensitive. Use a fixed-width view and verify columns line up after edits.
- The PDFs and EPS are binary artifacts; do not try to text-edit them. If the user wants changes, ask whether they want a regenerated drawing or a description of what to change in their CAD/illustration tool.
- No git history is available (this is not a git repo), so don't rely on `git log`/`git blame` for context.
