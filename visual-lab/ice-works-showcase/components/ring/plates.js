/**
 * The art on the cards, painted at load rather than shipped as photographs.
 *
 * Every plate is drawn from the maths of the work it stands for — the
 * tomography triptych integrates a real Radon transform over one phantom and
 * then back-projects it, the schlieren plate sums a director field from its
 * own defects — so the ring carries this portfolio's own material instead of
 * somebody else's renders. None of it is a simulation *result*; they are
 * illustrations with real geometry underneath.
 *
 * A painter is `(ctx, w, h)` and owns its whole cell. Cells are 1.5 : 1 to
 * match the plane and are handed to the atlas from `projects.js`.
 *
 * Per-pixel passes go through `field()`, which renders at a fraction of the
 * cell and scales up. The fields are all low frequency, eighteen of them are
 * painted in one pass on the main thread, and the softening that buys reads
 * as part of the liquid look rather than against it.
 */

const TAU = Math.PI * 2;

/* ------------------------------------------------------------- numbers -- */

const clamp = (v, lo, hi) => (v < lo ? lo : v > hi ? hi : v);

const smoothstep = (e0, e1, x) => {
  const t = clamp((x - e0) / (e1 - e0), 0, 1);
  return t * t * (3 - 2 * t);
};

// mulberry32. Seeded because a reload should redraw the same eighteen cards;
// art that reshuffles itself is a different card, not the same one again.
function rng(seed) {
  let s = seed >>> 0;
  return () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let t = Math.imul(s ^ (s >>> 15), 1 | s);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/**
 * Value noise on a 256² torus, with fbm hung off it. Value rather than
 * gradient noise: every use here is either warped or banded before it is
 * looked at, and the axis alignment value noise is criticised for never
 * survives that.
 */
function makeNoise(seed) {
  const N = 256;
  const rand = rng(seed);
  const g = new Float32Array(N * N);
  for (let i = 0; i < g.length; i++) g[i] = rand();

  const at = (x, y) => g[(y & (N - 1)) * N + (x & (N - 1))];
  const sm = (t) => t * t * (3 - 2 * t);

  const n = (x, y) => {
    const xi = Math.floor(x);
    const yi = Math.floor(y);
    const xf = sm(x - xi);
    const yf = sm(y - yi);
    const a = at(xi, yi);
    const b = at(xi + 1, yi);
    const c = at(xi, yi + 1);
    const d = at(xi + 1, yi + 1);
    return a + (b - a) * xf + (c - a) * yf + (a - b - c + d) * xf * yf;
  };

  n.fbm = (x, y, oct = 5, gain = 0.5) => {
    let sum = 0;
    let amp = 1;
    let norm = 0;
    let fx = x;
    let fy = y;
    for (let i = 0; i < oct; i++) {
      sum += amp * n(fx, fy);
      norm += amp;
      amp *= gain;
      // Irrational-ish lacunarity, or every octave lines its grid up with the
      // one below and the sum shows the lattice.
      fx = fx * 2.03 + 37.1;
      fy = fy * 2.01 - 19.7;
    }
    return sum / norm;
  };

  // Ridged: |2n-1| inverted. What makes a mountain a mountain.
  n.ridge = (x, y, oct = 5) => {
    let sum = 0;
    let amp = 1;
    let norm = 0;
    let fx = x;
    let fy = y;
    for (let i = 0; i < oct; i++) {
      const v = 1 - Math.abs(n(fx, fy) * 2 - 1);
      sum += amp * v * v;
      norm += amp;
      amp *= 0.5;
      fx = fx * 2.07 + 11.3;
      fy = fy * 2.02 - 5.9;
    }
    return sum / norm;
  };

  return n;
}

/* -------------------------------------------------------------- colour -- */

const hex = (s) => [
  parseInt(s.slice(1, 3), 16) / 255,
  parseInt(s.slice(3, 5), 16) / 255,
  parseInt(s.slice(5, 7), 16) / 255,
];

const mix = (a, b, t) => [
  a[0] + (b[0] - a[0]) * t,
  a[1] + (b[1] - a[1]) * t,
  a[2] + (b[2] - a[2]) * t,
];

const rgba = (c, a) =>
  `rgba(${Math.round(clamp(c[0], 0, 1) * 255)},${Math.round(
    clamp(c[1], 0, 1) * 255,
  )},${Math.round(clamp(c[2], 0, 1) * 255)},${a})`;

const CREAM = hex("#f7ecd9");

/* --------------------------------------------------------------- paint -- */

/**
 * A per-pixel pass, rendered at 1/`step` of the cell and scaled up. `fn`
 * writes linear-ish 0..1 rgb into `out` for uv in the unit square.
 */
function field(ctx, w, h, step, fn) {
  const cw = Math.max(2, Math.round(w / step));
  const ch = Math.max(2, Math.round(h / step));

  const off = document.createElement("canvas");
  off.width = cw;
  off.height = ch;
  const octx = off.getContext("2d");
  const img = octx.createImageData(cw, ch);
  const d = img.data;
  const out = [0, 0, 0];

  for (let y = 0; y < ch; y++) {
    for (let x = 0; x < cw; x++) {
      fn((x + 0.5) / cw, (y + 0.5) / ch, out);
      const i = (y * cw + x) * 4;
      d[i] = clamp(out[0], 0, 1) * 255;
      d[i + 1] = clamp(out[1], 0, 1) * 255;
      d[i + 2] = clamp(out[2], 0, 1) * 255;
      d[i + 3] = 255;
    }
  }
  octx.putImageData(img, 0, 0);

  ctx.imageSmoothingEnabled = true;
  ctx.imageSmoothingQuality = "high";
  ctx.drawImage(off, 0, 0, w, h);
}

function base(ctx, w, h, a = "#0a0c11", b = "#04050a") {
  const g = ctx.createLinearGradient(0, 0, w * 0.7, h);
  g.addColorStop(0, a);
  g.addColorStop(1, b);
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, w, h);
}

// Additive, always — every glow in here sits on something already painted.
function glow(ctx, x, y, r, c, a) {
  const g = ctx.createRadialGradient(x, y, 0, x, y, r);
  g.addColorStop(0, rgba(c, a));
  g.addColorStop(0.45, rgba(c, a * 0.3));
  g.addColorStop(1, rgba(c, 0));
  ctx.save();
  ctx.globalCompositeOperation = "lighter";
  ctx.fillStyle = g;
  ctx.fillRect(x - r, y - r, r * 2, r * 2);
  ctx.restore();
}

/**
 * The common finish: a raking sheen, a vignette and a little grain. Run last
 * on every plate — it is most of what makes eighteen unrelated drawings read
 * as one set, and what keeps them from looking like flat diagrams once the
 * glass lip and the goo get hold of them.
 */
