# three.js in a motion film

Reach for this only when 3D was chosen in the direction questions (`directing.md` §4); the default look is 2D (Canvas 2D with shaders composited in).
Then use three.js when a film needs **real meshes**: a figure with a skeleton, instanced 3D leaves or needles,
props with true shadows, planar reflections of meshes, depth of field on geometry. Keep raw GLSL
(`shaders.md`) for what it does better: skies, space, raymarched landscapes kilometres deep, water
surfaces, mist. The strongest films are often hybrids: raymarched world, three.js meshes, 2D text on top.
Skip three.js for a "no libraries" brief.

## Contents
1. Loading and setup
2. The contract: seek(t) with three.js
3. Sharing the camera with the raymarched world (and the handedness trap)
4. Compositing: layers, or one scene with raymarch depth
5. Figures: rigid-part rigs, skinned meshes, GLTF
6. Instanced foliage, particles, flocks
7. Light, shadows, materials
8. Reflections in a lake
9. Post-processing
10. Performance and pitfalls
11. Assembling and scattering a world: the exploded model

## 1. Loading and setup

Pin one exact version and vendor it beside the film, so renders are reproducible offline.
Find the current version with `npm view three version`.
```bash
V=0.183.0   # the pinned version
mkdir -p film/vendor/three/addons
curl -sL https://cdn.jsdelivr.net/npm/three@$V/build/three.module.js -o film/vendor/three/three.module.js
# plus only the addons you use, keeping their paths, e.g.:
# examples/jsm/postprocessing/{EffectComposer,RenderPass,ShaderPass,MaskPass,Pass,UnrealBloomPass,BokehPass,OutputPass}.js
# examples/jsm/shaders/{CopyShader,LuminosityHighPassShader,BokehShader,OutputShader}.js
```
Addons import `'three'` by bare name, so map it in an import map:
```html
<script type="importmap">{ "imports": {
  "three": "./vendor/three/three.module.js",
  "three/addons/": "./vendor/three/addons/" } }</script>
<script type="module">
import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
...
window.__film = { duration: DURATION, ready: false, seek, shots: SHOTS, marks: MARKS };   // modules are scoped: assign to window
</script>
```
Addon files import each other by relative path (`../shaders/CopyShader.js`), so copy the `examples/jsm/` subtree
with its folder layout, or fetch whole folders. The CDN URL in the import map works too, but then every render needs the network.

**The render tools open pages from `file://`, where modules fail to load by relative path** (origin `null`, blocked by CORS), so
the import map above only works when served over http. The robust way is one classic script: bundle three and exactly the
addons you use with esbuild, then load it with `<script src>`. The film code is then a plain script reading the global `THREE`:
```bash
npm i three@$V esbuild                                 # in a work folder
cat > entry.js <<'JS'
export * from 'three';
export { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';   // …only the addons you use
export * as BufferGeometryUtils from 'three/addons/utils/BufferGeometryUtils.js';
JS
npx esbuild entry.js --bundle --format=iife --global-name=THREE --minify --outfile=film/vendor/three-$V.iife.js
```

Renderer, sized in pixels, never by the device pixel ratio:
```js
const glc = document.createElement('canvas');                     // three draws here; the 2D canvas #c is the output
const renderer = new THREE.WebGLRenderer({ canvas: glc, antialias: true, alpha: true,
  premultipliedAlpha: true, preserveDrawingBuffer: true, powerPreference: 'high-performance' });
renderer.setPixelRatio(1);                                         // headless DPR differs from a laptop's
renderer.setSize(W, H, false);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.AgXToneMapping;                       // or ACESFilmic / Neutral; set exposure per shot from t
renderer.setClearColor(0x000000, 0);                               // transparent: this is a layer
```
Colour management is on by default: `new THREE.Color('#c9a45c')` is sRGB and converted to linear.
Canvas-drawn textures need `tex.colorSpace = THREE.SRGBColorSpace`; data textures (normals, masks) don't.

## 2. The contract: seek(t) with three.js

- **No render loop owns state.** `seek(t)` sets every transform, uniform, weight and exposure from `t`, then
  calls `renderer.render(scene, camera)` (or `composer.render()`) synchronously, then composites into the 2D canvas.
  The player's `requestAnimationFrame` only calls `seek`.
- **Never** use `THREE.Clock`, `getDelta()`, `performance.now()`, `Math.random()` in draw paths, or any addon
  that integrates over frames (physics steps, `FilmPass` time, OrbitControls damping). Physics: simulate
  offline at init with a fixed step into a baked table and then look up by `t`, or solve it in closed form.
