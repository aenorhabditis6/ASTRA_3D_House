(self.webpackChunk_N_E=self.webpackChunk_N_E||[]).push([[974],{1879:(e,t,a)=>{"use strict";a.d(t,{default:()=>et});var l=a(5155),o=a(2115),i=a(5269),r=a(9625),s=a(5911);let n=`
  varying vec2 vUv;

  void main() {
    vUv = uv;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`,h=`
  precision highp float;

  #define MAX_PLANES 32
  #define MAX_LINKS 32

  varying vec2 vUv;

  uniform vec2  uResolution;   // canvas size in px
  uniform vec2  uSize;         // resting plane size in px
  uniform float uRadius;       // resting corner radius in px

  // per-plane state, driven from JS
  uniform float uCount;
  uniform vec2  uPos[MAX_PLANES];    // centre in px, origin at screen centre
  uniform float uRot[MAX_PLANES];    // radians
  // xy = 0..1 per axis, z = brightness (1 = lit, 0 = black), w = which atlas
  // cell this plane wears. All three ride in here rather than in arrays of
  // their own because GLSL ES gives every element of a uniform array a full
  // vec4 row whatever it is declared as — zw were already being paid for and
  // thrown away. The cell is resolved on the CPU because it depends on where
  // the plane sits on the ring, not on its index, and working that out per
  // pixel in the loop below would be absurd.
  uniform vec4  uScale[MAX_PLANES];

  // honey threads between neighbours, driven from JS
  uniform float uLinkCount;
  uniform vec2  uLinkA[MAX_LINKS];
  uniform vec2  uLinkB[MAX_LINKS];
  // (radius at the ends, radius at the pinch, droop, fillet)
  uniform vec4  uLinkPar[MAX_LINKS];

  uniform float uK;            // smin blend strength in px
  uniform float uWobble;       // surface tension noise amount, px
  uniform float uTime;
  uniform vec3  uColor;
  uniform vec3  uPage;         // what is behind the ring, for the tag to read

  // All the artwork lives in one atlas: ESSL 1.00 cannot index an array of
  // samplers with a varying index, so a per-plane texture is not an option.
  uniform sampler2D uAtlas;
  uniform vec2  uGrid;         // atlas cells across, down
  uniform float uBlend;        // px over which neighbouring art crossfades
  uniform float uTextured;

  // --- ASCII particle opening ---------------------------------------------
  // Real glyphs rasterised into a tiny atlas for the intro assembly.
  uniform sampler2D uAsciiTex;
  uniform vec4 uIntro; // gather progress, cloud expansion, cell px, opacity
  uniform vec4 uCardParticles; // launch, reach px, cell px, opacity
  uniform vec2 uFocusParticlePos;
  uniform vec4 uFocusParticleBox; // half size, radius, rotation
  uniform vec4 uFocusParticles; // amount, reach px, cell px, opacity
  uniform vec2 uFocusParticleMotion; // flow phase, motion multiplier

  // --- pointer -------------------------------------------------------------
  // Nothing is ever drawn at the cursor. It only changes how the ring behaves
  // around it: the field goes soft, and a wake runs out through the surface.
  // Packed into vec4s for the same reason the link parameters are.
  uniform vec4 uMouse;  // cursor.xy px, presence 0..1, blend px added at it
  uniform vec4 uMelt;   // reach px, wake px, wake frequency, wake speed

  // --- the cursor tag ------------------------------------------------------
  // Drawn in this pass with everything else rather than as an element over the
  // canvas. That is what lets its label inspect the pixels it is sitting on and
  // invert against them, and it means the glass refracts the ring the same way
  // the lip does instead of having to sample it back out of a backdrop.
  uniform sampler2D uTagTex;  // the label; only its alpha is used, as a mask
  uniform vec4 uTag;   // centre.xy px, scale.xy — scale 0 is simply absent
  uniform vec4 uTagP;  // half width, half height, corner radius, refract px
  uniform vec4 uTagQ;  // frost, rim gain, unused, unused

  vec2 atlasUV(vec2 uv, float idx) {
    float col = mod(idx, uGrid.x);
    float row = floor(idx / uGrid.x);
    return (vec2(col, row) + uv) / uGrid;
  }

  float hash21(vec2 p) {
    p = fract(p * vec2(123.34, 456.21));
    p += dot(p, p + 45.32);
    return fract(p.x * p.y);
  }

  // --- glass lip -----------------------------------------------------------
  // A band along the top and bottom of the screen behaving like the rounded
  // edge of a thick glass sheet. Because the whole scene is evaluated from p,
  // warping p here refracts the planes and the honey together, with no second
  // pass and no render target.
  uniform float uBandTop;     // px
  uniform float uBandBottom;  // px
  uniform vec4  uGlass;       // refract px, squeeze, ripple px, ripple freq
  uniform float uFringe;      // px of chromatic split inside the band
  uniform float uSheen;       // lift applied across the lip

  // Warps p in place and returns how deep into the lip this pixel sits, 0..1.
  float glassBend(inout vec2 p) {
    float band = p.y > 0.0 ? uBandTop : uBandBottom;
    if (band <= 0.5) return 0.0;

    float dy = abs(p.y) - (uResolution.y * 0.5 - band);
    if (dy <= 0.0) return 0.0;

    float t = clamp(dy / band, 0.0, 1.0);
    // Circular profile: barely bends at the inner edge, falls away sharply at
    // the very edge, which is what reads as thickness rather than a gradient.
    float bend = 1.0 - sqrt(max(0.0, 1.0 - t * t));

    float s = sign(p.y);
    // Sampling back toward centre throws content outward, so the image
    // stretches forward into the lip and swells as it reaches the edge.
    // Both terms are signed: negatives invert the lip and compress instead.
    p.y -= s * bend * (uGlass.x + sin(p.x * uGlass.w) * uGlass.z);
    p.x *= 1.0 - bend * uGlass.y;

    return bend;
  }

  // --- simplex noise -------------------------------------------------------
  // Copyright (C) 2011 Ashima Arts. All rights reserved.
  // Copyright (C) 2011-2016 by Stefan Gustavson (Classic noise and others)
  // Distributed under the MIT License. https://github.com/ashima/webgl-noise
  vec3 mod289(vec3 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
  vec2 mod289(vec2 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
  vec3 permute(vec3 x) { return mod289(((x * 34.0) + 1.0) * x); }

  float snoise(vec2 v) {
    const vec4 C = vec4(0.211324865405187, 0.366025403784439,
                       -0.577350269189626, 0.024390243902439);
    vec2 i  = floor(v + dot(v, C.yy));
    vec2 x0 = v - i + dot(i, C.xx);
    vec2 i1 = (x0.x > x0.y) ? vec2(1.0, 0.0) : vec2(0.0, 1.0);
    vec4 x12 = x0.xyxy + C.xxzz;
    x12.xy -= i1;
    i = mod289(i);
    vec3 p = permute(permute(i.y + vec3(0.0, i1.y, 1.0))
                            + i.x + vec3(0.0, i1.x, 1.0));
    vec3 m = max(0.5 - vec3(dot(x0, x0), dot(x12.xy, x12.xy),
                            dot(x12.zw, x12.zw)), 0.0);
    m = m * m; m = m * m;
    vec3 x = 2.0 * fract(p * C.www) - 1.0;
    vec3 h = abs(x) - 0.5;
    vec3 ox = floor(x + 0.5);
    vec3 a0 = x - ox;
    m *= 1.79284291400159 - 0.85373472095314 * (a0 * a0 + h * h);
    vec3 g;
    g.x  = a0.x  * x0.x  + h.x  * x0.y;
    g.yz = a0.yz * x12.xz + h.yz * x12.yw;
    return 130.0 * dot(m, g);
  }

  // --- sdf helpers ---------------------------------------------------------
  float sdRoundBox(vec2 p, vec2 b, float r) {
    vec2 q = abs(p) - b + r;
    return min(max(q.x, q.y), 0.0) + length(max(q, 0.0)) - r;
  }

  // The honey between two planes: a flat slab spanning centre to centre, as
  // wide as the edges it comes off and pinched in the middle, drooping under
  // its own weight.
  //
  // Deliberately not a capsule. A capsule has a round cross-section, so at
  // full merge it bulges out past the flat sides of the planes themselves.
  // This is swept as a box, so while the planes overlap it stays entirely
  // inside them and the silhouette reads as one flat card.
  float sdBridge(vec2 p, vec2 a, vec2 b, float rEnd, float rMid, float sag) {
    vec2 ba = b - a;
    float len = length(ba);
    if (len < 0.001) return 1e6;

    vec2 dir = ba / len;
    vec2 nrm = vec2(-dir.y, dir.x);

    vec2 q = p - (a + b) * 0.5;
    float along = dot(q, dir);
    float across = dot(q, nrm);

    float h = clamp(along / len + 0.5, 0.0, 1.0);
    float bell = sin(3.14159265 * h);           // 0 at the ends, 1 in the middle

    // droop, world -Y, resolved onto the across axis
    across += sag * bell * nrm.y;

    float taper = pow(1.0 - bell, 1.7);         // 1 at the ends, 0 in the middle
    float r = mix(rMid, rEnd, taper);

    // Ends are square and buried inside the planes, so they never show.
    return max(abs(along) - len * 0.5, abs(across) - r);
  }

  // The tag's own outline, scaled by whatever the pop animation is doing.
  float sdTag(vec2 p) {
    vec2 hs = uTagP.xy * abs(uTag.zw);
    return sdRoundBox(p - uTag.xy, hs, min(uTagP.z, min(hs.x, hs.y)));
  }

  // Its surface normal, by difference. A pill's normal is vertical along the
  // flat edges and radial round the ends, so nothing simpler than this gets the
  // refraction pointing the right way the whole way round.
  vec2 tagNormal(vec2 p) {
    vec2 e = vec2(1.0, 0.0);
    vec2 g = vec2(
      sdTag(p + e.xy) - sdTag(p - e.xy),
      sdTag(p + e.yx) - sdTag(p - e.yx)
    );
    float l = length(g);
    return l > 0.0001 ? g / l : vec2(0.0);
  }

  // smooth minimum — this is what makes the shapes read as liquid.
  // Note it also behaves as a plain min() when a is the 1e6 sentinel.
  float smin(float a, float b, float k) {
    if (k <= 0.0001) return min(a, b);
    float h = clamp(0.5 + 0.5 * (b - a) / k, 0.0, 1.0);
    return mix(b, a, h) - k * h * (1.0 - h);
  }

  vec4 introParticles(vec2 p) {
    float t = clamp(uIntro.x, 0.0, 1.0);
    float gather = t * t * (3.0 - 2.0 * t);
    float cloudScale = mix(max(1.0, uIntro.y), 1.0, gather);

    // Work in the seed card's local frame so the opening follows the image as
    // the centre card begins its launch onto the ring.
    vec2 q = p - uPos[0];
    float a = uRot[0];
    float ca = cos(a), sa = sin(a);
    q = vec2(q.x * ca + q.y * sa, -q.x * sa + q.y * ca);

    vec2 target = q / cloudScale;
    vec2 halfSize = max(uSize * 0.5, vec2(1.0));
    vec2 normalised = target / halfSize;
    float diamondD = abs(normalised.x) + abs(normalised.y) - 1.0;
    float boxD = max(abs(normalised.x), abs(normalised.y)) - 1.0;
    float shapeMorph = smoothstep(0.35, 0.92, gather);
    float shapeD = mix(diamondD, boxD, shapeMorph);
    if (shapeD > 0.0) return vec4(0.0);

    float cell = max(uIntro.z, 5.0);
    float radius = max(length(q), 1.0);
    float ripple = sin(
      uTime * 1.4 + (abs(q.x) + abs(q.y)) * 0.018
    );
    vec2 current = q +
      (q / radius) * ripple * cell * 0.38 * (1.0 - gather);
    vec2 gridP = current / cell;
    vec2 mirrored = abs(gridP);
    vec2 tile = floor(mirrored);
    vec2 glyphUv = fract(mirrored);
    float seed = hash21(tile + 71.19);

    vec2 imageUv = target / uSize + 0.5;
    imageUv.y = 1.0 - imageUv.y;
    imageUv = clamp(imageUv, 0.004, 0.996);
    vec3 art = uTextured > 0.5
      ? texture2D(uAtlas, atlasUV(imageUv, uScale[0].w)).rgb
      : uColor;
    float luminance = dot(art, vec3(0.2126, 0.7152, 0.0722));

    float imageInfluence = smoothstep(0.28, 0.88, gather);
    float density = mix(0.30, 0.90, gather);
    float present = step(seed, density);
    float glyphBase = 3.0 + seed * 2.0;
    float glyphImage =
      (1.0 - luminance) * 4.8 + gather * 1.35 + seed * 0.8;
    float glyph = floor(clamp(
      mix(glyphBase, glyphImage, imageInfluence),
      0.0, 6.0
    ));
    vec2 atlasP = vec2((glyph + glyphUv.x) / 7.0, glyphUv.y);
    float mask = texture2D(uAsciiTex, atlasP).a;

    float born = smoothstep(0.0, 0.09, t);
    float handoff = 1.0 - smoothstep(0.58, 0.96, t);
    float pulse = 0.82 + 0.18 * sin(uTime * 3.2 + seed * 6.2831853);
    float cloudEdge = 1.0 - smoothstep(-0.16, 0.0, shapeD);
    float alpha =
      mask * present * born * handoff * pulse * cloudEdge * uIntro.w;

    // Keep pale source pixels legible on the paper field without flattening
    // the image back to monochrome.
    vec3 particle = mix(uColor, mix(uColor, art, 0.68), imageInfluence);
    return vec4(particle, alpha);
  }

  vec4 singleCardParticles(vec2 p) {
    float gather = clamp(uIntro.x, 0.0, 1.0);
    float launch = clamp(uCardParticles.x, 0.0, 1.0);
    float enter = smoothstep(0.52, 0.94, gather);
    float leave = smoothstep(0.04, 0.76, launch);
    float life = enter * (1.0 - leave);
    if (life <= 0.001) return vec4(0.0);

    // The field belongs only to the seed card. It rotates and contracts with
    // that card, then dies before the fan starts opening into a ring.
    vec2 q = p - uPos[0];
    float a = uRot[0];
    float ca = cos(a), sa = sin(a);
    q = vec2(q.x * ca + q.y * sa, -q.x * sa + q.y * ca);

    vec2 seedScale = max(uScale[0].xy, vec2(0.08));
    vec2 halfSize = max(uSize * 0.5 * seedScale, vec2(1.0));
    float cardD = sdRoundBox(q, halfSize, min(uRadius, halfSize.y));
    float reach = max(uCardParticles.y, 8.0);

    // A four-axis diamond holds the particles behind the card instead of
    // allowing a circular fog. The inner cutout keeps the photograph crisp.
    vec2 outerHalf = halfSize + vec2(reach * 1.35, reach);
    float diamondD =
      abs(q.x / outerHalf.x) + abs(q.y / outerHalf.y) - 1.0;
    float envelope = 1.0 - smoothstep(-0.10, 0.0, diamondD);
    float outside = smoothstep(1.5, 5.0, cardD);
    float falloff = 1.0 - smoothstep(0.0, reach, cardD);
    float field = envelope * outside * pow(max(falloff, 0.0), 0.72);
    if (field <= 0.001) return vec4(0.0);

    float cell = max(uCardParticles.z, 5.0);
    float radius = max(length(q), 1.0);
    vec2 direction = q / radius;

    // Positive travel pulls mirrored rows inward. The sign reverses on exit,
    // so the same glyphs visibly peel back out through the four diamond tips.
    float travel = enter * 2.2 - leave * 5.0 + uTime * 0.16 * life;
    vec2 particleP = q + direction * cell * travel;
    vec2 gridP = abs(particleP / cell);
    vec2 tile = floor(gridP);
    vec2 glyphUv = fract(gridP);
    float seed = hash21(tile + 143.57);

    float density = mix(0.12, 0.66, enter) *
                    mix(0.62, 1.0, pow(max(falloff, 0.0), 0.55));
    float present = step(seed, density);
    float glyph = floor(clamp(
      falloff * 5.2 + seed * 1.45,
      0.0, 6.0
    ));
    vec2 atlasP = vec2((glyph + glyphUv.x) / 7.0, glyphUv.y);
    float mask = texture2D(uAsciiTex, atlasP).a;

    float phase = hash21(tile + 29.31) * 6.2831853;
    float pulse = 0.76 + 0.24 * sin(uTime * 3.0 + phase);
    float alpha =
      mask * present * field * life * pulse * uCardParticles.w;
    return vec4(uColor, alpha);
  }

  vec4 hoveredCardParticles(vec2 p) {
    float amount = clamp(uFocusParticles.x, 0.0, 1.0);
    if (amount <= 0.001) return vec4(0.0);

    vec2 q = p - uFocusParticlePos;
    float a = uFocusParticleBox.w;
    float ca = cos(a), sa = sin(a);
    q = vec2(q.x * ca + q.y * sa, -q.x * sa + q.y * ca);

    vec2 halfSize = max(uFocusParticleBox.xy, vec2(1.0));
    float cardD = sdRoundBox(q, halfSize, uFocusParticleBox.z);
    float reach = max(uFocusParticles.y, 8.0);

    // Restore the original loose shadow field: distance from the rounded card
    // controls density, with no geometric envelope and no mirrored quadrants.
    float outside = smoothstep(1.5, 5.0, cardD);
    float falloff = 1.0 - smoothstep(0.0, reach, cardD);
    float field = outside * pow(max(falloff, 0.0), 1.25);
    if (field <= 0.001) return vec4(0.0);

    float cell = max(uFocusParticles.z, 5.0);
    float radius = max(length(q), 1.0);
    vec2 direction = q / radius;
    float travel =
      (uFocusParticleMotion.x + amount * 3.6) * uFocusParticleMotion.y;
    vec2 drift = vec2(
      uTime * 0.45 * cell,
      sin(uTime * 1.7 + q.x * 0.013) * cell * 0.34
    ) * uFocusParticleMotion.y;
    vec2 particleP = q + direction * cell * travel + drift;
    vec2 gridP = particleP / cell;
    vec2 tile = floor(gridP);
    vec2 glyphUv = fract(gridP);
    float seed = hash21(tile + 223.41);

    float density = mix(0.10, 0.76, pow(max(falloff, 0.0), 0.72)) *
                    mix(0.28, 1.0, amount);
    float present = step(seed, density);
    float glyph = floor(clamp(
      falloff * 6.35 + (seed - 0.5) * 1.35,
      0.0, 6.0
    ));
    vec2 atlasP = vec2((glyph + glyphUv.x) / 7.0, glyphUv.y);
    float mask = texture2D(uAsciiTex, atlasP).a;

    float phase = hash21(tile + 47.13) * 6.2831853;
    float movingPulse = 0.74 + 0.26 * sin(uTime * 3.2 + phase);
    float pulse = mix(1.0, movingPulse, uFocusParticleMotion.y);
    float alpha =
      mask * present * field * amount * pulse * uFocusParticles.w;
    return vec4(uColor, alpha);
  }

  void main() {
    // Screen position, kept unbent: the tag is pinned to the cursor, so it is
    // placed and drawn here rather than in the lip's warped space.
    vec2 ps = (vUv - 0.5) * uResolution;

    vec2 p = ps;
    float bend = glassBend(p);

    // The tag refracts whatever is under it, so its warp has to be applied to
    // the sampling position before the field is read — the same order the lip
    // works in. Flat through the middle, bending hard at the rim, which is what
    // reads as a thickness of glass rather than a smear.
    float dTag = sdTag(ps);
    float tagOn = min(abs(uTag.z), abs(uTag.w));
    if (tagOn > 0.001 && dTag < 0.0 && uTagP.w > 0.0) {
      float depth = clamp(-dTag / max(uTagP.y * abs(uTag.w), 1.0), 0.0, 1.0);
      float t = 1.0 - depth;
      p += tagNormal(ps) * (1.0 - sqrt(max(0.0, 1.0 - t * t))) * uTagP.w;
    }

    // Read after the bend, so the cursor acts in the same warped space as the
    // ring: dragged into the lip, its influence is refracted with everything
    // else rather than sitting flat on top of it.
    float toMouse = length(p - uMouse.xy);

    // Blend strength is lifted in a halo around the cursor, so the ring goes
    // soft exactly where it is being touched and stays crisp everywhere else.
    // Resolved once per pixel rather than per plane: it costs one length().
    float k = uK;
    if (uMouse.z > 0.001) {
      float t = 1.0 - smoothstep(0.0, max(uMelt.x, 1.0), toMouse);
      k += uMouse.w * uMouse.z * t * t;
    }

    float d = 1e6;

    // The two planes nearest this pixel, tracked alongside the field so the
    // colour can be resolved without a second pass. In the goo between two
    // planes both are close, which is exactly where the crossfade belongs.
    float d0 = 1e6, d1 = 1e6;
    vec2 uv0 = vec2(0.5), uv1 = vec2(0.5);
    float im0 = 0.0, im1 = 0.0;
    float dm0 = 1.0, dm1 = 1.0;

    float halfSpan = length(uSize) * 0.5;

    for (int i = 0; i < MAX_PLANES; i++) {
      if (float(i) >= uCount) break;

      vec4 st = uScale[i];
      vec2 sc = st.xy;
      float grown = max(sc.x, sc.y);
      if (grown <= 0.0001) continue;

      vec2 q = p - uPos[i];
      // Anything further out than this cannot affect the surface, so it can be
      // skipped outright — this is what keeps 32 planes affordable. Scaled by
      // the plane rather than fixed, because a plane swollen under the cursor
      // reaches further than its resting size, as does the melt around it.
      float cull = halfSpan * grown + k + uWobble + 8.0;
      if (dot(q, q) > cull * cull) continue;

      // into the plane's local frame
      float a  = uRot[i];
      float ca = cos(a), sa = sin(a);
      q = vec2(q.x * ca + q.y * sa, -q.x * sa + q.y * ca);

      vec2 halfSize = max(uSize * 0.5 * sc, vec2(0.0001));

      // starts as a circle (r = half extent), relaxes into the rounded rect
      float rMax = min(halfSize.x, halfSize.y);
      float r = min(rMax, mix(rMax, uRadius, smoothstep(0.30, 1.0, min(sc.x, sc.y))));

      float di = sdRoundBox(q, halfSize, r);
      d = smin(d, di, k);

      // Local UV. Clamped, so the goo outside a plane carries that plane's
      // edge colour rather than repeating or sampling the next atlas cell.
      vec2 luv = q / (2.0 * halfSize) + 0.5;
      luv.y = 1.0 - luv.y;
      luv = clamp(luv, 0.004, 0.996);

      if (di < d0) {
        d1 = d0; uv1 = uv0; im1 = im0; dm1 = dm0;
        d0 = di; uv0 = luv; im0 = st.w; dm0 = st.z;
      } else if (di < d1) {
        d1 = di; uv1 = luv; im1 = st.w; dm1 = st.z;
      }
    }

    // Threads strung between neighbours as they pull apart.
    for (int i = 0; i < MAX_LINKS; i++) {
      if (float(i) >= uLinkCount) break;

      vec4 par = uLinkPar[i];
      // Radii are allowed to go negative: that lifts the bridge's field clear
      // of the surface so it fades out, rather than bottoming out at zero as a
      // half-covered hairline. Only cull once it is further out than the
      // antialiasing can reach.
      if (par.x <= -3.0) continue;

      vec2 a = uLinkA[i];
      vec2 b = uLinkB[i];
      vec2 mid = (a + b) * 0.5;
      float reach = length(b - a) * 0.5 + par.x + par.w + 8.0;
      if (dot(p - mid, p - mid) > reach * reach) continue;

      d = smin(d, sdBridge(p, a, b, par.x, par.y, par.z), par.w);
    }

    // Surface tension wobble, decays to zero so resting planes are dead flat.
    if (uWobble > 0.001) {
      float n = snoise(p * 0.012 + vec2(uTime * 0.22, uTime * -0.17));
      d += n * uWobble;
    }

    // A capillary wake off the cursor, amplitude driven by how fast it is
    // moving. Rings out from it and dies over the same reach the softening
    // uses, so a flick leaves a ripple in the surface that outlives the
    // movement that made it.
    if (uMelt.y > 0.001) {
      d += sin(toMouse * uMelt.z - uTime * uMelt.w)
         * uMelt.y * exp(-toMouse / max(uMelt.x, 1.0));
    }

    // Clamped, not just floored: the distance cull above leaves a step in the
    // field, and an unclamped fwidth across that step paints a half-opaque
    // outline along every cull boundary.
    float aa = clamp(fwidth(d), 0.5, 2.0);
    float alpha = 1.0 - smoothstep(-aa, aa, d);

    vec4 intro = vec4(0.0);
    if (uIntro.w > 0.001 && uIntro.x < 0.999) {
      intro = introParticles(p);
    }
    vec4 cardParticles = vec4(0.0);
    if (
      uCardParticles.w > 0.001 &&
      uIntro.x > 0.48 &&
      uCardParticles.x < 0.80
    ) {
      cardParticles = singleCardParticles(p);
    }
    vec4 focusParticles = vec4(0.0);
    if (uFocusParticles.x > 0.001) {
      focusParticles = hoveredCardParticles(p);
    }

    // The tag has to survive this: it can overhang the edge of a card, and
    // those pixels are its own even though the ring has nothing there.
    float taa = clamp(fwidth(dTag), 0.5, 2.0);
    float ta = tagOn > 0.001 ? 1.0 - smoothstep(-taa, taa, dTag) : 0.0;

    if (
      alpha <= 0.001 &&
      ta <= 0.001 &&
      focusParticles.a <= 0.001 &&
      cardParticles.a <= 0.001 &&
      intro.a <= 0.001
    ) discard;

    // Even mix where the two nearest planes are equidistant, resolving to
    // whichever is clearly nearer beyond uBlend. Both the art and the dim are
    // carried across on it, so neither can put a seam down the goo.
    float nearest = smoothstep(-uBlend, uBlend, d1 - d0);

    vec3 col = uColor;
    if (uTextured > 0.5) {
      vec3 c0, c1;

      // Uniform branch, so the derivatives the mip selection needs stay
      // defined. The offset is scaled by bend, so outside the lip the three
      // taps land on the same texel and there is no fringe.
      if (uFringe > 0.0) {
        vec2 fr = vec2(uFringe * bend / max(uSize.x, 1.0), 0.0);
        c0 = vec3(
          texture2D(uAtlas, atlasUV(uv0 + fr, im0)).r,
          texture2D(uAtlas, atlasUV(uv0, im0)).g,
          texture2D(uAtlas, atlasUV(uv0 - fr, im0)).b
        );
        c1 = vec3(
          texture2D(uAtlas, atlasUV(uv1 + fr, im1)).r,
          texture2D(uAtlas, atlasUV(uv1, im1)).g,
          texture2D(uAtlas, atlasUV(uv1 - fr, im1)).b
        );
      } else {
        c0 = texture2D(uAtlas, atlasUV(uv0, im0)).rgb;
        c1 = texture2D(uAtlas, atlasUV(uv1, im1)).rgb;
      }

      col = mix(c1, c0, nearest);
    }

    // Cards standing off the one being pointed at are turned down, so the
    // hovered card reads as the lit one. Untextured, uColor is already almost
    // black and there is nothing here to see — which is fine, that mode exists
    // to read the goo's silhouette.
    col *= mix(dm1, dm0, nearest);

    // A touch of lift where the lip is steepest, so the band reads as a
    // surface catching light rather than only a warp.
    col += bend * uSheen;

    // Composite both particle phases behind the photographic surface. This
    // keeps antialiased card edges clean instead of tinting them like an
    // outline, and prevents the field from following the completed ring.
    if (cardParticles.a > 0.001) {
      float combined = alpha + cardParticles.a * (1.0 - alpha);
      col = (col * alpha +
             cardParticles.rgb * cardParticles.a * (1.0 - alpha)) /
            max(combined, 0.0001);
      alpha = combined;
    }
    if (focusParticles.a > 0.001) {
      float combined = alpha + focusParticles.a * (1.0 - alpha);
      col = (col * alpha +
             focusParticles.rgb * focusParticles.a * (1.0 - alpha)) /
            max(combined, 0.0001);
      alpha = combined;
    }
    if (intro.a > 0.001) {
      float combined = alpha + intro.a * (1.0 - alpha);
      col = (col * alpha + intro.rgb * intro.a * (1.0 - alpha)) /
            max(combined, 0.0001);
      alpha = combined;
    }
    // --- the tag -------------------------------------------------------------
    if (ta > 0.001) {
        // Where the ring does not reach, the page is what shows through the
        // glass, so the label has something real to read there too.
        vec3 under = mix(uPage, col, alpha);
        vec3 glass = mix(under, vec3(1.0), uTagQ.x);

        // Rim: lit where it faces the light, dark where it turns away. Signing
        // it is what gives an edge that reads as thickness rather than as an
        // outline drawn on.
        float band = clamp(1.0 + dTag / max(uTagP.z, 1.0), 0.0, 1.0);
        glass += band * band * uTagQ.y *
                 dot(tagNormal(ps), vec2(-0.7071, 0.7071));

        // The label. Pure black or pure white, decided per pixel from what that
        // pixel is sitting on, so a glyph crossing a light edge onto a dark one
        // changes colour halfway across. A blend cannot do this — inverting a
        // mid grey returns a mid grey — and picking one colour for the whole
        // label cannot either.
        vec2 tuv = (ps - uTag.xy) / (uTagP.xy * 2.0 * abs(uTag.zw)) + 0.5;
        float m = texture2D(uTagTex, clamp(tuv, 0.0, 1.0)).a;
        float l = dot(glass, vec3(0.2126, 0.7152, 0.0722));
        // Narrow, not hard: a step here would alias along the boundary.
        glass = mix(glass, vec3(1.0 - smoothstep(0.46, 0.54, l)), m);

      col = mix(col, glass, ta);
      alpha = max(alpha, ta);
    }

    // Written straight through. The atlas is tagged NoColorSpace so sampling
    // returns the authored sRGB values, and this shader adds no output
    // encoding of its own — decoding on read without encoding on write is
    // what darkens everything.
    gl_FragColor = vec4(col, alpha);
  }
`,u=2*Math.PI,c=(e,t,a)=>e<t?t:e>a?a:e,d=(e,t,a)=>{let l=c((a-e)/(t-e),0,1);return l*l*(3-2*l)};function f(e){let t=e>>>0;return()=>{let e=Math.imul((t=t+0x6d2b79f5>>>0)^t>>>15,1|t);return(((e=e+Math.imul(e^e>>>7,61|e)^e)^e>>>14)>>>0)/0x100000000}}function p(e){let t=f(e),a=new Float32Array(65536);for(let e=0;e<a.length;e++)a[e]=t();let l=(e,t)=>a[(255&t)*256+(255&e)],o=e=>e*e*(3-2*e),i=(e,t)=>{let a=Math.floor(e),i=Math.floor(t),r=o(e-a),s=o(t-i),n=l(a,i),h=l(a+1,i),u=l(a,i+1);return n+(h-n)*r+(u-n)*s+(n-h-u+l(a+1,i+1))*r*s};return i.fbm=(e,t,a=5,l=.5)=>{let o=0,r=1,s=0,n=e,h=t;for(let e=0;e<a;e++)o+=r*i(n,h),s+=r,r*=l,n=2.03*n+37.1,h=2.01*h-19.7;return o/s},i.ridge=(e,t,a=5)=>{let l=0,o=1,r=0,s=e,n=t;for(let e=0;e<a;e++){let e=1-Math.abs(2*i(s,n)-1);l+=o*e*e,r+=o,o*=.5,s=2.07*s+11.3,n=2.02*n-5.9}return l/r},i}let m=e=>[parseInt(e.slice(1,3),16)/255,parseInt(e.slice(3,5),16)/255,parseInt(e.slice(5,7),16)/255],g=(e,t,a)=>[e[0]+(t[0]-e[0])*a,e[1]+(t[1]-e[1])*a,e[2]+(t[2]-e[2])*a],v=(e,t)=>`rgba(${Math.round(255*c(e[0],0,1))},${Math.round(255*c(e[1],0,1))},${Math.round(255*c(e[2],0,1))},${t})`,y=m("#f7ecd9");function x(e,t,a,l,o){let i=Math.max(2,Math.round(t/l)),r=Math.max(2,Math.round(a/l)),s=document.createElement("canvas");s.width=i,s.height=r;let n=s.getContext("2d"),h=n.createImageData(i,r),u=h.data,d=[0,0,0];for(let e=0;e<r;e++)for(let t=0;t<i;t++){o((t+.5)/i,(e+.5)/r,d);let a=(e*i+t)*4;u[a]=255*c(d[0],0,1),u[a+1]=255*c(d[1],0,1),u[a+2]=255*c(d[2],0,1),u[a+3]=255}n.putImageData(h,0,0),e.imageSmoothingEnabled=!0,e.imageSmoothingQuality="high",e.drawImage(s,0,0,t,a)}function b(e,t,a,l="#0a0c11",o="#04050a"){let i=e.createLinearGradient(0,0,.7*t,a);i.addColorStop(0,l),i.addColorStop(1,o),e.fillStyle=i,e.fillRect(0,0,t,a)}function w(e,t,a,l,o,i){let r=e.createRadialGradient(t,a,0,t,a,l);r.addColorStop(0,v(o,i)),r.addColorStop(.45,v(o,.3*i)),r.addColorStop(1,v(o,0)),e.save(),e.globalCompositeOperation="lighter",e.fillStyle=r,e.fillRect(t-l,a-l,2*l,2*l),e.restore()}function M(e,t,a,l){e.save(),e.globalCompositeOperation="lighter";let o=e.createLinearGradient(0,a,.9*t,0);o.addColorStop(0,"rgba(255,255,255,0)"),o.addColorStop(.45,"rgba(255,246,232,0.055)"),o.addColorStop(.62,"rgba(255,246,232,0.02)"),o.addColorStop(1,"rgba(255,255,255,0)"),e.fillStyle=o,e.fillRect(0,0,t,a),e.globalCompositeOperation="multiply";let i=e.createRadialGradient(.5*t,.48*a,.2*a,.5*t,.5*a,.95*a);i.addColorStop(0,"rgba(255,255,255,1)"),i.addColorStop(1,"rgba(150,150,160,1)"),e.fillStyle=i,e.fillRect(0,0,t,a);let r=document.createElement("canvas");r.width=128,r.height=128;let s=r.getContext("2d"),n=s.createImageData(128,128),h=f(977*l+13);for(let e=0;e<n.data.length;e+=4){let t=110+60*h();n.data[e]=t,n.data[e+1]=t,n.data[e+2]=t,n.data[e+3]=255}s.putImageData(n,0,0),e.globalCompositeOperation="overlay",e.globalAlpha=.16;let u=e.createPattern(r,"repeat");e.fillStyle=u,e.fillRect(0,0,t,a),e.restore()}let S=m("#f2b46b"),P=m("#9fdbe0"),T=[{x:.03,y:.06,r:.78,d:.16},{x:0,y:.21,r:.3,d:.62},{x:0,y:-.13,r:.115,d:-.36},{x:-.43,y:-.05,r:.12,d:.95},{x:.43,y:-.05,r:.12,d:.95},{x:0,y:-.5,r:.1,d:.9}];function k(e,t,a){let l=0;for(let o of T){let i=o.x*t+o.y*a,r=o.r*o.r-(e-i)*(e-i);r>0&&(l+=o.d*Math.sqrt(r))}return l}let C=m("#c3aef5"),A=m("#c3d98b"),R=m("#9bb8f2");function F(e,t,a,l,o){let i=f(l);e.save(),e.globalCompositeOperation="lighter";for(let l=0;l<o;l++){let l=Math.pow(i(),2.4);e.fillStyle=v(y,.85*l),e.beginPath(),e.arc(i()*t,i()*a,a*(.0012+.004*l),0,u),e.fill()}e.restore()}let z=m("#f0a2ad"),q=[{x:.08,y:.14,w:.34,h:.4},{x:.42,y:.14,w:.26,h:.24},{x:.42,y:.38,w:.26,h:.16},{x:.68,y:.14,w:.24,h:.4},{x:.08,y:.54,w:.22,h:.32},{x:.3,y:.54,w:.38,h:.32},{x:.68,y:.54,w:.24,h:.32}];function O(e,t,a,l){for(let o of(e.save(),e.strokeStyle=v(z,l),e.lineWidth=.005*a,e.lineJoin="miter",q))e.strokeRect(o.x*t,o.y*a,o.w*t,o.h*a);e.restore()}let E=[{id:"venus",type:"Planetary",year:"2024",label:"NASA VfOx",meta:"Student Lead \xb7 DAVINCI / APL",blurb:"In-situ numerical analysis of the Venus atmosphere for the Oxygen Fugacity sensor, alongside instrument design, assembly and testing.",plates:[{id:"cloud-deck",name:"Cloud Deck",art:function(e,t,a){let l=p(11),o=m("#140a04"),i=m("#7d4415");x(e,t,a,2.5,(e,t,a)=>{let r=l.fbm(3.1*e+11,2.2*t,4)-.5,s=l.fbm(2.4*e,3.4*t+7,4)-.5,n=c(.6*(.5*Math.sin((t+.5*s)*12.5+3.6*r)+.5)+.55*l.fbm(5.5*e+2.4*r,8*t+2.4*s,6),0,1),h=d(-.3,1.2,.72*e+(1-t)*.48),u=g(o,i,d(.16,.64,n));u=g(u,S,d(.54,.96,n)*(.32+.78*h)),u=g(u,y,d(.87,1,n)*h*.8),a[0]=u[0],a[1]=u[1],a[2]=u[2]}),M(e,t,a,11)}},{id:"fugacity",name:"Oxygen Fugacity",art:function(e,t,a){b(e,t,a,"#0c0a08","#040303");let l=.5*t,o=.5*a,i=.38*a,r=f(202);w(e,l,o,2.6*i,S,.22),e.save();for(let t=9;t>=1;t--){let a=i*(.34+t/9*.66),r=e.createLinearGradient(l-a,o-a,l+a,o+a),s=.1+t/9*.12;r.addColorStop(0,`rgba(${210*s*2},${205*s*2},${200*s*2},1)`),r.addColorStop(.5,`rgba(${30*s},${28*s},${26*s},1)`),r.addColorStop(1,`rgba(${190*s*2},${180*s*2},${168*s*2},1)`),e.strokeStyle=r,e.lineWidth=.055*i,e.beginPath(),e.arc(l,o,a,0,u),e.stroke()}e.restore(),e.save(),e.globalCompositeOperation="lighter";let s=e.createRadialGradient(l,o,0,l,o,.42*i);s.addColorStop(0,v(y,.95)),s.addColorStop(.35,v(S,.8)),s.addColorStop(1,v(S,0)),e.fillStyle=s,e.beginPath(),e.arc(l,o,.42*i,0,u),e.fill(),e.restore(),e.save(),e.globalCompositeOperation="lighter";for(let t=0;t<46;t++){let t=r()*u,s=i*(1.5+1.1*r()),n=i*(.45+.25*r()),h=(r()-.5)*.8;e.beginPath();for(let a=0;a<=22;a++){let i=a/22,r=s+(n-s)*i,u=t+h*i*i,c=l+Math.cos(u)*r,d=o+Math.sin(u)*r*.94;0===a?e.moveTo(c,d):e.lineTo(c,d)}e.strokeStyle=v(S,.06+.1*r()),e.lineWidth=.004*a,e.stroke();let c=t+h;e.fillStyle=v(y,.5+.4*r()),e.beginPath(),e.arc(l+Math.cos(c)*n,o+Math.sin(c)*n*.94,.005*a,0,u),e.fill()}e.restore(),e.save(),e.strokeStyle=v(y,.16),e.lineWidth=1.2;for(let t=0;t<72;t++){let a=t/72*u,r=t%6==0,s=1.12*i,n=i*(r?1.24:1.18);e.globalAlpha=r?.5:.22,e.beginPath(),e.moveTo(l+Math.cos(a)*s,o+Math.sin(a)*s),e.lineTo(l+Math.cos(a)*n,o+Math.sin(a)*n),e.stroke()}e.restore(),M(e,t,a,202)}},{id:"descent",name:"Descent Profile",art:function(e,t,a){let l=p(303),o=m("#0a0603"),i=m("#6b3d16");x(e,t,a,3,(e,t,a)=>{let r=Math.pow(t,1.7),s=l.fbm(4*e+3,7*t,4)-.5,n=.5*Math.sin(22*t+2.6*s)+.5,h=g(o,i,.85*r+.12*n);h=g(h,S,d(.55,1,r)*(.18+.22*n)),a[0]=h[0],a[1]=h[1],a[2]=h[2]}),e.save(),e.strokeStyle=v(y,.1),e.lineWidth=1;for(let l=1;l<9;l++){let o=l/9*a;e.beginPath(),e.moveTo(.06*t,o),e.lineTo(.94*t,o),e.stroke()}e.restore();let r=[];for(let e=0;e<=160;e++){let o=e/160,i=l.fbm(5*o+2,1.5,4)-.5;r.push([t*(.14+.7*o+.16*i),a*(.05+.9*Math.pow(o,1.25))])}for(let[t,l]of(e.save(),e.globalCompositeOperation="lighter",e.lineCap="round",[[.045*a,.1],[.018*a,.22],[.006*a,.9]]))e.beginPath(),r.forEach(([t,a],l)=>l?e.lineTo(t,a):e.moveTo(t,a)),e.strokeStyle=v(t<.01*a?y:S,l),e.lineWidth=t,e.stroke();e.restore();let[s,n]=r[Math.floor(115.19999999999999)];w(e,s,n,.22*a,S,.55),e.fillStyle=v(y,.98),e.beginPath(),e.arc(s,n,.012*a,0,u),e.fill(),M(e,t,a,303)}}]},{id:"tomography",type:"Tomography",year:"2025",label:"Stanford RSL",meta:"Research Intern \xb7 REU",blurb:"A 2.5D physics-informed diffusion model for sparse-view cone-beam CT, with the Radon transform as a forward constraint and anatomical fidelity checked downstream.",link:"https://drive.google.com/file/d/1dviuzmckyB8s-0lzJKJfOB2dXtAYdcyc/view?usp=sharing",linkLabel:"Research poster",plates:[{id:"sinogram",name:"Sparse Sinogram",art:function(e,t,a){let l=p(404),o=m("#030708"),i=m("#1d3c44");x(e,t,a,2,(e,t,a)=>{let r=e*Math.PI,s=3.1*k((t-.5)*2,Math.cos(r),Math.sin(r)),n=Math.floor(33*e),h=2*Math.abs(33*e%1-.5);s*=n%3==0?1:.07+.05*d(.78,1,h);let u=g(o,i,d(0,.4,s+=(l(180*e,180*t)-.5)*.04));u=g(u,P,d(.3,.8,s)),u=g(u,y,d(.72,1.05,s)),a[0]=u[0],a[1]=u[1],a[2]=u[2]}),M(e,t,a,404)}},{id:"backprojection",name:"Back Projection",art:function(e,t,a){let l=p(505),o=m("#03070a"),i=m("#1b3a46"),r=[];for(let e=0;e<7;e++){let t=e/7*Math.PI;r.push([Math.cos(t),Math.sin(t)])}x(e,t,a,2,(e,t,a)=>{let s=(e-.5)*3,n=(t-.5)*2,h=0;for(let e=0;e<7;e++)h+=k(s*r[e][0]+n*r[e][1],r[e][0],r[e][1]);let u=(h/7-.05)/.23;u*=1-.92*d(.85,1.4,Math.hypot(s,n));let c=g(o,i,d(0,.45,u+=(l(90*e,90*t)-.5)*.05));c=g(c,P,.9*d(.42,1,u)),c=g(c,y,.5*d(.92,1.25,u)),a[0]=c[0],a[1]=c[1],a[2]=c[2]}),M(e,t,a,505)}},{id:"reconstruction",name:"Reconstruction",art:function(e,t,a){let l=p(606),o=m("#03070a"),i=m("#1c3c47");x(e,t,a,2,(e,t,a)=>{let r=(e-.5)*3,s=(t-.5)*2,n=0;for(let e of T)n+=e.d*(1-d(.7*e.r,1.01*e.r,Math.hypot(r-e.x,s-e.y)));n*=(1.35+(l.fbm(11*e,16*t,4)-.5)*.9)*(1-.95*d(.95,1.3,Math.hypot(r,s)));let h=g(o,i,d(0,.42,n+=.22*Math.exp(-Math.pow((t-.44)*9,2))));h=g(h,P,d(.35,.95,n)),h=g(h,y,.85*d(.78,1.3,n)),a[0]=h[0],a[1]=h[1],a[2]=h[2]}),e.save(),e.globalCompositeOperation="lighter",e.strokeStyle=v(y,.5),e.lineWidth=.004*a,e.beginPath(),e.moveTo(0,.44*a),e.lineTo(t,.44*a),e.stroke(),e.restore(),M(e,t,a,606)}}]},{id:"generative",type:"Generative",year:"2025",label:"Johns Hopkins",meta:"Research Assistant \xb7 with Dr. Fei Lu",blurb:"Patch-based generative models written as interacting particle systems, using statistical mechanics and optimal transport to study convergence and mode coverage.",plates:[{id:"interacting",name:"Interacting Particles",art:function(e,t,a){b(e,t,a,"#0a0814","#04030a");let l=f(707),o=[];for(let e=0;e<5;e++)o.push([l(),l()]);let i=[];for(let e=0;e<430;e++)if(.72>l()){let[e,r]=o[l()*o.length|0],s=l()*u,n=.22*Math.pow(l(),.65);i.push([c(e+Math.cos(s)*n,.02,.98)*t,c(r+Math.sin(s)*n*1.4,.02,.98)*a])}else i.push([l()*t,l()*a]);w(e,.42*t,.46*a,1.1*a,C,.16);let r=.14*a;e.save(),e.globalCompositeOperation="lighter",e.lineWidth=.0022*a;for(let t=0;t<430;t++)for(let a=t+1;a<430;a++){let l=Math.hypot(i[t][0]-i[a][0],i[t][1]-i[a][1]);l>r||(e.strokeStyle=v(C,.3*Math.pow(1-l/r,2.2)),e.beginPath(),e.moveTo(i[t][0],i[t][1]),e.lineTo(i[a][0],i[a][1]),e.stroke())}for(let[t,o]of i){let i=a*(.004+.005*l());e.fillStyle=v(g(C,y,.7*l()),.55+.45*l()),e.beginPath(),e.arc(t,o,i,0,u),e.fill()}e.restore(),M(e,t,a,707)}},{id:"transport",name:"Optimal Transport",art:function(e,t,a){let l=p(808),o=m("#08060f"),i=m("#3a2a5c");x(e,t,a,3,(e,t,a)=>{let r=(Math.exp(-(Math.pow((e-.2)*3.4,2)+Math.pow((t-.62)*2.6,2)))+(Math.exp(-(Math.pow((e-.82)*4.2,2)+Math.pow((t-.3)*3.4,2)))+.8*Math.exp(-(Math.pow((e-.72)*5.5,2)+Math.pow((t-.66)*4.4,2)))))*(.8+(l.fbm(6*e,6*t,4)-.5)*.5),s=g(o,i,d(0,.7,r));s=g(s,C,.55*d(.55,1.4,r)),a[0]=s[0],a[1]=s[1],a[2]=s[2]});let r=f(808),s=[],n=[];for(let e=0;e<76;e++){let l=e/76*u,o=Math.pow(r(),.5);s.push([(.2+Math.cos(l)*o*.17)*t,(.62+Math.sin(l)*o*.26)*a]);let i=e%2==0;n.push([((i?.82:.72)+Math.cos(l)*o*(i?.12:.1))*t,((i?.3:.66)+Math.sin(l)*o*(i?.18:.15))*a])}e.save(),e.globalCompositeOperation="lighter";for(let t=0;t<76;t++){let[l,o]=s[t],[i,r]=n[t],h=e.createLinearGradient(l,o,i,r);h.addColorStop(0,v(C,.05)),h.addColorStop(.5,v(y,.3)),h.addColorStop(1,v(C,.05)),e.strokeStyle=h,e.lineWidth=.0026*a,e.beginPath(),e.moveTo(l,o),e.quadraticCurveTo((l+i)/2,(o+r)/2-.14*a*(t%2?1:-1),i,r),e.stroke()}for(let[t,l]of[...s,...n])e.fillStyle=v(y,.6),e.beginPath(),e.arc(t,l,.0045*a,0,u),e.fill();e.restore(),M(e,t,a,808)}},{id:"emergence",name:"Noise to Form",art:function(e,t,a){let l=p(909),o=m("#08060f"),i=m("#3d2c60");x(e,t,a,2,(e,t,a)=>{let r=Math.hypot((e-.5)*3*.8,(t-.5)*2),s=l.fbm(34*e,34*t,5),n=.5+.5*Math.cos(13*r-1.2),h=d(.05,.95,e+(l.fbm(2.4*e,3.6*t,3)-.5)*.3),u=s+(n-s)*h;u*=1-.55*d(.85,1.45,r)*h;let c=g(o,i,d(.25,.75,u));c=g(c,C,d(.6,1,u)*(.35+.6*h)),c=g(c,y,d(.88,1,u)*h*.7),a[0]=c[0],a[1]=c[1],a[2]=c[2]}),M(e,t,a,909)}}]},{id:"soft-matter",type:"Soft Matter",year:"2024",label:"Beller Group",meta:"Undergraduate Researcher \xb7 Johns Hopkins",blurb:"Brownian dynamics of active particles and bead-spring chains under Lennard-Jones potentials and Hookean springs, on self-propulsion and diffusion in nematic-shaped particles.",link:"https://drive.google.com/file/d/1Z1x8eYSvfKmizgS9J_TXseVaaQUHejTi/view?usp=sharing",linkLabel:"Research summary",plates:[{id:"brownian",name:"Brownian Path",art:function(e,t,a){b(e,t,a,"#080c07","#030503");let l=f(1010);e.save(),e.globalCompositeOperation="lighter";for(let o=0;o<260;o++)e.fillStyle=v(A,.05+.12*l()),e.beginPath(),e.arc(l()*t,l()*a,a*(.002+.004*l()),0,u),e.fill();e.restore();let o=e=>{let t=f(e),a=[],l=0,o=0,i=[0,0],r=[0,0],s=0;for(let e=0;e<1300;e++){let e=Math.max(t(),1e-9),n=t(),h=Math.sqrt(-2*Math.log(e));l+=h*Math.cos(u*n),o+=h*Math.sin(u*n),a.push([l,o]),i=[Math.min(i[0],l),Math.min(i[1],o)],r=[Math.max(r[0],l),Math.max(r[1],o)],s+=l*l+o*o}return{pts:a,lo:i,hi:r,msd:Math.sqrt(s/1300)}},i=null;for(let e=0;e<8;e++){let l=o(1010+7919*e),r=[l.hi[0]-l.lo[0],l.hi[1]-l.lo[1]],s=Math.abs(Math.log(r[0]/r[1]/(t/a)));(!i||s<i.err)&&(i={...l,err:s})}let r=.08*a,s=Math.min((t-2*r)/(i.hi[0]-i.lo[0]),(a-2*r)/(i.hi[1]-i.lo[1])),n=(t-(i.hi[0]-i.lo[0])*s)/2-i.lo[0]*s,h=(a-(i.hi[1]-i.lo[1])*s)/2-i.lo[1]*s,c=i.pts.map(([e,t])=>[e*s+n,t*s+h]);e.save(),e.setLineDash([.012*a,.016*a]),e.strokeStyle=v(A,.26),e.lineWidth=1;for(let t=1;t<=4;t++)e.beginPath(),e.arc(n,h,Math.sqrt(t/4)*i.msd*s*1.25,0,u),e.stroke();e.restore(),w(e,n,h,.75*a,A,.13),e.save(),e.globalCompositeOperation="lighter",e.lineCap="round",e.lineJoin="round";for(let t=1;t<1300;t++){let l=t/1300;e.strokeStyle=v(g(A,y,l*l),.14+.6*l),e.lineWidth=a*(.0028+.005*l),e.beginPath(),e.moveTo(c[t-1][0],c[t-1][1]),e.lineTo(c[t][0],c[t][1]),e.stroke()}e.restore();let[d,p]=c[1299];w(e,d,p,.16*a,y,.6),e.fillStyle=v(y,1),e.beginPath(),e.arc(d,p,.011*a,0,u),e.fill(),M(e,t,a,1010)}},{id:"bead-spring",name:"Bead and Spring",art:function(e,t,a){b(e,t,a,"#070b06","#030503");let l=p(1111),o=f(1111);w(e,.5*t,.5*a,1.05*a,A,.1);for(let i=0;i<3;i++){let r=[],s=.24+.26*i;for(let e=0;e<13;e++){let o=e/12;r.push([(.09+.82*o)*t,(s+(l.fbm(3.4*o+9*i,4.1*i,4)-.5)*.36)*a])}e.save(),e.globalCompositeOperation="lighter",e.strokeStyle=v(A,.5),e.lineWidth=.0035*a,e.beginPath();for(let t=1;t<13;t++){let[l,o]=r[t-1],[i,s]=r[t],n=i-l,h=s-o,c=Math.hypot(n,h),d=-h/c,f=n/c,p=.018*a;for(let t=0;t<=40;t++){let a=t/40,i=Math.sin(a*Math.PI),r=Math.sin(7*a*u)*p*i,s=l+n*a+d*r,c=o+h*a+f*r;0===t?e.moveTo(s,c):e.lineTo(s,c)}}for(let[t,l]of(e.stroke(),e.restore(),r)){let i=a*(.021+.008*o());w(e,t,l,3.4*i,A,.32);let r=e.createRadialGradient(t-.35*i,l-.4*i,.1*i,t,l,i);r.addColorStop(0,v(y,.98)),r.addColorStop(.4,v(A,.85)),r.addColorStop(1,v([.05,.08,.04],1)),e.fillStyle=r,e.beginPath(),e.arc(t,l,i,0,u),e.fill()}}M(e,t,a,1111)}},{id:"nematic",name:"Nematic Defects",art:function(e,t,a){let l=[{x:.24,y:.34,q:.5},{x:.52,y:.68,q:-.5},{x:.74,y:.3,q:.5},{x:.87,y:.74,q:-.5},{x:.08,y:.78,q:.5}],o=(e,t)=>{let a=.42;for(let o of l)a+=o.q*Math.atan2(t-o.y,(e-o.x)*1.5);return a},i=m("#040602"),r=m("#26301a");x(e,t,a,2,(e,t,a)=>{let s=.66*Math.pow(Math.abs(Math.sin(2*o(e,t))),1.1);for(let a of l)s*=d(0,.06,Math.hypot((e-a.x)*1.5,t-a.y));let n=g(i,r,d(0,.45,s));n=g(n,A,.34*d(.32,.8,s)),a[0]=n[0],a[1]=n[1],a[2]=n[2]});let s=f(1212);e.save(),e.globalCompositeOperation="lighter",e.lineCap="round";for(let i=0;i<23;i++)for(let r=0;r<34;r++){let n=(r+.5+(s()-.5)*.6)/34,h=(i+.5+(s()-.5)*.6)/23,u=o(n,h),c=1;for(let e of l)c=Math.min(c,d(.01,.1,Math.hypot((n-e.x)*1.5,h-e.y)));if(c<.05)continue;let f=.019*a*(.6+.6*c),p=n*t,m=h*a;e.strokeStyle=v(g(A,y,.25),.12+.28*c),e.lineWidth=.0026*a,e.beginPath(),e.moveTo(p-Math.cos(u)*f/1.5,m-Math.sin(u)*f),e.lineTo(p+Math.cos(u)*f/1.5,m+Math.sin(u)*f),e.stroke()}for(let o of l){let l=o.x*t,i=o.y*a;w(e,l,i,.075*a,o.q>0?y:A,.3),e.fillStyle=v(y,o.q>0?.8:.42),e.beginPath(),e.arc(l,i,.0065*a,0,u),e.fill()}e.restore(),M(e,t,a,1212)}}]},{id:"moon",type:"Game Physics",year:"2024",label:"Backside of the Moon",meta:"Founder \xb7 Pava Accelerator",blurb:"An SCP-style roguelike: procedural level generation, game AI and physics integration, funded by the Pava Accelerator and the Engineering Department.",link:"https://github.com/ZichenFrankFu/Backside_of_the_Moon",linkLabel:"Game repository",plates:[{id:"far-side",name:"Far Side",art:function(e,t,a){b(e,t,a,"#05070e","#020306"),F(e,t,a,1313,150);let l=p(1313),o=.5*t,i=.5*a,r=.4*a;w(e,o,i,2.4*r,R,.16);let s=(e,t)=>{let a=Math.sin(t)*Math.cos(e),s=Math.cos(t),n=Math.sin(t)*Math.sin(e),h=r*(.94+(.09*l.ridge(3*a+5,3*n+1.7*s,5)+.045*l.fbm(7*a,7*n+3*s,4)));return[o+a*h,i+s*h,n,-.62*a+-.32*s+.72*n]},n=t=>{for(let l=1;l<t.length;l++){let[o,i]=t[l-1],[r,s,n,h]=t[l];if(n<-.02)continue;let u=d(-.02,.35,n),f=.12+.88*c(h,0,1);e.strokeStyle=v(g(R,y,.6*f),u*f*.75),e.lineWidth=.0022*a*(.5+u),e.beginPath(),e.moveTo(o,i),e.lineTo(r,s),e.stroke()}};e.save(),e.globalCompositeOperation="lighter";for(let e=1;e<18;e++){let t=e/18*Math.PI,a=[];for(let e=0;e<=110;e++)a.push(s(e/110*u,t));n(a)}for(let e=0;e<26;e++){let t=e/26*u,a=[];for(let e=0;e<=70;e++)a.push(s(t,e/70*Math.PI));n(a)}e.restore(),e.save(),e.globalCompositeOperation="multiply";let h=e.createLinearGradient(o-r,i-.5*r,o+1.1*r,i+r);h.addColorStop(0,"rgba(255,255,255,1)"),h.addColorStop(.55,"rgba(120,130,160,1)"),h.addColorStop(1,"rgba(30,34,48,1)"),e.fillStyle=h,e.beginPath(),e.arc(o,i,1.06*r,0,u),e.fill(),e.restore(),M(e,t,a,1313)}},{id:"level-seed",name:"Level Seed",art:function(e,t,a){b(e,t,a,"#060812","#020307");let l=f(1414),o=[{x:.05,y:.07,w:.9,h:.86}];for(let e=0;e<3;e++){let e=[];for(let t of o){let a=.66*t.w>t.h,o=.36+.28*l();a?(e.push({x:t.x,y:t.y,w:t.w*o,h:t.h}),e.push({x:t.x+t.w*o,y:t.y,w:t.w*(1-o),h:t.h})):(e.push({x:t.x,y:t.y,w:t.w,h:t.h*o}),e.push({x:t.x,y:t.y+t.h*o,w:t.w,h:t.h*(1-o)}))}o=e}let i=o.map(e=>{let o=e.w*(.5+.26*l()),i=e.h*(.46+.3*l());return{x:(e.x+(e.w-o)*(.2+.6*l()))*t,y:(e.y+(e.h-i)*(.2+.6*l()))*a,w:o*t,h:i*a}});e.save(),e.strokeStyle=v(R,.07),e.lineWidth=1;for(let l=0;l<t;l+=.055*a)e.beginPath(),e.moveTo(l,0),e.lineTo(l,a),e.stroke();for(let l=0;l<a;l+=.055*a)e.beginPath(),e.moveTo(0,l),e.lineTo(t,l),e.stroke();e.restore(),e.save(),e.globalCompositeOperation="lighter",e.strokeStyle=v(R,.42),e.lineWidth=.006*a;for(let t=1;t<i.length;t++){let a=i[t-1],l=i[t],o=a.x+a.w/2,r=a.y+a.h/2,s=l.x+l.w/2,n=l.y+l.h/2;e.beginPath(),e.moveTo(o,r),e.lineTo(s,r),e.lineTo(s,n),e.stroke()}e.restore(),i.forEach((t,l)=>{let o=0===l||l===i.length-1;e.save(),e.fillStyle=v(o?R:[.06,.08,.14],o?.16:.9),e.fillRect(t.x,t.y,t.w,t.h),e.globalCompositeOperation="lighter",e.strokeStyle=v(o?y:R,o?.9:.42),e.lineWidth=a*(o?.005:.003),e.strokeRect(t.x,t.y,t.w,t.h),e.restore(),o&&w(e,t.x+t.w/2,t.y+t.h/2,.3*a,R,.5)}),M(e,t,a,1414)}},{id:"terrain",name:"Night Terrain",art:function(e,t,a){let l=p(1515),o=m("#0b1226"),i=m("#050711");x(e,t,a,4,(e,t,a)=>{let l=g(o,i,d(0,.85,t));a[0]=l[0],a[1]=l[1],a[2]=l[2]}),F(e,t,a,1515,120),w(e,.76*t,.2*a,.5*a,R,.4),e.fillStyle=v(y,.9),e.beginPath(),e.arc(.76*t,.2*a,.045*a,0,u),e.fill();for(let o=0;o<26;o++){let r=o/25,s=a*(.34+.72*r),n=a*(.05+.2*r),h=[];for(let e=0;e<=t;e+=t/90){let a=e/t;h.push([e,s-l.ridge(a*(1.6+2.4*r)+3.7*o,1.31*o,5)*n])}e.save(),e.beginPath(),h.forEach(([t,a],l)=>l?e.lineTo(t,a):e.moveTo(t,a)),e.lineTo(t,a),e.lineTo(0,a),e.closePath();let u=e.createLinearGradient(0,s-n,0,s+.2*a);u.addColorStop(0,v(g(i,R,.16*(1-r)),1)),u.addColorStop(1,v([.01,.015,.03],1)),e.fillStyle=u,e.fill(),e.globalCompositeOperation="lighter",e.beginPath(),h.forEach(([t,a],l)=>l?e.lineTo(t,a):e.moveTo(t,a)),e.strokeStyle=v(g(R,y,.4),.15+(1-r)*.5),e.lineWidth=.0026*a,e.stroke(),e.restore()}M(e,t,a,1515)}}]},{id:"astra",type:"Spatial Capture",year:"2026",label:"ASTRA",meta:"Capture planning \xb7 this repository",blurb:"Planning a house scan: where to stand, what each station can actually see, and the route that covers the whole place in one pass.",plates:[{id:"point-cloud",name:"Point Cloud",art:function(e,t,a){b(e,t,a,"#0d0709","#040203");let l=f(1616);for(let o of(w(e,.36*t,.64*a,.55*a,z,.3),e.save(),e.globalCompositeOperation="lighter",q))for(let[i,r,s,n]of[[o.x,o.y,o.x+o.w,o.y],[o.x+o.w,o.y,o.x+o.w,o.y+o.h],[o.x+o.w,o.y+o.h,o.x,o.y+o.h],[o.x,o.y+o.h,o.x,o.y]]){let o=Math.round(420*Math.hypot((s-i)*1.5,n-r));for(let h=0;h<o;h++){let o=l(),h=(l()-.5)*.006,u=i+(s-i)*o+(n-r?h:0),d=r+(n-r)*o+(s-i?h:0),f=c(1-Math.hypot((u-.36)*1.5,d-.64)/.85,.06,1);l()>.9*f+.08||(e.fillStyle=v(g(z,y,.8*f),.18+.72*f),e.fillRect(u*t,d*a,.0045*a,.0045*a))}}e.restore(),O(e,t,a,.12),e.save(),e.globalCompositeOperation="lighter",e.fillStyle=v(y,1),e.beginPath(),e.arc(.36*t,.64*a,.012*a,0,u),e.fill(),e.restore(),M(e,t,a,1616)}},{id:"coverage",name:"Coverage Plan",art:function(e,t,a){b(e,t,a,"#0b0708","#030202");let l=[[.2,.32],[.54,.26],[.8,.36],[.22,.7],[.52,.7],[.82,.72]];for(let[o,i]of(e.save(),e.globalCompositeOperation="lighter",l)){let l=.34*a,r=e.createRadialGradient(o*t,i*a,0,o*t,i*a,l);r.addColorStop(0,v(z,.34)),r.addColorStop(.55,v(z,.13)),r.addColorStop(1,v(z,0)),e.fillStyle=r,e.beginPath(),e.arc(o*t,i*a,l,0,u),e.fill()}for(let[o,i]of(e.restore(),O(e,t,a,.5),e.save(),e.globalCompositeOperation="lighter",l))e.strokeStyle=v(y,.45),e.lineWidth=.0025*a,e.setLineDash([.01*a,.014*a]),e.beginPath(),e.arc(o*t,i*a,.34*a,0,u),e.stroke(),e.setLineDash([]),w(e,o*t,i*a,.09*a,y,.6),e.fillStyle=v(y,1),e.beginPath(),e.arc(o*t,i*a,.011*a,0,u),e.fill();e.restore(),M(e,t,a,1717)}},{id:"scan-route",name:"Scan Route",art:function(e,t,a){b(e,t,a,"#0b0709","#030203"),O(e,t,a,.22);let l=[[.18,.74],[.2,.34],[.36,.46],[.54,.26],[.55,.46],[.5,.7],[.72,.68],[.8,.36]],o=[];for(let e=0;e<l.length-1;e++){let t=l[Math.max(0,e-1)],a=l[e],i=l[e+1],r=l[Math.min(l.length-1,e+2)];for(let e=0;e<24;e++){let l=e/24,s=l*l,n=s*l;o.push([.5*(2*a[0]+(-t[0]+i[0])*l+(2*t[0]-5*a[0]+4*i[0]-r[0])*s+(-t[0]+3*a[0]-3*i[0]+r[0])*n),.5*(2*a[1]+(-t[1]+i[1])*l+(2*t[1]-5*a[1]+4*i[1]-r[1])*s+(-t[1]+3*a[1]-3*i[1]+r[1])*n)])}}e.save(),e.globalCompositeOperation="lighter",e.lineCap="round",e.lineJoin="round";for(let l=1;l<o.length;l++){let i=l/o.length;e.strokeStyle=v(g(z,y,i),.25+.6*i),e.lineWidth=a*(.004+.005*i),e.beginPath(),e.moveTo(o[l-1][0]*t,o[l-1][1]*a),e.lineTo(o[l][0]*t,o[l][1]*a),e.stroke()}l.forEach(([o,i],r)=>{let s=r/(l.length-1),n=.018*a;w(e,o*t,i*a,.13*a,z,.3+.4*s),e.strokeStyle=v(g(z,y,s),.9),e.lineWidth=.0035*a,e.beginPath(),e.arc(o*t,i*a,n,0,u),e.stroke(),e.fillStyle=v(y,.35+.6*s),e.beginPath(),e.arc(o*t,i*a,.36*n,0,u),e.fill()}),e.restore(),M(e,t,a,1818)}}]}],I=E.flatMap(e=>e.plates.map(t=>({...t,type:e.type,year:e.year,work:e}))),L=E.reduce((e,t)=>[...e,e[e.length-1]+t.plates.length],[0]).slice(0,-1),B=E.flatMap((e,t)=>e.plates.map(()=>t)),U=I.map(e=>e.art),D=Math.round(512),$=["left","right"],W=e=>e?.firstElementChild?.children;function G(e,t,a){e&&(t>=1?(e.style.filter="none",e.style.opacity="1"):t<=0?(e.style.filter="none",e.style.opacity="0"):(e.style.filter=`blur(${Math.min(a/t-a,100)}px)`,e.style.opacity=`${Math.pow(t,.4)}`))}function N(e,t,a){let l={t:1},o=["",""],i=[!1,!1],r=()=>{let o=t[e];if(!o)return;let r=W(o.layers[0]),s=W(o.layers[1]),n=W(o.plain),h=l.t;for(let e=0;e<2;e++)i[e]?(G(r?.[e],1-h,a.nameBlur),G(s?.[e],h,a.nameBlur),n?.[e]&&(n[e].style.opacity="0")):(r?.[e]&&(r[e].style.opacity="0"),s?.[e]&&(s[e].style.opacity="0"),n?.[e]&&(n[e].style.opacity="1"));o.goo&&(o.goo.style.filter=h>=1?"none":`url(#name-goo) blur(${a.nameSoften}px)`)};return{m:l,set:n=>{let h=t[e];if(!h?.layers[0]||!h.layers[1]||!h.plain)return;s.Ay.killTweensOf(l),l.t=1,r();let u=[n[0]??"",n[1]??""];i=[u[0]!==o[0],u[1]!==o[1]];let c=W(h.layers[0]),d=W(h.layers[1]),f=W(h.plain);for(let e=0;e<2;e++)c?.[e]&&(c[e].textContent=o[e]),d?.[e]&&(d[e].textContent=u[e]),f?.[e]&&(f[e].textContent=u[e]);if(o=u,!i[0]&&!i[1]){l.t=1,r();return}l.t=0,r(),s.Ay.to(l,{t:1,duration:a.nameMorphTime,ease:a.nameEase,onUpdate:r})}}}let j=`
  varying vec2 vUv;

  void main() {
    vUv = uv;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`,Y=`
  precision highp float;

  varying vec2 vUv;

  uniform sampler2D uTex;
  uniform float uReveal;
  uniform vec3  uColor;
  uniform float uOpacity;

  void main() {
    float gy = vUv.y + 1.0 - uReveal;
    if (gy > 1.0 || gy < 0.0) discard;

    float a = texture2D(uTex, vec2(vUv.x, gy)).a;
    if (a <= 0.001) discard;

    gl_FragColor = vec4(uColor, a * uOpacity);
  }
`,_=".:+x*#@",X=2*Math.PI,H=Math.PI/2,Q=Math.PI/180,V=e=>e<0?0:e>1?1:e,K=e=>1-Math.pow(1-e,3),J=(e,t,a)=>{let l=V((a-e)/(t-e));return l*l*(3-2*l)},Z=e=>0===e?0:e%2==1?(e+1)/2:-e/2,ee=(e,t)=>1-Math.pow(1-t,60*e);function et(){let e=(0,o.useRef)(null),t=(0,o.useRef)(null),a=(0,o.useRef)([]),u=(0,o.useRef)([]),c=(0,o.useRef)([]),d=(0,o.useRef)({box:null,label:null,blurb:null,link:null}),f=(0,o.useRef)(null),p=(0,o.useRef)(null),m=(0,o.useRef)(null),g=(0,o.useRef)({left:{box:null,goo:null,layers:[],plain:null},right:{box:null,goo:null,layers:[],plain:null}});return(0,o.useEffect)(()=>{var l;let o,v,y,x,b,w,M,S,P,T,k,C,A,R,F=e.current,z=t.current,q=f.current,O=!1,E={refWidth:1512,refHeight:870,fitHeight:0,minScale:.5,maxScale:1.75,narrowAt:1024,narrowPlane:1.25,narrowRadius:1.3,narrowText:1.5,narrowPosX:-2.5,narrowEndScale:4.22,tightAt:640,tightRadius:.82,tightPosX:-3.5,tightSplit:.8,tightName:1.5,tightNameBottom:16,tightNameRight:16,tightMetaWidth:70,planeSize:90,count:I.length,ringRadius:340,seed:0,radial:!0,radius:6,textured:!0,blend:14,imageOffset:0,holdAfter:0,loaderChase:.18,loaderBottom:1,loaderOut:.45,stagger:.34,launchTime:1.95,spreadEase:"power2.out",spreadTime:3.6,stageAt:.7,spinTurns:1,spinTime:2.6,spinEase:"power2.inOut",spinDelay:0,posX:-2,posY:0,endScale:4.46,moveTime:2.2,moveEase:"power2.inOut",moveDelay:.2,scrollSpeed:.0022,damping:.94,maxSpeed:12,dragSpeed:1,snap:!0,snapTime:.8,snapFrom:1,pickTime:.55,pickEase:"power3.inOut",text:"TINA SHEN",textSize:41,textFont:"Satoshi",textWeight:400,textTracking:0,textColor:"#0a0a0a",textAt:.42,textTime:.95,textStagger:.015,textEase:"power4.out",textOut:!0,textOutAt:-.5,textOutTime:.7,textOutEase:"power2.in",metaLeft:5.5,metaRight:5.5,metaGapL:4.7,metaGapR:3.6,metaWidth:34,nameSize:24/1440*100,nameFont:"Satoshi",nameWeight:500,idxSize:16/1440*100,idxFont:"Geist",idxWeight:400,listSize:.9,note:!0,noteWidth:23,noteSize:13/1440*100,noteLabelSize:11/1440*100,noteGap:.95,noteLead:1.55,noteOpacity:.62,noteFade:.42,noteOut:.22,nameMorphTime:1.2,nameEase:"circ.out",nameBlur:8.5,nameEdge:400,nameCut:.33,nameSoften:.35,glass:!0,bandTop:.08,bandBottom:.08,refract:60,squeeze:.05,ripple:5,rippleFreq:.02,fringe:1.5,sheen:.05,hover:!0,touchHold:.16,touchSlop:10,lag:.3,melt:34,meltReach:260,reach:1.7,swell:.09,pull:26,grab:.14,release:.06,web:.2,webReach:1.15,wave:4,waveFreq:.05,waveSpeed:7,sideScale:.035,sidePush:17,sideDim:.15,sideReach:2.4,focusParticles:!0,focusParticleFrom:1024,focusParticleReach:82,focusParticleCell:11,focusParticleOpacity:.58,focusParticleEnter:.16,focusParticleExit:.11,focusParticleDrift:.7,focusParticleOut:3.2,assemble:!0,assembleFrom:1024,assembleTime:1.55,assembleEase:"power3.inOut",assembleSpread:3.8,assembleCardScale:2.6,assembleCell:13,assembleOpacity:.96,assembleHaloReach:148,assembleHaloOpacity:.72,tagFrom:1024,tagText:"View",tagSize:14,tagWeight:500,tagArrow:14,tagGap:6,tagX:64,tagY:-38,tagFrost:.16,tagRim:.02,tagRefract:39.5,thread:1,thin:.4,pinch:.35,sag:6,dissolve:2.9,fillet:14,wobble:3,goo:35},L={progress:0,launch:0,spread:0,spin:0,shift:0},W={restingGap:0,window:"",scale:1,band:"wide"};try{o=new r.JeP({antialias:!0,alpha:!0})}catch(e){console.error("[ring] could not create a WebGL context:",e);return}o.setPixelRatio(Math.min(window.devicePixelRatio,2)),F.appendChild(o.domElement);let G=new i.Z58,et=new i.qUd(-1,1,1,-1,-100,100),ea=function(){let e=document.createElement("canvas");e.width=128*_.length,e.height=128;let t=e.getContext("2d");t.clearRect(0,0,e.width,e.height),t.fillStyle="#ffffff",t.font="700 84px ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",t.textAlign="center",t.textBaseline="middle";for(let e=0;e<_.length;e++)t.fillText(_[e],128*e+64,65.28);let a=new i.GOR(e);return a.colorSpace=i.jf0,a.minFilter=i.k6q,a.magFilter=i.k6q,a.generateMipmaps=!1,a.needsUpdate=!0,a}(),el=window.matchMedia("(prefers-reduced-motion: reduce)"),eo={uResolution:{value:new i.I9Y(1,1)},uSize:{value:new i.I9Y(150,100)},uRadius:{value:E.radius},uCount:{value:E.count},uPos:{value:Array.from({length:32},()=>new i.I9Y)},uRot:{value:new Float32Array(32)},uScale:{value:Array.from({length:32},()=>new i.IUQ(0,0,1,0))},uLinkCount:{value:0},uLinkA:{value:Array.from({length:32},()=>new i.I9Y)},uLinkB:{value:Array.from({length:32},()=>new i.I9Y)},uLinkPar:{value:Array.from({length:32},()=>new i.IUQ)},uK:{value:E.goo},uWobble:{value:E.wobble},uTime:{value:0},uColor:{value:new i.Q1f("#0a0a0a")},uAtlas:{value:((y=new i.GYF(new Uint8Array([255,255,255,255]),1,1)).needsUpdate=!0,y)},uGrid:{value:new i.I9Y(1,1)},uBlend:{value:E.blend},uTextured:{value:0},uBandTop:{value:0},uBandBottom:{value:0},uGlass:{value:new i.IUQ},uFringe:{value:0},uSheen:{value:0},uMouse:{value:new i.IUQ},uMelt:{value:new i.IUQ},uAsciiTex:{value:ea},uIntro:{value:new i.IUQ(1,1,12,0)},uCardParticles:{value:new i.IUQ(1,0,12,0)},uFocusParticlePos:{value:new i.I9Y},uFocusParticleBox:{value:new i.IUQ},uFocusParticles:{value:new i.IUQ},uFocusParticleMotion:{value:new i.I9Y},uTagTex:{value:new i.GYF(new Uint8Array([0,0,0,0]),1,1)},uTag:{value:new i.IUQ},uTagP:{value:new i.IUQ},uTagQ:{value:new i.IUQ},uPage:{value:new i.Q1f("#fafafa")}},ei=new i.eaF(new i.bdM(1,1),new i.BKk({vertexShader:n,fragmentShader:h,uniforms:eo,transparent:!0,depthWrite:!1}));ei.renderOrder=10,G.add(ei);let er=new i.YJl;G.add(er);let es=(x=[],b=[],{build:()=>{w();let e=E.textSize,t=2*Math.min(window.devicePixelRatio,2),a=`${E.textWeight} ${e}px "${E.textFont}", ui-sans-serif, system-ui, sans-serif`,l=document.createElement("canvas").getContext("2d");l.font=a;let o=[...E.text],r=o.map(e=>l.measureText(e).width),s=E.textTracking*e,n=r.reduce((e,t)=>e+t,0)+s*(o.length-1),h=.25*e,u=1.3*e+2*h,c=-n/2;o.forEach((l,o)=>{let n=r[o];if(l.trim()){let o=n+2*h,r=document.createElement("canvas");r.width=Math.max(1,Math.ceil(o*t)),r.height=Math.max(1,Math.ceil(u*t));let s=r.getContext("2d");s.scale(t,t),s.font=a,s.textBaseline="alphabetic",s.fillStyle="#000",s.fillText(l,h,h+e);let d=new i.GOR(r);d.colorSpace=i.jf0,d.minFilter=i.k6q,d.magFilter=i.k6q,d.generateMipmaps=!1;let f=new i.BKk({vertexShader:j,fragmentShader:Y,uniforms:{uTex:{value:d},uReveal:{value:0},uColor:{value:new i.Q1f(E.textColor)},uOpacity:{value:1}},transparent:!0,depthTest:!1,depthWrite:!1}),p=new i.eaF(new i.bdM(1,1),f);p.scale.set(o,u,1),p.position.set(c+n/2,0,0),p.renderOrder=0,er.add(p),x.push(f.uniforms.uReveal),b.push(f.uniforms.uOpacity)}c+=n+s})},dispose:w=()=>{for(let e of[...er.children])er.remove(e),e.geometry.dispose(),e.material.uniforms.uTex.value?.dispose(),e.material.dispose();x=[],b=[]},get chars(){return x},get fades(){return b}}),en=(M={sx:.5,sy:0},S=new Image,P=!1,T=null,{box:M,build:()=>{let e=2*Math.min(window.devicePixelRatio,2),t=document.createElement("canvas");t.width=Math.ceil(104*e),t.height=Math.ceil(40*e);let a=t.getContext("2d");a.scale(e,e),a.font=`${E.tagWeight} ${E.tagSize}px "${E.textFont}", ui-sans-serif, system-ui, sans-serif`,a.textBaseline="middle",a.fillStyle="#fff";let l=a.measureText(E.tagText).width,o=(104-(E.tagArrow+E.tagGap+l))*.5;if(a.fillText(E.tagText,o+E.tagArrow+E.tagGap,20),P){let e=(40-E.tagArrow)*.5;a.drawImage(S,o,e,E.tagArrow,E.tagArrow)}T?.dispose(),(T=new i.GOR(t)).colorSpace=i.jf0,T.minFilter=i.k6q,T.magFilter=i.k6q,T.generateMipmaps=!1,eo.uTagTex.value=T},show:e=>{s.Ay.killTweensOf(M),e?(s.Ay.to(M,{sx:1,duration:.62,ease:"elastic.out(1, 0.5)"}),s.Ay.to(M,{sy:1,duration:.74,ease:"elastic.out(1, 0.42)"})):s.Ay.to(M,{sx:.5,sy:0,duration:.28,ease:"power3.in"})},load:e=>{S.onload=()=>{P=!0,e?.()},S.src="/ASTRA_3D_House/works/arrow-top-right-svgrepo-com.svg"},dispose:()=>{s.Ay.killTweensOf(M),T?.dispose()}}),eh=function(e,t){let{groups:a,list:l,loader:o,cut:i,live:r}=e,n=N("left",a,t),h=N("right",a,t),u=()=>{i?.setAttribute("values",`1 0 0 0 0
       0 1 0 0 0
       0 0 1 0 0
       0 0 0 ${t.nameEdge} ${-t.nameEdge*t.nameCut}`)};return{show:e=>{let t=I[e];t&&(n.set([String(e+1).padStart(2,"0"),t.name]),h.set([t.type,t.year]),r&&(r.textContent=`${t.name}. ${t.type}, ${t.year}. ${t.work.label}.`))},style:({textK:e,tight:i,viewW:r})=>{let s=t.nameSize*e*(i?t.tightName:1),n=`${s}vw`,h=`${t.idxSize*e}vw`,c=`"${t.nameFont}", ui-sans-serif, system-ui, sans-serif`,d=`"${t.idxFont}", ui-sans-serif, system-ui, sans-serif`,f=`${t.nameWeight}`,p=`${t.idxWeight}`,m=3*s;for(let e of $){let l=a[e];if(!l?.box)continue;let o="right"===e,u=i&&!o;if(i&&o){l.box.style.display="none";continue}if(l.box.style.display="",l.box.style.width=`${u?t.tightMetaWidth:t.metaWidth}vw`,l.box.style.height=`${m}vw`,u){let e=m*r/100,a=s*r/100;l.box.style.top="auto",l.box.style.left="auto",l.box.style.right=`${t.tightNameRight}px`,l.box.style.bottom=`${t.tightNameBottom+.5*a-.5*e}px`,l.box.style.transform="none"}else l.box.style.top="",l.box.style.bottom="",l.box.style.transform="",l.box.style.left=o?"auto":`${t.metaLeft}vw`,l.box.style.right=o?`${t.metaRight}vw`:"auto";for(let e of[...l.layers,l.plain]){if(!e)continue;e.style.justifyContent=u||o?"flex-end":"flex-start";let a=e.firstElementChild;a.style.gap=`${o?t.metaGapR:t.metaGapL}vw`;let[l,i]=a.children;l.style.display=u?"none":"",l.style.fontFamily=o?c:d,l.style.fontSize=o?n:h,l.style.fontWeight=o?f:p,i.style.fontFamily=o?d:c,i.style.fontSize=o?h:n,i.style.fontWeight=o?p:f}}l&&(l.style.fontSize=`${t.listSize*e}vw`),o&&(o.style.bottom=`${t.loaderBottom}vh`,o.style.fontFamily=d,o.style.fontSize=h,o.style.fontWeight=p),u()},setThreshold:u,dispose:()=>{s.Ay.killTweensOf(n.m),s.Ay.killTweensOf(h.m)}}}({groups:g.current,list:z,loader:q,cut:m.current,live:p.current},E),eu=(l=d.current,k={t:0},C=null,A=()=>{let{box:e}=l;e&&(e.style.opacity=`${k.t*E.noteOpacity}`,e.style.transform=`translateY(${(1-k.t)*.5}em)`)},R=e=>{let{label:t,blurb:a,link:o}=l;t&&(t.textContent=`${e.label} \xb7 ${e.meta}`),a&&(a.textContent=e.blurb),o&&(o.style.display=e.link?"":"none",e.link&&(o.href=e.link,o.textContent=e.linkLabel??"Read more"))},{show:e=>{let t=I[e]?.work;if(!t||t===C)return;let a=null===C;if(C=t,s.Ay.killTweensOf(k),a){R(t),k.t=0,A(),s.Ay.to(k,{t:1,duration:E.noteFade,ease:"power2.out",onUpdate:A});return}s.Ay.to(k,{t:0,duration:E.noteOut,ease:"power2.in",onUpdate:A,onComplete:()=>{R(t),s.Ay.to(k,{t:1,duration:E.noteFade,ease:"power2.out",onUpdate:A})}})},style:({textK:e,tight:t,narrow:a})=>{let{box:o,label:i,blurb:r,link:s}=l;if(!o)return;if(t||a||!E.note){o.style.display="none";return}o.style.display="";let n=E.nameSize*e;for(let t of(o.style.left=`${E.metaLeft}vw`,o.style.lineHeight=`${E.noteLead}`,o.style.top=`calc(50% + ${n*E.noteGap}vw)`,o.style.width=`${E.noteWidth}vw`,i&&(i.style.fontFamily=`"${E.idxFont}", ui-sans-serif, system-ui, sans-serif`,i.style.fontSize=`${E.noteLabelSize*e}vw`,i.style.letterSpacing="0.07em"),[r,s]))t&&(t.style.fontFamily=`"${E.nameFont}", ui-sans-serif, system-ui, sans-serif`,t.style.fontSize=`${E.noteSize*e}vw`);A()},reset:()=>{s.Ay.killTweensOf(k),C=null,k.t=0,A()},dispose:()=>s.Ay.killTweensOf(k)}),ec=!1,ed=0,ef=!1,ep=[],em=function(e=U,t){let a=Math.ceil(Math.sqrt(e.length)),l=Math.ceil(e.length/a),o=document.createElement("canvas");o.width=768*a,o.height=l*D;let r=o.getContext("2d"),s=new i.GOR(o);s.flipY=!1,s.colorSpace=i.jf0,s.wrapS=i.ghU,s.wrapT=i.ghU,s.minFilter=i.$_I,s.magFilter=i.k6q,s.generateMipmaps=!0;let n=document.createElement("canvas");n.width=768,n.height=D;let h=n.getContext("2d"),u=0,c=()=>t?.(u/e.length),d=t=>{try{var l;l=e[t],h.setTransform(1,0,0,1,0,0),h.globalAlpha=1,h.globalCompositeOperation="source-over",h.clearRect(0,0,768,D),l(h,768,D),r.drawImage(n,t%a*768,Math.floor(t/a)*D)}catch(e){console.warn("[atlas] plate",t,e)}u++,c()};d(0),s.needsUpdate=!0;let f=Promise.resolve(),p=new Promise(t=>{setTimeout(()=>{for(let t=1;t<e.length;t++)d(t);s.needsUpdate=!0,t()},0)});return c(),{texture:s,grid:[a,l],count:e.length,first:f,ready:p}}(U,e=>{O||(ed=e)});eo.uAtlas.value.dispose(),em.texture.anisotropy=o.capabilities.getMaxAnisotropy(),eo.uAtlas.value=em.texture,eo.uGrid.value.set(em.grid[0],em.grid[1]);let eg=em.count;em.first.then(()=>{O||(ec=!0)}),em.ready.then(()=>{O||(ed=1)});let ev=1,ey=1,ex={left:0,top:0},eb=1,ew=1,eM=1,eS=1,eP=!1,eT=!1,ek=()=>{for(let e of(eh.style({textK:eS,tight:eT,viewW:ev}),eu.style({textK:eS,tight:eT,narrow:eP}),c.current))e&&(e.style.overflow="hidden",e.style.transition="height 340ms cubic-bezier(.4,0,.2,1), opacity 240ms linear");tf()},eC=()=>{let e,t,a,l,i,r;ev=F.clientWidth,ey=F.clientHeight,e=ev/Math.max(1,E.refWidth),t=ey/Math.max(1,E.refHeight),a=e*(1-E.fitHeight)+Math.min(e,t)*E.fitHeight,eb=Math.min(E.maxScale,Math.max(E.minScale,a)),l=ev<=E.narrowAt,i=ev<=E.tightAt,eP=l,eT=i,ew=l?E.narrowPlane:1,eM=(l?E.narrowRadius:1)*(i?E.tightRadius:1),eS=l?E.narrowText:1,W.window=`${Math.round(ev)} x ${Math.round(ey)}`,W.scale=Math.round(1e3*eb)/1e3,W.band=i?"tight":l?"narrow":"wide",r=eb*eS*(i?E.tightSplit:1),er.scale.set(r,r,1),o.setSize(ev,ey),et.left=-ev/2,et.right=ev/2,et.top=ey/2,et.bottom=-ey/2,et.updateProjectionMatrix(),ei.scale.set(ev,ey,1),eo.uResolution.value.set(ev,ey);let s=o.domElement.getBoundingClientRect();ex.left=s.left,ex.top=s.top},eA=()=>{eC(),ek()};eC(),window.addEventListener("resize",eA);let eR={x:0,y:0},eF=0,ez=!1,eq=0,eO=!1,eE=0,eI=0,eL=!1,eB=0,eU=0,eD=!1,e$=0,eW=0,eG=0,eN=e=>{let t=e.clientX-ex.left-eR.x;return Math.atan2(-(e.clientY-ex.top-eR.y),t)},ej=()=>{eD&&(s.Ay.killTweensOf(L),eD=!1)},eY={x:0,y:0,inside:!1,seeded:!1},e_={x:0,y:0,amt:0,wake:0},eX=!1,eH=!1,eQ=0,eV=()=>{clearTimeout(eQ),eQ=0,eH=!1},eK=e=>{eX="touch"===e.pointerType,eY.x=e.clientX-ex.left-.5*ev,eY.y=.5*ey-(e.clientY-ex.top),eY.inside=!0,eY.seeded||(eY.seeded=!0,e_.x=eY.x,e_.y=eY.y)},eJ=()=>{eY.inside=!1},eZ=e=>{if(!ez)return;e.preventDefault();let t=Math.abs(e.deltaX)>Math.abs(e.deltaY)?e.deltaX:e.deltaY;ej(),eL=!1,eq+=t*E.scrollSpeed,eq=Math.max(-E.maxSpeed,Math.min(E.maxSpeed,eq))},e0=e=>{e$=0,eW=e.clientX,eG=e.clientY,eK(e),ez&&(ej(),eX&&(clearTimeout(eQ),eQ=setTimeout(()=>{eH=!0},1e3*E.touchHold)),eO=!0,eL=!1,eq=0,eE=eN(e),eI=performance.now(),o.domElement.setPointerCapture?.(e.pointerId))},e1=e=>{if(eK(e),e$+=Math.abs(e.clientX-eW)+Math.abs(e.clientY-eG),eW=e.clientX,eG=e.clientY,eX&&!eH&&e$>E.touchSlop&&eV(),!eO)return;let t=eN(e),a=t-eE;a>Math.PI&&(a-=X),a<-Math.PI&&(a+=X);let l=a*E.dragSpeed;L.spin+=l;let o=performance.now();eq=l/(Math.max(8,o-eI)/1e3),eE=t,eI=o},e2=e=>{eK(e),eV(),eO&&(eO=!1,o.domElement.releasePointerCapture?.(e.pointerId))},e5=()=>{if(ez&&!(e$>=5)&&!(tn<0)){var e;let t,a,l,o;e=tn,t=X/Math.round(E.count),(o=Math.abs((l=(a=eF-E.seed*Q-Z(e)*t)+Math.round((L.spin-a)/X)*X)-L.spin)/t)<.01||(eq=0,eL=!1,eD=!0,s.Ay.killTweensOf(L),s.Ay.to(L,{spin:l,duration:E.pickTime*Math.sqrt(Math.max(1,o)),ease:E.pickEase,onComplete:()=>{eD=!1}}))}};F.addEventListener("wheel",eZ,{passive:!1}),F.addEventListener("pointerdown",e0),F.addEventListener("pointermove",e1),F.addEventListener("pointerup",e2),F.addEventListener("pointercancel",e2),F.addEventListener("pointerleave",eJ),F.addEventListener("click",e5);let e4={shown:0},e3=new Float32Array(32),e6=new Float32Array(32),e8=[],e9=Array.from({length:32},()=>new i.I9Y),e7=new Float32Array(32),te=new Float32Array(32),tt=new Float32Array(32),ta=new Float32Array(32),tl=new Float32Array(32),to=new i.I9Y,ti=e=>Math.max(.05,1+E.swell*e7[e]-E.sideScale*tl[e]),tr=-1,ts=-1,tn=-1,th=!1,tu=-1,tc=0,td=0,tf=()=>{let e=a.current;for(let t=0;t<e.length;t++){let a=e[t];if(!a)continue;let l=t===tr;a.style.opacity=l?"1":"0.2",l?a.setAttribute("aria-current","true"):a.removeAttribute("aria-current")}let t=B[tr],l=u.current,o=c.current;for(let e=0;e<l.length;e++){let a=e===t;l[e]&&(l[e].style.opacity=a?"1":"0.28");let i=o[e];if(!i)continue;let r=a&&!eP;i.style.height=r?`${i.scrollHeight}px`:"0px",i.style.opacity=r?"1":"0"}},tp=0;en.build(),en.load(()=>{O||en.build()}),ek();let tm=null,tg=()=>{O||tm||(es.build(),en.build(),ek(),tm?.kill(),tm=(()=>{ez=!1,ts=-1,eu.reset(),eq=0,eO=!1,eL=!1,tu=-1,tc=0,td=0,eo.uFocusParticles.value.x=0,ej();let e=++tp;q&&s.Ay.set(q,{opacity:+!ef});let t=s.Ay.timeline({delay:.25,onComplete:()=>{ez=!0}}),a=E.assemble&&ev>E.assembleFrom&&!el.matches;t.fromTo(L,{progress:0,launch:0,spread:0,spin:0,shift:0},{progress:1,duration:a?E.assembleTime:.65,ease:a?E.assembleEase:"power1.out"}),t.addPause(">",()=>{let a;a=()=>{s.Ay.delayedCall(E.holdAfter,()=>{!O&&e===tp&&(t.resume(),q&&s.Ay.to(q,{opacity:0,duration:E.loaderOut,ease:"power2.in"}))})},ef?a():ep.push(a)}),t.to(L,{launch:1,duration:E.launchTime,ease:"power2.inOut"});let l=t.duration()-.15;t.to(L,{spread:1,duration:E.spreadTime,ease:E.spreadEase},l);let o=l+E.stageAt*E.spreadTime;t.to(L,{spin:E.spinTurns*X,duration:E.spinTime,ease:E.spinEase},o+E.spinDelay),t.to(L,{shift:1,duration:E.moveTime,ease:E.moveEase},o+E.moveDelay);let i=l+E.textAt*E.spreadTime;if(es.chars.length&&t.fromTo(es.chars,{value:0},{value:1,duration:E.textTime,ease:E.textEase,stagger:E.textStagger},i),E.textOut&&es.fades.length){let e=Math.max(o+E.spinDelay+E.spinTime,o+E.moveDelay+E.moveTime);t.fromTo(es.fades,{value:1},{value:0,duration:E.textOutTime,ease:E.textOutEase,stagger:E.textStagger},Math.max(0,e+E.textOutAt))}return z&&t.fromTo(z,{opacity:0},{opacity:1,duration:E.textTime,ease:E.textEase},i),t})())},tv=setTimeout(tg,3e3);Promise.all([document.fonts?.ready??Promise.resolve(),em.first]).then(tg).catch(tg);let ty=performance.now(),tx=ty;return o.setAnimationLoop(()=>{let e,t,a,l=performance.now(),i=Math.min(.05,(l-tx)/1e3);if(tx=l,eo.uTime.value=(l-ty)*.001,ez&&!eO&&!eD){L.spin+=eq*i,eq*=Math.pow(E.damping,60*i);let e=0;if(E.snap){let t=X/Math.round(E.count),a=Math.max(.01,-(60*Math.log(E.damping))),l=Math.max(E.snapFrom,a*t*.5),o=4.8/Math.max(.05,E.snapTime);if(!eL&&Math.abs(eq)<l){let e=L.spin+eq/a,l=E.seed*Q-eF;eB=Math.round((e+l)/t)*t-l,eU=Math.max(Math.abs(eq),.5*t*o),eL=!0}if(eL){e=eB-L.spin;let t=Math.max(-eU,Math.min(eU,e*o));eq+=(t-eq)*V(o*i)}}else eL=!1;.0015>Math.abs(eq)&&8e-4>Math.abs(e)&&(eq=0,L.spin+=e)}let r=Math.min(ed,V(L.progress));e4.shown+=(r-e4.shown)*ee(i,E.loaderChase);let s=Math.min(100,Math.max(1,Math.round(100*e4.shown)));if(q&&(q.textContent=String(s).padStart(3,"0")),!ef&&s>=100){for(let e of(ef=!0,ep))e();ep.length=0}e=E.hover&&(eX?eH:eY.inside)&&eY.seeded&&ez,e_.amt+=(!!e-e_.amt)*ee(i,.12),t=ee(i,E.lag),e_.x+=(eY.x-e_.x)*t,e_.y+=(eY.y-e_.y)*t,a=Math.hypot(eY.x-e_.x,eY.y-e_.y),e_.wake=Math.max(e_.wake*Math.pow(.94,60*i),V(a/(2600*Math.max(i,.001)))),eo.uMouse.value.set(e_.x,e_.y,e_.amt,E.melt*eb),eo.uMelt.value.set(E.meltReach*eb,E.wave*eb*e_.wake*e_.amt,E.waveFreq,E.waveSpeed),(e=>{let t,a=Math.round(E.count);eo.uCount.value=a;let l=X/a,o=V(L.spread),i=eP?E.narrowEndScale:E.endScale,r=eT?E.tightPosX:eP?E.narrowPosX:E.posX,s=V(L.shift),n=(1+(i-1)*s)*eb,h=r*ev*.5*s,u=E.posY*ey*.5*s,c=E.assemble&&ev>E.assembleFrom&&!el.matches,d=c?1+(E.assembleCardScale-1)*(1-J(.05,.82,L.launch)):1;eR.x=.5*ev+h,eR.y=.5*ey-u,eF=0!==h||0!==u?Math.atan2(-u,-h):0;let f=E.planeSize*ew*n*d,p=f/1.5;eo.uSize.value.set(f,p),eo.uRadius.value=E.radius*ew*n;let m=E.radial?p:f,g=E.radial?f:p,v=E.ringRadius*eM*n,y=2*v*Math.sin(l/2)-m;W.restingGap=Math.round(y/n*10)/10;let x=Math.max(1,y),b=Math.max(1,Math.abs(Z(a-1))),w=Math.max(.1,.94-E.stagger);e6[0]=0;for(let e=1;e<=b;e++){let t=V((o-(.06+(e-1)/b*E.stagger))/w),a=t*t*(3-2*t);e3[e]=a,e6[e]=e6[e-1]+a}let M=E.seed*Q,S=(t=V(L.launch))<.5?4*t*t*t:1-Math.pow(-2*t+2,3)/2,P=v*S;e8.length=0;let T=e_.amt>.001,k=Math.max(1,E.reach*f),C=Math.max(1,E.sideReach*f),A=ee(e,E.grab),R=ee(e,E.release),F=-1,z=1e9,q=0,O=Math.round(E.imageOffset),I=e=>eg>0?((O-e)%eg+eg)%eg:0,B=eY.inside&&eY.seeded&&ez,U=-1,D=T?tn:-1;for(let e=0;e<a;e++){let t=Z(e),a=Math.abs(t),o=0===e?V(L.progress):e3[a],i=I(t),r=M+Math.sign(t)*l*e6[a]+L.spin,s=Math.cos(r)*P+h,n=Math.sin(r)*P+u;e9[e].set(s,n);let d=r-eF,m=Math.abs(Math.atan2(Math.sin(d),Math.cos(d)));m<z&&(z=m,F=e,q=i);let g=0,v=0,y=0;if(T){let e=e_.x-s,t=e_.y-n,a=Math.hypot(e,t);if((g=J(k,.22*k,a)*e_.amt*o)>1e-4&&a>1e-4){let l=E.pull*eb*g/a;v=e*l,y=t*l}}let x=g>e7[e]?A:R;e7[e]+=(g-e7[e])*x,te[e]+=(v-te[e])*x,tt[e]+=(y-tt[e])*x;let b=0;D>=0&&e!==D&&(b=J(C,.2*C,Math.hypot(to.x-s,to.y-n))*o),tl[e]+=(b-tl[e])*(b>tl[e]?A:R);let w=0,O=0;if(tl[e]>1e-4){let t=s-to.x,a=n-to.y,l=Math.hypot(t,a);if(l>1e-4){let o=E.sidePush*eb*tl[e]/l;w=t*o,O=a*o}}eo.uPos.value[e].set(s+te[e]+w,n+tt[e]+O),eo.uRot.value[e]=(E.radial?r:r+H)*S;let $=0===e?K(V(c?(o-.5)/.46:o/.7)):K(V(o/.34)),W=0===e?K(V(c?(o-.58)/.38:(o-.18)/.74)):K(V((o-.06)/.36)),G=ti(e);if(eo.uScale.value[e].set($*G,W*G,1-E.sideDim*tl[e],i),B&&U<0){let t=eo.uRot.value[e],a=e_.x-(s+te[e]+w),l=e_.y-(n+tt[e]+O),o=Math.cos(t),i=Math.sin(t);Math.abs(a*o+l*i)<=.5*f*$*G&&Math.abs(-a*i+l*o)<=.5*p*W*G&&(U=e)}e8.push(e)}for(let e=a;e<32;e++)eo.uScale.value[e].set(0,0,1,0),e7[e]=0,te[e]=0,tt[e]=0,tl[e]=0;tn=U;let $=E.focusParticles&&ev>E.focusParticleFrom&&!eX&&ez&&o>.995?tn:-1;tu<0&&$>=0&&(tu=$,td=0);let G=tu>=0&&tu===$,N=G?E.focusParticleEnter:E.focusParticleExit;if(tc+=(!!G-tc)*ee(e,N),!el.matches&&tu>=0&&(td+=e*(G?E.focusParticleDrift:-E.focusParticleOut)),!G&&tc<.015&&(tu=$,tc=0,td=0),tu>=0){let e=eo.uPos.value[tu],t=eo.uScale.value[tu],a=.5*f*t.x,l=.5*p*t.y,o=Math.min(a,l),i=J(.3,1,Math.min(t.x,t.y)),r=Math.min(o,o+(eo.uRadius.value-o)*i);eo.uFocusParticlePos.value.copy(e),eo.uFocusParticleBox.value.set(a,l,r,eo.uRot.value[tu])}eo.uFocusParticles.value.set(tc,E.focusParticleReach*eb,Math.max(6,E.focusParticleCell*eb),E.focusParticleOpacity),eo.uFocusParticleMotion.value.set(td,+!el.matches);let j=tn>=0&&!eX&&ev>E.tagFrom;j!==th&&(th=j,en.show(j)),tn>=0&&to.copy(e9[tn]),eo.uTag.value.set(e_.x+E.tagX,e_.y+E.tagY,en.box.sx,en.box.sy),eo.uTagP.value.set(52,20,20,E.tagRefract),eo.uTagQ.value.set(E.tagFrost,E.tagRim,0,0),F>=0&&eg>0&&q!==tr&&(tr=q,tf()),e8.sort((e,t)=>Z(e)-Z(t));let Y=.5*g*E.thread,_=Math.min(o>.995&&a>2?a:a-1,32);for(let e=0;e<_;e++){let t=e8[e],l=e8[(e+1)%a],o=eo.uPos.value[t],i=eo.uPos.value[l],r=eo.uScale.value[t],s=eo.uScale.value[l],h=(E.radial?r.y:r.x)/ti(t),u=(E.radial?s.y:s.x)/ti(l),c=V((e9[t].distanceTo(e9[l])-.5*m*(h+u))/x),d=0;if(T&&E.web>1e-4){let e=(o.x+i.x)*.5,t=(o.y+i.y)*.5,a=Math.max(1,E.webReach*f);d=J(a,.15*a,Math.hypot(e_.x-e,e_.y-t))*e_.amt}ta[e]+=(d-ta[e])*(d>ta[e]?A:R);let p=Y*Math.max(Math.pow(1-c,E.thin),E.web*ta[e])-E.dissolve,g=p*(1-(1-E.pinch)*J(0,.7,c));eo.uLinkA.value[e].copy(o),eo.uLinkB.value[e].copy(i),eo.uLinkPar.value[e].set(p,g,E.sag*n*Math.pow(c,1.5),Math.min(E.fillet*n*J(0,.35,c),1.5*Math.max(g,0)))}for(let e=_;e<32;e++)eo.uLinkPar.value[e].set(-100,-100,0,0);eo.uLinkCount.value=_,eo.uK.value=E.goo*ew*eb,eo.uWobble.value=E.wobble*eb*(1-J(.2,.95,L.progress)),eo.uTextured.value=E.textured&&ec?1:0,eo.uBlend.value=Math.max(.5,E.blend*ew*n),eo.uIntro.value.set(c?V(L.progress):1,E.assembleSpread,Math.max(7,E.assembleCell*eb),c?E.assembleOpacity:0),eo.uCardParticles.value.set(V(L.launch),E.assembleHaloReach*eb,Math.max(7,E.assembleCell*eb),c?E.assembleHaloOpacity:0);let et=E.glass;eo.uBandTop.value=et?E.bandTop*ey:0,eo.uBandBottom.value=et?E.bandBottom*ey:0,eo.uGlass.value.set(E.refract,E.squeeze,E.ripple,E.rippleFreq),eo.uFringe.value=et?E.fringe:0,eo.uSheen.value=et?E.sheen:0})(i),ez&&!eO&&!eD&&0===eq&&tr>=0&&tr!==ts&&(ts=tr,eh.show(tr),eu.show(tr)),o.render(G,et)}),()=>{O=!0,clearTimeout(eQ),clearTimeout(tv),o.setAnimationLoop(null),window.removeEventListener("resize",eA),F.removeEventListener("wheel",eZ),F.removeEventListener("pointerdown",e0),F.removeEventListener("pointermove",e1),F.removeEventListener("pointerup",e2),F.removeEventListener("pointercancel",e2),F.removeEventListener("pointerleave",eJ),F.removeEventListener("click",e5),tm?.kill(),s.Ay.killTweensOf(es.chars),s.Ay.killTweensOf(es.fades),s.Ay.killTweensOf(z),eh.dispose(),eu.dispose(),en.dispose(),es.dispose(),v?.destroy(),ei.geometry.dispose(),ei.material.dispose(),eo.uAtlas.value?.dispose(),eo.uAsciiTex.value?.dispose(),eo.uTagTex.value?.dispose(),o.dispose(),o.forceContextLoss(),o.domElement.remove()}},[]),(0,l.jsxs)(l.Fragment,{children:[(0,l.jsx)("div",{ref:e,className:"fixed inset-0 touch-none"}),(0,l.jsx)("ul",{ref:t,"aria-label":"Projects",style:{fontFamily:'"Satoshi", ui-sans-serif, system-ui, sans-serif'},className:"pointer-events-none fixed right-[12vw] top-[2.4vh] z-10 flex flex-col items-start text-right leading-[1.4] tracking-[0.01em] text-[#0a0a0a] opacity-0 max-sm:hidden",children:E.map((e,t)=>(0,l.jsxs)("li",{className:t?"mt-[0.55em]":"",children:[(0,l.jsx)("div",{ref:e=>{u.current[t]=e},style:{opacity:.28,fontFamily:'"Geist", ui-sans-serif, system-ui, sans-serif',fontSize:"0.88em",letterSpacing:"0.05em"},children:e.label}),(0,l.jsx)("ul",{ref:e=>{c.current[t]=e},style:{height:0,opacity:0,overflow:"hidden"},className:"pl-[0.9em]",children:e.plates.map((e,o)=>{let i=L[t]+o;return(0,l.jsx)("li",{ref:e=>{a.current[i]=e},style:{opacity:.2},children:e.name},e.id)})})]},e.id))}),(0,l.jsxs)("div",{ref:e=>{d.current.box=e},style:{willChange:"opacity, transform"},className:"pointer-events-none fixed z-10 text-[#0a0a0a] opacity-0 max-sm:hidden",children:[(0,l.jsx)("div",{ref:e=>{d.current.label=e}}),(0,l.jsx)("p",{ref:e=>{d.current.blurb=e},className:"mt-[0.5em]"}),(0,l.jsx)("a",{ref:e=>{d.current.link=e},target:"_blank",rel:"noreferrer",className:"pointer-events-auto mt-[0.75em] inline-block underline decoration-[0.05em] underline-offset-[0.35em]"})]}),[{side:"left",justify:"flex-start"},{side:"right",justify:"flex-end"}].map(({side:e,justify:t})=>{let a=(0,l.jsxs)("span",{className:"flex items-baseline whitespace-nowrap",children:[(0,l.jsx)("span",{}),(0,l.jsx)("span",{})]});return(0,l.jsxs)("div",{ref:t=>{g.current[e].box=t},"aria-hidden":"true",className:"pointer-events-none fixed top-1/2 z-10 -translate-y-1/2 tracking-[-0.01em] text-[#0a0a0a]",children:[(0,l.jsx)("span",{ref:t=>{g.current[e].goo=t},className:"absolute inset-0",style:{willChange:"filter"},children:[0,1].map(o=>(0,l.jsx)("span",{ref:t=>{g.current[e].layers[o]=t},className:"absolute inset-0 flex items-center",style:{justifyContent:t},children:a},o))}),(0,l.jsx)("span",{ref:t=>{g.current[e].plain=t},className:"absolute inset-0 flex items-center",style:{justifyContent:t},children:a})]},e)}),(0,l.jsx)("div",{ref:f,"aria-hidden":"true",className:"pointer-events-none fixed left-1/2 z-10 -translate-x-1/2 tracking-[-0.01em] text-[#0a0a0a]"}),(0,l.jsx)("div",{ref:p,"aria-live":"polite",className:"sr-only"}),(0,l.jsx)("svg",{"aria-hidden":"true",className:"pointer-events-none absolute h-0 w-0",focusable:"false",children:(0,l.jsx)("defs",{children:(0,l.jsx)("filter",{id:"name-goo",x:"-20%",y:"-100%",width:"140%",height:"300%",colorInterpolationFilters:"sRGB",children:(0,l.jsx)("feColorMatrix",{ref:m,in:"SourceGraphic",type:"matrix",values:"1 0 0 0 0\n                      0 1 0 0 0\n                      0 0 1 0 0\n                      0 0 0 255 -140"})})})})]})}},6549:(e,t,a)=>{Promise.resolve().then(a.bind(a,1879))}},e=>{e.O(0,[831,367,592,911,441,794,358],()=>e(e.s=6549)),_N_E=e.O()}]);