function finish(ctx, w, h, seed) {
  ctx.save();

  ctx.globalCompositeOperation = "lighter";
  const sheen = ctx.createLinearGradient(0, h, w * 0.9, 0);
  sheen.addColorStop(0, "rgba(255,255,255,0)");
  sheen.addColorStop(0.45, "rgba(255,246,232,0.055)");
  sheen.addColorStop(0.62, "rgba(255,246,232,0.02)");
  sheen.addColorStop(1, "rgba(255,255,255,0)");
  ctx.fillStyle = sheen;
  ctx.fillRect(0, 0, w, h);

  ctx.globalCompositeOperation = "multiply";
  const vig = ctx.createRadialGradient(
    w * 0.5,
    h * 0.48,
    h * 0.2,
    w * 0.5,
    h * 0.5,
    h * 0.95,
  );
  vig.addColorStop(0, "rgba(255,255,255,1)");
  vig.addColorStop(1, "rgba(150,150,160,1)");
  ctx.fillStyle = vig;
  ctx.fillRect(0, 0, w, h);

  // Grain from one small tile rather than a full-size ImageData: the atlas
  // downsamples anyway, and eighteen full passes is real time on the gate.
  const tile = document.createElement("canvas");
  tile.width = 128;
  tile.height = 128;
  const tctx = tile.getContext("2d");
  const gi = tctx.createImageData(128, 128);
  const r = rng(seed * 977 + 13);
  for (let i = 0; i < gi.data.length; i += 4) {
    const v = 110 + r() * 60;
    gi.data[i] = v;
    gi.data[i + 1] = v;
    gi.data[i + 2] = v;
    gi.data[i + 3] = 255;
  }
  tctx.putImageData(gi, 0, 0);
  ctx.globalCompositeOperation = "overlay";
  ctx.globalAlpha = 0.16;
  const pat = ctx.createPattern(tile, "repeat");
  ctx.fillStyle = pat;
  ctx.fillRect(0, 0, w, h);

  ctx.restore();
}

/* ============================================================== VENUS === */

const VENUS = hex("#f2b46b");

/** 01 — the super-rotating sulfuric deck, sheared by its own wind. */
function cloudDeck(ctx, w, h) {
  const n = makeNoise(11);
  const deep = hex("#140a04");
  const mid = hex("#7d4415");

  field(ctx, w, h, 2.5, (u, v, out) => {
    // Domain warp first: the bands are latitude lines that the zonal wind has
    // dragged out of true, not stripes with noise laid over them.
    const wx = n.fbm(u * 3.1 + 11, v * 2.2, 4) - 0.5;
    const wy = n.fbm(u * 2.4, v * 3.4 + 7, 4) - 0.5;

    const band = Math.sin((v + wy * 0.5) * 12.5 + wx * 3.6) * 0.5 + 0.5;
    const curl = n.fbm(u * 5.5 + wx * 2.4, v * 8 + wy * 2.4, 6);
    const t = clamp(band * 0.6 + curl * 0.55, 0, 1);

    // Sun from the upper right, so the deck has a side to it.
    const lit = smoothstep(-0.3, 1.2, u * 0.72 + (1 - v) * 0.48);

    let c = mix(deep, mid, smoothstep(0.16, 0.64, t));
    c = mix(c, VENUS, smoothstep(0.54, 0.96, t) * (0.32 + lit * 0.78));
    c = mix(c, CREAM, smoothstep(0.87, 1, t) * lit * 0.8);
    out[0] = c[0];
    out[1] = c[1];
    out[2] = c[2];
  });

  finish(ctx, w, h, 11);
}

/** 02 — the sensor: a solid electrolyte cell with oxygen crossing it. */
function fugacity(ctx, w, h) {
  base(ctx, w, h, "#0c0a08", "#040303");

  const cx = w * 0.5;
  const cy = h * 0.5;
  const R = h * 0.38;
  const r = rng(202);

  glow(ctx, cx, cy, R * 2.6, VENUS, 0.22);

  // Ceramic body: rings of a cool grey, so the core reads as the only heat.
  ctx.save();
  for (let i = 9; i >= 1; i--) {
    const rad = R * (0.34 + (i / 9) * 0.66);
    const g = ctx.createLinearGradient(cx - rad, cy - rad, cx + rad, cy + rad);
    const k = 0.1 + (i / 9) * 0.12;
    g.addColorStop(0, `rgba(${210 * k * 2},${205 * k * 2},${200 * k * 2},1)`);
    g.addColorStop(0.5, `rgba(${30 * k},${28 * k},${26 * k},1)`);
    g.addColorStop(1, `rgba(${190 * k * 2},${180 * k * 2},${168 * k * 2},1)`);
    ctx.strokeStyle = g;
    ctx.lineWidth = R * 0.055;
    ctx.beginPath();
    ctx.arc(cx, cy, rad, 0, TAU);
    ctx.stroke();
  }
  ctx.restore();

  // Reference electrode: the bright half of the cell.
  ctx.save();
  ctx.globalCompositeOperation = "lighter";
  const core = ctx.createRadialGradient(cx, cy, 0, cx, cy, R * 0.42);
  core.addColorStop(0, rgba(CREAM, 0.95));
  core.addColorStop(0.35, rgba(VENUS, 0.8));
  core.addColorStop(1, rgba(VENUS, 0));
  ctx.fillStyle = core;
  ctx.beginPath();
  ctx.arc(cx, cy, R * 0.42, 0, TAU);
  ctx.fill();
  ctx.restore();

  // Ion tracks. O²⁻ arrives from the atmosphere side and crosses inward; the
  // tail is the track, the head is where it is now.
  ctx.save();
  ctx.globalCompositeOperation = "lighter";
  for (let i = 0; i < 46; i++) {
    const a = r() * TAU;
    const start = R * (1.5 + r() * 1.1);
    const end = R * (0.45 + r() * 0.25);
    const bend = (r() - 0.5) * 0.8;
    const steps = 22;
    ctx.beginPath();
    for (let s = 0; s <= steps; s++) {
      const t = s / steps;
      const rad = start + (end - start) * t;
      const ang = a + bend * t * t;
      const x = cx + Math.cos(ang) * rad;
      const y = cy + Math.sin(ang) * rad * 0.94;
      if (s === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.strokeStyle = rgba(VENUS, 0.06 + r() * 0.1);
    ctx.lineWidth = h * 0.004;
    ctx.stroke();

    const ang = a + bend;
    ctx.fillStyle = rgba(CREAM, 0.5 + r() * 0.4);
    ctx.beginPath();
    ctx.arc(
      cx + Math.cos(ang) * end,
      cy + Math.sin(ang) * end * 0.94,
      h * 0.005,
      0,
      TAU,
    );
    ctx.fill();
  }
  ctx.restore();

  // Radial ticks: the instrument's own scale, unlabelled.
  ctx.save();
  ctx.strokeStyle = rgba(CREAM, 0.16);
  ctx.lineWidth = 1.2;
  for (let i = 0; i < 72; i++) {
    const a = (i / 72) * TAU;
    const long = i % 6 === 0;
    const r0 = R * 1.12;
    const r1 = R * (long ? 1.24 : 1.18);
    ctx.globalAlpha = long ? 0.5 : 0.22;
    ctx.beginPath();
    ctx.moveTo(cx + Math.cos(a) * r0, cy + Math.sin(a) * r0);
    ctx.lineTo(cx + Math.cos(a) * r1, cy + Math.sin(a) * r1);
    ctx.stroke();
  }
  ctx.restore();

  finish(ctx, w, h, 202);
}

/** 03 — descent: one trajectory down through the layers it is measuring. */
function descent(ctx, w, h) {
  const n = makeNoise(303);
  const deep = hex("#0a0603");
  const haze = hex("#6b3d16");

  field(ctx, w, h, 3, (u, v, out) => {
    // Denser and hotter the further down: the plate reads as a column of
    // atmosphere, not a background.
    const d = Math.pow(v, 1.7);
    const stir = n.fbm(u * 4 + 3, v * 7, 4) - 0.5;
    const layer = Math.sin(v * 22 + stir * 2.6) * 0.5 + 0.5;
    let c = mix(deep, haze, d * 0.85 + layer * 0.12);
    c = mix(c, VENUS, smoothstep(0.55, 1, d) * (0.18 + layer * 0.22));
    out[0] = c[0];
    out[1] = c[1];
    out[2] = c[2];
  });

  // Altitude grid.
  ctx.save();
  ctx.strokeStyle = rgba(CREAM, 0.1);
  ctx.lineWidth = 1;
  for (let i = 1; i < 9; i++) {
    const y = (i / 9) * h;
    ctx.beginPath();
    ctx.moveTo(w * 0.06, y);
    ctx.lineTo(w * 0.94, y);
    ctx.stroke();
  }
  ctx.restore();

  // The descent itself, blown downwind as it falls.
  const path = [];
  const steps = 160;
  for (let i = 0; i <= steps; i++) {
    const t = i / steps;
    const drift = n.fbm(t * 5 + 2, 1.5, 4) - 0.5;
    path.push([
      w * (0.14 + t * 0.7 + drift * 0.16),
      h * (0.05 + Math.pow(t, 1.25) * 0.9),
    ]);
  }

  ctx.save();
  ctx.globalCompositeOperation = "lighter";
  ctx.lineCap = "round";
  for (const [width, alpha] of [
    [h * 0.045, 0.1],
    [h * 0.018, 0.22],
    [h * 0.006, 0.9],
  ]) {
    ctx.beginPath();
    path.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)));
    ctx.strokeStyle = rgba(width < h * 0.01 ? CREAM : VENUS, alpha);
    ctx.lineWidth = width;
    ctx.stroke();
  }
  ctx.restore();

  const [px, py] = path[Math.floor(steps * 0.72)];
  glow(ctx, px, py, h * 0.22, VENUS, 0.55);
  ctx.fillStyle = rgba(CREAM, 0.98);
  ctx.beginPath();
  ctx.arc(px, py, h * 0.012, 0, TAU);
  ctx.fill();

  finish(ctx, w, h, 303);
}

