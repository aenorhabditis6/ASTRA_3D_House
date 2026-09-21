# Dorm Diagnostic Capture Package Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate a validated, phone-friendly 48-image shooting guide for the right dorm bedroom, using a Xiaomi 17 Ultra as the single primary camera.

**Architecture:** A standard-library capture-plan domain module validates reviewed wall assignments, shot targets, counts, and room-space standing points against the existing `RoomModel`. A separate renderer projects those points back onto the trusted plan and atomically writes a self-contained HTML guide plus two JSON handoff files. The existing CLI gains a Blender-free `build-capture-pack` command.

**Tech Stack:** Python 3.11+ standard library, `unittest`, JSON, HTML/CSS/SVG, existing ASTRA room/plan modules, Playwright CLI for local visual QA only

**Spec:** `docs/superpowers/specs/2026-09-20-dorm-capture-package-design.md`

## Global Constraints

- The diagnostic batch contains exactly 48 still images: 24 structure-loop, 8 high/low, 8 corner/occlusion, and 8 opening/anchor images.
- All 48 images use the Xiaomi 17 Ultra 1× Leica 23 mm main camera in landscape 4:3 JPG mode.
- Do not mix an iPhone or another lens into this capture ID.
- `bath-door-south` belongs to `wall-02`; `wall-03` is a connecting return with no opening.
- Generated operator guidance is a self-contained offline HTML file and must remain legible at desktop and phone widths.
- Route markers are approximate safe standing zones, not survey-grade camera coordinates.
- Original photo files are never renamed or modified by this subproject.
- No runtime dependency, cloud service, COLMAP, hloc, OpenCV, HEIC converter, or AI-generated diagram is introduced.
- Invalid input must fail before any output file is replaced.

## Review Focus

- A reviewed opening assigned to the wrong wall must stop generation and name both wall IDs; `tests/test_capture.py` pins the bath-door regression.
- A standing point outside the L-shaped floor must be rejected; `tests/test_capture.py` exercises the concave notch, not only the bounding box.
- Duplicate shot IDs or any total other than 48 must be rejected; `tests/test_capture.py` exercises both cases.
- A changed floor-plan source hash must stop the CLI before writing the pack; `tests/test_capture_cli.py` verifies the manifest boundary.
- The route map and shot ledger must not overflow at 390 CSS pixels; Task 5 records Playwright screenshots and checks `scrollWidth == clientWidth`.

## File Structure

```text
projects/dorm-right-bedroom/capture-plan.json   Reviewed 48-shot source plan
src/astra_house/capture.py                      Capture-plan parsing and validation
src/astra_house/capture_pack.py                 HTML/SVG/JSON package renderer
src/astra_house/cli.py                          `build-capture-pack` orchestration
tests/test_capture.py                           Domain, count, geometry, wall-review tests
tests/test_capture_pack.py                      Deterministic renderer and artifact tests
tests/test_capture_cli.py                       CLI and manifest-boundary tests
README.md                                       Build and shooting instructions
build/dorm-right-bedroom/capture-pack/          Ignored generated deliverables
```

---

### Task 1: Capture-plan domain and structural review gate

**Files:**
- Create: `src/astra_house/capture.py`
- Create: `tests/test_capture.py`

**Interfaces:**
- Consumes: `RoomModel`, `Vec2`, and decoded JSON-compatible dictionaries.
- Produces: `CapturePlan.from_dict(data: dict[str, Any]) -> CapturePlan` and `CapturePlan.validate(room: RoomModel) -> None`.

- [ ] **Step 1: Write failing parser and validation tests**

Create a 48-shot in-memory fixture and assert the public behavior:

```python
ROOM = Path("projects/dorm-right-bedroom/room.json")


def valid_capture_data() -> dict[str, object]:
    counts = {"A": 24, "B": 8, "C": 8, "D": 8}
    passes = []
    for pass_id, count in counts.items():
        passes.append(
            {
                "id": pass_id,
                "title": f"Pass {pass_id}",
                "purpose": "validation fixture",
                "shots": [
                    {
                        "id": f"{pass_id}{index:02d}",
                        "standing_point_m": [2.0, 2.0],
                        "pitch": "level",
                        "target_ids": ["wall-00"],
                        "instruction": "Keep wall-00 and both neighboring edges visible.",
                    }
                    for index in range(1, count + 1)
                ],
            }
        )
    return {
        "schema_version": "1.0",
        "room_id": "dorm-right-bedroom",
        "capture_id": "dorm-right-bedroom-diagnostic-01",
        "expected_image_count": 48,
        "device_profile": {
            "make": "Xiaomi",
            "model": "Xiaomi 17 Ultra",
            "lens": "1x Leica 23 mm main",
            "orientation": "landscape",
            "aspect_ratio": "4:3",
            "file_format": "JPG",
            "arcore_status": "unverified_optional",
        },
        "wall_review": {
            "wall-00": {"role": "east double-window wall", "opening_ids": ["window-west", "window-east"]},
            "wall-01": {"role": "south long wall", "opening_ids": []},
            "wall-02": {"role": "west-facing bathroom-door wall", "opening_ids": ["bath-door-south"]},
            "wall-03": {"role": "connecting return", "opening_ids": []},
            "wall-04": {"role": "west-facing entry wall", "opening_ids": ["entry-door"]},
            "wall-05": {"role": "north measured wall", "opening_ids": []},
        },
        "passes": passes,
    }


class CapturePlanTest(unittest.TestCase):
    def test_accepts_48_unique_shots_and_reviewed_openings(self) -> None:
        plan = CapturePlan.from_dict(valid_capture_data())
        plan.validate(load_room(Path("projects/dorm-right-bedroom/room.json")))
        self.assertEqual(plan.expected_image_count, 48)
        self.assertEqual(len(plan.shots), 48)

    def test_rejects_bath_door_on_return_wall(self) -> None:
        data = valid_capture_data()
        data["wall_review"]["wall-02"]["opening_ids"] = []
        data["wall_review"]["wall-03"]["opening_ids"] = ["bath-door-south"]
        plan = CapturePlan.from_dict(data)
        with self.assertRaisesRegex(
            ValidationError,
            "bath-door-south.*wall-03.*wall-02",
        ):
            plan.validate(load_room(Path("projects/dorm-right-bedroom/room.json")))

    def test_rejects_point_in_l_shape_notch(self) -> None:
        data = valid_capture_data()
        data["passes"][0]["shots"][0]["standing_point_m"] = [1.0, 0.5]
        with self.assertRaisesRegex(ValidationError, "outside floor polygon"):
            CapturePlan.from_dict(data).validate(load_room(ROOM))

    def test_rejects_duplicate_ids_and_wrong_total(self) -> None:
        duplicate = valid_capture_data()
        duplicate["passes"][0]["shots"][1]["id"] = "A01-L"
        with self.assertRaisesRegex(ValidationError, "duplicate shot id"):
            CapturePlan.from_dict(duplicate).validate(load_room(ROOM))
        short = valid_capture_data()
        short["passes"][0]["shots"].pop()
        with self.assertRaisesRegex(ValidationError, "expected 48.*found 47"):
            CapturePlan.from_dict(short).validate(load_room(ROOM))
```

- [ ] **Step 2: Run the tests and verify RED**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_capture -v
```

Expected: import failure because `astra_house.capture` does not exist.

- [ ] **Step 3: Implement immutable capture types and validation**

Create these types:

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

@dataclass(frozen=True)
class WallReview:
    wall_id: str
    role: str
    opening_ids: tuple[str, ...]

@dataclass(frozen=True)
class CaptureShot:
    id: str
    standing_point_m: Vec2
    pitch: str
    target_ids: tuple[str, ...]
    instruction: str

@dataclass(frozen=True)
class CapturePass:
    id: str
    title: str
    purpose: str
    shots: tuple[CaptureShot, ...]

@dataclass(frozen=True)
class CapturePlan:
    schema_version: str
    room_id: str
    capture_id: str
    expected_image_count: int
    device_profile: DeviceProfile
    wall_review: tuple[WallReview, ...]
    passes: tuple[CapturePass, ...]

    @property
    def shots(self) -> tuple[CaptureShot, ...]:
        return tuple(shot for item in self.passes for shot in item.shots)
```

Add `from_dict(cls, data: dict[str, Any]) -> CapturePlan` using direct field
lookups inside `try/except (KeyError, TypeError, ValueError)` and translate the
caught exception to `ValidationError(f"invalid capture plan: {error}")`. Add
`validate(self, room: RoomModel) -> None`. Validation must enforce schema `1.0`, non-empty strings, pitch in
`{"level", "up", "down"}`, exact count equality, global shot-ID uniqueness,
all target IDs existing in walls/openings/proxies, every room wall appearing
exactly once in `wall_review`, reviewed opening ownership matching
`Opening.wall_id`, and every point inside or on the room floor polygon. Implement
an even/odd ray-cast point-in-polygon helper that correctly handles the concave
notch.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run the Task 1 command again. Expected: all `CapturePlanTest` cases pass.

