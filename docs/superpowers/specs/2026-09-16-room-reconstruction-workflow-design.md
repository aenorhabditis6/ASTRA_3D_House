# ASTRA Single-Room Reconstruction Workflow Design

Date: 2026-09-16

Status: proposed for implementation

First target: upper-right bedroom in the supplied dorm suite floor plan

## 1. Purpose

ASTRA reconstructs an editable, metrically meaningful room and a separate photorealistic appearance representation from a trusted floor plan plus ordinary iPhone imagery. LiDAR improves the result when available but is never required.

The workflow deliberately separates structural truth from visual appearance:

- A parametric room model provides clean walls, openings, scale, semantic objects, and editable topology.
- Photographs refine facts missing from the plan and supply textures.
- An optional Gaussian Splat represents view-dependent detail without corrupting the clean architectural mesh.

The first implementation is a semi-automatic desktop workflow. It uses command-line orchestration and Blender Python, with explicit human review gates. A button-driven Blender add-on may be built after the workflow is stable.

## 2. Scope

### 2.1 MVP scope

- Reconstruct only the upper-right bedroom in `assets/reference/floorplans/dorm-suite-floorplan.png`.
- Exclude the adjacent bathroom and central shared area.
- Use the supplied floor plan as the hard constraint for relative plan geometry.
- Use a Full mattress footprint of 54 x 75 in (1.3716 x 1.905 m) as the initial XY scale anchor.
- Use the confirmed 11 ft (3.3528 m) floor-to-ceiling height as the Z scale anchor.
- Represent the bed, desk, chair, chest, and pedestal as simple semantic proxy geometry.
- Produce an editable Blender master, a GLB delivery model, a quality report, and an optional Gaussian Splat PLY.
- Run geometry and Blender generation on Apple Silicon with 16 GB memory or better, without requiring NVIDIA CUDA.
- Allow optional cloud GPU execution for Gaussian Splatting and other expensive appearance work.

### 2.2 Non-goals for the MVP

- Fully automatic reconstruction with no human review.
- Multi-room alignment or complete dorm-suite reconstruction.
- High-fidelity custom furniture modeling.
- Inventing surfaces hidden in every photograph.
- Developing a mobile capture app or Blender GUI add-on.
- Treating a Gaussian Splat as the editable architectural model.

## 3. Source-of-Truth Policy

Conflicts are resolved in this order:

1. Trusted floor-plan topology and proportions.
2. Confirmed tape or laser measurements.
3. Optional LiDAR or Apple RoomPlan measurements.
4. Multi-view image geometry and recovered camera poses.
5. Monocular depth or other learned estimates.

The plan determines wall relationships and room topology. Photographs may refine heights, openings, fixture positions, and appearance, but they must not silently distort plan proportions. Every inferred field in the room schema records its source and confidence.

The Full bed is an initial metric anchor, not a permanent substitute for a wall measurement. A later measured wall length replaces the bed-derived global XY scale without changing the relative plan geometry.

## 4. Capture Protocol

### 4.1 Room preparation

- Keep furniture and objects stationary during a capture set.
- Keep all room lights on and avoid changing lighting mid-session.
- Disable digital zoom, filters, portrait mode, and lens switching.
- Use the 1x rear camera in landscape orientation.
- Clean the camera lens and preserve original files with EXIF metadata.
- People and pets remain outside the frame.

Clutter is acceptable for structural capture. A later, tidier pass is preferred for clean material acquisition because occluded surfaces cannot be recovered faithfully.

### 4.2 RGB capture passes

1. **Structure loop:** Walk around the room at chest height, 0.8-1.5 m from walls when possible. Move about 20-30 cm between photographs and keep 70-80% overlap.
2. **Occlusion pass:** Photograph room corners and the boundaries behind or beside the bed, desk, and cabinets from both sides. Each wall corner should be visible from at least three positions.
3. **High/low pass:** Repeat shorter routes with the camera tilted slightly upward and downward to cover the ceiling line, baseboards, and furniture undersides.
4. **Opening details:** Capture the window and door together with surrounding wall features. Reflective glass is not used as a geometric feature.