/* ========================================================= TOMOGRAPHY === */

const ICE = hex("#9fdbe0");

/**
 * One phantom, shared by all three tomography plates: a body, a vertebral
 * body, the canal as a negative disc, the processes. Discs specifically —
 * the Radon transform of a uniform disc is a closed form, so plate 04 is the
 * actual integral rather than a picture of one.
 */
const PHANTOM = [
  { x: 0.03, y: 0.06, r: 0.78, d: 0.16 }, // soft tissue, deliberately faint
  { x: 0, y: 0.21, r: 0.3, d: 0.62 }, // vertebral body
  { x: 0, y: -0.13, r: 0.115, d: -0.36 }, // the canal, as negative density
  { x: -0.43, y: -0.05, r: 0.12, d: 0.95 }, // transverse processes: these are
  { x: 0.43, y: -0.05, r: 0.12, d: 0.95 }, // what draw the sinusoids
  { x: 0, y: -0.5, r: 0.1, d: 0.9 }, // spinous process
];

// ∫ along the ray at offset s, angle θ. Chord length through each disc.
function radon(s, cos, sin) {
  let acc = 0;
  for (const p of PHANTOM) {
    const c = p.x * cos + p.y * sin;
    const dd = p.r * p.r - (s - c) * (s - c);
    if (dd > 0) acc += p.d * Math.sqrt(dd);
  }
  return acc;
}

/** 04 — the sinogram, with most of its views thrown away. */
function sinogram(ctx, w, h) {
  const n = makeNoise(404);
  const deep = hex("#030708");
  const steel = hex("#1d3c44");
  const VIEWS = 33; // angles across the detector's whole sweep
  const KEEP = 3; // and one in three a sparse acquisition actually measures

  field(ctx, w, h, 2, (u, v, out) => {
    const th = u * Math.PI;
    const s = (v - 0.5) * 2;
    let val = radon(s, Math.cos(th), Math.sin(th)) * 3.1;

    // The gaps are the whole point of the card: the bright sinusoids are
    // there, and two thirds of them were never measured.
    const col = Math.floor(u * VIEWS);
    const kept = col % KEEP === 0;
    const edge = Math.abs(((u * VIEWS) % 1) - 0.5) * 2;
    const gate = kept ? 1 : 0.07 + smoothstep(0.78, 1, edge) * 0.05;

    val *= gate;
    val += (n(u * 180, v * 180) - 0.5) * 0.04; // detector noise

    let c = mix(deep, steel, smoothstep(0, 0.4, val));
    c = mix(c, ICE, smoothstep(0.3, 0.8, val));
    c = mix(c, CREAM, smoothstep(0.72, 1.05, val));
    out[0] = c[0];
    out[1] = c[1];
    out[2] = c[2];
  });

  finish(ctx, w, h, 404);
}

/** 05 — back-projected from those few views. The streaks are the problem. */
function backprojection(ctx, w, h) {
  const n = makeNoise(505);
  const deep = hex("#03070a");
  const steel = hex("#1b3a46");
  const VIEWS = 7; // few enough that each one's smear stays a separate streak

  // Pre-rolled, or the trig runs once per pixel per view.
  const dirs = [];
  for (let i = 0; i < VIEWS; i++) {
    const th = (i / VIEWS) * Math.PI;
    dirs.push([Math.cos(th), Math.sin(th)]);
  }

  field(ctx, w, h, 2, (u, v, out) => {
    // Square the coordinates off the 1.5 : 1 cell, or the phantom is an oval.
    const x = (u - 0.5) * 3;
    const y = (v - 0.5) * 2;

    let acc = 0;
    for (let i = 0; i < VIEWS; i++) {
      acc += radon(x * dirs[i][0] + y * dirs[i][1], dirs[i][0], dirs[i][1]);
    }
    // Windowed hard around where the sum actually sits. Unfiltered back
    // projection has very little dynamic range of its own; open the window up
    // and all seven streaks average into one blur, which is the problem the
    // filter exists to solve rather than a picture of it.
    let val = (acc / VIEWS - 0.05) / 0.23;
    val *= 1 - smoothstep(0.85, 1.4, Math.hypot(x, y)) * 0.92; // field of view
    val += (n(u * 90, v * 90) - 0.5) * 0.05;

    let c = mix(deep, steel, smoothstep(0, 0.45, val));
    c = mix(c, ICE, smoothstep(0.42, 1, val) * 0.9);
    c = mix(c, CREAM, smoothstep(0.92, 1.25, val) * 0.5);
    out[0] = c[0];
    out[1] = c[1];
    out[2] = c[2];
  });

  finish(ctx, w, h, 505);
}

