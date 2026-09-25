#!/usr/bin/env python3
"""Paint a still pixel by pixel in a painter's manner: no image model, no reference pictures,
no art software. numpy + scipy + Pillow only.

  python3 paint.py --demo storm --size 1080 --out storm.png     # vortex sea storm, impasto, rain
  python3 paint.py --demo pool --size 1080 --out pool.png       # flat acrylic, hard edges, caustic lines

As a library (write your own scene in a new file next to this one):
  from paint import Canvas, fbm, vortex_flow, noise_flow, lay, stroke, finish, sketch
  c = Canvas(1080, 1080, ground=(.86, .82, .72), seed=1)
  c.wash(color_at)                                   # underpainting from a colour function
  lay(c, flow, color_at, n=1500, length=120, width=38)   # big brushes first, then smaller
  finish(c, light=(-.6, -.8), impasto=1.0, weave=.05).save('out.png')

Model: strokes are polylines traced along a flow field. Each stroke has bristles (streaks
across its width), a paint load that runs out along its length (dry-brush breaks), picks up
wet paint from the canvas at its start (wet-in-wet), and deposits height for impasto, which
`finish` lights like a raking lamp. Colour comes from a function of position (the scene),
never from an image. Work coarse to fine, as a painter does: wash, masses, forms, accents.
"""
import argparse, math
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter


def fbm(h, w, scale, octaves=5, seed=0):
    """Smooth noise in [-1, 1]-ish: blurred white noise summed over octaves (scale = largest feature, px)."""
    rng = np.random.default_rng(seed)
    out = np.zeros((h, w), np.float32)
    amp, sig, tot = 1.0, scale / 3.0, 0.0
    for _ in range(octaves):
        n = gaussian_filter(rng.standard_normal((h, w)).astype(np.float32), max(sig, .6), mode='wrap')
        out += amp * n / (n.std() + 1e-6)
        tot += amp; amp *= .5; sig *= .5
    return out / tot


def vortex_flow(h, w, cx, cy, inward=.25, noise=.35, seed=0):
    """Angle field (radians) circling (cx, cy) counter-clockwise and spiralling in."""
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    th = np.arctan2(y - cy, x - cx)
    return th + np.pi / 2 + inward + noise * fbm(h, w, w / 5, 4, seed)


def noise_flow(h, w, base=0.0, amount=1.0, scale=None, seed=0):
    return base + amount * fbm(h, w, scale or w / 4, 4, seed)


class Canvas:
    def __init__(self, w, h, ground=(.9, .88, .82), seed=0):
        self.w, self.h = w, h
        self.rgb = np.ones((h, w, 3), np.float32) * np.array(ground, np.float32)
        self.height = np.zeros((h, w), np.float32)
        self.rng = np.random.default_rng(seed)

    def grid(self):
        y, x = np.mgrid[0:self.h, 0:self.w].astype(np.float32)
        return x / self.w, y / self.h

    def wash(self, color_at, blur=12, opacity=1.0):
        """Thin underpainting: the scene colour, softened."""
        x, y = self.grid()
        col = np.clip(color_at(x, y), 0, 1).astype(np.float32)
        col = np.stack([gaussian_filter(col[..., i], blur) for i in range(3)], -1)
        self.rgb = self.rgb * (1 - opacity) + col * opacity


def trace(flow, x, y, length, step=5.0, sign=1):
    """Polyline from (x, y) following the angle field."""
    h, w = flow.shape
    pts = [(x, y)]
    for _ in range(max(1, int(length / step))):
        a = flow[int(min(max(y, 0), h - 1)), int(min(max(x, 0), w - 1))]
        x += sign * math.cos(a) * step; y += sign * math.sin(a) * step
        if not (-20 < x < w + 20 and -20 < y < h + 20):
            break
        pts.append((x, y))
    return np.array(pts, np.float32)