- [ ] **Step 5: Commit Task 1**

```bash
git add src/astra_house/capture.py tests/test_capture.py
git commit -m "feat: validate diagnostic capture plans"
```

---

### Task 2: Reviewed Xiaomi 48-shot source plan

**Files:**
- Create: `projects/dorm-right-bedroom/capture-plan.json`
- Modify: `tests/test_capture.py`

**Interfaces:**
- Consumes: the Task 1 `CapturePlan` schema and current `room.json` semantic IDs.
- Produces: one reviewed source plan whose ordered `CapturePlan.shots` are the canonical shot ledger.

- [ ] **Step 1: Add failing project-data assertions**

```python
CAPTURE_PLAN = Path("projects/dorm-right-bedroom/capture-plan.json")
ROOM = Path("projects/dorm-right-bedroom/room.json")


def test_project_capture_plan_has_expected_passes_and_device(self) -> None:
    plan = CapturePlan.from_dict(json.loads(CAPTURE_PLAN.read_text()))
    plan.validate(load_room(ROOM))
    self.assertEqual([item.id for item in plan.passes], ["A", "B", "C", "D"])
    self.assertEqual([len(item.shots) for item in plan.passes], [24, 8, 8, 8])
    self.assertEqual(plan.device_profile.model, "Xiaomi 17 Ultra")
    self.assertEqual(plan.device_profile.lens, "1x Leica 23 mm main")
    self.assertEqual(plan.device_profile.arcore_status, "unverified_optional")
    review = {item.wall_id: item for item in plan.wall_review}
    self.assertEqual(review["wall-02"].opening_ids, ("bath-door-south",))
    self.assertEqual(review["wall-03"].opening_ids, ())
```

- [ ] **Step 2: Run the new test and verify RED**

Expected: `FileNotFoundError` for `capture-plan.json`.

- [ ] **Step 3: Create the reviewed source plan**

Use this exact device profile:

```json
{
  "make": "Xiaomi",
  "model": "Xiaomi 17 Ultra",
  "lens": "1x Leica 23 mm main",
  "orientation": "landscape",
  "aspect_ratio": "4:3",
  "file_format": "JPG",
  "arcore_status": "unverified_optional"
}
```

Use these eight clockwise structure-loop standing zones, repeating each point
for left/center/right level shots `A01-L` through `A08-R`:

| Station | Room-space point (m) |
| --- | --- |
| A01 | `[1.35, 1.65]` |
| A02 | `[2.15, 1.55]` |
| A03 | `[3.10, 1.45]` |
| A04 | `[3.65, 1.80]` |
| A05 | `[2.55, 2.10]` |
| A06 | `[2.20, 2.80]` |
| A07 | `[1.55, 2.75]` |
| A08 | `[1.10, 2.10]` |

Pass B reuses A01, A03, A05, and A07 for `B01-U/D` through `B04-U/D`.
Pass C uses two views for each group: `C01-A/B` desk-window corner,
`C02-A/B` bed-window corner, `C03-A/B` closet/bath-door area, and `C04-A/B`
entry/north-wall area. Pass D enumerates `D01`–`D03` windows, `D04`–`D05`
entry door, `D06`–`D07` bathroom door plus closet, and `D08` bed plus two wall
directions. Every target uses existing semantic IDs; every instruction names the
required surrounding context rather than asking for an isolated close-up.

Use this exact point and target assignment for Passes B–D:

| Shot IDs | Points | Targets |
| --- | --- | --- |
| B01-U/D | A01 | `wall-04`, `wall-05` |
| B02-U/D | A03 | `wall-02`, `wall-01` |
| B03-U/D | A05 | `wall-00`, `wall-01` |
| B04-U/D | A07 | `wall-00`, `wall-05` |
| C01-A/B | A07, A08 | `wall-00`, `wall-05`, `desk` |
| C02-A/B | A04, A05 | `wall-00`, `wall-01`, `bed-full` |
| C03-A/B | A03, A04 | `wall-02`, `bath-door-south`, `closet` |
| C04-A/B | A01, A02 | `wall-04`, `wall-05`, `entry-door` |
| D01/D02/D03 | A07, A06, A05 | `wall-00`, `window-west`, `window-east` |
| D04/D05 | A01, A02 | `wall-04`, `entry-door` |
| D06/D07 | A03, A04 | `wall-02`, `bath-door-south`, `closet` |
| D08 | A06 | `bed-full`, `wall-00`, `wall-01` |

For Pass A, each station's left/center/right targets are respectively:

| Station | Left / center / right target walls |
| --- | --- |
| A01 | `wall-05` / `wall-00` / `wall-04` |
| A02 | `wall-05` / `wall-00` / `wall-02` |
| A03 | `wall-04` / `wall-02` / `wall-01` |
| A04 | `wall-02` / `wall-01` / `wall-00` |
| A05 | `wall-05` / `wall-00` / `wall-01` |
| A06 | `wall-05` / `wall-00` / `wall-01` |
| A07 | `wall-05` / `wall-00` / `wall-01` |
| A08 | `wall-04` / `wall-05` / `wall-00` |

- [ ] **Step 4: Run Task 1 and Task 2 tests**

Expected: all capture-domain tests pass and the flattened order contains 48 IDs.

- [ ] **Step 5: Commit Task 2**

```bash
git add projects/dorm-right-bedroom/capture-plan.json tests/test_capture.py
git commit -m "feat: define Xiaomi dorm capture route"
```

---

### Task 3: Self-contained HTML capture-pack renderer

**Files:**
- Create: `src/astra_house/capture_pack.py`
- Create: `tests/test_capture_pack.py`

**Interfaces:**
- Consumes: validated `CapturePlan`, `PlanAnnotation`, `RoomModel`, source-plan bytes, and an output directory.
- Produces: `write_capture_pack(plan, annotation, room, source_plan_path, output_dir) -> Path`, returning the generated `index.html` path after writing all three required artifacts.

- [ ] **Step 1: Write failing renderer tests**

```python
def test_writes_three_deterministic_self_contained_artifacts(self) -> None:
    with tempfile.TemporaryDirectory() as directory:
        index = write_capture_pack(plan, annotation, room, source_png, Path(directory))
        self.assertEqual(index.name, "index.html")
        html = index.read_text()
        self.assertIn("data:image/png;base64,", html)
        self.assertIn("Xiaomi 17 Ultra", html)
        self.assertIn("1× Leica 23 mm", html)
        self.assertIn("ARCore: optional / unverified", html)
        self.assertIn("wall-02", html)
        self.assertIn("bath-door-south", html)
        self.assertIn("wall-03", html)
        for shot in plan.shots:
            self.assertIn(shot.id, html)
        intake = json.loads((Path(directory) / "capture-intake.json").read_text())
        self.assertEqual(len(intake["shots"]), 48)
        self.assertTrue(all(item["source_filename"] is None for item in intake["shots"]))
        report = json.loads((Path(directory) / "capture-pack-report.json").read_text())
        self.assertEqual(report["status"], "valid")
        self.assertEqual(report["shot_count"], 48)
```

Add a failure test that places an invalid reviewed opening in the plan, creates
sentinel output files, calls `write_capture_pack`, and proves the sentinels were
not replaced.

- [ ] **Step 2: Run renderer tests and verify RED**

Expected: import failure because `capture_pack.py` does not exist.

- [ ] **Step 3: Implement deterministic rendering**

Implement:

```python
def write_capture_pack(
    plan: CapturePlan,
    annotation: PlanAnnotation,
    room: RoomModel,
    source_plan_path: Path,
    output_dir: Path,
) -> Path:
    plan.validate(room)
    # Verify room IDs, read source bytes, render all strings in memory,
    # then atomically replace each file from a same-directory temporary file.
```

The HTML must contain:

- embedded base64 PNG and responsive SVG using the source image viewBox;
- target floor polygon and opening lines;
- a clockwise polyline through the eight unique Pass A points projected with
  `PlanCalibration.room_to_pixel`;
- numbered station circles whose `<title>` includes point and shot IDs;
- orientation/wall table before the route;
- Xiaomi settings card explaining that laser focus is not LiDAR;
- four pass sections with shot cards in canonical order;
- before/during/after checklists and upload instructions;
- CSS grid that collapses to one column below 720 px, with no external fonts,
  scripts, images, or stylesheets.

Use `html.escape`, `json.dumps(value, sort_keys=True, indent=2)`, SHA-256 from
`hashlib`, base64 from `base64`, and atomic `Path.replace` writes from
same-directory temporary files.

- [ ] **Step 4: Run renderer tests and full Python suite**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_capture_pack -v
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Expected: renderer tests and all existing tests pass.

- [ ] **Step 5: Commit Task 3**

```bash
git add src/astra_house/capture_pack.py tests/test_capture_pack.py
git commit -m "feat: render offline capture package"
```

---

### Task 4: Blender-free CLI orchestration

