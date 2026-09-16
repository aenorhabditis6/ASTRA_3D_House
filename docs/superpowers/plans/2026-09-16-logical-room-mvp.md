# Logical Room MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the trusted dorm floor plan and confirmed measurements into a validated `room.json`, an editable untextured Blender scene, a GLB export, and a review report for the upper-right bedroom.

**Architecture:** A pure-standard-library Python package owns the metric room model, validation, plan calibration, wall decomposition, overlay generation, and command-line orchestration. A thin Blender Python adapter consumes the same `room.json` and deterministic box specifications to create named collections and export `.blend`/`.glb` artifacts. The raster plan is not reinterpreted inside Blender; all provenance and provisional assumptions remain explicit in JSON.

**Tech Stack:** Python 3.11+ standard library, `unittest`, JSON, SVG, Blender 5.2.2 LTS and Blender Python (`bpy`)

**Spec:** `docs/superpowers/specs/2026-09-16-room-reconstruction-workflow-design.md`

## Global Constraints

- Reconstruct only the upper-right bedroom in `assets/reference/floorplans/dorm-suite-floorplan.png`; exclude the adjacent bathroom and central shared area.
- Treat the supplied plan topology and relative proportions as hard constraints.
- Use a Full mattress footprint of 54 x 75 in (1.3716 x 1.905 m) as a provisional XY scale anchor; the measured plan symbol is approximately 149 x 109 px.
- Use 11 ft (3.3528 m) as the confirmed floor-to-ceiling height.
- Use meters, radians, and a right-handed Z-up room coordinate system.
- Keep source assets immutable and record provenance and confidence for every assumed or inferred dimension.
- Run this logical-model phase locally on Apple Silicon without CUDA or network services.
- Represent furniture as simple semantic proxy boxes; do not model fabric, clutter, textures, dense geometry, or Gaussian Splats in this plan.
- Unknown opening heights remain explicit provisional assumptions and must appear in the quality report.
- All commands below run from `/Users/KingBear/Documents/GitHub/ASTRA_3D_House`.

## Subproject Boundary

This plan is the first of four independently testable implementation plans:

1. Logical room MVP: plan calibration, `room.json`, Blender shell, GLB, and review artifacts — covered here.
2. Capture QC and camera recovery: image ingestion, hloc/SIFT profiles, COLMAP mapping, and reshoot reporting.
3. Structural fusion: dense geometry, plane extraction, wall assignment, and `Sim(3)` alignment.
4. Appearance delivery: texture baking, neutral/reshoot surfaces, cloud Splatting, and final combined quality report.

The first plan ends with usable software and a reviewable room model. It does not stub or pretend to complete the other three subprojects.

## File Structure

```text
.gitignore                                      Generated files and Python caches
pyproject.toml                                  Package metadata and CLI entry point
src/astra_house/__init__.py                     Public package version
src/astra_house/errors.py                       Typed validation and build errors
src/astra_house/model.py                        Immutable room-domain dataclasses and JSON conversion
src/astra_house/io.py                           Atomic JSON load/save functions
src/astra_house/manifest.py                     Immutable source hashing and verification
src/astra_house/plan.py                         Plan annotation parsing and pixel-to-meter calibration
src/astra_house/logical_room.py                 Annotation-to-RoomModel conversion
src/astra_house/geometry.py                     Blender-independent box and polygon specifications
src/astra_house/review.py                       SVG overlay and JSON quality report generation
src/astra_house/cli.py                          `astra-house build-logical` orchestration
blender/build_scene.py                          Blender adapter and `.blend`/`.glb` writer
projects/dorm-right-bedroom/plan-annotation.json Reviewed pixel-space source annotation
projects/dorm-right-bedroom/manifest.json        Immutable source-asset hashes
projects/dorm-right-bedroom/room.json            Versioned metric logical room
tests/test_model.py                              Domain validation and round-trip tests
tests/test_manifest.py                           Source-integrity tests
tests/test_plan.py                               Scale and coordinate conversion tests
tests/test_logical_room.py                       Target-room generation tests
tests/test_geometry.py                           Wall/opening decomposition tests
tests/test_review.py                             Overlay and report tests
tests/test_cli.py                                Non-Blender orchestration tests
tests/blender/assert_scene.py                    Blender collection and object assertions
tests/blender/assert_glb.py                      Blender GLB read-back assertions
README.md                                        Setup and first-room commands
```

Generated files live under `build/dorm-right-bedroom/` and are ignored by Git. The reviewed `projects/dorm-right-bedroom/room.json` remains versioned because it is the structural source of truth.

---

### Task 1: Package and command skeleton

**Files:**
- Create: `.gitignore`
- Create: `pyproject.toml`
- Create: `src/astra_house/__init__.py`
- Create: `src/astra_house/errors.py`
- Create: `src/astra_house/cli.py`
- Create: `tests/test_cli.py`

**Interfaces:**
- Consumes: no earlier task interfaces.
- Produces: `astra_house.cli.main(argv: list[str] | None = None) -> int`, `AstraError`, `ValidationError`, and an installable `astra-house` console entry point.

- [ ] **Step 1: Write the failing CLI smoke test**

