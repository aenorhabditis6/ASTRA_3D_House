# Interactive Capture Guide Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the printable 48-shot dorm guide with one self-contained, map-first field workflow that supports the reviewed `lite-24` and `standard-48` routes, validates their geometry before release, preserves standard-route semantics exactly, and records auditable manual progress without storing photographs.

**Architecture:** Schema `2.0` keeps stations, optics, anchors, modes, passes, groups, shots, and optional coverage review in trusted JSON. Python validates source facts, computes deterministic coverage geometry and mode hashes, and atomically emits the same three artifacts. A server-rendered static guide contains all 72 instructions; embedded framework-free JavaScript enhances it with an event-sourced controller, storage resilience, live map state, and progress export. Browser tests exercise the generated artifact rather than a separate mock application.

**Tech Stack:** Python 3.11+ standard library, immutable dataclasses, `unittest`, JSON, HTML/CSS/SVG, framework-free ES2022 JavaScript, Node.js only for development, Playwright test runner and pinned Chromium only for browser verification

**Spec:** `docs/superpowers/specs/2026-09-21-interactive-capture-guide-design.md`

## Global Constraints

- Keep `astra-house build-capture-pack --project projects/dorm-right-bedroom --output build/dorm-right-bedroom/capture-pack` stable and Blender-free.
- Generate exactly `index.html`, `capture-intake.json`, and `capture-pack-report.json`; source assets may be separate files but must be inlined into `index.html`.
- Add no Python runtime dependency and no browser runtime network request, service worker, external font, analytics, framework, or CDN resource.
- Preserve every ordered schema-`1.0` standard tuple `(shot_id, standing_point_m, pitch, target_ids, instruction)` exactly in `standard-48`.
- Keep `bath-door-south` on `wall-02`; keep `wall-03` opening-free.
- Treat station confirmation as manual, visit-local state. Never claim automatic position, shutter observation, camera verification, or photo existence.
- Store metadata only. Never read, store, transform, rename, or upload image bytes.
- Keep `lite-24` at 24 shots/14 groups and `standard-48` at 48 shots/28 groups. The domain and renderer must still accept a third fixed-count mode without branching on these IDs.
- Quantize all derived coordinates and lengths to `1e-4 m` and angles to `0.01°` before threshold comparison, hashing, reporting, or embedding.
- A geometric error stops generation before artifact replacement. Unreviewed or stale warning codes produce a deterministic draft report. Only an exact mode hash and warning-code match is publishable.
- The first deliverable is a pilot implementation. Current Chrome on the Xiaomi over stable HTTPS and Mac-LAN HTTP still require the real-device matrix before field release.
- Keep both doors closed for each current route. If a door state must change, restart under a new capture ID.

## Review Focus

- The migration fixture must prove all 48 standard shots retain exact values and order after normalization into stations and groups.
- Concave-room line of sight, first boundary hits, usable FOV, target membership, station clearance, seam coverage, adjacent shared spans, wall redundancy, and anchor baselines must be computed from geometry rather than prose.
- The event reducer must stop at the longest valid prefix, keep raw invalid suffixes exportable, make undo a strict backward compensation stack, emit no event for a no-op, and never restore in-memory station confirmation after reload.
- Mode hashes must isolate each selected mode and exclude `coverage_review`; storage failures/stale hashes must preserve discoverable raw work, and export must degrade through Blob, Clipboard, `execCommand('copy')`, then selected manual text.
- Static content must survive disabled/failed JavaScript and hostile text without injection; at desktop, `390 × 844`, and `320 × 800`, it must have no horizontal overflow and nearby SVG markers must remain reachable through native station buttons.

## File and Responsibility Map

```text
projects/dorm-right-bedroom/capture-plan.json
    Reviewed schema-2.0 stations, modes, explicit aim/framing points, anchors,
    optics, and optional coverage-review acknowledgements.

tests/fixtures/dorm-right-bedroom-capture-plan-v1.json
    Frozen pre-migration source used only to prove standard-route equivalence.

src/astra_house/capture.py
    Immutable schema-2.0 parsing, identifier scopes, structural validation,
    measurement/anchor validation, and normalized iteration helpers.

src/astra_house/capture_geometry.py
    Quantization, concave-polygon visibility, target geometry, FOV analysis,
    overlap/seam/anchor diagnostics, mode hashes, and report-ready values.

src/astra_house/capture_pack.py
    Input coordination, hashes, intake/report contracts, publishability state,
    deterministic serialization, and atomic three-file output.

src/astra_house/capture_web.py
    Static semantic HTML and SVG composition plus safe JSON/CSS/JS embedding.

src/astra_house/assets/capture-guide.css
    Responsive, print, focus, state, no-script, and enhanced-layout styling.

src/astra_house/assets/capture-guide.js
    EventReducer, StateStore, CaptureController, MapView, TaskView, and
    ProgressExport. No mode-specific branches and no network operations.

src/astra_house/cli.py
    Stable command; additionally loads measurements for anchor validation.

pyproject.toml
    Includes CSS and JavaScript source assets in installed packages.

tests/test_capture.py
    Schema, project invariants, migration equivalence, and extension tests.

tests/test_capture_geometry.py
    Low-level geometry and end-to-end route coverage diagnostics.

tests/test_capture_pack.py
    Deterministic three-file contract, hashes, static DOM, embedding, and
    fail-before-replacement behavior.

tests/test_capture_cli.py
    Stable CLI, manifest boundary, measurement loading, and draft status.

package.json / package-lock.json / playwright.config.mjs
    Development-only, exact Playwright toolchain and browser-test commands.

tests/browser/capture-guide.spec.mjs
    Generated-page interaction, persistence, resilience, accessibility,
    responsive layout, third-mode, and export tests.

tests/browser/capture-guide.spec.mjs-snapshots/
    Baselines from the pinned Chromium revision and explicit font stack.

docs/field-tests/xiaomi-capture-guide-pilot.md
    Real-device matrix and evidence record; unchecked until physically run.

README.md
    Build, stable-origin serving, capture, export, and pilot-release guidance.
```

No second plan is needed: these parts share one schema and one generated artifact, and each later task depends on the contracts established by the earlier tasks.

---

### Task 1: Freeze schema `1.0` and introduce the schema `2.0` domain

**Files:**
- Create: `tests/fixtures/dorm-right-bedroom-capture-plan-v1.json`
- Modify: `src/astra_house/capture.py`
- Modify: `tests/test_capture.py`

**Interfaces:**

```python
@dataclass(frozen=True)
class DeviceProfile:
    make: str
    model: str
    lens: str
    orientation: str
    aspect_ratio: str
    file_format: str
    arcore_status: str
    equivalent_focal_length_mm: float
    horizontal_fov_deg: float
    vertical_fov_deg: float
    fov_source: str
    fov_confidence: float
    camera_height_m: float
    camera_height_tolerance_m: float
    coverage_margin_deg: float

@dataclass(frozen=True)
class ScaleAnchor:
    id: str
    target_id: str
    measurement_ids: tuple[str, ...]

@dataclass(frozen=True)
class CaptureStation:
    id: str
    number: int
    standing_point_m: Vec2
    label: str

@dataclass(frozen=True)
class CaptureShot:
    id: str
    aim_point_m: Vec2
    framing_points_m: tuple[Vec3, ...]
    pitch: str
    pitch_deg: float
    target_ids: tuple[str, ...]
    instruction: str

@dataclass(frozen=True)
class CaptureGroup:
    id: str
    title: str
    purpose: str
    station_id: str
    next_hint: str | None
    shots: tuple[CaptureShot, ...]

@dataclass(frozen=True)
class CapturePass:
    id: str
    title: str
    purpose: str
    groups: tuple[CaptureGroup, ...]

@dataclass(frozen=True)
class CaptureMode:
    id: str
    title: str
    description: str
    expected_image_count: int
    risk_note: str
    required_scale_anchor_ids: tuple[str, ...]
    passes: tuple[CapturePass, ...]

@dataclass(frozen=True)
class CoverageReview:
    mode_id: str
    mode_plan_sha256: str
    warning_codes: tuple[str, ...]
    reviewer: str
    reviewed_at: str

@dataclass(frozen=True)
class CapturePlan:
    schema_version: str
    room_id: str
    capture_id: str
    device_profile: DeviceProfile
    wall_review: tuple[WallReview, ...]
    scale_anchors: tuple[ScaleAnchor, ...]
    coverage_review: tuple[CoverageReview, ...]
    stations: tuple[CaptureStation, ...]
    modes: tuple[CaptureMode, ...]

    # Public signatures implemented in Step 4:
    # from_dict(cls, data: dict[str, Any]) -> CapturePlan
    # validate(self, room: RoomModel, measurements: MeasurementSet) -> None
    # station(self, station_id: str) -> CaptureStation
    # mode(self, mode_id: str) -> CaptureMode
```

- [ ] **Step 1: Freeze the current source before changing it**

Copy the existing committed `capture-plan.json` byte-for-byte to the fixture and add a test that reads it as raw JSON. The fixture remains schema `1.0`; production parsing intentionally rejects it after migration.

```bash
mkdir -p tests/fixtures
cp projects/dorm-right-bedroom/capture-plan.json tests/fixtures/dorm-right-bedroom-capture-plan-v1.json
cmp projects/dorm-right-bedroom/capture-plan.json tests/fixtures/dorm-right-bedroom-capture-plan-v1.json
```

- [ ] **Step 2: Write failing schema-`2.0` parser and scope tests**

Replace the synthetic schema-`1.0` helper in `tests/test_capture.py` with `valid_capture_data_v2()`. It has two stations and one arbitrary mode so the library test does not hard-code project mode IDs. Assert:

```python
MEASUREMENTS = Path("projects/dorm-right-bedroom/measurements.json")

def load_measurements(path: Path) -> MeasurementSet:
    return MeasurementSet.from_dict(json.loads(path.read_text(encoding="utf-8")))

def valid_capture_data_v2() -> dict[str, object]:
    return {
        "schema_version": "2.0",
        "room_id": "dorm-right-bedroom",
        "capture_id": "domain-test",
        "device_profile": {
            "make": "Xiaomi", "model": "Xiaomi 17 Ultra",
            "lens": "1x Leica 23 mm main", "orientation": "landscape",
            "aspect_ratio": "4:3", "file_format": "JPG",
            "arcore_status": "unverified_optional",
            "equivalent_focal_length_mm": 23.0,
            "horizontal_fov_deg": 70.0, "vertical_fov_deg": 55.0,
            "fov_source": "test fixture", "fov_confidence": 0.5,
            "camera_height_m": 1.45, "camera_height_tolerance_m": 0.10,
            "coverage_margin_deg": 5.0,
        },
        "wall_review": {
            "wall-00": {"role": "east", "opening_ids": ["window-west", "window-east"]},
            "wall-01": {"role": "south", "opening_ids": []},
            "wall-02": {"role": "bath", "opening_ids": ["bath-door-south"]},
            "wall-03": {"role": "return", "opening_ids": []},
            "wall-04": {"role": "entry", "opening_ids": ["entry-door"]},
            "wall-05": {"role": "north", "opening_ids": []},
        },
        "scale_anchors": [
            {"id": "window-west", "target_id": "window-west", "measurement_ids": ["window-west-width"]}
        ],
        "stations": [
            {"id": "S01", "number": 1, "standing_point_m": [2.0, 2.0], "label": "first"},
            {"id": "S02", "number": 2, "standing_point_m": [3.0, 2.0], "label": "second"},
        ],
        "modes": [{
            "id": "test-2", "title": "Test", "description": "Generic mode",
            "expected_image_count": 2, "risk_note": "Fixture only",
            "required_scale_anchor_ids": ["window-west"],
            "passes": [{
                "id": "P", "title": "Pass", "purpose": "Domain fixture",
                "groups": [{
                    "id": "G01", "title": "Group", "purpose": "Two views",
                    "station_id": "S01", "next_hint": None,
                    "shots": [
                        {
                            "id": "T01", "aim_point_m": [1.425, 4.2266],
                            "framing_points_m": [[0.79, 4.2266, 1.66], [2.06, 4.2266, 1.66]],
                            "pitch": "level", "pitch_deg": 0.0,
                            "target_ids": ["wall-00", "window-west"],
                            "instruction": "Frame the west window and surrounding east wall."
                        },
                        {
                            "id": "T02", "aim_point_m": [0.0, 2.0],
                            "framing_points_m": [[0.0, 2.0, 1.45]],
                            "pitch": "level", "pitch_deg": 0.0,
                            "target_ids": ["wall-05"],
                            "instruction": "Frame the north wall."
                        },
                    ],
                }],
            }],
        }],
    }

plan = CapturePlan.from_dict(valid_capture_data_v2())
plan.validate(load_room(ROOM), load_measurements(MEASUREMENTS))
self.assertEqual(plan.station("S01").number, 1)
self.assertEqual(plan.mode("test-2").shots[0].aim_point_m, Vec2(1.425, 4.2266))
```

Add individual failures for schema `1.0`, duplicate station IDs/numbers, duplicate mode IDs, duplicate pass/group IDs within a mode, globally duplicate shot IDs, missing station references, unknown targets, an empty group, count mismatch, invalid pitch category/range, an aim point closer than `0.50 m`, an aim point outside the floor, and a station on the boundary or in the concave notch.

```python
def test_rejects_duplicate_station_number(self) -> None:
    data = valid_capture_data_v2()
    data["stations"][1]["number"] = 1
    with self.assertRaisesRegex(ValidationError, "duplicate station number 1"):
        CapturePlan.from_dict(data).validate(
            load_room(ROOM), load_measurements(MEASUREMENTS)
        )

def test_rejects_unknown_group_station(self) -> None:
    data = valid_capture_data_v2()
    data["modes"][0]["passes"][0]["groups"][0]["station_id"] = "S99"
    with self.assertRaisesRegex(ValidationError, "unknown station 'S99'"):
        CapturePlan.from_dict(data).validate(
            load_room(ROOM), load_measurements(MEASUREMENTS)
        )

def test_rejects_aim_point_too_close(self) -> None:
    data = valid_capture_data_v2()
    data["modes"][0]["passes"][0]["groups"][0]["shots"][0]["aim_point_m"] = [2.1, 2.0]
    with self.assertRaisesRegex(ValidationError, "at least 0.50 m"):
        CapturePlan.from_dict(data).validate(
            load_room(ROOM), load_measurements(MEASUREMENTS)
        )

def test_accepts_a_third_fixed_count_mode_without_known_id_branch(self) -> None:
    data = valid_capture_data_v2()
    third = copy.deepcopy(data["modes"][0])
    third["id"] = "production-fixture"
    third["passes"][0]["id"] = "P3"
    third["passes"][0]["groups"][0]["id"] = "G3"
    for shot in third["passes"][0]["groups"][0]["shots"]:
        shot["id"] = f"P3-{shot['id']}"
    data["modes"].append(third)
    plan = CapturePlan.from_dict(data)
    plan.validate(load_room(ROOM), load_measurements(MEASUREMENTS))
    self.assertEqual(plan.mode("production-fixture").expected_image_count, 2)
```

- [ ] **Step 3: Run the focused tests and verify RED**

```bash
PYTHONPATH=src python3 -m unittest tests.test_capture -v
```

Expected: schema `2.0` fields are not accepted and `CapturePlan.validate` has the old signature.

- [ ] **Step 4: Implement the immutable domain and general validation**

Use one source of truth for station coordinates. Add flattening properties without special-casing mode IDs:

```python
@property
def shots(self) -> tuple[CaptureShot, ...]:
    return tuple(
        shot
        for capture_pass in self.passes
        for group in capture_pass.groups
        for shot in group.shots
    )

@property
def groups(self) -> tuple[CaptureGroup, ...]:
    return tuple(group for capture_pass in self.passes for group in capture_pass.groups)
```

Validate pitch categories with these initial numeric ranges: `level` from `-15°` through `+10°`, `up` from `+15°` through `+45°`, and `down` from `-45°` through `-20°`. Require finite optics, `0 < margin × 2 < horizontal_fov < 180`, `0 < vertical_fov < 180`, positive camera height/tolerance, and confidence in `[0, 1]`. Keep wall/opening ownership validation, including the explicit bath-door regression.

```python
PITCH_RANGES = {
    "level": (-15.0, 10.0),
    "up": (15.0, 45.0),
    "down": (-45.0, -20.0),
}

def _validate_pitch(shot: CaptureShot) -> None:
    bounds = PITCH_RANGES.get(shot.pitch)
    if bounds is None:
        raise ValidationError(
            f"shot {shot.id!r} has unsupported pitch {shot.pitch!r}"
        )
    if not math.isfinite(shot.pitch_deg) or not bounds[0] <= shot.pitch_deg <= bounds[1]:
        raise ValidationError(
            f"shot {shot.id!r} pitch_deg {shot.pitch_deg!r} disagrees with {shot.pitch!r}"
        )
```

Parse `coverage_review` as an optional object keyed by mode ID:

```json
{
  "coverage_review": {
    "lite-24": {
      "mode_plan_sha256": "0000000000000000000000000000000000000000000000000000000000000000",
      "warning_codes": ["W_WALL_REDUNDANCY:wall-03"],
      "reviewer": "ASTRA plan-author preflight",
      "reviewed_at": "2026-09-21T20:00:00Z"
    }
  }
}
```

For each scale anchor, resolve every named `MeasurementRecord` and require its `target_id` to equal the anchor target, `application == "exact_override"`, and positive finite value.

- [ ] **Step 5: Run focused tests and verify GREEN**

```bash
PYTHONPATH=src python3 -m unittest tests.test_capture -v
```

Expected: all domain tests pass while the project-data test is temporarily skipped with the exact reason `schema-2 project fixture arrives in Task 2`.

- [ ] **Step 6: Commit Task 1**

```bash
git add src/astra_house/capture.py tests/test_capture.py tests/fixtures/dorm-right-bedroom-capture-plan-v1.json
git commit -m "refactor: define multi-mode capture domain"
```

---

### Task 2: Replace the project plan with reviewed two-mode data

**Files:**
- Modify: `projects/dorm-right-bedroom/capture-plan.json`
- Modify: `tests/test_capture.py`

**Interfaces:**
- Consumes the Task 1 schema, current `room.json`, `measurements.json`, and frozen schema-`1.0` fixture.
- Produces one reviewed schema-`2.0` source plan with 8 stations, 2 modes, 7 scale anchors, 42 groups, and 72 globally unique shots.

- [ ] **Step 1: Add failing project invariant and migration tests**

Define the legacy comparison tuple exactly:

```python
def legacy_tuple(shot: dict[str, object]) -> tuple[object, ...]:
    return (
        shot["id"],
        tuple(shot["standing_point_m"]),
        shot["pitch"],
        tuple(shot["target_ids"]),
        shot["instruction"],
    )

def normalized_tuple(plan: CapturePlan, group: CaptureGroup, shot: CaptureShot) -> tuple[object, ...]:
    station = plan.station(group.station_id)
    return (
        shot.id,
        tuple(station.standing_point_m.to_list()),
        shot.pitch,
        tuple(shot.target_ids),
        shot.instruction,
    )
```

Flatten standard groups in pass/group/shot order and compare the 48 resulting values to the frozen fixture. Assert mode order `("lite-24", "standard-48")`, counts `(24, 48)`, group counts `(14, 28)`, the exact pass distribution, all station coordinates, all pitch values, and the seven anchor mappings.

- [ ] **Step 2: Run the project test and verify RED**

```bash
PYTHONPATH=src python3 -m unittest tests.test_capture.CapturePlanTest.test_project_plan_v2_invariants -v
```

Expected: the committed project plan still reports unsupported schema `1.0`.

- [ ] **Step 3: Write the shared top-level data**

Set schema `2.0`, retain the capture identity and reviewed Xiaomi strings, and add:

```json
{
  "equivalent_focal_length_mm": 23.0,
  "horizontal_fov_deg": 70.0,
  "vertical_fov_deg": 55.0,
  "fov_source": "provisional conservative Xiaomi 17 Ultra 4:3 landscape estimate",
  "fov_confidence": 0.5,
  "camera_height_m": 1.45,
  "camera_height_tolerance_m": 0.10,
  "coverage_margin_deg": 5.0
}
```

Keep the current six wall-review records. Add exact anchors:

```text
window-west       -> window-west-width
window-east       -> window-east-width
entry-door        -> entry-door-width
bath-door-south   -> bath-door-width
bed-full          -> bed-length, bed-width
desk              -> desk-width
closet            -> closet-depth
```

Add S01–S08 in numeric order using `[1.35,1.65]`, `[2.15,1.55]`, `[3.10,1.45]`, `[3.65,1.80]`, `[2.55,2.10]`, `[2.20,2.80]`, `[1.55,2.75]`, and `[1.10,2.10]`. Their labels are respectively `just inside the entry area`, `inner north-side route point`, `bathroom-door/closet approach`, `far side beside the bed zone`, `central crossing point`, `window side near the bed`, `window side near the desk`, and `desk/entry-side return point`.

