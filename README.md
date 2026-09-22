# ASTRA 3D House

ASTRA converts a reviewed 2D room trace into a deterministic, editable Blender
logic model. The first implemented project is the **right-side bedroom** in the
supplied dorm floor plan. It deliberately builds structure and semantic proxy
objects before any photo-derived geometry or texture is introduced.

## What this MVP proves

The workflow has one inspectable chain of evidence:

```text
immutable floor-plan PNG
  → reviewed pixel-space annotation
  → bed-based metric calibration
  → validated room.json
  → Blender structure and proxy objects
  → GLB read-back
```

Every measured or assumed value has a source kind and confidence. The supplied
11 ft ceiling height, `2.13 × 1.45 m` bed, two door heights, and window dimensions
are confirmed. Unmeasured furniture heights remain explicit assumptions.

## Prerequisites

- Python 3.11 or newer (the package has no third-party Python dependencies)
- Blender 5.2.2 LTS at `/Applications/Blender.app/Contents/MacOS/Blender`, or an
  equivalent executable supplied with `--blender`
- macOS users must allow a headless Blender process to access Metal. A restricted
  sandbox without Metal can crash before Blender reaches the Python script.

## Build the right-bedroom model

From the repository root:

```bash
PYTHONPATH=src python3 -m astra_house.cli build-logical \
  --project projects/dorm-right-bedroom \
  --output build/dorm-right-bedroom \
  --blender /Applications/Blender.app/Contents/MacOS/Blender
```

The command first verifies the immutable source SHA-256, regenerates and
validates the logical model, writes human/machine review artifacts, invokes
Blender, and finally checks that the Blend, GLB, and schematic PNG all exist. A
validation failure returns exit code 2; a failed Blender process returns exit
code 3.

## Build the Xiaomi diagnostic capture guide

This step does not require Blender. It turns the reviewed room model into a
self-contained shooting guide for the first 48-photo reconstruction test:

```bash
PYTHONPATH=src python3 -m astra_house.cli build-capture-pack \
  --project projects/dorm-right-bedroom \
  --output build/dorm-right-bedroom/capture-pack
```

Open `build/dorm-right-bedroom/capture-pack/index.html` on a phone or computer.
The guide contains four ordered passes: 24 structure-loop views, 8 high/low
views, 8 corner/occlusion views, and 8 opening/scale-anchor views. The same
command also writes an empty `capture-intake.json` for matching original files
to shot IDs and a `capture-pack-report.json` containing validation status,
counts, and source hashes.

Use one Xiaomi 17 Ultra for the complete batch: landscape 4:3 JPG stills from
the 1× Leica 23 mm main camera only. Do not mix iPhone images into this capture
ID, switch lenses, use 50 MP/RAW, or rename files on the phone. ARCore is
optional and currently unverified for the exact Xiaomi 17 Ultra model; the RGB
route and later camera-pose recovery do not depend on it. The phone's laser
focus sensor is not LiDAR.

## Artifacts

- `projects/dorm-right-bedroom/room.json` — versioned meter/Z-up logical model,
  with six walls, four openings, six semantic proxies, and field-level sources.
- `projects/dorm-right-bedroom/measurements.json` — original confirmed metric
  observations, their targets, and whether each is an exact override or an
  audit-only constraint.
- `build/dorm-right-bedroom/plan-review.svg` — portable, self-contained overlay;
  the original PNG is embedded and every trace remains visible.
- `build/dorm-right-bedroom/quality-report.json` — hashes, scale, counts,
  confidence data, a measured-versus-modeled residual table, and stable warnings.
- `build/dorm-right-bedroom/house_master.blend` — editable Blender source with
  named collections and custom provenance properties.
- `build/dorm-right-bedroom/house.glb` — portable geometry export whose semantic
  object names are verified by importing it into a clean Blender scene.
- `build/dorm-right-bedroom/schematic-axonometric.png` — `1600 × 1200` colored
  orthographic cutaway rendered from the same geometry, with blue bed, orange
  work area, yellow storage, and cyan windows.
- On a geometry-valid route, `build/dorm-right-bedroom/capture-pack/index.html`
  is a self-contained interactive map with independent capture modes and a
  complete printable fallback. Intake/report JSON contain mode-specific rows,
  input hashes, coverage diagnostics and review status.

**Current route status: blocked by geometry preflight.** The frozen 24/48-shot
source contains mutually incompatible target/station requirements under the
60° usable field of view. For example, `L01-A` and `C04-A` require a minimum
77.47° span between the north wall and entry door from station 1. The production
build correctly fails before replacing existing outputs. Existing old build
files are not evidence that the new route passed. Source route revision is
pending; no coverage-review approval is recorded.

`build/` is reproducible and intentionally ignored by Git.

## Interactive workflow preview and field delivery

The browser fixtures provide a **simulation only**, visibly marked blocked,
so the interaction can be reviewed while the source route is being corrected:

```bash
npm ci
npx playwright install chromium
npm run build:capture-fixtures
python3 -m http.server 8765 --directory build/browser-simulation/capture-pack
```

See the fixture script's printed paths if the test output layout changes.
The simulation renders the actual plan and failed diagnostics without calling
the production package writer. It is not a capture-release artifact.