/** 06 — what the reconstruction is asked to return: the slice itself. */
function reconstruction(ctx, w, h) {
  const n = makeNoise(606);
  const deep = hex("#03070a");
  const steel = hex("#1c3c47");

  field(ctx, w, h, 2, (u, v, out) => {
    const x = (u - 0.5) * 3;
    const y = (v - 0.5) * 2;

    // The phantom drawn directly, edges softened so it reads as tissue
    // rather than as clip art of tissue.
    let val = 0;
    for (const p of PHANTOM) {
      val +=
        p.d *
        (1 - smoothstep(p.r * 0.7, p.r * 1.01, Math.hypot(x - p.x, y - p.y)));
    }
    val *= 1.35 + (n.fbm(u * 11, v * 16, 4) - 0.5) * 0.9; // trabecular texture
    val *= 1 - smoothstep(0.95, 1.3, Math.hypot(x, y)) * 0.95;

    // The scan plane crossing it, which is where the two halves differ.
    const scan = Math.exp(-Math.pow((v - 0.44) * 9, 2));
    val += scan * 0.22;

    let c = mix(deep, steel, smoothstep(0, 0.42, val));
    c = mix(c, ICE, smoothstep(0.35, 0.95, val));
    c = mix(c, CREAM, smoothstep(0.78, 1.3, val) * 0.85);
    out[0] = c[0];
    out[1] = c[1];
    out[2] = c[2];
  });

  ctx.save();
  ctx.globalCompositeOperation = "lighter";
  ctx.strokeStyle = rgba(CREAM, 0.5);
  ctx.lineWidth = h * 0.004;
  ctx.beginPath();
  ctx.moveTo(0, h * 0.44);
  ctx.lineTo(w, h * 0.44);
  ctx.stroke();
  ctx.restore();

  finish(ctx, w, h, 606);
}

/* ========================================================== GENERATIVE === */

const VIOLET = hex("#c3aef5");

/** 07 — a patch model read as particles that only see their neighbours. */
function interacting(ctx, w, h) {
  base(ctx, w, h, "#0a0814", "#04030a");
  const r = rng(707);

  // Clustered, not uniform: the interesting claim is that local rules make
  // global structure, and uniform noise makes that impossible to see.
  const hubs = [];
  for (let i = 0; i < 5; i++) hubs.push([r(), r()]);

  const N = 430;
  const pts = [];
  for (let i = 0; i < N; i++) {
    if (r() < 0.72) {
      const [hx, hy] = hubs[(r() * hubs.length) | 0];
      const a = r() * TAU;
      const d = Math.pow(r(), 0.65) * 0.22;
      pts.push([
        clamp(hx + Math.cos(a) * d, 0.02, 0.98) * w,
        clamp(hy + Math.sin(a) * d * 1.4, 0.02, 0.98) * h,
      ]);
    } else {
      pts.push([r() * w, r() * h]);
    }
  }

  glow(ctx, w * 0.42, h * 0.46, h * 1.1, VIOLET, 0.16);

  const REACH = h * 0.14;
  ctx.save();
  ctx.globalCompositeOperation = "lighter";
  ctx.lineWidth = h * 0.0022;
  for (let i = 0; i < N; i++) {
    for (let j = i + 1; j < N; j++) {
      const dx = pts[i][0] - pts[j][0];
      const dy = pts[i][1] - pts[j][1];
      const d = Math.hypot(dx, dy);
      if (d > REACH) continue;
      ctx.strokeStyle = rgba(VIOLET, 0.3 * Math.pow(1 - d / REACH, 2.2));
      ctx.beginPath();
      ctx.moveTo(pts[i][0], pts[i][1]);
      ctx.lineTo(pts[j][0], pts[j][1]);
      ctx.stroke();
    }
  }

  for (const [x, y] of pts) {
    const s = h * (0.004 + r() * 0.005);
    ctx.fillStyle = rgba(mix(VIOLET, CREAM, r() * 0.7), 0.55 + r() * 0.45);
    ctx.beginPath();
    ctx.arc(x, y, s, 0, TAU);
    ctx.fill();
  }
  ctx.restore();

  finish(ctx, w, h, 707);
}

/** 08 — one measure carried onto another along the map between them. */
function transport(ctx, w, h) {
  const n = makeNoise(808);
  const deep = hex("#08060f");
  const plum = hex("#3a2a5c");

  // The two measures, as a background density before anything is drawn on it.
  field(ctx, w, h, 3, (u, v, out) => {
    const a = Math.exp(
      -(Math.pow((u - 0.2) * 3.4, 2) + Math.pow((v - 0.62) * 2.6, 2)),
    );
    const b =
      Math.exp(
        -(Math.pow((u - 0.82) * 4.2, 2) + Math.pow((v - 0.3) * 3.4, 2)),
      ) +
      Math.exp(
        -(Math.pow((u - 0.72) * 5.5, 2) + Math.pow((v - 0.66) * 4.4, 2)),
      ) *
        0.8;
    const val = (a + b) * (0.8 + (n.fbm(u * 6, v * 6, 4) - 0.5) * 0.5);
    let c = mix(deep, plum, smoothstep(0, 0.7, val));
    c = mix(c, VIOLET, smoothstep(0.55, 1.4, val) * 0.55);
    out[0] = c[0];
    out[1] = c[1];
    out[2] = c[2];
  });

  // The map. Both sides are sampled by angle around their own centroid and
  // paired in that order, which is a monotone map — so the lines fan without
  // crossing, which is the whole point of the picture.
  const r = rng(808);
  const LINES = 76;
  const src = [];
  const dst = [];
  for (let i = 0; i < LINES; i++) {
    const a = (i / LINES) * TAU;
    const da = Math.pow(r(), 0.5);
    src.push([
      (0.2 + Math.cos(a) * da * 0.17) * w,
      (0.62 + Math.sin(a) * da * 0.26) * h,
    ]);
    const lobe = i % 2 === 0;
    dst.push([
      ((lobe ? 0.82 : 0.72) + Math.cos(a) * da * (lobe ? 0.12 : 0.1)) * w,
      ((lobe ? 0.3 : 0.66) + Math.sin(a) * da * (lobe ? 0.18 : 0.15)) * h,
    ]);
  }

  ctx.save();
  ctx.globalCompositeOperation = "lighter";
  for (let i = 0; i < LINES; i++) {
    const [x0, y0] = src[i];
    const [x1, y1] = dst[i];
    const g = ctx.createLinearGradient(x0, y0, x1, y1);
    g.addColorStop(0, rgba(VIOLET, 0.05));
    g.addColorStop(0.5, rgba(CREAM, 0.3));
    g.addColorStop(1, rgba(VIOLET, 0.05));
    ctx.strokeStyle = g;
    ctx.lineWidth = h * 0.0026;
    ctx.beginPath();
    ctx.moveTo(x0, y0);
    ctx.quadraticCurveTo(
      (x0 + x1) / 2,
      (y0 + y1) / 2 - h * 0.14 * (i % 2 ? 1 : -1),
      x1,
      y1,
    );
    ctx.stroke();
  }
  for (const [x, y] of [...src, ...dst]) {
    ctx.fillStyle = rgba(CREAM, 0.6);
    ctx.beginPath();
    ctx.arc(x, y, h * 0.0045, 0, TAU);
    ctx.fill();
  }
  ctx.restore();

  finish(ctx, w, h, 808);
}

/** 09 — the reverse process, read left to right: noise resolving into form. */
function emergence(ctx, w, h) {
  const n = makeNoise(909);
  const deep = hex("#08060f");
  const plum = hex("#3d2c60");

  field(ctx, w, h, 2, (u, v, out) => {
    const x = (u - 0.5) * 3;
    const y = (v - 0.5) * 2;
    const d = Math.hypot(x * 0.8, y);

    const raw = n.fbm(u * 34, v * 34, 5);
    const form = 0.5 + 0.5 * Math.cos(d * 13 - 1.2);

    // The schedule wobbles, so the front between the two is a front and not
    // a wipe.
    const t = smoothstep(
      0.05,
      0.95,
      u + (n.fbm(u * 2.4, v * 3.6, 3) - 0.5) * 0.3,
    );
    let val = raw + (form - raw) * t;
    val *= 1 - smoothstep(0.85, 1.45, d) * 0.55 * t;

    let c = mix(deep, plum, smoothstep(0.25, 0.75, val));
    c = mix(c, VIOLET, smoothstep(0.6, 1, val) * (0.35 + t * 0.6));
    c = mix(c, CREAM, smoothstep(0.88, 1, val) * t * 0.7);
    out[0] = c[0];
    out[1] = c[1];
    out[2] = c[2];
  });

  finish(ctx, w, h, 909);
}

