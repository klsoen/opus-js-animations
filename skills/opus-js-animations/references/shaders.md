# Shaders and render recipes

Tested recipes from finished films. WebGL1 GLSL (works everywhere), one full-screen
fragment shader whose features are switched by uniform weights, drawn into an offscreen
WebGL canvas and composited into the 2D canvas with `ctx.drawImage(glCanvas, 0, 0)` each
frame. The 2D canvas stays the single output that tools capture.

## Contents
1. WebGL boilerplate
2. Noise
3. Starfield (fixed star size under zoom)
4. Milky Way band
5. Nebula (domain-warped)
6. Spiral galaxy
7. Deep field and cosmic web
8. Planet with terminator, clouds, city lights, atmosphere
9. Sky gradient, sun, bloom, tone mapping
10. 2D recipes: rim light, glow sprites, diffraction spikes, grain, vignette
11. Raymarched terrain (dunes) and two-pass compositing
12. Sky driven by the sun's elevation
13. Star catalog in 2D: fixed pixel size, exact trails
14. Mirror lake: water, reflections, and what sits between the passes
15. Trees and foliage as lit sprite layers
16. Mountains, forests, mist
17. A journey through the universe: flight on layers (stars → nebula → galaxies → cosmic web → home)

## 1. WebGL boilerplate

```js
const glc = document.createElement('canvas'); glc.width = W; glc.height = H;
const gl = glc.getContext('webgl', { preserveDrawingBuffer: true, antialias: false });
const prog = (() => {
  const sh = (type, src) => { const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s);
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s)); return s; };
  const p = gl.createProgram();
  gl.attachShader(p, sh(gl.VERTEX_SHADER, 'attribute vec2 a; void main(){ gl_Position = vec4(a, 0., 1.); }'));
  gl.attachShader(p, sh(gl.FRAGMENT_SHADER, FRAG)); gl.linkProgram(p); gl.useProgram(p);
  gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer());
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);  // one big triangle
  const loc = gl.getAttribLocation(p, 'a'); gl.enableVertexAttribArray(loc); gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
  gl.viewport(0, 0, W, H); return p;
})();
const ULOC = {};
function uni(name, ...v) { if (!(name in ULOC)) ULOC[name] = gl.getUniformLocation(prog, name); gl['uniform' + v.length + 'f'](ULOC[name], ...v); }
// per frame: set uniforms, gl.drawArrays(gl.TRIANGLES, 0, 3); ctx.drawImage(glc, 0, 0);
```

In the shader use canvas coordinates: `vec2 fc = vec2(gl_FragCoord.x, uRes.y - gl_FragCoord.y);`
Gate each feature: `if (uMilky.x > .001) { ... }` so unused features cost nothing.

## 2. Noise

```glsl
float h12(vec2 p){ vec3 p3 = fract(vec3(p.xyx) * .1031); p3 += dot(p3, p3.yzx + 33.33); return fract((p3.x + p3.y) * p3.z); }
vec2 h22(vec2 p){ vec3 p3 = fract(vec3(p.xyx) * vec3(.1031, .1030, .0973)); p3 += dot(p3, p3.yzx + 33.33); return fract((p3.xx + p3.yz) * p3.zy); }
float vn(vec2 p){ vec2 i = floor(p), f = fract(p); vec2 u = f * f * (3. - 2. * f);
  return mix(mix(h12(i), h12(i + vec2(1., 0.)), u.x), mix(h12(i + vec2(0., 1.)), h12(i + vec2(1., 1.)), u.x), u.y); }
const mat2 M2 = mat2(1.6, 1.2, -1.2, 1.6);
float fbm(vec2 p){ float v = 0., a = .5; for (int i = 0; i < 6; i++){ v += a * vn(p); p = M2 * p + vec2(1.7, 9.2); a *= .5; } return v; }
float fbm4(vec2 p){ float v = 0., a = .5; for (int i = 0; i < 4; i++){ v += a * vn(p); p = M2 * p + vec2(1.7, 9.2); a *= .5; } return v; }  // cheaper, for large areas
```

## 3. Starfield

Stars live in pixel-sized cells; `k` is the zoom so stars spread apart but keep their
pixel size (swelling stars look cheap).

