import { PLATES } from "./plates";

// Ring order, not project order. Art is dealt straight down this list, so
// entry n sits one slot along from n-1 and the column can count 01..18 as the
// carousel turns. Reordering these rows moves the ring, the column and the
// numbering together; nothing else needs touching.
//
// Six pieces of work, three cards each, kept together rather than shuffled:
// scrolling through one is meant to walk the length of a single problem —
// what was measured, what that leaves you with, what comes out — before the
// palette changes and the next one starts.
//
// Every plate is painted from the maths in `plates.js`. Nothing here is a
// simulation result or a clinical image; they are illustrations of real work.
export const PROJECTS = [
  // NASA VfOx — oxygen fugacity in the Venus atmosphere, for DAVINCI / APL.
  { id: "cloud-deck", name: "Cloud Deck", type: "Planetary", year: "2024", art: PLATES.cloudDeck }, // prettier-ignore
  { id: "fugacity", name: "Oxygen Fugacity", type: "Planetary", year: "2024", art: PLATES.fugacity }, // prettier-ignore
  { id: "descent", name: "Descent Profile", type: "Planetary", year: "2024", art: PLATES.descent }, // prettier-ignore

  // Stanford RSL — sparse-view cone-beam CT with the Radon transform as a
  // physical constraint. The three cards are one pipeline, in order.
  { id: "sinogram", name: "Sparse Sinogram", type: "Tomography", year: "2025", art: PLATES.sinogram }, // prettier-ignore
  { id: "backprojection", name: "Back Projection", type: "Tomography", year: "2025", art: PLATES.backprojection }, // prettier-ignore
  { id: "reconstruction", name: "Reconstruction", type: "Tomography", year: "2025", art: PLATES.reconstruction }, // prettier-ignore

  // Generative models as interacting particle systems, with Dr. Fei Lu.
  { id: "interacting", name: "Interacting Particles", type: "Generative", year: "2025", art: PLATES.interacting }, // prettier-ignore
  { id: "transport", name: "Optimal Transport", type: "Generative", year: "2025", art: PLATES.transport }, // prettier-ignore
  { id: "emergence", name: "Noise to Form", type: "Generative", year: "2025", art: PLATES.emergence }, // prettier-ignore

  // Beller group — Brownian dynamics of active particles and chains.
  { id: "brownian", name: "Brownian Path", type: "Soft Matter", year: "2024", art: PLATES.brownian }, // prettier-ignore
  { id: "bead-spring", name: "Bead and Spring", type: "Soft Matter", year: "2024", art: PLATES.beadSpring }, // prettier-ignore
  { id: "nematic", name: "Nematic Defects", type: "Soft Matter", year: "2024", art: PLATES.nematic }, // prettier-ignore

  // Backside of the Moon — procedural generation and physics in a roguelike.
  { id: "far-side", name: "Far Side", type: "Game Physics", year: "2024", art: PLATES.proceduralMoon }, // prettier-ignore
  { id: "level-seed", name: "Level Seed", type: "Game Physics", year: "2024", art: PLATES.levelSeed }, // prettier-ignore
  { id: "terrain", name: "Night Terrain", type: "Game Physics", year: "2024", art: PLATES.terrain }, // prettier-ignore

  // ASTRA — the capture work this repository is actually for.
  { id: "point-cloud", name: "Point Cloud", type: "Spatial Capture", year: "2026", art: PLATES.pointCloud }, // prettier-ignore
  { id: "coverage", name: "Coverage Plan", type: "Spatial Capture", year: "2026", art: PLATES.coverage }, // prettier-ignore
  { id: "scan-route", name: "Scan Route", type: "Spatial Capture", year: "2026", art: PLATES.scanPath }, // prettier-ignore
];

export const PLATE_ART = PROJECTS.map((p) => p.art);
