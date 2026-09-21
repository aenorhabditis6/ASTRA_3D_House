# Interactive Capture Guide Design

Date: 2026-09-21

Status: draft for user review

Target: right-side dorm bedroom in `projects/dorm-right-bedroom`

Supersedes only the operator-interface and capture-plan portions of
`2026-09-20-dorm-capture-package-design.md`. The reviewed room geometry,
wall/opening ownership, Xiaomi camera rules, and untouched-original upload
contract remain authoritative.

## 1. Purpose

The current capture package is a correct offline reference but behaves like a
printable document. A person shooting the room still has to find the right
station, remember the current direction, and track completion independently.

This change turns the generated `index.html` into an offline, map-first field
workflow. The operator chooses either a 24-image lightweight route or the
existing 48-image diagnostic route, follows one current task at a time, and
checks off photographs or groups after taking them with the Xiaomi native camera
application. The room diagram updates after every action to show where to stand
and which way to aim.

This is not an in-browser camera application. It does not store, transform, or
upload photographs. The native camera remains the source of the untouched JPG
originals and their EXIF metadata.

## 2. Agreed Product Decisions

- Generate one self-contained HTML file with embedded CSS, JavaScript, plan
  image, room geometry, and capture-mode data.
- Continue using the Xiaomi native camera; completion is recorded manually in
  the guide after each photograph or group.
- Use the map-first mobile layout selected in the visual comparison.
- Provide two enabled modes:
  - `lite-24`: a faster 24-image route with lower redundancy;
  - `standard-48`: the existing 48-image diagnostic route.
- Do not call the 48-image route a full professional production capture. A
  future 120–220-image production mode remains deferred until camera recovery
  from the smaller batches is understood.
- Make capture modes data-driven so a future production mode can be added
  without restructuring the renderer or interaction controller.
- Use manual station confirmation in this release. Automatic indoor position
  detection and WebXR/ARCore are optional future providers, not silent claims
  made by the current UI.
- Prioritize a correct, testable workflow now; visual polish may iterate later.

## 3. Goals and Success Criteria

The change succeeds when:

- a user can complete the 24- or 48-image route from one phone-readable page;
- the current station, current aim direction, group instructions, and progress
  are visible without scanning a long document;
- checking one photograph immediately updates the arrow and the next task;
- completing a group advances to the next incomplete group;
- completed, current, skipped, and upcoming station states are distinguishable
  by both color and text/shape;
- the user can jump to another station without falsely completing intervening
  work;
- progress survives refresh in a supported browser and remains independent for
  the two modes;
- the user can undo, skip with a note, reset a mode, and export a progress JSON;
- the page remains fully useful as a static guide if JavaScript is disabled;
- the page never claims that it automatically knows the user's physical
  position;
- the generated package remains deterministic, dependency-free at Python
  runtime, and usable without network resources.

## 4. Scope

### 4.1 Included

- A capture-plan schema that represents shared stations and multiple ordered
  capture modes.
- Explicit aim points for every planned photograph.
- A reviewed 24-image lightweight mode and the existing 48-image standard mode.
- An interactive map-first workflow with per-shot and per-group completion.
- Pending, completed, and skipped shot states with optional notes.
- Independent local progress for each capture mode.
- Progress export, mode reset, direct station navigation, and completion
  summary.
- Static no-JavaScript fallback content for both modes.
- Updated intake/report JSON contracts that describe both modes.
- Automated domain, rendering, CLI, interaction, persistence, accessibility,
  and responsive-layout checks.

### 4.2 Deferred

- The final 120–220-image production route and its exact station density.
- In-browser photography, image storage, image upload, or camera control.
- Progress import from a previously exported JSON file.
- Automatic EXIF-to-shot matching and image quality control.
- Blur, exposure, duplicate, and coverage analysis.
- WebXR, ARCore, GPS, compass-gated completion, or automatic station detection.
- COLMAP, hloc, LightGlue, dense depth, Gaussian Splatting, and texture fusion.
- Hosting, PWA installation, accounts, and cross-device synchronization.

The future production route is an additional data mode, not a reason to leave an
empty or misleading third choice in the current UI.

## 5. Capture Modes

### 5.1 Standard mode — `standard-48`

The standard mode preserves the existing 48 photographs and four passes:

| Pass | Purpose | Images |
| --- | --- | ---: |
| A | Eight-station structure loop, left/center/right at each station | 24 |
| B | Up/down coverage at four reused stations | 8 |
| C | Two-sided corner and occlusion coverage | 8 |
| D | Openings and metric anchors with surrounding context | 8 |
| **Total** |  | **48** |

Existing shot IDs and target semantics remain stable. Each shot gains an
explicit `aim_point_m` used to draw a direction arrow from its station. The
mode remains diagnostic: it is intended to validate camera recovery and room
structure, not to promise production-level appearance completeness.

The schema-`1.0` standing points become stations without changing their
coordinates. Standard-mode groups are station visits, not merely semantic
subjects:

- pass A has eight three-shot groups, A01–A08 at S01–S08;
- pass B has four two-shot groups: B01 at S01, B02 at S03, B03 at S05, and B04
  at S07;
- pass C keeps its existing shot order but uses eight one-shot groups because
  each A/B occlusion pair is photographed from two different stations;
- pass D uses eight one-shot groups at the station represented by each existing
  standing point.

This produces 28 standard-mode groups while preserving all 48 shot IDs, their
order, pitch, instructions, and semantic targets. It also keeps the invariant
that one group has exactly one station to confirm.

### 5.2 Lightweight mode — `lite-24`

The lightweight mode is an explicit reviewed plan, not a runtime sample of the
48-shot mode:

| Group | Coverage | Images |
| --- | --- | ---: |
| L01–L08 | Two overlapping level directions at stations 1–8 | 16 |
| L09 | Up/down coverage at station 3: bath-door/closet and south-wall area | 2 |
| L10 | Up/down coverage at station 7: double-window/desk and north-wall area | 2 |
| L11 | Both windows with surrounding east wall | 1 |
| L12 | Entry door with north/entry-wall context | 1 |
| L13 | Bathroom door plus closet and both ends of `wall-02` | 1 |
| L14 | Measured bed together with the east and south wall directions | 1 |
| **Total** |  | **24** |

The 16 level views use these reviewed target pairs:

| Station | First view | Second view |
| --- | --- | --- |
| S01 | `wall-05` + `wall-00` | `wall-00` + `wall-04` |
| S02 | `wall-05` + `wall-00` | `wall-00` + `wall-02` |
| S03 | `wall-04` + `wall-02` | `wall-02` + `wall-01` |
| S04 | `wall-02` + `wall-01` | `wall-01` + `wall-00` |
| S05 | `wall-05` + `wall-00` | `wall-00` + `wall-01` |
| S06 | `wall-05` + `wall-00` | `wall-00` + `wall-01` |
| S07 | `wall-05` + `wall-00` | `wall-00` + `wall-01` |
| S08 | `wall-04` + `wall-05` | `wall-05` + `wall-00` |

L09 reuses S03, L10 reuses S07, L11 uses S06, L12 uses S02, L13
uses S04, and L14 uses S06. Exact aim points are reviewed in room coordinates
so each paired view overlaps both its partner and the neighboring station.
Lightweight shot IDs are `L01-A`/`L01-B` through `L10-A`/`L10-B`, followed by
the single shots `L11-A` through `L14-A`. The IDs are not aliases for standard
shots even where the operator instruction is similar.

The two level views at each route station must overlap each other and adjacent
stations. They must not become isolated close-ups. This mode intentionally has
less angular, high/low, and occlusion redundancy than `standard-48`; the UI
states that its reconstruction success rate and completeness are lower.

### 5.3 Future mode extension

The domain model and renderer iterate over enabled modes from source data. They
must not encode a two-mode maximum or hard-code rendering logic for only the
`lite-24` and `standard-48` IDs. Adding a future reviewed `production-*` mode
should require new capture-plan data and validation tests, not a new UI
architecture.

## 6. Source Data Contract

The source remains
`projects/dorm-right-bedroom/capture-plan.json` and moves to schema `2.0`.

Top-level fields:

- `schema_version`: exactly `2.0` for the multi-mode contract;
- `room_id`: must match `room.json` and `plan-annotation.json`;
- `capture_id`: stable identity shared by the two current modes;
- `device_profile`: the reviewed Xiaomi settings and ARCore status;
- `wall_review`: the reviewed wall-to-opening ownership table;
- `stations`: ordered reusable room-space standing zones;
- `modes`: ordered enabled capture modes.