/* ========================================================= SOFT MATTER === */

const MOSS = hex("#c3d98b");

/** 10 — one trajectory, and the √t it is spreading into. */
function brownian(ctx, w, h) {
  base(ctx, w, h, "#080c07", "#030503");

  // Its own stream, so choosing a walk below cannot shift the bath.
  const br = rng(1010);
  ctx.save();
  ctx.globalCompositeOperation = "lighter";
  for (let i = 0; i < 260; i++) {
    ctx.fillStyle = rgba(MOSS, 0.05 + br() * 0.12);
    ctx.beginPath();
    ctx.arc(br() * w, br() * h, h * (0.002 + br() * 0.004), 0, TAU);
    ctx.fill();
  }
  ctx.restore();

  const STEPS = 1300;
  const run = (seed) => {
    const r = rng(seed);
    const pts = [];
    let x = 0;
    let y = 0;
    let lo = [0, 0];
    let hi = [0, 0];
    let msd = 0;
    for (let i = 0; i < STEPS; i++) {
      // Box–Muller, so the steps are actually Gaussian.
      const u1 = Math.max(r(), 1e-9);
      const u2 = r();
      const mag = Math.sqrt(-2 * Math.log(u1));
      x += mag * Math.cos(TAU * u2);
      y += mag * Math.sin(TAU * u2);
      pts.push([x, y]);
      lo = [Math.min(lo[0], x), Math.min(lo[1], y)];
      hi = [Math.max(hi[0], x), Math.max(hi[1], y)];
      msd += x * x + y * y;
    }
    return { pts, lo, hi, msd: Math.sqrt(msd / STEPS) };
  };

  // A walk is one sample, and most samples are a poor drawing: too narrow for
  // the cell, or all of it in one corner. Eight are run and the one whose own
  // bounding box is nearest the cell's proportions is kept — art direction
  // over the seed, not over the physics, which is the same in all eight.
  let best = null;
  for (let i = 0; i < 8; i++) {
    const cand = run(1010 + i * 7919);
    const box = [cand.hi[0] - cand.lo[0], cand.hi[1] - cand.lo[1]];
    const err = Math.abs(Math.log(box[0] / box[1] / (w / h)));
    if (!best || err < best.err) best = { ...cand, err };
  }

  // Arbitrary units, so the trace is fitted to the cell rather than the step
  // size being tuned until one seed happens to land well. Uniform scale: an
  // isotropic walk squashed on one axis stops looking isotropic.
  const pad = h * 0.08;
  const k = Math.min(
    (w - pad * 2) / (best.hi[0] - best.lo[0]),
    (h - pad * 2) / (best.hi[1] - best.lo[1]),
  );
  const ox = (w - (best.hi[0] - best.lo[0]) * k) / 2 - best.lo[0] * k;
  const oy = (h - (best.hi[1] - best.lo[1]) * k) / 2 - best.lo[1] * k;
  const walk = best.pts.map(([px, py]) => [px * k + ox, py * k + oy]);

  // ⟨Δr²⟩ = 2dDt, so the guides go out as √t and not evenly, and they are
  // centred on where the walk actually started.
  ctx.save();
  ctx.setLineDash([h * 0.012, h * 0.016]);
  ctx.strokeStyle = rgba(MOSS, 0.26);
  ctx.lineWidth = 1;
  for (let i = 1; i <= 4; i++) {
    ctx.beginPath();
    ctx.arc(ox, oy, Math.sqrt(i / 4) * best.msd * k * 1.25, 0, TAU);
    ctx.stroke();
  }
  ctx.restore();

  glow(ctx, ox, oy, h * 0.75, MOSS, 0.13);

  ctx.save();
  ctx.globalCompositeOperation = "lighter";
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  for (let i = 1; i < STEPS; i++) {
    const t = i / STEPS;
    ctx.strokeStyle = rgba(mix(MOSS, CREAM, t * t), 0.14 + t * 0.6);
    ctx.lineWidth = h * (0.0028 + t * 0.005);
    ctx.beginPath();
    ctx.moveTo(walk[i - 1][0], walk[i - 1][1]);
    ctx.lineTo(walk[i][0], walk[i][1]);
    ctx.stroke();
  }
  ctx.restore();

  const [hx, hy] = walk[STEPS - 1];
  glow(ctx, hx, hy, h * 0.16, CREAM, 0.6);
  ctx.fillStyle = rgba(CREAM, 1);
  ctx.beginPath();
  ctx.arc(hx, hy, h * 0.011, 0, TAU);
  ctx.fill();

  finish(ctx, w, h, 1010);
}

/** 11 — beads on Hookean springs, in a Lennard-Jones bath. */
function beadSpring(ctx, w, h) {
  base(ctx, w, h, "#070b06", "#030503");
  const n = makeNoise(1111);
  const r = rng(1111);

  glow(ctx, w * 0.5, h * 0.5, h * 1.05, MOSS, 0.1);

  for (let c = 0; c < 3; c++) {
    const BEADS = 13;
    const pts = [];
    const y0 = 0.24 + c * 0.26;
    for (let i = 0; i < BEADS; i++) {
      const t = i / (BEADS - 1);
      pts.push([
        (0.09 + t * 0.82) * w,
        (y0 + (n.fbm(t * 3.4 + c * 9, c * 4.1, 4) - 0.5) * 0.36) * h,
      ]);
    }

    // Springs first, so the beads sit on top of their own coils.
    ctx.save();
    ctx.globalCompositeOperation = "lighter";
    ctx.strokeStyle = rgba(MOSS, 0.5);
    ctx.lineWidth = h * 0.0035;
    ctx.beginPath();
    for (let i = 1; i < BEADS; i++) {
      const [ax, ay] = pts[i - 1];
      const [bx, by] = pts[i];
      const dx = bx - ax;
      const dy = by - ay;
      const len = Math.hypot(dx, dy);
      const nx = -dy / len;
      const ny = dx / len;
      const turns = 7;
      const amp = h * 0.018;
      const seg = 40;
      for (let s = 0; s <= seg; s++) {
        const t = s / seg;
        // Held flat at the ends so the coil meets the bead cleanly.
        const env = Math.sin(t * Math.PI);
        const off = Math.sin(t * turns * TAU) * amp * env;
        const px = ax + dx * t + nx * off;
        const py = ay + dy * t + ny * off;
        if (s === 0) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
      }
    }
    ctx.stroke();
    ctx.restore();

    for (const [x, y] of pts) {
      const rad = h * (0.021 + r() * 0.008);
      glow(ctx, x, y, rad * 3.4, MOSS, 0.32);
      const g = ctx.createRadialGradient(
        x - rad * 0.35,
        y - rad * 0.4,
        rad * 0.1,
        x,
        y,
        rad,
      );
      g.addColorStop(0, rgba(CREAM, 0.98));
      g.addColorStop(0.4, rgba(MOSS, 0.85));
      g.addColorStop(1, rgba([0.05, 0.08, 0.04], 1));
      ctx.fillStyle = g;
      ctx.beginPath();
      ctx.arc(x, y, rad, 0, TAU);
      ctx.fill();
    }
  }

  finish(ctx, w, h, 1111);
}