def stroke(c, pts, width, color, opacity=.92, bristle=.55, load=1.0, dry=.6, pickup=.25, impasto=.0, rng=None):
    """One brush stroke along pts (N×2, pixels). Rendered segment by segment into a patch."""
    rng = rng or c.rng
    if len(pts) < 2:
        return
    r = width / 2
    x0, y0 = np.floor(pts.min(0) - r - 2).astype(int); x1, y1 = np.ceil(pts.max(0) + r + 2).astype(int)
    x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, c.w), min(y1, c.h)
    if x1 <= x0 or y1 <= y0:
        return
    ph, pw = y1 - y0, x1 - x0
    dist = np.full((ph, pw), np.inf, np.float32); along = np.zeros((ph, pw), np.float32); across = np.zeros((ph, pw), np.float32)
    seg = np.diff(pts, axis=0); seglen = np.hypot(seg[:, 0], seg[:, 1]) + 1e-6
    cum = np.concatenate([[0], np.cumsum(seglen)]); total = cum[-1]
    for i in range(len(seg)):
        a, d, L = pts[i], seg[i], seglen[i]
        bx0 = int(max(min(a[0], a[0] + d[0]) - r - 1, x0)); bx1 = int(min(max(a[0], a[0] + d[0]) + r + 2, x1))
        by0 = int(max(min(a[1], a[1] + d[1]) - r - 1, y0)); by1 = int(min(max(a[1], a[1] + d[1]) + r + 2, y1))
        if bx1 <= bx0 or by1 <= by0:
            continue
        yy, xx = np.mgrid[by0:by1, bx0:bx1].astype(np.float32)
        px, py = xx - a[0], yy - a[1]
        t = np.clip((px * d[0] + py * d[1]) / (L * L), 0, 1)
        qx, qy = px - t * d[0], py - t * d[1]
        dd = np.hypot(qx, qy)
        sub = (slice(by0 - y0, by1 - y0), slice(bx0 - x0, bx1 - x0))
        m = dd < dist[sub]
        dist[sub] = np.where(m, dd, dist[sub])
        along[sub] = np.where(m, cum[i] + t * L, along[sub])
        across[sub] = np.where(m, (px * d[1] - py * d[0]) / L, across[sub])     # signed distance across
    u = np.clip(across / r, -1, 1)
    s = along / total
    # bristles: fixed streak pattern across the brush; paint runs out along the stroke
    K = 48
    bprof = 1 - bristle * rng.random(K).astype(np.float32)
    bprof = np.convolve(np.r_[bprof, bprof[:2]], [.25, .5, .25], 'same')[:K]
    b = np.interp((u + 1) / 2 * (K - 1), np.arange(K), bprof)
    paint = load * (1 - dry * s ** 1.5)
    edge = np.clip((1 - np.abs(u)) * r / 1.2, 0, 1) * (dist < r + 1)
    ends = np.clip(along / (r * .6 + 1), 0, 1) * np.clip((total - along) / (r * .9 + 1), 0, 1)
    alpha = opacity * edge * ends * np.clip((b - (1 - paint)) * 3.5, 0, 1)
    if not alpha.any():
        return
    region = c.rgb[y0:y1, x0:x1]
    under = region[alpha > .05].mean(0) if (alpha > .05).any() else np.array(color)
    col = np.array(color, np.float32) * (1 - pickup) + under * pickup                 # wet-in-wet
    col = col[None, None, :] * (.94 + .1 * b[..., None])                              # bristle value shifts
    c.rgb[y0:y1, x0:x1] = region * (1 - alpha[..., None]) + col * alpha[..., None]
    if impasto:
        c.height[y0:y1, x0:x1] += impasto * alpha * (b - .5 + .6 * np.abs(u) ** 6)      # ridges and rims


def lay(c, flow, color_at, n, length, width, jitter=.06, hue=.012, mask=None, opacity=.92, impasto=.0, both_ways=True, **kw):
    """n strokes: random starts (inside mask, if given), traced along flow, coloured by the scene.
    jitter varies value per stroke, hue adds a little temperature noise per channel."""
    rng = c.rng
    done = 0
    while done < n:
        x, y = rng.random() * c.w, rng.random() * c.h
        if mask is not None and not mask[int(y), int(x)]:
            if rng.random() < .98:
                continue
        L = length * (.6 + .8 * rng.random())
        pts = trace(flow, x, y, L, step=max(3.0, width / 4), sign=1 if (not both_ways or rng.random() < .5) else -1)
        base = np.asarray(color_at(np.float32(x / c.w), np.float32(y / c.h)), np.float32)
        col = np.clip(base * (1 + rng.normal(0, jitter)) + rng.normal(0, hue, 3), 0, 1)
        stroke(c, pts, width * (.75 + .5 * rng.random()), col, opacity=opacity, impasto=impasto, **kw)
        done += 1


