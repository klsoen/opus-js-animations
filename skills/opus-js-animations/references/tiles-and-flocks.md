# Tiles and flocks: figures made of many small elements

For films where the picture is built from thousands of elements that each have a home, such as mosaic
tiles, paper scraps, leaves, pixels, birds, letters or dominoes, and where figures are made by those
elements moving together: "a fish swims by its tiles swimming". Worked example at the end
(an 80 s glass and gold-leaf mosaic in WebGL2, no libraries and no asset files).

## Contents
1. The rule: flocks without simulation
2. Data per element
3. Motions: lift, fly, land, flip, wave, spiral, peel and swarm
4. Keeping figures legible
5. Rendering in WebGL2 (instancing) and materials (gold leaf, glass smalti, plaster)
6. Sound from the same data
7. Loops, square format, no-asset constraint
8. Worked example: the mosaic wall that was never glued

## 1. The rule: flocks without simulation

A boids simulation depends on history, which breaks `seek(t)`. Replace every flocking rule
with a closed-form expression of `t`:

| Flocking behaviour | Closed form |
|---|---|
| cohesion / keeping the figure's shape | each element has a fixed **formation offset** `o_i` in the figure's local frame |
| alignment / following the leader | one shared **path** `P(τ)` and heading `θ(τ)` per figure (keyed spline); element `i` samples it at `τ = t − d_i` |
| separation / individuality | small **flutter**: sum of 2–3 sines with per-element seeded frequency and phase, faded by an envelope |
| a body that swims or flaps | a travelling wave on the offsets: `o_i.y += A · sin(k·o_i.x − ω t) · taper(o_i.x)` |

```js
// element i of figure g at time t (2D wall coordinates + z toward the camera)
function flight(i, t) {
  const e = EL[i], g = FIG[e.fig], tau = t - e.delay;                // tail lags the head
  const p = g.path(tau), th = g.heading(tau), s = g.scale(tau);
  const ox = e.o[0], oy = e.o[1] + g.wave * Math.sin(g.k * e.o[0] - g.w * t) * taper(e.o[0]);
  const c = Math.cos(th), sn = Math.sin(th);
  const fl = g.flutter * (Math.sin(t * e.f1 + e.p1) + .6 * Math.sin(t * e.f2 + e.p2));
  return [p[0] + s * (c * ox - sn * oy), p[1] + s * (sn * ox + c * oy) + fl, g.z(tau)];
}
```
The formation offsets are the elements' **home positions relative to the figure's anchor on
the wall**. The figure that flies away is exactly the figure that was in the wall, so it
lands back into its own hole.

## 2. Data per element

Build once, seeded (never `Math.random()` at draw time):
- `home` (grid cell centre, with a little seeded jitter and rotation, because real mosaics are hand set and uneven)
- `faces`: day and night material ids and colours (and a star or moon flag for the night face)
- `fig` (which figure it belongs to, or none), `o` (offset in the figure frame), `delay`
- seeds: `f1, f2, p1, p2` (flutter), `tilt` (a small normal tilt, which is what makes gold mosaics glitter)
- event times derived from the timeline: `tLift`, `tLand`, `tFlip`, and so on. Store them, because the sound reads them too.

Assign figure membership by rasterising a figure silhouette (a polygon or SDF) over the grid:
cells inside belong to it. Give the figure a one-tile **outline ring** in a contrasting
material (see §4).

## 3. Motions

**Lift and land.** Blend home → flight with an eased weight `w(t)` per element, staggered by
distance from the figure's head. Lift out of the wall first (`z = sin(πw) · h` pushes
toward the camera, with slight scale-up and a shadow offset on the plaster). Then fly.
**Click back into place** with a closed-form damped spring after contact time `tc`:
```js
const settle = t => t < tc ? 0 : A * Math.exp(-7 * (t - tc)) * Math.cos(38 * (t - tc));   // overshoot + ring
```
and a tiny rotation wobble with the same envelope. The contact times are the click cues.

**Flip (day ↔ night).** `angle_i = π · ease((t − tFlip_i)/dur)`, where
`tFlip_i = t0 + |home_i − origin| / speed + jitter`, so the flip runs across the wall as a wave.
Draw the day face while `angle < π/2`, the night face after, and light it by `|cos angle|`.
While a tile is edge-on the wall behind shows. **If many tiles are edge-on at once the frame
flashes the backing colour.** Darken the backing during the wave, keep `dur` short, or
widen the wave front.

**Ripple / light sweep.** A travelling wave lifts tiles slightly:
`z += a · sin(k·|home − src| − ω t) · env`, and tilts their normals, so the glints run across the wall.

**Spiral release.** In polar coordinates about the centre: `φ(t) = φ_i + Ω(r_i) · g(t)`,
`r(t) = r_i · (1 + e·g(t))`. Use **differential rotation** (inner faster, e.g. `Ω ∝ r^-0.6`),
because with uniform rotation the spiral arms don't show. Snap back **from the centre outward**:
`tReturn_i = t0 + r_i / speed`.

**Peel and swarm into a constellation.** Assign star tiles to target points with a
deterministic assignment (greedy nearest, or Hungarian in a build step) so paths don't cross.
Travel on a Bézier from home to target with a lift. Swarm flutter is large at mid-flight and
zero on arrival. Draw constellation lines only after the stars settle, and fade them in.

## 4. Keeping figures legible (lessons from review)

- **Contrast with the ground.** A gold fish on a gold wall read as a blob. Make figures a
  different material (copper and orange glass) with a one-tile outline in a contrasting colour (blue).