```python
# tests/test_cli.py
import contextlib
import io
import unittest

from astra_house.cli import main


class CliSmokeTest(unittest.TestCase):
    def test_no_command_prints_help_and_returns_two(self) -> None:
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            result = main([])
        self.assertEqual(result, 2)
        self.assertIn("build-logical", stderr.getvalue())
```

- [ ] **Step 2: Run the test and verify the package is missing**

Run: `PYTHONPATH=src python3 -m unittest tests.test_cli -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'astra_house'`.

- [ ] **Step 3: Add the minimal package, error types, and CLI parser**

```toml
# pyproject.toml
[build-system]
requires = ["setuptools>=78"]
build-backend = "setuptools.build_meta"

[project]
name = "astra-3d-house"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = []

[project.scripts]
astra-house = "astra_house.cli:console_main"

[tool.setuptools.packages.find]
where = ["src"]
```

Implement `main()` with `argparse`, register an initially empty `build-logical` subparser, print help to stderr when no command is supplied, and have `console_main()` raise `SystemExit(main())`. Add `if __name__ == "__main__": console_main()` so `python -m astra_house.cli` works. Define `AstraError(RuntimeError)` and `ValidationError(AstraError)` in `errors.py`. Set `__version__ = "0.1.0"`.

Add these ignore rules:

```gitignore
.venv/
__pycache__/
*.py[cod]
build/
.DS_Store
```

- [ ] **Step 4: Run the smoke test**

Run: `PYTHONPATH=src python3 -m unittest tests.test_cli -v`

Expected: one test passes.

- [ ] **Step 5: Commit the skeleton**

```bash
git add .gitignore pyproject.toml src/astra_house tests/test_cli.py
git commit -m "build: scaffold logical room package"
```

---

### Task 2: Validated room-domain model

**Files:**
- Create: `src/astra_house/model.py`
- Create: `src/astra_house/io.py`
- Create: `tests/test_model.py`

**Interfaces:**
- Consumes: `ValidationError` from `astra_house.errors`.
- Produces: `Vec2`, `Vec3`, `SourceRef`, `Wall`, `Opening`, `ProxyObject`, `RoomModel`, `load_room(path: Path) -> RoomModel`, and `save_room(model: RoomModel, path: Path) -> None`.

- [ ] **Step 1: Write failing validation and JSON round-trip tests**

```python
# tests/test_model.py
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from astra_house.errors import ValidationError
from astra_house.io import load_room, save_room
from astra_house.model import Opening, RoomModel, SourceRef, Vec2, Wall


class RoomModelTest(unittest.TestCase):
    def make_room(self) -> RoomModel:
        source = SourceRef("confirmed_measurement", "user", 1.0)
        return RoomModel(
            schema_version="1.0", room_id="test-room", units="meters", up_axis="Z",
            ceiling_height_m=3.0, ceiling_height_source=source, scale_source=source,
            floor_polygon=(Vec2(0, 0), Vec2(4, 0), Vec2(4, 3), Vec2(0, 3)),
            walls=(Wall("north", Vec2(0, 3), Vec2(4, 3), 0.12, source, source),),
            openings=(Opening("door", "north", 1.0, 0.9, 0.0, 2.03, source, source),),
            proxies=(), provenance=(source,),
        )

    def test_round_trip_preserves_room(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "room.json"
            room = self.make_room()
            save_room(room, path)
            self.assertEqual(load_room(path), room)

    def test_opening_must_fit_parent_wall(self) -> None:
        room = self.make_room()
        source = room.provenance[0]
        bad = replace(room, openings=(Opening("door", "north", 3.5, 0.9, 0.0, 2.03, source, source),))
        with self.assertRaisesRegex(ValidationError, "door.*north"):
            bad.validate()
```

- [ ] **Step 2: Run the tests and verify missing model types**

Run: `PYTHONPATH=src python3 -m unittest tests.test_model -v`

Expected: FAIL because `astra_house.model` does not exist.

- [ ] **Step 3: Implement immutable dataclasses and validation**

Use frozen dataclasses. `SourceRef` contains `kind: str`, `reference: str`, and `confidence: float`. `Opening.offset_m` is measured from its parent wall's `start`; `sill_m=0` denotes a door. Preserve per-field provenance with these exact fields:

- `Wall(..., thickness_m, geometry_source, thickness_source)`.
- `Opening(..., sill_m, height_m, position_source, vertical_source)`.
- `ProxyObject(id, kind, center, size, yaw_rad, footprint_source, height_source)`.
- `RoomModel(..., ceiling_height_m, ceiling_height_source, scale_source, ...)`.

`RoomModel.validate()` must enforce:

- `schema_version == "1.0"`, `units == "meters"`, and `up_axis == "Z"`.
- positive ceiling height and at least three non-collinear floor points.
- unique wall, opening, and proxy identifiers.
- positive wall lengths and thicknesses.
- every opening references an existing wall and fits within its length and the ceiling height.
- every confidence value lies in `[0, 1]`.

Add `to_dict()` and `from_dict()` methods with stable keys and tuples restored on load. `save_room()` must validate first, write sorted/indented JSON to a sibling temporary file, and replace the destination atomically. `load_room()` must reject malformed JSON with `ValidationError` including the path.

