# Interactive guide implementation status

Date: 2026-09-21. Deliverable: implemented and browser-tested workflow plus a
separate production-gated **draft route candidate**. No field-release approval.

## What is available

- Schema-2 immutable domain with preserved schema-1 standard tuples.
- Concave-room LOS, first-boundary rays, horizontal/vertical framing checks,
  station clearance, wall/seam/adjacency metrics, anchor baselines and mode hashes.
- Strict production generation: errors stop before existing files are replaced;
  warning review must match both the exact mode hash and code set.
- One self-contained map-first page with static fallback, manual station gating,
  individual/group completion, skip/notes, successive undo and native station
  navigation. No photographs, camera permissions or position sensing.
- Independent per-mode event storage, reload resume without station confirmation,
  corrupt-data quarantine, stale-state discovery/raw export, download/copy/manual
  export fallbacks and reset confirmation.
- Original 24/48 UI simulation, generic third-mode fixture, and an actual
  production-gated 32/64 candidate. These are explicitly different artifacts.

## Why the original route remains blocked

The frozen source has 120 computed errors. A necessary-condition proof shows
that some required target combinations exceed the usable 60° FOV for any aim
point; see [geometry evidence](2026-09-21-capture-route-geometry-blockers.md).
The original source and migration fixture have not been changed. Its zero-error
acceptance is explicitly skipped, not represented as passing.

## Concrete alternative for review

Run `npm run build:capture-candidate`. This creates:

- `build/dorm-right-bedroom/capture-plan-candidate.json` — proposed source;
- `build/dorm-right-bedroom/capture-candidate/index.html` — usable interactive draft;
- `capture-intake.json` and `capture-pack-report.json` in that same package.

The reproducible authoring recipe is `scripts/build_capture_candidate.py`.
It leaves source stations, optics, wall ownership, dimensions and the original
24/48 routes untouched. Its new capture ID prevents reuse of old progress.

| Candidate | Images | Geometry errors | Unreviewed warnings | Full measured anchor views |
| --- | ---: | ---: | ---: | --- |
| candidate-lite-32 | 32 | 0 | 13 | All seven anchors, at least two stations each |
| candidate-standard-64 | 64 | 0 | 27 | Same full-span guarantee, with extra views/details |

The 32 images comprise 12 local wall views, 14 measured-anchor views and six
floor-seam views. The 64-image mode adds 12 wall patches, six ceiling seams and
14 anchor/detail views. Whole windows are separated; opening anchors require
their full measured width at lens height, not the full door/window height.
Full bed and desk outlines are preserved from two stations. Two additional
standard bed views are explicitly local texture patches, not whole-bed scale
observations. The smallest full-anchor baseline is 0.5148 m (bed), so operator
station placement needs care.

Remaining warnings concern adjacent shared span (lite), large within-group
bearing changes, short boundary rays, station clearance and vertical overlap.
No `coverage_review` approval has been written. Current visibility math covers
the floor polygon, not photo evidence or complete 3D furniture occlusion; proxy
heights/positions include provisional assumptions. Zero errors do not prove
SfM recovery, texture completeness, safety of actual cluttered standing areas,
or correct phone intrinsics.

## Verification evidence

- Python: 85 tests run; 84 pass, one explicit blocked-original-route acceptance
  skipped. Includes candidate full-extent and seven-anchor baseline checks.
- Node: eight event/storage regression tests pass.
- Pinned Chromium / Playwright 1.63.0: 37 browser tests pass, including both
  original-mode simulation completions, actual draft-candidate completions,
  third-mode extension, reload, reset, undo, bad storage, raw-tail preservation,
  export fallbacks, static/failed-init fallback and 320/390/1280 layouts.
- Eleven screenshot baselines inspected: mode selection, maps, current tasks,
  gap and completed handoff. Timestamp-only regions in handoff images are masked.
- Repeated candidate builds produce identical bytes for exactly three files.
- `git diff --check` passes. Generated build files and runtime dependencies are
  ignored and not committed.

Independent review caught a reset-history resurrection bug. The fix clears both
the in-memory controller and saved record, returns to a visible camera checklist,
and removes old action controls; the browser regression verifies a fresh start
contains only one `capture_started` event and leaves the other mode untouched.
The independent reviews were interrupted by service usage limits, so this is
not represented as a completed independent whole-branch sign-off.

## Remaining approval and field work

Adopting the 32/64 proposal changes the previously frozen route semantics/counts
and therefore remains a separate review decision. It is not the default project
capture source. A golden publishable report and current coverage-review records
are intentionally absent. The actual Xiaomi matrix remains entirely unrun:
[field evidence checklist](../field-tests/xiaomi-capture-guide-pilot.md).