- **Formation beats flutter.** When the flock was loose and fluttered a lot, the figure dissolved.
  Hold offsets tighter and reduce flutter so each figure keeps its shape in flight. Put the life
  into the path and the body wave instead.
- **Light must not wash out the symbols.** A moving light's reflections were washing out the
  sun and moon, so make reflections tighter (higher exponent) and weaker.
- **Background texture stays quiet.** Plaster stripes with too much contrast competed with the tiles. Tone them down.
- Check a frame-by-frame strip of every flip and every landing (`stills.mjs --range a:b:0.0333`).

## 5. Rendering in WebGL2

JS computes per-element state each frame (a few thousand elements is trivial), and the GPU draws
instanced quads and does the materials.

```js
const gl = cv.getContext('webgl2', { antialias: true, preserveDrawingBuffer: true });  // preserve: capture tools read the canvas
const vao = gl.createVertexArray(); gl.bindVertexArray(vao);
const inst = new Float32Array(N * 12), ib = gl.createBuffer();
gl.bindBuffer(gl.ARRAY_BUFFER, ib); gl.bufferData(gl.ARRAY_BUFFER, inst.byteLength, gl.DYNAMIC_DRAW);
for (let k = 0; k < 3; k++) {                         // 3 × vec4 per instance: pos.xyz+size, rot axis.xy+angle+face, material ids/seeds
  gl.enableVertexAttribArray(k); gl.vertexAttribPointer(k, 4, gl.FLOAT, false, 48, k * 16); gl.vertexAttribDivisor(k, 1);
}
// seek(t): fill inst from the closed forms, gl.bufferSubData(gl.ARRAY_BUFFER, 0, inst);
//          draw the plaster (full-screen pass), then the shadows (instanced, offset, dark, soft alpha),
//          then the tiles: gl.drawArraysInstanced(gl.TRIANGLE_STRIP, 0, 4, N)
```
The vertex shader builds the quad corner from `gl_VertexID` (`vec2(gl_VertexID & 1, gl_VertexID >> 1) - .5`),
rotates it by the flip angle about the tile's axis (a real 3D rotation, so edge-on tiles get thin),
and applies a mild perspective from `z`. Enable the depth test, or sort flying tiles by `z`.

Materials (fragment shader), each tile with its own seeded values:
- **Gold leaf**: base `(1.0, .78, .34)`, a faint crackle (cell-noise lines), and a **per-tile
  normal tilt** of a few degrees. As the light moves, tiles light up individually, which is the
  shimmer of real gold mosaics. Specular `pow(max(dot(R, V), 0.), 60.)` plus a broad sheen.
- **Glass smalti**: saturated colour, darker core with a brighter rim (thickness), a few tiny
  bubbles (dots), a slightly irregular edge (noise on the quad's alpha), and a sharp small highlight.
- **Night face**: navy glass, silver tiles for stars (a brighter, cooler specular), a moon built from tiles.
- **Plaster / grout**: warm lime, low-contrast trowel texture, darker in the gaps. Tiles cast soft
  shadows on it when they lift.

## 6. Sound from the same data

All synthesized in Web Audio. For export, render offline with `OfflineAudioContext` into a WAV and
mux it (`references/audio.md` §5).
- **Clicks at every landing**: one short filtered noise burst + a tiny high sine per contact time,
  pitch seeded per tile, panned by screen x. Merge contacts within ~15 ms into one louder click
  (gain ∝ √count), or a mass landing turns into mush.
- **Shimmer** under the light sweep (a few high partials with slow tremolo), and a **chord pad**
  that swells during the spiral and resolves at the snap back.
- The clicks read their times from the element table, so retiming the picture retimes the sound.

## 7. Loops, square format, no-asset constraint

- 1080×1080 for a square post. For a loop, make the last frame's state equal the first and
  end on a small gesture (one last tile flips) before the fade.
- "No image, font or audio files": everything procedural. Text, if any, is built from tiles or
  drawn paths; system fonts only if the brief allows.
- WebGL-only films still follow the contract: `seek(t)` draws synchronously and the canvas uses
  `preserveDrawingBuffer: true`, so `stills.mjs` and `render.mjs` can read it.

## 8. Worked example: the mosaic wall that was never glued

Brief: 80 s, square, one HTML file, WebGL2 + plain JavaScript, no libraries, no image/font/audio
files. A glass and gold-leaf wall mosaic whose tiles were never glued down, so they can lift,
flip, fly and click back into place. Figures are flocks of tiles.

| Time | What happens |
|---|---|
| 0–8 s | A light sweeps across the gold wall; ripples run through the tiles |
| 8–21 s | The fish's tiles lift off and swim as a flock, leap, dive into the sea, and land back in place |
| ~21–34 s | Two cranes and a dove fly out of the wall the same way |
| 34–40 s | A wave flips every tile to its night face: navy glass, silver stars, a moon |
| 40–58 s | The stars peel off and swarm into a constellation |
| 58 s | A second wave flips the wall back to day |
| 63–72 s | The whole wall lets go into a spiral, then snaps back from the centre outward |
| 75 s | One last tile flips; fade out and loop |

Sound: a chord pad that swells during the spiral, a shimmer, and a small click whenever a tile lands.

Changes after watching it frame by frame: the fish went from gold to copper and orange glass
with a blue outline (it was a blob on the gold wall). The flocks were held tighter with less
flutter. The light's reflections were made tighter and weaker (they washed out the sun and moon).
The plaster stripes were toned down. The spiral got differential rotation so its arms show.

Still rough: the sky looks pale for about a second during the day-to-night flip, while the
tiles are edge-on (the backing shows, see §3). The night sea is close to black and needs a little teal.