/** 12 — the director field, summed from its own defects. */
function nematic(ctx, w, h) {
  // ±1/2 disclinations. θ = Σ qᵢ·atan2 is the actual solution of the
  // one-constant Frank free energy, so the brushes fall where they should.
  const DEFECTS = [
    { x: 0.24, y: 0.34, q: 0.5 },
    { x: 0.52, y: 0.68, q: -0.5 },
    { x: 0.74, y: 0.3, q: 0.5 },
    { x: 0.87, y: 0.74, q: -0.5 },
    { x: 0.08, y: 0.78, q: 0.5 },
  ];
  const A = 3 / 2; // cell aspect, to keep the field isotropic on screen

  const dir = (u, v) => {
    let th = 0.42;
    for (const d of DEFECTS) th += d.q * Math.atan2(v - d.y, (u - d.x) * A);
    return th;
  };

  const deep = hex("#040602");
  const moss = hex("#26301a");

  // Schlieren: what the same field looks like between crossed polarisers.
  field(ctx, w, h, 2, (u, v, out) => {
    const th = dir(u, v);
    let val = Math.pow(Math.abs(Math.sin(2 * th)), 1.1) * 0.66;
    // Order melts at the core, so each defect sits in its own dark spot.
    for (const d of DEFECTS) {
      val *= smoothstep(0, 0.06, Math.hypot((u - d.x) * A, v - d.y));
    }
    let c = mix(deep, moss, smoothstep(0, 0.45, val));
    c = mix(c, MOSS, smoothstep(0.32, 0.8, val) * 0.34);
    out[0] = c[0];
    out[1] = c[1];
    out[2] = c[2];
  });

  // The director itself, as a line field. No arrowheads: n and −n are the
  // same state and drawing a head would be the wrong physics.
  const r = rng(1212);
  const COLS = 34;
  const ROWS = 23;
  ctx.save();
  ctx.globalCompositeOperation = "lighter";
  ctx.lineCap = "round";
  for (let j = 0; j < ROWS; j++) {
    for (let i = 0; i < COLS; i++) {
      const u = (i + 0.5 + (r() - 0.5) * 0.6) / COLS;
      const v = (j + 0.5 + (r() - 0.5) * 0.6) / ROWS;
      const th = dir(u, v);

      let near = 1;
      for (const d of DEFECTS) {
        near = Math.min(
          near,
          smoothstep(0.01, 0.1, Math.hypot((u - d.x) * A, v - d.y)),
        );
      }
      if (near < 0.05) continue;

      const len = h * 0.019 * (0.6 + near * 0.6);
      const x = u * w;
      const y = v * h;
      ctx.strokeStyle = rgba(mix(MOSS, CREAM, 0.25), 0.12 + near * 0.28);
      ctx.lineWidth = h * 0.0026;
      ctx.beginPath();
      ctx.moveTo(x - (Math.cos(th) * len) / A, y - Math.sin(th) * len);
      ctx.lineTo(x + (Math.cos(th) * len) / A, y + Math.sin(th) * len);
      ctx.stroke();
    }
  }
  for (const d of DEFECTS) {
    const x = d.x * w;
    const y = d.y * h;
    glow(ctx, x, y, h * 0.075, d.q > 0 ? CREAM : MOSS, 0.3);
    ctx.fillStyle = rgba(CREAM, d.q > 0 ? 0.8 : 0.42);
    ctx.beginPath();
    ctx.arc(x, y, h * 0.0065, 0, TAU);
    ctx.fill();
  }
  ctx.restore();

  finish(ctx, w, h, 1212);
}

/* =============================================================== MOON === */

const PERI = hex("#9bb8f2");

function stars(ctx, w, h, seed, count) {
  const r = rng(seed);
  ctx.save();
  ctx.globalCompositeOperation = "lighter";
  for (let i = 0; i < count; i++) {
    const a = Math.pow(r(), 2.4);
    ctx.fillStyle = rgba(CREAM, a * 0.85);
    ctx.beginPath();
    ctx.arc(r() * w, r() * h, h * (0.0012 + a * 0.004), 0, TAU);
    ctx.fill();
  }
  ctx.restore();
}

/** 13 — the far side, still wireframe. A world that is being built. */
function proceduralMoon(ctx, w, h) {
  base(ctx, w, h, "#05070e", "#020306");
  stars(ctx, w, h, 1313, 150);

  const n = makeNoise(1313);
  const cx = w * 0.5;
  const cy = h * 0.5;
  const R = h * 0.4;
  // Light from the left, so the far limb falls away instead of ending.
  const L = [-0.62, -0.32, 0.72];

  glow(ctx, cx, cy, R * 2.4, PERI, 0.16);

  // Radius displaced by ridged noise on the sphere: craters and maria, not
  // a ball with a texture wrapped round it.
  const surf = (th, ph) => {
    const sx = Math.sin(ph) * Math.cos(th);
    const sy = Math.cos(ph);
    const sz = Math.sin(ph) * Math.sin(th);
    const relief =
      n.ridge(sx * 3 + 5, sz * 3 + sy * 1.7, 5) * 0.09 +
      n.fbm(sx * 7, sz * 7 + sy * 3, 4) * 0.045;
    const rad = R * (0.94 + relief);
    return [
      cx + sx * rad,
      cy + sy * rad,
      sz,
      sx * L[0] + sy * L[1] + sz * L[2],
    ];
  };

  const stroke = (pts) => {
    for (let i = 1; i < pts.length; i++) {
      const [x0, y0] = pts[i - 1];
      const [x1, y1, z, lit] = pts[i];
      if (z < -0.02) continue; // the back of the sphere stays hidden
      const front = smoothstep(-0.02, 0.35, z);
      const shade = 0.12 + clamp(lit, 0, 1) * 0.88;
      ctx.strokeStyle = rgba(
        mix(PERI, CREAM, shade * 0.6),
        front * shade * 0.75,
      );
      ctx.lineWidth = h * 0.0022 * (0.5 + front);
      ctx.beginPath();
      ctx.moveTo(x0, y0);
      ctx.lineTo(x1, y1);
      ctx.stroke();
    }
  };

  ctx.save();
  ctx.globalCompositeOperation = "lighter";
  for (let i = 1; i < 18; i++) {
    const ph = (i / 18) * Math.PI;
    const pts = [];
    for (let j = 0; j <= 110; j++) pts.push(surf((j / 110) * TAU, ph));
    stroke(pts);
  }
  for (let i = 0; i < 26; i++) {
    const th = (i / 26) * TAU;
    const pts = [];
    for (let j = 0; j <= 70; j++) pts.push(surf(th, (j / 70) * Math.PI));
    stroke(pts);
  }
  ctx.restore();

  // Terminator: a soft wash over the unlit side rather than a hard edge.
  ctx.save();
  ctx.globalCompositeOperation = "multiply";
  const term = ctx.createLinearGradient(
    cx - R,
    cy - R * 0.5,
    cx + R * 1.1,
    cy + R,
  );
  term.addColorStop(0, "rgba(255,255,255,1)");
  term.addColorStop(0.55, "rgba(120,130,160,1)");
  term.addColorStop(1, "rgba(30,34,48,1)");
  ctx.fillStyle = term;
  ctx.beginPath();
  ctx.arc(cx, cy, R * 1.06, 0, TAU);
  ctx.fill();
  ctx.restore();

  finish(ctx, w, h, 1313);
}