```glsl
vec3 starL(vec2 p, float cell, float prob, float seed, float k){
  vec2 id = floor(p / cell); float h = h12(id + seed);
  if (h > prob) return vec3(0.);
  vec2 d = p - (id + .5) * cell - (h22(id + seed * 1.37) - .5) * cell * .7;
  float b = pow(h12(id + seed * 2.11), 8.);                       // few bright stars
  float tw = .75 + .25 * sin(uT * (1.1 + 2. * h12(id + seed * 4.7)) + h * 50.);
  float r2 = dot(d, d) * k * k;
  vec3 tint = mix(vec3(.72, .82, 1.), vec3(1., .86, .66), h12(id + seed * 6.3));
  return tint * (exp(-r2 / (.4 + 2.2 * b)) * (.25 + 1.6 * b) + b * exp(-sqrt(r2) / (1.5 + 5. * b)) * .5) * tw;
}
// p = (fc - uRes*.5) / zoom + uRes*.5 - offset;
// stars = starL(p, 9., .2, 1., zoom) + starL(p, 19., .4, 2., zoom) + starL(p, 40., .55, 3., zoom) * 1.2;
```

## 4. Milky Way band

```glsl
vec3 milky(vec2 fc, out float dust){   // uMilky = (weight, zoom, offX, offY)
  vec2 p = (fc - uRes * .5) / uMilky.y - uMilky.zw;
  vec2 dir = normalize(vec2(.5, 1.)), nr = vec2(-dir.y, dir.x);
  float v = dot(p, nr) / 430., u = dot(p, dir) / 700.; vec2 q = vec2(u, v);
  float n = fbm(q * vec2(1.6, 3.2) + 3.1);
  float band = exp(-v * v * 2.) * (.3 + 1.8 * n * n);
  float core = exp(-v * v * 6.) * smoothstep(-1.8, 1.2, u);
  dust = clamp(smoothstep(.46, .72, fbm(q * vec2(2.4, 7.5) + vec2(7., 1.))) * exp(-v * v * 9.) * 1.1, 0., .9);
  vec3 c = vec3(.42, .52, .92) * band * .32 + vec3(1., .8, .58) * core * n * .55;
  return c + starL(p, 4., .45, 21., uMilky.y) * band * 1.5;
}
// composite: col *= 1. - dust * w * .5; E *= 1. - dust * w * .8; E += m * w;
```

## 5. Nebula

```glsl
vec3 nebula(vec2 fc, out float dark){  // uNeb = (weight, zoom, driftX, driftY); zoom up = fly in
  vec2 p = (fc - uRes * .5) / (uNeb.y * 460.) + uNeb.zw;
  vec2 q = vec2(fbm(p + vec2(0., uT * .01)), fbm(p + vec2(5.2, 1.3)));
  vec2 r = vec2(fbm(p + 3.5 * q + vec2(1.7, 9.2)), fbm(p + 3.5 * q + vec2(8.3, 2.8) + uT * .012));
  float f = fbm(p + 3. * r);
  vec3 c = vec3(.95, .22, .45) * smoothstep(.35, .95, f) * 1.3            // H-alpha magenta
         + vec3(.12, .62, .86) * smoothstep(.35, .95, length(q) * .78) * .9 // O-III teal
         + vec3(1., .72, .4) * pow(smoothstep(.5, 1., r.x), 2.) * 1.3       // warm
         + vec3(1., .95, .85) * pow(smoothstep(.62, .9, f), 3.) * .45;      // hot cores (keep low)
  c *= smoothstep(.22, .7, f) * .85;
  dark = smoothstep(.5, .74, fbm(p * 2.3 + r * 1.5 + 11.));
  return c * (1. - dark * .85);
}
```

## 6. Spiral galaxy