- [ ] **Step 4: Run domain tests**

Run: `PYTHONPATH=src python3 -m unittest tests.test_model -v`

Expected: both tests pass.

- [ ] **Step 5: Commit the data contract**

```bash
git add src/astra_house/model.py src/astra_house/io.py tests/test_model.py
git commit -m "feat: add validated room data contract"
```

---

### Task 3: Immutable source manifest

**Files:**
- Create: `src/astra_house/manifest.py`
- Create: `tests/test_manifest.py`
- Create: `projects/dorm-right-bedroom/manifest.json`

**Interfaces:**
- Consumes: `ValidationError` and the stored floor-plan PNG.
- Produces: `sha256_file(path: Path) -> str`, `build_manifest(root: Path, paths: tuple[Path, ...]) -> dict`, and `verify_manifest(root: Path, manifest: dict) -> None`.

- [ ] **Step 1: Write failing source-integrity tests**

```python
# tests/test_manifest.py
import json
import tempfile
import unittest
from pathlib import Path

from astra_house.errors import ValidationError
from astra_house.manifest import sha256_file, verify_manifest


class ManifestTest(unittest.TestCase):
    def test_floorplan_hash_matches_recorded_source(self) -> None:
        manifest = json.loads(Path("projects/dorm-right-bedroom/manifest.json").read_text())
        asset = manifest["assets"][0]
        self.assertEqual(asset["sha256"], "8aae212209211a2e0f668801de6148cee8dae6c155b487a66c8797fdbcc77011")
        self.assertEqual(sha256_file(Path(asset["path"])), asset["sha256"])

    def test_changed_source_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "plan.png"
            path.write_bytes(b"changed")
            manifest = {"schema_version": "1.0", "assets": [{"path": "plan.png", "bytes": 7, "sha256": "0" * 64}]}
            with self.assertRaisesRegex(ValidationError, "plan.png.*SHA-256"):
                verify_manifest(root, manifest)
```

- [ ] **Step 2: Add the recorded manifest and run the failing test**

```json
{
  "schema_version": "1.0",
  "assets": [
    {
      "path": "assets/reference/floorplans/dorm-suite-floorplan.png",
      "bytes": 183782,
      "sha256": "8aae212209211a2e0f668801de6148cee8dae6c155b487a66c8797fdbcc77011",
      "received_date": "2026-09-16",
      "role": "trusted_floorplan"
    }
  ]
}
```

Run: `PYTHONPATH=src python3 -m unittest tests.test_manifest -v`

Expected: FAIL because `astra_house.manifest` does not exist.

- [ ] **Step 3: Implement deterministic hashing and verification**

Stream files through `hashlib.sha256()` in 1 MiB blocks. Reject an unsupported schema version, duplicate relative paths, absolute paths, parent traversal, missing files, byte-size mismatches, and digest mismatches. `build_manifest()` returns assets sorted by POSIX relative path and never writes into the source asset directory.

- [ ] **Step 4: Run manifest tests**

Run: `PYTHONPATH=src python3 -m unittest tests.test_manifest -v`

Expected: two tests pass.

- [ ] **Step 5: Commit source integrity support**

```bash
git add src/astra_house/manifest.py tests/test_manifest.py projects/dorm-right-bedroom/manifest.json
git commit -m "feat: verify immutable reconstruction sources"
```

---

### Task 4: Plan annotation and metric calibration

**Files:**
- Create: `projects/dorm-right-bedroom/plan-annotation.json`
- Create: `src/astra_house/plan.py`
- Create: `tests/test_plan.py`

**Interfaces:**
- Consumes: `Vec2` and `ValidationError`.
- Produces: `PlanAnnotation.from_dict(data: dict)`, `PlanCalibration.from_annotation(annotation)`, `PlanCalibration.meters_per_pixel`, `pixel_to_room(point: Vec2) -> Vec2`, and `room_to_pixel(point: Vec2) -> Vec2`.

- [ ] **Step 1: Add the reviewed source annotation**

Create `plan-annotation.json` with these exact source-space values:

```json
{
  "schema_version": "1.0",
  "image": {
    "path": "assets/reference/floorplans/dorm-suite-floorplan.png",
    "width_px": 1000,
    "height_px": 680
  },
  "target": {
    "room_id": "dorm-right-bedroom",
    "origin_px": [495, 385],
    "floor_polygon_px": [[495, 82], [849, 82], [849, 385], [665, 385], [665, 294], [495, 294]],
    "ceiling_height_m": 3.3528,
    "wall_thickness_m": 0.12
  },
  "scale_anchor": {
    "id": "full-bed",
    "bbox_px": [694, 118, 843, 227],
    "size_m": [1.905, 1.3716],
    "fit": "isotropic_least_squares",
    "source": "floorplan label FULL BED"
  },
  "openings": [
    {"id": "window-north", "edge_index": 0, "start_px": [558, 82], "end_px": [776, 82], "sill_m": 0.9, "height_m": 1.5, "confidence": 0.35},
    {"id": "bath-door-south", "edge_index": 2, "start_px": [758, 385], "end_px": [686, 385], "sill_m": 0.0, "height_m": 2.03, "confidence": 0.35},
    {"id": "entry-door", "edge_index": 4, "start_px": [665, 294], "end_px": [601, 294], "sill_m": 0.0, "height_m": 2.03, "confidence": 0.35}
  ],
  "objects": [
    {"id": "bed-full", "kind": "bed", "bbox_px": [694, 118, 843, 227], "height_m": 0.55},
    {"id": "desk", "kind": "desk", "bbox_px": [510, 84, 558, 184], "height_m": 0.76},
    {"id": "chair", "kind": "chair", "bbox_px": [557, 103, 591, 146], "height_m": 0.9},
    {"id": "chest", "kind": "chest", "bbox_px": [724, 166, 775, 218], "height_m": 0.65},
    {"id": "pedestal", "kind": "pedestal", "bbox_px": [810, 229, 845, 261], "height_m": 0.65},
    {"id": "closet", "kind": "fixed_closet", "bbox_px": [795, 272, 849, 385], "height_m": 2.4}
  ]
}
```

These values are the initial reviewed trace. Their review overlay is produced in Task 8; edits after that review change this source file rather than hiding adjustments in Blender.

- [ ] **Step 2: Write failing calibration tests**

```python
# tests/test_plan.py
import json
import unittest
from pathlib import Path

from astra_house.model import Vec2
from astra_house.plan import PlanAnnotation, PlanCalibration


class PlanCalibrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        data = json.loads(Path("projects/dorm-right-bedroom/plan-annotation.json").read_text())
        cls.annotation = PlanAnnotation.from_dict(data)
        cls.calibration = PlanCalibration.from_annotation(cls.annotation)

    def test_isotropic_scale_uses_both_bed_axes(self) -> None:
        self.assertAlmostEqual(self.calibration.meters_per_pixel, 0.0127149052, places=9)

    def test_coordinate_round_trip(self) -> None:
        pixel = Vec2(849, 82)
        restored = self.calibration.room_to_pixel(self.calibration.pixel_to_room(pixel))
        self.assertAlmostEqual(restored.x, pixel.x, places=9)
        self.assertAlmostEqual(restored.y, pixel.y, places=9)

    def test_y_axis_points_up_in_room_space(self) -> None:
        top = self.calibration.pixel_to_room(Vec2(495, 82))
        bottom = self.calibration.pixel_to_room(Vec2(495, 294))
        self.assertGreater(top.y, bottom.y)
```

- [ ] **Step 3: Run tests and verify calibration is missing**

Run: `PYTHONPATH=src python3 -m unittest tests.test_plan -v`

Expected: FAIL because `astra_house.plan` does not exist.

- [ ] **Step 4: Implement annotation parsing and calibration**

For bed pixel width `w`, height `h`, metric width `W`, and height `H`, compute the single isotropic scale that minimizes squared axis error:

```python
meters_per_pixel = (w * W + h * H) / (w * w + h * h)
```

Map pixels into the room frame with the declared origin:

```python
x_m = (x_px - origin_x_px) * meters_per_pixel
y_m = (origin_y_px - y_px) * meters_per_pixel
```

Validate image bounds, nonzero anchor dimensions, opening endpoints on their declared polygon edge within two pixels, and every object box inside the target bounding extent.

- [ ] **Step 5: Run calibration tests**

Run: `PYTHONPATH=src python3 -m unittest tests.test_plan -v`

Expected: three tests pass.

- [ ] **Step 6: Commit the trace and calibration**

```bash
git add projects/dorm-right-bedroom/plan-annotation.json src/astra_house/plan.py tests/test_plan.py
git commit -m "feat: calibrate right bedroom floor plan"
```

---

### Task 5: Generate the versioned logical room

**Files:**
- Create: `src/astra_house/logical_room.py`
- Create: `tests/test_logical_room.py`
- Generate and add: `projects/dorm-right-bedroom/room.json`

**Interfaces:**
- Consumes: `PlanAnnotation`, `PlanCalibration`, and all room model dataclasses.
- Produces: `build_logical_room(annotation: PlanAnnotation) -> RoomModel`.

- [ ] **Step 1: Write failing target-room tests**

```python
# tests/test_logical_room.py
import json
import unittest
from pathlib import Path

from astra_house.logical_room import build_logical_room
from astra_house.plan import PlanAnnotation


class LogicalRoomTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        raw = json.loads(Path("projects/dorm-right-bedroom/plan-annotation.json").read_text())
        cls.room = build_logical_room(PlanAnnotation.from_dict(raw))

    def test_confirmed_height_and_l_shaped_floor(self) -> None:
        self.assertAlmostEqual(self.room.ceiling_height_m, 3.3528)
        self.assertEqual(len(self.room.floor_polygon), 6)

    def test_semantic_inventory(self) -> None:
        self.assertEqual({item.id for item in self.room.proxies},
                         {"bed-full", "desk", "chair", "chest", "pedestal", "closet"})
        self.assertEqual({opening.id for opening in self.room.openings},
                         {"window-north", "bath-door-south", "entry-door"})
        bed = next(item for item in self.room.proxies if item.id == "bed-full")
        self.assertAlmostEqual(bed.size.x, 1.905)
        self.assertAlmostEqual(bed.size.y, 1.3716)

    def test_provisional_values_are_not_marked_confirmed(self) -> None:
        confidence = {opening.id: opening.vertical_source.confidence for opening in self.room.openings}
        self.assertLess(confidence["window-north"], 0.5)
        self.assertLess(confidence["entry-door"], 0.5)
```

