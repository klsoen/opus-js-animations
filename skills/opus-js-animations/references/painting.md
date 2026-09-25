# Painting in code: stills and painterly motion

For a still image (poster, thumbnail, cover frame, a painting as the deliverable), for painted
plates inside a film, and for animation that should look painted. Every pixel comes from a
program: no image model, no off-the-shelf art software, no reference pictures. It is possible
to emulate a painter from knowledge alone. One practitioner's style-emulation engine grew to
~7,500 lines of Python on standard libraries. The starting point here is `scripts/paint.py`.

## Contents
1. Encode the painter's process, not a picture
2. Style sheets (what to write down before coding)
3. Techniques and how to code them
4. `scripts/paint.py`
5. Review: digital tells to remove
6. Painted motion
7. Paper → sketch → living painting (reveal and animation)

## 1. Encode the painter's process, not a picture

A style is a process: ground, palette, tools, the order of operations, the vocabulary of marks,
and habits of composition. Write those down and implement them as steps. Don't try to
reproduce the surface of one famous canvas. Work as the painter would: **value plan
(notan) → wash / underpainting → big masses → forms → accents → texture and varnish.**

Composition first: design a 3–4 value thumbnail (where the light is, where the eye goes), then
colour. The same scene function (`color_at(x, y)`) feeds every layer, so the layers agree.

## 2. Style sheets

Fill this in for the requested painter before writing code:

| Field | Question |
|---|---|
| Medium and ground | oil on primed canvas, acrylic on raw canvas, watercolour on cold-press paper, woodblock on washi… |
| Palette | the limited set of pigments, named, then approximate RGB (e.g. lead white, Naples yellow, raw umber, Prussian blue) |
| Marks | brush size and shape, stroke length, direction logic (follows form? flow? flat?), palette knife, dabs |
| Edges | hard, soft, lost; tape-sharp or feathered |
| Value structure | high-key, low-key, one luminous centre, flat |
| Texture | impasto, thin glaze, scumble, granulation, roller-flat |
| Composition habits | vortex, strict geometry, high horizon, framing border, off-centre tiny figure |
| Signature devices | what makes a viewer name the painter in one second |

Examples (from general knowledge):
- **Turner, late seascapes**: a vortex composition around one luminous centre; forms dissolve into
  weather; warm cream and ochre lights, grey-green and umber darks; broad scumbled sweeps and
  palette-knife impasto in the lights; rain and spray as streaks; a small dark boat with smoke
  pulled into the spiral.
- **Hockney, 1960s pool paintings**: flat acrylic fields with no modulation, tape-sharp edges; water as
  a network of wavy interlocking lines in two blues; simple modernist architecture; palms as
  flat silhouettes; an unpainted canvas border.
- **Van Gogh**: directional impasto dashes following form, complementary contrasts, outlines, a swirling sky.
- **Monet, late**: broken colour in side-by-side dabs (optical mixing), no black, soft edges, high key.
- **Ukiyo-e (Hokusai)**: flat key-block areas, Prussian blue, *bokashi* gradients, crisp keylines, claw-like wave crests.
- **Rothko**: soft-edged stacked rectangles, many thin glazes, a glowing edge where layers meet.
- **Watercolour**: pigment pools at wet edges (darker rims), granulation, preserved paper white, back-run blooms.

## 3. Techniques

| Technique | Code |
|---|---|
| Form-following strokes | trace polylines along a **flow field** (angle per pixel): vortex, noise, or the tangent of the form's contours |
| Bristle marks | across the stroke, a fixed 1D random profile interpolated over the width gives streaks parallel to the stroke |
| Paint load, dry brush | paint `= load · (1 − dry · s^1.5)` along the stroke; alpha where `bristle > 1 − paint`, so the end breaks up |
| Wet-in-wet | mix the stroke colour with the average canvas colour under its start (`pickup`) |
| Impasto | each stroke adds height (bristle ridges, raised rims); light the height map with a raking light: shade = 1 + k·(−∇h·L), plus a small specular |
| Glaze | multiply a thin transparent colour over dry layers |
| Scumble | light opaque paint dragged thin over dark: low opacity, high `dry`, big brush |
| Flat acrylic | fill shapes with one colour × (1 + 1% roller noise); edges exact |
| Line networks (pool water) | isolines of smooth noise: `abs(fract(n·k + offset) − .5) < w`, two colours at two offsets |
| Watercolour edge | darken just inside a wash's boundary: `mask − blur(mask)` > 0 |
| Pigment mixing | averaging in linear RGB looks digital; a geometric mean of reflectances (subtractive-ish) gives muddier, more painterly mixes |
| Ground and support | canvas weave (two low-amplitude sines), paper grain, an unpainted border |
| Colour variation | vary **value and temperature per stroke**, not random RGB per channel (that makes magenta/green specks) |

Coarse to fine: in the storm demo, 650 broad soft sweeps (width 6.5% of the image), then 2,600
medium strokes, then 2,600 small accents only near the focal centre. The focal centre gets the
most detail, the finest marks and the highest contrast.

## 4. `scripts/paint.py`

