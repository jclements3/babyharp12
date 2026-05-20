# BabyHarp 12 — Bill of Materials

12-string diatonic prototype, C5–G6. Parts listed here are referenced by the
parametric script (`babyharp.py` constants and per-string output table).

## Strings

12 monofilament nylon strings, diameters back-solved by `babyharp.py` from the
Mersenne formula with a linear tension gradient (bass 100 N → treble 8 N) and
ρ = 1140 kg/m³.

| # | Note | Hz      | L (mm) | T (N) | d (mm) |
|---|------|---------|--------|-------|--------|
| 1 | C5   | 523.25  | 300.8  | 100.0 | 1.062 |
| 2 | D5   | 587.33  | 278.3  |  91.6 | 0.979 |
| 3 | E5   | 659.26  | 250.3  |  83.3 | 0.924 |
| 4 | F5   | 698.46  | 214.7  |  74.9 | 0.964 |
| 5 | G5   | 783.99  | 178.7  |  66.5 | 0.973 |
| 6 | A5   | 880.00  | 153.0  |  58.2 | 0.947 |
| 7 | B5   | 987.77  | 133.0  |  49.8 | 0.898 |
| 8 | C6   | 1046.50 | 116.7  |  41.5 | 0.881 |
| 9 | D6   | 1174.66 | 103.0  |  33.1 | 0.795 |
| 10 | E6  | 1318.51 |  91.9  |  24.7 | 0.686 |
| 11 | F6  | 1396.91 |  82.9  |  16.4 | 0.584 |
| 12 | G6  | 1567.98 |  75.9  |   8.0 | 0.397 |

Source: TBD (lever-harp nylon set, custom gauges, or individual lengths from
a luthier-supply roll).

## Eyelets

12 × CRAFTME Studio 2 mm Tiny Self-Backing Grommets, one per string.

- ASIN: B0DCG6Z83Q
- Link: <https://www.amazon.com/dp/B0DCG6Z83Q>
- Inner diameter: 2.0 mm (matches `EYELET_ID_MM` in `babyharp.py`).
- Self-backing — no separate washer needed.
- Mounted in the soundboard; string OD sits tangent to upper inner rim under
  tension.

## Bridge pins

12 pins, one per string. Pin OD currently modelled at 3.0 mm
(`SMALL_CIRCLE_DIA_MM`); update the constant if a different pin is chosen.

**Candidate: Roosebeck Bridge Pins, Large Groove, 6-pack** — 2 packs needed.
- ASIN: B08JCP7CYQ
- UPC: 844731063541
- Brand: Roosebeck
- Link: <https://www.amazon.com/Roosebeck-Bridge-Large-Groove-6-Pack/dp/B08JCP7CYQ>
- Notes: dimensions not yet confirmed from the listing — verify pin OD vs. the
  3 mm `SMALL_CIRCLE_DIA_MM` design value before ordering.

## Tuning pegs (tuners)

12 tuning pegs, one per string. Currently modelled at 7.0 mm OD
(`BIG_CIRCLE_DIA_MM` — this is also the mm-scale anchor for the whole drawing).

**Candidate: Guyker Guitar Locking Tuners, 3L + 3R, Chrome** — 2 packs
needed (6 tuners per pack × 2 = 12; gives 6 left-handed + 6 right-handed,
matching the alternation of odd strings on the left cheek and even strings
on the right cheek).
- UPC: 718893958574
- Brand: Guyker
- Color: Chrome
- Quantity per pack: 6 (3 left-handed + 3 right-handed)
- Gear ratio: 1:18, sealed lubrication
- Mounting hole: 10 mm (headstock peg hole diameter)
- Hexagonal button, includes screws, bushings, washers
- Notes:
  - The 10 mm shaft hole > the current 7 mm `BIG_CIRCLE_DIA_MM` design
    value — re-evaluate the mm-scale anchor (the whole drawing scale is
    pinned to this constant) or change to a smaller tuner OD before
    ordering.
  - The 3L/3R split per pack maps naturally to the babyharp's two-cheek
    layout: 6 odd-string tuners on the left cheek, 6 even-string tuners
    on the right cheek.