Each station contains:

- `id`: stable semantic ID such as `S01`;
- `number`: human-facing integer used on the map;
- `standing_point_m`: approximate point inside or on the floor polygon;
- `label`: short landmark-based description.

The current station conversion is fixed as follows:

| Station | `standing_point_m` | Landmark label |
| --- | --- | --- |
| S01 | `[1.35, 1.65]` | just inside the entry area |
| S02 | `[2.15, 1.55]` | inner north-side route point |
| S03 | `[3.10, 1.45]` | bathroom-door/closet approach |
| S04 | `[3.65, 1.80]` | far side beside the bed zone |
| S05 | `[2.55, 2.10]` | central crossing point |
| S06 | `[2.20, 2.80]` | window side near the bed |
| S07 | `[1.55, 2.75]` | window side near the desk |
| S08 | `[1.10, 2.10]` | desk/entry-side return point |

Coordinates are metres in the existing room coordinate system. Labels are
navigation hints, not additional geometric constraints.

Each mode contains:

- `id`, `title`, and `description`;
- `expected_image_count`;
- `risk_note`: concise statement of the mode's intended reliability;
- ordered `passes`, each containing ordered groups.

Each group contains:

- `id`, `title`, `purpose`, and `station_id`;
- one or more ordered shots;
- optional `next_hint` shown before advancing.

Each shot contains:

- globally unique `id`;
- `aim_point_m`, a room-space point distinct from its standing point;
- `pitch`: `level`, `up`, or `down`;
- one or more semantic `target_ids` from walls, openings, or proxies;
- operator-facing instruction.

`aim_point_m` represents only the horizontal bearing. `pitch` separately tells
the user whether to hold the phone level, raise it, or lower it. For a single
wall/opening target the point normally lies on its centre; for a proxy it
normally uses the proxy centre. Multi-target and context views use a reviewed
point on the intended view bisector. Those points are stored explicitly in the
plan and are never inferred by browser code. The SVG normalizes and visually
clamps the station-to-aim vector, so arrow length is not presented as camera
distance or field of view.

The standing point belongs to the station rather than being duplicated in every
shot. Runtime view data may denormalize the station point for rendering, but the
reviewed JSON has one source of truth.

## 7. Validation Rules

Generation stops before replacing outputs unless all rules pass:

- schema, room identity, capture identity, and required strings are valid;
- station IDs and display numbers are unique;
- station points lie inside or on the concave floor polygon;
- every mode ID is unique and each mode has at least one pass and group;
- pass, group, and shot IDs are unique within their documented scopes; shot IDs
  are globally unique across enabled modes;
- the actual shot count for each mode equals its declared count;
- project tests pin `lite-24` to 24 shots and `standard-48` to 48 shots with the
  reviewed group/pass distribution;
- every group references a known station;
- every shot references at least one known wall, opening, or proxy;
- every aim point is finite, lies inside or on the floor polygon, and is at least
  `0.10 m` from its station point;
- every pitch is one of the three supported values;
- every room wall appears exactly once in `wall_review`;
- every room opening appears exactly once under its actual parent wall;
- `bath-door-south` remains on `wall-02`, while `wall-03` remains opening-free;
- the immutable floor-plan asset exists and matches its manifest hash.

The general domain validator allows additional future fixed-count modes. The
project fixture tests, rather than hard-coded library branches, lock the two
current mode IDs and their exact counts.

## 8. Operator Interaction Flow

### 8.1 Entry and resume

On first load, the page presents the two modes with count, purpose, and risk
note. If saved progress exists, each mode also shows its completed/required
count and offers `Resume`. Starting one mode does not alter the other.

If no saved state exists, the recommended default is `standard-48`; the user
must still make the selection explicitly. The card may carry a `Recommended`
badge, but neither mode is preselected, so the smaller route is never mistaken
for equivalent coverage.

### 8.2 Map-first field screen

The field screen follows the approved map-first concept:

1. a compact header shows room, selected mode, and numeric progress;
2. the dominant responsive SVG map shows all eight stations and the room
   boundary;