- [ ] **Step 4: Normalize `standard-48` without semantic changes**

Create the 28 groups specified by the approved design. Pass A groups `STD-A01`–`STD-A08` contain each old L/C/R triplet at S01–S08. Pass B groups are `STD-B01@S01`, `STD-B02@S03`, `STD-B03@S05`, and `STD-B04@S07`. Pass C uses one-shot groups `STD-C01A`, `STD-C01B`, through `STD-C04A`, `STD-C04B` at the station matching the frozen standing point. Pass D uses one-shot groups `STD-D01`–`STD-D08` at the matching station. Preserve every frozen ID, pitch, target list, instruction, and order. Assign level/up/down numeric pitches `0/+30/-35`.

```text
A: STD-A01@S01[A01-L,A01-C,A01-R]
   STD-A02@S02[A02-L,A02-C,A02-R]
   STD-A03@S03[A03-L,A03-C,A03-R]
   STD-A04@S04[A04-L,A04-C,A04-R]
   STD-A05@S05[A05-L,A05-C,A05-R]
   STD-A06@S06[A06-L,A06-C,A06-R]
   STD-A07@S07[A07-L,A07-C,A07-R]
   STD-A08@S08[A08-L,A08-C,A08-R]
B: STD-B01@S01[B01-U,B01-D] STD-B02@S03[B02-U,B02-D]
   STD-B03@S05[B03-U,B03-D] STD-B04@S07[B04-U,B04-D]
C: STD-C01A@S07[C01-A] STD-C01B@S08[C01-B]
   STD-C02A@S04[C02-A] STD-C02B@S05[C02-B]
   STD-C03A@S03[C03-A] STD-C03B@S04[C03-B]
   STD-C04A@S01[C04-A] STD-C04B@S02[C04-B]
D: STD-D01@S07[D01] STD-D02@S06[D02] STD-D03@S05[D03] STD-D04@S01[D04]
   STD-D05@S02[D05] STD-D06@S03[D06] STD-D07@S04[D07] STD-D08@S06[D08]
```

- [ ] **Step 5: Add `lite-24` in the reviewed route order**

Create passes `L-STRUCTURE`, `L-VERTICAL`, and `L-ANCHORS`. Use two shots in each L01–L10 and one shot in each L11–L14. Level groups use the approved pairs:

```text
L01 S01: wall-04+wall-05 | wall-05+wall-00
L02 S02: wall-05+wall-00 | wall-00+wall-01
L03 S03: wall-03+wall-02 | wall-02+wall-01
L04 S04: wall-02+wall-01 | wall-01+wall-00
L05 S05: wall-05+wall-00 | wall-00+wall-01
L06 S06: wall-05+wall-00 | wall-00+wall-01
L07 S07: wall-05+wall-00 | wall-00+wall-01
L08 S08: wall-04+wall-05 | wall-05+wall-00
```

Add deliberately framed anchor IDs to the level views at the required stations: windows S05/S07, entry S01/S02, bathroom door and closet S03/S04, bed S04/S05, desk S07/S08. Use `-10°` for lightweight level shots, `+25°/-35°` for L09/L10, then L11 windows at S06, L12 bed at S06, L13 bath/closet at S04, and L14 entry at S02.

- [ ] **Step 6: Store explicit aim and framing geometry**

For every shot, commit numeric `aim_point_m` and ordered 3D `framing_points_m`; browser code must not derive either. Construct candidates from these exact rules, round source coordinates to four decimal places, inspect the resulting Task 3 diagnostic overlay, and adjust only the committed JSON values:

- wall centers and corner-bisector points use wall spans from `room.json` at camera-height Z;
- opening width shots include both jamb points at the opening vertical midpoint; a full-height instruction also includes sill and head points;
- proxy dimension shots include the two measured-dimension extremes at proxy center height;
- multi-target context shots aim along the angular bisector of their primary framing-point bearings, with a point at least `0.50 m` from the station and inside/on the floor;
- each declared target contributes at least one framing point; full-width language contributes both horizontal extremes;
- aim points are horizontal-bearing controls only; Z exists only in framing points.

Use these geometry helpers while preparing the committed values, then paste their numeric results into JSON rather than calling them in the browser:

```python
def point_on_wall(wall: Wall, offset_m: float, z_m: float) -> Vec3:
    ratio = offset_m / wall.length_m
    return Vec3(
        wall.start.x + (wall.end.x - wall.start.x) * ratio,
        wall.start.y + (wall.end.y - wall.start.y) * ratio,
        z_m,
    )

def opening_width_points(opening: Opening, wall: Wall) -> tuple[Vec3, Vec3]:
    z_m = opening.sill_m + opening.height_m / 2.0
    return (
        point_on_wall(wall, opening.offset_m, z_m),
        point_on_wall(wall, opening.offset_m + opening.width_m, z_m),
    )
```

Do not add `coverage_review` yet. The initial route is intentionally a draft until Task 10 records the exact preflight result.

- [ ] **Step 7: Run migration and project tests**

```bash
PYTHONPATH=src python3 -m unittest tests.test_capture -v
```

Expected: schema `2.0`, exact counts and assignments pass; all 48 normalized standard tuples equal the frozen source.

- [ ] **Step 8: Commit Task 2**

```bash
git add projects/dorm-right-bedroom/capture-plan.json tests/test_capture.py
git commit -m "feat: add reviewed lite and standard capture modes"
```

---

### Task 3: Implement deterministic coverage geometry and release diagnostics

**Files:**
- Create: `src/astra_house/capture_geometry.py`
- Create: `tests/test_capture_geometry.py`
- Modify: `src/astra_house/capture.py`

**Interfaces:**

```python
@dataclass(frozen=True)
class CoverageIssue:
    code: str
    severity: str
    mode_id: str
    subject_id: str
    message: str

@dataclass(frozen=True)
class ShotCoverage:
    shot_id: str
    station_id: str
    bearing_deg: float
    boundary_hit_m: Vec2
    boundary_distance_m: float
    usable_horizontal_fov_deg: float
    horizontal_span_deg: float
    vertical_interval_deg: tuple[float, float]
    visible_target_ids: tuple[str, ...]
    cone_polygon_m: tuple[Vec2, ...]

@dataclass(frozen=True)
class ModeCoverage:
    mode_id: str
    mode_plan_sha256: str
    shots: tuple[ShotCoverage, ...]
    adjacent_shared_spans_m: tuple[tuple[str, str, float], ...]
    wall_station_baselines_m: tuple[tuple[str, int, float], ...]
    anchor_station_baselines_m: tuple[tuple[str, int, float], ...]
    issues: tuple[CoverageIssue, ...]

# Public signatures implemented in Steps 4–6:
# quantize_m(value: float) -> float
# quantize_deg(value: float) -> float
# segment_inside_polygon(start: Vec2, end: Vec2, polygon: tuple[Vec2, ...]) -> bool
# mode_plan_sha256(plan: CapturePlan, mode: CaptureMode, room_sha256: str) -> str
# analyze_capture_plan(plan: CapturePlan, room: RoomModel, room_sha256: str) -> tuple[ModeCoverage, ...]
# raise_for_coverage_errors(coverage: tuple[ModeCoverage, ...]) -> None
```

- [ ] **Step 1: Write RED tests for geometry primitives**

Use small convex and concave polygons with fixed expected results. Cover strict point containment with `0.01 m` tolerance, a segment crossing the L-shaped notch, a first-boundary ray, left/right bearing wrap at ±180°, a target behind the aim direction, and quantization edges. Pin:

```python
def test_quantizes_derived_geometry_half_up(self) -> None:
    self.assertEqual(quantize_m(1.23456), 1.2346)
    self.assertEqual(quantize_deg(-12.345), -12.35)

def test_rejects_segment_that_crosses_concave_notch(self) -> None:
    polygon = (
        Vec2(0, 0), Vec2(4, 0), Vec2(4, 4),
        Vec2(2, 4), Vec2(2, 2), Vec2(0, 2),
    )
    self.assertFalse(segment_inside_polygon(Vec2(1, 1), Vec2(3, 3), polygon))
```

Use `Decimal(str(value)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)` for metre values and `Decimal("0.01")` for angles; never rely on binary `round()` at threshold boundaries.

- [ ] **Step 2: Write RED tests for target membership and route analysis**

Assert opening points lie on their owning wall rectangle, proxy points lie on an oriented box face/edge, and wall points lie on their segment within `0.01 m`. Add fixtures that separately trigger stable codes for:

```text
E_LOS_OUTSIDE_ROOM
E_STATION_BLOCKED
E_ANCHOR_BASELINE
E_HORIZONTAL_FOV
E_VERTICAL_FOV
E_TARGET_BEHIND_BEARING
W_PAIRED_BEARING_GAP
W_ADJACENT_SHARED_SPAN
W_STATION_CLEARANCE
W_SHORT_BOUNDARY_RAY
W_VERTICAL_OVERLAP
W_FLOOR_SEAM_GAP
W_WALL_REDUNDANCY
```

Assert `lite-24` reports `W_WALL_REDUNDANCY` for `wall-03`; assert both modes have zero coverage errors and every required anchor has two stations with at least `0.50 m` maximum baseline.

```python
def test_project_routes_have_no_geometry_errors(self) -> None:
    plan = CapturePlan.from_dict(json.loads(CAPTURE_PLAN.read_text(encoding="utf-8")))
    room = load_room(ROOM)
    measurements = MeasurementSet.from_dict(
        json.loads(MEASUREMENTS.read_text(encoding="utf-8"))
    )
    plan.validate(room, measurements)
    room_digest = hashlib.sha256(
        json.dumps(room.to_dict(), sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    coverage = analyze_capture_plan(plan, room, room_digest)
    errors = [issue for mode in coverage for issue in mode.issues if issue.severity == "error"]
    self.assertEqual(errors, [])
    lite = next(item for item in coverage if item.mode_id == "lite-24")
    self.assertIn(
        "W_WALL_REDUNDANCY:wall-03",
        {issue.code for issue in lite.issues},
    )
    self.assertTrue(
        all(count >= 2 and baseline >= 0.5 for _, count, baseline in lite.anchor_station_baselines_m)
    )
```

- [ ] **Step 3: Run coverage tests and verify RED**

```bash
PYTHONPATH=src python3 -m unittest tests.test_capture_geometry -v
```

Expected: `astra_house.capture_geometry` does not exist.

