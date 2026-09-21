# Interactive Capture Guide Design

Date: 2026-09-21

Status: approved for implementation after two external technical reviews

Target: right-side dorm bedroom in `projects/dorm-right-bedroom`

Supersedes only the operator-interface and capture-plan portions of
`2026-09-20-dorm-capture-package-design.md`. The reviewed room geometry,
wall/opening ownership, Xiaomi camera rules, and untouched-original upload
contract remain authoritative.

## 1. Purpose

The current capture package is a correct offline reference but behaves like a
printable document. A person shooting the room still has to find the right
station, remember the current direction, and track completion independently.

This change turns the generated `index.html` into a self-contained, map-first
field workflow that needs no further network request while the document remains
loaded. A reload still needs the same origin. The operator chooses either a
24-image lightweight route or the existing 48-image diagnostic route, follows
one current task at a time, and
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
- For the pilot, open the guide on the same Xiaomi phone used for photography,
  in Chrome for Android. A stable HTTPS origin is preferred; a Mac-hosted LAN
  HTTP origin is the documented development fallback and has explicit uptime
  constraints. Opening the file directly, an in-app browser, Xiaomi Browser,
  and WeChat are fallback/test cases rather than persistence-supported paths.
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
  detection and WebXR/ARCore remain future work, not silent claims or placeholder
  providers in the current UI.
- Record operator actions as an auditable event log. The log aids later manual
  EXIF matching but never claims to observe the shutter or prove photo existence.
- Preflight the planned bearings against the room polygon, a conservative camera
  field of view, target spans, and scale-anchor redundancy before field use.
- Prioritize a correct, testable workflow now; visual polish may iterate later.

## 3. Goals and Success Criteria

The change succeeds when:

- a user can complete the 24- or 48-image route from one phone-readable page;
- the current station, current aim direction, group instructions, and progress
  are visible without scanning a long document;
- checking one photograph immediately updates the arrow and the next task;
- completing a group advances to the next incomplete group;
- completed, current, gap, in-progress, and upcoming station states are
  distinguishable by both color and text/shape;
- the user can jump to another station without falsely completing intervening
  work;
- progress survives refresh in a supported browser and remains independent for
  the two modes;
- a killed/reloaded browser tab returns directly to the last active route and
  group, while requiring a fresh manual station confirmation;
- the user can undo, skip with a note, reset a mode, and export a progress JSON;
- the page remains fully useful as a static guide if JavaScript is disabled;
- the page never claims that it automatically knows the user's physical
  position;
- coverage diagnostics expose infeasible or weak bearings before the route is
  released, rather than relying only on prose about overlap;
- the generated package remains deterministic, dependency-free at Python
  runtime, and free of external network resources after the document loads.

## 4. Scope

### 4.1 Included

- A capture-plan schema that represents shared stations and multiple ordered
  capture modes.
- Explicit aim points for every planned photograph.
- Machine-readable camera field of view, nominal camera height, and numeric
  pitch for coverage checks.
- A reviewed 24-image lightweight mode and the existing 48-image standard mode.
- An interactive map-first workflow with per-shot and per-group completion.
- Pending, completed, and skipped shot states with optional notes.
- Independent local progress for each capture mode.
- Progress export, mode reset, direct station navigation, and completion
  summary.
- A compact action-event ledger and a documented manual photo-intake contract.
- Embedded coverage diagnostics for line of sight, angular span, adjacent-route
  overlap, vertical coverage, and scale anchors.
- Static no-JavaScript fallback content for both modes.
- Updated intake/report JSON contracts that describe both modes.
- A delivery contract for stable HTTPS and a documented Mac-LAN development
  fallback; deployment itself remains external to the generator.
- Automated domain, rendering, CLI, interaction, persistence, accessibility,
  and responsive-layout checks.

### 4.2 Deferred

- The final 120–220-image production route and its exact station density.
- In-browser photography, image storage, image upload, or camera control.
- Progress import from a previously exported JSON file.
- Automatic EXIF/filename-to-shot matching and image quality control. The
  current release records evidence for a later tool but leaves ambiguity for
  manual resolution.
- Photo-derived blur, exposure, duplicate, and coverage analysis. Plan-geometry
  coverage preflight remains included.
- WebXR, ARCore, GPS, compass-gated completion, or automatic station detection.
- COLMAP, hloc, LightGlue, dense depth, Gaussian Splatting, and texture fusion.
- Bundled hosting/provider setup, PWA installation, accounts, and cross-device
  synchronization.

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
coordinates. A frozen migration fixture preserves every ordered
`(shot_id, standing_point_m, pitch, target_ids, instruction)` tuple before the
source file is replaced. Standard-mode groups are station visits, not merely
semantic subjects:

- pass A has eight three-shot groups, `STD-A01`–`STD-A08` at S01–S08;
- pass B has four two-shot groups: `STD-B01` at S01, `STD-B02` at S03,
  `STD-B03` at S05, and `STD-B04` at S07;
- pass C keeps its existing shot order but uses eight one-shot groups because
  each A/B occlusion pair is photographed from two different stations. Their
  IDs are `STD-C01A`, `STD-C01B`, through `STD-C04A`, `STD-C04B`;
- pass D uses eight one-shot groups `STD-D01`–`STD-D08` at the station
  represented by each existing standing point.

This produces 28 standard-mode groups while preserving all 48 shot IDs, their
order, pitch, instructions, and semantic targets. It also keeps the invariant
that one group has exactly one station to confirm.