```glsl
vec3 galaxy(vec2 fc, out float dark){  // uGal = (weight, radiusPx, rotation, inclination≈.42); uGalC = centre
  vec2 p = (fc - uGalC) / uGal.y; float cs = cos(uGal.z), sn = sin(uGal.z);
  p = mat2(cs, sn, -sn, cs) * p; p.y /= uGal.w;
  float r = length(p), a = atan(p.y, p.x);
  float sp = a - log(r + .02) * 2.4 + uT * .03;                 // logarithmic spiral
  float arm = pow(.5 + .5 * cos(2. * sp), 2.5);
  float disk = exp(-r * 3.3);
  float d = disk * (.22 + 1.6 * arm * (.45 + .9 * fbm(p * 7. + vec2(3., 1.))));
  dark = clamp(pow(.5 + .5 * cos(2. * (sp + .5)), 8.) * smoothstep(.05, .22, r) * exp(-r * 2.4) * .9, 0., .85);
  vec3 col = vec3(.5, .66, 1.) * d * 1.3
           + vec3(1., .86, .62) * (exp(-r * r * 60.) * 2.2 + exp(-r * 6.5) * .5)            // bulge
           + vec3(1., .38, .6) * smoothstep(.72, .92, fbm(p * 22. + 9.)) * arm * disk * 3.2; // HII knots
  col += vec3(.9, .95, 1.) * step(.988, h12(floor(p * 240.))) * d * 2.4 * smoothstep(300., 1100., uGal.y);
  return col * (1. - dark) + vec3(.35, .45, .8) * exp(-r * 1.6) * .07;
}
```
Zoom out by shrinking `uGal.y` geometrically (e.g. 3400 → 700 → 280 → 215 px).

## 7. Deep field and cosmic web

```glsl
vec3 deep(vec2 fc){   // uDeep = (weight, zoom, webStrength, _)
  vec2 p = (fc - uRes * .5) / uDeep.y, wq = p / 560.;
  float w1 = fbm4(wq * 1.2 + vec2(2., 7.)), w2 = fbm4(wq * 2.5 + vec2(9., 3.));
  float web = pow(1. - abs(2. * w1 - 1.), 8.) + .5 * pow(1. - abs(2. * w2 - 1.), 10.);   // ridged filaments
  vec3 col = (vec3(.52, .38, 1.) * .24 * uDeep.z + vec3(.22, .28, .7) * .04) * web;
  for (int l = 0; l < 3; l++){
    float fl = float(l), cell = 48. + fl * 40.; vec2 id = floor(p / cell);
    vec2 d = p - (id + .5) * cell - (h22(id + fl * 13.1) - .5) * cell * .75;
    if (h12(id + fl * 7.7) < .22 + web * 1.1 * uDeep.z){         // galaxies gather on the filaments
      float ang = h12(id + fl * 3.3) * 6.283, c = cos(ang), s = sin(ang);
      d = mat2(c, s, -s, c) * d; d.y /= mix(.22, 1., h12(id + fl * 4.4));
      float rr = length(d) / (mix(1.1, 8., pow(h12(id + fl * 5.5), 4.)) * (1. + fl * .5));
      vec3 tint = h12(id + fl * 9.9) > .5 ? vec3(.65, .76, 1.) : vec3(1., .8, .56);
      col += tint * (exp(-rr * rr * 2.) + .3 * exp(-rr * 1.3) * step(.5, h12(id + fl * 8.8))) * (.6 + web * .9);
    }
  }
  return col;
}
```
Raising `webStrength` over a few seconds makes structure "emerge": a strong image for order.

## 8. Planet