def finish(c, light=(-.6, -.8), impasto=1.0, weave=.04, vignette=.25, grain=.02):
    """Rake light across the paint relief, add canvas weave, return a PIL image."""
    hmap = gaussian_filter(c.height, 1.0)
    gy, gx = np.gradient(hmap)
    lx, ly = light
    shade = 1 + impasto * np.clip(-(gx * lx + gy * ly), -1.5, 1.5) * .35
    spec = np.clip(-(gx * lx + gy * ly) - .25, 0, None) ** 2 * impasto * .5
    img = c.rgb * shade[..., None] + spec[..., None]
    y, x = np.mgrid[0:c.h, 0:c.w].astype(np.float32)
    if weave:
        img *= (1 - weave * (.5 + .25 * np.sin(x * 1.9) + .25 * np.sin(y * 2.1)))[..., None]
    if vignette:
        r = np.hypot((x - c.w / 2) / c.w, (y - c.h / 2) / c.h) * 1.5
        img *= (1 - vignette * np.clip(r, 0, 1) ** 2)[..., None]
    if grain:
        img += c.rng.normal(0, grain, img.shape[:2])[..., None].astype(np.float32)
    return Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8))


def sketch(rgb, flow=None, seed=0, paper=(.93, .9, .84), density=1.0):
    """A graphite/ink drawing of a painted image: contour lines from value edges, hatching whose
    density follows darkness, cross-hatching in the darkest areas. Returns a Canvas-ready float
    array (h, w, 3). Used for 'paper → sketch → paint' reveals and for drawn stills."""
    h, w = rgb.shape[:2]
    c = Canvas(w, h, ground=paper, seed=seed)
    c.rgb *= (1 + .025 * fbm(h, w, 6, 2, seed + 1))[..., None]                 # paper tooth
    L = rgb @ np.array([.3, .59, .11], np.float32)
    Ls = gaussian_filter(L, max(2.0, w / 250))                                  # structure, not brush texture
    gy, gx = np.gradient(Ls)
    edge = np.hypot(gx, gy)
    ink = np.clip((edge - np.percentile(edge, 88)) / (np.percentile(edge, 99.5) - np.percentile(edge, 88) + 1e-6), 0, 1)
    if flow is None:                                                             # hatch along the contours
        a = np.arctan2(gy, gx) + np.pi / 2
        cs, sn = gaussian_filter(np.cos(2 * a), w / 60), gaussian_filter(np.sin(2 * a), w / 60)
        flow = .5 * np.arctan2(sn, cs)
    lo, hi = np.percentile(Ls, 15), np.percentile(Ls, 60)
    dark = np.clip((hi - Ls) / (hi - lo + 1e-6), 0, 1) ** 1.2                  # only the darker half is hatched
    rng = c.rng
    n = int(w * h / 160 * density)
    ys, xs = rng.random(n) * h, rng.random(n) * w
    keep = rng.random(n) < dark[ys.astype(int), xs.astype(int)] * 1.1
    graphite = np.array([.2, .19, .18], np.float32)
    for x, y in zip(xs[keep], ys[keep]):
        d = dark[int(y), int(x)]
        for k, off in enumerate([0.0, .9] if d > .62 else [0.0]):             # cross-hatch the darks
            px, py = (x, y) if k == 0 else (x + rng.normal(0, 7), y + rng.normal(0, 7))   # separate starts: no V shapes
            L = 10 + 22 * d
            fwd, back = trace(flow + off, px, py, L / 2, step=3.0), trace(flow + off, px, py, L / 2, step=3.0, sign=-1)
            pts = np.vstack([back[::-1], fwd[1:]])                                # centred on the point
            stroke(c, pts, 1.1 + .6 * d, graphite, opacity=.25 + .5 * d, bristle=.25, dry=.5, pickup=0, rng=rng)
    c.rgb *= (1 - .8 * gaussian_filter(ink, .7))[..., None] * .85 + .15             # contours
    return np.clip(c.rgb, 0, 1)


def palette(stops):
    """stops: [(t, (r,g,b)), ...] → vectorised lookup."""
    ts = np.array([s[0] for s in stops], np.float32); cs = np.array([s[1] for s in stops], np.float32)
    return lambda v: np.stack([np.interp(v, ts, cs[:, i]) for i in range(3)], -1)