3. the current station is enlarged and labeled;
4. arrows show every shot in the current group;
5. the current shot arrow is thick and prominent;
6. completed arrows remain visible in a completed treatment;
7. later arrows in the group remain subdued;
8. the current group card below the map contains the shot checklist,
   instructions, targets, and navigation actions.

Map meaning never relies on color alone. Marker fill, ring, opacity, line width,
labels, and status text distinguish current, completed, skipped, and upcoming
states.

Station state is derived only from shots in the selected mode. `current`
overrides every other visual state. A non-current station is `completed` when
all of its shots are completed, `gap` when it has no pending shots and at least
one skipped shot, `in progress` when it mixes resolved and pending shots, and
`upcoming` when every shot remains pending. A station with no shots in a future
mode is not rendered as a selectable route station.

### 8.3 Manual station confirmation

The guide says `Go to station N` and describes nearby landmarks. The user taps
`I am at station N` before the shot checkboxes and group-completion action are
enabled. This is a manual confirmation, not automatic detection. Confirmation
is held only for the current in-memory group visit; selecting another group or
reloading requires confirmation again, and confirmation is not exported as
evidence of physical position.

The current release uses `position_provider: manual` in its embedded UI config.
The controller boundary may accept a future `webxr` provider, but the current
page does not request camera, geolocation, motion, compass, or XR permission.

### 8.4 Shot and group completion

Each shot starts `pending` and offers a native checkbox. Checking it records a
completion timestamp and advances the highlighted arrow to the next pending shot
in the group. Unchecking it restores `pending` and updates group and mode totals.

`Complete group` marks every pending shot in the group completed. It does not
silently erase notes. The user may undo individual shots after group completion.
The action is labeled `All photos taken — complete group` and, like the shot
checkboxes, is disabled until the current station has been manually confirmed.

When all shots in a group are completed or skipped, the page selects the next
group that still has pending work and updates the map. It does not mark travel
between stations as photographic progress.

### 8.5 Skip, notes, and out-of-order work

A shot may be marked `skipped`. The UI asks for an optional brief reason, such
as furniture obstruction, safety, or lost access. Skipped shots are not counted
as completed. The progress display shows both values, for example
`20 / 24 complete · 1 skipped`.

Skipping is available before station confirmation so an inaccessible location
can be recorded honestly. Marking the current shot skipped advances the arrow
using the same next-pending rule as completion. Restoring a skipped shot returns
it to `pending` and clears neither its note nor unrelated progress.

The user may select any station marker. Selection opens the first incomplete
group at that station but does not change shot status. `Next incomplete` returns
to the planned route order. This permits safe field adaptation without
pretending the original sequence was followed.

### 8.6 Completion and upload handoff

When every required shot is completed, the page displays a completion state and
the existing untouched-original upload checklist. If any shot is skipped, the
page instead displays `Route reviewed with gaps`, lists the missing IDs, and
does not claim full completion.

The completion screen reminds the user to:

- upload all original Xiaomi JPG files together as one folder or ZIP;
- avoid renaming, editing, recompressing, or messaging-app transfer;
- include the exported progress JSON;
- mention materially moved stations or additional untracked retakes.

## 9. Progress State and Persistence

The page stores no image bytes. It stores only workflow state.

Each mode uses an independent key derived from:

```text
room_id + capture_id + mode_id + mode_plan_sha256
```

The mode-specific hash covers a canonical bundle containing the capture schema,
room/capture identity, device profile, wall review, selected complete mode,
every station referenced by that mode, and the source room-model SHA-256. It
prevents changed instructions, camera settings, geometry, shots, aim points, or
station coordinates from silently reusing stale completion state, while avoiding
a reset when only another mode is edited.

Saved state contains:

- progress schema version;
- room, capture, and mode IDs;
- mode-plan hash;
- current group and shot IDs;
- per-shot status: `pending`, `completed`, or `skipped`;
- per-shot status-change timestamp and optional resolved-order integer;
- a monotonically increasing next-order counter;
- per-shot optional notes.

When a pending shot becomes completed or skipped, it receives the next
resolved-order integer. Returning it to pending clears that integer; resolving
it again assigns a new one. `Complete group` assigns consecutive integers in
the group's displayed shot order. This ordering is an operator-action audit aid
for later EXIF/manual matching, not a claim that the browser observed the camera
shutter or knows the true capture time.

