// Channel watermark for a seek(t) film: faint inside the picture while it plays, a card front and centre at the end.
//
// While the film plays, the handle is part of the picture: plain text at ~20% opacity, with no box, border, icon or shadow.
// It sits in one calm spot and is drawn BEFORE the vignette and grain, so it takes the film's texture.
// At the end it glides to the centre, grows and turns to gold while the film's own motif assembles above it (your `ornament`
// callback: the pieces of a medallion locking together, stars gathering into a shape…). A hairline then draws beneath it
// and a light sweep crosses the letters. Pure in t. Leave ~2.2 s after the picture's fade for the card; pad the audio with silence.
//
//   <script src="watermark.js"></script>
//   const wm = makeWatermark({ ctx, W, H, handle: '@yourchannel',
//     mark: { x: 92, y: 206, align: 'left', size: 23, alpha: .2, t0: .4 },    // one calm spot: away from text, subjects and platform UI
//     card: { cx: W / 2, ty: H / 2 + 130, size: 50, t0: 19.9 },               // the handle's glide begins at card.t0
//     ornament: (ctx, t, u) => { /* u: 0 → 1 over the card; draw your motif centred above (cx, ty) */ } });
//   await wm.ready;                                        // before __film.ready (it measures the font)
//   in seek(t): scene, text…; wm.mark(t); vignette, grain; fade to black; wm.card(t); then the grain again, over the card
//
// In 9:16 keep the mark at x ≤ 920 (TikTok's buttons) and y ≈ 180–1450. Frame 0 stays clean (mark.t0 > 0).
function makeWatermark({ ctx, W, H, handle, mark, card, ornament = null, font = '"Jost", "Helvetica Neue", sans-serif', ink = '#f3eee4' }) {
  const sm = x => { x = Math.min(1, Math.max(0, x)); return x * x * (3 - 2 * x); };
  const eio = x => { x = Math.min(1, Math.max(0, x)); return x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; };
  const S = { mark: null, card: null };
  const span = { glide: .95, line: [.85, 1.4], sweep: [1.35, 2.1] };

  function sprite(size, weight, gold, track) {
    const R = 2, f = `${weight} ${size}px ${font}`, m = document.createElement('canvas').getContext('2d');
    m.font = f; m.letterSpacing = `${track}px`;
    const w = Math.ceil(m.measureText(handle).width) + 8, h = Math.ceil(size * 1.5);
    const c = document.createElement('canvas'); c.width = w * R; c.height = h * R;
    const g = c.getContext('2d'); g.scale(R, R); g.font = f; g.letterSpacing = `${track}px`; g.textBaseline = 'middle'; g.textAlign = 'center';
    if (gold) {
      const gr = g.createLinearGradient(0, h * .2, 0, h * .8); gr.addColorStop(0, '#fbecc2'); gr.addColorStop(.5, '#e2bd72'); gr.addColorStop(1, '#b8873f');
      g.shadowColor = 'rgba(255,195,110,.35)'; g.shadowBlur = 18; g.fillStyle = gr; g.fillText(handle, w / 2, h / 2);
      g.shadowColor = 'transparent'; g.fillText(handle, w / 2, h / 2);
    } else { g.fillStyle = ink; g.fillText(handle, w / 2, h / 2); }
    return { c, w, h };
  }

  function drawMark(t) {                                     // call before the vignette and grain
    const a = (mark.alpha ?? .2) * sm((t - (mark.t0 ?? .4)) / .7) * (card ? 1 - sm((t - card.t0) / .25) : 1);
    if (a < .004 || !S.mark) return;
    const x = mark.align === 'left' ? mark.x : mark.align === 'right' ? mark.x - S.mark.w : mark.x - S.mark.w / 2;
    ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.globalAlpha = a;
    ctx.drawImage(S.mark.c, x, mark.y - S.mark.h / 2, S.mark.w, S.mark.h); ctx.restore();
  }

  function drawCard(t) {                                     // call after the fade to black
    if (!card || !S.card || t < card.t0 - .6) return;
    const u = t - card.t0;
    ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0);
    if (ornament) ornament(ctx, t, Math.max(0, u));
    const g = sm(u / span.glide);
    if (g > 0) {                                             // glide from the mark's spot, grow, turn to gold
      const mx = mark.align === 'left' ? mark.x + S.mark.w / 2 : mark.align === 'right' ? mark.x - S.mark.w / 2 : mark.x;
      const e = eio(g), x = mx + (card.cx - mx) * e, y = mark.y + (card.ty - mark.y) * e - Math.sin(Math.PI * e) * 40;
      const s = mark.size / card.size + (1 - mark.size / card.size) * e, a = .2 + .8 * g, ks = s * card.size / mark.size;
      ctx.globalAlpha = a * (1 - g); ctx.drawImage(S.mark.c, x - S.mark.w * ks / 2, y - S.mark.h * ks / 2, S.mark.w * ks, S.mark.h * ks);
      ctx.globalAlpha = a * g; ctx.drawImage(S.card.c, x - S.card.w * s / 2, y - S.card.h * s / 2, S.card.w * s, S.card.h * s);
      ctx.globalAlpha = 1;
    }
    const ln = sm((u - span.line[0]) / (span.line[1] - span.line[0]));
    if (ln > 0) {                                            // a hairline draws outward beneath it
      const half = S.card.w * .42 * ln, ly = card.ty + card.size * .9, lg = ctx.createLinearGradient(card.cx - half, 0, card.cx + half, 0);
      lg.addColorStop(0, 'rgba(214,184,120,0)'); lg.addColorStop(.5, 'rgba(234,206,145,.9)'); lg.addColorStop(1, 'rgba(214,184,120,0)');
      ctx.fillStyle = lg; ctx.fillRect(card.cx - half, ly, half * 2, 1.4);
    }
    const sw = (u - span.sweep[0]) / (span.sweep[1] - span.sweep[0]);
    if (sw > 0 && sw < 1) {                                  // a light sweep across the letters
      const F = document.createElement('canvas'); F.width = S.card.c.width; F.height = S.card.c.height;
      const fg = F.getContext('2d'), fw = F.width, fh = F.height, sx = (-.3 + 1.6 * sw) * fw;
      fg.drawImage(S.card.c, 0, 0); fg.globalCompositeOperation = 'source-in';
      const lg = fg.createLinearGradient(sx - fw * .1, 0, sx + fw * .1, fh * .5);
      lg.addColorStop(0, 'rgba(255,244,215,0)'); lg.addColorStop(.5, 'rgba(255,250,232,1)'); lg.addColorStop(1, 'rgba(255,244,215,0)');
      fg.fillStyle = lg; fg.fillRect(0, 0, fw, fh);
      ctx.globalCompositeOperation = 'lighter'; ctx.globalAlpha = .8;
      ctx.drawImage(F, card.cx - S.card.w / 2, card.ty - S.card.h / 2, S.card.w, S.card.h);
    }
    ctx.restore();
  }

  const ready = Promise.all([document.fonts.load(`400 ${mark.size}px ${font}`, handle), document.fonts.load(`500 ${card?.size ?? 50}px ${font}`, handle)])
    .catch(() => {}).then(() => { S.mark = sprite(mark.size, 400, false, 1.2); if (card) S.card = sprite(card.size, 500, true, 3); });
  return { ready, mark: drawMark, card: drawCard };
}