The target for the first room is 120-220 accepted still images. Video may be ingested later, but still images are the reference capture format for the MVP.

### 4.3 Metric anchors

- Required for the first logical model: Full bed label and 11 ft ceiling height.
- Recommended refinement: one measured full wall length.
- Useful additional measurements: room depth, door width and height, window width and sill height.
- Optional: one Apple RoomPlan export from a LiDAR-equipped iPhone.

## 5. System Architecture

The workflow is divided into seven replaceable modules with versioned file interfaces.

### 5.1 Asset archive

Stores immutable source files and a manifest containing hashes, timestamps, device metadata, and capture-set identity. Derived assets never overwrite sources.

### 5.2 Plan interpretation

Registers the floor-plan image, isolates the selected room, vectorizes walls and openings, places semantic furniture proxies, and writes `room.json`. The first version may include a human confirmation step for extracted line segments.

### 5.3 Image quality control

Reads EXIF, normalizes orientation, detects blur, flags exposure discontinuities, finds near-duplicates, and reports likely coverage gaps. Rejected images remain in the archive with rejection reasons.

### 5.4 Camera and reference geometry

Uses COLMAP/PyCOLMAP for feature matching, camera calibration, Structure-from-Motion, and a reference point cloud. Optional RoomPlan/LiDAR data is transformed into the same coordinate system as an additional constraint.

### 5.5 Structural fusion

Aligns recovered cameras and reference geometry to the parametric room. It may refine fields not fixed by the plan, but preserves the plan topology and relative proportions. Low-confidence changes require human confirmation.

### 5.6 Blender scene generation

A deterministic Blender Python script consumes `room.json` and creates these collections:

- `STRUCTURE`: walls, floor, and ceiling.
- `OPENINGS`: door and window geometry.
- `FIXTURES`: fixed room elements.
- `FURNITURE_PROXY`: simplified semantic furniture.
- `PHOTO_REFERENCE`: cameras and reconstruction references.
- `APPEARANCE`: textured meshes or links to appearance assets.

Re-running generation produces the same logical scene for the same schema version and input values. Manual review changes are written back as explicit overrides rather than becoming unexplained mesh edits.

### 5.7 Appearance and export

Selected photographs are projected and baked into PBR textures for the clean structure. Unknown or occluded regions retain a neutral material and an explicit reshoot flag. A separate cloud-capable path trains a Gaussian Splat from registered images and exports a PLY. The master `.blend`, delivery `.glb`, and appearance `.ply` remain separate artifacts.

## 6. Core Data Contract

`room.json` is the stable boundary between interpretation, reconstruction, and Blender generation. Dimensions use meters, angles use radians, and the room uses a right-handed Z-up coordinate system.

The document contains:

- Schema and generator versions.
- Room identity and coordinate-system declaration.
- Scale anchors and their provenance.
- Floor polygon and ceiling height.
- Wall segments with thickness and connectivity.
- Doors, windows, and other openings attached to wall identifiers.
- Fixtures and furniture proxies with semantic class, dimensions, and transform.
- Optional registered cameras and reconstruction references.
- Per-field provenance, confidence, and manual overrides.
- Validation state and unresolved reshoot requirements.

Generated geometry is not the source of truth. A corrected dimension is written to `room.json`, after which Blender geometry is regenerated.

## 7. End-to-End Data Flow