- [ ] **Step 4: Implement robust 2D visibility and FOV math**

For a segment-inside-polygon test, collect segment parameters at every polygon-edge intersection, include `0` and `1`, sort/deduplicate them, and test every open-interval midpoint as inside/on. This handles the concave notch without a bounding-box shortcut. Extend the normalized aim bearing until the nearest positive intersection with any floor edge.

Build each horizontal cone from the station, the two usable half-angle boundary rays, and their first room-boundary hits. The usable horizontal field is `horizontal_fov_deg - 2 * coverage_margin_deg`. A framing span is the smallest circular interval covering all point bearings relative to the shot bearing. Reject points with a relative angle outside half the usable field.

For vertical checks, compute `atan2(point.z - camera_height_m, horizontal_distance)` for each point. A point must lie inside `pitch_deg ± vertical_fov_deg/2`; height tolerance is tested at both camera-height extremes. Same-station vertical overlap is intersection length divided by the smaller angular interval.

```python
def quantize_m(value: float) -> float:
    return float(Decimal(str(value)).quantize(METER_QUANTUM, rounding=ROUND_HALF_UP))

def quantize_deg(value: float) -> float:
    return float(Decimal(str(value)).quantize(ANGLE_QUANTUM, rounding=ROUND_HALF_UP))

def relative_bearing_deg(origin: Vec2, aim: Vec2, point: Vec2) -> float:
    axis = math.degrees(math.atan2(aim.y - origin.y, aim.x - origin.x))
    bearing = math.degrees(math.atan2(point.y - origin.y, point.x - origin.x))
    return (bearing - axis + 180.0) % 360.0 - 180.0
```

- [ ] **Step 5: Implement analytic shared-span and seam checks**

For each wall and cone, create candidate along-wall parameters from wall endpoints and intersections with both cone rays. Classify each parameter interval by its midpoint using FOV and concave LOS. Intersect accepted intervals from adjacent route stations and sum their lengths. Use the same interval representation for floor-wall seam coverage. Ceiling seams are reported as advisory metrics, not release blockers.

Wall and anchor redundancy use distinct station IDs and maximum pairwise station distance, not shot count. Anchor validation counts an anchor only when it appears in `target_ids` and its framing points lie on that anchor geometry.

```python
def intersect_intervals(
    left: tuple[tuple[float, float], ...],
    right: tuple[tuple[float, float], ...],
) -> tuple[tuple[float, float], ...]:
    result: list[tuple[float, float]] = []
    for left_start, left_end in left:
        for right_start, right_end in right:
            start, end = max(left_start, right_start), min(left_end, right_end)
            if end > start:
                result.append((start, end))
    return tuple(result)
```

- [ ] **Step 6: Implement canonical mode hashing**

Hash a sorted-key, compact JSON bundle containing schema, room/capture IDs, device profile, wall review, scale anchors, the selected full mode, only stations referenced by that mode, and `room_model_sha256`. Exclude all `coverage_review` records. Serialize with `ensure_ascii=False`, separators `(',', ':')`, and UTF-8 before SHA-256.

Add a test that changes one standard instruction and proves only the standard hash changes; then change only reviewer/timestamp and prove neither mode hash changes:

```python
def test_mode_hash_isolated_from_other_modes_and_coverage_review(self) -> None:
    plan = CapturePlan.from_dict(json.loads(CAPTURE_PLAN.read_text(encoding="utf-8")))
    room = load_room(ROOM)
    room_digest = hashlib.sha256(
        json.dumps(room.to_dict(), sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    lite_before = mode_plan_sha256(plan, plan.mode("lite-24"), room_digest)
    standard_before = mode_plan_sha256(plan, plan.mode("standard-48"), room_digest)
    changed_data = json.loads(CAPTURE_PLAN.read_text(encoding="utf-8"))
    changed_data["modes"][1]["passes"][0]["groups"][0]["shots"][0]["instruction"] += " Recheck."
    changed = CapturePlan.from_dict(changed_data)
    self.assertEqual(lite_before, mode_plan_sha256(changed, changed.mode("lite-24"), room_digest))
    self.assertNotEqual(standard_before, mode_plan_sha256(changed, changed.mode("standard-48"), room_digest))
    changed_data["coverage_review"] = {
        "lite-24": {
            "mode_plan_sha256": lite_before,
            "warning_codes": [],
            "reviewer": "hash exclusion test",
            "reviewed_at": "2026-09-21T20:00:00Z"
        }
    }
    reviewed = CapturePlan.from_dict(changed_data)
    self.assertEqual(
        mode_plan_sha256(changed, changed.mode("lite-24"), room_digest),
        mode_plan_sha256(reviewed, reviewed.mode("lite-24"), room_digest),
    )
```

```python
payload = {
    "schema_version": plan.schema_version,
    "room_id": plan.room_id,
    "capture_id": plan.capture_id,
    "device_profile": asdict(plan.device_profile),
    "wall_review": [asdict(item) for item in plan.wall_review],
    "scale_anchors": [asdict(item) for item in plan.scale_anchors],
    "mode": asdict(mode),
    "stations": [asdict(plan.station(station_id)) for station_id in station_ids],
    "room_model_sha256": room_sha256,
}
encoded = json.dumps(
    payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")
).encode("utf-8")
return hashlib.sha256(encoded).hexdigest()
```

- [ ] **Step 7: Tune only reviewed source geometry until the project has no errors**

Run the project tests, read each issue's subject ID and metric, and adjust explicit aim/framing points in `capture-plan.json`. Do not weaken optics or thresholds to silence a route-data error. Warnings remain visible, including the intentional lightweight `wall-03` warning.

```bash
PYTHONPATH=src python3 -m unittest tests.test_capture_geometry -v
```

Expected: all primitive and route tests pass, both modes have zero errors, and warning codes are sorted and deterministic.

- [ ] **Step 8: Commit Task 3**

```bash
git add src/astra_house/capture.py src/astra_house/capture_geometry.py tests/test_capture_geometry.py projects/dorm-right-bedroom/capture-plan.json
git commit -m "feat: preflight capture coverage geometry"
```

---

### Task 4: Upgrade deterministic intake, report, and mode-hash packaging

**Files:**
- Modify: `src/astra_house/capture_pack.py`
- Modify: `src/astra_house/cli.py`
- Modify: `tests/test_capture_pack.py`
- Modify: `tests/test_capture_cli.py`

**Interfaces:**

```text
write_capture_pack(plan: CapturePlan, annotation: PlanAnnotation,
                   room: RoomModel, measurements: MeasurementSet,
                   source_plan_path: Path, output_dir: Path) -> Path
build_capture_intake(plan: CapturePlan,
                     coverage: tuple[ModeCoverage, ...]) -> dict[str, Any]
build_capture_report(plan: CapturePlan,
                     coverage: tuple[ModeCoverage, ...],
                     source_hashes: dict[str, str]) -> dict[str, Any]
```

- [ ] **Step 1: Write RED package-contract tests**

Assert exactly three files, schema `2.0`, all 72 IDs in intake, and mode-keyed ledgers. Pin each row to:

```json
{
  "assigned_shot_id": "L01-A",
  "pass_id": "L-STRUCTURE",
  "group_id": "L01",
  "station_id": "S01",
  "planned_order": 1,
  "source_filename": null,
  "sha256": null,
  "dimensions_px": null,
  "exif": {
    "date_time_original": null,
    "sub_sec_time_original": null,
    "offset_time_original": null,
    "orientation": null
  }
}
```

Assert the report contains generator/schema version `2.0`, `mode_counts`, per-mode pass/group/station counts, hashes, quantized shot/adjacency/anchor/wall diagnostics, sorted issues, and `draft` when coverage review is absent or stale. Add an exact review record in a test copy and assert `publishable` only when both hash and sorted code set match.

```python
def test_report_is_draft_without_current_coverage_review(self) -> None:
    with tempfile.TemporaryDirectory() as directory:
        write_capture_pack(
            self.plan, self.annotation, self.room, self.measurements,
            self.source_png, Path(directory),
        )
        report = json.loads(
            (Path(directory) / "capture-pack-report.json").read_text(encoding="utf-8")
        )
    self.assertEqual(report["status"], "draft")
    self.assertEqual(report["mode_counts"], {"lite-24": 24, "standard-48": 48})
    self.assertEqual(report["group_counts"], {"lite-24": 14, "standard-48": 28})
```

- [ ] **Step 2: Run package tests and verify RED**

```bash
PYTHONPATH=src python3 -m unittest tests.test_capture_pack tests.test_capture_cli -v
```

Expected: old report has one `shot_count`, old intake is flat, and CLI does not load measurements.

- [ ] **Step 3: Refactor package orchestration**

Bump `GENERATOR_VERSION` to `astra-house-capture-pack/2.0`. Validate plan/annotation/room/measurements and immutable PNG before rendering any bytes. Compute capture-plan, floorplan, room-model, and measurements hashes. Run coverage, reject errors, compute publishability, build all three byte payloads in memory, then atomically replace each named artifact. Preserve existing sentinels for any validation failure.

The report status rules are exact:

```text
publishable  every mode has a review with its current hash and exact warning codes
draft        at least one review is absent or stale and there are no geometry errors
```

Include `coverage_review_status` per mode as `current`, `missing`, `stale_hash`, or `stale_codes`.

```python
def _review_status(
    review: CoverageReview | None,
    coverage: ModeCoverage,
) -> str:
    if review is None:
        return "missing"
    if review.mode_plan_sha256 != coverage.mode_plan_sha256:
        return "stale_hash"
    expected_codes = tuple(sorted(
        issue.code for issue in coverage.issues if issue.severity == "warning"
    ))
    if tuple(sorted(review.warning_codes)) != expected_codes:
        return "stale_codes"
    return "current"

statuses = {
    mode.mode_id: _review_status(review_by_mode.get(mode.mode_id), mode)
    for mode in coverage
}
report["status"] = (
    "publishable" if all(value == "current" for value in statuses.values()) else "draft"
)
```

- [ ] **Step 4: Load measurements through the stable CLI**

In `build_capture_project`, load `measurements.json` with `MeasurementSet.from_dict`, pass it to `write_capture_pack`, and leave public arguments unchanged. Add a CLI regression showing an anchor that references an audit-only or wrong-target measurement exits with code `2` before output replacement.

```python
measurements_path = project_dir / "measurements.json"
measurements = MeasurementSet.from_dict(
    _load_json(measurements_path, "measurements")
)
return write_capture_pack(
    plan,
    annotation,
    room,
    measurements,
    source_plan_path,
    output_dir,
)
```