- [ ] **Step 2: Run tests and verify the builder is missing**

Run: `PYTHONPATH=src python3 -m unittest tests.test_logical_room -v`

Expected: FAIL because `astra_house.logical_room` does not exist.

- [ ] **Step 3: Implement deterministic annotation conversion**

Create one wall per floor-polygon edge, named `wall-00` through `wall-05`, preserving edge direction. Convert opening endpoints into an offset and width on their parent edge. Convert proxy bounding boxes into metric centers and XY sizes; for `bed-full`, use the exact annotated `size_m` for XY and only use its pixel box for position. Use the annotated height for each proxy. Use these sources:

```python
plan_source = SourceRef("trusted_floorplan", "dorm-suite-floorplan.png", 1.0)
bed_scale_source = SourceRef("provisional_scale", "full-bed 54x75in", 0.6)
height_source = SourceRef("confirmed_measurement", "user: 11ft", 1.0)
assumption_source = SourceRef("provisional_assumption", "opening/furniture default height", 0.35)
```

Assign `plan_source` to wall geometry, opening position/width, and proxy footprints; assign `assumption_source` to wall thickness, opening vertical dimensions, and proxy heights. Assign `height_source` and `bed_scale_source` to the corresponding room-level fields. Call `room.validate()` before returning.

- [ ] **Step 4: Run logical-room tests**

Run: `PYTHONPATH=src python3 -m unittest tests.test_logical_room -v`

Expected: three tests pass.

- [ ] **Step 5: Generate and validate the versioned room file**

Run:

```bash
PYTHONPATH=src python3 -c 'import json; from pathlib import Path; from astra_house.io import save_room; from astra_house.logical_room import build_logical_room; from astra_house.plan import PlanAnnotation; p=Path("projects/dorm-right-bedroom/plan-annotation.json"); save_room(build_logical_room(PlanAnnotation.from_dict(json.loads(p.read_text()))), Path("projects/dorm-right-bedroom/room.json"))'
PYTHONPATH=src python3 -c 'from pathlib import Path; from astra_house.io import load_room; print(load_room(Path("projects/dorm-right-bedroom/room.json")).room_id)'
```

Expected: the second command prints `dorm-right-bedroom`.

- [ ] **Step 6: Commit the logical model**

```bash
git add src/astra_house/logical_room.py tests/test_logical_room.py projects/dorm-right-bedroom/room.json
git commit -m "feat: generate right bedroom logical model"
```

---

### Task 6: Decompose walls and openings into solid geometry

**Files:**
- Create: `src/astra_house/geometry.py`
- Create: `tests/test_geometry.py`

**Interfaces:**
- Consumes: `RoomModel`, `Wall`, and `Opening`.
- Produces: `BoxSpec`, `PolygonSpec`, `build_wall_boxes(room: RoomModel) -> tuple[BoxSpec, ...]`, `build_opening_boxes(room: RoomModel) -> tuple[BoxSpec, ...]`, `build_floor_spec(room: RoomModel) -> PolygonSpec`, and `build_ceiling_spec(room: RoomModel) -> PolygonSpec`.

- [ ] **Step 1: Write failing wall-opening tests**

```python
# tests/test_geometry.py
import unittest

from astra_house.geometry import build_opening_boxes, build_wall_boxes
from astra_house.model import Opening, RoomModel, SourceRef, Vec2, Wall


class WallGeometryTest(unittest.TestCase):
    def test_door_splits_wall_into_jambs_and_header(self) -> None:
        source = SourceRef("test", "fixture", 1.0)
        room = RoomModel(
            schema_version="1.0", room_id="door", units="meters", up_axis="Z",
            ceiling_height_m=3.0, ceiling_height_source=source, scale_source=source,
            floor_polygon=(Vec2(0, 0), Vec2(4, 0), Vec2(4, 3), Vec2(0, 3)),
            walls=(Wall("wall", Vec2(0, 0), Vec2(4, 0), 0.12, source, source),),
            openings=(Opening("door", "wall", 1.0, 0.9, 0.0, 2.1, source, source),),
            proxies=(), provenance=(source,),
        )
        boxes = build_wall_boxes(room)
        self.assertEqual([box.id for box in boxes],
                         ["wall:span-00", "wall:span-01", "wall:door:header"])
        self.assertAlmostEqual(sum(box.size.x * box.size.z for box in boxes), 10.11, places=6)

    def test_window_creates_sill_header_and_two_sides(self) -> None:
        source = SourceRef("test", "fixture", 1.0)
        room = RoomModel(
            schema_version="1.0", room_id="window", units="meters", up_axis="Z",
            ceiling_height_m=3.0, ceiling_height_source=source, scale_source=source,
            floor_polygon=(Vec2(0, 0), Vec2(4, 0), Vec2(4, 3), Vec2(0, 3)),
            walls=(Wall("wall", Vec2(0, 0), Vec2(4, 0), 0.12, source, source),),
            openings=(Opening("window", "wall", 1.0, 1.5, 0.8, 1.2, source, source),),
            proxies=(), provenance=(source,),
        )
        self.assertEqual(len(build_wall_boxes(room)), 4)
        opening_box = build_opening_boxes(room)[0]
        self.assertEqual(opening_box.id, "window")
        self.assertEqual(opening_box.collection, "OPENINGS")
```

