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
11 ft ceiling height is confirmed; the full-bed scale is provisional; opening
and furniture heights are explicit assumptions.

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
Blender, and finally checks that both Blender outputs exist. A validation failure
returns exit code 2; a failed Blender process returns exit code 3.

## Artifacts

- `projects/dorm-right-bedroom/room.json` — versioned meter/Z-up logical model,
  with six walls, three openings, six semantic proxies, and field-level sources.
- `build/dorm-right-bedroom/plan-review.svg` — portable, self-contained overlay;
  the original PNG is embedded and every trace remains visible.
- `build/dorm-right-bedroom/quality-report.json` — hashes, scale, counts,
  confidence data, and stable warnings for provisional assumptions.
- `build/dorm-right-bedroom/house_master.blend` — editable Blender source with
  named collections and custom provenance properties.
- `build/dorm-right-bedroom/house.glb` — portable geometry export whose semantic
  object names are verified by importing it into a clean Blender scene.

`build/` is reproducible and intentionally ignored by Git.

## Verification

Run the standard-library suite:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Verify the generated Blender file and GLB independently:

```bash
/Applications/Blender.app/Contents/MacOS/Blender \
  --background build/dorm-right-bedroom/house_master.blend \
  --python-exit-code 1 --python tests/blender/assert_scene.py

/Applications/Blender.app/Contents/MacOS/Blender \
  --background --factory-startup --python-exit-code 1 \
  --python tests/blender/assert_glb.py -- build/dorm-right-bedroom/house.glb
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

## Scope boundary

This first plan contains **no photo reconstruction, LiDAR processing, COLMAP,
dense depth, generated texture, NeRF, Gaussian Splatting, or structural fusion**.
Those later stages will consume this logical model as the metric/semantic prior.
Keeping them separate makes the current geometry independently reviewable and
lets future photos replace appearance without rewriting room structure.