```glsl
vec4 planet(vec2 fc){  // uPlanet = (weight, radiusPx, cx, cy); uLight = unit vector (x right, y up, z to viewer)
  vec2 d = (fc - uPlanet.zw) / uPlanet.y; float r2 = dot(d, d), r = sqrt(r2);
  vec3 L = uLight; float back = max(-L.z, 0.);
  vec2 dn = r > 0. ? d / r : vec2(0.);
  float side = max(dot(normalize(vec3(dn.x, -dn.y, 0.)), L) + .3, 0.) + back * 1.4;
  if (r > 1.) return vec4(vec3(.35, .6, 1.) * exp(-(r - 1.) * uPlanet.y / 34.) * side * .8, 0.);  // halo
  float z = sqrt(1. - r2); vec3 n = vec3(d.x, -d.y, z); float diff = dot(n, L);
  float lon = atan(n.x, n.z) + uSpin, lat = asin(clamp(n.y, -1., 1.)); vec2 uv = vec2(lon * 1.7, lat * 3.1);
  float hgt = fbm(uv * 1.3 + 2.), land = smoothstep(.49, .56, hgt);
  vec3 ocean = mix(vec3(.008, .035, .11), vec3(.03, .12, .27), smoothstep(.3, .5, hgt));
  vec3 grd = mix(vec3(.1, .18, .08), vec3(.4, .33, .22), smoothstep(.4, .7, fbm(uv * 3.1 + 7.))) * (.75 + .35 * fbm(uv * 9. + 3.));
  vec3 surf = mix(mix(ocean, grd, land), vec3(.92), smoothstep(1.15, 1.3, abs(lat)));   // ice caps
  float cl = smoothstep(.5, .82, fbm(uv * 2.4 + vec2(uT * .015, 0.) + 10.));
  surf = mix(surf, vec3(.92, .94, .97), cl * .7);
  float day = max(diff, 0.);
  vec3 lit = surf * (day * 1.15 + .012);
  lit = mix(lit, vec3(.42, .62, 1.) * day, pow(1. - z, 1.6) * .38);                     // haze toward the limb
  lit += vec3(1., .9, .75) * pow(max(dot(reflect(-L, n), vec3(0., 0., 1.)), 0.), 40.) * (1. - land) * (1. - cl) * .5 * day;  // sea glint
  lit += vec3(1., .72, .38) * land * (1. - cl) * step(.965, h12(floor(uv * 220.))) * smoothstep(.5, .7, fbm(uv * 5. + 1.)) * smoothstep(.12, -.1, diff) * 1.3;  // cities at night
  float rim = pow(1. - z, 2.4);
  lit += vec3(.35, .6, 1.) * rim * (smoothstep(-.35, .45, diff) + back * 1.8) * 1.2;    // atmosphere, glows when backlit
  lit += vec3(1., .55, .3) * rim * exp(-diff * diff * 30.) * .45;                       // sunset band on the terminator
  return vec4(lit, smoothstep(1., .996, r));
}
```
Day and night: rotate `uLight` around the vertical axis (`L = (sin a, .28, cos a)`); at
`a≈π` the planet is backlit, a dark disc with a blue ring. Add a 2D sun flare at the limb
then. Dive: grow the radius exponentially while holding one surface point fixed on screen.

## 9. Sky, sun, bloom, tone mapping

```glsl
float y = fc.y / uHorY;                       // horizon pixel row
vec3 col = mix(mix(uSkyTop, uSkyMid, smoothstep(0., .62, y)), uSkyHor, smoothstep(.55, 1.02, y));
vec3 E = vec3(0.);                            // accumulate emission: stars, galaxies, glows
// sun: disc + two-scale glow; the land drawn later occludes it below the horizon
float dd = length(fc - uSun.xy);
E += uSunCol * (exp(-dd / 220.) * .5 + exp(-dd / 60.) * .7) * uSun.z;
col = mix(col, mix(uSunCol, vec3(1.), .65), smoothstep(uSun.w + 1.5, uSun.w - 1.5, dd) * uSun.z);
col += E / (1. + E * .38);                    // soft tone map: glows never clip to flat white
```
Sky palettes: keyframe named palettes (`space, night, predawn, dawn, day, golden, dusk,
ember, morning`), each with sky stops, ground, glow (rim) colour, ambient cloth colour,
star amount and light level, and interpolate everything between keys. Drive the sun along
an arc `[cx + sin θ·640, horizon + 220 − cos θ·1180]` with θ keyframed linearly.

## 10. 2D recipes