1. Create a room project and copy source assets into the immutable archive.
2. Hash assets and build the capture manifest.
3. Register and crop the floor plan to the upper-right bedroom.
4. Create `room.json` v0 using plan proportions, the Full bed scale anchor, and the 11 ft height.
5. Generate the untextured Blender shell and proxy furniture.
6. Render a top-down overlay against the source plan and require human structural approval.
7. Ingest room images and run automated image quality checks.
8. Recover camera poses and reference geometry.
9. Align the reconstruction to the approved parametric room and propose only allowed refinements.
10. Require human approval for low-confidence or topology-affecting proposals.
11. Bake clean structural textures from selected views.
12. Optionally train and export a Gaussian Splat on a cloud GPU.
13. Validate, export, and write a machine-readable and human-readable quality report.

## 8. Failure Handling

- If fewer than 80% of accepted images register, stop appearance processing and produce a reshoot report.
- If camera reconstruction splits into disconnected components, do not merge them by guesswork; report the missing transition views.
- If plan extraction is ambiguous, preserve the source overlay and require a human line or opening confirmation.
- If scale anchors conflict, preserve both measurements, identify their sources, and require a choice rather than averaging silently.
- If a surface is hidden or texture evidence is inconsistent, assign a neutral material and mark it for reshoot.
- Mask mirrors, windows, displays, people, and other unstable or reflective content before dense geometry or texture baking.
- If LiDAR disagrees with a trusted plan, use it as diagnostic evidence. It does not automatically replace plan topology.
- Each stage is restartable from its own outputs; failure in Splatting does not invalidate the structural model.

## 9. Quality Gates

### 9.1 Provisional model

- Bed-anchored overall dimensional error target: at most 10 cm or 3%, whichever is larger.
- Floor-plan overlay shows no unexplained wall or opening displacement.
- Wall, floor, and ceiling geometry is closed and manifold where expected.
- Door and window objects are attached to their parent walls and do not float or intersect incorrectly.

### 9.2 Refined model

- After one measured wall length is supplied, major wall and opening error target: 3-5 cm.
- At least 80% of accepted images register into one connected reconstruction.
- Blender headless generation completes without errors.
- Exported GLB can be read back, uses meters, and retains expected object names and material assignments.
- Visible structural surfaces have usable textures or explicit neutral/reshoot status.

### 9.3 Automated tests

- JSON schema and semantic validation.
- Unit and coordinate conversion tests.
- Wall connectivity and opening-placement tests.
- Deterministic geometry-generation fixtures.
- Blender headless build smoke test.
- GLB export and read-back test.
- Rendered top-down overlay regression test.

## 10. Project Artifacts

Each reconstruction project produces:

- Immutable source assets and `manifest.json`.
- Versioned `room.json` plus explicit override history.
- Image QC and reshoot reports.
- COLMAP cameras, sparse points, and alignment transform.
- Plan overlay and structural review renders.
- Editable `house_master.blend`.
- Portable `house.glb`.
- Optional `appearance.ply` and Splat training metadata.
- Final quality report containing metric errors, warnings, software versions, and source provenance.

## 11. Technology Choices

- Python for orchestration, schemas, validation, and image preparation.
- OpenCV-compatible image operations for plan registration and quality analysis.
- COLMAP/PyCOLMAP for camera recovery and reference geometry.
- Blender and its Python API for deterministic parametric modeling, review renders, material baking, and export.
- Nerfstudio Splatfacto or a compatible replaceable backend for optional cloud Gaussian Splatting.
- Apple RoomPlan as an optional LiDAR input, not a mandatory dependency.

Primary references:

- COLMAP: <https://colmap.github.io/>
- Apple RoomPlan: <https://developer.apple.com/augmented-reality/roomplan/>
- Blender glTF: <https://docs.blender.org/manual/en/4.0/addons/import_export/scene_gltf2.html>
- Nerfstudio Splatfacto: <https://github.com/nerfstudio-project/nerfstudio/blob/main/docs/nerfology/methods/splat.md>

## 12. Future Expansion

After the single-room workflow meets its quality gates, the same contracts may be extended to connected rooms, shared openings, global room graphs, multi-session alignment, guided mobile capture, and a Blender add-on. These extensions must reuse the validated room schema and must not be folded into the MVP implementation.