- [ ] **Step 5: Run package and CLI tests and verify GREEN**

```bash
PYTHONPATH=src python3 -m unittest tests.test_capture_pack tests.test_capture_cli -v
```

Expected: all tests pass and repeated builds are byte-identical while source timestamps remain absent from generated artifacts.

- [ ] **Step 6: Commit Task 4**

```bash
git add src/astra_house/capture_pack.py src/astra_house/cli.py tests/test_capture_pack.py tests/test_capture_cli.py
git commit -m "feat: emit multi-mode capture handoff data"
```

---

### Task 5: Render the complete static and accessible guide

**Files:**
- Create: `src/astra_house/capture_web.py`
- Create: `src/astra_house/assets/capture-guide.css`
- Create: `src/astra_house/assets/capture-guide.js`
- Modify: `src/astra_house/capture_pack.py`
- Modify: `pyproject.toml`
- Modify: `tests/test_capture_pack.py`

**Interfaces:**

```text
render_capture_html(plan: CapturePlan, annotation: PlanAnnotation,
                    plan_image: bytes, coverage: tuple[ModeCoverage, ...],
                    report: dict[str, Any]) -> str
embedded_capture_data(plan: CapturePlan, annotation: PlanAnnotation,
                      coverage: tuple[ModeCoverage, ...],
                      report: dict[str, Any]) -> dict[str, Any]
```

- [ ] **Step 1: Write RED static-render tests**

Assert all 72 distinct shot IDs, both modes, all stations, instructions, targets, aim descriptions, warning codes, Xiaomi settings, closed-door rule, upload guidance, and mode hashes exist before JavaScript execution. Parse `#capture-data` as JSON and compare its mode/group/shot text with static DOM strings. Assert eight station markers plus per-shot ray/cone paths are embedded.

Add an instruction/note-shaped string containing `</script><img src=x onerror=alert(1)>` to a test copy. Assert static text is HTML-escaped, embedded JSON remains parseable, and no injected image element exists. Browser rendering must later assign operator notes with `textContent`, never `innerHTML`.

Reject network URLs in executable/resource attributes, external `<link>` elements, module imports, service-worker registration, and fetch/XHR code. Explanatory HTTPS prose and embedded data-image URLs are allowed.

```python
def test_html_has_no_runtime_network_dependency(self) -> None:
    html = self.build_pack_and_read_html()
    scrubbed = re.sub(r"data:image/[^;]+;base64,[A-Za-z0-9+/=]+", "", html)
    self.assertNotRegex(
        scrubbed,
        r'<(?:script|img|link)[^>]+(?:src|href)=["\'](?:https?:)?//',
    )
    for forbidden in ("fetch(", "XMLHttpRequest", "serviceWorker.register"):
        self.assertNotIn(forbidden, scrubbed)
```

- [ ] **Step 2: Run renderer tests and verify RED**

```bash
PYTHONPATH=src python3 -m unittest tests.test_capture_pack -v
```

Expected: the old single-mode monolith lacks schema-`2.0` data and both static ledgers.

- [ ] **Step 3: Implement semantic static HTML and safe embedding**

Render a mode chooser summary, a room SVG with station labels/rays/cones and diagnostic toggle content, one ordered static checklist per mode, wall review, camera checklist, warnings, persistence-origin warning text, and upload instructions. Use native headings, tables, buttons, labels, checkboxes, `textarea readonly`, `<dialog>` only with a non-dialog fallback, and `aria-live="polite"`.

Mark `standard-48` as recommended but leave both modes unselected until the user acts. State the coordinate/compass interpretation exactly: +X north-to-south, +Y west-to-east, `wall-00` east/double-window, `wall-01` south, `wall-05` north, and `wall-02`/`wall-04` west-facing; explain that both legacy-named windows are on `wall-00`. The camera checklist names 1× 23 mm, landscape 4:3 JPG, one unchanged Leica style, both doors closed, stable lights/curtains, and watermark/filter/AI-scene/HDR/flash/digital-zoom/Dynamic-Shot off.

Pass every server-rendered text node and attribute through `html.escape(..., quote=True)`. Browser updates use DOM construction plus `textContent`/`.value`; plan text, notes, stale-state text, and errors are never concatenated into `innerHTML`.

Serialize embedded JSON with `<`, `>`, `&`, U+2028, and U+2029 escaped so plan text cannot terminate the script element. Inline CSS and JavaScript by reading package assets with `importlib.resources.files("astra_house").joinpath("assets", name).read_text(encoding="utf-8")`. Configure:

```python
def _script_json(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return (
        encoded.replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )

def _asset_text(name: str) -> str:
    return resources.files("astra_house").joinpath("assets", name).read_text(
        encoding="utf-8"
    )
```

Initialization uses a failure-safe boundary; the test flag exists only to exercise that path:

```javascript
const readEmbeddedData = () => JSON.parse(
  document.getElementById("capture-data").textContent
);
const readIdentity = () => {
  const data = readEmbeddedData();
  return { room_id: data.room_id, capture_id: data.capture_id };
};

window.addEventListener("DOMContentLoaded", () => {
  try {
    if (window.__ASTRA_FORCE_INIT_ERROR__) throw new Error("forced initialization failure");
    const controller = new CaptureController(readEmbeddedData(), new StateStore(readIdentity()));
    controller.init();
    document.documentElement.classList.add("enhanced");
  } catch (error) {
    document.getElementById("enhancement-warning").textContent =
      `Interactive controls unavailable; use the complete static guide below. ${String(error)}`;
  }
});
```

```toml
[tool.setuptools.package-data]
astra_house = ["assets/*.css", "assets/*.js"]
```

- [ ] **Step 4: Add no-script, failure-safe, responsive, and print CSS**

Use an explicit deterministic stack `Arial, Helvetica, sans-serif`. Keep `.static-guide` visible by default. Only `.enhanced .static-guide` may collapse into its accessible details view after controller success. `noscript` explains manual checkboxes. Print hides interactive-only controls and shows empty checkbox glyphs. Every grid uses `minmax(0, 1fr)`, long hashes use `overflow-wrap:anywhere`, and SVG/button containers have `max-width:100%`.

```css
html { font-family: Arial, Helvetica, sans-serif; }
.static-guide { display: block; }
.interactive-guide { display: none; }
.enhanced .interactive-guide { display: block; }
.enhanced .static-guide[data-enhanced-collapse="true"] { display: none; }
.layout-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); }
.hash { overflow-wrap: anywhere; }
svg, button, textarea { max-width: 100%; }
@media (max-width: 640px) { .layout-grid { grid-template-columns: minmax(0, 1fr); } }
@media print { .interactive-only { display: none !important; } .static-guide { display: block !important; } }
```

- [ ] **Step 5: Run renderer tests and verify GREEN**

```bash
PYTHONPATH=src python3 -m unittest tests.test_capture_pack -v
```

Expected: deterministic self-contained HTML contains the complete static workflow and the exact embedded plan/report data.

- [ ] **Step 6: Commit Task 5**

```bash
git add src/astra_house/capture_web.py src/astra_house/assets/capture-guide.css src/astra_house/assets/capture-guide.js src/astra_house/capture_pack.py pyproject.toml tests/test_capture_pack.py
git commit -m "feat: render self-contained static capture guide"
```

---

### Task 6: Add the event reducer and capture controller

**Files:**
- Modify: `src/astra_house/assets/capture-guide.js`
- Create: `package.json`
- Create: `package-lock.json`
- Create: `playwright.config.mjs`
- Create: `tests/browser/capture-guide.spec.mjs`

**Interfaces:**

```javascript
/** @typedef {{
 * seq:number, t_ms:number, tz_offset_min:number, type:string,
 * room_id:string, capture_id:string, mode_id:string,
 * mode_plan_sha256:string, group_id?:string, station_id?:string,
 * shot_ids?:string[], method?:"shot"|"group"|"manual_station",
 * within_group_order?:"inferred", note?:string, undoes_seq?:number
 * }} CaptureEvent */

/** @typedef {{
 * shots:Record<string,{status:"pending"|"completed"|"skipped",note:string}>,
 * valid_events:CaptureEvent[], raw_events:unknown[], valid_prefix_length:number,
 * compensated_seqs:number[], warning:string|null
 * }} ReplayResult */
```

```text
EventReducer.replay(mode, rawEvents) -> ReplayResult
EventReducer.nextUndoTarget(validEvents) -> CaptureEvent | null
new CaptureController(data, store, clock = Date)
CaptureController.init() -> void
CaptureController.startMode(modeId) -> void
CaptureController.confirmStation(stationId) -> void
CaptureController.setShotCompleted(groupId, shotId, completed) -> void
CaptureController.completeGroup(groupId) -> void
CaptureController.skipShot(groupId, shotId, note) -> void
CaptureController.setNote(groupId, shotId, note) -> void
CaptureController.undoLastAction() -> void
CaptureController.selectStation(stationId) -> void
CaptureController.nextIncomplete() -> void
```

- [ ] **Step 1: Pin the development-only Playwright toolchain**

Run `npm install --save-dev --save-exact @playwright/test`, commit both package files, and configure one Chromium project, deterministic locale `zh-CN`, timezone `America/Los_Angeles`, reduced motion, light color scheme, and a Python `http.server` web server for `build/dorm-right-bedroom/capture-pack`. Set workers to `1` for snapshot stability.

```javascript
// playwright.config.mjs
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "tests/browser",
  workers: 1,
  fullyParallel: false,
  use: {
    ...devices["Desktop Chrome"],
    baseURL: "http://127.0.0.1:8765",
    locale: "zh-CN",
    timezoneId: "America/Los_Angeles",
    colorScheme: "light",
    reducedMotion: "reduce",
  },
  webServer: {
    command: "python3 -m http.server 8765 --directory build/dorm-right-bedroom/capture-pack",
    url: "http://127.0.0.1:8765/index.html",
    reuseExistingServer: false,
  },
});
```

- [ ] **Step 2: Write RED interaction tests**

Build the pack in test setup. Test explicit mode selection, one-time `capture_started`, station gating, confirmation retention across consecutive groups at the same station, confirmation loss after station change, shot completion, group completion with ordered shot IDs, reopen, skip/note, forward-then-wrap, direct station navigation without status mutation, completed-station reopening, and gap versus complete handoff.

Inspect exported events and require base identity plus:

```json
{
  "seq": 2,
  "t_ms": 1789981200000,
  "tz_offset_min": -420,
  "type": "station_confirmed",
  "room_id": "dorm-right-bedroom",
  "capture_id": "dorm-right-bedroom-diagnostic-01",
  "mode_id": "lite-24",
  "mode_plan_sha256": "0000000000000000000000000000000000000000000000000000000000000000",
  "group_id": "L01",
  "station_id": "S01",
  "method": "manual_station"
}
```

The JSON above fixes field shape; the test reads the current nonzero digest and checks it with `/^[0-9a-f]{64}$/`. Define the shared Playwright helpers in the same file:

```javascript
import { expect, test } from "@playwright/test";

async function startMode(page, modeId, url = "/index.html") {
  await page.goto(url);
  await page.getByRole("button", { name: new RegExp(modeId) }).click();
  await page.getByLabel("I checked the Xiaomi settings").check();
  await page.getByRole("button", { name: "Start route" }).click();
}

async function startAndConfirm(page, modeId, stationId, url = "/index.html") {
  await startMode(page, modeId, url);
  const number = Number(stationId.slice(1));
  await page.getByRole("button", { name: new RegExp(`I am at station ${number}`) }).click();
}

async function readExport(page) {
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export progress" }).click();
  const download = await downloadPromise;
  const stream = await download.createReadStream();
  const chunks = [];
  for await (const chunk of stream) chunks.push(chunk);
  return JSON.parse(Buffer.concat(chunks).toString("utf8"));
}
```

```javascript
test("capture controller gates completion and emits one event", async ({ page }) => {
  await page.goto("/index.html");
  await page.getByRole("button", { name: /standard-48/ }).click();
  await page.getByLabel("I checked the Xiaomi settings").check();
  await page.getByRole("button", { name: "Start route" }).click();
  await expect(page.getByLabel("A01-L")).toBeDisabled();
  await page.getByRole("button", { name: /I am at station 1/ }).click();
  await page.getByLabel("A01-L").check();
  await expect(page.getByTestId("complete-count")).toHaveText("1");
  const exported = await readExport(page);
  expect(exported.events.filter(event => event.type === "capture_started")).toHaveLength(1);
  expect(exported.mode_plan_sha256).toMatch(/^[0-9a-f]{64}$/);
  expect(exported.events.at(-1)).toMatchObject({
    type: "shot_completed",
    group_id: "STD-A01",
    station_id: "S01",
    shot_ids: ["A01-L"],
    method: "shot",
    tz_offset_min: -420,
  });
});
```

- [ ] **Step 3: Run the focused browser tests and verify RED**

```bash
PYTHONPATH=src python3 -m astra_house.cli build-capture-pack --project projects/dorm-right-bedroom --output build/dorm-right-bedroom/capture-pack
npx playwright install chromium
npx playwright test -g "capture controller"
```

Expected: the static page has no operational controller.

- [ ] **Step 4: Implement exact event and replay semantics**

Use event types `capture_started`, `station_confirmed`, `shot_completed`, `group_completed`, `shot_skipped`, `shot_reopened`, `note_changed`, and `undo`. Each event has strictly increasing `seq`, `Date.now()` milliseconds, and `tz_offset_min = -new Date().getTimezoneOffset()`.

`group_completed` stores only the pending shot IDs in displayed order plus `method:"group"` and `within_group_order:"inferred"`. `undo` stores `undoes_seq` for the latest uncompensated reversible event; undo events, `capture_started`, and `station_confirmed` are never targets. Replay first validates the longest sequential prefix and undo references, then applies uncompensated events in original order. It returns derived statuses/notes, valid-prefix length, untouched raw events, warning text, and compensated sequence IDs.

Keep `confirmedStationId` only on the live controller instance. Completion actions require it to equal the current group's station. Reopen, undo, note, skip, cursor navigation, and restoring a skipped shot do not. Check derived state before appending so a repeated/no-op activation emits nothing.

Mode selection first shows the inherited Xiaomi/closed-door checklist. `startMode` accepts the route only after the acknowledgement checkbox is checked, then appends the sole `capture_started` event and opens the first group.

```javascript
static replay(mode, rawEvents) {
  const validEvents = [];
  const compensated = new Set();
  let warning = null;
  for (const raw of rawEvents) {
    const event = validateEvent(mode, raw, validEvents.length + 1);
    if (!event.ok) { warning = event.message; break; }
    if (event.value.type === "undo") {
      const expected = EventReducer.nextUndoTarget(validEvents, compensated);
      if (!expected || event.value.undoes_seq !== expected.seq) {
        warning = `invalid undo target at seq ${event.value.seq}`;
        break;
      }
      compensated.add(expected.seq);
    }
    validEvents.push(event.value);
  }
  const activeEvents = validEvents.filter(
    event => event.type !== "undo" && !compensated.has(event.seq)
  );
  return deriveModeState(mode, activeEvents, rawEvents, warning, compensated);
}
```

- [ ] **Step 5: Implement generic group/station traversal**

Flatten groups from the selected mode. `nextIncomplete` searches strictly after the current group and wraps once. Station selection chooses its first group with pending work or its last group if none is pending. Cursor changes save `last_group_id` but are not events. No branch names `lite-24` or `standard-48` outside recommendation labels supplied by data.

```javascript
function findNextPendingGroup(groups, currentGroupId, replay) {
  const start = groups.findIndex(group => group.id === currentGroupId);
  for (let offset = 1; offset <= groups.length; offset += 1) {
    const group = groups[(start + offset) % groups.length];
    if (group.shots.some(shot => replay.shots[shot.id].status === "pending")) {
      return group;
    }
  }
  return null;
}
```

- [ ] **Step 6: Run interaction tests and verify GREEN**

```bash
PYTHONPATH=src python3 -m astra_house.cli build-capture-pack --project projects/dorm-right-bedroom --output build/dorm-right-bedroom/capture-pack
npx playwright test -g "capture controller"
```

Expected: workflow transitions and event payload assertions pass.

- [ ] **Step 7: Commit Task 6**

```bash
git add src/astra_house/assets/capture-guide.js package.json package-lock.json playwright.config.mjs tests/browser/capture-guide.spec.mjs
git commit -m "feat: add event-sourced capture controller"
```

---

### Task 7: Add resilient per-mode persistence, export, and reset

**Files:**
- Modify: `src/astra_house/assets/capture-guide.js`
- Modify: `src/astra_house/assets/capture-guide.css`
- Modify: `tests/browser/capture-guide.spec.mjs`
- Create: `tests/browser/build_capture_fixtures.py`
- Modify: `package.json`

**Interfaces:**

```javascript
/** @typedef {{
 * schema_version:"2.0", room_id:string, capture_id:string, mode_id:string,
 * mode_plan_sha256:string, last_group_id:string, events:CaptureEvent[]
 * }} StoredModeState */

/** @typedef {{key:string, mode_plan_sha256:string, event_count:number, raw:string}} StaleStateSummary */

/** @typedef {{
 * schema_version:"2.0", room_id:string, capture_id:string, mode_id:string,
 * mode_plan_sha256:string, coverage_review_status:string,
 * coverage_review_digest:string|null, events:CaptureEvent[],
 * completed_shot_ids:string[], skipped_shot_ids:string[], pending_shot_ids:string[],
 * first_event_t_ms:number|null, last_event_t_ms:number|null
 * }} ProgressDocument */

/** @typedef {"download"|"clipboard"|"execCommand"|"manual"} DeliveryResult */
```

```text
new StateStore(identity, storage = window.localStorage)
StateStore.load(mode) -> StoredModeState
StateStore.save(mode, events, lastGroupId) -> void
StateStore.findStale(mode) -> StaleStateSummary[]
StateStore.reset(mode) -> void
ProgressExport.build(data, mode, replay) -> ProgressDocument
ProgressExport.canonicalJson(document) -> string
ProgressExport.deliver(jsonText, environment = window) -> Promise<DeliveryResult>
```

- [ ] **Step 1: Write RED persistence and failure tests**

Cover refresh resume, independent mode keys, reset-one-mode confirmation, invalid cursor recovery, corrupt JSON quarantine, quarantine failure, write failure/in-memory continuation, unavailable storage, stale hash discovery/export without application, invalid-middle-event longest-prefix replay, raw suffix preservation, and fresh station confirmation after reload.

Assert the key format is versioned and composite:

```text
astra.capture.v2/room:dorm-right-bedroom/capture:dorm-right-bedroom-diagnostic-01/mode:lite-24/hash/${mode.mode_plan_sha256}
```

The last-active pointer stores only room/capture/mode/hash/group identity.

```javascript
test("reload restores events but requires station confirmation", async ({ page }) => {
  await startAndConfirm(page, "lite-24", "S01");
  await page.getByLabel("L01-A").check();
  await page.reload();
  await expect(page.getByTestId("complete-count")).toHaveText("1");
  await expect(page.getByLabel("L01-B")).toBeDisabled();
  await expect(page.getByRole("button", { name: /I am at station 1/ })).toBeEnabled();
});

test("corrupt storage is quarantined and capture continues in memory", async ({ page }) => {
  await page.goto("/index.html");
  await page.evaluate(() => {
    const data = JSON.parse(document.getElementById("capture-data").textContent);
    const mode = data.modes.find(item => item.id === "lite-24");
    const key = [
      "astra.capture.v2/room:dorm-right-bedroom",
      "capture:dorm-right-bedroom-diagnostic-01",
      "mode:lite-24",
      `hash/${mode.mode_plan_sha256}`,
    ].join("/");
    localStorage.setItem(key, "{not-json");
  });
  await page.reload();
  await expect(page.getByRole("status")).toContainText(/could not read saved progress/i);
  const keys = await page.evaluate(() => Object.keys(localStorage));
  expect(keys.some(key => key.includes("/corrupt/"))).toBe(true);
});
```

- [ ] **Step 2: Write RED export fallback tests**

Intercept Blob download and validate identity, full events, sorted completed/skipped/pending IDs, coverage-review digest/status, and first/last event times. Force Blob failure, then verify secure Clipboard; force Clipboard failure and verify `execCommand('copy')`; force both and verify the exact read-only JSON remains selected.

```javascript
test("manual export fallback leaves exact JSON selected", async ({ page }) => {
  await page.addInitScript(() => {
    URL.createObjectURL = () => { throw new Error("blocked"); };
    Object.defineProperty(navigator, "clipboard", { value: undefined });
    document.execCommand = () => false;
  });
  await startMode(page, "lite-24");
  await page.getByRole("button", { name: "Export progress" }).click();
  const area = page.getByRole("textbox", { name: "Progress JSON" });
  await expect(area).toBeVisible();
  await page.getByRole("button", { name: "Copy" }).click();
  const selection = await area.evaluate(node => [node.selectionStart, node.selectionEnd, node.value.length]);
  expect(selection).toEqual([0, selection[2], selection[2]]);
});
```