# ── demos ────────────────────────────────────────────────────────────────────
def demo_storm(size, seed):
    """Sea storm in a romantic manner: a vortex of light around a small steamboat, impasto, rain."""
    W = H = size
    c = Canvas(W, H, ground=(.55, .5, .4), seed=seed)
    cx, cy = .5, .55
    ramp = palette([(0, (.14, .13, .11)), (.25, (.29, .28, .23)), (.45, (.48, .45, .36)), (.65, (.7, .65, .51)),
                    (.82, (.88, .84, .7)), (1, (.98, .96, .88))])
    swirl = fbm(H, W, W / 6, 5, seed + 1)
    def color_at(x, y):
        dx, dy = x - cx, (y - cy) * 1.25
        r = np.sqrt(dx * dx + dy * dy); th = np.arctan2(dy, dx)
        xi = np.clip((np.asarray(x) * W).astype(int), 0, W - 1); yi = np.clip((np.asarray(y) * H).astype(int), 0, H - 1)
        spiral = np.sin(th * 2 + r * 22 + swirl[yi, xi] * 2.2)
        v = .95 * np.exp(-r * r / .05) + .16 * spiral * np.exp(-r / .35) + .12 * swirl[yi, xi]
        sea = np.clip((np.asarray(y) - .68) / .3, 0, 1)
        v = v * (1 - .7 * sea) + .08
        col = ramp(np.clip(v, 0, 1))
        green = np.array([.2, .27, .23], np.float32)
        return col * (1 - .55 * sea[..., None]) + green * .55 * sea[..., None]
    c.wash(color_at, blur=18)
    flow = vortex_flow(H, W, cx * W, cy * H, inward=.35, noise=.3, seed=seed)
    y, x = np.mgrid[0:H, 0:W]
    seaflow = noise_flow(H, W, base=-.15, amount=.35, seed=seed + 3)
    k = np.clip((y / H - .66) / .1, 0, 1)
    flow = flow * (1 - k) + seaflow * k
    lay(c, flow, color_at, n=650, length=size * .24, width=size * .065, opacity=.7, pickup=.45, bristle=.35, dry=.3, impasto=.4)
    lay(c, flow, color_at, n=2600, length=size * .1, width=size * .02, opacity=.8, pickup=.35, impasto=.7, dry=.55)
    near = np.hypot(x / W - cx, (y / H - cy) * 1.25) < .28
    lay(c, flow, color_at, n=2600, length=size * .05, width=size * .007, impasto=.9, mask=near, jitter=.05)
    # the boat: a dark hull in horizontal dabs, a mast, a lamp, and smoke pulled into the vortex
    bx, by = cx * W, cy * H + size * .02
    tilt = -.14
    for i in range(90):                                   # hull: rows of dabs, wide deck tapering to the keel
        v = c.rng.random()
        half = size * (.045 - .03 * v)
        u = (c.rng.random() * 2 - 1) * half
        yy = by + v * size * .016 + u * tilt
        pts = np.array([[bx + u - size * .008, yy - size * .008 * tilt], [bx + u + size * .008, yy + size * .008 * tilt]], np.float32)
        stroke(c, pts, size * .005, (.06, .05, .045), opacity=.95, bristle=.2, dry=.1, pickup=.05)
    for i in range(18):                                   # deckhouse and paddle box
        u = (c.rng.random() * 2 - 1) * size * .012
        pts = np.array([[bx + u, by - size * .012], [bx + u, by - size * .001]], np.float32)
        stroke(c, pts, size * .005, (.07, .06, .05), opacity=.95, bristle=.2, dry=.1, pickup=.05)
    stroke(c, np.array([[bx + size * .01, by], [bx + size * .012, by - size * .06]], np.float32), size * .003, (.06, .05, .045), bristle=.1, dry=0, pickup=0)
    sm = np.array([[bx - size * .005, by - size * .01]], np.float32)
    for i in range(40):
        sm = np.vstack([sm, sm[-1] + [-size * .004 - i * .1, -size * .004 + i * .12]])
    for i in range(14):
        stroke(c, sm + c.rng.normal(0, size * .003, sm.shape), size * (.012 + i * .0008), (.12, .11, .1), opacity=.5, bristle=.6, dry=.7, pickup=.4, impasto=.3)
    ly, lx = int(by - size * .045), int(bx + size * .012)
    glow = np.exp(-((x - lx) ** 2 + (y - ly) ** 2) / (2 * (size * .006) ** 2))
    c.rgb += (glow[..., None] * np.array([1, .85, .55]) * .9).astype(np.float32)
    # rain: long thin pale streaks on a slant
    rain = np.zeros((H, W), np.float32)
    for i in range(420):
        x0, y0 = c.rng.random() * W * 1.3 - W * .15, c.rng.random() * H * 1.2 - H * .2
        Lr = size * (.1 + .25 * c.rng.random())
        pts = np.array([[x0, y0], [x0 + Lr * .32, y0 + Lr]], np.float32)
        stroke(c, pts, size * .0018, (.86, .86, .8), opacity=.18 + .2 * c.rng.random(), bristle=.3, dry=.5, pickup=.5)
    return finish(c, light=(-.55, -.85), impasto=1.2, weave=.04, vignette=.35), flow


