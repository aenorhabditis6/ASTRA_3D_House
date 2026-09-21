# Dorm Diagnostic Capture Package Design

Date: 2026-09-20

Status: approved

Target: right-side dorm bedroom in `projects/dorm-right-bedroom`

## 1. Purpose

This subproject creates a lightweight, repeatable shooting package for the
first RGB reconstruction experiment. It tells a non-specialist exactly what to
photograph with an ordinary phone and records enough shot identity to diagnose
coverage failures later. The pilot uses a Xiaomi 17 Ultra as its primary camera;
an iPhone remains a fallback for a separate batch, not a second camera mixed into
the same capture.

The package is deliberately smaller than the final 120–220-image capture. Its
first batch contains 48 planned still images and answers one question: can the
room be captured with enough continuous overlap to recover one connected set of
camera poses before the user spends time on a full appearance pass?

## 2. Success Criteria

- A single command generates a self-contained capture guide for the current
  `room.json` and reviewed floor-plan annotation.
- The guide contains exactly 48 unique shot IDs divided into four purposeful
  passes.
- A route map shows approximate standing zones, travel direction, and the room
  surfaces each pass must cover; it never claims the stations are survey-grade
  camera coordinates.
- The guide is readable on a phone and printable without an internet connection.
- Doors and windows are listed by parent wall, cardinal role, and plan location
  before any camera route is shown.
- The bathroom door is attached to `wall-02`, beside the closet on the
  west-facing drawing-bottom wall. `wall-03` is explicitly identified as the
  connecting return and contains no door.
- The generated package uses only the Python standard library and existing
  project data. It does not install COLMAP, hloc, OpenCV, or a cloud client.
- The device card distinguishes RGB camera-pose recovery, optional ARCore
  depth-from-motion, laser autofocus, and hardware LiDAR instead of treating
  them as interchangeable capabilities.

## 3. Scope

### 3.1 Included

- A versioned capture-plan data file for the dorm room.
- Validation of pass counts, shot IDs, target wall IDs, and station locations.
- A deterministic self-contained HTML guide with an embedded vector route map,
  shot ledger, Xiaomi settings, preparation checklist, and upload checklist.
- A machine-readable empty intake manifest that maps later source filenames to
  planned shot IDs without modifying the originals.
- Automated unit tests plus a rendered browser screenshot for visual QA.

### 3.2 Deferred

- Reading or converting uploaded images.
- Blur, exposure, duplicate, or EXIF quality analysis.
- HEIC-to-JPEG working-copy generation.
- hloc, LightGlue, COLMAP, dense depth, LiDAR, or Gaussian Splatting.
- Automatic reshoot recommendations based on recovered cameras.
- A mobile capture application.

Those functions belong to the next subproject after the 48-image batch exists.

## 4. Structural Review Gate

The capture plan contains an explicit `wall_review` table. Generation fails if
an opening points to a different wall than its reviewed entry. This is the
defense against confusing a door swing or opened door leaf with the actual wall
opening.

The first room uses this mapping:

| Wall ID | Reviewed role | Openings |
| --- | --- | --- |
| `wall-00` | east wall, drawing top | two windows |
| `wall-01` | south long wall, drawing right | none |
| `wall-02` | west-facing bath wall beside closet, drawing bottom | bathroom door |
| `wall-03` | connecting return between the two west-facing walls | none |
| `wall-04` | west-facing entry wall, drawing bottom | living-room exit door |
| `wall-05` | north wall, drawing left, measured 2.94 m | none |

The guide shows this table next to a small orientation key. Door-swing arcs may
be visible in the embedded floor plan, but they are never used as the source of
the parent-wall assignment.

## 5. Capture Plan Contract

The source file is
`projects/dorm-right-bedroom/capture-plan.json`. It has these top-level fields:

- `schema_version`: capture-plan schema version, initially `1.0`.
- `room_id`: must match `room.json` and `plan-annotation.json`.
- `capture_id`: stable identifier for this diagnostic batch.
- `expected_image_count`: exactly `48` for this batch.
- `device_profile`: orientation, lens, file-format, lighting, and motion rules.
- `wall_review`: reviewed wall roles and opening assignments.
- `passes`: ordered passes containing shot groups and instructions.
- `intake_fields`: columns required by the empty intake manifest.

Each shot contains a unique ID, pass ID, approximate room-space standing point,
target wall IDs or opening IDs, pitch class (`level`, `up`, or `down`), and a
short operator instruction. Standing points are guidance markers. They must be
inside the floor polygon, but approximate furniture proxies do not make them
hard navigation constraints; the operator moves to the nearest safe clear spot
without changing the sequence.

## 6. The 48-Image Diagnostic Batch

### Pass A — structure loop, 24 images

Eight clockwise standing zones, three overlapping level images per zone. At
each zone the operator photographs left, center, and right with roughly 70–80%
visual overlap. The path stays in accessible floor space and keeps the 1× rear
camera near chest height.

Purpose: create a continuous camera graph around the room and connect every
major wall to its neighbors.

### Pass B — high/low coverage, 8 images

Four of the structure-loop zones are reused. Each produces one slightly upward
and one slightly downward image while retaining substantial content from the
corresponding level views.

Purpose: cover ceiling lines, baseboards, the floor, and furniture tops without
creating a disconnected second route.

### Pass C — corners and occlusions, 8 images

Four important boundaries are photographed from two sides: the desk/window
corner, bed/window corner, closet/bath-door area, and entry-door/north-wall
area.

Purpose: supply parallax where large furniture or the L-shaped return hides
wall-floor junctions.

### Pass D — openings and anchors, 8 images