**Rim light** (outline glow on the light-facing edge of any drawn object):
```js
function rimLayer(draw, rimCol, dx, dy, strength) {   // dx,dy = direction AWAY from the light, ~3 px
  ra.clearRect(0, 0, S, S); draw(ra);                              // the object, in its colours
  rb.clearRect(0, 0, S, S); rb.globalCompositeOperation = 'source-over'; rb.drawImage(RA, 0, 0);
  rb.globalCompositeOperation = 'source-in'; rb.fillStyle = rimCol; rb.fillRect(0, 0, S, S);   // silhouette in rim colour
  rb.globalCompositeOperation = 'destination-out'; rb.drawImage(RA, dx, dy);                    // keep only the lit edge
  ra.globalCompositeOperation = 'source-atop'; ra.globalAlpha = strength; ra.drawImage(RB, 0, 0);
  ra.globalAlpha = 1; ra.globalCompositeOperation = 'source-over';
  return RA;                                                        // drawImage onto the frame
}
```
**Glow sprites**: pre-render radial gradients once (`128²`), draw with
`globalCompositeOperation = 'lighter'`. **Diffraction spikes**: six thin tapered triangles at
60° plus two short horizontals, additive. **Grain**: three 256² noise patterns at alpha ≤ 10,
offset by the frame index derived from t (`f = round(t*30)`), never a running counter.
**Vignette**: pre-rendered radial gradient to ~0.4 black.

Performance: a 1080×1920 frame with these shaders renders in 30–400 ms on an Apple M1 GPU
in headless Chrome with `--use-angle=metal`; without GPU (SwiftShader) it can be 10× slower.

## 11. Raymarched terrain (dunes) and two-pass compositing

A heightfield `terrain(xz)` in metres, raymarched per pixel. A real 3D camera (yaw, pitch,
focal length in px) lets the same world serve a telephoto portrait, a tilt up to the sky and a wide end.
```glsl
float fieldH(vec2 p){   // transverse dunes: gentle windward slope toward the camera, sharp crest, steep slip face
  vec2 q = vec2(.94 * p.x + .34 * p.y, -.34 * p.x + .94 * p.y);
  float w = q.y + 9. * sin(q.x * .017 + 1.) + 4. * sin(q.x * .043 + 2.);   // meandering crest lines
  float s = fract(w / 125.);
  float pr = s < .74 ? pow(s / .74, 1.4) : pow(1. - (s - .74) / .26, 1.6);
  return pr * 15. * (.55 + .45 * sin(q.x * .006)) + 11. * (sin(p.x * .0016 + 1.3) * sin(p.y * .0012 + .4) + 1.);
}
float terrain(vec2 p){ float d = length(p);
  return fieldH(p) * smoothstep(70., 420., d) + heroH(p) - d * d / 12.742e6; }   // hero dune + earth curvature
float march(vec3 ro, vec3 rd, out float mk, out float mt){   // mk: closest approach in pixels (for edge AA)
  float t = .3, lt = .3; mk = 1e9; mt = 0.;
  for (int i = 0; i < 420; i++){
    vec3 p = ro + rd * t; float dh = p.y - terrain(p.xz);
    if (dh < 0.){ float a = lt, b = t;                                     // bisection refine
      for (int j = 0; j < 7; j++){ float m = .5 * (a + b); vec3 q = ro + rd * m; if (q.y - terrain(q.xz) < 0.) b = m; else a = m; }
      return b; }
    float k = dh / (t / uF); if (k < mk){ mk = k; mt = t; }
    if ((p.y > 60. && rd.y >= 0.) || t > 12000.) break;
    lt = t; t += max(dh * .55, .012 * t);                                   // relative min step keeps far rays affordable
  }
  return -1.;
}
```
- **Near-miss antialiasing**: a ray that passes within half a pixel of the surface gets partial
  alpha `1 − clamp(mk · .8, 0, 1)` and the colour at `mt`, which gives a soft silhouette.
- Normal by central differences with `e = max(.02, t · .0012)`; wind ripples as a normal
  perturbation that fades out when a ripple is under ~3 px (`t / uF` = metres per pixel).
- Soft shadows toward the sun (`res = min(res, 12 · dh / s)`), only when the sun is up.
- Lighting: `key · max(n·L, 0) · shadow + fill (twilight glow from the sun's azimuth) + ambient (sky)`;
  aerial perspective `mix(col, horizonSky, 1 − exp(−t / 2600))`.
- **Hero element**: a hand-shaped mound (asymmetric Gaussian ridge, crest curving away) mirrored in JS
  so a 2D figure can be planted on its crest with `project()`.
- **Two passes with 2D in between**: draw the sky pass (`uMode = 0`, opaque) → `drawImage` →
  2D stars and trails → the terrain pass (`uMode = 1`, alpha 0 where the ray misses,
  premultiplied) → `drawImage` → figure and text. The terrain covers the stars exactly.
  Use `getContext('webgl', { alpha: true, premultipliedAlpha: true, preserveDrawingBuffer: true })`.