**Files:**
- Modify: `src/astra_house/cli.py`
- Create: `tests/test_capture_cli.py`

**Interfaces:**
- Consumes: `--project` containing manifest, plan annotation, room, and capture plan.
- Produces: CLI exit `0` plus printed `index.html` path, or validation exit `2` with no partial replacement.

- [ ] **Step 1: Write failing CLI tests**

```python
def test_build_capture_pack_does_not_require_blender(self) -> None:
    with tempfile.TemporaryDirectory() as directory:
        result = main([
            "build-capture-pack",
            "--project", "projects/dorm-right-bedroom",
            "--output", directory,
        ])
        self.assertEqual(result, 0)
        self.assertTrue((Path(directory) / "index.html").is_file())

def test_changed_source_hash_fails_before_output(self) -> None:
    # Copy project and source fixture, alter one source byte, run command,
    # assert exit 2 and that a sentinel index.html remains unchanged.
```

- [ ] **Step 2: Run CLI tests and verify RED**

Expected: argparse rejects `build-capture-pack`.

- [ ] **Step 3: Add the subcommand and orchestration**

Add parser options:

```text
astra-house build-capture-pack --project PATH [--output PATH]
```

Default output is `build/<project-name>/capture-pack`. Load and validate all
four project JSON files, verify the immutable source manifest, call
`write_capture_pack`, print the returned absolute or repository-resolved path,
and reuse exit code `2` for validation/input errors. Do not accept or invoke a
Blender executable.

- [ ] **Step 4: Run CLI and full suite**

```bash
PYTHONPATH=src python3 -m unittest tests.test_capture_cli -v
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit Task 4**

```bash
git add src/astra_house/cli.py tests/test_capture_cli.py
git commit -m "feat: add capture package command"
```

---

### Task 5: User documentation, generation, and visual QA

**Files:**
- Modify: `README.md`
- Generate ignored: `build/dorm-right-bedroom/capture-pack/index.html`
- Generate ignored: `build/dorm-right-bedroom/capture-pack/capture-intake.json`
- Generate ignored: `build/dorm-right-bedroom/capture-pack/capture-pack-report.json`
- Capture for inspection only: desktop and 390 px Playwright screenshots under `/private/tmp`

**Interfaces:**
- Consumes: the completed `build-capture-pack` CLI.
- Produces: the actual shooting guide the user opens and follows.

- [ ] **Step 1: Add README instructions**

Document the exact build command, the three outputs, the 48-image pass counts,
the Xiaomi 23 mm/JPG/single-device rule, and the statement that ARCore is
optional and currently unverified for the exact Ultra model.

- [ ] **Step 2: Generate the actual package**

```bash
PYTHONPATH=src python3 -m astra_house.cli build-capture-pack \
  --project projects/dorm-right-bedroom \
  --output build/dorm-right-bedroom/capture-pack
```

Expected: command exits `0`, prints `index.html`, and the report says
`"status": "valid"` and `"shot_count": 48`.

- [ ] **Step 3: Run browser visual QA**

Use the installed Playwright workflow to open the local `index.html` at
1440×1000 and 390×844. At both sizes assert:

```javascript
document.documentElement.scrollWidth === document.documentElement.clientWidth
```

Capture screenshots and visually check route labels, the wall-review table,
Xiaomi settings, and the shot ledger. Fix only layout defects, then regenerate
and repeat both viewport checks.

- [ ] **Step 4: Run final verification**

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
git diff --check
```

Also parse both generated JSON files with `python3 -m json.tool` and confirm the
HTML contains no `http://`, `https://`, external `<script src>`, or external
`<link href>` resource.

- [ ] **Step 5: Commit Task 5**

```bash
git add README.md
git commit -m "docs: add Xiaomi diagnostic capture guide"
```

Generated `build/` files and `/private/tmp` screenshots remain uncommitted and
are reproducible from the committed plan and command.

---

### Task 6: Branch completion

**Files:** none beyond the preceding tasks.

**Interfaces:**
- Consumes: all committed source, tests, and the regenerated local pack.
- Produces: a verified pushed branch and user-facing links to the local guide.

- [ ] **Step 1: Re-run complete verification from a clean status audit**

Run the full suite, regenerate the pack once, repeat the two viewport checks,
and inspect `git status --short` so only ignored build outputs are absent.

- [ ] **Step 2: Push the existing feature branch**

```bash
git push origin codex/logical-room-mvp
```

- [ ] **Step 3: Hand off the guide**

Report the branch commit, test count, three generated artifact paths, and one
remaining user action: capture the 48 images in order and upload the untouched
originals together.