## Frame and structural

### Plywood

**Baltic birch plywood, 6 mm (1/4") nominal thickness**, full Baltic birch
construction (5 plies). Used for every laminated piece below; the 30 mm
total neck thickness = 5 × 6 mm layers.

Sized so a single sheet (typical 5'×5' / 1525×1525 mm Baltic birch panel)
can hold all the parts below with significant nesting room for waste.

### Layer breakdown (all 6 mm Baltic birch)

| qty | part            | shape source                                    |
|-----|-----------------|-------------------------------------------------|
| 2   | neck cheek      | full neck outline (`neck_back_outline` / `neck_front_outline`) |
| 3   | neck spacer     | treble-end spacer shape (`neck_spacer_outline`) |
| 2   | column support  | top portion of column outline (short — overlaps the neck-cheek area by ~30–50 mm) |
| 3   | column body     | full column outline (`column_outline`), all the way to the soundboard slot |
| 2   | soundbox cheek  | full soundbox outline (`soundbox_outline`) |
| 1   | joint piece     | small joint quad (`joint_outline`)              |
| 1   | soundboard      | TBD — likely a separate tonewood (spruce/cedar), not Baltic birch |

**Total Baltic birch parts: 13.** Plus the soundbox interior / bracing /
back as designed.

### Assembly

- Glue the 3 column-body layers into one solid 18 mm column first.
- Glue the 2 column supports flush to either side of the column-top, giving
  the column a 30 mm-thick "T" at the neck-attach area.
- The 3 neck-spacer layers glue between the 2 neck cheeks — the assembled
  neck slides over the column top so the 18 mm spacer slot mates with the
  18 mm column body, with the 6 mm cheeks flush against the 6 mm column
  supports on each side. Continuous flat exterior surface results.
- The spacer / column-body interior is the 18 mm gap that houses the
  bridge-pin shafts (~4 mm) and the Guyker tuner string-post / lock area
  (~8–12 mm tall). With 18 mm interior there's comfortable clearance.

### Soundboard tonewood

**Sitka spruce, quartersawn, 3 mm (≈1/8") thickness.**

| property | value | rationale |
|---|---|---|
| species | Sitka spruce (*Picea sitchensis*) | high stiffness-to-weight ratio; standard for guitar/harp soundboards; broadly available |
| cut | quartersawn | annual rings perpendicular to the face → max stiffness along the string axis, minimal cupping |
| thickness | ~3.0 mm | typical small-harp range (2.5–3.5 mm); thin enough to be responsive at the low string tensions (8–100 N), thick enough to resist warping under the 12 strings' pull |
| grade | luthier AAA or AA | tight, even grain (8–14 lines/inch); no knots / runout / pitch pockets in the playing area |
| dimensions needed | ~300 × 60 mm playing strip + tabs at each end for the column-foot slot and the soundbox slot | derived from soundboard span C8 → S0 (~238 mm) + margins |

Alternate tonewoods (interchangeable in this design):
- **Western Red Cedar** — warmer / softer attack, slightly less projection. Cheaper than Sitka.
- **Engelmann Spruce** — lighter than Sitka, more responsive, but more expensive and slightly less durable.
- **Adirondack (Red) Spruce** — louder / more dynamic range; pricier and harder to source.

Source: Stewart-MacDonald (StewMac), Luthiers Mercantile International (LMI),
Notre Dame de Bois (NDB), or any local luthier supplier. Quartersawn 3 mm
soundboard blanks pre-jointed and pre-thicknessed are available stock items.

### Soundboard bracing

The string-pull line (eyelet centers, ≈238 mm bass→treble) sits directly on
the underside stringband, which carries essentially all 55 kg of string
load. Two fan braces stiffen the soundboard against drum-mode flexing while
leaving the lower-bout area (below the strings) free to vibrate.

| qty | brace            | material            | dimensions                  | placement                                                                 |
|-----|------------------|---------------------|-----------------------------|---------------------------------------------------------------------------|
| 1   | stringband       | hard maple (or walnut), quartersawn | ~10 mm wide × 8 mm tall × ~260 mm long | underside of soundboard, directly under the eyelet line, full length |
| 2   | fan brace        | Sitka spruce stripping | ~5 mm wide × 8 mm tall × ~160 mm long | underside of soundboard, fanning ±15° from the stringband mid-point toward the lower bout edges |
| 2   | end caps         | Sitka spruce        | ~10 × 10 × 30 mm            | glued at each end of the stringband to reinforce the column-foot and soundbox-top tabs |

Glue with hide glue (best for tone, fully reversible) or Titebond Original
PVA (easier and still acceptable for a prototype). Brace the soundboard
**before** trimming to final shape so braces stiffen the panel during
final scraping.

### Soundbox internals

| qty | part                | material            | notes                                                                            |
|-----|---------------------|---------------------|----------------------------------------------------------------------------------|
| 1   | back panel          | 3 mm Baltic birch or 3 mm Sitka | parallel to the soundboard, glued to the back edges of the soundbox cheeks |
| 2   | bass / treble blocks | hard maple or Baltic birch | 12 × 18 × ~60 mm — solid blocks at each end where the soundboard tabs slot in; takes the full string-tension transfer to the cheeks |
| ~30 | kerfed linings      | basswood or spruce kerfing | ~6 × 8 mm strip, glued continuously around the inside perimeter of the soundbox cheeks; provides ~6 mm of gluing surface for the back and soundboard |
| 2-4 | transverse braces   | Sitka spruce        | ~6 × 10 mm, cross-braced inside the box if needed to suppress unwanted modes (tunable during build) |

### Sound holes

**Two ovals on the back panel**, vertically aligned along the box centerline.

- Shape: ovals, 40 mm long × 22 mm wide each (long axis parallel to the
  player-facing centerline of the box).
- Total open area: 2 × π × 20 × 11 = **≈ 1380 mm²**.
- Placement: centered laterally on the back panel; one centered roughly at
  the bass-half of the box (1/3 of the way from the bass end), the other at
  the treble-half (2/3 of the way from the bass end).

Tuning rationale (Helmholtz resonator):

$$f_{H} = \frac{c}{2\pi}\sqrt{\dfrac{A}{V\,L_{eff}}}$$

- Estimated soundbox internal volume V ≈ 238 × 60 × 50 mm ≈ **7.1 × 10⁻⁴ m³**.
- Effective hole length L_eff ≈ 3 mm (back-panel thickness) + π·r/2 end
  correction × 2 ≈ ~18 mm.
- With A = 1380 mm² and the values above: **f_H ≈ 290 Hz**, about an octave
  below the bass C5 (523 Hz). This puts the Helmholtz peak near the
  fundamental of the missing-low-octave (C4) — exactly where the small
  soundbox most needs help projecting bass response.

Why two holes instead of one big one:

- Two holes spread along the bass→treble axis couple to the soundboard's
  upper and lower bouts more evenly than a single central hole.
- Ovals (vs round) place more open area near the box centerline (where
  the soundboard is structurally weakest) without removing material near
  the side glue joints (where the soundbox needs strength).
- Long-axis along the centerline keeps the perimeter glue joint to the
  back-panel kerfing uninterrupted on each side.

Variants to consider during build:

- If bass response is thin, **enlarge each oval to 45 × 25 mm** (raises A
  by ~30%, drops f_H modestly toward C4).
- If the box sounds boomy / one-note, **add a third smaller round hole**
  (~10 mm diameter) at the centerline between the two ovals; this raises
  f_H toward D4/E4 and broadens the resonance.
- For a more traditional Paraguayan look, **stylize the oval edges** with
  Celtic-knot or geometric piercings around each hole (purely cosmetic,
  no measurable acoustic effect at these sizes).

Fasteners (screws, dowels) and adhesives (Titebond Original PVA for
plywood; hide glue or Titebond for the soundboard / tonewood if you want
reversibility): TBD.

## Electronics

- 3 × Teensy microcontrollers (planned for the full 47-string harp; the
  12-string prototype may use a single MCU). Bluetooth on Teensy 1 only.
- 12 × piezo pickups, one per string, mounted on the soundboard.

Source: TBD.