- Cost: ~0.1–0.2 s per 1080×1920 frame on an M1 in headless Chrome (Metal).

## 12. Sky driven by the sun's elevation

Drive everything from one number: the sun's elevation. A table keyed on elevation holds zenith,
horizon-toward-sun and horizon-away colours (display hex, converted to linear once). A few
more tables hold belt-of-Venus weight, sun-glow amount, key light intensity and colour, twilight fill and star
visibility. Interpolate linearly by elevation; the sun's position comes from an hour angle
keyed on film time (a spline, so a time-lapse can accelerate and settle).
```glsl
vec3 skyCol(vec3 d){
  float e = max(d.y, 0.);
  vec2 sx = normalize(uSun.xz + 1e-5), dx = normalize(d.xz + 1e-5);
  float cs = dot(sx, dx);
  float ws = pow(clamp(.5 + .5 * cs, 0., 1.), 2.), anti = pow(max(.5 - .5 * cs, 0.), 1.5);   // clamp: pow(neg) = NaN
  vec3 col = mix(mix(uHorA, uHorS, ws), uZen, 1. - exp(-e * 4.5));
  col += uHorS * ws * exp(-e * 18.) * .35;                                  // low glow on the sun side
  col = mix(col, uShad, uBeltW * anti * (1. - smoothstep(0., .05, e)));    // earth shadow
  col += uBelt * uBeltW * anti * exp(-pow((e - .09) / .05, 2.));           // belt of Venus
  float mu = max(dot(d, uSun), 0.);
  return col + uGlow * (pow(mu, 6.) * .25 + pow(mu, 60.) * .5 + pow(mu, 900.) * 1.2);
}
```
Sun path: `dir(h) = cos(h)·EAST + sin(h)·(cos(lat)·UP + sin(lat)·SOUTH)` (h = 0 at sunrise).
A pre-dawn "ember" term (deep red, low, toward the sun's azimuth) gives a restrained fire image.
Figures take their colours from the same light (ambient, key by facing, and a rim when backlit),
so they sit in the scene.

## 13. Star catalog in 2D: fixed pixel size, exact trails

Stars as a seeded catalog in polar coordinates around the celestial pole: `(ρ, θ, brightness b = u^6.5)`.
World direction `P cos ρ + (Q1 cos(θ + rot) + Q2 sin(θ + rot)) sin ρ`, projected with the same
camera as the shader, drawn as small pre-rendered glow sprites (radius `1.7 + 6√b` px, fixed
under zoom). Sky rotation `rot(t)` is a spline: fast in a time-lapse, near zero in real time.
- **Motion blur**: draw the arc from `rot(t − 1/30)` to `rot(t)`, alpha ÷ length.
- **Star trails**: draw the arc from `rot(T0)` to `rot(t)`, as polylines of projected points
  (a segment every ~12 px). Batch into one `Path2D` per (tint, alpha level) so thousands of arcs cost
  about 30 strokes. Draw only the brighter stars (alpha `.5 · b^1.5`, skip < .06); trailing every
  star makes grey moiré.
- Full circles on a cue: make `rot` advance exactly 2π between `T0` and the cue.
- A brightness wave (`1 + 1.6·exp(−((ρ/ρmax − w)/.07)²)`) running outward through the rings gives a quiet "glory" beat.
- The stars sit between the sky pass and the terrain pass (§11), so the land hides them.

## 14. Mirror lake: water, reflections, and what sits between the passes

From "Kagami" (a lake so still that sky, trails, trees and a lamp all appear twice). The lake is the plane y = 0.
One shader, three passes, with 2D layers between them:
1. **Pass 0 (opaque)**: the sky for `rd.y ≥ 0`. For `rd.y < 0`, the water: `pw = ro + rd·tw` with `tw = −ro.y/rd.y`,
   a normal from the ripple gradient, `rr = reflect(rd, n)`, `col = body·(1−F) + fullSky(rr)·F`.
   The moon, the sun disc, the Milky Way and a point-light glint (`pow(dot(rr, lampDir), 900)`) all reflect for free.
2. **2D**: the sky's stars and trails **clipped at the horizon** (`d.y > 0`). Then their mirror image: the direction `(x, −y, z)`,
   nudged by the ripple slope at the water point the view ray hits (below).
3. **Pass 1 (alpha)**: reflections of the land and the deck. March the reflected ray from `pw`. Where it hits,
   output opaque `body·(1−F) + land·F`; where it escapes to the sky, output alpha 0, so passes 0 and 2D show through.
4. **2D**: mirrored near objects (trees, figure, lamp glow, birds). Project `mirror(p)`, flip the sprite vertically,
   draw at about 0.5 alpha. Horizontal strip offsets `sin(y·.09 + t·1.7)` make the figure's image ripple.
5. **Pass 2 (alpha)**: direct land and deck. Over open water, output only premultiplied mist (`rgb·a, a`), so
   everything reflected in 1–4 stays visible under the mist.
6. **2D**: direct near objects, text, grade.

- **Ripples shared by the shader and JS**: a few deep-water swells (`ω = √(g·k)`, amplitude ~1 mm, each faded out when its
  wavelength is under a few pixels: `fp = t / f / max(−rd.y, .03)`) plus ring packets for drops, as a `vec4 uDrops[12]`
  (x, z, t0, strength). JS computes the same gradient to move the reflected stars:
  `m' = m + 2·(m.y·tilt − (m·tilt)·up)` with `tilt = (−gx, 0, −gz)`.
- **Ring packet**: `front = .26·age`, `u = (r − front)/(.12 + .08·age)`, `slope = e^{−u²}·e^{−age/2}/√(1+3r) · 80·cos(80(r − front))·.0022`.
  At night rings are invisible in a uniform sky reflection. Add `skyColour·clamp(3·dot(gDrops, dir), −.1, .55)`, which lights one flank
  of each crest and gives fine concentric silver rings. With `abs(slope)` instead, the rings read as a flat disc.
- **Reflectance**: art-direct a floor, `F = floor + (1 − floor)·schlick`. A high floor (0.55) makes a black mirror for a
  looking-down opening; use about 0.2 for the rest. Reflected star **trails** need their own, lower curve
  (`.8·(.08 + .92·schlick(sin el))`) so the mirrored rings are strong near the horizon and fade toward the bottom of the frame.
- **Mirror composition**: stars are at infinity, so their image is symmetric about the horizon line from any camera
  height. Pin the pole about 400 px above the horizon (`f ≈ 1000`) and both wheels fit the portrait frame.

## 15. Trees and foliage as lit sprite layers

A tree is branch polylines `[x, y, z, radius]` plus clumps (ellipsoids). Each clump is filled at init with seeded elements
(position on the shell with a top bias, size, sprite index, a brightness tier from the up-facing component).
Sprites: pine = fans of 46 curved needles; maple = clusters of 6 seven-lobed leaves; each drawn at 3 tiers (1, .68, .42).
Per frame: project, cull, sort far → near, and `setTransform(cos·k, sin·k, −sin·k, cos·k, x, y)` for each element.
Lighting, with two offscreen layers, costs a few full-frame composites:
```js
la.clearRect(...); drawAlbedo(la);                                   // sprites at "unit light"
lb.globalCompositeOperation = 'copy'; lb.drawImage(LA, 0, 0);
lb.globalCompositeOperation = 'multiply'; lb.fillStyle = rgba(lightFactor); lb.fillRect(0, 0, W, H);   // lightFactor = (amb+key+fill)^(1/2.2)
lb.globalCompositeOperation = 'lighter';  /* radial gradients: lamp glow through the leaves */
lb.globalCompositeOperation = 'destination-in'; lb.drawImage(LA, 0, 0);                              // back to the albedo's alpha
```
The mirrored tree uses the same list with `mirror(p)` and one tier darker. Sway: one small sinusoid offset per clump.

## 16. Mountains, forests, mist

- **Volcanic cone**: `h = H·(1 − r/R)^2.3`, capped a little below H with a crater dip. Gullies: `vn(atan·26, x·6)` ridged,
  cut deeper on the upper slopes. Snow line `≈ 0.62H`, pushed down in the gullies, plus noise by angle.
  Light each point with **the sun's elevation seen from its height**, `el + √(2h/R_earth)`. The summit then turns rose before the lake sees the sun.
- **Autumn forest albedo**: never colour by a hashed grid cell (square patches). Use contour bands of a smooth value
  noise at tree-group scale (evergreen, red, crimson, orange, gold, rust, each a narrow smoothstep), multiply by the same
  noise that raises the canopy (dark gaps between crowns), desaturate ~18%, and fade detail to the mean once a
  pixel covers more than ~1 m.
- **Mist**: 12 log-spaced samples along the ray (40 m → hit). Two layers: low lake banks
  `exp(−y/16)·smoothstep(fbm(xz·.0032 + drift))`, and bands between the ranges at y ≈ 170 m. The drift runs on a world clock
  (a spline that is fast during the time-lapse). Light = ambient + twilight fill + forward-scattered sun.
- **Far shore**: a dip in the hills straight below the mountain mirrors into an arch that reads as a bridge. Keep the dip shallow and wide.

## 17. A journey through the universe: flight on layers

From "Kagami" v2 (the client asked for "a journey of the universe, its galaxies and nebulas, and then bring us back").
Everything is a **forward flight along the view axis**, so the whole journey is one camera language: things ahead grow,
stream outward and pass. A second full-frame WebGL program replaces the earthly scene while `SPACE_A(t)` is 1.
The crossfades hide in the sky: look up from the land first, dissolve into space, and on the way home dissolve back into the same sky, then tilt down.

- **Layers**: `N` layers repeat along depth. Layer `i` sits at `d = fract(i/N − fly)`, with the seed `i + 131.7·floor(i/N − fly)` so
  every pass brings new content. A pixel's world point on a layer is `wp = uv·d` (with `uv = (fc − centre) / min(W, H)`), so objects project
  as `world / d` and stream outward as `fly` grows. Fade in at `d → 1`, and out before `d → 0`.
- **Stars** (24 layers, cell .028, probability ≈ .17): a fixed pixel radius, and a streak toward the vanishing point with length
  `|screen|·speed/d·px/30` **capped at ~9 px**. Longer streaks read as sci-fi warp speed or rain. Speed = the spline's derivative.
- **Never clip a glow at its cell edge**: multiply each star or galaxy by `smoothstep(0, 7px, distance to the cell border)`.
  Otherwise the halos of bright stars become faint squares.
- **Nebula** = 8 veils at fixed depths (domain-warped fbm of §5 plus cavities `1 − .55·smoothstep(fbm)` and ionisation rims
  `exp(−((f − .62)/.07)²)`), composited back to front with dust absorption. Two things stop it becoming a flat wall as it fills the frame:
  veils fade out before they reach the lens (`smoothstep(.03, .38, d)`), so the gas parts around you; and extra detail octaves
  **anchored to the world** (frequency ×3 per octave), each shown only while its features are 10–260 px on screen. Use warped ridges,
  `1 − |2n − 1|`; plain high-frequency fbm looks like pink granite.
- **Galaxies** (16 layers, cell .085, density modulated by a web field so they cluster): below 2 px, draw a Gaussian whose flux is `∝ rpx²`;
  above that, a mini galaxy (random inclination and angle, arms appearing as it grows past ~5–40 px).
  **A hero spiral** passes on one side from a fixed depth.
- **Cosmic web**: the deep field of §7, with thin filaments (`pow(1 − |2w − 1|, 16)`), very little diffuse glow (or it reads as purple smoke),
  and galaxies gathered on the threads. A slow zoom-out as the flight slows. The "glory" beat is a ring `exp(−((R − g)/.09)²)·sin(πg)` running out through it.
- **Home**: our galaxy face-on at a depth spline, pinned so that an **arm point** (not the bulge) sits on the flight axis. Resolved stars come in at
  three cell scales and detail octaves as it fills the frame. Tame the bulge once it's large (`mix(1, .3, smoothstep(600, 3000, rpx))`).
  Then hand over to the star layers, slow down to rest, and dissolve into the scene's own sky.
- About 0.25 s per 1080×1920 frame on an M1 (the nebula is the costly part).