`standard-48.required_scale_anchor_ids` contains all seven reviewed anchors:
both windows, both doors, bed, desk, and closet. The schema-`1.0` audit confirms
that its unchanged `target_ids` already cover windows from three stations,
entry door from two, bathroom door/closet from two, bed from three, and desk
from two. Standard therefore satisfies the two-station rule without weakening
the frozen migration fixture or adding target IDs.

### 5.2 Lightweight mode — `lite-24`

The lightweight mode is an explicit reviewed plan, not a runtime sample of the
48-shot mode. It contains three ordered passes: `L-STRUCTURE` for L01–L08,
`L-VERTICAL` for L09–L10, and `L-ANCHORS` for L11–L14.

| Group | Coverage | Images |
| --- | --- | ---: |
| L01–L08 | Two overlapping level directions at stations 1–8 | 16 |
| L09 | Up/down coverage at station 3: bath-door/closet and south-wall area | 2 |
| L10 | Up/down coverage at station 7: double-window/desk and north-wall area | 2 |
| L11 | Both windows with surrounding east wall | 1 |
| L12 | Measured bed together with the east and south wall directions | 1 |
| L13 | Bathroom door plus closet with surrounding `wall-02` | 1 |
| L14 | Entry door with north/entry-wall context | 1 |
| **Total** |  | **24** |

The 16 level views use these reviewed target pairs:

| Station | First view | Second view |
| --- | --- | --- |
| S01 | `wall-04` + `wall-05` | `wall-05` + `wall-00` |
| S02 | `wall-05` + `wall-00` | `wall-00` + `wall-01` |
| S03 | `wall-03` + `wall-02` | `wall-02` + `wall-01` |
| S04 | `wall-02` + `wall-01` | `wall-01` + `wall-00` |
| S05 | `wall-05` + `wall-00` | `wall-00` + `wall-01` |
| S06 | `wall-05` + `wall-00` | `wall-00` + `wall-01` |
| S07 | `wall-05` + `wall-00` | `wall-00` + `wall-01` |
| S08 | `wall-04` + `wall-05` | `wall-05` + `wall-00` |

L09 reuses S03, L10 reuses S07, L11 and L12 form one confirmed visit at S06,
L13 uses S04, and L14 uses S02. Exact aim points are reviewed in room
coordinates so each paired view overlaps both its partner and the neighboring station.
Lightweight shot IDs are `L01-A`/`L01-B` through `L10-A`/`L10-B`, followed by
the single shots `L11-A` through `L14-A`. The IDs are not aliases for standard
shots even where the operator instruction is similar.

The anchor/vertical groups have these required primary targets:

| Group | Required `target_ids` |
| --- | --- |
| L09 | `wall-02`, `wall-01`, `bath-door-south`, `closet` |
| L10 | `wall-00`, `wall-05`, `window-west`, `window-east`, `desk` |
| L11 | `wall-00`, `window-west`, `window-east` |
| L12 | `bed-full`, `wall-00`, `wall-01` |
| L13 | `wall-02`, `bath-door-south`, `closet` |
| L14 | `wall-04`, `wall-05`, `entry-door` |

Primary scale anchors are `window-west`, `window-east`, `entry-door`,
`bath-door-south`, `bed-full`, `desk`, and `closet`. Existing level views must
also name an anchor when it is deliberately framed: windows from at least S05
and S07, entry door from S01 and S02, bathroom door/closet from S03 and S04,
bed from S04 and S05, and desk from S07 and S08. Thus every anchor is targeted
from two stations with at least a 0.5 m baseline without adding photographs.

For the pilot data, lightweight level shots use `pitch_deg: -10`, up shots use
`+25`, and down shots use `-35`. Standard-mode level shots preserve a nominal
`0`; existing B up/down shots receive `+30`/`-35`. These are operator targets,
not claims of measured IMU attitude, and their vertical-coverage warnings are
rechecked after the first Xiaomi trial.

The sequence intentionally uses adjacent wall-corner pairs. At each station the
two views share a wall, and every neighboring station pair in the closed
S01→…→S08→S01 route shares at least one structural wall target; repeated
S05–S07 views add translational baseline rather than new directions. The two
level views at each route station must overlap each other and adjacent stations.
They must not become isolated close-ups. `target_ids` define the minimum
elements that must remain recognizable and horizontally uncropped unless 3D
framing points explicitly require vertical extent; they are not an exhaustive
claim about every object incidentally visible in the frame. This mode
intentionally has less angular, high/low, and occlusion redundancy than
`standard-48`; the UI states that its reconstruction success rate and
completeness are lower.

### 5.3 Future mode extension

The domain model and renderer iterate over enabled modes from source data. They
must not encode a two-mode maximum or hard-code rendering logic for only the
`lite-24` and `standard-48` IDs. The station/group/shot primitives can express
a future reviewed `production-*` mode, including many closely spaced along-wall
stations. Such a mode still requires its own route data, performance review,
coverage thresholds, and interaction tests; this design does not promise that
adding 120–220 shots is validation-free.

## 6. Source Data Contract

The source remains
`projects/dorm-right-bedroom/capture-plan.json` and moves to schema `2.0`.

Top-level fields:

- `schema_version`: exactly `2.0` for the multi-mode contract;
- `room_id`: must match `room.json` and `plan-annotation.json`;
- `capture_id`: stable identity shared by the two current modes;
- `device_profile`: the reviewed Xiaomi settings and conservative optical
  parameters;
- `wall_review`: the reviewed wall-to-opening ownership table;
- `scale_anchors`: measured openings/proxies, each with a target ID and one or
  more exact measurement IDs used for scale;
