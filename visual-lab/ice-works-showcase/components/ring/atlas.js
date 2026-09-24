import * as THREE from "three";
import { PLATE_ART } from "./projects";

// Cell aspect matches the plane's 1.5 : 1 so nothing is distorted. Larger
// than the 512 the photographs used to need: the art is drawn here rather
// than downloaded, so the only cost of more pixels is the paint itself.
const CELL_W = 768;
const CELL_H = Math.round(CELL_W / 1.5);

/**
 * Packs every plate into one texture. A single atlas rather than one texture
 * per plane because ESSL 1.00 cannot index an array of samplers with a
 * non-constant index.
 *
 * Returns synchronously with the sheet blank and filling in as plates are
 * painted: the caller needs something to bind on frame one, and the entry
 * shows cell 0 while the rest are still coming.
 *
 * `first` settles once cell 0 is on the texture, `ready` once all of them
 * are. Neither rejects — a painter that throws leaves its cell blank and
 * still counts as settled, so one bad plate cannot strand the entry.
 *
 * Cell 0 is painted before this returns and the other seventeen in a single
 * deferred task. Exactly that split for two reasons: the seed's own art is
 * wanted on frame one, and a timer per plate would be eighteen timers — which
 * a background tab clamps to around one a second each, so a page opened in a
 * tab nobody is looking at yet comes back to a counter still climbing.
 */
export function buildAtlas(art = PLATE_ART, onProgress) {
  const cols = Math.ceil(Math.sqrt(art.length));
  const rows = Math.ceil(art.length / cols);

  const canvas = document.createElement("canvas");
  canvas.width = cols * CELL_W;
  canvas.height = rows * CELL_H;
  const ctx = canvas.getContext("2d");

  const texture = new THREE.CanvasTexture(canvas);
  // The shader flips each cell itself, so leave the sheet as drawn.
  texture.flipY = false;
  // NoColorSpace deliberately: this shader writes straight to the framebuffer
  // with no encoding step, and decoding on read without encoding on write is
  // what washes everything out.
  texture.colorSpace = THREE.NoColorSpace;
  texture.wrapS = THREE.ClampToEdgeWrapping;
  texture.wrapT = THREE.ClampToEdgeWrapping;
  texture.minFilter = THREE.LinearMipmapLinearFilter;
  texture.magFilter = THREE.LinearFilter;
  texture.generateMipmaps = true;

  // Painted into its own cell-sized canvas and blitted, so a painter can work
  // in plain 0,0..w,h and cannot bleed into its neighbours.
  const cell = document.createElement("canvas");
  cell.width = CELL_W;
  cell.height = CELL_H;
  const cctx = cell.getContext("2d");

  const paint = (fn, i) => {
    cctx.setTransform(1, 0, 0, 1, 0, 0);
    cctx.globalAlpha = 1;
    cctx.globalCompositeOperation = "source-over";
    cctx.clearRect(0, 0, CELL_W, CELL_H);
    fn(cctx, CELL_W, CELL_H);
    ctx.drawImage(cell, (i % cols) * CELL_W, Math.floor(i / cols) * CELL_H);
  };

  let settled = 0;
  const tick = () => onProgress?.(settled / art.length);

  const draw = (i) => {
    try {
      paint(art[i], i);
    } catch (err) {
      console.warn("[atlas] plate", i, err);
    }
    settled++;
    tick();
  };

  // Cell 0 is the seed's art, the only thing on screen during the hold, so it
  // is painted ahead of the rest and uploaded the moment it lands.
  draw(0);
  texture.needsUpdate = true;
  const first = Promise.resolve();

  // One task and one upload for everything else. Marking dirty per plate
  // would re-send the whole sheet seventeen times for cells nobody is looking
  // at yet.
  const ready = new Promise((resolve) => {
    setTimeout(() => {
      for (let i = 1; i < art.length; i++) draw(i);
      texture.needsUpdate = true;
      resolve();
    }, 0);
  });

  tick();
  return { texture, grid: [cols, rows], count: art.length, first, ready };
}