- **Animation clips**: `action.play()` once at init, then `mixer.setTime(t)` in every seek (absolute time).
  Blend clips with explicit weights from `t` (`action.setEffectiveWeight(w)`), not `crossFadeTo` (it keeps state).
- **Ready means everything is on the GPU.** Await every loader (`loadAsync`), then
  `renderer.compile(scene, camera)` (or `await renderer.compileAsync(...)`), `renderer.initTexture(tex)` for each
  texture, render one warm-up frame, and only then set `__film.ready = true`. Otherwise the first frames stall or render blank.
- `WebGPURenderer` renders asynchronously. The stills and contact-sheet tools call `seek` synchronously, so use
  `WebGLRenderer` for films.
- Run `verify.mjs` as usual: it catches hidden state (a mixer advanced by delta, a pass with its own clock).

## 3. Sharing the camera with the raymarched world

Our camera is `{ P, F, R, U, f }` (position, forward, right, up, focal length in px) in a world with x = east/right,
y = up, z = north/forward. **That world is left-handed; three.js is right-handed.** Using the same numbers
mirrors the scene left↔right. Map every point and direction with z → −z:
```js
const T = v => new THREE.Vector3(v[0], v[1], -v[2]);               // world → three
function syncCamera(cam3, cam) {
  cam3.fov = 2 * Math.atan(H / 2 / cam.f) * 180 / Math.PI;         // vertical fov from the focal length in px
  cam3.aspect = W / H;
  cam3.position.copy(T(cam.P));
  cam3.up.copy(T(cam.U));
  cam3.lookAt(T(cam.P).add(T(cam.F)));
  cam3.updateProjectionMatrix(); cam3.updateMatrixWorld();
}
```
Keep `project()` in JS for 2D elements. A mesh placed at `T(p)` then lands on the same pixel as `project(cam, p)`.
Check one known point (the figure's feet) with a still before building more.
Near and far: meshes rarely need more than `near = .05, far = 2000`. Let the raymarcher own everything beyond.
A 5 cm to 60 km range in one depth buffer z-fights (if you must, use `logarithmicDepthBuffer: true`).

## 4. Compositing

**A. Layers (when the depth order is known).** Render three.js scenes into the transparent `glc` and
`ctx.drawImage(glc, 0, 0)` at the right place in the pass order (`shaders.md` §11, §14). Several scenes can share the
renderer: set up scene A, render, draw; set up scene B, render, draw. Examples: the figure after the land pass, or the trees after the figure.

**B. One scene with the raymarch writing depth (when meshes and the raymarched world interpenetrate).**
Draw the raymarcher as a full-screen quad in the three.js scene (`ShaderMaterial`, `depthWrite: true`,
`renderOrder = -1`, `frustumCulled = false`, geometry `PlaneGeometry(2, 2)` with the vertex shader outputting clip
space directly). In the fragment shader, write the hit's depth so meshes sort against it:
```glsl
float d = tHit * dot(rd, uCamF);                                   // view-space depth along the camera axis
float zn = (uFar + uNear) / (uFar - uNear) - 2. * uFar * uNear / ((uFar - uNear) * d);
gl_FragDepth = tHit > 0. ? zn * .5 + .5 : 1.;                      // missed rays: at the far plane
```
(Standard perspective depth; this formula is wrong with `logarithmicDepthBuffer` or reversed depth.)

## 5. Figures

- **Rigid-part rig (usually enough for a clothed figure).** A `Group` hierarchy (pelvis → spine → chest →
  neck → head; shoulder → elbow → hand; hip → knee → foot). Parts are simple smooth geometry: a
  `LatheGeometry` bell for a long coat or robe (a profile of ~12 points), a `CapsuleGeometry` for each limb, a sphere for the head,
  and a short cylinder for a cap. Poses are tables of joint Euler angles. Between keyed poses, `slerp` the quaternions
  with an eased weight from `t`. Posture changes (standing → kneeling) that stretch the cloth: give the lathe
  **morph targets** (standing, kneeling, lying profiles) and set `morphTargetInfluences` from `t`.
- **Skinned mesh** when cloth must bend smoothly: `SkinnedMesh` + `Skeleton` built in code
  (`skinIndex` / `skinWeight` attributes by distance to each bone), or a GLTF.
- **GLTF models**: `GLTFLoader.loadAsync`. Check the licence: CC0 or CC-BY is simplest. Mixamo characters may be used inside a project, but not
  redistributed as standalone model files. Faceless depictions: remove or flatten facial geometry, and keep faces in shadow or turned away.
- Keep the 2D-figure rules from `design.md` §6: silhouette first, accurate postures, rim light from the key.
- **A sculpted part that must bend (a porcelain hand).** Model it as a signed-distance sum (round cones for phalanges, ellipsoids
  for the thenar pads, a rounded box for the palm, smooth-union radii 0.15–1.6 cm), polygonise once with the `MarchingCubes`
  addon (write `field = −sdf`, `isolation = 0`, 150³ over the hand's box, a rough distance outside it), `mergeVertices`,
  `computeVertexNormals`, then skin it: weight each vertex by `exp(−(d_prim − d_min)/0.22)` per primitive, summed per bone, top 4.
  Neighbouring fingers stay separate because each primitive owns one bone. Poses are joint-angle tables (open, cup, fist, press)
  mixed per frame; search the thumb's angles numerically for a fist (its tip on the curled index and middle). Place a hand by where its
  palm centre must be and which way the palm faces; add wrist flexion when the forearm must leave a wall. Fade the forearm with alpha.

## 6. Instanced foliage, particles, flocks

- `InstancedMesh(geometry, material, count)`: set `setMatrixAt(i, m)` for every instance **in every seek** from a closed-form
  function of `t` (sway = small sinusoids per clump), then `instanceMatrix.needsUpdate = true`. Per-instance colour:
  `setColorAt` + `instanceColor.needsUpdate`.
- Moving instances leave the bounding sphere computed at init and get culled: `mesh.frustumCulled = false`,
  or `computeBoundingSphere()` after the update.
- Leaves and needles: a small quad (or 2 crossed quads) with a `CanvasTexture` drawn by the sprite code of
  `shaders.md` §15. Use `alphaTest: .5` and `side: DoubleSide`. **Don't use `transparent: true`**: sorting thousands of instances fails and flickers.
  For translucency against a lamp or low sun, add an `onBeforeCompile` term that adds `lightColour · max(0, −N·L)`.
- Tens of thousands of instances are fine on an M1. Beyond ~200k, move the per-instance maths into the vertex shader
  (attributes: seed, clump, phase; uniform: `uT`), which is still a pure function of time.

## 7. Light, shadows, materials

- Drive lights from the same timeline tables as the sky (`shaders.md` §12): `sun.position = T(sunDir(t)) · 100`,
  colour and intensity from the sun's elevation, and `HemisphereLight` (sky / ground) for the ambient.
- Shadows: `renderer.shadowMap.enabled = true`, `type = THREE.PCFSoftShadowMap` (or `VSMShadowMap` for soft
  contact). For the sun, set a `DirectionalLight` with a tight orthographic shadow camera around the subject (a few metres), `mapSize`
  2048, `bias ≈ −.0005`, `normalBias ≈ .02`. Shadow acne means raising `normalBias`; floating shadows mean lowering `bias`.
  A lamp: `PointLight` with `castShadow` renders 6 faces, so keep `mapSize` at 512–1024, `decay: 2`, and a small `distance`.
- Materials: `MeshStandardMaterial` (roughness and metalness) for wood, cloth and paper; `MeshPhysicalMaterial` with
  `sheen` for cloth. A paper lantern is an `emissive` box plus a real `PointLight` inside.
- Environment light without HDR files: `PMREMGenerator.fromScene(new RoomEnvironment())` or a scene built from
  the current sky colours. Regenerate only when the light changes enough (it is costly), keyed to `t` buckets
  so the result is still a pure function of `t`.

## 8. Reflections in a lake

- **Mirror layer (matches `shaders.md` §14).** Put the meshes **and their lights** in a `Group`. For the reflection, render a
  second time with `group.scale.y = -1` (three flips the face winding automatically for a negative determinant)
  into the transparent canvas and draw it as the mirror layer at about 0.5 alpha. Lights must be mirrored too, or the reflection is
  lit from the wrong side.
- **`Reflector`** (`three/addons/objects/Reflector.js`): a plane that renders a mirrored camera into a texture;
  set `clipBias ≈ .003` and texture size = frame size. It is exact but plain: no Fresnel or ripples unless you replace its shader.
  **`Water`** (`addons/objects/Water.js`) adds a normal map and Fresnel; set `material.uniforms.time.value = t` in seek.
  Both cost one extra full scene render.

## 9. Post-processing

```js
const rt = new THREE.WebGLRenderTarget(W, H, { samples: 4, type: THREE.HalfFloatType });   // MSAA inside the composer
const composer = new EffectComposer(renderer, rt);
composer.addPass(new RenderPass(scene, cam3));
composer.addPass(new BokehPass(scene, cam3, { focus: 16, aperture: .002, maxblur: .006 }));   // focus in metres, keyed from t
composer.addPass(new UnrealBloomPass(new THREE.Vector2(W, H), .35, .6, .85));             // strength, radius, threshold
composer.addPass(new OutputPass());                                                       // tone mapping + sRGB at the end
```
- With a composer, tone mapping happens in `OutputPass`. Don't also rely on the renderer's output, or it is applied twice.
- Keep grain, vignette and text in 2D (`seek` in the template), with the grain seeded by the frame index. Don't use `FilmPass`.
- Depth of field is the pass that sells "being there". Key `focus` to the subject's distance from the camera every frame.
- Saturated emissives (amber windows, lamps) go pale under AgX, which desaturates bright values toward white. `NeutralToneMapping`
  keeps their hue; pair it with bloom at a threshold above 1 (≈1.25) so only real lights halo.
- A matte finish is a grade, too: after `OutputPass`, a `ShaderPass` that lifts blacks to a deep ink (`c = lift + (1 - lift - .03) * c`),
  cools shadows and warms lights. GTAO (`GTAOPass`, world radius ≈1 m) gives plaster models their crevices.

## 10. Performance and pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| Scene mirrored left↔right against the raymarched world | Our world is left-handed | Map z → −z (§3) |
| Meshes drift off their 2D/raymarched counterparts | fov from the wrong axis, or a DPR ≠ 1 | Vertical fov `2·atan(H/2/f)`, `setPixelRatio(1)` |
| First frames blank or stalled in renders | Shaders and textures compile lazily | `compile`, `initTexture`, a warm-up render before `ready` |
| Frame differs on a cold seek | Mixer advanced by delta, a pass with its own time, `crossFadeTo` | `mixer.setTime(t)`, weights from `t`, no clocks |
| Foliage flickers or pops | `transparent` instances sorted per frame; culling on stale bounds | `alphaTest`, `frustumCulled = false` |
| Bands on large surfaces / z-fighting far away | Huge near/far ratio | Short far plane for meshes; the raymarcher owns distance |
| Colours washed out or too dark | Double tone mapping, or a canvas texture left in linear | `OutputPass` only; `colorSpace = SRGBColorSpace` on colour textures |
| Render needs internet / differs next month | CDN `three@latest` | Vendor one pinned version (§1) |

Cost on an M1 (headless, Metal): a figure plus a few thousand instances is about 10–30 ms per frame; with soft shadows,
a mirror render, bloom and depth of field, about 60–150 ms. That's fine for `render.mjs`, but live playback may stutter.
(Measured: a city model with ~9k instances, 14 point lights, GTAO, bokeh, bloom and a half-resolution mirror, renders at 10 fps with 3 workers.)

## 11. Assembling and scattering a world: the exploded model

A city (or any object) that builds itself around the lens, or comes apart, is made of **pieces** in a few `InstancedMesh` sets
(boxes for storeys, bands, frames; a hip-roof cone; cylinders; unlit panes whose instance colour is the light).
- **A piece** has a home transform, a flight vector `d`, a tumble axis and angle, and a time window. Displacement `a(t)` is 0 at home and
  1 at the scattered place: `pos = home + d·a`, `rot = home · axisAngle(ax, ang·a)`. Gather is `a = 1 − smooth(k)`; scatter eases out
  and keeps drifting (`+ .25·(t − end)`). Recompute every matrix in `seek` from `t`.
- **Exploded, not exploded-by-a-bomb.** Random offsets read as rubble. Give it the logic of an architect's exploded view:
  storeys lift by their level (`up = 3 + level·2.3`), windows push out along their façade normal, roofs go highest, with a small
  tumble (±0.35 rad). That is legible, elegant and still dramatic, and lit panes floating between storeys are the sparkle.
- **Parts of one thing fly together.** A window's frame, pane and lintel share one flight (a `win` id), or frames half-cover
  panes and make fake letterforms.
- **Lock ahead of the lens.** Sample the hook camera path once and give each piece the time the camera reaches its z
  (plus a margin), so the world completes just before you arrive. Flash a pane's light briefly as it locks.
- **Nothing blinds the frame.** Scale a piece toward 0 when it comes within ~2 m of the camera.
- **Backs need windows too.** A flight that looks toward the water sees the city's backs: give those façades lit windows.
- A second flight vector on some pieces lets the same windows assemble in the hook and scatter later in the story.
