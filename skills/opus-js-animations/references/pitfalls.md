# Pitfalls that cost time

| Symptom | Cause | Fix |
|---|---|---|
| `No such file` on a Desktop screen recording | macOS names contain a narrow no-break space (U+202F) before AM/PM | Glob it: `for f in ~/Desktop/Screen\ Recording*.mov; do …; done` or `ls -t … | head -1` into a quoted variable |
| `ls` output looks odd or breaks parsing | `ls` aliased (eza/lsd) | Use `/bin/ls` |
| `ffmpeg -vf "scale=$3:$4:flags=…"` fails in zsh with "Option not found" (`1920ags`) | zsh reads `$4:f…` as a modifier on `$4` | Brace every variable followed by `:`: `${3}:${4}:flags=…` |
| `ffmpeg -ss $1` fails with "Invalid duration 7.4 12.4" | zsh doesn't word-split `$var` | Loop in Python, or `set -- ${=r}` in zsh |
| Headless screenshot of a page with `OfflineAudioContext` hangs | `--virtual-time-budget` doesn't wait for audio rendering threads | Drive the page over DevTools (`scripts/lib.mjs`) and poll a result |
| `window.X is undefined` right after navigating | `Page.navigate` returns before load; you evaluated `about:blank` | Poll for `window.__film.ready` (lib.mjs does) |
| Text missing or in a fallback font on the first frames | Canvas draws before web fonts load | `await document.fonts.load(font, sample)`, set `ready` after |
| Audio silent from a `file://` page | Media element routed into Web Audio from an opaque origin | Embed base64 (`embed_audio.py`), decode with `decodeAudioData` |
| Real-time recording stutters or drops frames | Heavy frames and background-tab throttling | Export with `render.mjs` (frame-exact); real-time record only for previews |
| Flicker between frames; exported MP4 differs from stills | `Math.random()` or a frame counter in the draw path | Seeded RNG, everything from `t`; run `verify.mjs` |
| At `--ss 2` a layer comes out at double size or covers a quarter of the frame | `drawImage(canvas, x, y)` draws at the canvas's pixel size, which is now SS× | Give every baked canvas its film-pixel size: `drawImage(c, x, y, w, h)`; source rectangles in its own pixels (`delivery.md` §3) |
| At `--ss 2` shadows, glows and blurs are half as soft | `shadowBlur`, shadow offsets and `filter` lengths are canvas pixels; the transform doesn't scale them | `supersample(ctx, SS)` on the main context; inside bakes multiply them by SS yourself |
| Star/particle texture "crawls" | Noise recomputed per frame instead of pinned to objects | Seed per object; pin textures to world coordinates |
| Stars grow into blobs on zoom | Scaling coordinates without compensating size | Multiply distance² by zoom² in the star function |
| Nebula/bloom washes to grey or white | Additive emission unclamped; flat bloom term | Tone-map emission; no constant bloom term |
| Hard white/black flash at a cut | A scene's first frame differs from its settled state, or a fade overlaps wrongly | Strip-check every boundary at 1/30 s |
| Headless WebGL very slow | SwiftShader fallback | `--use-angle=metal --ignore-gpu-blocklist` on macOS; check the renderer string lib.mjs prints |
| Concat of segments fails | Relative paths in the concat list resolve against the list file | Absolute paths, `-safe 0` |
| Python string parsing of the source misses items | Delimiter appears inside content (`];` in "[above such a thing];") | Slice between known section markers |
| `sleep N && check` blocked in Claude Code | Harness blocks chained sleeps | Background command with an `until …; do sleep 2; done` loop |
| `yt-dlp` fails with "Unable to extract", 403 or signature errors | The site changed; the installed yt-dlp is stale | Update (`brew upgrade yt-dlp`, `pipx upgrade yt-dlp`, `yt-dlp -U`); `get_audio.py` does this and retries |
| `yt-dlp: command not found` / Python deprecation warning | Not installed, or installed under an old Python | `get_audio.py --install`, or the standalone binary from github.com/yt-dlp/yt-dlp/releases |
| The last word is cut off in the finished film | The downloaded section ended while the voice was still sounding | Check the tail loudness before editing (`get_audio.py` warns); download a longer section |
| A dashed line or black specks along one direction in a shader | `pow(x, y)` with x slightly negative (e.g. `.5 − .5·dot` when the dot rounds above 1) returns NaN | `pow(max(x, 0.), y)`; clamp every base |
| Final MP4 is enormous (≈60 Mbps) | Film grain barely compresses at CRF 16 | Keep the master; make an upload copy: `ffmpeg -i master.mp4 -c:v libx264 -preset slow -crf 21 -maxrate 24M -bufsize 48M -c:a copy -movflags +faststart upload.mp4` |
| Frame flashes pale during a tile flip | Many tiles edge-on at once, so the backing shows | Darken the backing during the wave, shorten the flip, widen the wave front |
| Painted image full of magenta/green specks | Random jitter per RGB channel | Jitter value (and a little temperature) per stroke |
| Stills crop misses the subject | The subject's screen position moved after reframing | Crop wide first, or compute the subject's screen position from `project()` |
| A mass of bright star-trail arcs "in the lake" | Direct stars below the horizon drawn in 2D show through water passes that are transparent (mirror setups have no opaque ground there) | Clip direct stars and trail points at `d.y > 0`; only the mirrored copies belong in the water |
| Forest looks like camouflage or square confetti | Albedo chosen per hashed grid cell | Smooth-noise contour bands, crown-gap darkening from the canopy noise, fade detail with distance (`shaders.md` §16) |
| Water drop rings read as a flat disc or bullseye | Brightness from `abs(slope)` or a wide single-wavelength packet | Signed slope toward one light direction, shorter wavelength, envelope wider than 2–3 wavelengths |
| Birds read as bow-ties | Near and far wings drawn flapping in opposite directions | Both wings beat together; the far one is a little smaller and darker |
| Flight through stars looks like warp speed or rain | Long radial streaks on every star | Cap the streak at ~9 px, fewer and finer stars, slower spline (`shaders.md` §17) |
| Faint squares around bright stars and galaxies | A glow clipped at its grid cell's border | Fade by distance to the cell edge |
| Flying into a nebula becomes a flat pink wall or pink granite | Wide veils all in front; plain high-frequency noise | Veils dissolve before the lens; world-anchored warped ridge octaves by pixel size |
| `Cannot read properties of null` while the camera looks up | A subject behind the camera: `project()` returned null | Guard every projection of the figure, feet and lamp |
| `verify.mjs` fails only on the cold jump (third hash differs) in a physics film | `draw` wrote into simulation state (e.g. forward kinematics from snapshot angles left in live positions), so a frame depends on whether earlier frames were drawn | `draw` reads snapshots only; restore anything it computes into shared fields (`styles.md` §2.13) |
| three.js film is blank; console: module blocked by CORS / `null` origin | ES modules and import maps don't load by relative path from `file://`, which the render tools use | Bundle three + addons into one IIFE script with esbuild (`threejs.md` §1) |
| Subject lands at the edge or out of a portrait frame | Portrait's horizontal fov is only ≈35° at a 58° vertical fov: a 0.3 m sideways offset at 2 m is already 8° | Aim at the subject; probe where heads land (`project()` after `seek`) before judging stills |
| 16:9 close-ups cut the head or collide with the text | The same shot at the same vertical fov is too tight in a short frame | Scale the X fov by shot size (≈0.64 for wide shots, up to ≈0.86 for close ones), and give X its own aims where needed |
| Stop-motion poses stutter 2-3-2-3 in the MP4 | poses every 5 sim frames at 60 Hz, output at 30 fps | choose `EXPO` so each pose covers whole output frames (`styles.md` §2.12), or render at 60 fps |
| Earlier frames (old captions, other shots) ghost through the picture; `verify.mjs` fails at most times | three r16x+ always creates an alpha context; a full-frame 3D canvas with alpha < 1 blends over the previous 2D frame | Patch `OutputPass` to write `vec4(rgb, 1.)` and fill the 2D canvas black before `drawImage` |
| The whole frame goes black at a few times | One NaN pixel (`pow(1. − dot, k)` with the dot rounding above 1) spread over the frame by bloom's blur chain | `pow(max(x, 0.), k)` everywhere; with bloom one speck blacks out the frame |
| A mesh silently never renders | A GLSL error in an `onBeforeCompile` patch (e.g. `mix(1., vec3, t)`); three logs it to a console the tools don't read | `R.debug.onShaderError = (gl, p, vs, fs) => window.__errs.push(gl.getShaderInfoLog(fs))`, then read `__errs` from a probe |
| Big soft white discs or haze on a glossy floor | Direct-light speculars (point, key, rim) on a smooth floor, grown into discs by DOF and bloom; three's F90 still lets a low `specularIntensity` glint at grazing angles | `specularIntensity: 0` on the lacquer with reflections from a mirror pass; IBL only on inlays (`reflectedLight.indirectSpecular *= mask`); light hands with a hand-only warm uniform, not a point light |
| A dithered-discard fade shows screen-door dots | Per-pixel dither survives DOF and grain | Real alpha on that one mesh (`transparent: true`, set `diffuseColor.a`) |