- optional `coverage_review`: reviewed mode-plan hash, warning codes, reviewer,
  and review timestamp; required only when marking a generated route publishable;
- `stations`: ordered reusable room-space standing zones;
- `modes`: ordered enabled capture modes.

The device profile retains its human-readable `lens`, `orientation`,
`aspect_ratio`, and file-format fields and adds:

- `equivalent_focal_length_mm`: `23` for the selected 1× main camera;
- `horizontal_fov_deg` and `vertical_fov_deg`: conservative 4:3 landscape
  values used by validation and map cones;
- `fov_source` and `fov_confidence`: provenance rather than false precision;
- `camera_height_m` and `camera_height_tolerance_m`: the nominal handheld lens
  height and permitted variation;
- `coverage_margin_deg`: an angular margin removed from both frame edges.

The pilot starts with conservative provisional values of 70° horizontal, 55°
vertical, 1.45 m camera height, ±0.10 m height tolerance, and a 5° margin at
each horizontal edge. The first Xiaomi trial must measure effective field of
view and either confirm or revise them before the route is promoted beyond the
pilot. After calibration, source data should store image dimensions and focal
length in pixels and derive both FOV values from one camera model rather than
maintaining two independent estimates. `orientation` already exists and remains
fixed to `landscape`.

The reviewed scale-anchor catalog is:

| Target | Exact measurement IDs used for scale |
| --- | --- |
| `window-west` | `window-west-width` |
| `window-east` | `window-east-width` |
| `entry-door` | `entry-door-width` |
| `bath-door-south` | `bath-door-width` |
| `bed-full` | `bed-length`, `bed-width` |
| `desk` | `desk-width` |
| `closet` | `closet-depth` |

Every referenced measurement must exist in `measurements.json`, target the same
object, have a positive value, and use `exact_override`. Width/length/depth are
the required scale dimensions for this pilot; measured opening heights remain
valuable model constraints but are not required to fit uncropped in every
anchor photograph.

Each station contains:

- `id`: stable semantic ID such as `S01`;
- `number`: human-facing integer used on the map;
- `standing_point_m`: approximate point strictly inside the floor polygon;
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

Compass mapping is explicit: +X runs from the north side toward the south side,
and +Y runs from west toward east. Therefore `wall-00` is the east double-window
wall, `wall-01` the south wall, `wall-05` the north wall, and `wall-02`/`wall-04`
are west-facing segments. `window-west` and `window-east` are legacy plan-image
ordering IDs, not compass claims; `plan-annotation.json` and `room.json` place
both openings on `wall-00`, and their stable IDs are not renamed.

Each mode contains:

- `id`, `title`, and `description`;
- `expected_image_count`;
- `risk_note`: concise statement of the mode's intended reliability;
- `required_scale_anchor_ids`;
- ordered `passes`, each containing ordered groups.

Each group contains:

- `id`, `title`, `purpose`, and `station_id`;
- one or more ordered shots;
- optional `next_hint` shown before advancing.

Each shot contains:

- globally unique `id`;
- `aim_point_m`, a room-space point distinct from its standing point;
- `framing_points_m`: ordered 3D room-space landmark points `[x, y, z]` that
  must fit inside the declared usable frame;
- `pitch`: `level`, `up`, or `down`;
- `pitch_deg`: nominal optical-axis elevation in degrees, positive upward;
- one or more semantic `target_ids` from walls, openings, or proxies;
- operator-facing instruction.

`aim_point_m` represents only the horizontal bearing. `pitch` separately tells
the user whether to hold the phone level, raise it, or lower it, while
`pitch_deg` makes that instruction testable. Lightweight level shots use a
nominal −10° pitch to include more textured floor boundary; up/down values are
stored explicitly per shot. For a single wall/opening target the point normally
lies on its centre; for a proxy it
normally uses the proxy centre. Multi-target and context views use a reviewed
point on the intended view bisector. Those points are stored explicitly in the
plan and are never inferred by browser code. Python extends the bearing to its
first room-boundary intersection and precomputes a field-of-view cone; the
browser renders those values and never treats arrow length as camera distance.

`framing_points_m` make requirements such as “include both window edges” or
“keep both sides of the door wall” numerically reviewable. They are selected 3D
points on walls, opening edges/centres, or proxy bounds and are not inferred from
an entire wall ID. Every primary target has at least one associated framing
point. A target that must appear at full width has points at both horizontal
extremes; a shot that explicitly requires full height also has points at its
vertical extremes and is checked against vertical FOV. Otherwise `uncropped`
means horizontally uncropped only. This prevents a generic `wall-00` target from
incorrectly requiring the whole wall to fit in every photograph.

### 6.1 Identifier scopes and browser keys

| Identifier | Required scope |
| --- | --- |
| station ID and display number | unique for the capture plan |
| mode ID | unique for the capture plan |
| pass ID | unique within its mode |
| group ID | unique within its mode |
| shot ID | unique across all enabled modes |

DOM IDs, storage records, and controller lookups never rely on a bare pass or
group ID. They use typed composite keys such as
`mode:standard-48/group:STD-A01` and `shot:A01-L`, preventing collisions between
separate identifier namespaces.

The standing point belongs to the station rather than being duplicated in every
shot. Runtime view data may denormalize the station point for rendering, but the
reviewed JSON has one source of truth.

## 7. Validation Rules

Generation stops before replacing outputs unless all rules pass:

- schema, room identity, capture identity, and required strings are valid;
- station IDs and display numbers are unique;
- station points lie strictly inside the concave floor polygon with the same
  `0.01 m` numerical tolerance used by geometry tests;