/** 14 — one seed, expanded: rooms, doors, the route between them. */
function levelSeed(ctx, w, h) {
  base(ctx, w, h, "#060812", "#020307");
  const r = rng(1414);

  // Binary space partition, the way the generator actually does it.
  let cells = [{ x: 0.05, y: 0.07, w: 0.9, h: 0.86 }];
  for (let pass = 0; pass < 3; pass++) {
    const next = [];
    for (const c of cells) {
      const vertical = c.w * 0.66 > c.h;
      const cut = 0.36 + r() * 0.28;
      if (vertical) {
        next.push({ x: c.x, y: c.y, w: c.w * cut, h: c.h });
        next.push({ x: c.x + c.w * cut, y: c.y, w: c.w * (1 - cut), h: c.h });
      } else {
        next.push({ x: c.x, y: c.y, w: c.w, h: c.h * cut });
        next.push({ x: c.x, y: c.y + c.h * cut, w: c.w, h: c.h * (1 - cut) });
      }
    }
    cells = next;
  }

  // A room inset inside each cell, so the corridors have somewhere to run.
  const rooms = cells.map((c) => {
    const pw = c.w * (0.5 + r() * 0.26);
    const ph = c.h * (0.46 + r() * 0.3);
    return {
      x: (c.x + (c.w - pw) * (0.2 + r() * 0.6)) * w,
      y: (c.y + (c.h - ph) * (0.2 + r() * 0.6)) * h,
      w: pw * w,
      h: ph * h,
    };
  });

  // Floor grid, under everything.
  ctx.save();
  ctx.strokeStyle = rgba(PERI, 0.07);
  ctx.lineWidth = 1;
  for (let x = 0; x < w; x += h * 0.055) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, h);
    ctx.stroke();
  }
  for (let y = 0; y < h; y += h * 0.055) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(w, y);
    ctx.stroke();
  }
  ctx.restore();

  // Corridors: always dogleg, never diagonal.
  ctx.save();
  ctx.globalCompositeOperation = "lighter";
  ctx.strokeStyle = rgba(PERI, 0.42);
  ctx.lineWidth = h * 0.006;
  for (let i = 1; i < rooms.length; i++) {
    const a = rooms[i - 1];
    const b = rooms[i];
    const ax = a.x + a.w / 2;
    const ay = a.y + a.h / 2;
    const bx = b.x + b.w / 2;
    const by = b.y + b.h / 2;
    ctx.beginPath();
    ctx.moveTo(ax, ay);
    ctx.lineTo(bx, ay);
    ctx.lineTo(bx, by);
    ctx.stroke();
  }
  ctx.restore();

  rooms.forEach((rm, i) => {
    const lit = i === 0 || i === rooms.length - 1;
    ctx.save();
    ctx.fillStyle = rgba(lit ? PERI : [0.06, 0.08, 0.14], lit ? 0.16 : 0.9);
    ctx.fillRect(rm.x, rm.y, rm.w, rm.h);
    ctx.globalCompositeOperation = "lighter";
    ctx.strokeStyle = rgba(lit ? CREAM : PERI, lit ? 0.9 : 0.42);
    ctx.lineWidth = h * (lit ? 0.005 : 0.003);
    ctx.strokeRect(rm.x, rm.y, rm.w, rm.h);
    ctx.restore();
    if (lit) glow(ctx, rm.x + rm.w / 2, rm.y + rm.h / 2, h * 0.3, PERI, 0.5);
  });

  finish(ctx, w, h, 1414);
}

/** 15 — the terrain that seed grows into, ridge by ridge. */
function terrain(ctx, w, h) {
  const n = makeNoise(1515);
  const sky = hex("#0b1226");
  const low = hex("#050711");

  field(ctx, w, h, 4, (u, v, out) => {
    const c = mix(sky, low, smoothstep(0, 0.85, v));
    out[0] = c[0];
    out[1] = c[1];
    out[2] = c[2];
  });
  stars(ctx, w, h, 1515, 120);
  glow(ctx, w * 0.76, h * 0.2, h * 0.5, PERI, 0.4);
  ctx.fillStyle = rgba(CREAM, 0.9);
  ctx.beginPath();
  ctx.arc(w * 0.76, h * 0.2, h * 0.045, 0, TAU);
  ctx.fill();

  // Back to front, each ridge filled opaque so it occludes the one behind.
  const RIDGES = 26;
  for (let i = 0; i < RIDGES; i++) {
    const t = i / (RIDGES - 1);
    const y0 = h * (0.34 + t * 0.72);
    const amp = h * (0.05 + t * 0.2);
    const pts = [];
    for (let x = 0; x <= w; x += w / 90) {
      const k = x / w;
      pts.push([
        x,
        y0 - n.ridge(k * (1.6 + t * 2.4) + i * 3.7, i * 1.31, 5) * amp,
      ]);
    }

    ctx.save();
    ctx.beginPath();
    pts.forEach(([x, y], j) => (j ? ctx.lineTo(x, y) : ctx.moveTo(x, y)));
    ctx.lineTo(w, h);
    ctx.lineTo(0, h);
    ctx.closePath();
    const g = ctx.createLinearGradient(0, y0 - amp, 0, y0 + h * 0.2);
    g.addColorStop(0, rgba(mix(low, PERI, 0.16 * (1 - t)), 1));
    g.addColorStop(1, rgba([0.01, 0.015, 0.03], 1));
    ctx.fillStyle = g;
    ctx.fill();

    ctx.globalCompositeOperation = "lighter";
    ctx.beginPath();
    pts.forEach(([x, y], j) => (j ? ctx.lineTo(x, y) : ctx.moveTo(x, y)));
    ctx.strokeStyle = rgba(mix(PERI, CREAM, 0.4), 0.15 + (1 - t) * 0.5);
    ctx.lineWidth = h * 0.0026;
    ctx.stroke();
    ctx.restore();
  }

  finish(ctx, w, h, 1515);
}

/* ============================================================== ASTRA === */

const ROSE = hex("#f0a2ad");

// The plan all three ASTRA plates are drawn on, in unit coordinates.
const HOUSE = [
  { x: 0.08, y: 0.14, w: 0.34, h: 0.4 },
  { x: 0.42, y: 0.14, w: 0.26, h: 0.24 },
  { x: 0.42, y: 0.38, w: 0.26, h: 0.16 },
  { x: 0.68, y: 0.14, w: 0.24, h: 0.4 },
  { x: 0.08, y: 0.54, w: 0.22, h: 0.32 },
  { x: 0.3, y: 0.54, w: 0.38, h: 0.32 },
  { x: 0.68, y: 0.54, w: 0.24, h: 0.32 },
];

function plan(ctx, w, h, alpha) {
  ctx.save();
  ctx.strokeStyle = rgba(ROSE, alpha);
  ctx.lineWidth = h * 0.005;
  ctx.lineJoin = "miter";
  for (const rm of HOUSE)
    ctx.strokeRect(rm.x * w, rm.y * h, rm.w * w, rm.h * h);
  ctx.restore();
}