The controller writes after every state transition. Refresh reconstructs the
view from saved state. Switching modes preserves both states.

### 9.1 Storage failure

If `localStorage` is unavailable, denied, full, or corrupt:

- the workflow continues in memory;
- a persistent warning says refresh or closing the page will lose progress;
- no completion action is blocked;
- corrupt state is ignored rather than partially applied;
- the page does not automatically delete the unreadable stored value.

Because direct `file://` storage behavior varies among browsers, persistence is
best-effort when opening a downloaded file and must be tested on the target
Chromium browser. The warning path is a supported fallback, not an exception
that crashes the guide.

### 9.2 Export and reset

`Export progress` is available at any time and downloads a canonically ordered
JSON document containing the saved fields plus ordered completed, skipped, and
pending shot IDs. Its values include real action timestamps, so separate capture
sessions are not expected to produce byte-identical exports. It never includes
photos or browser/device identifiers.

The export also includes the current resolved-order ledger. Downstream tools
may compare it with EXIF chronology, but automatic filename-to-shot assignment
remains deferred and must not be silently guessed by this release.

`Reset current mode` requires confirmation and removes only the selected mode's
current-hash state. It does not reset the other mode.

Progress import and cross-device sync remain deferred.

## 10. Generated Package Contract

The CLI remains:

```text
astra-house build-capture-pack \
  --project projects/dorm-right-bedroom \
  --output build/dorm-right-bedroom/capture-pack
```

It still produces exactly three deterministic files:

1. `index.html` — self-contained interactive guide plus static fallback;
2. `capture-intake.json` — both mode ledgers, keyed by mode and ordered shot ID;
3. `capture-pack-report.json` — generator version, source hashes, mode counts,
   station/group counts, and validation status.

The report changes from a single `shot_count` to:

```json
{
  "mode_counts": {
    "lite-24": 24,
    "standard-48": 48
  }
}
```

The intake document does not imply that both routes are captured in one batch.
The exported progress JSON identifies the selected mode for later intake and
EXIF matching.

## 11. Rendering and Component Boundaries

Python remains responsible for trusted input parsing, geometric projection,
validation, source hashes, deterministic serialization, and atomic output.

The generated browser code is responsible only for local presentation state:

- `CaptureState`: mode-specific statuses, timestamps, notes, and cursor;
- `StateStore`: validated `localStorage` access with in-memory fallback;
- `CaptureController`: pure state transitions and next-incomplete selection;
- `MapView`: station/arrow/status rendering from embedded projected geometry;
- `TaskView`: current group, checkboxes, navigation, notes, and completion;
- `ProgressExport`: canonical client-side JSON serialization and download.

The implementation may split Python HTML/SVG rendering from package orchestration
to prevent `capture_pack.py` from becoming an untestable template monolith. No
new Python runtime dependency is permitted.

The page contains no external scripts, fonts, images, stylesheets, analytics,
network requests, service workers, or CDN dependencies.

## 12. Static and Accessible Fallback

The server-rendered HTML includes every mode, pass, group, shot ID, instruction,
target, station, and aim description before JavaScript runs. JavaScript enhances
that content into the field screen; it does not make the instructions exist.

With JavaScript disabled, the page displays:

- mode summaries and coverage warnings;
- the full route map and direction legend;
- printable 24- and 48-shot checklists;
- Xiaomi settings, structural wall review, and upload instructions.

Interactive controls use native buttons, checkboxes, text areas, and confirmation
dialogs. Dynamic progress changes use a polite live region. Keyboard focus is
never removed or replaced with custom-only gestures.

The layout supports at least 320 CSS pixels. At 390 pixels, map labels,
instructions, controls, and status text must fit without document-level
horizontal overflow. Print output shows static checkboxes and omits controls
whose behavior cannot exist on paper.

## 13. Error Handling

- Invalid capture data stops generation before replacing any artifact.
- Missing or hash-mismatched floor-plan data stops generation.
- Unknown current group or shot IDs in saved state cause the state to be ignored
  with a warning; they are never coerced to a different task.
- A mode-plan hash mismatch starts a fresh state under a new key and leaves the
  previous key untouched.