- every mode ID is unique and each mode has at least one pass and group;
- pass, group, and shot IDs are unique within their documented scopes; shot IDs
  are globally unique across enabled modes;
- the actual shot count for each mode equals its declared count;
- project tests pin `lite-24` to 24 shots and `standard-48` to 48 shots with the
  reviewed group/pass distribution;
- every group references a known station;
- every shot references at least one known wall, opening, or proxy;
- every aim point is finite, lies inside or on the floor polygon, and is at least
  `0.50 m` from its station point;
- every 3D framing point is finite, belongs to one declared target geometry
  within a `0.01 m` tolerance, and has horizontal line of sight from the station
  inside the room;
- every pitch is one of the three supported values;
- every numeric pitch is finite, agrees with its category, and is within the
  reviewed camera guidance range;
- every scale-anchor measurement exists, targets the declared object, is
  positive, and has `exact_override` provenance;
- every room wall appears exactly once in `wall_review`;
- every room opening appears exactly once under its actual parent wall;
- `bath-door-south` remains on `wall-02`, while `wall-03` remains opening-free;
- the immutable floor-plan asset exists and matches its manifest hash.

Geometry validation distinguishes release-blocking errors from pilot warnings.
The following are errors:

- the complete segment from a station to its aim point leaves the concave floor
  polygon before reaching the aim point;
- a station lies on a wall or inside any non-walkable proxy footprint;
- a required scale anchor is not a primary target from at least two distinct
  stations whose baseline is at least `0.50 m`;
- the angular span of a shot's framing points exceeds the usable horizontal
  field of view after its margins;
- framing points that explicitly require a full vertical extent exceed the
  usable vertical field of view at the shot's pitch and camera height;
- a referenced target is geometrically behind the shot bearing rather than
  inside its field-of-view cone.

The following initially produce report warnings, because their thresholds must
be calibrated by the first real Xiaomi batch:

- paired views at one station differ by more than `0.7 × horizontal_fov_deg`;
- neighboring route stations do not have a mutually visible structural wall
  span of at least `0.50 m` inside both view cones;
- a station is closer than `0.30 m` to a wall or movable proxy;
- the first boundary hit is closer than `1.0 m` to the station;
- a same-station up/down shot overlaps every compatible level shot by less than
  30% of the smaller vertical angular interval;
- vertical ray/FOV analysis using room height, camera height, pitch, and vertical
  FOV finds no planned coverage of a required floor-wall seam. Every structural
  wall's floor seam is required; ceiling seams are advisory because the room
  height is already measured;
- a wall is a primary target from fewer than two stations, or the maximum
  baseline between those stations is below `0.50 m`. Under the reviewed
  `lite-24` targets this intentionally reports `wall-03`; it cannot pass
  silently merely because one station names it.

The report stores per-shot bearings, first-wall intersections, angular target
spans, visible target IDs, adjacent-station shared spans, vertical extents, and
all warning/error codes. The HTML embeds a toggleable diagnostic FOV layer over
the floor plan; this satisfies the coverage-map requirement without creating a
fourth generated file. Warnings remain visible in the mode-selection screen and
report, but the field operator does not make a geometry-release decision. A
plan author records reviewed warning codes, reviewer, and timestamp in a
`coverage_review` record before publishing the route. During this pilot the plan
author and operator may be the same person. After measured FOV and one completed
trial, the reviewed thresholds may be promoted to errors.

A draft build may emit unreviewed warnings so they can be inspected. A
publishable build requires `coverage_review` to match the current mode-plan hash
and exact warning-code set; changing geometry, optics, or warnings makes the
review stale without making exploratory generation impossible.

The general domain validator allows additional future fixed-count modes. The
project fixture tests, rather than hard-coded library branches, lock the two
current mode IDs and their exact counts.

## 8. Operator Interaction Flow

### 8.1 Entry and resume

When no valid last-active pointer exists, the page presents the two modes with
count, purpose, and risk note. If saved progress exists, each mode also shows
its completed/required count and offers `Resume`. Starting one mode does not
alter the other.

The supported pilot entry path is the same Xiaomi phone used for capture,
running current Chrome for Android and loading the page from one stable URL. A
static HTTPS origin is preferred because its origin survives Mac sleep/address
changes and enables the modern clipboard API. The development Mac may serve a
LAN HTTP URL under the §10 runtime constraints. Direct `file://`/`content://`,
in-app browsers, Xiaomi Browser, and message-app WebViews show a warning that
persistence and download are unverified.

If no saved state exists, the recommended default is `standard-48`; the user
must still make the selection explicitly. The card may carry a `Recommended`
badge, but neither mode is preselected, so the smaller route is never mistaken
for equivalent coverage.

After a mode has been started, a small `last_active_mode` pointer and its last
group are persisted. A reload or tab restoration returns directly to that route
instead of the mode chooser. It does not restore physical station confirmation.
`Change mode` remains available in the header.

Before the first station, the inherited Xiaomi checklist is mandatory: 1× 23 mm
main camera, landscape 4:3 JPG, one unchanged Leica style, watermark/filters/
AI-scene/HDR/flash/digital zoom/Dynamic Shot off, stable room lights and
curtains, and no moving screens or people. Both the entry and bathroom door are
closed before either current route starts and remain closed for the entire
route. If access or safety requires changing a door state, finish/restart under
a new capture ID rather than mixing states. The guide records acknowledgement
but cannot verify camera settings.

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
labels, and status text distinguish `current`, `completed`, `gap`, `in progress`,
and `upcoming` states.