After a corrected route passes preflight, use the unchanged production command:

```bash
PYTHONPATH=src python3 -m astra_house.cli build-capture-pack \
  --project projects/dorm-right-bedroom \
  --output build/dorm-right-bedroom/capture-pack
caffeinate -i python3 -m http.server 8765 --directory build/dorm-right-bedroom/capture-pack
```

Prefer a stable HTTPS URL for field delivery. For Mac-LAN HTTP, keep the Mac
powered with its lid open, and keep server, port, hostname/IP and network
unchanged. Open and reload the exact phone URL before capture. Campus Wi-Fi
client isolation may prevent LAN access; use stable HTTPS in that case. A loaded
page needs no further network requests, but a reclaimed/reloaded tab still
needs the same reachable origin. Do not change origins mid-capture.

Select a mode, acknowledge the camera/closed-door checklist, then manually
confirm each station visit. Mark each photo or group after using the native
camera. Mode progress is independent; refresh resumes the route but requires
fresh station confirmation. The guide does not detect indoor position or read
images. Export progress regularly and before resetting a mode. Storage failure
keeps the workflow in memory and displays a warning. Older route hashes remain
discoverable for raw export; invalid event suffixes are retained for diagnosis.

`capture_started` opens the first photo-intake interval. Each completion,
group-completion or skip closes an interval and begins the next;
`station_confirmed` is only an auxiliary marker. Group shot order is inferred.
Match EXIF `DateTimeOriginal` with optional `SubSecTimeOriginal` and
`OffsetTimeOriginal`; without the offset, event `tz_offset_min` is an explicit
assumption. Reopened/undone shots and ambiguous timing need manual review.
Out-of-window images remain unassigned and retained. Upload original JPGs,
unrenamed and uncompressed, with the exported progress JSON; keep retakes.

The [Xiaomi pilot matrix](docs/field-tests/xiaomi-capture-guide-pilot.md) remains
unrun. Desktop tests establish software behavior, not Android field readiness.

## Verification

Run the standard-library suite:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
node --test tests/test_capture_events.cjs
npm run test:capture-browser
```

Verify the generated Blender file and GLB independently:

```bash
/Applications/Blender.app/Contents/MacOS/Blender \
  --background build/dorm-right-bedroom/house_master.blend \
  --python-exit-code 1 --python tests/blender/assert_scene.py

/Applications/Blender.app/Contents/MacOS/Blender \
  --background --factory-startup --python-exit-code 1 \
  --python tests/blender/assert_glb.py -- build/dorm-right-bedroom/house.glb

/Applications/Blender.app/Contents/MacOS/Blender \
  --background --factory-startup --python-exit-code 1 \
  --python tests/blender/assert_schematic.py -- \
  build/dorm-right-bedroom/schematic-axonometric.png
```

`--python-exit-code 1` is important: without it Blender can print a Python
assertion traceback yet still return process status 0.

## Review and correction rules

1. Check `plan-review.svg` before trusting the 3D file.
2. Correct source-space facts—room boundary, opening span, object footprint—in
   `projects/dorm-right-bedroom/plan-annotation.json`, then rebuild.
3. Record an approved real-world dimension in the logical-data generation path
   and its `SourceRef`; do not silently replace a provisional value.
4. Never hand-edit generated wall geometry as the source of truth. Blender edits
   are presentation experiments until represented in the annotation/model layer.
5. Treat `quality-report.json` warnings as unresolved until a new measurement or
   photograph supplies evidence.

## Current confirmed measurements

- bed: `2.13 × 1.45 m`;
- east wall: `4.85 m`, containing two windows each `1.27 m` wide and `1.78 m`
  high with `0.77 m` sills; their along-wall offsets are `0.79 m` and `2.55 m`;
- north wall: `2.94 m`;
- desk width: `1.22 m`;
- closet projection depth: `0.73 m`;
- west living-room exit door: `1.00 × 2.37 m`;
- bathroom door: `0.91 × 2.37 m`;
- west-facing bathroom-door wall: `1.33 m` (audit-only; the current unsegmented
  floor-plan edge measures `2.57 m`, so this remains an explicit conflict);
- west exit-door wall: `2.50 m` (audit-only).

The cardinal interpretation follows the on-site correction: the double-window
wall is east, the `2.94 m` wall is north, and the west side first contains the
`2.50 m` exit-door wall before the footprint extends into the bathroom return.
The bathroom door is on the separate west-facing wall beside the closet—the
horizontal wall below the bedroom in the drawing—not on the connecting return
or at the entry-door corner.

Exact overrides are written into generated geometry. Audit-only wall lengths do
not silently distort the floor polygon: their residuals are reported against the
current plan trace, with absolute errors above 5% marked `needs_review`.

## Scope boundary

This first plan contains **no photo reconstruction, LiDAR processing, COLMAP,
dense depth, generated texture, NeRF, Gaussian Splatting, or structural fusion**.
Those later stages will consume this logical model as the metric/semantic prior.
Keeping them separate makes the current geometry independently reviewable and
lets future photos replace appearance without rewriting room structure.