- [ ] **Step 2: Run tests and verify geometry functions are missing**

Run: `PYTHONPATH=src python3 -m unittest tests.test_geometry -v`

Expected: FAIL because `astra_house.geometry` does not exist.

- [ ] **Step 3: Implement box decomposition without Blender imports**

`BoxSpec` contains `id`, `center: Vec3`, `size: Vec3`, `yaw_rad`, `collection`, and `source_id`. For each wall:

1. Sort openings by `offset_m` and reject overlap.
2. Emit full-height solid segments before, between, and after openings as `<wall-id>:span-00`, `<wall-id>:span-01`, and so on.
3. Emit a sill box when `sill_m > 0`.
4. Emit a header box from `sill_m + height_m` to the ceiling.
5. Transform along-wall centers into room XY coordinates and set yaw with `atan2`.

For the sample door, wall area is `4*3 - 0.9*2.1 = 10.11 m²`, which is the assertion above. Floor and ceiling specs reuse the exact six-point room polygon at `z=0` and `z=ceiling_height_m`.

`build_opening_boxes()` emits one thin semantic placeholder volume per opening, centered in its parent wall aperture and assigned to `OPENINGS`. It uses the exact opening ID so Blender creates `OPENINGS.entry-door`, `OPENINGS.bath-door-south`, and `OPENINGS.window-north`. The placeholder records dimensions and provenance but is not joined to structural wall solids.

- [ ] **Step 4: Run geometry tests and the full local suite**

Run: `PYTHONPATH=src python3 -m unittest discover -s tests -v`

Expected: all tests pass.

- [ ] **Step 5: Commit geometry generation**

```bash
git add src/astra_house/geometry.py tests/test_geometry.py
git commit -m "feat: generate wall and opening solids"
```

---

### Task 7: Build the Blender scene and export GLB

**Files:**
- Create: `blender/build_scene.py`
- Create: `tests/blender/assert_scene.py`
- Create: `tests/blender/assert_glb.py`

**Interfaces:**
- Consumes: `load_room()`, `build_wall_boxes()`, `build_floor_spec()`, and `build_ceiling_spec()`.
- Produces: `build_scene(room_path: Path, blend_path: Path, glb_path: Path) -> None`, `build/dorm-right-bedroom/house_master.blend`, and `build/dorm-right-bedroom/house.glb`.

- [ ] **Step 1: Write the failing Blender scene assertion**

```python
# tests/blender/assert_scene.py
import bpy

expected_collections = {"STRUCTURE", "OPENINGS", "FIXTURES", "FURNITURE_PROXY", "PHOTO_REFERENCE", "APPEARANCE"}
actual_collections = {collection.name for collection in bpy.data.collections}
assert expected_collections <= actual_collections, (expected_collections - actual_collections)
assert "STRUCTURE.floor" in bpy.data.objects
assert "STRUCTURE.ceiling" in bpy.data.objects
assert "OPENINGS.entry-door" in bpy.data.objects
assert "FURNITURE_PROXY.bed-full" in bpy.data.objects
assert "FIXTURES.closet" in bpy.data.objects
assert abs(bpy.data.objects["STRUCTURE.ceiling"].location.z - 3.3528) < 1e-6
assert bpy.context.scene.unit_settings.system == "METRIC"
assert abs(bpy.context.scene.unit_settings.scale_length - 1.0) < 1e-9
```

Run: `/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python tests/blender/assert_scene.py`

Expected: FAIL because the empty factory scene lacks the required collections.

- [ ] **Step 2: Implement deterministic Blender construction**

`build_scene.py` must:

- derive the repository root from `__file__` and prepend `src/` to `sys.path`;
- parse arguments after Blender's `--` separator;
- require exactly three positional arguments after `--`, delete any default cube/camera/light objects, and fail without overwriting existing outputs when arguments are invalid;
- set metric units and Z-up conventions;
- create all six required collections;
- create wall boxes, opening placeholder boxes, and proxy boxes with `bpy.data.meshes.new` or cube primitives, apply dimensions, and name objects as `<COLLECTION>.<semantic-id>`;
- route `fixed_closet` to `FIXTURES` and all movable proxy kinds to `FURNITURE_PROXY`;
- create the L-shaped floor and ceiling from the exact polygon as planar n-gons with opposing normals;
- create neutral materials `MAT.structure`, `MAT.fixture`, and `MAT.proxy` with no image textures;
- store `room_id`, `schema_version`, `geometry_source_kind`, `geometry_source_confidence`, `height_source_kind`, and `height_source_confidence` as custom object properties, using the matching wall/opening/proxy provenance fields;
- save the `.blend` and export visible mesh objects to GLB.