The prominent station fill is derived from the current pass so completing pass A
does not make every standard-route marker permanently `in progress`. `current`
overrides every other visual state. Within that pass, a non-current station is
`completed` when all of its shots are completed, `gap` when it has no pending
shots and at least one skipped shot, `in progress` when it mixes resolved and
pending shots, and `upcoming` when every shot remains pending. A secondary ring
and accessible label expose whole-mode state using the same rules. A station
with no shots anywhere in a future mode is not rendered as selectable. A station
that belongs to the mode but has no task in the current pass uses a neutral
`not in this pass` fill; its outer mode ring remains active and the station
remains selectable for review.

Because tightly spaced SVG markers may overlap at phone width, the map is not
the only navigation control. A native-button station list below it exposes the
same state and is the accessibility/touch fallback.

### 8.3 Manual station confirmation

The guide says `Go to station N` and describes nearby landmarks. The user taps
`I am at station N` before the shot checkboxes and group-completion action are
enabled. This is a manual confirmation, not automatic detection. Confirmation
is held for the current in-memory station visit, including consecutive groups at
the same station. Selecting a different station or reloading requires
confirmation again. The confirmation action is exported as an audit-marker
event while being explicitly labeled operator input, not an intake interval
boundary or evidence that the phone was physically at the station.

The current page does not expose a `position_provider` field and does not request
camera, geolocation, motion, compass, or XR permission. A future automatic
provider requires a separate contract for room-coordinate registration,
confidence, permission lifecycle, secure hosting, and fallback behavior.

### 8.4 Shot and group completion

Each shot starts `pending` and offers a native checkbox. Checking it records a
completion event and advances the highlighted arrow to the next pending shot in
the group. Reopening it records a new event, restores `pending`, and updates
group and mode totals.

`Complete group` marks every pending shot in the group completed. It does not
silently erase notes. The user may undo individual shots after group completion.
The action is labeled `All photos taken — complete group` and, like the shot
checkboxes, is disabled until the current station has been manually confirmed.

When all shots in a group are completed or skipped, the page selects the next
group that still has pending work and updates the map. The search starts after
the current group in selected-mode plan order and wraps once at the end. If no
pending group exists, it opens the completion/gaps screen. It does not mark
travel between stations as photographic progress.

`Undo last action` is always available when the event log has a reversible
action. It appends an inverse event and reopens the affected group. Individual
reopen/undo, note editing, and restoring a skipped shot are allowed without
station confirmation; only a transition from pending to completed and the group
completion action require current-station confirmation. A compensation applied
by undo may restore an earlier completed state without confirmation because it
does not assert that a new photograph was taken.

Controls that would not change derived state are disabled. Repeated activation,
completing a group with no pending shots, reopening an already pending shot, or
skipping an already skipped shot appends no event.

### 8.5 Skip, notes, and out-of-order work

A shot may be marked `skipped`. The UI asks for an optional brief reason, such
as furniture obstruction, safety, or lost access. Skipped shots are not counted
as completed. The progress display shows both values, for example
`20 / 24 complete · 1 skipped`.

Skipping is available before station confirmation so an inaccessible location
can be recorded honestly. Marking the current shot skipped advances the arrow
using the same next-pending rule as completion. Restoring a skipped shot returns
it to `pending` and clears neither its note nor unrelated progress. The undo and
reopen events preserve the prior audit history.

The user may select any station marker. Selection opens the first incomplete
group at that station but does not change shot status. If the station has no
pending group, selection opens its last group so completed/skipped shots remain
reviewable and reversible. `Next incomplete` applies the same forward-then-wrap
search rule described above. This permits safe field adaptation without
pretending the original sequence was followed.

### 8.6 Completion and upload handoff

When every planned shot is operator-marked completed, the page displays
`Checklist complete — verify the album` and the existing untouched-original
upload checklist. It never states that the browser verified photo existence. If
any shot is skipped, the page instead displays `Route reviewed with gaps`, lists
the missing IDs, and does not claim full completion.

The completion screen reminds the user to:

- upload all original Xiaomi JPG files together as one folder or ZIP;
- avoid renaming, editing, recompressing, or messaging-app transfer;
- include the exported progress JSON;
- mention materially moved stations or additional untracked retakes.

The page also displays the event-log time window and the minimum number of
planned photographs expected in the phone album during that window. Extra
retakes are allowed and must not be deleted before intake.

## 9. Progress State and Persistence

The page stores no image bytes. It stores only workflow state.

Each mode uses an independent key derived from:

```text
room_id + capture_id + mode_id + mode_plan_sha256
```

The mode-specific hash covers a canonical bundle containing the capture schema,
room/capture identity, device profile, wall review, scale-anchor catalog,
selected complete mode, every station referenced by that mode, and the source
room-model SHA-256. It prevents changed instructions, camera settings, geometry,
shots, aim points, or station coordinates from silently reusing stale completion
state, while avoiding a reset when only another mode is edited.

`coverage_review` is excluded from the mode-plan hash to avoid a self-referential
digest; instead it stores and is validated against that hash. Updating only the
reviewer or review timestamp does not invalidate field progress.

Saved state contains:

- progress schema version;
- room, capture, and mode IDs;
- mode-plan hash;
- last selected group ID; the current shot is derived as the first pending shot
  in that group and is not redundantly persisted;
- an append-only action-event array with strictly increasing `seq` values.

Every event contains:

- `seq`;
- `t_ms`, UTC Unix epoch milliseconds;
- `tz_offset_min`, minutes east of UTC at the time of the action, implemented as
  the negation of JavaScript `Date.getTimezoneOffset()`;
- `type`;
- `group_id`, `station_id`, and ordered `shot_ids` where applicable;
- `method`: `shot`, `group`, or `manual_station` where applicable;
- a note payload only for note/skip events.

Event types cover capture start, station confirmation, shot completion, group
completion, skip, reopen, note change, and undo. `capture_started` is appended
after the preflight checklist when the field route opens. `group_complete`
stores all affected pending shot IDs in displayed order and `method: group`; it
does not synthesize individual shutter events.

Undo is a strict backward stack, not a toggle or redo. An undo event is never an
undo candidate. Each new undo references the latest earlier state-changing
event that is not itself an undo and has not already been compensated; two
successive undo actions therefore roll back two distinct actions. Station
confirmation is not an undo target, cursor changes are not events, and
compensation bypasses station-confirmation gating. Current per-shot status and
note values are derived by replay.

Replay accepts only the longest valid event prefix. At the first invalid event
or reference it stops, warns, and derives state from the valid prefix; it never
skips forward into later events whose dependencies may be broken. The complete
raw event array remains untouched and exportable for diagnosis.

The controller writes after every event and cursor change. Refresh replays the
event log, validates the last group, derives its current shot, and reconstructs
the view. Switching modes preserves both mode logs. The last-active-mode pointer
contains only room/capture/mode/hash/group identity and never station
confirmation.

### 9.1 Storage failure

If `localStorage` is unavailable, denied, full, or corrupt:

- the workflow continues in memory;
- a persistent warning says refresh or closing the page will lose progress;
- no completion action is blocked;
- a corrupt raw value is first copied to a timestamped quarantine key when a
  write is possible, then a clean current state is started;
- if quarantine also fails, the unreadable value is left untouched and the
  workflow runs in memory;
- a valid event log with only an invalid cursor preserves its events and
  recomputes the first pending group instead of discarding all progress.

On load, the page scans the same room/capture/mode prefix for states with older
mode hashes. It never applies them to the new route, but shows their counts and
offers raw export so a copy edit or material plan revision cannot make field
work undiscoverable.

Direct `file://`/`content://` storage remains best-effort and is not the pilot's
persistence-supported path. The warning path is a supported degradation, not an
exception that crashes the guide.

### 9.2 Export and reset

`Export progress` is available at any time and downloads a canonically ordered
JSON document for the currently selected mode. It contains identity/hash fields,
the full ordered event log, derived completed/skipped/pending shot IDs, the
build-time coverage-review digest, and the first/last event time. Its values
include real action timestamps, so separate capture sessions are not expected
to produce byte-identical exports. It never includes photos or persistent
browser/device identifiers.

If Blob download fails, the page displays the exact export JSON in a read-only
text area with `Select all` and `Copy` controls. `Copy` first uses the modern
Clipboard API in a secure context, then selects the text and tries
`document.execCommand('copy')` on LAN HTTP. If both fail, the selection remains
active for manual copying.

`Reset current mode` requires confirmation and removes only the selected mode's
current-hash state. It does not reset the other mode.

Progress import and cross-device sync remain deferred.

### 9.3 Manual photo-intake contract

- The supported pilot runs the guide and Xiaomi native camera on the same phone.
- Matching uses contiguous operator-action intervals: the first begins at
  `capture_started`; each completion/group-completion/skip resolution closes the
  current interval and becomes the next interval's lower boundary.
- `station_confirmed` events are auxiliary markers inside those intervals, not
  interval boundaries, measured shutter times, or proof of station location.
  A photograph taken after arriving but before tapping confirmation therefore
  does not fall into an artificial gap.
- For `method: shot`, action order is evidence of reported shot order, still not
  direct shutter observation.
- For `method: group`, ordered `shot_ids` are explicitly marked
  `within_group_order: inferred`; downstream matching must not present them as
  observed.
- EXIF `DateTimeOriginal` is combined with `SubSecTimeOriginal` when present and
  interpreted with `OffsetTimeOriginal` when present; otherwise the event's
  `tz_offset_min` is an explicit matching assumption.
- Reopened/undone shots, overlapping time windows, missing EXIF, unexpected file
  counts, and multiple plausible photos require manual confirmation.
- Images outside every plausible action window remain `unassigned` but are
  retained for SfM and manual review; they are never discarded automatically.
- Original filenames, file bytes, and EXIF remain authoritative. The progress
  log is advisory metadata and never overwrites them.

## 10. Generated Package Contract

The CLI remains:

```text
astra-house build-capture-pack \
  --project projects/dorm-right-bedroom \
  --output build/dorm-right-bedroom/capture-pack
```

The preferred field delivery is a stable static HTTPS URL. Hosting credentials,
provider choice, and publication remain outside this generator change. For
development or the dorm pilot, the Mac may instead serve the directory on one
trusted LAN origin:

```text
caffeinate -i python3 -m http.server 8765 \
  --directory build/dorm-right-bedroom/capture-pack
```

The Mac stays connected to power with its lid open; the command, port, hostname
or reserved IP, and network remain unchanged for the complete capture. Before
starting, the phone must open and reload the exact URL successfully. If campus
Wi-Fi client isolation blocks phone-to-Mac traffic, use the stable HTTPS path
rather than changing LAN origins mid-capture. A reclaimed tab needs the same
origin to reload, so the LAN fallback is not described as independent of the
Mac. This serving step adds no generated artifact or runtime package dependency.