```bash
python3 <skill>/scripts/paint.py --demo storm --size 1080 --out storm.png   # Turner-like vortex, ~15 s
python3 <skill>/scripts/paint.py --demo pool --size 1080 --out pool.png     # Hockney-like flat acrylic, ~7 s
```
As a library: `Canvas`, `fbm`, `vortex_flow`, `noise_flow`, `palette`, `trace`, `stroke`, `lay`,
`finish`, `sketch`. `--sketch` also writes the drawing under the painting (`sketch()`: contours from
large-scale value edges; hatching only in the darker half, density by darkness, along the
painting's own flow field; cross-hatching in the darkest areas, with separate start points so lines
don't form V shapes). Write the scene as a `color_at(x, y)` over normalised coordinates, pick flow fields,
then `wash → lay (big) → lay (medium) → lay (accents, masked) → special marks (figures, rain) → finish`.
The two demos show the two ends of the range: brush-heavy with impasto vs. flat and hard-edged.

## 5. Review: digital tells to remove

Look at the whole image at thumbnail size (does the value structure read in one second?) and at
100% crops (do the marks look made by a tool?). Common tells:
- uniform stroke size and density everywhere (vary by importance; leave quiet areas quiet)
- chromatic speckle from per-channel random jitter
- perfect gradients and perfectly straight or perfectly smooth edges where the painter would be ragged
- symmetric, centred composition when the painter's habit is off-centre
- identical texture scale across the image (the support texture should be one scale, the marks another)
- black where the painter never used black (mix darks from colours)

## 6. Painted motion

- **Temporal coherence.** Re-randomising strokes each frame makes the image boil. Anchor each
  stroke to the world or an object (seeded by id, positioned in object space) and re-render it
  at that object's pose, or paint plates once and move the camera over them.
- **Intentional boil.** A hand-made feel: redraw strokes with a new seed on every 2nd or 3rd
  frame (8–12 fps), keyed to `floor(t · 12)` so it remains a pure function of time.
- **Plates.** Paint layers offline in Python with alpha (sky, far, mid, near, figure), then
  animate them in the HTML film: parallax camera moves, light passes, weather. Load them as
  textures or base64. Keep the "no asset files" constraint in mind if the brief has one; then
  port the stroke model to GLSL (instanced quads with a procedural bristle texture) instead.
- **Stills from a film.** For a thumbnail or poster from a film, `stills.mjs --times T --png`
  gives the exact frame; run a painterly pass over it only if the style calls for it.

## 7. Paper → sketch → living painting

A reference clip ("Claude Opus 5.5 drew every frame of this animation in JavaScript", 14 s,
landscape) measured frame by frame:

| Time | What happens |
|---|---|
| 0–0.8 s | blank cream paper with fine tooth |
| 0.8–2.6 s | a graphite/ink drawing of the whole scene appears in **soft-edged blotches** (not stroke by stroke), like wet media spreading: sea and horizon first, then the tree, the foreground last |
| 2.6–3.3 s | the finished drawing holds |
| 3.3–4.5 s | colour blooms in through a second set of blotches: sea and grass first, sky next, the tree last |
| 4.5–14 s | a finished plein-air oil painting that stays alive: foam lines roll to the shore, the sun path glitters, grass and tree sway; the strokes never boil |

The scene: golden hour from a high cliff; a curving bay as the leading line to far headlands; the
low sun on the left with a glitter path; a windswept pine framing the right; ochre grass on a
diagonal in the foreground. The drawing matches the painting exactly, so both come from the same
scene data, and the drawing is derived from the painting (contours + hatching, as `sketch()` does).

**Reveal: three states per pixel, two noise masks.**
```glsl
// uSketch, uPaint: 0→1 progress keyed on t. Each mask is seeded fbm plus a spatial bias
// (what should arrive first: e.g. bias = sea/horizon for the drawing, sea+grass for the colour).
float n1 = .75 * fbm(uv * 3. + 11.) + .25 * bias1(uv);
float n2 = .75 * fbm(uv * 2.4 + 37.) + .25 * bias2(uv);
float m1 = smoothstep(n1 - .05, n1 + .05, uSketch * 1.1 - .05);
float m2 = smoothstep(n2 - .05, n2 + .05, uPaint * 1.1 - .05);
vec3 col = mix(mix(paper, drawing, m1), painting, m2);
col *= 1. - .22 * (4. * m2 * (1. - m2));      // a darker wet edge at the colour front
```
Precompute `paper`, `drawing` and each painting layer once (textures or offscreen canvases); the
reveal costs only the masks per frame.

**Living painting: animate the strokes, not the pixels.** Keep the painting as stroke data
(position, angle, length, width, colour, layer, id). Static layers (sky, far hills) are rendered once to
a cached canvas. Animated layers are redrawn every frame from their strokes (WebGL2 instancing, or
Canvas 2D `drawImage` of a few pre-rendered brush sprites), with parameters that are functions of `t`:
- **Sea**: strokes shift along the wave direction by `A·sin(k·p − ωt)`; foam strokes take their alpha from
  a crest function travelling toward the shore, `pow(.5 + .5·sin(k·dShore − ωt), 8)`.
- **Sun glitter**: strokes inside the sun path twinkle by `hash(id, floor(t · 12))` (stepped, so it sparkles
  rather than flickers).
- **Grass and foliage**: `angle += wind(x, t)·tipWeight` with `wind = A·(sin(ωt + kx) + .5·sin(2.3ωt + 1.7kx))`,
  so gusts travel across the slope. Foliage clumps rotate slightly about their branch anchors; the trunk stays still.
- **Clouds**: slow drift, `x += v·t`.
Every stroke keeps its seeded identity, which is why the painting doesn't boil.

**Loop.** The reference loops by cutting from the painting back to paper. For a seamless loop, reverse
the reveal (wash back to paper) or bring the paper back in through the same masks at the end.