- Storage write failure switches to memory and reports the persistence loss.
- Repeated button activation is idempotent; it cannot increment counts twice.
- Direct station selection changes only the cursor, never completion state.
- Skipped shots prevent a false `complete` result.
- Export failure is surfaced as an actionable message and leaves progress intact.
- Missing browser APIs degrade to static/manual operation rather than blocking
  capture.

## 14. Testing Strategy

### 14.1 Domain tests

- Parse schema `2.0` into immutable stations, modes, passes, groups, and shots.
- Pin current mode order and exact counts to 24 and 48.
- Pin lightweight mode to 14 groups and standard mode to 28 groups with the
  reviewed station assignments.
- Reject duplicate IDs or station numbers, missing station references, invalid
  counts, unknown targets, invalid pitch, invalid aim points, and stations outside
  the concave floor polygon.
- Preserve the regression that `bath-door-south` belongs to `wall-02` and
  `wall-03` contains no opening.
- Prove a third valid fixed-count mode can be parsed without adding a renderer
  branch, demonstrating the production-mode extension point.

### 14.2 Renderer and CLI tests

- Generate exactly the three promised files deterministically.
- Assert both modes and all 72 distinct shot IDs are present in static HTML and
  machine-readable intake data.
- Assert mode-plan hashes and counts appear in the report.
- Assert the embedded map contains eight stations and per-shot aim geometry.
- Assert no external resource URL or network-dependent element is emitted.
- Preserve fail-before-replacement behavior for invalid inputs.

### 14.3 Browser interaction tests

Playwright exercises the generated file at desktop and 390 × 844 viewports:

- select each mode and verify its independent total;
- confirm a station, complete one shot, and verify progress and arrow state;
- complete a group and verify automatic next-group selection;
- undo and verify counts decrease correctly;
- skip with a note and verify the route is not reported complete;
- click an out-of-order station and verify no shot status changes;
- reload and verify persistence;
- switch modes and verify state isolation;
- reset one mode and verify the other remains unchanged;
- intercept and validate the progress JSON download;
- inject unavailable, corrupt, and failing storage and verify the warning and
  in-memory fallback;
- disable JavaScript and verify both static checklists remain readable;
- assert `scrollWidth == clientWidth` at both viewports;
- visually inspect map labels, active/completed/skipped states, direction arrows,
  current task, and completion handoff.

No camera, motion-sensor, WebXR, cloud, or network permission is needed by the
test or production page.

## 15. Migration and Compatibility

- Replace the committed schema-`1.0` capture plan with the reviewed schema-`2.0`
  multi-mode plan in one change; generated `build/` artifacts remain ignored.
- Keep the public CLI command and its arguments stable.
- Bump the capture-pack generator and machine-readable intake/report schema
  versions because their shapes change.
- Existing schema-`1.0` project data produces an explicit unsupported-schema
  validation error; silent conversion is not required for this sole pilot
  project.
- Existing room, plan annotation, measurement, Blender, GLB, and schematic
  contracts remain unchanged.

## 16. Resource Budget

- Python standard library only at runtime.
- No frontend framework, build tool, database, hosting service, or cloud job.
- One self-contained operator page and two small JSON handoff files.
- Progress contains metadata only; browser storage does not grow with photograph
  count or image size.
- Browser tests use the already established Playwright development workflow.

## 17. Acceptance Checklist

- [ ] `lite-24` contains exactly 24 reviewed images.
- [ ] `standard-48` preserves exactly 48 reviewed images.
- [ ] Both modes use the same eight valid station locations.
- [ ] Every shot has a validated target, pitch, instruction, and aim point.
- [ ] The map updates station and arrow state after each checkbox action.
- [ ] The current group can be completed, undone, skipped, or visited out of
      order without corrupting totals.
- [ ] Mode progress is independent and survives refresh when storage works.
- [ ] Storage failure is visible and non-blocking.
- [ ] Exported progress identifies the exact room, batch, mode, plan hash, and
      missing shots.
- [ ] No automatic physical-position claim appears in the interface.
- [ ] Static fallback includes all 72 current planned photographs.
- [ ] The page is readable without horizontal overflow at 390 CSS pixels.
- [ ] The package remains self-contained and reproducible.
- [ ] The future production mode can be introduced as reviewed data without a
      renderer redesign.
