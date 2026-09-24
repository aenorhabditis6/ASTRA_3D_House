import { PLATES } from "./plates";

/**
 * Six pieces of work, three plates each, in ring order.
 *
 * The grouping is the data rather than a comment on it: the ring, the column,
 * the numbering and the note under the name are all derived from this list, so
 * moving a work moves all four together and nothing else needs touching.
 * Three plates kept adjacent means scrolling walks the length of one problem —
 * what was measured, what that leaves you with, what comes out — before the
 * palette changes and the next one starts.
 *
 * `type` and `year` are what the right-hand lockup reads; `label`, `meta` and
 * `blurb` are the note under the left one, and change only when the work does.
 *
 * Every plate is painted from the maths in `plates.js`. Nothing here is a
 * simulation result or a clinical image; they are illustrations of real work.
 */
export const WORKS = [
  {
    id: "venus",
    type: "Planetary",
    year: "2024",
    label: "NASA VfOx",
    meta: "Student Lead · DAVINCI / APL",
    blurb:
      "In-situ numerical analysis of the Venus atmosphere for the Oxygen Fugacity sensor, alongside instrument design, assembly and testing.",
    plates: [
      { id: "cloud-deck", name: "Cloud Deck", art: PLATES.cloudDeck },
      { id: "fugacity", name: "Oxygen Fugacity", art: PLATES.fugacity },
      { id: "descent", name: "Descent Profile", art: PLATES.descent },
    ],
  },
  {
    id: "tomography",
    type: "Tomography",
    year: "2025",
    label: "Stanford RSL",
    meta: "Research Intern · REU",
    blurb:
      "A 2.5D physics-informed diffusion model for sparse-view cone-beam CT, with the Radon transform as a forward constraint and anatomical fidelity checked downstream.",
    link: "https://drive.google.com/file/d/1dviuzmckyB8s-0lzJKJfOB2dXtAYdcyc/view?usp=sharing",
    linkLabel: "Research poster",
    plates: [
      { id: "sinogram", name: "Sparse Sinogram", art: PLATES.sinogram },
      { id: "backprojection", name: "Back Projection", art: PLATES.backprojection }, // prettier-ignore
      {
        id: "reconstruction",
        name: "Reconstruction",
        art: PLATES.reconstruction,
      },
    ],
  },
  {
    id: "generative",
    type: "Generative",
    year: "2025",
    label: "Johns Hopkins",
    meta: "Research Assistant · with Dr. Fei Lu",
    blurb:
      "Patch-based generative models written as interacting particle systems, using statistical mechanics and optimal transport to study convergence and mode coverage.",
    plates: [
      { id: "interacting", name: "Interacting Particles", art: PLATES.interacting }, // prettier-ignore
      { id: "transport", name: "Optimal Transport", art: PLATES.transport },
      { id: "emergence", name: "Noise to Form", art: PLATES.emergence },
    ],
  },
  {
    id: "soft-matter",
    type: "Soft Matter",
    year: "2024",
    label: "Beller Group",
    meta: "Undergraduate Researcher · Johns Hopkins",
    blurb:
      "Brownian dynamics of active particles and bead-spring chains under Lennard-Jones potentials and Hookean springs, on self-propulsion and diffusion in nematic-shaped particles.",
    link: "https://drive.google.com/file/d/1Z1x8eYSvfKmizgS9J_TXseVaaQUHejTi/view?usp=sharing",
    linkLabel: "Research summary",
    plates: [
      { id: "brownian", name: "Brownian Path", art: PLATES.brownian },
      { id: "bead-spring", name: "Bead and Spring", art: PLATES.beadSpring },
      { id: "nematic", name: "Nematic Defects", art: PLATES.nematic },
    ],
  },
  {
    id: "moon",
    type: "Game Physics",
    year: "2024",
    label: "Backside of the Moon",
    meta: "Founder · Pava Accelerator",
    blurb:
      "An SCP-style roguelike: procedural level generation, game AI and physics integration, funded by the Pava Accelerator and the Engineering Department.",
    link: "https://github.com/ZichenFrankFu/Backside_of_the_Moon",
    linkLabel: "Game repository",
    plates: [
      { id: "far-side", name: "Far Side", art: PLATES.proceduralMoon },
      { id: "level-seed", name: "Level Seed", art: PLATES.levelSeed },
      { id: "terrain", name: "Night Terrain", art: PLATES.terrain },
    ],
  },
  {
    id: "astra",
    type: "Spatial Capture",
    year: "2026",
    label: "ASTRA",
    meta: "Capture planning · this repository",
    blurb:
      "Planning a house scan: where to stand, what each station can actually see, and the route that covers the whole place in one pass.",
    plates: [
      { id: "point-cloud", name: "Point Cloud", art: PLATES.pointCloud },
      { id: "coverage", name: "Coverage Plan", art: PLATES.coverage },
      { id: "scan-route", name: "Scan Route", art: PLATES.scanPath },
    ],
  },
];

// Flattened for the ring. `work` is the row's own group, so anything reading a
// card can reach its context without a second lookup.
export const PROJECTS = WORKS.flatMap((work) =>
  work.plates.map((plate) => ({
    ...plate,
    type: work.type,
    year: work.year,
    work,
  })),
);

// Where each work's run of three starts, and which work each card belongs to.
// The column needs the first to lay its headings out, `paintList` the second
// to light the right one up.
export const WORK_OFFSETS = WORKS.reduce(
  (acc, work) => [...acc, acc[acc.length - 1] + work.plates.length],
  [0],
).slice(0, -1);

export const WORK_OF = WORKS.flatMap((work, w) => work.plates.map(() => w));

export const PLATE_ART = PROJECTS.map((p) => p.art);