The script invocation is:

```bash
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python blender/build_scene.py -- projects/dorm-right-bedroom/room.json build/dorm-right-bedroom/house_master.blend build/dorm-right-bedroom/house.glb
```

- [ ] **Step 3: Run the builder and scene assertion**

Run the builder command above, then:

```bash
/Applications/Blender.app/Contents/MacOS/Blender --background build/dorm-right-bedroom/house_master.blend --python tests/blender/assert_scene.py
```

Expected: Blender exits with status 0 and no Python assertion failure.

- [ ] **Step 4: Add and run GLB read-back assertions**

```python
# tests/blender/assert_glb.py
import bpy
import sys

glb_path = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb_path)
names = {obj.name for obj in bpy.data.objects if obj.type == "MESH"}
assert "STRUCTURE.floor" in names
assert "OPENINGS.entry-door" in names
assert "FURNITURE_PROXY.bed-full" in names
assert len(names) >= 10
```

Run:

```bash
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python tests/blender/assert_glb.py -- build/dorm-right-bedroom/house.glb
```

Expected: Blender exits with status 0 and no Python assertion failure.

- [ ] **Step 5: Commit the Blender adapter and tests**

```bash
git add blender/build_scene.py tests/blender
git commit -m "feat: build and export logical Blender room"
```

---

### Task 8: Generate the plan overlay and quality report

**Files:**
- Create: `src/astra_house/review.py`
- Create: `tests/test_review.py`

**Interfaces:**
- Consumes: `PlanAnnotation`, `PlanCalibration`, and `RoomModel`.
- Produces: `write_plan_overlay(annotation, room, output: Path) -> None` and `write_quality_report(annotation, room, output: Path) -> None`.

- [ ] **Step 1: Write failing review-artifact tests**

```python
# tests/test_review.py
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from astra_house.io import load_room
from astra_house.plan import PlanAnnotation
from astra_house.review import write_plan_overlay, write_quality_report


class ReviewArtifactTest(unittest.TestCase):
    def test_overlay_and_report_expose_provisional_values(self) -> None:
        annotation = PlanAnnotation.from_dict(json.loads(Path("projects/dorm-right-bedroom/plan-annotation.json").read_text()))
        room = load_room(Path("projects/dorm-right-bedroom/room.json"))
        with tempfile.TemporaryDirectory() as directory:
            overlay = Path(directory) / "plan-review.svg"
            report = Path(directory) / "quality-report.json"
            write_plan_overlay(annotation, room, overlay)
            write_quality_report(annotation, room, report)
            root = ET.parse(overlay).getroot()
            self.assertEqual(root.attrib["viewBox"], "0 0 1000 680")
            result = json.loads(report.read_text())
            self.assertEqual(result["room_id"], "dorm-right-bedroom")
            self.assertIn("provisional_scale", result["warnings"])
            self.assertIn("assumed_opening_heights", result["warnings"])
```

- [ ] **Step 2: Run tests and verify review functions are missing**

Run: `PYTHONPATH=src python3 -m unittest tests.test_review -v`

Expected: FAIL because `astra_house.review` does not exist.

- [ ] **Step 3: Implement a self-contained SVG overlay**

The SVG must use the source image at 50% opacity and overlay:

- the six-point target polygon in blue;
- openings in orange, labeled with their identifiers;
- proxy bounding boxes in green, labeled with identifiers;
- the numeric scale `0.0127149052 m/px` and ceiling height `3.3528 m`;
- a visible warning that door/window heights are provisional.

Embed the PNG as a base64 `data:image/png` URI so the SVG remains portable. Escape all labels with `html.escape`.

The JSON report must include schema version, room ID, plan SHA-256, meters per pixel, ceiling height, counts by semantic kind, every source/confidence pair, and these warnings in stable order:

```json
["provisional_scale", "assumed_opening_heights", "untextured_proxy_geometry"]
```

- [ ] **Step 4: Run review tests and inspect the real overlay**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_review -v
PYTHONPATH=src python3 -c 'import json; from pathlib import Path; from astra_house.io import load_room; from astra_house.plan import PlanAnnotation; from astra_house.review import write_plan_overlay, write_quality_report; a=PlanAnnotation.from_dict(json.loads(Path("projects/dorm-right-bedroom/plan-annotation.json").read_text())); r=load_room(Path("projects/dorm-right-bedroom/room.json")); write_plan_overlay(a,r,Path("build/dorm-right-bedroom/plan-review.svg")); write_quality_report(a,r,Path("build/dorm-right-bedroom/quality-report.json"))'
open build/dorm-right-bedroom/plan-review.svg
```

Expected: tests pass; the polygon follows the right bedroom walls, the entry and bathroom openings interrupt the correct lower edges, and all six proxy boxes overlap their source symbols. If a trace is visibly displaced, edit only `plan-annotation.json`, regenerate `room.json`, and rerun Tasks 5-8 tests before committing.

- [ ] **Step 5: Commit review generation**

```bash
git add src/astra_house/review.py tests/test_review.py projects/dorm-right-bedroom/plan-annotation.json projects/dorm-right-bedroom/room.json
git commit -m "feat: add logical room review artifacts"
```

---

### Task 9: Wire the end-to-end command and acceptance workflow

**Files:**
- Modify: `src/astra_house/cli.py`
- Modify: `tests/test_cli.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: every interface from Tasks 2-8 and the Blender executable path.
- Produces: `astra-house build-logical --project projects/dorm-right-bedroom --blender /Applications/Blender.app/Contents/MacOS/Blender` and the complete `build/dorm-right-bedroom/` artifact set.