def demo_pool(size, seed):
    """Flat acrylic in a sunlit Californian manner: hard edges, unmodulated fields, a caustic line net."""
    W = H = size
    c = Canvas(W, H, ground=(.93, .91, .86), seed=seed)
    x, y = c.grid()
    m = .06                                                         # unpainted border
    inside = (x > m) & (x < 1 - m) & (y > m) & (y < 1 - m)
    def fill(mask, col, roll=.025):                                 # flat field with a faint roller texture
        tex = 1 + roll * fbm(H, W, 30, 3, int(c.rng.integers(1e6)))
        c.rgb[mask] = (np.array(col, np.float32)[None, :] * tex[mask][:, None])
    fill(inside & (y < .5), (.47, .7, .88), roll=.01)               # sky, flat
    fill(inside & (y >= .5) & (y < .56) & (x >= .62), (.86, .84, .8))   # low wall
    fill(inside & (y >= .46) & (y < .56) & (x < .62), (.94, .94, .92))   # house
    for i in range(7):                                              # window slats
        fill(inside & (y > .475) & (y < .54) & (np.abs(x - (.12 + i * .02)) < .004), (.72, .62, .42))
    fill(inside & (y >= .56) & (y < .6), (.3, .5, .28))             # hedge line
    fill(inside & (y >= .6) & (y < .66), (.93, .8, .76))            # pink paving
    pool = inside & (y >= .66)
    fill(pool, (.26, .66, .86))
    n = fbm(H, W, W / 4, 2, seed + 5) + 1.4 * (y - .66)
    for lvl, col, wdt in [(0, (.72, .9, .97), .07), (.5, (.14, .48, .74), .05)]:
        f = np.abs(((n * 4.5 + lvl) % 1) - .5)
        c.rgb[pool & (f < wdt)] = col                               # the wavy interlocking lines
    board = pool & (np.abs((x - .1) - (y - .72) * .55) < .045) & (y < .98)
    fill(board, (.86, .72, .38))
    for px_, top in [(.22, .12), (.78, .2), (.9, .08)]:             # palms: trunk, fronds
        trunk = inside & (np.abs(x - px_ - (y - .5) * .03) < .006) & (y > top) & (y < .5)
        fill(trunk, (.45, .36, .25))
        for k in range(9):
            a = k / 9 * 2 * np.pi
            fx, fy = px_ + np.cos(a) * .07, top + np.sin(a) * .035 + .02
            t = np.clip(((x - px_) * (fx - px_) + (y - top) * (fy - top)) / ((fx - px_) ** 2 + (fy - top) ** 2), 0, 1)
            d = np.hypot(x - px_ - t * (fx - px_), y - top - t * (fy - top) - .02 * np.sin(t * np.pi))
            fill(inside & (d < .01 * (1 - t) + .002), (.16, .42, .2))
    return finish(c, impasto=0, weave=.015, vignette=0, grain=.008), None


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--demo', choices=['storm', 'pool'], default='storm')
    ap.add_argument('--size', type=int, default=1080)
    ap.add_argument('--seed', type=int, default=3)
    ap.add_argument('--out', default='painting.png')
    ap.add_argument('--sketch', action='store_true', help='also write <out>-sketch.png: the drawing under the painting')
    a = ap.parse_args()
    img, flow = {'storm': demo_storm, 'pool': demo_pool}[a.demo](a.size, a.seed)
    img.save(a.out)
    print(a.out)
    if a.sketch:
        out = a.out.rsplit('.', 1)[0] + '-sketch.png'
        Image.fromarray((sketch(np.asarray(img, np.float32) / 255, flow=flow, seed=a.seed) * 255).astype(np.uint8)).save(out)
        print(out)