- [ ] **Step 3: Run focused tests and verify RED**

```bash
PYTHONPATH=src python3 -m astra_house.cli build-capture-pack --project projects/dorm-right-bedroom --output build/dorm-right-bedroom/capture-pack
npx playwright test -g "persistence|export|storage|stale|invalid prefix"
```

Expected: state disappears on refresh and export controls are inert.

- [ ] **Step 4: Implement storage without blocking field work**

Validate saved schema and composite identity before replay. Quarantine corrupt raw strings under the current key plus `/corrupt/${Date.now()}` when writable. If any storage operation throws, retain the live in-memory record and show one persistent warning that refresh/close can lose work. Scan only the current room/capture/mode prefix for older hashes and expose their raw values and event counts.

After valid reload, restore the last group if known; otherwise derive the first pending group. Never restore `confirmedStationId`. Save after every accepted event and cursor change.

```javascript
save(mode, events, lastGroupId) {
  const record = {
    schema_version: "2.0",
    room_id: this.identity.room_id,
    capture_id: this.identity.capture_id,
    mode_id: mode.id,
    mode_plan_sha256: mode.mode_plan_sha256,
    last_group_id: lastGroupId,
    events,
  };
  try {
    this.storage.setItem(this.key(mode), JSON.stringify(record));
    this.memory.set(mode.id, record);
  } catch (error) {
    this.memory.set(mode.id, record);
    this.persistenceWarning = String(error);
  }
}
```

- [ ] **Step 5: Implement canonical export and fallback delivery**

Create objects in a fixed documented key order, sort derived ID arrays by plan order, and serialize with two-space indentation plus trailing newline. Try `URL.createObjectURL(new Blob([jsonText], {type: "application/json"}))`; on failure reveal the exact string. Copy uses `navigator.clipboard.writeText` only in a secure context, then selected text plus `document.execCommand('copy')`, then leaves selection active with manual instructions.

```javascript
static canonicalJson(document) {
  return `${JSON.stringify(document, null, 2)}\n`;
}

static async copyFallback(textarea) {
  textarea.focus();
  textarea.select();
  if (window.isSecureContext && navigator.clipboard?.writeText) {
    try { await navigator.clipboard.writeText(textarea.value); return "clipboard"; }
    catch (error) { textarea.dataset.clipboardError = String(error); }
  }
  if (document.execCommand?.("copy")) return "execCommand";
  return "manual";
}
```

- [ ] **Step 6: Run focused tests and verify GREEN**

```bash
PYTHONPATH=src python3 -m astra_house.cli build-capture-pack --project projects/dorm-right-bedroom --output build/dorm-right-bedroom/capture-pack
npx playwright test -g "persistence|export|storage|stale|invalid prefix"
```

Expected: every degradation path preserves the current in-memory workflow and communicates what will be lost.

- [ ] **Step 7: Commit Task 7**

```bash
git add src/astra_house/assets/capture-guide.js src/astra_house/assets/capture-guide.css tests/browser/capture-guide.spec.mjs
git commit -m "feat: persist and export capture progress"
```

---

### Task 8: Complete map-first rendering and accessible task controls

**Files:**
- Modify: `src/astra_house/assets/capture-guide.js`
- Modify: `src/astra_house/assets/capture-guide.css`
- Modify: `tests/browser/capture-guide.spec.mjs`

**Interfaces:**

```text
new MapView(root, data, onStationSelected)
MapView.render(mode, group, replay, currentShotId) -> void
new TaskView(root, handlers)
TaskView.render(mode, group, replay, confirmedStationId) -> void
TaskView.renderCompletion(mode, replay) -> void
```

- [ ] **Step 1: Write RED map-state and accessibility tests**

Assert the current group shows all arrows, current is thick/prominent, completed remains visible, later shots are subdued, and the FOV diagnostic layer toggles without changing progress. Pin current-pass marker states and separate whole-mode rings for `current`, `completed`, `gap`, `in progress`, `upcoming`, and `not in this pass` using classes plus text/shape attributes.

Verify native station buttons select every overlapping marker's station, keyboard focus remains visible, inputs have labels, live progress uses `aria-live=polite`, and no camera/geolocation/motion/compass/XR permission is requested.

```javascript
test("station list reaches every map station without changing progress", async ({ page }) => {
  await startMode(page, "standard-48");
  for (let number = 1; number <= 8; number += 1) {
    await page.getByRole("button", { name: new RegExp(`Station ${number}`) }).click();
    await expect(page.getByTestId("current-station")).toHaveText(String(number));
    await expect(page.getByTestId("complete-count")).toHaveText("0");
  }
});
```

- [ ] **Step 2: Run map tests and verify RED**

```bash
PYTHONPATH=src python3 -m astra_house.cli build-capture-pack --project projects/dorm-right-bedroom --output build/dorm-right-bedroom/capture-pack
npx playwright test -g "map-first|station state|accessibility"
```

Expected: controller changes are not yet reflected in the SVG/task layout.

- [ ] **Step 3: Implement derived station states and map updates**

For the current pass, aggregate only its shots at a station. `current` overrides all. Otherwise use all-completed, no-pending-plus-skipped, mixed-resolved/pending, all-pending, or no-current-pass-shots in that order. Compute a second state from all mode shots for the marker ring and accessible label. Render only stations used by the selected mode.

Use the precomputed boundary ray and cone polygon from embedded Python data. Arrow length is the first-boundary distance, never target distance. Update classes and labels after every accepted action; do not recompute geometry in JavaScript.

```javascript
function passState(statuses) {
  if (statuses.every(status => status === "completed")) return "completed";
  if (statuses.every(status => status !== "pending") && statuses.includes("skipped")) return "gap";
  if (statuses.some(status => status !== "pending")) return "in-progress";
  return "upcoming";
}

marker.dataset.passState = current ? "current" : (
  passShots.length ? passState(passShots.map(shot => replay.shots[shot.id].status)) : "not-in-pass"
);
marker.dataset.modeState = passState(modeShots.map(shot => replay.shots[shot.id].status));
```

- [ ] **Step 4: Implement current-task and completion views**

Before confirmation, show `Go to station N` plus landmark and enable only confirmation, skip, note, navigation, undo, mode change, and export. After confirmation, enable native shot checkboxes and `All photos taken — complete group`. Show `Checklist complete — verify the album` only for all-completed; otherwise show `Route reviewed with gaps` and missing IDs. Always repeat untouched-original upload rules and the event-log interval disclaimer.

```javascript
const canCapture = confirmedStationId === group.station_id;
for (const checkbox of root.querySelectorAll("input[data-shot-id]")) {
  checkbox.disabled = !canCapture;
}
completeGroupButton.disabled = !canCapture || !group.shots.some(
  shot => replay.shots[shot.id].status === "pending"
);
```

- [ ] **Step 5: Run map/accessibility tests and verify GREEN**

```bash
PYTHONPATH=src python3 -m astra_house.cli build-capture-pack --project projects/dorm-right-bedroom --output build/dorm-right-bedroom/capture-pack
npx playwright test -g "map-first|station state|accessibility"
```

Expected: map, task, station list, and live text agree after every state change.

- [ ] **Step 6: Commit Task 8**

```bash
git add src/astra_house/assets/capture-guide.js src/astra_house/assets/capture-guide.css tests/browser/capture-guide.spec.mjs
git commit -m "feat: render interactive map-first capture flow"
```

---

### Task 9: Lock full browser, responsive, fallback, and extension coverage

**Files:**
- Modify: `tests/browser/capture-guide.spec.mjs`
- Modify: `playwright.config.mjs`
- Create: `tests/browser/capture-guide.spec.mjs-snapshots/` files generated by Playwright
- Modify: `src/astra_house/capture_web.py`
- Modify: `src/astra_house/assets/capture-guide.css`
- Modify: `src/astra_house/assets/capture-guide.js`

**Interfaces:**
- The tests consume only the generated `index.html` and its public controls/data.
- A test-only third-mode document is produced by Python generation from a valid temporary plan; production JavaScript receives it through the same embedded JSON path.

- [ ] **Step 1: Add the remaining RED browser matrix**

Test both current modes end-to-end plus a generated `test-3` mode through select, confirm, complete, persist, export. Add two consecutive undo actions, compensation restoring completion without confirmation, Pacific daylight offset `-420`, no-op event counts, mode switching, stale-state display, and unsupported-origin warning.

`build_capture_fixtures.py` deep-copies the project JSON into a temporary directory, appends this valid mode, clears `coverage_review`, and calls `build_capture_project` with output `build/dorm-right-bedroom/capture-pack-third-mode`:

```python
THIRD_MODE = {
    "id": "test-3",
    "title": "Third-mode fixture",
    "description": "Proves the renderer and controller are data-driven.",
    "expected_image_count": 1,
    "risk_note": "Browser-test fixture only.",
    "required_scale_anchor_ids": [],
    "passes": [{
        "id": "T-PASS",
        "title": "Fixture pass",
        "purpose": "Complete one generic mode.",
        "groups": [{
            "id": "T-G01",
            "title": "Fixture group",
            "purpose": "One wall view.",
            "station_id": "S01",
            "next_hint": None,
            "shots": [{
                "id": "T-ONLY",
                "aim_point_m": [0.0, 2.0],
                "framing_points_m": [[0.0, 2.0, 1.45]],
                "pitch": "level",
                "pitch_deg": 0.0,
                "target_ids": ["wall-05"],
                "instruction": "Frame the north wall from station 1."
            }]
        }]
    }]
}

def main() -> None:
    project = Path("projects/dorm-right-bedroom")
    build_capture_project(
        project_dir=project,
        output_dir=Path("build/dorm-right-bedroom/capture-pack"),
    )
    with tempfile.TemporaryDirectory() as directory:
        fixture_project = Path(directory) / "dorm-right-bedroom"
        shutil.copytree(project, fixture_project)
        capture_path = fixture_project / "capture-plan.json"
        capture_data = json.loads(capture_path.read_text(encoding="utf-8"))
        capture_data.pop("coverage_review", None)
        capture_data["modes"].append(THIRD_MODE)
        capture_path.write_text(
            json.dumps(capture_data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        build_capture_project(
            project_dir=fixture_project,
            output_dir=Path("build/dorm-right-bedroom/capture-pack-third-mode"),
        )

if __name__ == "__main__":
    main()
```