- [ ] **Step 1: Write the failing orchestration test**

Use a fake Blender executable so the unit test verifies arguments without launching Blender:

```python
import tempfile
from pathlib import Path

from astra_house.cli import build_logical_project


def test_build_logical_writes_non_blender_artifacts_and_invokes_blender(self) -> None:
    with tempfile.TemporaryDirectory() as directory:
        output = Path(directory) / "build"
        calls: list[list[str]] = []

        def fake_runner(command: list[str]) -> None:
            calls.append(command)
            (output / "house_master.blend").touch()
            (output / "house.glb").touch()

        result = build_logical_project(
            project_dir=Path("projects/dorm-right-bedroom"),
            output_dir=output,
            blender=Path("/Applications/Blender.app/Contents/MacOS/Blender"),
            runner=fake_runner,
        )
        self.assertEqual(result, output / "house_master.blend")
        self.assertTrue((output / "plan-review.svg").exists())
        self.assertTrue((output / "quality-report.json").exists())
        self.assertEqual(calls[0][0], "/Applications/Blender.app/Contents/MacOS/Blender")
        self.assertTrue(any(str(item).endswith("blender/build_scene.py") for item in calls[0]))
```

- [ ] **Step 2: Run the focused test and verify orchestration is missing**

Run: `PYTHONPATH=src python3 -m unittest tests.test_cli.CliSmokeTest.test_build_logical_writes_non_blender_artifacts_and_invokes_blender -v`

Expected: FAIL because `build_logical_project` is not defined.

- [ ] **Step 3: Implement orchestration and exit behavior**

`build_logical_project()` must:

1. derive the repository root from `cli.py`, load `manifest.json`, and verify every repo-relative immutable source asset before reading the annotation;
2. load `plan-annotation.json`;
3. build, validate, and atomically save `room.json`;
4. create the output directory;
5. write `plan-review.svg` and `quality-report.json`;
6. invoke Blender with `subprocess.run(command, check=True)` through the injected runner;
7. verify that both `.blend` and `.glb` files exist after the runner returns;
8. return the `.blend` path.

Map `ValidationError` to exit code 2 and failed external commands to exit code 3, with concise stderr messages. Do not catch unexpected exceptions.

- [ ] **Step 4: Run all unit and Blender acceptance tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m astra_house.cli build-logical --project projects/dorm-right-bedroom --output build/dorm-right-bedroom --blender /Applications/Blender.app/Contents/MacOS/Blender
/Applications/Blender.app/Contents/MacOS/Blender --background build/dorm-right-bedroom/house_master.blend --python tests/blender/assert_scene.py
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python tests/blender/assert_glb.py -- build/dorm-right-bedroom/house.glb
```

Expected: all unit tests pass, the CLI exits 0, and both Blender assertions exit 0.

- [ ] **Step 5: Document the exact first-room workflow**

Update `README.md` with:

- Python 3.11+ and Blender 5.2.2 LTS prerequisites;
- the one `build-logical` command above;
- artifact descriptions for `room.json`, `plan-review.svg`, `quality-report.json`, `house_master.blend`, and `house.glb`;
- the review rule: fix plan-space facts in `plan-annotation.json`, fix approved metric overrides in `room.json`, and never hand-edit generated walls as the source of truth;
- the explicit statement that photo reconstruction and appearance are outside this first plan.

- [ ] **Step 6: Run final verification and inspect repository state**

Run:

```bash
git diff --check
PYTHONPATH=src python3 -m unittest discover -s tests -v
git status --short
```

Expected: no whitespace errors, all tests pass, and only Task 9 source/documentation changes are uncommitted; `build/` does not appear.

- [ ] **Step 7: Commit the end-to-end logical MVP**

```bash
git add README.md src/astra_house/cli.py tests/test_cli.py
git commit -m "feat: complete logical room MVP workflow"
```

## Final Acceptance Checklist

- `projects/dorm-right-bedroom/room.json` validates and records trusted, confirmed, provisional, and assumed sources separately.
- `build/dorm-right-bedroom/plan-review.svg` visibly matches the supplied floor plan after human inspection.
- `build/dorm-right-bedroom/house_master.blend` opens with all six named collections and an editable L-shaped room.
- `build/dorm-right-bedroom/house.glb` imports into a factory Blender scene and retains expected object names.
- `build/dorm-right-bedroom/quality-report.json` exposes the bed-derived scale and assumed opening heights as warnings.
- The full standard-library test suite and both Blender read-back scripts exit successfully.
- No photo, LiDAR, dense reconstruction, generated texture, or Splatting dependency is introduced in this subproject.