/** 16 — the house as the scanner sees it: points, and the shadows behind. */
function pointCloud(ctx, w, h) {
  base(ctx, w, h, "#0d0709", "#040203");
  const r = rng(1616);

  // One station. Everything it can see is dense; everything a wall hides is
  // the gap that makes a second station necessary.
  const sx = 0.36;
  const sy = 0.64;

  glow(ctx, sx * w, sy * h, h * 0.55, ROSE, 0.3);

  ctx.save();
  ctx.globalCompositeOperation = "lighter";
  for (const rm of HOUSE) {
    // Points on the walls only — a lidar returns surfaces, not volumes.
    const edges = [
      [rm.x, rm.y, rm.x + rm.w, rm.y],
      [rm.x + rm.w, rm.y, rm.x + rm.w, rm.y + rm.h],
      [rm.x + rm.w, rm.y + rm.h, rm.x, rm.y + rm.h],
      [rm.x, rm.y + rm.h, rm.x, rm.y],
    ];
    for (const [x0, y0, x1, y1] of edges) {
      const len = Math.hypot((x1 - x0) * 1.5, y1 - y0);
      const N = Math.round(len * 420);
      for (let i = 0; i < N; i++) {
        const t = r();
        // Jitter along the surface normal: range noise, the reason a cloud
        // looks like a cloud and not like a line.
        const j = (r() - 0.5) * 0.006;
        const px = x0 + (x1 - x0) * t + (y1 - y0 ? j : 0);
        const py = y0 + (y1 - y0) * t + (x1 - x0 ? j : 0);

        const d = Math.hypot((px - sx) * 1.5, py - sy);
        const near = clamp(1 - d / 0.85, 0.06, 1);
        if (r() > near * 0.9 + 0.08) continue; // density falls off with range

        ctx.fillStyle = rgba(mix(ROSE, CREAM, near * 0.8), 0.18 + near * 0.72);
        ctx.fillRect(px * w, py * h, h * 0.0045, h * 0.0045);
      }
    }
  }
  ctx.restore();

  plan(ctx, w, h, 0.12);

  ctx.save();
  ctx.globalCompositeOperation = "lighter";
  ctx.fillStyle = rgba(CREAM, 1);
  ctx.beginPath();
  ctx.arc(sx * w, sy * h, h * 0.012, 0, TAU);
  ctx.fill();
  ctx.restore();

  finish(ctx, w, h, 1616);
}

/** 17 — coverage: where the stations overlap, and where nothing reaches. */
function coverage(ctx, w, h) {
  base(ctx, w, h, "#0b0708", "#030202");

  const STATIONS = [
    [0.2, 0.32],
    [0.54, 0.26],
    [0.8, 0.36],
    [0.22, 0.7],
    [0.52, 0.7],
    [0.82, 0.72],
  ];

  // Additive discs: two overlapping stations read brighter than one, which
  // is exactly the quantity the plan is solving for.
  ctx.save();
  ctx.globalCompositeOperation = "lighter";
  for (const [x, y] of STATIONS) {
    const R = h * 0.34;
    const g = ctx.createRadialGradient(x * w, y * h, 0, x * w, y * h, R);
    g.addColorStop(0, rgba(ROSE, 0.34));
    g.addColorStop(0.55, rgba(ROSE, 0.13));
    g.addColorStop(1, rgba(ROSE, 0));
    ctx.fillStyle = g;
    ctx.beginPath();
    ctx.arc(x * w, y * h, R, 0, TAU);
    ctx.fill();
  }
  ctx.restore();

  plan(ctx, w, h, 0.5);

  ctx.save();
  ctx.globalCompositeOperation = "lighter";
  for (const [x, y] of STATIONS) {
    ctx.strokeStyle = rgba(CREAM, 0.45);
    ctx.lineWidth = h * 0.0025;
    ctx.setLineDash([h * 0.01, h * 0.014]);
    ctx.beginPath();
    ctx.arc(x * w, y * h, h * 0.34, 0, TAU);
    ctx.stroke();
    ctx.setLineDash([]);

    glow(ctx, x * w, y * h, h * 0.09, CREAM, 0.6);
    ctx.fillStyle = rgba(CREAM, 1);
    ctx.beginPath();
    ctx.arc(x * w, y * h, h * 0.011, 0, TAU);
    ctx.fill();
  }
  ctx.restore();

  finish(ctx, w, h, 1717);
}

/** 18 — the route that visits them, in the order the capture runs. */
function scanPath(ctx, w, h) {
  base(ctx, w, h, "#0b0709", "#030203");
  plan(ctx, w, h, 0.22);

  const ROUTE = [
    [0.18, 0.74],
    [0.2, 0.34],
    [0.36, 0.46],
    [0.54, 0.26],
    [0.55, 0.46],
    [0.5, 0.7],
    [0.72, 0.68],
    [0.8, 0.36],
  ];

  // Catmull–Rom through the stops: a person walking, not a polyline.
  const smooth = [];
  for (let i = 0; i < ROUTE.length - 1; i++) {
    const p0 = ROUTE[Math.max(0, i - 1)];
    const p1 = ROUTE[i];
    const p2 = ROUTE[i + 1];
    const p3 = ROUTE[Math.min(ROUTE.length - 1, i + 2)];
    for (let s = 0; s < 24; s++) {
      const t = s / 24;
      const t2 = t * t;
      const t3 = t2 * t;
      smooth.push([
        0.5 *
          (2 * p1[0] +
            (-p0[0] + p2[0]) * t +
            (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 +
            (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3),
        0.5 *
          (2 * p1[1] +
            (-p0[1] + p2[1]) * t +
            (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 +
            (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3),
      ]);
    }
  }

  ctx.save();
  ctx.globalCompositeOperation = "lighter";
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  for (let i = 1; i < smooth.length; i++) {
    const t = i / smooth.length;
    ctx.strokeStyle = rgba(mix(ROSE, CREAM, t), 0.25 + t * 0.6);
    ctx.lineWidth = h * (0.004 + t * 0.005);
    ctx.beginPath();
    ctx.moveTo(smooth[i - 1][0] * w, smooth[i - 1][1] * h);
    ctx.lineTo(smooth[i][0] * w, smooth[i][1] * h);
    ctx.stroke();
  }

  ROUTE.forEach(([x, y], i) => {
    const t = i / (ROUTE.length - 1);
    const rad = h * 0.018;
    glow(ctx, x * w, y * h, h * 0.13, ROSE, 0.3 + t * 0.4);
    ctx.strokeStyle = rgba(mix(ROSE, CREAM, t), 0.9);
    ctx.lineWidth = h * 0.0035;
    ctx.beginPath();
    ctx.arc(x * w, y * h, rad, 0, TAU);
    ctx.stroke();
    ctx.fillStyle = rgba(CREAM, 0.35 + t * 0.6);
    ctx.beginPath();
    ctx.arc(x * w, y * h, rad * 0.36, 0, TAU);
    ctx.fill();
  });
  ctx.restore();

  finish(ctx, w, h, 1818);
}

/* ---------------------------------------------------------------------- */

export const PLATES = {
  cloudDeck,
  fugacity,
  descent,
  sinogram,
  backprojection,
  reconstruction,
  interacting,
  transport,
  emergence,
  brownian,
  beadSpring,
  nematic,
  proceduralMoon,
  levelSeed,
  terrain,
  pointCloud,
  coverage,
  scanPath,
};