Update `package.json` so the full command always builds both fixtures first, then change `playwright.config.mjs` to serve the normal pack on port `8765` and the third-mode pack on `8766`:

```json
{
  "scripts": {
    "build:capture-fixtures": "PYTHONPATH=src python3 tests/browser/build_capture_fixtures.py",
    "test:capture-browser": "npm run build:capture-fixtures && playwright test",
    "update:capture-snapshots": "npm run build:capture-fixtures && playwright test --update-snapshots"
  }
}
```

```javascript
webServer: [
  {
    command: "python3 -m http.server 8765 --directory build/dorm-right-bedroom/capture-pack",
    url: "http://127.0.0.1:8765/index.html",
    reuseExistingServer: false,
  },
  {
    command: "python3 -m http.server 8766 --directory build/dorm-right-bedroom/capture-pack-third-mode",
    url: "http://127.0.0.1:8766/index.html",
    reuseExistingServer: false,
  },
],
```

For static fallback, create a context with JavaScript disabled and assert both full ledgers remain readable. For initialization failure, inject `window.__ASTRA_FORCE_INIT_ERROR__ = true` before page code and assert static content stays visible with an enhancement warning.

```javascript
test("static ledgers survive disabled JavaScript", async ({ browser }) => {
  const context = await browser.newContext({ javaScriptEnabled: false });
  const page = await context.newPage();
  await page.goto("http://127.0.0.1:8765/index.html");
  await expect(page.getByText("lite-24")).toBeVisible();
  await expect(page.getByText("standard-48")).toBeVisible();
  await expect(page.getByText("L14-A")).toBeVisible();
  await expect(page.getByText("D08")).toBeVisible();
  await context.close();
});

test("direct file opening warns without blocking static guidance", async ({ page }) => {
  await page.goto(`file://${process.cwd()}/build/dorm-right-bedroom/capture-pack/index.html`);
  await expect(page.getByRole("status")).toContainText(/persistence.*unverified/i);
  await expect(page.getByText("L01-A")).toBeVisible();
});

test("third mode completes through the generic controller", async ({ page }) => {
  await startAndConfirm(page, "test-3", "S01", "http://127.0.0.1:8766/index.html");
  await page.getByLabel("T-ONLY").check();
  await expect(page.getByText("Checklist complete — verify the album")).toBeVisible();
});
```

At desktop, `390 × 844`, and `320 × 800`, assert:

```javascript
const widths = await page.evaluate(() => ({
  client: document.documentElement.clientWidth,
  scroll: document.documentElement.scrollWidth,
}));
expect(widths.scroll).toBe(widths.client);
```

Take named snapshots of mode choice, current map/task, gap state, and completion handoff with animations disabled.

- [ ] **Step 2: Run the complete browser suite and verify RED**

```bash
npm run test:capture-browser
```

Expected: at least third-mode, fallback, small-width, or visual assertions fail before final integration adjustments.

- [ ] **Step 3: Make generic and responsive fixes only**

Fix shared data-driven rendering, layout, hit targets, or accessible labels. Do not branch on current mode IDs to satisfy the third-mode case. Do not hide overflow at the document root to mask layout failures. Keep unsupported origins honest rather than suppressing their warning.

```css
.map-shell, .task-card, .station-list { min-width: 0; max-width: 100%; }
.station-list { display: grid; grid-template-columns: repeat(auto-fit, minmax(7.5rem, 1fr)); }
.station-button { min-height: 44px; white-space: normal; }
.map-label { paint-order: stroke; stroke: #fff; stroke-width: 3px; }
```

- [ ] **Step 4: Generate and inspect pinned screenshot baselines**

```bash
npm run update:capture-snapshots
npm run test:capture-browser
```

Open every baseline and confirm station labels, arrow/cone direction, status distinctions, task controls, and handoff text are legible. The committed `package-lock.json`, Playwright browser revision, one-worker configuration, viewport, locale, timezone, reduced motion, and Arial font stack define the baseline environment.

- [ ] **Step 5: Run all Python and browser tests**

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
npm run test:capture-browser
```

Expected: all suites pass.

- [ ] **Step 6: Commit Task 9**

```bash
git add tests/browser package.json playwright.config.mjs src/astra_house/capture_web.py src/astra_house/assets/capture-guide.css src/astra_house/assets/capture-guide.js
git commit -m "test: verify capture guide in the browser"
```

---

### Task 10: Review coverage, document field delivery, and verify the pilot build

**Files:**
- Modify: `projects/dorm-right-bedroom/capture-plan.json`
- Create: `tests/fixtures/dorm-right-bedroom-capture-pack-report-v2.json`
- Create: `docs/field-tests/xiaomi-capture-guide-pilot.md`
- Modify: `README.md`
- Modify: `tests/test_capture_geometry.py`
- Modify: `tests/test_capture_pack.py`

**Interfaces:**
- The source `coverage_review` mapping records exact generated mode hashes and warning-code sets after plan-author inspection.
- The pilot document records evidence without changing application state or implying an unrun device result.

- [ ] **Step 1: Build the draft and inspect every coverage diagnostic**

```bash
PYTHONPATH=src python3 -m astra_house.cli build-capture-pack --project projects/dorm-right-bedroom --output build/dorm-right-bedroom/capture-pack
python3 -m json.tool build/dorm-right-bedroom/capture-pack/capture-pack-report.json
```

Open the embedded diagnostic FOV layer and verify every arrow points into the labeled intended targets, framing points lie inside the usable cones, neighboring shared spans are visually plausible, and each warning corresponds to a known pilot limitation. Correct source aim/framing data and repeat all geometry tests for any mismatch.

- [ ] **Step 2: Record exact reviewed warning sets**

After inspection, copy each report's exact `mode_plan_sha256` and sorted warning codes into `coverage_review`, with reviewer `ASTRA plan-author preflight` and an ISO-8601 UTC review timestamp. Do not record an empty or guessed digest. Rebuild and assert both mode review states are `current` and overall status is `publishable` for the pilot geometry.

Add tests proving a one-character instruction change causes `stale_hash` and a warning-set change causes `stale_codes` without deleting the old review record.

After the reviews are current, copy the canonical report to `tests/fixtures/dorm-right-bedroom-capture-pack-report-v2.json` and assert the generated report bytes equal that fixture. This pins quantized geometry, issue ordering, counts, hashes, and status across the supported macOS and Linux test environments.

```bash
cp build/dorm-right-bedroom/capture-pack/capture-pack-report.json tests/fixtures/dorm-right-bedroom-capture-pack-report-v2.json
```

```python
self.assertEqual(
    (output / "capture-pack-report.json").read_bytes(),
    Path("tests/fixtures/dorm-right-bedroom-capture-pack-report-v2.json").read_bytes(),
)
```

- [ ] **Step 3: Write the real-Xiaomi matrix without claiming execution**

Create a checklist with evidence columns for date, Chrome/Android versions, origin URL, action, expected result, observed result, pass/fail, screenshot/log path, and notes. Include stable HTTPS and Mac-LAN cases for first open, refresh, native-camera round trip, documented ADB tab-kill method, server log evidence of reload, independent mode state, download, all copy paths, server unreachable during reload, same-origin recovery, direct file warning, Xiaomi Browser warning, and WeChat warning.

Leave observation cells unchecked until the user performs the test on the Xiaomi. State that field release is blocked by any failed supported-path row, but local implementation testing may proceed.

- [ ] **Step 4: Update operator documentation**

Document the stable build command and preferred stable HTTPS delivery. Add the development command exactly:

```bash
caffeinate -i python3 -m http.server 8765 --directory build/dorm-right-bedroom/capture-pack
```

State that the Mac must remain powered, lid open, server/port/hostname/network unchanged, and the exact phone URL must reload before capture. Explain campus Wi-Fi client isolation, same-origin recovery, two independent modes, event export, native-camera originals, no automatic positioning, and the uncompleted real-device release gate.

Document intake timing explicitly: `capture_started` opens the first interval; each completion/group-completion/skip closes it and opens the next; `station_confirmed` is an auxiliary marker only; group shot order is inferred; EXIF combines `DateTimeOriginal`, optional `SubSecTimeOriginal`, and optional `OffsetTimeOriginal`, otherwise using event `tz_offset_min` as an assumption. Ambiguous and out-of-window images remain unassigned but retained.

- [ ] **Step 5: Run final verification from a clean generated directory**

Remove only the ignored capture-pack directory, rebuild, and verify the exact file set and deterministic second build:

```bash
rm -rf build/dorm-right-bedroom/capture-pack
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m astra_house.cli build-capture-pack --project projects/dorm-right-bedroom --output build/dorm-right-bedroom/capture-pack
find build/dorm-right-bedroom/capture-pack -maxdepth 1 -type f -print | sort
npm run test:capture-browser
git status --short
```

Expected generated file set:

```text
build/dorm-right-bedroom/capture-pack/capture-intake.json
build/dorm-right-bedroom/capture-pack/capture-pack-report.json
build/dorm-right-bedroom/capture-pack/index.html
```

Run a second build and compare SHA-256 values for all three artifacts. Expected: identical digests. Confirm no generated `build/` file is staged.

- [ ] **Step 6: Commit Task 10**

```bash
git add projects/dorm-right-bedroom/capture-plan.json tests/fixtures/dorm-right-bedroom-capture-pack-report-v2.json docs/field-tests/xiaomi-capture-guide-pilot.md README.md tests/test_capture_geometry.py tests/test_capture_pack.py
git commit -m "docs: prepare Xiaomi capture guide pilot"
```

---

## Final Review Gate

- [ ] Run `PYTHONPATH=src python3 -m unittest discover -s tests -v` and retain the passing count.
- [ ] Run `npm run test:capture-browser` and retain the passing count plus snapshot result.
- [ ] Rebuild twice and prove byte-identical generated artifacts.
- [ ] Inspect `capture-pack-report.json`: 24/48 images, 14/28 groups, eight shared stations, 72 unique shot IDs, zero geometry errors, current coverage reviews, and intentional warnings visible.
- [ ] Inspect the static page with JavaScript disabled and with forced initialization failure.
- [ ] Inspect 320- and 390-pixel screenshots for text clipping, target reachability, and non-color status cues.
- [ ] Search source and generated HTML for external network resources and forbidden automatic-position claims.
- [ ] Review the diff against the approved spec, focusing on migration equality, hash isolation, undo semantics, longest-prefix replay, and static fallback.
- [ ] Keep the Xiaomi matrix explicitly unpassed until physical evidence is added; do not describe desktop success as field release.