- three images covering both east-wall windows together and from oblique sides;
- two images covering the entry door with surrounding wall context;
- two images covering the bathroom door and adjacent closet with surrounding
  wall context;
- one image showing the bed together with two wall directions as a visual scale
  cross-check.

Purpose: make openings and existing metric anchors identifiable without relying
on reflective window glass as a geometric feature.

## 7. Xiaomi 17 Ultra Capture Rules

- Use still photographs, landscape orientation, and only the 1× Leica 23 mm
  main camera for all 48 images. Do not switch to the 14 mm ultra-wide or the
  75–100 mm telephoto.
- Use the normal 4:3 photo mode and JPG output. Do not use 50 MP, RAW, portrait,
  panorama, long exposure, burst, Dynamic Shot, digital zoom, or video for the
  diagnostic batch.
- Select one Leica photographic style before the first image and do not change
  it during the batch. Disable Leica filters and the Leica watermark.
- Keep room lights and curtains in one state for the complete batch. Turn flash
  off and avoid people, moving pets, television content, and changing displays.
- Clean the lens, hold the phone with two hands, pause before each exposure, and
  retake visibly blurred frames immediately without deleting the original until
  intake.
- Do not rename files on the phone. Capture order plus EXIF time will later map
  originals to planned shot IDs.

Xiaomi lists a 50 MP, 23 mm-equivalent, one-inch main camera with OIS and JPG,
HEIF, and RAW capture. It also lists a laser focus sensor, but no LiDAR or ToF
depth sensor. Laser autofocus is not treated as room-scanning geometry.

Official specification:
<https://www.mi.com/global/product/xiaomi-17-ultra/specs/>.

### 7.1 Optional ARCore probe

Ordinary still-photo reconstruction does not require ARCore: camera positions
are recovered later from overlap between images. ARCore, if supported by the
exact phone/ROM, can additionally record motion tracking and software depth in
a separate experiment. Google describes its Depth API as depth-from-motion that
may merge available ToF hardware; it is not equivalent to an iPhone Pro LiDAR
scan.

The current official ARCore device table lists Xiaomi 17, 17 Pro, 17 Pro Max,
17T, and 17T Pro with Depth API support but does not explicitly list Xiaomi 17
Ultra. The capture pack therefore labels ARCore as `unverified_optional` and
does not require it. A later compatibility probe may promote it without changing
the 48-shot RGB batch.

Official references:

- <https://developers.google.com/ar/develop/depth>
- <https://developers.google.com/ar/devices>

### 7.2 Single-device rule

All 48 diagnostic images come from the Xiaomi 17 Ultra. An iPhone reshoot is a
new capture batch with a new capture ID. Images from different phones are not
silently mixed because their intrinsics, processing, color, and filenames may
form separate reconstruction behavior that must be diagnosed independently.

## 8. Generated Guide

The command

```text
astra-house build-capture-pack \
  --project projects/dorm-right-bedroom \
  --output build/dorm-right-bedroom/capture-pack
```

produces only three files:

1. `index.html` — self-contained guide with the plan image embedded as data,
   the SVG route map, preparation/settings checklists, wall review, four passes,
   upload instructions, and the Xiaomi 17 Ultra settings card.
2. `capture-intake.json` — empty 48-row manifest keyed by planned shot ID, ready
   for later source filenames and hashes.
3. `capture-pack-report.json` — generator version, source hashes, counts, and
   validation status.

The HTML is the operator-facing artifact. The JSON files are for the later
intake/QC command. Generated files remain under ignored `build/`; the reviewed
source capture plan is committed.

## 9. Upload Contract

After shooting, the user uploads all original images from this batch together,
preferably as one folder or ZIP. Originals remain byte-for-byte unchanged. The
later intake step records original filename, SHA-256, EXIF capture time,
orientation, dimensions, and assigned shot ID. Derived JPEG or resized working
copies live outside the originals directory.

The capture guide asks the user to include one note if they skipped, repeated,
or materially moved a station. It does not ask them to rename 48 files by hand.

## 10. Validation and Failure Handling

- Duplicate shot IDs, unknown wall/opening targets, a count other than 48, or a
  room-ID mismatch stop generation.
- A station outside the room polygon stops generation.
- A `wall_review` opening assignment that disagrees with `room.json` stops
  generation and names the conflicting opening and walls.
- Missing floor-plan assets or hash mismatches stop generation before output.
- Existing output files are replaced only after all input validation succeeds.
- Furniture obstructing an approximate station is handled operationally: move
  the photographer to the nearest safe clear spot, not the furniture, and keep
  the same target and sequence.
- The guide marks reflective window glass, mirrors, screens, and featureless
  painted walls as unreliable geometry; they must remain framed with textured
  surrounding edges.

## 11. Testing

- Unit tests parse and validate the capture plan, including count, uniqueness,
  room membership, and target references.
- A regression test pins the bathroom door to `wall-02` and proves `wall-03`
  contains no opening.
- CLI tests verify deterministic creation of all three output files and failure
  before partial output on invalid input.
- HTML tests verify the 48 shot IDs, four pass headings, source hash, wall review,
  embedded plan image, Xiaomi 23 mm primary-camera rule, and optional/unverified
  ARCore status.
- Browser visual QA renders the local HTML at desktop and phone widths and checks
  that the map, checklist, and shot table are legible without horizontal
  overflow.

## 12. Resource Budget

- No new runtime Python package.
- No cloud job during capture-pack generation.
- No AI-generated diagram; the route is drawn from reviewed room geometry.
- One self-contained human-facing HTML file rather than a web application.
- The 48-image batch is diagnostic. A full 120–220-image capture is requested
  only after camera recovery proves the route is viable.