It still produces exactly three deterministic files:

1. `index.html` — self-contained interactive guide plus static fallback;
2. `capture-intake.json` — both mode ledgers, keyed by mode and ordered shot ID;
3. `capture-pack-report.json` — generator version, source hashes, mode counts,
   station/group counts, coverage metrics/warnings, and validation status.

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

Before comparison, hashing, or serialization, derived geometry is canonically
quantized: lengths/coordinates to `1e-4 m` and angles to `0.01°`. Threshold
decisions use the same quantized metrics. Source measurements retain their
reviewed precision. This prevents insignificant platform `libm` differences in
ray/FOV calculations from changing report bytes or warning decisions.

## 11. Rendering and Component Boundaries

Python remains responsible for trusted input parsing, geometric projection,
validation, source hashes, deterministic serialization, and atomic output.

The generated browser code is responsible only for local presentation state:

- `EventReducer`: pure replay of mode-specific events into status and notes;
- `StateStore`: validated `localStorage`, stale-version discovery, quarantine,
  and in-memory fallback;
- `CaptureController`: event creation, undo, cursor derivation, and the
  forward-then-wrap selection rule;
- `MapView`: station, ray/cone, pass/mode status, and diagnostic rendering from
  embedded precomputed geometry;
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
Static content remains visible until controller initialization has completed
successfully. Only then may an `enhanced` class switch to the interactive view;
an initialization exception therefore leaves a usable guide rather than a blank
page.

With JavaScript disabled, the page displays:

- mode summaries and coverage warnings;
- the full route map and direction legend;
- printable 24- and 48-shot checklists;
- Xiaomi settings, structural wall review, and upload instructions.

Interactive controls use native buttons, checkboxes, text areas, and confirmation
dialogs. Dynamic progress changes use a polite live region. Keyboard focus is
never removed or replaced with custom-only gestures.

At both 320 and 390 CSS pixels, map labels, instructions, controls, and status
text must fit without document-level horizontal overflow. Print output shows
static checkboxes and omits controls whose behavior cannot exist on paper.

## 13. Error Handling

- Invalid capture data stops generation before replacing any artifact.
- Missing or hash-mismatched floor-plan data stops generation.
- An invalid event or unknown group/shot reference stops replay at that event;
  the longest valid prefix supplies state, while the untouched raw log remains
  exportable with a warning.
- An invalid cursor is recomputed from the event-derived statuses.
- A mode-plan hash mismatch starts a fresh state under a new key and leaves the
  previous key untouched and exportable.
- Storage write failure switches to memory and reports the persistence loss.
- Repeated/no-op button activation is idempotent, cannot increment counts twice,
  and appends no event.
- Direct station selection changes only the cursor, never completion state.
- Skipped shots prevent a false `complete` result.
- Export failure is surfaced as an actionable message and leaves progress intact.
- Missing browser APIs degrade to static/manual operation rather than blocking
  capture.
- Unsupported origin/browser combinations are identified before capture and do
  not receive a false persistence guarantee.

## 14. Testing Strategy

### 14.1 Domain tests

- Parse schema `2.0` into immutable stations, modes, passes, groups, and shots.
- Pin current mode order and exact counts to 24 and 48.
- Pin lightweight mode to 14 groups and standard mode to 28 groups with the
  reviewed station assignments.
- Freeze the schema-`1.0` ordered shot tuples and prove that flattening
  `standard-48` from schema `2.0` reproduces every ID, standing point, pitch,
  target list, instruction, and order exactly.
- Reject duplicate IDs or station numbers, missing station references, invalid
  counts, unknown targets, invalid pitch, invalid aim points, and stations outside
  the concave floor polygon.
- Test concave-polygon segment containment, first-wall ray intersections,
  horizontal/vertical FOV framing spans, anchor measurements/baselines, station
  clearances, adjacent shared spans, two-station wall coverage, required floor
  seams, and 30% vertical-overlap warnings.
- Assert the unchanged standard targets satisfy every required anchor from at
  least two stations, while `lite-24` reports the reviewed single-station
  `wall-03` warning.
- Allow draft warning output but require an exact current hash/code match before
  report status becomes publishable; stale coverage review remains visible.
- Preserve the regression that `bath-door-south` belongs to `wall-02` and
  `wall-03` contains no opening.
- Prove a third valid fixed-count mode can be parsed without adding a renderer
  branch, demonstrating the production-mode extension point.

### 14.2 Renderer and CLI tests

- Generate exactly the three promised files deterministically.
- Assert both modes and all 72 distinct shot IDs are present in static HTML and
  machine-readable intake data.
- Assert mode-plan hashes and counts appear in the report.
- Assert the embedded map contains eight stations, per-shot aim geometry, FOV
  cones, and the same diagnostic codes as the report.
- Assert derived coordinates and angles use canonical quantization and match
  fixed expected report bytes in the supported macOS and Linux CI environments.
- Assert no external resource URL or network-dependent element is emitted.
- Preserve fail-before-replacement behavior for invalid inputs.

### 14.3 Browser interaction tests

Playwright serves the generated directory from a local HTTP origin and exercises
it at desktop, 390 × 844, and 320-pixel-wide viewports. A separate smoke test
opens `file://` only to verify honest fallback behavior:

- select each mode and verify its independent total;
- confirm a station, complete one shot, and verify progress and arrow state;
- verify station-confirmation and resolution events contain sequence, UTC time,
  timezone offset, method, and composite identity;
- complete a group and verify automatic next-group selection;
- verify forward-then-wrap traversal, completed-station reopening, global undo,
  and undo without station confirmation;
- verify two consecutive undo actions compensate two distinct events, undo
  events are never undo targets, and compensation may restore completed state
  without station confirmation;
- skip with a note and verify the route is not reported complete;
- click an out-of-order station and verify no shot status changes;
- reload and verify persistence;
- switch modes and verify state isolation;
- reset one mode and verify the other remains unchanged;
- intercept and validate the progress JSON download;
- force Blob/clipboard failure and verify the read-only manual-copy fallback;
- verify secure-context Clipboard API, LAN-HTTP `execCommand` fallback, and
  final manual selection paths;
- inject unavailable, corrupt, and failing storage and verify the warning and
  in-memory fallback, corrupt-value quarantine, and invalid-cursor recovery;
- simulate a stale mode hash and verify old progress is discoverable/exportable
  but never applied;
- inject an invalid middle event and verify replay stops at the longest valid
  prefix while raw export retains the suffix;
- assert no-op controls append no event and `capture_started` is emitted once;
- assert Pacific daylight time records `tz_offset_min: -420`;
- verify `not in this pass` styling while the station remains selectable;
- disable JavaScript and verify both static checklists remain readable;
- inject an initialization exception and verify static content stays visible;
- assert `scrollWidth == clientWidth` at desktop, 390 × 844, and 320-pixel-wide
  viewports;
- use station-list buttons and hit-testing to verify nearby SVG targets do not
  make a station unreachable;
- compare static DOM instructions against embedded plan data exactly;
- render a third-mode fixture and run its full select/confirm/complete/export
  flow, rather than proving parsing alone;
- use screenshot baselines for map labels, status treatments, direction/FOV
  geometry, current task, and completion handoff in a pinned browser/container
  image with an explicit system-font stack.

No camera, motion-sensor, WebXR, or cloud permission is needed. While the loaded
document remains alive it makes no further network request; a browser reload
still requires the same origin to be reachable.

### 14.4 Required real-device pilot matrix

Desktop Playwright cannot validate Android `content://`, tab reclamation, LAN
client isolation, or vendor WebViews. Before field release, the Xiaomi test
records pass/fail evidence for current Chrome over stable HTTPS and the Mac-LAN
fallback: first open, refresh, switch to the native camera and return, simulated
tab kill/reload, independent mode state, download, copy fallback, server
unreachable during reload, and recovery through the same origin. The tab-kill
report records the exact Android developer/ADB method and confirms from server
logs whether Chrome requested the document again. Direct file, Xiaomi Browser,
and WeChat are tested only to verify that they warn or degrade honestly; they are
not promoted to supported paths by a desktop test.

## 15. Migration and Compatibility

- Replace the committed schema-`1.0` capture plan with the reviewed schema-`2.0`
  multi-mode plan in one change; generated `build/` artifacts remain ignored.
- The repository audit confirms that schema `1.0` currently has exactly eight
  unique standing points; B shots are already consecutive by station; and every
  C/D standing point exactly equals one of those eight points. Standard shot IDs
  use A/B/C/D prefixes, so they do not collide with the new L-prefixed shots.
- Before replacement, commit the ordered schema-`1.0` tuples as a test fixture
  and require byte-for-value equivalence after flattening `standard-48`.
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
- The generator adds no frontend framework, build tool, database, hosting
  service, or cloud job; a separately supplied static HTTPS origin may serve the
  three generated files.
- One self-contained operator page and two small JSON handoff files.
- Progress contains metadata only. Its append-only log grows with operator
  actions, not photograph bytes, and remains small at the planned route sizes.
- Browser tests use the already established Playwright development workflow.

## 17. Acceptance Checklist

- [ ] `lite-24` contains exactly 24 reviewed images.
- [ ] `standard-48` preserves exactly 48 reviewed images.
- [ ] Both modes use the same eight valid station locations.
- [ ] Every shot has validated targets, pitch, instruction, aim point, and 3D
      framing points.
- [ ] Every required scale anchor is targeted from two stations at least 0.5 m
      apart and references exact measurements for the same object.
- [ ] Geometry preflight reports line of sight, FOV span, neighboring overlap,
      vertical coverage, and uncovered walls before field use.
- [ ] The map updates pass/mode station state, ray, and FOV cone after each
      action.
- [ ] The current group can be completed, undone, skipped, or visited out of
      order without corrupting totals.
- [ ] The event log distinguishes individual and group resolution, records UTC
      plus timezone offset, preserves undo history, and rolls consecutive undo
      actions backward rather than toggling.
- [ ] Mode progress is independent and survives refresh when storage works.
- [ ] Storage failure is visible and non-blocking.
- [ ] A supported Chrome/HTTP(S) reload resumes the active mode and group when
      the same origin is reachable, without pretending station confirmation
      survived; unreachable/recovery behavior is tested explicitly.
- [ ] Exported progress identifies the exact room, batch, mode, plan hash, and
      missing shots.
- [ ] Download failure exposes the same JSON for manual copy.
- [ ] No automatic physical-position claim appears in the interface.
- [ ] Static fallback includes all 72 current planned photographs.
- [ ] The page is readable without horizontal overflow at 320 and 390 CSS
      pixels, with native station buttons available when map markers overlap.
- [ ] The Xiaomi real-device matrix passes for Chrome over the supported URL;
      unsupported opening paths warn rather than promising persistence.
- [ ] The package remains self-contained and reproducible.
- [ ] A third-mode fixture completes the full interaction flow without a
      mode-specific renderer branch.
